"""
Tests for magic link authentication functionality.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session as SQLAlchemySession

from src.services.magic_link_service import MagicLinkService, generate_token, hash_token
from src.database import get_db, Session, Base, get_session
from src.models.auth_models import MagicLink
from src.models.employee import Employee

# Test data
TEST_EMAIL = "test@example.com"
TEST_IP = "192.168.1.1"
TEST_USER_AGENT = "Mozilla/5.0 (Test Browser)"
TEST_EMPLOYEE_ID = 1  # Must match the ID in conftest.py

def test_generate_token():
    """Test token generation produces a non-empty string."""
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) >= 32  # Should be at least 32 chars

def test_hash_token():
    """Test that token hashing produces consistent results."""
    token = "test_token_123"
    hashed = hash_token(token)
    assert isinstance(hashed, str)
    assert hashed != token  # Should be hashed
    assert len(hashed) == 64  # SHA-256 produces 64-char hex string
    
    # Same token should produce same hash
    assert hashed == hash_token(token)
    
    # Different tokens should produce different hashes
    assert hashed != hash_token("different_token")

from freezegun import freeze_time

@freeze_time("2023-01-01 12:00:00")
def test_create_magic_link(db_session):
    """Test creating a magic link."""
    fixed_now = datetime(2023, 1, 1, 12, 0, 0)
    
    # Get the test employee
    employee = db_session.query(Employee).filter_by(id=TEST_EMPLOYEE_ID).first()
    assert employee is not None
    
    # Create a function to verify the magic link state
    def verify_magic_link(link, expected_now):
        assert link.id is not None
        assert link.email == employee.email
        assert link.user_id == employee.id
        assert link.user_agent == TEST_USER_AGENT
        assert link.ip_address == TEST_IP
        assert link.created_at == expected_now
        assert link.expires_at == expected_now + timedelta(minutes=15)
        assert not link.is_used
        assert link.used_at is None
    
    # Create magic link using the service
    # Since we're using freezegun, we don't need to pass datetime_override
    service = MagicLinkService(db_session)
    
    # Create the magic link
    token, magic_link = service.create_magic_link(
        email=employee.email,
        user_agent=TEST_USER_AGENT,
        ip_address=TEST_IP,
        user_id=employee.id,
        expiration_minutes=15
    )
    
    # Verify the magic link state
    assert magic_link.id is not None
    assert magic_link.email == employee.email
    assert magic_link.user_id == employee.id
    assert magic_link.user_agent == TEST_USER_AGENT
    assert magic_link.ip_address == TEST_IP
    
    # With freezegun, the timestamps should match our fixed time
    assert magic_link.created_at == fixed_now
    assert magic_link.expires_at == fixed_now + timedelta(minutes=15)
    assert not magic_link.is_used
    assert magic_link.used_at is None
    
    # Commit and verify persistence
    db_session.commit()
    
    # Get a fresh instance from the database
    fresh_link = db_session.get(MagicLink, magic_link.id)
    assert fresh_link is not None
    
    # Verify the timestamps were persisted correctly
    assert fresh_link.created_at == fixed_now
    assert fresh_link.expires_at == fixed_now + timedelta(minutes=15)
    
    assert not magic_link.is_used
    assert magic_link.used_at is None

@freeze_time("2023-01-01 12:00:00")
def test_validate_magic_link(db_session):
    """Test validating a magic link."""
    fixed_now = datetime(2023, 1, 1, 12, 0, 0)
    
    # Create service
    service = MagicLinkService(db_session)
    token, magic_link = service.create_magic_link(
        email=TEST_EMAIL,
        user_agent=TEST_USER_AGENT,
        ip_address=TEST_IP,
        user_id=db_session.query(Employee).first().id,
        expiration_minutes=15
    )
    
    # Test validation (should not mark as used)
    validated_link = service.validate_magic_link(token, TEST_IP, TEST_USER_AGENT)
    assert validated_link is not None
    assert validated_link.id == magic_link.id
    assert not validated_link.is_used
    
    # Mark as used
    service.mark_used(validated_link)
    
    # Test reusing the same token (should fail because it's now used)
    assert service.validate_magic_link(token, TEST_IP, TEST_USER_AGENT) is None
    
    # Test with wrong IP
    assert service.validate_magic_link(token, "192.168.1.2", TEST_USER_AGENT) is None
    
    # Test with wrong user agent
    assert service.validate_magic_link(token, TEST_IP, "Different Browser") is None

@freeze_time("2023-01-01 12:00:00")
def test_expired_magic_link(db_session):
    """Test that expired magic links are not valid."""
    # Get the test employee
    employee = db_session.query(Employee).filter_by(id=TEST_EMPLOYEE_ID).first()
    assert employee is not None
    
    fixed_now = datetime(2023, 1, 1, 12, 0, 0)
    
    # Create service
    service = MagicLinkService(db_session)
    token, magic_link = service.create_magic_link(
        email=TEST_EMAIL,
        user_agent=TEST_USER_AGENT,
        ip_address=TEST_IP,
        user_id=employee.id,
        expiration_minutes=15  # Will expire at 12:15
    )
    
    # Verify the magic link was created with the expected expiration
    expected_expiration = fixed_now + timedelta(minutes=15)
    assert magic_link.expires_at == expected_expiration
    
    # Move time to after expiration (now + 16 minutes) using freezegun
    with freeze_time("2023-01-01 12:16:00"):
        # Should be expired and return None
        assert service.validate_magic_link(token, TEST_IP, TEST_USER_AGENT) is None

@freeze_time("2023-01-01 12:00:00")
def test_mark_used(db_session):
    """Test marking a magic link as used."""
    fixed_now = datetime(2023, 1, 1, 12, 0, 0)
    
    # Get the test employee
    employee = db_session.query(Employee).filter_by(id=TEST_EMPLOYEE_ID).first()
    assert employee is not None
    
    # Create service
    service = MagicLinkService(db_session)
    token, magic_link = service.create_magic_link(
        email=TEST_EMAIL,
        user_agent=TEST_USER_AGENT,
        ip_address=TEST_IP,
        user_id=employee.id,
        expiration_minutes=15
    )
    
    # Verify initial state
    assert not magic_link.is_used
    assert magic_link.used_at is None
    
    # Mark as used
    service.mark_used(magic_link)
    
    # Verify it's marked as used
    db_session.refresh(magic_link)
    assert magic_link.is_used
    assert magic_link.used_at == fixed_now
    
    # Should not validate because it's already used
    assert service.validate_magic_link(token, TEST_IP, TEST_USER_AGENT) is None
