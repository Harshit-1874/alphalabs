"""
Export Endpoints.

Purpose:
    Exposes RESTful API endpoints for Data Export operations.
    Acts as the interface between the frontend and the Export Service.

Data Flow:
    - Incoming: HTTP requests for creating and checking export jobs.
    - Processing:
        - Authenticates user via Clerk.
        - Delegates business logic to ExportService.
        - Handles HTTP errors (404 Not Found, 400 Bad Request).
    - Outgoing: JSON responses containing export job status and download information.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from dependencies import get_current_user
from services.export_service import ExportService
from schemas.export_schemas import (
    ExportCreate,
    ExportResponse
)
from models import User

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    export_data: ExportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new data export job.
    
    Initiates an export job that will collect and package the user's data
    based on the specified inclusions. The export is generated asynchronously
    in the background.
    
    Request Body:
    - include: Dictionary specifying what data to include:
        - agents: Include agent configurations (default: true)
        - test_results: Include test results (default: true)
        - trades: Include trade history (default: true)
        - settings: Include user settings (default: true)
        - reasoning_traces: Include AI reasoning logs (default: false)
    - format: Export format - 'json' or 'zip' (default: 'zip')
    
    Returns the export job ID and initial status. Use GET /api/export/{id}
    to check the status and get the download URL when ready.
    """
    service = ExportService(db)
    
    try:
        # Create export job
        export_job = await service.create_export(
            user_id=current_user.id,
            include=export_data.include,
            format=export_data.format
        )
        
        # Queue background task to generate the export package
        export_id = UUID(export_job['export_id'])
        background_tasks.add_task(
            service.generate_export_package,
            export_id
        )
        
        # Return initial status
        return ExportResponse(
            export_id=export_id,
            status=export_job['status'],
            progress_pct=export_job['progress_pct'],
            download_url=None,
            expires_at=None,
            size_mb=None,
            error_message=None,
            created_at=export_job['created_at']
        )
    except ValueError as e:
        # Handle validation errors (invalid format, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create export job: {str(e)}"
        )


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export_status(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status of an export job.
    
    Returns the current status of the export job including:
    - Status: 'processing', 'ready', or 'failed'
    - Progress percentage (0-100)
    - Download URL (when status is 'ready')
    - Expiration timestamp (when status is 'ready')
    - File size in MB (when status is 'ready')
    - Error message (when status is 'failed')
    
    Validates that the export job belongs to the requesting user.
    """
    service = ExportService(db)
    
    try:
        export_status = await service.get_export_status(
            export_id=export_id,
            user_id=current_user.id
        )
        
        if not export_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found or does not belong to user"
            )
        
        # Convert to response model
        return ExportResponse(
            export_id=UUID(export_status['export_id']),
            status=export_status['status'],
            progress_pct=export_status['progress_pct'],
            download_url=export_status['download_url'],
            expires_at=export_status['expires_at'],
            size_mb=export_status['size_mb'],
            error_message=export_status.get('error'),
            created_at=export_status['created_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve export status: {str(e)}"
        )
