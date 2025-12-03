"""
Encryption Service.

Purpose:
    Provides secure AES-256 encryption and decryption for sensitive data (API keys).
    Ensures that user API keys are never stored in plain text in the database.

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

@lru_cache()
def get_fernet() -> Fernet:
    """
    Get or create Fernet instance.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # In production, this must fail if the key is missing to prevent data loss
        raise ValueError("CRITICAL: ENCRYPTION_KEY environment variable is not set. Cannot start encryption service.")
    
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage."""
    f = get_fernet()
    return f.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for use."""
    f = get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()

def mask_api_key(api_key: str) -> str:
    """Create masked version for display: sk-or-v1-••••••••"""
    if not api_key:
        return ""
    if len(api_key) < 15:
        return "••••••••"
    # Assuming OpenRouter keys start with sk-or-v1-
    # If generic, just show first few chars
    return api_key[:10] + "••••••••"
