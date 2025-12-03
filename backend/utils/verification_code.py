"""
Verification code generation and validation utilities for certificates.

Format: ALX-YYYY-MMDD-XXXXX
- ALX: AlphaLab prefix
- YYYY: Year (4 digits)
- MM: Month (2 digits)
- DD: Day (2 digits)
- XXXXX: Random alphanumeric string (5 characters, uppercase)
"""

import re
import secrets
import string
from datetime import datetime
from typing import Tuple


def generate_verification_code() -> str:
    """
    Generate a unique verification code for certificates.
    
    Format: ALX-YYYY-MMDD-XXXXX
    Example: ALX-2024-1204-A7K9M
    
    Returns:
        str: Generated verification code
    """
    now = datetime.utcnow()
    
    # Date components
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    
    # Random alphanumeric suffix (5 characters, uppercase)
    # Using secrets for cryptographically strong randomness
    alphabet = string.ascii_uppercase + string.digits
    random_suffix = ''.join(secrets.choice(alphabet) for _ in range(5))
    
    # Construct verification code
    verification_code = f"ALX-{year}-{month}{day}-{random_suffix}"
    
    return verification_code


def validate_verification_code(code: str) -> Tuple[bool, str]:
    """
    Validate the format of a verification code.
    
    Args:
        code: The verification code to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if code format is valid, False otherwise
            - error_message: Empty string if valid, error description if invalid
    """
    if not code:
        return False, "Verification code cannot be empty"
    
    # Expected format: ALX-YYYY-MMDD-XXXXX
    pattern = r'^ALX-\d{4}-\d{4}-[A-Z0-9]{5}$'
    
    if not re.match(pattern, code):
        return False, "Invalid verification code format. Expected format: ALX-YYYY-MMDD-XXXXX"
    
    # Extract date components for additional validation
    try:
        parts = code.split('-')
        year = int(parts[1])
        month_day = parts[2]
        month = int(month_day[:2])
        day = int(month_day[2:])
        
        # Validate year range (reasonable bounds)
        if year < 2024 or year > 2100:
            return False, "Invalid year in verification code"
        
        # Validate month
        if month < 1 or month > 12:
            return False, "Invalid month in verification code"
        
        # Validate day
        if day < 1 or day > 31:
            return False, "Invalid day in verification code"
        
        # Additional validation: check if date is valid
        datetime(year, month, day)
        
    except (ValueError, IndexError):
        return False, "Invalid date components in verification code"
    
    return True, ""
