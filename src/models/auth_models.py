"""
Authentication-related database models.
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Import Base from the local base module to ensure consistent metadata
from .base import Base

class MagicLink(Base):
    """
    Represents a magic link for passwordless authentication.
    """
    __tablename__ = 'magic_links'
    
    # Token expiration time (15 minutes)
    TOKEN_EXPIRATION_MINUTES = 15
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    token = Column(
        String(255), 
        unique=True, 
        index=True,
        nullable=False,
        comment='Hashed token for authentication'
    )
    email = Column(
        String(255), 
        index=True,
        nullable=False,
        comment='Email address this link was sent to'
    )
    user_agent = Column(
        String(512),
        nullable=True,
        comment='User agent of the browser that requested the link'
    )
    ip_address = Column(
        String(45),
        nullable=True,
        comment='IP address that requested the link'
    )
    is_used = Column(
        Boolean,
        default=False,
        nullable=False,
        comment='Whether this link has been used'
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When the link was created'
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When the link expires'
    )
    used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='When the link was used (if used)'
    )
    
    # Relationships
    user = relationship("Employee", back_populates="magic_links")
    user_id = Column(
        Integer,
        ForeignKey('employees.id', ondelete='CASCADE'),
        nullable=True,
        comment='Reference to the user (if they exist)'
    )
    
    __table_args__ = (
        # Index for looking up valid, unused tokens
        Index('idx_magic_link_token_valid', 'token', 'is_used', 'expires_at'),
        # Index for cleaning up expired tokens
        Index('idx_magic_link_expiry', 'expires_at'),
    )
    
    def __init__(self, **kwargs):
        """
        Initialize a new MagicLink with default expiration.
        
        Args:
            **kwargs: Additional arguments to pass to the base class
        """
        # Set created_at if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow()
        
        # Set expires_at if not provided
        if 'expires_at' not in kwargs and 'created_at' in kwargs:
            kwargs['expires_at'] = kwargs['created_at'] + timedelta(minutes=self.TOKEN_EXPIRATION_MINUTES)
        
        # Initialize the SQLAlchemy model
        super().__init__(**kwargs)
    
    @property
    def is_expired(self) -> bool:
        """Check if the magic link has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the magic link is still valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
    
    def mark_used(self):
        """Mark this magic link as used."""
        self.is_used = True
        self.used_at = datetime.utcnow()
        return self
