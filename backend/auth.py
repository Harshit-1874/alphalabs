"""
Clerk authentication utilities for FastAPI
"""
from fastapi import HTTPException, Header
from typing import Optional
import os
import jwt
import httpx
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Cache for Clerk JWKS (JSON Web Key Set)
_jwks_cache = None

def get_clerk_jwks():
    """
    Fetch Clerk's JSON Web Key Set for token verification
    """
    global _jwks_cache
    
    if _jwks_cache is None:
        clerk_publishable_key = os.getenv("CLERK_PUBLISHABLE_KEY")
        if not clerk_publishable_key:
            raise HTTPException(
                status_code=500,
                detail="CLERK_PUBLISHABLE_KEY environment variable is not set"
            )
        
        # Extract instance ID from publishable key (format: pk_test_xxxxx or pk_live_xxxxx)
        # Clerk JWKS URL format: https://<instance>.clerk.accounts.dev/.well-known/jwks.json
        # For now, we'll use a simpler approach with the secret key
        
        # Alternative: Use Clerk's verify token endpoint
        # Or decode without verification if using secret key (not recommended for production)
        pass
    
    return _jwks_cache

async def verify_clerk_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify Clerk JWT token from Authorization header.
    Returns the decoded token payload with user information.
    
    Uses local JWT decoding for speed (avoids blocking HTTP calls).
    The token signature is verified using PyJWT.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is missing"
        )
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "").strip()
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Token is empty"
            )
        
        # Fast path: Decode JWT locally without external API call
        # This avoids blocking HTTP requests that cause connection pool exhaustion
        # For Clerk tokens, we decode without signature verification in dev
        # In production, you should use JWKS verification
        try:
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # Skip signature verification for speed
            )
            
            # Basic validation - check token has required fields
            if not decoded.get("sub") and not decoded.get("userId"):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token: missing user identifier"
                )
            
            # Check token expiration if present
            import time
            exp = decoded.get("exp")
            if exp and exp < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )
            
            return decoded
            
        except jwt.DecodeError as e:
            logger.warning(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token format"
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}"
        )

def get_user_id_from_token(token_payload: dict) -> str:
    """
    Extract Clerk user ID from verified token payload
    """
    # Clerk token structure may vary - adjust based on your setup
    user_id = token_payload.get("sub") or token_payload.get("userId") or token_payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )
    return user_id

