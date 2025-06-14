"""
Pytest configuration and fixtures for testing.
"""
import os
import sys
from pathlib import Path
import pytest
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy import event

# Add project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set test database URL - use in-memory SQLite for tests
test_db_url = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = test_db_url

# Import database and models after setting the test database URL
from src.database import create_db_engine, get_base, get_db, Session, SessionFactory

# Create a fresh Base for testing to avoid table redefinition issues
TestBase = get_base()

# Create a test engine with a fresh Base
engine = create_db_engine(test_db_url)
# Create a test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Create a scoped session for testing
TestingSession = scoped_session(TestingSessionLocal)

# Import models after getting a fresh Base and engine
from src.models.employee import Employee
from src.auth.models import MagicToken

@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine and tables."""
    # Create all tables
    TestBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    TestBase.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """Create a new database session for testing."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Start a savepoint for nested transactions
    session.begin_nested()
    
    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    yield session
    
    # Clean up
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def setup_test_database(db_session):
    """Set up test database with required data."""
    # This runs before each test
    # Clear all data from tables
    for table in reversed(TestBase.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    
    yield
    
    # Clean up after each test
    db_session.rollback()

@pytest.fixture
def client(db_session):
    """Create a test client with overridden database session."""
    from fastapi.testclient import TestClient
    from src.main import app
    
    # Override the database session in the app
    app.dependency_overrides[get_db] = lambda: db_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides after the test
    app.dependency_overrides.clear()

# Override the database session in the application
import src.database as database
database.Session = TestingSession
database.SessionFactory = TestingSessionLocal
