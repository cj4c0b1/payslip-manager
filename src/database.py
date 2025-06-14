import os
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional, Any, List, Dict
from pathlib import Path
import logging
from dotenv import load_dotenv
from decimal import Decimal

from sqlalchemy import create_engine, event, DDL
from sqlalchemy.orm import sessionmaker, scoped_session, Session, sessionmaker
from sqlalchemy.engine import Engine

# Import Base from models to ensure all models use the same metadata
from src.models import Base  # noqa: F401

# Import models to ensure they are registered with SQLAlchemy
# These imports are now done in models/__init__.py to avoid circular imports

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

def create_db_engine(url: str = None) -> Engine:
    """Create and configure the SQLAlchemy engine.
    
    Args:
        url: Optional database URL. If not provided, uses DATABASE_URL from environment.
    """
    from sqlalchemy.pool import StaticPool, QueuePool
    
    db_url = url or DATABASE_URL
    is_sqlite = db_url.startswith('sqlite')
    
    # Configure engine options
    engine_args = {
        'echo': bool(os.getenv('SQL_ECHO', False)),
        'json_serializer': lambda obj: str(obj) if isinstance(obj, Decimal) else None,
    }
    
    # SQLite specific configuration
    if is_sqlite:
        engine_args.update({
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,  # Use StaticPool for SQLite in-memory
            'pool_pre_ping': False,   # Not needed for SQLite
        })
    else:
        # Connection pooling for other databases
        engine_args.update({
            'poolclass': QueuePool,
            'pool_pre_ping': True,
            'pool_recycle': 300,  # Recycle connections after 5 minutes
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
        })
    
    # Create the engine
    engine = create_engine(db_url, **engine_args)
    
    # Configure SQLite specific settings
    if is_sqlite:
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

# For backward compatibility, export SessionLocal as an alias for Session
SessionLocal = Session

# Make Session available for direct import
from sqlalchemy.orm import Session as _SessionBase
Session: _SessionBase = Session  # type: ignore

# Base class for all models with timestamp fields
class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
@event.listens_for(Base, 'before_insert')
def set_created_at(mapper, connection, target):
    """Set created_at and updated_at timestamps on insert."""
    if hasattr(target, 'created_at') and hasattr(target, 'updated_at'):
        now = datetime.utcnow()
        target.created_at = now
        target.updated_at = now

@event.listens_for(Base, 'before_update')
def set_updated_at(mapper, connection, target):
    """Set updated_at timestamp on update."""
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()

def get_base():
    """Return the SQLAlchemy declarative base.
    
    This function is maintained for backward compatibility.
    It now returns the Base from src.models to ensure all models are properly registered.
    """
    return Base

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

# Only initialize the database if this module is run directly
if __name__ == "__main__":
    init_db()
