"""
Security utilities for the application.

This module provides security-related utilities including CSRF protection,
secure headers, and other security middleware.
"""
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token.
    
    Returns:
        str: A secure random token
    """
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, stored_token: str) -> bool:
    """
    Verify a CSRF token against a stored token.
    
    Args:
        token: The token to verify
        stored_token: The stored token to verify against
        
    Returns:
        bool: True if the token is valid, False otherwise
    """
    if not token or not stored_token:
        return False
    return hmac.compare_digest(token, stored_token)

def get_secure_headers() -> Dict[str, str]:
    """
    Get a dictionary of secure HTTP headers.
    
    Returns:
        Dict[str, str]: Dictionary of security headers
    """
    return {
        # Prevent MIME type sniffing
        'X-Content-Type-Options': 'nosniff',
        # Enable XSS filtering in browsers that support it
        'X-XSS-Protection': '1; mode=block',
        # Restrict frame embedding to same-origin
        'X-Frame-Options': 'SAMEORIGIN',
        # Enable strict transport security (should be configured with care)
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        # Content Security Policy
        'Content-Security-Policy': 
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'",
        # Prevent browsers from embedding the page in frames
        'X-Permitted-Cross-Domain-Policies': 'none',
        # Disable caching for sensitive pages
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

def generate_secure_filename(filename: str) -> str:
    """
    Generate a secure filename by removing potentially dangerous characters.
    
    Args:
        filename: The original filename
        
    Returns:
        str: A sanitized filename
    """
    # Keep only alphanumeric, dots, underscores, and hyphens
    import re
    filename = re.sub(r'[^\w\-_. ]', '', filename)
    # Remove any leading or trailing dots and spaces
    filename = filename.strip('. ')
    return filename

def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Hash a password with a salt using PBKDF2-HMAC-SHA256.
    
    Args:
        password: The password to hash
        salt: Optional salt (if None, a new one will be generated)
        
    Returns:
        Tuple[bytes, bytes]: (salt, hashed_password)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # Use PBKDF2 with 100,000 iterations
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    
    return salt, hashed

def verify_password(stored_password: bytes, provided_password: str, salt: bytes) -> bool:
    """
    Verify a password against a stored hash and salt.
    
    Args:
        stored_password: The stored hashed password
        provided_password: The password to verify
        salt: The salt used to hash the stored password
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    _, hashed = hash_password(provided_password, salt)
    return hmac.compare_digest(stored_password, hashed)
