"""Authentication models for the renato application."""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, ForeignKey, Index,
    event, DDL, func, text
)
from sqlalchemy.orm import relationship, Session

from ..database import Base, get_db_session


class MagicToken(Base):
    """
    Model for storing magic link authentication tokens.
    
    Tokens are single-use and expire after a configurable time period.
    """
    __tablename__ = 'magic_tokens'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    email = Column(
        String(100), 
        nullable=False, 
        index=True, 
        comment='Email address the token was sent to'
    )
    token_hash = Column(
        String(64),  # SHA-256 hash is 64 chars
        nullable=False,
        index=True,
        comment='Hashed token value for security'
    )
    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
        comment='When this token expires (UTC)'
    )
    used = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment='Whether this token has been used'
    )
    used_at = Column(
        DateTime,
        nullable=True,
        comment='When this token was used (UTC)'
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment='When this token was created (UTC)'
    )
    user_agent = Column(
        String(255),
        nullable=True,
        comment='User agent from the login request'
    )
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        comment='IP address from the login request'
    )
    
    # Relationship to user (if needed)
    # user = relationship("Employee", back_populates="magic_tokens")
    
    __table_args__ = (
        # Index for faster lookups of valid tokens
        Index('idx_magic_token_valid', 'email', 'token_hash', 'expires_at', 'used'),
        # Add a partial index for faster cleanup of expired tokens
        Index('idx_magic_token_expired', 'expires_at', postgresql_where=text("expires_at < now()")),
    )
    
    def __repr__(self) -> str:
        return f"<MagicToken(email='{self.email}', expires='{self.expires_at}')>"
    
    @classmethod
    def create_token(
        cls,
        email: str,
        expires_in_minutes: int = 15,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> tuple['MagicToken', str]:
        """
        Create a new magic token for the given email.
        
        Args:
            email: The email address to send the token to
            expires_in_minutes: How many minutes until the token expires
            user_agent: The user agent from the login request
            ip_address: The IP address from the login request
            db_session: Optional database session to use
            
        Returns:
            tuple: (MagicToken instance, plaintext_token)
        """
        # Generate a secure random token
        plaintext_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plaintext_token.encode()).hexdigest()
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        # Create the token instance
        token = cls(
            email=email.lower().strip(),
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Save to database
        if db_session is None:
            db_session = next(get_db_session())
            
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        
        return token, plaintext_token
    
    @classmethod
    def validate_token(
        cls,
        email: str,
        token: str,
        db_session: Optional[Session] = None
    ) -> tuple[bool, Optional['MagicToken']]:
        """
        Validate a magic token.
        
        Args:
            email: The email address the token was sent to
            token: The plaintext token to validate
            db_session: Optional database session to use
            
        Returns:
            tuple: (is_valid, token_instance)
        """
        if not email or not token:
            return False, None
            
        # Hash the provided token for comparison
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Get a database session if none provided
        if db_session is None:
            db_session = next(get_db_session())
        
        try:
            # Find a matching, unused, unexpired token
            token_instance = db_session.query(cls).filter(
                cls.email == email.lower().strip(),
                cls.token_hash == token_hash,
                cls.used == False,  # noqa
                cls.expires_at > datetime.utcnow()
            ).first()
            
            if not token_instance:
                return False, None
                
            # Mark the token as used and set the used_at timestamp
            token_instance.used = True
            token_instance.used_at = datetime.utcnow()
            db_session.commit()
            
            return True, token_instance
            
        except Exception as e:
            if db_session:
                db_session.rollback()
            raise e

# Add event listener to clean up expired tokens
@event.listens_for(MagicToken, 'after_insert')
def receive_after_insert(mapper, connection, target):
    """Clean up expired tokens after inserting a new one."""
    # This runs in a separate transaction
    # Only clean up tokens that are both used AND expired more than 1 day ago
    # This prevents us from cleaning up tokens that might still be valid
    connection.execute(
        text("""
            DELETE FROM magic_tokens 
            WHERE used = 1 AND expires_at < datetime('now', '-1 day')
        """)
    )
