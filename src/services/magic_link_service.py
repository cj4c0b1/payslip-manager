"""
Service for handling magic link authentication.
"""
import secrets
import string
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from src.models.auth_models import MagicLink
from src.config import settings

def generate_token(length: int = 64) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token in characters
        
    Returns:
        str: A secure random token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.
    
    Args:
        token: The token to hash
        
    Returns:
        str: The hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()

class MagicLinkService:
    """
    Service for handling magic link authentication.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the MagicLinkService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_magic_link(
        self,
        email: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        expiration_minutes: int = 15
    ) -> Tuple[str, MagicLink]:
        """
        Create a new magic link for the given email.
        
        Args:
            email: The email address to send the magic link to
            user_agent: The user agent of the requester
            ip_address: The IP address of the requester
            user_id: Optional user ID if the user already exists
            expiration_minutes: Minutes until the link expires (default: 15)
            
        Returns:
            tuple: (plaintext_token, magic_link_object)
        """
        # Generate a secure token
        token = generate_token()
        token_hash = hash_token(token)
        
        # Get the current time (will be mocked by freezegun)
        now = datetime.utcnow()
        
        # Create and save the magic link with explicit timestamps
        magic_link = MagicLink(
            email=email,
            token=token_hash,
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now,
            expires_at=now + timedelta(minutes=expiration_minutes),
            is_used=False
        )
        
        self.db.add(magic_link)
        self.db.commit()
        self.db.refresh(magic_link)
        
        return token, magic_link
    
    def validate_magic_link(
        self,
        token: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[MagicLink]:
        """
        Validate a magic link token and return the associated magic link if valid.
        
        Note: This method only validates the token, it does not mark it as used.
        Use mark_used() explicitly after successful validation.
        
        Args:
            token: The token to validate
            ip_address: The IP address that made the request
            user_agent: The user agent that made the request
            
        Returns:
            Optional[MagicLink]: The validated magic link if valid, None otherwise
        """
        if not token or not ip_address or not user_agent:
            return None
            
        # Calculate the token hash for lookup
        token_hash = hash_token(token)
        
        # Get current time (will be mocked by freezegun in tests)
        now = datetime.utcnow()
        
        # Find the magic link
        magic_link = self.db.query(MagicLink).filter(
            MagicLink.token == token_hash,
            MagicLink.ip_address == ip_address,
            MagicLink.user_agent == user_agent,
            MagicLink.is_used == False,
            MagicLink.expires_at > now
        ).first()

        return magic_link
        
    def mark_used(self, magic_link: MagicLink) -> None:
        """
        Mark a magic link as used.
        
        Args:
            magic_link: The magic link to mark as used
            
        Returns:
            None
        """
        try:
            magic_link.is_used = True
            magic_link.used_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(magic_link)
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error updating magic link status: {str(e)}")
            return None
    
    def is_valid_magic_link(self, token: str, ip_address: str, user_agent: str) -> bool:
        """
        Check if a magic link is valid without consuming it.
        
        Args:
            token: The token to validate
            ip_address: The IP address that made the request
            user_agent: The user agent that made the request
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        if not token or not ip_address or not user_agent:
            return False
            
        token_hash = hash_token(token)
        magic_link = self.db.query(MagicLink).filter(
            MagicLink.token == token_hash,
            MagicLink.ip_address == ip_address,
            MagicLink.user_agent == user_agent,
            MagicLink.is_used == False,
            MagicLink.expires_at > self._datetime.utcnow()
        ).first()
        
        return magic_link is not None
