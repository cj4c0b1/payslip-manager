"""
Earning model for tracking individual earnings in a payslip.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, ForeignKey, Date, Text, Boolean,
    CheckConstraint, Index
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin

class Earning(Base, TimestampMixin):
    """
    Represents an individual earning line item in a payslip.
    """
    __tablename__ = 'earnings'
    __table_args__ = (
        # Add index for common query patterns
        Index('idx_earning_payslip', 'payslip_id'),
        Index('idx_earning_type', 'earning_type'),
        # Add check constraints
        CheckConstraint("amount >= 0", name='non_negative_earning_amount'),
        {'extend_existing': True}  # Allow table redefinition
    )
    
    # Earning types
    TYPE_REGULAR = 'regular'
    TYPE_OVERTIME = 'overtime'
    TYPE_BONUS = 'bonus'
    TYPE_COMMISSION = 'commission'
    TYPE_ALLOWANCE = 'allowance'
    TYPE_OTHER = 'other'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    payslip_id = Column(
        Integer, 
        ForeignKey('payslips.id', ondelete='CASCADE'), 
        nullable=False,
        index=True,
        comment='Reference to payslip'
    )
    earning_type = Column(
        String(20), 
        nullable=False,
        comment='Type of earning (regular, overtime, bonus, etc.)'
    )
    description = Column(
        String(255), 
        comment='Description of the earning'
    )
    amount = Column(
        Numeric(12, 2), 
        nullable=False,
        comment='Earning amount'
    )
    quantity = Column(
        Numeric(10, 2),
        default=1.0,
        comment='Quantity for calculation (e.g., hours, units)'
    )
    rate = Column(
        Numeric(12, 4),
        comment='Rate per unit (e.g., hourly rate)'
    )
    is_taxable = Column(
        Boolean,
        default=True,
        comment='Whether this earning is subject to tax'
    )
    notes = Column(
        Text,
        comment='Additional notes about this earning'
    )
    
    # Relationship to Payslip (using string reference to avoid circular imports)
    payslip = relationship("Payslip", back_populates="earnings")
    
    def __repr__(self):
        return f"<Earning(id={self.id}, type={self.earning_type}, amount={self.amount})>"
    
    def to_dict(self):
        """Convert the earning to a dictionary."""
        return {
            'id': self.id,
            'payslip_id': self.payslip_id,
            'earning_type': self.earning_type,
            'description': self.description,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'quantity': float(self.quantity) if self.quantity is not None else 1.0,
            'rate': float(self.rate) if self.rate is not None else None,
            'is_taxable': self.is_taxable,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
