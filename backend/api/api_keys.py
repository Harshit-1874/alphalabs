"""
API Key Endpoints.

Purpose:
    Handles HTTP requests related to API key management.
    Allows users to securely store, list, and delete their external service API keys.

Data Flow:
    - Incoming: HTTP requests (POST, GET, DELETE) from the frontend, authenticated via Clerk.
    - Processing:
        - POST /: Receives raw key -> Encrypts via core.encryption -> Stores in DB.
        - GET /: Fetches keys from DB -> Masks them -> Returns list.
        - DELETE /: Verifies ownership -> Deletes from DB.
        - POST /{id}/validate: Decrypts key -> Calls OpenRouter API -> Updates status -> Returns result.
    - Outgoing: JSON responses containing masked key details or success messages to the user.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import List
from uuid import UUID

import httpx
from database import get_db
from dependencies import get_current_user
from models import ApiKey, User
from schemas.api_key_schemas import APIKeyCreate, APIKeyResponse, APIKeyListResponse, APIKeyValidationResponse
from core.encryption import encrypt_api_key, mask_api_key, decrypt_api_key

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])

@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys for the current user."""
    user_id = current_user.id
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return {"api_keys": keys}

@router.post("/", response_model=dict)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key."""
    user_id = current_user.id
    
    # If set as default, unset other defaults
    if key_data.set_as_default:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.user_id == user_id)
            .values(is_default=False)
        )
    
    # Encrypt key
    encrypted = encrypt_api_key(key_data.api_key)
    masked = mask_api_key(key_data.api_key)
    
    new_key = ApiKey(
        user_id=user_id,
        provider=key_data.provider,
        label=key_data.label,
        encrypted_key=encrypted,
        key_prefix=masked,
        is_default=key_data.set_as_default,
        status="untested"
    )
    
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    
    return {"api_key": APIKeyResponse.model_validate(new_key)}

@router.delete("/{key_id}", response_model=dict)
async def delete_api_key(
    key_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    user_id = current_user.id
    
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    await db.delete(key)
    await db.commit()
    
    return {"message": "API key deleted"}



@router.post("/{key_id}/validate", response_model=APIKeyValidationResponse)
async def validate_api_key(
    key_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate an API key by making a test request to OpenRouter.
    """
    user_id = current_user.id
    
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Decrypt key for validation
    try:
        decrypted_key = decrypt_api_key(key.encrypted_key)
    except Exception:
        key.status = "invalid"
        await db.commit()
        return {
            "valid": False,
            "status": "invalid",
            "error": "Failed to decrypt key"
        }

    # 1. Check format (OpenRouter keys usually start with sk-or-v1-)
    if not decrypted_key.startswith("sk-or-v1-"):
        key.status = "invalid"
        await db.commit()
        return {
            "valid": False,
            "status": "invalid",
            "error": "Invalid key format. OpenRouter keys must start with 'sk-or-v1-'"
        }

    # 2. Verify with OpenRouter API
    # We'll fetch models to verify the key and get available models
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {decrypted_key}",
                    "HTTP-Referer": "https://alphalab.io", # Required by OpenRouter
                    "X-Title": "AlphaLab"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract model IDs
                models = [model["id"] for model in data.get("data", [])]
                
                # Update DB status
                key.status = "valid"
                key.last_validated_at = func.now()
                await db.commit()
                
                return {
                    "valid": True,
                    "status": "valid",
                    "models_available": models[:10] # Return top 10 to avoid huge payload
                }
            elif response.status_code == 401:
                key.status = "invalid"
                await db.commit()
                return {
                    "valid": False,
                    "status": "invalid",
                    "error": "OpenRouter rejected the key (401 Unauthorized)"
                }
            else:
                # Other errors (rate limit, server error) - don't mark invalid, just return error
                return {
                    "valid": False,
                    "status": key.status, # Keep existing status
                    "error": f"Validation failed with status {response.status_code}"
                }
                
    except httpx.RequestError as e:
        return {
            "valid": False,
            "status": key.status,
            "error": f"Network error during validation: {str(e)}"
        }
