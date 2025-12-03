"""
Export Schemas.

Purpose:
    Defines Pydantic models for data export creation and status tracking.
    Validates export requests and formats export job responses.

Data Flow:
    - Incoming: JSON payloads for creating export jobs with inclusion options.
    - Processing: Validates constraints and formats response data.
    - Outgoing: Structured data for the Export Service, and JSON responses for the API.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ExportCreate(BaseModel):
    """
    Schema for creating a new data export.
    
    Used when a user wants to export their data including agents,
    test results, trade history, and settings.
    """
    include: Dict[str, bool] = Field(
        default_factory=lambda: {
            "agents": True,
            "test_results": True,
            "trades": True,
            "settings": True,
            "reasoning_traces": False
        },
        description="Dictionary specifying which data types to include in the export"
    )
    format: str = Field(
        default="zip",
        description="Export format: 'json' or 'zip'"
    )


class ExportResponse(BaseModel):
    """
    Schema for export job status and download information.
    
    Contains all information needed to track export job progress
    and download the completed export package.
    """
    export_id: UUID = Field(
        ...,
        description="Unique identifier for the export job"
    )
    status: str = Field(
        ...,
        description="Export job status: 'processing', 'ready', 'failed'"
    )
    progress_pct: Optional[float] = Field(
        default=None,
        description="Export generation progress percentage (0-100)"
    )
    download_url: Optional[str] = Field(
        default=None,
        description="URL to download the export package (available when status is 'ready')"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the download URL expires"
    )
    size_mb: Optional[float] = Field(
        default=None,
        description="Size of the export package in megabytes"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is 'failed'"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the export job was created"
    )
    
    model_config = ConfigDict(from_attributes=True)
