"""
API Key Schemas.

Purpose:
    Defines the Pydantic models for API Key creation, validation, and response serialization.
    Ensures that API key data adheres to expected formats before processing.

Data Flow:
    - Incoming: JSON payloads from the frontend (e.g., creating a new key).
    - Processing: Validates fields (e.g., key length, provider).
    - Outgoing: Structured Python objects for the API layer, and JSON responses back to the client.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class APIKeyBase(BaseModel):
    provider: str = "openrouter"
    label: Optional[str] = None
    is_default: Optional[bool] = False

class APIKeyCreate(APIKeyBase):
    api_key: str = Field(..., min_length=10, description="Raw API key")
    set_as_default: Optional[bool] = False

class APIKeyResponse(APIKeyBase):
    id: UUID
    key_prefix: Optional[str]
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class APIKeyListResponse(BaseModel):
    api_keys: List[APIKeyResponse]

class APIKeyValidationResponse(BaseModel):
    valid: bool
    status: str
    models_available: Optional[List[str]] = None
    error: Optional[str] = None
