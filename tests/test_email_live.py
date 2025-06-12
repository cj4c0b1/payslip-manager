"""
Live test for email service functionality.

This script tests the actual email sending functionality using the configuration
from secrets.toml. It will send a real email to the specified recipient.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import pytest

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_test_email():
    """Get the test email address from environment or secrets."""
    test_email = os.getenv('TEST_EMAIL')
    if not test_email:
        try:
            import streamlit as st
            test_email = st.secrets.get('TEST_EMAIL')
            if not test_email:
                test_email = st.secrets.get('email', {}).get('test_recipient')
        except Exception:
            pass
    return test_email

@pytest.mark.skipif(
    not get_test_email(),
    reason="TEST_EMAIL environment variable or test_recipient in secrets not set"
)
def test_send_live_email():
    """Test sending a real email using the configured SMTP server."""
    from src.services.email_service import send_magic_link_email
    
    test_email = get_test_email()
    assert test_email, "No test email address configured"
    
    logger.info(f"Sending test email to: {test_email}")
    
    # Create a test magic link
    magic_link = "https://your-app-url.com/auth/verify?token=test_token&email=" + test_email
    
    # Send the test email
    try:
        result = send_magic_link_email(
            email=test_email,
            magic_link=magic_link,
            expiration_minutes=15,
            app_name="Payslip Manager Test"
        )
        
        assert result is True, "Email sending failed"
        logger.info("✅ Test email sent successfully!")
        logger.info(f"Check your email ({test_email}) for the test message.")
        
    except Exception as e:
        logger.exception("❌ Error sending test email:")
        pytest.fail(f"Failed to send test email: {str(e)}")

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
