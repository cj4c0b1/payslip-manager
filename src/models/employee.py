"""
Employee model for the application.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, event
from sqlalchemy.orm import relationship, Mapped, mapped_column

# Import Base from models to ensure we're using the same metadata
from .base import Base, TimestampMixin

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from .payslip import Payslip

class Employee(Base):
    """Employee model representing a user of the system."""
    __tablename__ = 'employees'
    __table_args__ = {'extend_existing': True}  # Allow table redefinition
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    cpf = Column(String(14), unique=True, index=True, nullable=True, comment='Brazilian CPF (Cadastro de Pessoas Físicas)')
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime, nullable=True)
    password_reset_token = Column(String(100), nullable=True)
    password_reset_token_expires = Column(DateTime, nullable=True)
    
    # Relationships with string-based class names to avoid circular imports
    payslips: Mapped[List['Payslip']] = relationship(
        'Payslip', 
        back_populates='employee',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f"<Employee(id={self.id}, email={self.email})>"
    
    @property
    def full_name(self) -> str:
        """Return the full name of the employee."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    def is_account_locked(self) -> bool:
        """Check if the account is currently locked."""
        if not self.account_locked_until:
            return False
        return self.account_locked_until > datetime.utcnow()
    
    def record_successful_login(self):
        """Record a successful login."""
        self.last_login_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.account_locked_until = None
    
    def record_failed_login(self):
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            self.account_locked_until = datetime.utcnow() + datetime.timedelta(minutes=30)
