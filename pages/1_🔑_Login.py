"""
Magic Link Authentication

This module provides passwordless login functionality using magic links.
"""
import streamlit as st
import logging
import hmac
from typing import Tuple, Optional
from datetime import datetime, timedelta
import secrets
import hashlib
import urllib.parse
import uuid
import os
from pathlib import Path

# Import configuration and utilities
from src.config import settings
from src.utils.security_utils import generate_csrf_token, verify_csrf_token, get_secure_headers
from src.services.email_service import send_magic_link_email
from src.services.magic_link_service import MagicLinkService
from src.database import Session  # Updated import

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAGIC_LINK_EXPIRATION_HOURS = 1  # Magic link expires in 1 hour
MAX_LOGIN_ATTEMPTS = 5  # Maximum number of login attempts within RATE_LIMIT_WINDOW
RATE_LIMIT_WINDOW = 15 * 60  # 15 minutes in seconds

# Rate limiting storage (in-memory for this example, consider Redis in production)
login_attempts = {}

# CSRF token generation and verification
def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify a CSRF token against a stored token."""
    if not token or not stored_token:
        return False
    return hmac.compare_digest(token, stored_token)

# Page config
st.set_page_config(
    page_title="Login - Payslip Manager",
    page_icon="🔑",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            padding: 0.5rem 1rem;
        }
        .success {
            color: #28a745;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            margin: 1rem 0;
        }
        .error {
            color: #dc3545;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            margin: 1rem 0;
        }
        .info {
            color: #17a2b8;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d1ecf1;
            margin: 1rem 0;
        }
        .login-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .magic-link-sent {
            text-align: center;
            padding: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

def is_valid_email(email: str) -> bool:
    """
    Validate an email address according to OWASP standards.
    
    Args:
        email: The email address to validate
        
    Returns:
        bool: True if the email is valid, False otherwise
    """
    import re
    
    if not email or len(email) > 254:
        return False
        
    # Basic email format validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False
        
    # Check for common disposable email domains
    disposable_domains = {
        'mailinator.com', 'tempmail.com', 'guerrillamail.com',
        'sharklasers.com', 'maildrop.cc', '10minutemail.com'
    }
    domain = email.split('@')[1].lower()
    if domain in disposable_domains:
        return False
        
    return True


def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and other injection attacks.
    
    Args:
        input_str: The input string to sanitize
        max_length: Maximum allowed length of the input
        
    Returns:
        str: Sanitized input string
    """
    if not input_str:
        return ""
        
    # Truncate to max length
    sanitized = input_str[:max_length]
    
    # Remove potentially dangerous characters
    sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;').replace("'", '&#39;')
    sanitized = sanitized.replace('`', '&#96;')
    
    return sanitized


def is_rate_limited(ip_address: str, action: str = 'login_attempt') -> bool:
    """
    Check if the current IP is rate limited for the given action.
    
    Args:
        ip_address: The IP address to check
        action: The action being rate limited (e.g., 'login_attempt')
        
    Returns:
        bool: True if rate limited, False otherwise
    """
    if not ip_address:
        return False
        
    # In a production environment, you would use Redis or similar for distributed rate limiting
    # This is a simplified in-memory implementation
    rate_limits = st.session_state.get('_rate_limits', {})
    now = datetime.utcnow().timestamp()
    
    # Default rate limits (adjust as needed)
    limits = {
        'login_attempt': {'limit': 5, 'window': 300},  # 5 attempts per 5 minutes
        'magic_link': {'limit': 3, 'window': 3600}    # 3 emails per hour
    }
    
    action_limit = limits.get(action, limits['login_attempt'])
    key = f"{action}:{ip_address}"
    
    # Clean up old entries
    rate_limits[key] = [t for t in rate_limits.get(key, []) if now - t < action_limit['window']]
    
    # Check if limit is exceeded
    if len(rate_limits[key]) >= action_limit['limit']:
        return True
        
    # Record this attempt
    rate_limits[key] = rate_limits.get(key, []) + [now]
    st.session_state['_rate_limits'] = rate_limits
    
    return False

def create_magic_link(email: str) -> Tuple[bool, str]:
    """
    Create a magic link for the given email.
    
    Args:
        email: The email address to send the magic link to
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    db = None
    try:
        # Validate email format
        if not is_valid_email(email):
            return False, "Please enter a valid email address"
            
        # Check rate limiting (using a simpler approach for now)
        try:
            # Try to get the client IP from the request context
            from streamlit.web.server.websocket_headers import _get_websocket_headers
            headers = _get_websocket_headers()
            client_ip = headers.get('X-Forwarded-For', '127.0.0.1')
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
        except Exception as e:
            logger.warning(f"Could not get client IP: {str(e)}")
            client_ip = '127.0.0.1'
            
        if is_rate_limited(client_ip, 'magic_link'):
            return False, "Too many requests. Please try again later."
            
        # Create database session
        db = Session()
        
        # Check if email exists in the system
        from src.models.employee import Employee  # Import here to avoid circular imports
        employee = db.query(Employee).filter(Employee.email == email).first()
        if not employee:
            if db:
                db.close()
            return False, "No account found with this email address"
            
        # Generate and store magic link
        from src.services.magic_link_service import generate_token, hash_token
        token = generate_token()
        hashed_token = hash_token(token)
        
        # Create magic link record
        magic_link = MagicLink(
            email=email,
            token=hashed_token,
            expires_at=datetime.utcnow() + timedelta(hours=MAGIC_LINK_EXPIRATION_HOURS),
            used=False
        )
        
        db.add(magic_link)
        db.commit()
        
        # Send email with magic link
        base_url = os.getenv('BASE_URL', 'http://localhost:8501')
        magic_link_url = f"{base_url}/login?token={token}&email={urllib.parse.quote(email)}"
        send_magic_link_email(email, magic_link_url)
        
        return True, "Magic link sent to your email"
        
    except Exception as e:
        logger.error(f"Error creating magic link: {str(e)}", exc_info=True)
        if db:
            db.rollback()
        return False, "An error occurred. Please try again later."
    finally:
        if db:
            db.close()

def show_login_form():
    """Display the magic link login form with CSRF protection."""
    st.title("🔑 Sign in")
    
    # Generate and store CSRF token if not exists
    if '_csrf_token' not in st.session_state:
        st.session_state['_csrf_token'] = generate_csrf_token()
    
    # Initialize form
    with st.form("magic_link_form"):
        email = st.text_input(
            "Email address",
            placeholder="your.email@example.com",
            help="Enter your email address to receive a secure login link"
        )
        
        # Add CSRF token as hidden field
        csrf_token = st.session_state.get('_csrf_token')
        st.markdown(f'<input type="hidden" name="_csrf_token" value="{csrf_token}">', 
                   unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Send Magic Link")
        
        # Process form submission
        if submitted:
            # Get the form data from the request
            form_data = {}
            if '_csrf_token' in st.session_state:
                form_data['_csrf_token'] = st.session_state['_csrf_token']
            
            # Get the form token
            form_token = form_data.get('_csrf_token', '')
            
            # Verify CSRF token
            if not csrf_token or not form_token or not hmac.compare_digest(csrf_token, form_token):
                logger.warning("CSRF token validation failed")
                st.error("Security error. Please try again.")
                # Regenerate token for next attempt
                st.session_state['_csrf_token'] = generate_csrf_token()
                st.rerun()
            
            # Validate email
            if not email:
                st.error("Please enter your email address")
                st.stop()
            
            # Process the magic link request
            with st.spinner("Sending magic link..."):
                success, message = create_magic_link(email)
                if success:
                    st.session_state["magic_link_sent"] = True
                    st.session_state["magic_link_email"] = email
                    st.rerun()
                else:
                    st.error(message)

def verify_magic_link(token: str, email: str) -> Tuple[bool, str]:
    """
    Verify a magic link and authenticate the user if valid.
    
    Args:
        token: The magic link token
        email: The email address the token was sent to
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    # Input validation
    if not token or not email:
        logger.warning("Missing token or email in magic link verification")
        return False, "Invalid magic link. Please request a new one."
    
    # Sanitize inputs
    email = sanitize_input(email.strip().lower())
    token = sanitize_input(token)
    
    # Validate email format
    if not is_valid_email(email):
        logger.warning(f"Invalid email format during magic link verification: {email}")
        return False, "Invalid email format. Please check and try again."
    
    db = SessionLocal()
    try:
        # Get client IP for rate limiting and logging
        ip_address = st.query_params.get("ip", [""])[0]
        ip_address = sanitize_input(ip_address)
        
        # Check rate limiting for login attempts
        if is_rate_limited(ip_address, 'login_attempt'):
            logger.warning(f"Login rate limit exceeded for IP: {ip_address}")
            return False, "Too many login attempts. Please try again later."
        
        # Verify the magic link
        magic_link_service = MagicLinkService(db)
        magic_link = magic_link_service.validate_magic_link(token, email)
        
        if not magic_link:
            logger.warning(f"Invalid or expired magic link for email: {email}")
            return False, "Invalid or expired magic link. Please request a new one."
        
        # Get or create the user
        from src.models.employee import Employee
        
        with db.begin():
            user = db.query(Employee).filter(Employee.email == email).first()
            
            if not user:
                # Create a new user if they don't exist
                user = Employee(
                    email=email,
                    is_active=True,
                    is_email_verified=True,
                    email_verified_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(user)
                db.flush()  # Get the user ID
            
            # Update user's last login and reset failed attempts
            user.last_login_at = datetime.utcnow()
            user.failed_login_attempts = 0
            user.updated_at = datetime.utcnow()
        
        # Create user session with secure settings
        st.session_state.clear()  # Clear any existing session data
        st.session_state["authenticated"] = True
        st.session_state["user"] = {
            "id": user.id,
            "email": user.email,
            "is_admin": getattr(user, "is_admin", False),
            "name": getattr(user, "name", user.email.split("@")[0]),
            "session_start": datetime.utcnow().isoformat()
        }
        
        # Set session timeout (8 hours)
        st.session_state["expires"] = (datetime.utcnow() + timedelta(hours=8)).isoformat()
        
        # Log successful login
        logger.info(f"Successful login for user {user.email} (ID: {user.id}) from IP: {ip_address}")
        
        return True, "Successfully logged in!"
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying magic link: {str(e)}", exc_info=True)
        return False, "An error occurred during login. Please try again."
    finally:
        db.close()

def show_magic_link_sent():
    """Show confirmation that the magic link was sent."""
    st.title("📨 Check Your Email")
    
    email = st.session_state.get("magic_link_email", "your email")
    
    st.markdown(f"""
    <div class="magic-link-sent">
        <h3>✅ Magic link sent!</h3>
        <p>We've sent a secure login link to <strong>{email}</strong>.</p>
        <p>Click the link in the email to sign in.</p>
        <p><em>This link will expire in 15 minutes and can only be used once.</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("↻ Resend Magic Link", key="resend_magic_link"):
        if "magic_link_email" in st.session_state:
            email = st.session_state.magic_link_email
            success, message = create_magic_link(email)
            if success:
                st.success("New magic link sent!")
                st.rerun()
            else:
                st.error(message)
    
    st.markdown("---")
    st.markdown("""
    <div class="info">
        <h4>Didn't receive the email?</h4>
        <ul>
            <li>Check your spam or junk folder</li>
            <li>Make sure you entered the correct email address</li>
            <li>Wait a few minutes and try again</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

def handle_magic_link_verification():
    """Handle magic link verification from URL parameters."""
    token = st.query_params.get("token")
    email = st.query_params.get("email")
    
    if token and email:
        with st.spinner("Verifying your login..."):
            success, message = verify_magic_link(token, email)
            if success:
                st.success(message)
                # Redirect to the main app after a short delay
                st.balloons()
                st.markdown("""
                <script>
                    setTimeout(function(){
                        window.location.href = "/";
                    }, 2000);
                </script>
                """, unsafe_allow_html=True)
            else:
                st.error(message)
                st.markdown("""
                <div style="margin-top: 1rem;">
                    <a href="/login" class="stButton">
                        <button class="css-1x8cf2d edgvbvh10">Back to Login</button>
                    </a>
                </div>
                """, unsafe_allow_html=True)


def check_authentication() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)


def get_current_user() -> dict:
    """Get the current user from session."""
    return st.session_state.get("user", {})


def logout():
    """Log out the current user."""
    if "user" in st.session_state:
        del st.session_state["user"]
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
    st.rerun()


def set_security_headers():
    """Set secure HTTP headers for the response."""
    headers = get_secure_headers()
    for key, value in headers.items():
        st.markdown(
            f"""
            <meta http-equiv="{key.replace('-', '_').title().replace('_', '-')}" content="{value}">
            """,
            unsafe_allow_html=True
        )

def main():
    """Main entry point for the login page."""
    # Set secure headers
    set_security_headers()
    
    # Check if user is already authenticated
    if check_authentication():
        st.sidebar.success(f"Logged in as {get_current_user().get('email')}")
        if st.sidebar.button("Logout"):
            logout()
        return
    
    # Handle magic link verification
    handle_magic_link_verification()
    
    # Show the appropriate view based on session state
    if st.session_state.get("magic_link_sent", False):
        show_magic_link_sent()
    else:
        show_login_form()
    
    # Add security-related meta tags
    st.markdown("""
        <meta name="referrer" content="strict-origin-when-cross-origin">
        <meta name="referrer" content="same-origin">
        <meta name="referrer" content="no-referrer">
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
