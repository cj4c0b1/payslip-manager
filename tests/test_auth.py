"""
Test script for the authentication system.
Run with: python -m pytest tests/test_auth.py -v
"""
import sys
import os
import logging
import datetime
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auth_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Import modules after path is set
import pytest
from sqlalchemy.orm import Session

# Import test configuration
from tests.conftest import db_session

# Import models and services
from src.models import Employee
from src.auth.models import MagicToken
from src.auth.service import AuthService

# Test configuration
TEST_EMAIL = "test@example.com"
TEST_EMAIL_2 = "another@example.com"

@pytest.fixture
def auth_service(db_session):
    """Create a new AuthService instance for testing."""
    # Create a new AuthService with the test database session
    service = AuthService(db=db_session)
    yield service
    
    # Clean up after the test
    if db_session:
        db_session.rollback()
        db_session.close()

def test_create_magic_link(auth_service, db_session):
    """Test creating a magic link token."""
    # Clean up any existing tokens for the test email
    db_session.query(MagicToken).filter(MagicToken.email == TEST_EMAIL).delete()
    db_session.commit()
    db_session.query(MagicToken).delete()
    db_session.commit()
    
    # Create a magic link
    token, success = auth_service.create_magic_link(
        email=TEST_EMAIL,
        user_agent="test_agent",
        ip_address="127.0.0.1"
    )
    
    assert success is True
    assert isinstance(token, str)
    assert len(token) > 20  # Should be a long random string
    
    # Verify the token was saved to the database
    token_hash = auth_service._hash_token(token)
    db_token = db_session.query(MagicToken).filter(MagicToken.token_hash == token_hash).first()
    assert db_token is not None
    assert db_token.email == TEST_EMAIL
    assert db_token.used is False
    assert db_token.expires_at > datetime.datetime.utcnow()

def test_verify_token(auth_service, db_session):
    """Test verifying a magic link token."""
    # Clean up any existing tokens for the test email
    db_session.query(MagicToken).filter(MagicToken.email == TEST_EMAIL).delete()
    db_session.commit()
    db_session.query(MagicToken).delete()
    db_session.query(Employee).filter(Employee.email == TEST_EMAIL).delete()
    db_session.commit()
    
    # Create a test token
    token, _ = auth_service.create_magic_link(
        email=TEST_EMAIL,
        user_agent="test_agent",
        ip_address="127.0.0.1"
    )
    
    # Verify the token
    is_valid, user_data = auth_service.verify_token(token)
    
    assert is_valid is True
    assert isinstance(user_data, dict)
    assert user_data["email"] == TEST_EMAIL
    
    # Verify the user was created
    user = db_session.query(Employee).filter(Employee.email == TEST_EMAIL).first()
    assert user is not None
    assert user.email == TEST_EMAIL
    assert user.is_active is True
    
    # Verify the token was marked as used
    token_hash = auth_service._hash_token(token)
    db_token = db_session.query(MagicToken).filter(MagicToken.token_hash == token_hash).first()
    assert db_token.used is True
    assert db_token.used_at is not None

def test_verify_invalid_token(auth_service, db_session):
    """Test verifying an invalid token."""
    # Clean up any existing tokens for the test email
    db_session.query(MagicToken).filter(MagicToken.email == TEST_EMAIL).delete()
    db_session.commit()
    
    # Verify an invalid token
    is_valid, user_data = auth_service.verify_token("invalid_token_123")
    assert is_valid is False
    assert user_data is None

def test_verify_used_token(auth_service, db_session):
    """Test that a used token cannot be used again."""
    # Clean up any existing tokens for the test email
    db_session.query(MagicToken).filter(MagicToken.email == TEST_EMAIL).delete()
    db_session.commit()
    db_session.query(MagicToken).delete()
    db_session.commit()
    
    # Create and use a token
    token, _ = auth_service.create_magic_link(
        email=TEST_EMAIL_2,
        user_agent="test_agent",
        ip_address="127.0.0.1"
    )
    
    # First verification should succeed
    is_valid, _ = auth_service.verify_token(token)
    assert is_valid is True
    
    # Second verification should fail
    is_valid, user_data = auth_service.verify_token(token)
    assert is_valid is False
    assert user_data is None

def test_cleanup_expired_tokens(auth_service, db_session):
    """Test cleaning up expired tokens."""
    # Clean up any existing tokens for the test emails
    db_session.query(MagicToken).filter(MagicToken.email.in_([TEST_EMAIL, TEST_EMAIL_2])).delete()
    db_session.commit()
    db_session.query(MagicToken).delete()
    db_session.commit()
    
    # Create some test tokens
    now = datetime.datetime.utcnow()
    
    # Expired token
    expired_token = MagicToken(
        email="expired@example.com",
        token_hash="expired_hash",
        expires_at=now - datetime.timedelta(days=1),
        used=False,
        created_at=now - datetime.timedelta(days=2)
    )
    
    # Used token
    used_token = MagicToken(
        email=TEST_EMAIL,
        token_hash="used_hash",
        expires_at=now + datetime.timedelta(days=1),
        used=True,
        used_at=now - datetime.timedelta(hours=1),
        created_at=now - datetime.timedelta(days=2)
    )
    
    # Valid token
    valid_token = MagicToken(
        email=TEST_EMAIL_2,
        token_hash="valid_hash",
        expires_at=now + datetime.timedelta(days=1),
        used=False,
        created_at=now
    )
    
    # Add to database
    db_session.add(expired_token)
    db_session.add(used_token)
    db_session.add(valid_token)
    db_session.commit()
    
    # Verify tokens were added
    assert db_session.query(MagicToken).count() == 3
    
    # Clean up expired and used tokens
    deleted_count = auth_service.cleanup_expired_tokens()
    
    # Should delete the expired and used tokens
    assert deleted_count == 2
    
    # Only the valid token should remain
    remaining_tokens = db_session.query(MagicToken).all()
    assert len(remaining_tokens) == 1
    assert remaining_tokens[0].token_hash == "valid_hash"

if __name__ == "__main__":
    # Run tests directly with pytest
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
