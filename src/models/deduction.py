"""
Deduction model for tracking individual deductions in a payslip.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, ForeignKey, Date, Text, 
    CheckConstraint, Index, Boolean
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin

class Deduction(Base, TimestampMixin):
    """
    Represents an individual deduction line item in a payslip.
    """
    __tablename__ = 'deductions'
    __table_args__ = (
        # Add index for common query patterns
        Index('idx_deduction_payslip', 'payslip_id'),
        Index('idx_deduction_type', 'deduction_type'),
        # Add check constraints
        CheckConstraint("amount >= 0", name='non_negative_deduction_amount'),
        {'extend_existing': True}  # Allow table redefinition
    )
    
    # Deduction types
    TYPE_TAX = 'tax'
    TYPE_INSURANCE = 'insurance'
    TYPE_RETIREMENT = 'retirement'
    TYPE_LOAN = 'loan'
    TYPE_GARNISHMENT = 'garnishment'
    TYPE_OTHER = 'other'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    payslip_id = Column(
        Integer, 
        ForeignKey('payslips.id', ondelete='CASCADE'), 
        nullable=False,
        index=True,
        comment='Reference to payslip'
    )
    deduction_type = Column(
        String(20), 
        nullable=False,
        comment='Type of deduction (tax, insurance, retirement, etc.)'
    )
    description = Column(
        String(255), 
        comment='Description of the deduction'
    )
    amount = Column(
        Numeric(12, 2), 
        nullable=False,
        comment='Deduction amount'
    )
    is_pretax = Column(
        Boolean,
        default=False,
        comment='Whether this is a pre-tax deduction'
    )
    is_employer_contribution = Column(
        Boolean,
        default=False,
        comment='Whether this is an employer contribution (not deducted from employee pay)'
    )
    notes = Column(
        Text,
        comment='Additional notes about this deduction'
    )
    
    # Relationship to Payslip (using string reference to avoid circular imports)
    payslip = relationship("Payslip", back_populates="deductions")
    
    def __repr__(self):
        return f"<Deduction(id={self.id}, type={self.deduction_type}, amount={self.amount})>"
    
    def to_dict(self):
        """Convert the deduction to a dictionary."""
        return {
            'id': self.id,
            'payslip_id': self.payslip_id,
            'deduction_type': self.deduction_type,
            'description': self.description,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'is_pretax': self.is_pretax,
            'is_employer_contribution': self.is_employer_contribution,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
