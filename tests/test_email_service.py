"""
Test script for email service functionality.

This script tests the email service by sending a test email with a magic link.
"""
import os
import sys
import logging
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock configuration for testing
TEST_CONFIG = {
    "smtp_server": "smtp.testserver.com",
    "smtp_port": 587,
    "smtp_username": "test@example.com",
    "smtp_password": "testpassword",
    "from_email": "test@example.com",
    "default_sender": "Test Sender <test@example.com>",
    "templates_dir": "email_templates"
}

# Mock the Streamlit module
sys.modules['streamlit'] = MagicMock()

@pytest.fixture
def mock_smtp():
    """Mock SMTP server for testing."""
    with patch('smtplib.SMTP') as mock_smtp:
        yield mock_smtp

@pytest.fixture
def email_service():
    """Create an email service with test configuration."""
    # Create a deep copy of the test config
    config = TEST_CONFIG.copy()
    
    # Mock the template loading
    template_content = """
    <html>
    <body>
        <h1>Magic Link</h1>
        <p>Click <a href="{{ magic_link }}">here</a> to log in.</p>
    </body>
    </html>
    """
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                from src.services.email_service import EmailService
                service = EmailService(config=config)
                yield service

def test_send_magic_link_email(mock_smtp):
    """Test sending a magic link email."""
    # Import the module-level function
    from src.services.email_service import send_magic_link_email
    
    # Test data
    test_email = "test@example.com"
    magic_link = "https://test-app.com/magic_link?token=test_token&email=test@example.com"
    
    # Mock the SMTP server
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server
    
    # Mock the email service instance
    with patch('src.services.email_service.email_service') as mock_service:
        # Configure the mock service
        mock_service.config = TEST_CONFIG
        mock_service.send_email.return_value = True
        
        # Send the test email
        result = send_magic_link_email(
            email=test_email,
            magic_link=magic_link,
            expiration_minutes=15,
            app_name="Payslip Manager Test"
        )
        
        # Verify the email was sent
        assert result is True, "Email sending should return True on success"
        mock_smtp.assert_called_once_with(TEST_CONFIG['smtp_server'], TEST_CONFIG['smtp_port'])
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            TEST_CONFIG['smtp_username'], 
            TEST_CONFIG['smtp_password']
        )
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()
        
        # Verify the service was called with the correct parameters
        mock_service.send_email.assert_called_once()

def test_missing_required_config():
    """Test that missing required configuration raises an error."""
    from src.services.email_service import EmailService, EmailServiceError
    
    # Test with missing required fields
    with pytest.raises(EmailServiceError) as excinfo:
        EmailService(config={})
    assert "Missing required email configuration" in str(excinfo.value)
    
    # Test with minimal required config
    minimal_config = {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user",
        "smtp_password": "pass",
        "from_email": "test@example.com"
    }
    service = EmailService(config=minimal_config)
    assert service is not None

if __name__ == "__main__":
    # This allows running the test directly with python -m tests.test_email_service
    pytest.main(["-v", "tests/test_email_service.py"])

if __name__ == "__main__":
    print("Testing email service...")
    result = test_send_magic_link_email()
    sys.exit(0 if result else 1)
