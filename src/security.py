"""
Security module for handling encryption and sensitive data operations.
"""
import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Base class for security-related exceptions."""
    pass

class EncryptionManager:
    """
    Handles encryption and decryption of sensitive data.
    
    Uses Fernet symmetric encryption with a key derived from a master key.
    """
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption manager with a key.
        
        Args:
            key: The encryption key. If not provided, will try to get from Streamlit secrets.
        """
        self.key = self._get_encryption_key(key)
        self.fernet = Fernet(self.key)
    
    def _get_encryption_key(self, key: Optional[str] = None) -> bytes:
        """Get the encryption key from the provided key or Streamlit secrets."""
        if key is None:
            try:
                key = st.secrets.get("ENCRYPTION_KEY")
                if not key:
                    raise SecurityError("Encryption key not found in secrets")
            except Exception as e:
                logger.error("Failed to get encryption key from secrets: %s", str(e))
                raise SecurityError("Failed to initialize encryption: missing key") from e
        
        # Ensure the key is the correct length and URL-safe base64-encoded
        try:
            # Pad the key if necessary
            key = key.encode()
            key = key + b'=' * (4 - (len(key) % 4))  # Add padding if needed
            # Verify the key is valid base64
            base64.urlsafe_b64decode(key)
            return key
        except Exception as e:
            logger.error("Invalid encryption key format: %s", str(e))
            raise SecurityError("Invalid encryption key format") from e
    
    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypt the provided data."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        try:
            return self.fernet.encrypt(data)
        except Exception as e:
            logger.error("Encryption failed: %s", str(e))
            raise SecurityError("Failed to encrypt data") from e
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt the provided data and return as string."""
        try:
            return self.fernet.decrypt(encrypted_data).decode('utf-8')
        except InvalidToken:
            logger.error("Invalid or corrupted encrypted data")
            raise SecurityError("Invalid or corrupted data") from None
        except Exception as e:
            logger.error("Decryption failed: %s", str(e))
            raise SecurityError("Failed to decrypt data") from e

def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Hash a password with a salt using PBKDF2.
    
    Args:
        password: The password to hash
        salt: Optional salt. If not provided, a new one will be generated.
        
    Returns:
        tuple: (salt, hashed_password) as bytes
    """
    if salt is None:
        salt = os.urandom(16)  # 16 bytes = 128 bits
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=390000,  # OWASP recommended minimum as of 2023
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return salt, key

def verify_password(stored_salt: bytes, stored_key: bytes, password: str) -> bool:
    """Verify a password against a stored salt and key."""
    try:
        _, new_key = hash_password(password, stored_salt)
        return hmac.compare_digest(stored_key, new_key)
    except Exception as e:
        logger.error("Password verification failed: %s", str(e))
        return False

# Initialize a default encryption manager for convenience
try:
    security = EncryptionManager()
except SecurityError as e:
    logger.warning("Failed to initialize default encryption: %s", str(e))
    security = None
