"""
Authentication service for handling magic link authentication.
"""
import os
import secrets
import string
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.database import SessionLocal
from src.auth.models import MagicToken
from src.auth.schemas import TokenCreate, TokenResponse, UserSession, TokenData
from src.auth.email import EmailService
from src.security import get_password_hash

# Configure logging
logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication logic."""
    
    def __init__(self, db: Optional[Session] = None, email_service: Optional[EmailService] = None):
        """Initialize the authentication service.
        
        Args:
            db: SQLAlchemy session (will create a new one if not provided)
            email_service: Email service instance (will create a new one if not provided)
        """
        self._db = db
        self.email_service = email_service or EmailService()
    
    @property
    def db(self) -> Session:
        """Get the current database session."""
        if self._db is None:
            raise RuntimeError("Database session not set. Use as a context manager.")
        return self._db
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        if self._db is not None:
            # If a session was provided, use it without committing/closing
            yield self._db
        else:
            # Create a new session for this scope
            session = SessionLocal()
            try:
                self._db = session
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._db = None
    
    def __enter__(self):
        """Context manager entry point."""
        if self._db is None:
            self._db = SessionLocal()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        if self._db is not None and self._db.is_active:
            if exc_type is not None:
                self._db.rollback()
            else:
                self._db.commit()
            self._db.close()
            self._db = None
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate a secure random token.
        
        Args:
            length: Length of the token in characters
            
        Returns:
            str: A securely generated random token
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage.
        
        Args:
            token: The token to hash
            
        Returns:
            str: SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def create_magic_link(self, email: str, user_agent: Optional[str] = None, 
                         ip_address: Optional[str] = None, expires_in_hours: int = 1) -> Tuple[Optional[str], bool]:
        """Create a magic login link for the given email.
        
        Args:
            email: User's email address
            user_agent: User agent from the login request (optional)
            ip_address: IP address from the login request (optional)
            expires_in_hours: Number of hours until the token expires (1-24)
            
        Returns:
            tuple: (token, success) - The generated token (or None if failed) and success status
        """
        # Validate expiration time
        expires_in_hours = max(1, min(24, expires_in_hours))  # Clamp between 1 and 24 hours
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        # Generate token and its hash
        token = self._generate_token()
        token_hash = self._hash_token(token)
        
        try:
            # Clean up any existing tokens for this email
            self.db.query(MagicToken).filter(
                MagicToken.email == email,
                MagicToken.used == False
            ).delete(synchronize_session=False)
            
            # Create new token record
            db_token = MagicToken(
                email=email,
                token_hash=token_hash,
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            self.db.add(db_token)
            self.db.commit()
            
            return token, True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create magic token for {email}: {str(e)}")
            return None, False
    
    def send_magic_link(self, email: str, user_agent: Optional[str] = None, 
                        ip_address: Optional[str] = None) -> bool:
        """Generate and send a magic login link to the user's email.
        
        Args:
            email: User's email address
            user_agent: User agent from the login request (optional)
            ip_address: IP address from the login request (optional)
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        # Create magic link token
        token, success = self.create_magic_link(
            email=email,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_in_hours=1  # Default 1 hour expiration
        )
        
        if not success or not token:
            return False
        
        # Send email with magic link
        return self.email_service.send_magic_link(
            email=email,
            token=token,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify a magic link token and mark it as used.
        
        Args:
            token: The token to verify
            
        Returns:
            tuple: (is_valid, user_data) - Whether the token is valid and associated user data if valid
        """
        token_hash = self._hash_token(token)
        now = datetime.utcnow()
        
        try:
            # Find the token in the database
            db_token = self.db.query(MagicToken).filter(
                MagicToken.token_hash == token_hash,
                MagicToken.used == False,
                MagicToken.expires_at > now
            ).first()
            
            if not db_token:
                return False, None
            
            # Mark token as used
            db_token.used = True
            db_token.used_at = now
            
            # Get or create user
            from src.models.employee import Employee
            user = self.db.query(Employee).filter(
                Employee.email == db_token.email
            ).first()
            
            # If user doesn't exist, create a new one
            if not user:
                user = Employee(
                    email=db_token.email,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
                self.db.flush()  # Flush to get the user ID
            
            # Update user's last login
            user.last_login_at = now
            user.failed_login_attempts = 0  # Reset failed login attempts
            user.account_locked_until = None  # Unlock account if it was locked
            
            self.db.commit()
            
            # Prepare user data for session
            user_data = {
                'id': user.id,
                'email': user.email,
                'is_active': user.is_active,
                'last_login': user.last_login_at
            }
            
            return True, user_data
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error verifying token: {str(e)}")
            return False, None
    
    def get_user_session(self, user_data: Dict[str, Any]) -> UserSession:
        """Create a user session from user data.
        
        Args:
            user_data: User data from the database
            
        Returns:
            UserSession: The user session object
        """
        return UserSession(
            user_id=user_data['id'],
            email=user_data['email'],
            is_active=user_data.get('is_active', True),
            last_login=user_data.get('last_login')
        )
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired and used tokens from the database.
        
        Returns:
            int: Number of tokens deleted
        """
        try:
            # Delete tokens that are either used or expired
            result = self.db.query(MagicToken).filter(
                (MagicToken.used == True) | 
                (MagicToken.expires_at < datetime.utcnow())
            ).delete(synchronize_session=False)
            
            self.db.commit()
            return result
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            return 0

# Factory function to create an AuthService instance
def create_auth_service(db: Optional[Session] = None) -> AuthService:
    """Create an AuthService instance with an optional database session.
    
    Args:
        db: Optional database session. If not provided, the service will create
           its own session when used as a context manager or with session_scope().
           
    Returns:
        AuthService: A new AuthService instance
    """
    return AuthService(db=db)

# Context manager for using AuthService with a managed session
@contextmanager
def auth_service_scope() -> Generator[AuthService, None, None]:
    """Context manager that provides an AuthService with a managed database session.
    
    Example:
        with auth_service_scope() as auth_service:
            # Use auth_service here
            user = auth_service.get_user_by_email("user@example.com")
    """
    with AuthService() as auth_service:
        try:
            yield auth_service
        except Exception:
            # Re-raise any exceptions
            raise

# For backward compatibility, provide a function that returns a new AuthService
def get_auth_service() -> AuthService:
    """Get a new AuthService instance.
    
    Note: It's recommended to use auth_service_scope() for better session management.
    """
    return AuthService()

# For backward compatibility, maintain a function that returns a singleton instance
# but document that it's not the recommended approach
_auth_service_instance = None

def get_auth_service_singleton() -> AuthService:
    """Get a singleton instance of AuthService (not recommended for production).
    
    This is provided for backward compatibility but is not the recommended approach
    for managing database sessions. Consider using auth_service_scope() instead.
    """
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance
