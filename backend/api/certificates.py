"""
Certificate Endpoints.

Purpose:
    Exposes RESTful API endpoints for Certificate operations.
    Acts as the interface between the frontend and the Certificate Service.

Data Flow:
    - Incoming: HTTP requests for certificate operations (Create, Read, Verify, Download).
    - Processing:
        - Authenticates user via Clerk (except for public verification).
        - Delegates business logic to CertificateService.
        - Handles HTTP errors (404 Not Found, 400 Bad Request).
    - Outgoing: JSON responses containing certificate details or PDF files to the client.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from dependencies import get_current_user
from services.certificate_service import CertificateService
from schemas.certificate_schemas import (
    CertificateCreate,
    CertificateResponse,
    CertificateVerifyResponse
)
from utils.pdf_generator import PDFGenerator
from models import User

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.post("/", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    certificate_data: CertificateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new certificate for a profitable test result.
    
    Validates that:
    - Result exists and belongs to the user
    - Result is profitable
    - Certificate doesn't already exist for this result
    
    Returns the created certificate with verification code and URLs.
    """
    service = CertificateService(db)
    
    try:
        certificate = await service.generate_certificate(
            user_id=current_user.id,
            result_id=certificate_data.result_id
        )
        return certificate
    except ValueError as e:
        # Handle business logic errors (unprofitable result, already exists, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate certificate: {str(e)}"
        )


@router.get("/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get certificate details by ID.
    
    Requires authentication and validates that the certificate
    belongs to the requesting user.
    """
    service = CertificateService(db)
    
    certificate = await service.get_certificate(
        certificate_id=certificate_id,
        user_id=current_user.id
    )
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )
    
    return certificate


@router.get("/{certificate_id}/pdf")
async def download_certificate_pdf(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the certificate as a PDF file.
    
    Generates the PDF on-the-fly using the certificate data.
    Returns the PDF as a downloadable file.
    """
    service = CertificateService(db)
    
    # Get certificate with ownership validation
    certificate = await service.get_certificate(
        certificate_id=certificate_id,
        user_id=current_user.id
    )
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )
    
    try:
        # Generate PDF
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generate_certificate(certificate)
        
        # Return PDF as downloadable file
        filename = f"certificate_{certificate.verification_code}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/verify/{verification_code}", response_model=CertificateVerifyResponse)
async def verify_certificate(
    verification_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint to verify a certificate by its verification code.
    
    Does NOT require authentication - anyone with the verification code
    can verify the certificate's authenticity.
    
    Increments the view count each time it's accessed.
    """
    service = CertificateService(db)
    
    certificate_data = await service.verify_certificate(verification_code)
    
    if not certificate_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found or invalid verification code"
        )
    
    return {
        "verified": True,
        "certificate": certificate_data
    }
