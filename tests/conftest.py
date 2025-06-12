"""
Pytest configuration and fixtures for testing the application.
"""
import os
import tempfile
import pytest
from pathlib import Path
import shutil

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SessionType

# Set up test database path
TEST_DB_DIR = os.path.join(tempfile.gettempdir(), 'payslip_tests')
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, 'test_payslips.db')
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = TEST_DATABASE_URL
    
    # Clean up any existing test database
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(scope='session')
def db_engine():
    """Create a test database engine."""
    # Create a new SQLite database for testing
    engine = create_engine(TEST_DATABASE_URL)
    
    # Import models to create tables
    from src.database import Base
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

@pytest.fixture(scope='function')
def db_session(db_engine):
    """Create a new database session for each test."""
    from src.database import Base
    
    # Create all tables
    Base.metadata.create_all(bind=db_engine)
    
    # Create a new session
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    # Create test employee
    from src.models.employee import Employee
    employee = Employee(
        id=1,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    session.add(employee)
    session.commit()
    
    yield session
    
    # Clean up
    session.close()
    Base.metadata.drop_all(bind=db_engine)
