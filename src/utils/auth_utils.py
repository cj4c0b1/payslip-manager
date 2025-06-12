"""
Authentication utilities for the application.
"""
from functools import wraps
from typing import Callable, Any, Optional
import streamlit as st
from jose import jwt
from jose.exceptions import JWTError
import logging

logger = logging.getLogger(__name__)

def login_required(func: Callable) -> Callable:
    """
    Decorator to ensure the user is logged in.
    
    Redirects to login page if not authenticated.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            # Store the current page to redirect back after login
            st.session_state["redirect_after_login"] = dict(st.query_params)
            # Redirect to login page
            st.rerun()
            return
        return func(*args, **kwargs)
    return wrapper

def admin_required(func: Callable) -> Callable:
    """
    Decorator to ensure the user is logged in as an admin.
    
    Redirects to login page if not authenticated, or shows an error if not an admin.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            st.session_state["redirect_after_login"] = dict(st.query_params)
            st.rerun()
            return
            
        if not is_admin():
            st.error("You don't have permission to access this page.")
            st.stop()
            return
            
        return func(*args, **kwargs)
    return wrapper

def is_authenticated() -> bool:
    """Check if the user is currently authenticated."""
    return st.session_state.get("authenticated", False)

def is_admin() -> bool:
    """Check if the current user is an admin."""
    return st.session_state.get("user", {}).get("is_admin", False)

def get_current_user() -> Optional[dict]:
    """Get the current user's information."""
    return st.session_state.get("user")

def logout():
    """Log the current user out."""
    if "user" in st.session_state:
        del st.session_state["user"]
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
    st.experimental_rerun()

def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return the payload if valid.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Optional[dict]: The decoded token payload if valid, None otherwise
    """
    try:
        # Get the secret key from environment or use a default (not for production)
        secret_key = st.secrets.get("SECRET_KEY", "default-insecure-secret-key")
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"]
        )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None

def get_auth_headers() -> dict:
    """
    Get headers for authenticated requests.
    
    Returns:
        dict: Headers with authorization token if logged in
    """
    if is_authenticated() and "auth_token" in st.session_state:
        return {"Authorization": f"Bearer {st.session_state.auth_token}"}
    return {}

def handle_unauthorized():
    """Handle unauthorized access by redirecting to login."""
    st.error("You need to be logged in to access this page.")
    st.session_state["redirect_after_login"] = dict(st.query_params)
    st.rerun()
