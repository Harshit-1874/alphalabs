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
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from urllib.parse import urlparse

from database import get_db

logger = logging.getLogger(__name__)
from dependencies import get_current_user
from services.certificate_service import CertificateService
from schemas.certificate_schemas import (
    CertificateCreate,
    CertificateResponse,
    CertificateVerifyResponse
)
from models import User

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


def _extract_frontend_url(request: Request) -> Optional[str]:
    """
    Extract frontend base URL from request headers.
    
    Tries in order:
    1. X-Frontend-URL header (explicitly sent by frontend - most reliable)
    2. Origin header (for CORS requests)
    3. Referer header (fallback)
    4. Host header (constructs from request)
    
    Returns:
        Frontend base URL (e.g., "http://localhost:3000") or None
    """
    # Try X-Frontend-URL header first (explicitly sent by frontend)
    frontend_url = request.headers.get("X-Frontend-URL")
    if frontend_url:
        # Validate it's a proper URL
        try:
            parsed = urlparse(frontend_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
    
    # Try Origin header (for CORS requests)
    origin = request.headers.get("Origin")
    if origin:
        parsed = urlparse(origin)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    # Try Referer header
    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    # Try to construct from request URL (for same-origin requests)
    # This is less reliable but works if frontend and backend are on same domain
    host = request.headers.get("Host")
    if host:
        scheme = "https" if request.url.scheme == "https" else "http"
        # Check if it's the backend port (5000), if so try frontend port (3000)
        if ":5000" in host:
            host = host.replace(":5000", ":3000")
        return f"{scheme}://{host}"
    
    return None


@router.post("", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    certificate_data: CertificateCreate,
    request: Request,
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
    
    # Extract frontend URL from request
    frontend_base_url = _extract_frontend_url(request)
    
    # Log for debugging - show all headers to help debug
    logger.info(f"Request headers: Origin={request.headers.get('Origin')}, "
                f"Referer={request.headers.get('Referer')}, "
                f"X-Frontend-URL={request.headers.get('X-Frontend-URL')}, "
                f"Host={request.headers.get('Host')}")
    
    if frontend_base_url:
        logger.info(f"✓ Using frontend URL from request: {frontend_base_url}")
    else:
        logger.warning("✗ Could not extract frontend URL from request, falling back to settings")
        logger.warning(f"  Settings fallback: {settings.CERTIFICATE_SHARE_BASE_URL}")
    
    try:
        certificate = await service.generate_certificate(
            user_id=current_user.id,
            result_id=certificate_data.result_id,
            frontend_base_url=frontend_base_url
        )
        return certificate
    except ValueError as e:
        # Handle business logic errors (unprofitable result, already exists, etc.)
        error_message = str(e)
        logger.warning(
            f"Certificate creation failed for user {current_user.id}, "
            f"result {certificate_data.result_id}: {error_message}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
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
    
    if certificate.pdf_url:
        return RedirectResponse(
            url=certificate.pdf_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    
    try:
        pdf_bytes = certificate_service.build_pdf_for_certificate(certificate)
        filename = f"certificate_{certificate.verification_code}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(exc)}"
        )


@router.get("/{certificate_id}/image")
async def download_certificate_image(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a PNG preview of the certificate.
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
    
    if certificate.image_url:
        return RedirectResponse(
            url=certificate.image_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    
    try:
        image_bytes = service.build_image_for_certificate(certificate)
        filename = f"certificate_{certificate.verification_code}.png"
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(exc)}"
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
