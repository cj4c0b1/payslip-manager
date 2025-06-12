"""
Authentication services for the application.
"""
import os
import secrets
import string
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from jose import jwt
from jose.exceptions import JWTError

from src.database import Session
from src.models.auth_models import MagicLink
from src.security import SecurityError, EncryptionManager

# Initialize encryption manager
try:
    security = EncryptionManager()
except SecurityError as e:
    logger.error(f"Failed to initialize encryption: {e}")
    raise

class AuthService:
    """
    Service for handling authentication operations.
    """
    # Token expiration time in minutes
    TOKEN_EXPIRATION_MINUTES = 15
    
    @classmethod
    def generate_token(cls, length: int = 64) -> str:
        """
        Generate a secure random token.
        
        Args:
            length: Length of the token in characters
            
        Returns:
            str: A secure random token
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @classmethod
    def hash_token(cls, token: str) -> str:
        """
        Hash a token for secure storage.
        
        Args:
            token: The token to hash
            
        Returns:
            str: The hashed token
        """
        # Use HMAC with a secret key for secure hashing
        secret_key = os.getenv('SECRET_KEY', 'default-insecure-secret-key')
        hmac_obj = hmac.new(
            secret_key.encode(),
            msg=token.encode(),
            digestmod=hashlib.sha256
        )
        return hmac_obj.hexdigest()
    
    @classmethod
    def create_magic_link(
        cls,
        email: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Tuple[str, MagicLink]:
        """
        Create a new magic link for the given email.
        
        Args:
            email: The email address to send the magic link to
            user_agent: The user agent of the requester
            ip_address: The IP address of the requester
            user_id: Optional user ID if the user already exists
            
        Returns:
            tuple: (plaintext_token, magic_link_object)
        """
        # Generate a secure token
        token = cls.generate_token()
        hashed_token = cls.hash_token(token)
        
        # Create and save the magic link
        with Session() as session:
            magic_link = MagicLink(
                token=hashed_token,
                email=email,
                user_agent=user_agent,
                ip_address=ip_address,
                user_id=user_id
            )
            
            session.add(magic_link)
            session.commit()
            
            # Refresh to get the updated object with database defaults
            session.refresh(magic_link)
            
            return token, magic_link
    
    @classmethod
    def verify_magic_link(
        cls,
        token: str,
        email: str
    ) -> Optional[MagicLink]:
        """
        Verify a magic link token and return the associated magic link if valid.
        
        Args:
            token: The token to verify
            email: The email address the token was sent to
            
        Returns:
            Optional[MagicLink]: The magic link if valid, None otherwise
        """
        hashed_token = cls.hash_token(token)
        
        with Session() as session:
            # Find a matching, unused, unexpired token
            magic_link = session.query(MagicLink).filter(
                MagicLink.token == hashed_token,
                MagicLink.email == email,
                MagicLink.is_used == False,
                MagicLink.expires_at > datetime.utcnow()
            ).first()
            
            if magic_link:
                # Mark the token as used
                magic_link.mark_used()
                session.commit()
                return magic_link
            
            return None
    
    @classmethod
    def create_access_token(
        cls,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: The data to encode in the token
            expires_delta: Optional timedelta for token expiration
            
        Returns:
            str: The encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
            
        to_encode.update({"exp": expire})
        
        # Get secret key from environment or use a default (not for production)
        secret_key = os.getenv("SECRET_KEY", "default-insecure-secret-key")
        
        return jwt.encode(
            to_encode,
            secret_key,
            algorithm="HS256"
        )
    
    @classmethod
    def verify_access_token(
        cls,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT access token.
        
        Args:
            token: The JWT token to verify
            
        Returns:
            Optional[Dict]: The decoded token data if valid, None otherwise
        """
        try:
            secret_key = os.getenv("SECRET_KEY", "default-insecure-secret-key")
            
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=["HS256"]
            )
            
            return payload
            
        except JWTError:
            return None

# Create a singleton instance
auth_service = AuthService()
