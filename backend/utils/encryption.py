"""
Encryption Utilities.

Purpose:
    Provides secure AES-256 encryption and decryption for sensitive data (API keys).
    Ensures that user API keys are never stored in plain text in the database.

Usage:
    from utils.encryption import encrypt_api_key, decrypt_api_key, mask_api_key

Data Flow:
    - Incoming: Raw API key strings from the API layer (e.g., api/api_keys.py).
    - Processing: 
        - Encrypts raw keys using Fernet (symmetric encryption) with a server-side secret key.
        - Decrypts stored keys when needed for making external API calls (e.g., to OpenRouter).
        - Masks keys (e.g., "sk-or-v1-••••") for safe display in the UI.
    - Outgoing: Encrypted strings for database storage, or decrypted strings for internal service use.
"""
from cryptography.fernet import Fernet
import os
import base64
from functools import lru_cache
from exceptions import ConfigurationError


@lru_cache()
def get_fernet() -> Fernet:
    """
    Get or create Fernet instance.
    
    Returns:
        Fernet: Encryption instance
        
    Raises:
        ConfigurationError: If ENCRYPTION_KEY is not set
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ConfigurationError(
            "ENCRYPTION_KEY environment variable is not set. Cannot start encryption service."
        )
    
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt API key for storage.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key string
    """
    f = get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt API key for use.
    
    Args:
        encrypted_key: Encrypted API key
        
    Returns:
        Plain text API key
    """
    f = get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()


def mask_api_key(api_key: str) -> str:
    """
    Create masked version for display: sk-or-v1-••••••••
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Masked API key for safe display
    """
    if not api_key:
        return ""
    if len(api_key) < 15:
        return "••••••••"
    # Show first 10 characters, mask the rest
    return api_key[:10] + "••••••••"


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key
        
    Note:
        This should only be used once during initial setup.
        Store the key securely in environment variables.
    """
    return Fernet.generate_key().decode()
