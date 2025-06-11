import os
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, ForeignKey, 
    DateTime, func, event, DDL, Numeric, Boolean, Text, CheckConstraint, 
    UniqueConstraint, Index, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session, Session
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Generator, Optional, Any, List, Dict
import logging
from dotenv import load_dotenv
from decimal import Decimal
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Type aliases
SessionType = scoped_session[sessionmaker]  # type: ignore

# Load environment variables
load_dotenv()

# Database URL from environment variable or default to SQLite
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/payslips.db')

# Ensure the data directory exists for SQLite
db_dir = None
if DATABASE_URL.startswith('sqlite'):
    db_path = Path(DATABASE_URL.split('///')[-1])
    db_dir = db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_path}"
    logger.info(f"Using SQLite database at: {db_path}")

# SQLAlchemy engine configuration
def get_engine_config() -> Dict[str, Any]:
    """Get database engine configuration from environment variables."""
    return {
        'echo': os.getenv('SQL_ECHO', 'false').lower() == 'true',
        'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
        'pool_pre_ping': os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true',
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
    }

# Create database engine
def create_db_engine() -> Engine:
    """Create and configure the SQLAlchemy engine."""
    engine_config = get_engine_config()
    
    # Handle SQLite specific configuration
    connect_args = {}
    if DATABASE_URL.startswith('sqlite'):
        connect_args['check_same_thread'] = False  # Required for SQLite with multiple threads
    
    engine = create_engine(
        DATABASE_URL,
        **engine_config,
        connect_args=connect_args,
        json_serializer=lambda obj: str(obj) if isinstance(obj, Decimal) else None,
    )
    
    # Configure SQLite specific settings
    if DATABASE_URL.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Enable SQLite WAL mode and other optimizations."""
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA temp_store=MEMORY')
            cursor.execute('PRAGMA cache_size=-2000')  # 2MB cache
            cursor.close()
    
    return engine

# Create engine
engine = create_db_engine()

def create_session_factory(engine: Engine) -> sessionmaker:
    """Create a session factory for the given engine."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

# Create scoped session factory
SessionFactory = create_session_factory(engine)
Session: SessionType = scoped_session(SessionFactory)

# Make Session available for direct import
from sqlalchemy.orm import Session as _SessionBase
Session: _SessionBase = Session  # type: ignore

# Base class for all models with timestamp fields
class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False,
                       comment='Timestamp when the record was created')
    updated_at = Column(DateTime, default=datetime.utcnow, 
                       onupdate=datetime.utcnow, nullable=False,
                       comment='Timestamp when the record was last updated')

# Create declarative base with our mixin
Base = declarative_base()

# Set up event listeners for timestamps
@event.listens_for(Base, 'before_insert')
def set_created_at(mapper, connection, target):
    """Set created_at and updated_at timestamps on insert."""
    if hasattr(target, 'created_at'):
        target.created_at = datetime.utcnow()
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()

@event.listens_for(Base, 'before_update')
def set_updated_at(mapper, connection, target):
    """Set updated_at timestamp on update."""
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()

class Employee(Base, TimestampMixin):
    """Employee information model."""
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    employee_id = Column(
        String(50), 
        unique=True, 
        index=True, 
        nullable=False, 
        comment='Employee ID from the company system'
    )
    name = Column(
        String(100), 
        nullable=False, 
        comment='Full name of the employee',
        index=True
    )
    email = Column(
        String(100), 
        unique=True, 
        index=True, 
        comment='Employee email address',
        nullable=False
    )
    _password_hash = Column(
        String(255),
        name='password_hash',
        comment='Hashed password for authentication',
        nullable=True
    )
    department = Column(
        String(100), 
        comment='Department name',
        index=True
    )
    position = Column(
        String(100), 
        comment='Job position/title',
        index=True
    )
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment='Whether the employee is currently active',
        index=True
    )
    is_admin = Column(
        Boolean,
        default=False,
        nullable=False,
        comment='Whether the user has admin privileges',
        index=True
    )
    last_login_at = Column(
        DateTime,
        nullable=True,
        comment='Timestamp of last successful login'
    )
    failed_login_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Number of consecutive failed login attempts'
    )
    account_locked_until = Column(
        DateTime,
        nullable=True,
        comment='Timestamp until which the account is locked due to too many failed attempts'
    )
    is_email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment='Whether the user has verified their email address',
        index=True
    )
    email_verified_at = Column(
        DateTime,
        nullable=True,
        comment='When the email was verified'
    )
    
    # Relationships
    payslips = relationship(
        'Payslip',
        back_populates='employee',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    magic_links = relationship(
        'MagicLink',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    
    __table_args__ = (
        # Add a check constraint for email format
        CheckConstraint(
            "email LIKE '%_@__%.__%'",
            name='valid_email_format'
        ),
        # Add a composite index for common query patterns
        Index('idx_employee_dept_active', 'department', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}', email='{self.email}')>"
        
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set the password with hashing."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        if not self._password_hash:
            return False
            
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self._password_hash)
    
    def is_account_locked(self) -> bool:
        """Check if the account is currently locked."""
        if not self.account_locked_until:
            return False
        from datetime import datetime
        return datetime.utcnow() < self.account_locked_until
    
    def record_failed_login_attempt(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        """Record a failed login attempt and lock the account if needed."""
        from datetime import datetime, timedelta
        
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
    
    def record_successful_login(self) -> None:
        """Record a successful login."""
        from datetime import datetime
        
        self.last_login_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.account_locked_until = None
    
    @classmethod
    def get_by_employee_id(cls, session: Session, employee_id: str) -> Optional['Employee']:
        """Get an employee by their employee ID"""
        return session.query(cls).filter(cls.employee_id == employee_id).first()
    
    @classmethod
    def search(cls, session: Session, query: str, limit: int = 10) -> list['Employee']:
        """Search employees by name or employee ID"""
        search = f"%{query}%"
        return session.query(cls).filter(
            (cls.name.ilike(search)) | (cls.employee_id.ilike(search))
        ).limit(limit).all()
    
    def get_latest_payslip(self) -> Optional['Payslip']:
        """Get the most recent payslip for this employee"""
        return self.payslips.order_by(Payslip.reference_month.desc()).first()

class Payslip(Base, TimestampMixin):
    """Payslip information model."""
    __tablename__ = 'payslips'
    
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
    
    # Relationships
    employee = relationship(
        'Employee', 
        back_populates='payslips',
        lazy='joined'
    )
    earnings = relationship(
        'Earning',
        back_populates='payslip',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='dynamic'
    )
    deductions = relationship(
        'Deduction',
        back_populates='payslip',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='dynamic'
    )
    
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
    )
    
    def __repr__(self) -> str:
        return (
            f'<Payslip(id={self.id}, employee_id={self.employee_id}, '
            f'reference_month={self.reference_month.strftime("%Y-%m") if self.reference_month else None}, '
            f'status=\'{self.status}\')>'
        )
    
    @property
    def reference_month_str(self) -> str:
        """Get reference month as string (YYYY-MM)."""
        return self.reference_month.strftime('%Y-%m') if self.reference_month else ''
    
    @classmethod
    def get_by_employee_and_month(
        cls, 
        session: Session, 
        employee_id: int, 
        year: int, 
        month: int
    ) -> Optional['Payslip']:
        """Get a payslip by employee ID and reference month."""
        from sqlalchemy import and_, extract
        
        return session.query(cls).filter(
            and_(
                cls.employee_id == employee_id,
                extract('year', cls.reference_month) == year,
                extract('month', cls.reference_month) == month
            )
        ).first()
    
    def calculate_totals(self) -> None:
        """Recalculate all totals based on earnings and deductions."""
        from decimal import Decimal
        
        # Calculate totals from related records
        self.total_earnings = float(sum(
            Decimal(str(earning.amount)) 
            for earning in self.earnings
        ))
        
        self.total_deductions = float(sum(
            Decimal(str(deduction.amount)) 
            for deduction in self.deductions
        ))
        
        # Update tax and other deductions
        self.tax_deductions = float(sum(
            Decimal(str(deduction.amount))
            for deduction in self.deductions
            if deduction.is_tax
        ))
        
        self.other_deductions = self.total_deductions - self.tax_deductions
        
        # Ensure net salary is non-negative
        self.net_salary = max(0, self.gross_salary - self.total_deductions)
    
    def update_status(self, new_status: str, commit: bool = False) -> bool:
        """Update the status of the payslip with validation."""
        valid_statuses = [
            self.STATUS_DRAFT,
            self.STATUS_APPROVED,
            self.STATUS_PAID,
            self.STATUS_CANCELLED
        ]
        
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")
            
        self.status = new_status
        
        if commit and Session:
            try:
                session = Session()
                session.add(self)
                session.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to update payslip status: {e}")
                if 'session' in locals():
                    session.rollback()
                return False
        
        return True

class Earning(Base, TimestampMixin):
    """Earning line item for a payslip."""
    __tablename__ = 'earnings'
    
    # Common earning categories
    CATEGORY_SALARY = 'salary'
    CATEGORY_BONUS = 'bonus'
    CATEGORY_OVERTIME = 'overtime'
    CATEGORY_COMMISSION = 'commission'
    CATEGORY_ALLOWANCE = 'allowance'
    CATEGORY_REIMBURSEMENT = 'reimbursement'
    CATEGORY_OTHER = 'other'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    payslip_id = Column(
        Integer, 
        ForeignKey('payslips.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True, 
        comment='Reference to payslip'
    )
    category = Column(
        String(50), 
        nullable=False, 
        index=True,
        comment='Earning category (salary, bonus, overtime, etc.)'
    )
    description = Column(
        String(255), 
        nullable=False, 
        comment='Earning description'
    )
    reference = Column(
        String(100), 
        comment='Reference code or identifier',
        index=True
    )
    amount = Column(
        Numeric(12, 2), 
        nullable=False, 
        comment='Earning amount'
    )
    is_taxable = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment='Whether this earning is taxable'
    )
    quantity = Column(
        Numeric(10, 2),
        default=1.0,
        comment='Quantity for calculation (e.g., hours for overtime)'
    )
    rate = Column(
        Numeric(12, 4),
        comment='Rate per unit (e.g., hourly rate)'
    )
    
    # Relationships
    payslip = relationship(
        'Payslip', 
        back_populates='earnings',
        lazy='selectin'  # Eager load by default
    )
    
    __table_args__ = (
        # Add check constraints
        CheckConstraint(
            "amount >= 0",
            name='non_negative_earning_amount'
        ),
        CheckConstraint(
            "quantity >= 0",
            name='non_negative_quantity'
        ),
        # Add index for common query patterns
        Index('idx_earning_category', 'category'),
        Index('idx_earning_reference', 'reference'),
    )
    
    def __repr__(self) -> str:
        return (
            f'<Earning(id={self.id}, description=\'{self.description}\', '
            f'amount={self.amount}, category=\'{self.category}\')>'
        )
    
    @classmethod
    def get_by_category(
        cls, 
        session: Session, 
        category: str,
        limit: int = 100
    ) -> List['Earning']:
        """Get earnings by category."""
        return (
            session.query(cls)
            .filter(cls.category == category)
            .order_by(cls.amount.desc())
            .limit(limit)
            .all()
        )
    
    def calculate_amount(self) -> Decimal:
        """Calculate amount based on quantity and rate if applicable."""
        if self.rate is not None:
            return Decimal(str(self.quantity)) * Decimal(str(self.rate))
        return Decimal(str(self.amount)) if self.amount is not None else Decimal('0')

class Deduction(Base, TimestampMixin):
    """Deduction line item for a payslip."""
    __tablename__ = 'deductions'
    
    # Common deduction categories
    CATEGORY_TAX = 'tax'
    CATEGORY_INSURANCE = 'insurance'
    CATEGORY_RETIREMENT = 'retirement'
    CATEGORY_LOAN = 'loan'
    CATEGORY_ADVANCE = 'advance'
    CATEGORY_OTHER = 'other'
    
    id = Column(Integer, primary_key=True, index=True, comment='Primary key')
    payslip_id = Column(
        Integer, 
        ForeignKey('payslips.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True, 
        comment='Reference to payslip'
    )
    category = Column(
        String(50), 
        nullable=False, 
        index=True,
        comment='Deduction category (tax, insurance, loan, etc.)'
    )
    description = Column(
        String(255), 
        nullable=False, 
        comment='Deduction description'
    )
    reference = Column(
        String(100), 
        comment='Reference code or identifier',
        index=True
    )
    amount = Column(
        Numeric(12, 2), 
        nullable=False, 
        comment='Deduction amount'
    )
    is_tax = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment='Whether this is a tax-related deduction'
    )
    is_pretax = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment='Whether this is a pre-tax deduction'
    )
    tax_year = Column(
        Integer,
        comment='Tax year this deduction applies to',
        index=True
    )
    
    # Relationships
    payslip = relationship(
        'Payslip', 
        back_populates='deductions',
        lazy='selectin'  # Eager load by default
    )
    
    __table_args__ = (
        # Add check constraints
        CheckConstraint(
            "amount >= 0",
            name='non_negative_deduction_amount'
        ),
        # Add index for common query patterns
        Index('idx_deduction_category', 'category'),
        Index('idx_deduction_reference', 'reference'),
        Index('idx_deduction_tax_year', 'tax_year'),
    )
    
    def __repr__(self) -> str:
        return (
            f'<Deduction(id={self.id}, description=\'{self.description}\', '
            f'amount={self.amount}, category=\'{self.category}\')>'
        )
    
    @classmethod
    def get_tax_deductions(
        cls, 
        session: Session, 
        employee_id: int,
        tax_year: int
    ) -> List['Deduction']:
        """Get all tax deductions for an employee in a specific tax year."""
        return (
            session.query(cls)
            .join(Payslip)
            .filter(
                Payslip.employee_id == employee_id,
                cls.tax_year == tax_year,
                cls.is_tax == True  # noqa: E712
            )
            .all()
        )
    
    @property
    def is_post_tax(self) -> bool:
        """Check if this is a post-tax deduction."""
        return not (self.is_tax or self.is_pretax)
    
    @classmethod
    def get_by_payslip_id(cls, session: Session, payslip_id: int) -> list['Deduction']:
        """Helper method to get all deductions for a specific payslip"""
        return session.query(cls).filter(cls.payslip_id == payslip_id).all()

@contextmanager
def get_db_session(commit: bool = True) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic transaction handling.
    
    Args:
        commit: If True, commit the transaction on success, otherwise rollback.
               Useful for read-only operations or when you want to manage
               transactions manually.
    
    Yields:
        Session: A database session
        
    Example:
        # For read operations
        with get_db_session(commit=False) as session:
            employees = session.query(Employee).all()
            
        # For write operations (default)
        with get_db_session() as session:
            employee = Employee(name='John Doe', email='john@example.com')
            session.add(employee)
    """
    session = Session()
    try:
        yield session
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error("Database error: %s", str(e), exc_info=True)
        raise
    finally:
        session.close()
        Session.remove()  # Important for scoped sessions

def with_db_session(func):
    """
    Decorator to provide a database session to a function.
    
    The decorated function should accept a 'db' parameter which will be
    a database session. The session will be automatically committed if
    the function returns without raising an exception.
    
    Example:
        @with_db_session
        def get_employee(employee_id: int, db: Session) -> Optional[Employee]:
            return db.query(Employee).filter(Employee.id == employee_id).first()
            
        # Call the function without providing the session
        employee = get_employee(1)
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_session(commit=True) as session:
            return func(*args, **kwargs, db=session)
    
    return wrapper

def get_db() -> Generator[Session, None, None]:
    """Generator function for FastAPI dependency injection.
    
    Yields:
        Session: A database session
    """
    with get_db_session() as session:
        yield session

def init_db(drop_existing: bool = False) -> None:
    """
    Initialize the database by creating all tables.
    
    Args:
        drop_existing: If True, drop all tables before creating them.
                     Use with caution as this will delete all data.
    """
    global db_dir  # Make sure we can modify the global db_dir
    
    try:
        if drop_existing:
            Base.metadata.drop_all(bind=engine)
            logger.warning("Dropped all existing tables")
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Apply any pending migrations if using migrations
        try:
            from alembic.config import Config
            from alembic import command
            
            # Create migrations directory if it doesn't exist
            migrations_dir = Path("migrations")
            if not migrations_dir.exists():
                migrations_dir.mkdir(exist_ok=True)
                logger.info(f"Created migrations directory at: {migrations_dir.absolute()}")
            
            # Initialize Alembic if not already initialized
            if not (migrations_dir / "env.py").exists():
                logger.info("Initializing Alembic migrations...")
                command.init("migrations")
            
            # Run migrations
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("Applied database migrations")
        except ImportError:
            logger.debug("Alembic not installed, skipping migrations")
        except Exception as e:
            logger.warning("Failed to apply migrations: %s", str(e))
        
        # Log database location
        if db_dir:
            logger.info(f"Database directory: {db_dir.absolute()}")
        logger.info(f"Database URL: {DATABASE_URL}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def reset_db(confirm: bool = False) -> None:
    """
    Drop all tables and recreate them.
    
    Args:
        confirm: Must be set to True to actually perform the reset.
                This is a safety measure to prevent accidental data loss.
    """
    if not confirm:
        logger.warning("reset_db() called without confirm=True. No changes were made.")
        return
        
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
    
    # Recreate all tables
    init_db()
    logger.info("Database reset complete")

def get_session() -> Session:
    """Get a new database session.
    
    Returns:
        Session: A new database session
        
    Note:
        Remember to close the session when done using session.close()
        or use the session as a context manager:
        
        with get_session() as session:
            # use session here
            pass
    """
    return SessionFactory()

# Create database tables if they don't exist
init_db()
