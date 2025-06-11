"""
Magic Link Authentication

This module provides passwordless login functionality using magic links.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from src.services.auth_service import auth_service
from src.services.email_service import send_magic_link_email
from database import Session
from src.models.auth_models import MagicLink

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
    </style>
""", unsafe_allow_html=True)

def show_login_form():
    """Display the magic link login form."""
    st.title("🔑 Sign in")
    
    with st.form("magic_link_form"):
        email = st.text_input("Email address", 
                           placeholder="your.email@example.com",
                           help="Enter your email address to receive a secure login link")
        
        submitted = st.form_submit_button("Send Magic Link")
        
        if submitted:
            if not email or "@" not in email:
                st.error("Please enter a valid email address")
                return
            
            with st.spinner("Sending magic link..."):
                try:
                    # Generate and save magic link
                    token, magic_link = auth_service.create_magic_link(
                        email=email,
                        user_agent=st.experimental_get_query_params().get("user_agent", [""])[0],
                        ip_address=st.experimental_get_query_params().get("ip", [""])[0]
                    )
                    
                    # Build the magic link URL
                    base_url = st.experimental_get_query_params().get("base_url", ["http://localhost:8501"])[0]
                    magic_link_url = f"{base_url.rstrip('/')}/magic_link?token={token}&email={email}"
                    
                    # Send the email
                    if send_magic_link_email(
                        email=email,
                        magic_link=magic_link_url,
                        expiration_minutes=MagicLink.TOKEN_EXPIRATION_MINUTES,
                        app_name="Payslip Manager"
                    ):
                        st.session_state["magic_link_sent"] = True
                        st.session_state["magic_link_email"] = email
                        st.experimental_rerun()
                    else:
                        st.error("Failed to send magic link. Please try again later.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.stop()

def show_magic_link_sent():
    """Show confirmation that the magic link was sent."""
    st.title("📨 Check Your Email")
    
    email = st.session_state.get("magic_link_email", "your email")
    
    st.markdown(f"""
    <div class="success">
        <h3>Magic link sent!</h3>
        <p>We've sent a secure login link to <strong>{email}</strong>.</p>
        <p>Click the link in the email to sign in.</p>
        <p><em>This link will expire in {MagicLink.TOKEN_EXPIRATION_MINUTES} minutes and can only be used once.</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("↻ Resend Magic Link"):
        del st.session_state["magic_link_sent"]
        st.experimental_rerun()
    
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

def verify_magic_link(token: str, email: str):
    """
    Verify a magic link and log the user in if valid.
    
    Args:
        token: The magic link token
        email: The email address the token was sent to
    """
    with st.spinner("Verifying login..."):
        try:
            # Verify the magic link
            magic_link = auth_service.verify_magic_link(token, email)
            
            if magic_link and magic_link.is_valid:
                # Get or create the user
                with Session() as session:
                    # Look up the user by email
                    from src.models.employee import Employee  # Import here to avoid circular imports
                    user = session.query(Employee).filter(
                        Employee.email == email
                    ).first()
                    
                    # If user doesn't exist, create them
                    if not user:
                        user = Employee(
                            email=email,
                            is_active=True,
                            is_email_verified=True,
                            email_verified_at=datetime.utcnow()
                        )
                        session.add(user)
                        session.commit()
                        session.refresh(user)
                    
                    # Update user's last login
                    user.last_login_at = datetime.utcnow()
                    user.failed_login_attempts = 0
                    user.account_locked_until = None
                    
                    # Mark email as verified
                    if not user.is_email_verified:
                        user.is_email_verified = True
                        user.email_verified_at = datetime.utcnow()
                    
                    session.commit()
                    
                    # Create a session for the user
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = {
                        "id": user.id,
                        "email": user.email,
                        "is_admin": user.is_admin,
                        "name": user.name or user.email.split("@")[0]
                    }
                    
                    # Redirect to the main app
                    st.experimental_set_query_params()
                    st.experimental_rerun()
            else:
                st.error("Invalid or expired login link. Please request a new one.")
                st.stop()
                
        except Exception as e:
            st.error(f"An error occurred during login: {str(e)}")
            st.stop()

def main():
    """Main entry point for the login page."""
    # Check for magic link in URL
    query_params = st.experimental_get_query_params()
    
    if "token" in query_params and "email" in query_params:
        verify_magic_link(
            token=query_params["token"][0],
            email=query_params["email"][0]
        )
    elif st.session_state.get("magic_link_sent", False):
        show_magic_link_sent()
    else:
        show_login_form()

if __name__ == "__main__":
    main()
