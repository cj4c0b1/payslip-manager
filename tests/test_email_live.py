"""
Live test for email service functionality.

This script tests the actual email sending functionality using the configuration
from environment variables or secrets.toml. It will send a real email to the specified recipient.
"""
import os
import sys
import logging
import pytest
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_email_live.log')
    ]
)
logger = logging.getLogger(__name__)

def get_test_config() -> Dict[str, Any]:
    """Get test configuration from environment or secrets."""
    config = {}
    
    # Try to get config from environment variables
    env_config = {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': os.getenv('SMTP_PORT'),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'from_email': os.getenv('FROM_EMAIL'),
        'test_email': os.getenv('TEST_EMAIL')
    }
    
    # Try to get from Streamlit secrets if not in environment
    if not all(env_config.values()):
        try:
            import streamlit as st
            secrets = st.secrets.get('email', {})
            config.update({
                'smtp_server': secrets.get('smtp_server'),
                'smtp_port': int(secrets.get('smtp_port', 587)),
                'smtp_username': secrets.get('smtp_username'),
                'smtp_password': secrets.get('smtp_password'),
                'from_email': secrets.get('default_sender'),
                'test_email': secrets.get('test_recipient') or secrets.get('TEST_EMAIL')
            })
        except Exception as e:
            logger.warning(f"Could not load Streamlit secrets: {e}")
    
    # Update with any environment variables that are set
    config.update({k: v for k, v in env_config.items() if v is not None})
    
    return config

def is_email_configured() -> bool:
    """Check if email configuration is complete for testing and live testing is enabled."""
    if not os.environ.get('RUN_LIVE_EMAIL_TESTS'):
        return False
    config = get_test_config()
    required = ['smtp_server', 'smtp_username', 'smtp_password', 'test_email']
    return all(config.get(key) for key in required)

@pytest.mark.skipif(
    not is_email_configured(),
    reason="Email configuration not complete or live email tests not enabled. Set SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, and TEST_EMAIL environment variables and RUN_LIVE_EMAIL_TESTS to run live email tests."
)
def test_email_configuration():
    """Test that the email configuration is valid."""
    config = get_test_config()
    logger.info("Email configuration:")
    for key in ['smtp_server', 'smtp_port', 'smtp_username', 'from_email', 'test_email']:
        logger.info(f"  {key}: {'*' * 8 if 'password' in key else config.get(key, 'Not set')}")
    
    # Basic validation
    assert config.get('smtp_server'), "SMTP server not configured"
    assert config.get('smtp_username'), "SMTP username not configured"
    assert config.get('smtp_password'), "SMTP password not configured"
    assert config.get('test_email'), "Test email address not configured"

@pytest.mark.skipif(
    not is_email_configured(),
    reason="Email configuration not complete. Set SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, and TEST_EMAIL environment variables."
)
def test_send_live_email():
    """Test sending a real email using the configured SMTP server."""
    from src.services.email_service import send_magic_link_email, EmailService
    
    config = get_test_config()
    test_email = config['test_email']
    
    logger.info(f"Sending test email to: {test_email}")
    logger.info(f"Using SMTP server: {config['smtp_server']}:{config.get('smtp_port', 587)}")
    
    # Create a test magic link with a timestamp to make it unique
    timestamp = int(datetime.utcnow().timestamp())
    magic_link = f"https://your-app-url.com/auth/verify?token=test_token_{timestamp}&email={test_email}"
    
    # Send the test email
    try:
        logger.info("Sending magic link email...")
        result = send_magic_link_email(
            email=test_email,
            magic_link=magic_link,
            expiration_minutes=15,
            app_name="Payslip Manager Test"
        )
        
        assert result is True, "Email sending failed (returned False)"
        logger.info("✅ Test email sent successfully!")
        logger.info(f"Check your email ({test_email}) for the test message.")
        
    except Exception as e:
        logger.exception("❌ Error sending test email:")
        pytest.fail(f"Failed to send test email: {str(e)}")
    finally:
        # Clean up any resources if needed
        pass

if __name__ == "__main__":
    print("Testing live email sending...")
    
    # Get test email
    test_email = get_test_email()
    if not test_email:
        print("Error: TEST_EMAIL environment variable or test_recipient in secrets not set")
        print("Please set TEST_EMAIL environment variable or add test_recipient to secrets.toml")
        sys.exit(1)
    
    # Run the test
    print(f"Sending test email to: {test_email}")
    try:
        # Import here to ensure logging is set up first
        from src.services.email_service import send_magic_link_email
        
        # Create a test magic link
        magic_link = f"https://your-app-url.com/auth/verify?token=test_token&email={test_email}"
        
        # Send the test email
        result = send_magic_link_email(
            email=test_email,
            magic_link=magic_link,
            expiration_minutes=15,
            app_name="Payslip Manager Test"
        )
        
        if result:
            print("✅ Test email sent successfully!")
            print(f"Check your email ({test_email}) for the test message.")
            sys.exit(0)
        else:
            print("❌ Failed to send test email.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error sending test email: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
