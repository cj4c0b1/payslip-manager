"""
Streamlit authentication module for handling user authentication in the UI.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.auth.service import auth_service
from src.auth.schemas import UserSession
from src.database import get_db_session
from src.models.employee import Employee

# Session state keys
SESSION_KEY = "user_session"
TOKEN_KEY = "auth_token"
LAST_ACTIVITY_KEY = "last_activity"
SESSION_TIMEOUT_MINUTES = 30  # 30 minutes of inactivity

class StreamlitAuth:
    """Handles authentication for Streamlit applications."""
    
    @staticmethod
    def init_session():
        """Initialize session state for authentication if it doesn't exist."""
        if SESSION_KEY not in st.session_state:
            st.session_state[SESSION_KEY] = None
        if TOKEN_KEY not in st.session_state:
            st.session_state[TOKEN_KEY] = None
        if LAST_ACTIVITY_KEY not in st.session_state:
            st.session_state[LAST_ACTIVITY_KEY] = datetime.now()
    
    @staticmethod
    def update_activity():
        """Update the last activity timestamp."""
        st.session_state[LAST_ACTIVITY_KEY] = datetime.now()
    
    @staticmethod
    def is_session_expired() -> bool:
        """Check if the current session has expired due to inactivity."""
        if LAST_ACTIVITY_KEY not in st.session_state:
            return True
            
        last_activity = st.session_state[LAST_ACTIVITY_KEY]
        if not last_activity:
            return True
            
        inactive_time = datetime.now() - last_activity
        return inactive_time.total_seconds() > (SESSION_TIMEOUT_MINUTES * 60)
    
    @staticmethod
    def login_with_token(token: str) -> bool:
        """
        Log in a user with a magic link token.
        
        Args:
            token: The magic link token
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            # Verify the token
            is_valid, user_data = auth_service.verify_token(token)
            
            if not is_valid or not user_data:
                st.error("Invalid or expired login link. Please request a new one.")
                return False
            
            # Get the user from the database
            with get_db_session() as db:
                user = db.query(Employee).filter(Employee.email == user_data["email"]).first()
                
                if not user:
                    st.error("User not found. Please contact support.")
                    return False
                
                # Create user session
                session_data = {
                    "user_id": user.id,
                    "email": user.email,
                    "is_active": user.is_active,
                    "last_login": user.last_login_at
                }
                
                # Store session data
                st.session_state[SESSION_KEY] = session_data
                st.session_state[TOKEN_KEY] = token
                StreamlitAuth.update_activity()
                
                st.success(f"Welcome back, {user.email}!")
                return True
                
        except Exception as e:
            st.error(f"An error occurred during login: {str(e)}")
            return False
    
    @staticmethod
    def logout():
        """Log out the current user."""
        if SESSION_KEY in st.session_state:
            del st.session_state[SESSION_KEY]
        if TOKEN_KEY in st.session_state:
            del st.session_state[TOKEN_KEY]
        if LAST_ACTIVITY_KEY in st.session_state:
            del st.session_state[LAST_ACTIVITY_KEY]
    
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """
        Get the current authenticated user.
        
        Returns:
            Optional[Dict[str, Any]]: User data if authenticated, None otherwise
        """
        # Check if session exists and is not expired
        if SESSION_KEY not in st.session_state or not st.session_state[SESSION_KEY]:
            return None
            
        if StreamlitAuth.is_session_expired():
            st.session_state[SESSION_KEY] = None
            st.session_state[TOKEN_KEY] = None
            st.warning("Your session has expired. Please log in again.")
            return None
            
        # Update last activity
        StreamlitAuth.update_activity()
        return st.session_state[SESSION_KEY]
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if a user is currently authenticated."""
        return StreamlitAuth.get_current_user() is not None
    
    @staticmethod
    def require_auth():
        """Decorator to protect routes that require authentication."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not StreamlitAuth.is_authenticated():
                    # Store the current page to redirect back after login
                    st.session_state["redirect_after_login"] = st.query_params.get("page", "")
                    st.switch_page("/login")
                    return
                return func(*args, **kwargs)
            return wrapper
        return decorator

# Initialize auth when module is imported
StreamlitAuth.init_session()
