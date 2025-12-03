"""
Certificate Schemas.

Purpose:
    Defines Pydantic models for certificate generation, retrieval, and verification.
    Validates certificate creation requests and formats certificate responses.

Data Flow:
    - Incoming: JSON payloads for creating certificates (result_id, options).
    - Processing: Validates constraints and formats response data.
    - Outgoing: Structured data for the Certificate Service, and JSON responses for the API.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class CertificateCreate(BaseModel):
    """
    Schema for creating a new certificate.
    
    Used when a user wants to generate a shareable certificate
    for a profitable test result.
    """
    result_id: UUID = Field(
        ...,
        description="ID of the test result to generate certificate for"
    )
    include_reasoning_trace: bool = Field(
        default=False,
        description="Whether to include AI reasoning traces in the certificate"
    )


class CertificateResponse(BaseModel):
    """
    Schema for certificate data returned to the user.
    
    Contains all information needed to display and share the certificate,
    including URLs for generated assets and verification details.
    """
    id: UUID
    result_id: UUID
    verification_code: str
    
    # Cached display data
    agent_name: str
    model: str
    mode: str
    test_type: str
    asset: str
    
    # Key metrics
    pnl_pct: Decimal
    win_rate: Decimal
    total_trades: int
    max_drawdown_pct: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    
    # Display strings
    duration_display: str
    test_period: str
    
    # Generated assets
    pdf_url: Optional[str] = None
    image_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    
    # Sharing
    share_url: str
    view_count: int
    
    # Timestamps
    issued_at: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyResponse(BaseModel):
    """
    Schema for public certificate verification response.
    
    Used by the public verification endpoint to confirm certificate
    authenticity and display basic information without requiring authentication.
    """
    verified: bool = Field(
        ...,
        description="Whether the certificate was found and is valid"
    )
    certificate: Optional[dict] = Field(
        default=None,
        description="Certificate data if verified (subset of fields for public display)"
    )
