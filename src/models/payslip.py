"""
Payslip model for the application.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, TYPE_CHECKING

from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, ForeignKey, 
    Date, Text, Boolean, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

# Import Base from models to ensure we're using the same metadata
from .base import Base, TimestampMixin

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from .employee import Employee
    from .earning import Earning
    from .deduction import Deduction

class Payslip(Base):
    """Payslip information model."""
    __tablename__ = 'payslips'
    __table_args__ = (
        # Ensure each employee has only one payslip per month
        UniqueConstraint('employee_id', 'reference_month', 
                       name='uq_employee_month'),
        # Add index for common query patterns
        Index('idx_payslip_status_date', 'status', 'reference_month'),
        Index('idx_payslip_employee_date', 'employee_id', 'reference_month'),
        # Add check constraints
        CheckConstraint(
            "status IN ('draft', 'approved', 'paid', 'cancelled')",
            name='valid_payslip_status'
        ),
        CheckConstraint(
            "gross_salary >= 0",
            name='non_negative_gross_salary'
        ),
        CheckConstraint(
            "net_salary >= 0",
            name='non_negative_net_salary'
        ),
        CheckConstraint(
            "total_earnings >= 0",
            name='non_negative_earnings'
        ),
        CheckConstraint(
            "total_deductions >= 0",
            name='non_negative_deductions'
        ),
        {'extend_existing': True}  # Allow table redefinition
    )
    
    # Status constants
    STATUS_DRAFT = 'draft'
    STATUS_APPROVED = 'approved'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'
    
    # Payment method constants
    PAYMENT_BANK_TRANSFER = 'bank_transfer'
    PAYMENT_CHECK = 'check'
    PAYMENT_CASH = 'cash'
    PAYMENT_OTHER = 'other'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    employee_id = Column(
        Integer, 
        ForeignKey('employees.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True, 
        comment='Reference to employee'
    )
    reference_month = Column(
        Date, 
        nullable=False, 
        index=True, 
        comment='The month this payslip is for (YYYY-MM-01)'
    )
    issue_date = Column(
        Date, 
        index=True, 
        comment='Date when the payslip was issued'
    )
    payment_date = Column(
        Date, 
        index=True, 
        comment='Date when payment was made'
    )
    bank_account = Column(
        String(50), 
        comment='Bank account number',
        index=True
    )
    payment_method = Column(
        String(20), 
        default=PAYMENT_BANK_TRANSFER,
        nullable=False,
        comment='Payment method (bank_transfer, check, cash, other)'
    )
    currency = Column(
        String(3), 
        default='USD', 
        nullable=False,
        comment='Currency code (ISO 4217)'
    )
    gross_salary = Column(
        Numeric(12, 2), 
        default=0.0, 
        nullable=False, 
        comment='Gross salary amount'
    )
    net_salary = Column(
        Numeric(12, 2), 
        default=0.0, 
        nullable=False, 
        comment='Net salary amount'
    )
    total_earnings = Column(
        Numeric(12, 2), 
        default=0.0, 
        nullable=False, 
        comment='Sum of all earnings'
    )
    total_deductions = Column(
        Numeric(12, 2), 
        default=0.0, 
        nullable=False, 
        comment='Sum of all deductions'
    )
    tax_deductions = Column(
        Numeric(12, 2), 
        default=0.0,
        comment='Total tax deductions'
    )
    other_deductions = Column(
        Numeric(12, 2), 
        default=0.0,
        comment='Total other deductions (non-tax)'
    )
    notes = Column(
        Text, 
        comment='Additional notes or comments'
    )
    status = Column(
        String(20), 
        default=STATUS_DRAFT, 
        nullable=False,
        index=True,
        comment='Status: draft, approved, paid, cancelled'
    )
    original_filename = Column(
        String(255), 
        comment='Original PDF filename',
        index=True
    )
    file_hash = Column(
        String(64), 
        unique=True, 
        index=True,
        comment='SHA-256 hash of the original file for deduplication'
    )
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        comment='Timestamp when the record was created'
    )
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False,
        comment='Timestamp when the record was last updated'
    )
    
    # Relationships
    employee: Mapped['Employee'] = relationship(
        'Employee', 
        back_populates='payslips',
        lazy='joined'
    )
    
    earnings: Mapped[List['Earning']] = relationship(
        'Earning',
        back_populates='payslip',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='dynamic'
    )
    
    deductions: Mapped[List['Deduction']] = relationship(
        'Deduction',
        back_populates='payslip',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f"<Payslip(id={self.id}, employee_id={self.employee_id}, reference_month={self.reference_month})>"
    
    @property
    def reference_month_str(self):
        """Get reference month as string (YYYY-MM)."""
        return self.reference_month.strftime('%Y-%m') if self.reference_month else ''
    
    @classmethod
    def get_by_employee_and_month(
        cls, 
        session, 
        employee_id: int, 
        year: int, 
        month: int
    ):
        """Get a payslip by employee ID and reference month."""
        from datetime import date
        ref_date = date(year, month, 1)
        return session.query(cls).filter(
            cls.employee_id == employee_id,
            func.strftime('%Y-%m', cls.reference_month) == ref_date.strftime('%Y-%m')
        ).first()
    
    def calculate_totals(self):
        """Recalculate all totals based on earnings and deductions."""
        # Sum all earnings
        self.total_earnings = sum(earning.amount for earning in self.earnings)
        
        # Sum all deductions, separating tax and non-tax
        tax_deductions = 0.0
        other_deductions = 0.0
        
        for deduction in self.deductions:
            if deduction.is_tax:
                tax_deductions += deduction.amount
            else:
                other_deductions += deduction.amount
                
        self.tax_deductions = tax_deductions
        self.other_deductions = other_deductions
        self.total_deductions = tax_deductions + other_deductions
        
        # Calculate net salary
        self.net_salary = self.gross_salary - self.total_deductions
        
        return self
    
    def update_status(self, new_status: str, commit: bool = False):
        """Update the status of the payslip with validation."""
        valid_statuses = [
            self.STATUS_DRAFT, 
            self.STATUS_APPROVED, 
            self.STATUS_PAID, 
            self.STATUS_CANCELLED
        ]
        
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
            
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if commit and hasattr(self, 'session'):
            self.session.commit()
    
    # Relationships
    employee = relationship("Employee", back_populates="payslips")
    
    def __repr__(self):
        return f"<Payslip(id={self.id}, employee_id={self.employee_id}, payment_date={self.payment_date})>"
    
    @property
    def formatted_pay_period(self) -> str:
        """Return the pay period as a formatted string."""
        return f"{self.pay_period_start.strftime('%b %d, %Y')} - {self.pay_period_end.strftime('%b %d, %Y')}"
    
    @property
    def formatted_payment_date(self) -> str:
        """Return the payment date as a formatted string."""
        return self.payment_date.strftime('%b %d, %Y')
    
    def to_dict(self) -> dict:
        """Convert the payslip to a dictionary."""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.full_name if self.employee else 'Unknown',
            'pay_period': self.formatted_pay_period,
            'pay_period_start': self.pay_period_start.isoformat(),
            'pay_period_end': self.pay_period_end.isoformat(),
            'payment_date': self.payment_date.isoformat(),
            'formatted_payment_date': self.formatted_payment_date,
            'gross_pay': float(self.gross_pay) if self.gross_pay is not None else 0.0,
            'tax_amount': float(self.tax_amount) if self.tax_amount is not None else 0.0,
            'net_pay': float(self.net_pay) if self.net_pay is not None else 0.0,
            'currency': self.currency,
            'status': self.status,
            'notes': self.notes or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
