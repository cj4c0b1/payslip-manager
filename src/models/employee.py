"""
Employee model for the application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

# Import Base from the local base module to avoid circular imports
from .base import Base

class Employee(Base):
    """
    Employee model representing a user of the application.
    """
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # For future password-based auth
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    payslips = relationship("Payslip", back_populates="employee")
    magic_links = relationship("MagicLink", back_populates="user")
    
    def __repr__(self):
        return f"<Employee(id={self.id}, email={self.email}, is_active={self.is_active})>"
    
    def to_dict(self):
        """Convert the employee to a dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
