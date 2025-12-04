"""
Certificate Service.

Purpose:
    Encapsulates business logic for managing certificates.
    Handles certificate generation, retrieval, verification, and PDF generation.

Data Flow:
    - Incoming: User ID, result ID, and certificate requests from API layer
    - Processing:
        - Validates test results are profitable
        - Generates unique verification codes
        - Creates certificate records in database
        - Manages certificate retrieval and verification
    - Outgoing: SQLAlchemy Certificate model instances returned to API layer
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime
from io import BytesIO
import secrets
import string

import qrcode

from models import Certificate, TestResult, Agent
from utils.storage import StorageClient
from utils.pdf_generator import PDFGenerator
from utils.image_generator import CertificateImageGenerator
from config import settings


class CertificateService:
    """Service for managing certificates."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the certificate service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self._storage = None  # Lazy initialization
        self.pdf_generator = PDFGenerator()
        self.image_generator = CertificateImageGenerator()
    
    @property
    def storage(self) -> StorageClient:
        """Lazy initialization of storage client."""
        if self._storage is None:
            self._storage = StorageClient()
        return self._storage
    
    async def generate_certificate(
        self, 
        user_id: UUID, 
        result_id: UUID,
        frontend_base_url: Optional[str] = None
    ) -> Certificate:
        """
        Generate a certificate for a test result.
        
        Validates that:
        - Result exists and belongs to user
        - Result is profitable
        - Certificate doesn't already exist for this result
        
        Args:
            user_id: ID of the user requesting certificate
            result_id: ID of the test result to certify
            
        Returns:
            Certificate: Newly created certificate
            
        Raises:
            ValueError: If result not found, not owned by user, not profitable,
                       or certificate already exists
        """
        # Fetch the test result with related data
        result = await self.db.execute(
            select(TestResult)
            .options(joinedload(TestResult.agent))
            .where(
                TestResult.id == result_id,
                TestResult.user_id == user_id
            )
        )
        test_result = result.scalar_one_or_none()
        
        if not test_result:
            raise ValueError("Test result not found or access denied")
        
        # Validate result is profitable
        if not test_result.is_profitable:
            raise ValueError("Cannot generate certificate for unprofitable result")
        
        # Check if certificate already exists
        existing_cert_result = await self.db.execute(
            select(Certificate).where(Certificate.result_id == result_id)
        )
        existing_cert = existing_cert_result.scalar_one_or_none()
        if existing_cert:
            # Certificate already exists, but update share_url if frontend_base_url is provided
            # This ensures the URL matches the current environment (localhost vs production)
            if frontend_base_url:
                new_share_url = self._build_share_url(existing_cert.verification_code, frontend_base_url)
                if existing_cert.share_url != new_share_url:
                    # Update the share URL to match current frontend
                    existing_cert.share_url = new_share_url
                    await self.db.commit()
                    await self.db.refresh(existing_cert)
            return existing_cert
        
        # Generate unique verification code
        verification_code = await self._generate_verification_code()
        
        # Format test period for display
        test_period = self._format_test_period(
            test_result.start_date,
            test_result.end_date
        )
        
        share_url = self._build_share_url(verification_code, frontend_base_url)
        
        # Create certificate record with cached data
        new_certificate = Certificate(
            result_id=result_id,
            user_id=user_id,
            verification_code=verification_code,
            agent_name=test_result.agent.name,
            model=test_result.agent.model,
            mode=test_result.mode,
            test_type=test_result.type,
            asset=test_result.asset,
            pnl_pct=test_result.total_pnl_pct,
            win_rate=test_result.win_rate,
            total_trades=test_result.total_trades,
            max_drawdown_pct=test_result.max_drawdown_pct,
            sharpe_ratio=test_result.sharpe_ratio,
            duration_display=test_result.duration_display or f"{test_result.duration_seconds}s",
            test_period=test_period,
            share_url=share_url,
            view_count=0
        )
        
        # Generate and upload assets
        pdf_bytes = self._build_pdf_bytes(
            agent_name=new_certificate.agent_name,
            model=new_certificate.model,
            mode=new_certificate.mode,
            test_type=new_certificate.test_type,
            asset=new_certificate.asset,
            pnl_pct=new_certificate.pnl_pct,
            win_rate=new_certificate.win_rate,
            total_trades=new_certificate.total_trades,
            max_drawdown_pct=new_certificate.max_drawdown_pct,
            sharpe_ratio=new_certificate.sharpe_ratio,
            duration_display=new_certificate.duration_display,
            test_period=new_certificate.test_period,
            verification_code=new_certificate.verification_code,
            share_url=new_certificate.share_url,
            issued_at=datetime.utcnow(),
        )
        image_bytes = self.image_generator.generate_certificate_image(
            agent_name=new_certificate.agent_name,
            model=new_certificate.model,
            mode=new_certificate.mode,
            test_type=new_certificate.test_type,
            asset=new_certificate.asset,
            pnl_pct=new_certificate.pnl_pct,
            win_rate=new_certificate.win_rate,
            total_trades=new_certificate.total_trades,
            max_drawdown_pct=new_certificate.max_drawdown_pct,
            sharpe_ratio=new_certificate.sharpe_ratio,
            duration_display=new_certificate.duration_display,
            test_period=new_certificate.test_period,
            verification_code=new_certificate.verification_code,
            share_url=new_certificate.share_url,
            issued_at=datetime.utcnow(),
        )
        qr_bytes = self._generate_qr_code(new_certificate.share_url)

        # Save certificate first to get the ID
        self.db.add(new_certificate)
        await self.db.commit()
        await self.db.refresh(new_certificate)
        
        # Now we have the certificate ID, build file paths
        asset_prefix = f"{new_certificate.user_id}/{new_certificate.id}"
        pdf_path = f"{asset_prefix}/certificate.pdf"
        image_path = f"{asset_prefix}/certificate.png"
        qr_path = f"{asset_prefix}/qr.png"

        # Upload files to storage
        pdf_url = await self.storage.upload_file(
            bucket=settings.CERTIFICATE_BUCKET,
            file_name=pdf_path,
            file_data=pdf_bytes,
            content_type="application/pdf",
            upsert=True,
        )
        image_url = await self.storage.upload_file(
            bucket=settings.CERTIFICATE_BUCKET,
            file_name=image_path,
            file_data=image_bytes,
            content_type="image/png",
            upsert=True,
        )
        qr_url = await self.storage.upload_file(
            bucket=settings.CERTIFICATE_BUCKET,
            file_name=qr_path,
            file_data=qr_bytes,
            content_type="image/png",
            upsert=True,
        )

        # Update certificate with storage URLs
        new_certificate.pdf_url = pdf_url
        new_certificate.image_url = image_url
        new_certificate.qr_code_url = qr_url
        
        await self.db.commit()
        await self.db.refresh(new_certificate)
        
        return new_certificate
    
    async def get_certificate(
        self, 
        certificate_id: UUID, 
        user_id: UUID
    ) -> Optional[Certificate]:
        """
        Get a certificate by ID with ownership validation.
        
        Args:
            certificate_id: ID of the certificate
            user_id: ID of the user requesting the certificate
            
        Returns:
            Certificate if found and owned by user, None otherwise
        """
        result = await self.db.execute(
            select(Certificate)
            .options(joinedload(Certificate.result))
            .where(
                Certificate.id == certificate_id,
                Certificate.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def verify_certificate(
        self, 
        verification_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Public verification of a certificate by verification code.
        
        This method is accessible without authentication and increments
        the view count each time it's called.
        
        Args:
            verification_code: Unique verification code (e.g., 'ALX-2025-1127-A3F8K')
            
        Returns:
            Dictionary with certificate data if found, None otherwise
        """
        # Fetch certificate by verification code
        result = await self.db.execute(
            select(Certificate).where(
                Certificate.verification_code == verification_code
            )
        )
        certificate = result.scalar_one_or_none()
        
        if not certificate:
            return None
        
        # Increment view count
        await self.db.execute(
            update(Certificate)
            .where(Certificate.id == certificate.id)
            .values(view_count=Certificate.view_count + 1)
        )
        await self.db.commit()
        
        # Return public certificate data (no sensitive information)
        return {
            "verified": True,
            "verification_code": certificate.verification_code,
            "agent_name": certificate.agent_name,
            "model": certificate.model,
            "mode": certificate.mode,
            "test_type": certificate.test_type,
            "asset": certificate.asset,
            "pnl_pct": float(certificate.pnl_pct),
            "win_rate": float(certificate.win_rate),
            "total_trades": certificate.total_trades,
            "max_drawdown_pct": float(certificate.max_drawdown_pct) if certificate.max_drawdown_pct else None,
            "sharpe_ratio": float(certificate.sharpe_ratio) if certificate.sharpe_ratio else None,
            "duration_display": certificate.duration_display,
            "test_period": certificate.test_period,
            "issued_at": certificate.issued_at.isoformat(),
            "view_count": certificate.view_count + 1,  # Include the incremented count
            "pdf_url": certificate.pdf_url,
            "image_url": certificate.image_url,
            "qr_code_url": certificate.qr_code_url
        }
    
    def build_pdf_for_certificate(self, certificate: Certificate) -> bytes:
        """Regenerate the certificate PDF for download endpoints."""
        return self.pdf_generator.generate_certificate(
            agent_name=certificate.agent_name,
            model=certificate.model,
            mode=certificate.mode,
            test_type=certificate.test_type,
            asset=certificate.asset,
            pnl_pct=certificate.pnl_pct,
            win_rate=certificate.win_rate,
            total_trades=certificate.total_trades,
            max_drawdown_pct=certificate.max_drawdown_pct,
            sharpe_ratio=certificate.sharpe_ratio,
            duration_display=certificate.duration_display,
            test_period=certificate.test_period,
            verification_code=certificate.verification_code,
            share_url=certificate.share_url,
            issued_at=certificate.issued_at,
        )
    
    def build_image_for_certificate(self, certificate: Certificate) -> bytes:
        """Regenerate the certificate PNG for download endpoints."""
        return self.image_generator.generate_certificate_image(
            agent_name=certificate.agent_name,
            model=certificate.model,
            mode=certificate.mode,
            test_type=certificate.test_type,
            asset=certificate.asset,
            pnl_pct=certificate.pnl_pct,
            win_rate=certificate.win_rate,
            total_trades=certificate.total_trades,
            max_drawdown_pct=certificate.max_drawdown_pct,
            sharpe_ratio=certificate.sharpe_ratio,
            duration_display=certificate.duration_display,
            test_period=certificate.test_period,
            verification_code=certificate.verification_code,
            share_url=certificate.share_url,
            issued_at=certificate.issued_at,
        )
    
    async def _generate_verification_code(self) -> str:
        """
        Generate a unique verification code.
        
        Format: ALX-YYYY-MMDD-XXXXX
        Where:
        - ALX: AlphaLab prefix
        - YYYY: Current year
        - MMDD: Current month and day
        - XXXXX: Random 5-character alphanumeric string (uppercase)
        
        Ensures uniqueness by checking against existing codes.
        
        Returns:
            str: Unique verification code
        """
        max_attempts = 10
        
        for _ in range(max_attempts):
            # Get current date components
            now = datetime.utcnow()
            year = now.strftime("%Y")
            month_day = now.strftime("%m%d")
            
            # Generate random 5-character suffix
            chars = string.ascii_uppercase + string.digits
            random_suffix = ''.join(secrets.choice(chars) for _ in range(5))
            
            # Construct verification code
            verification_code = f"ALX-{year}-{month_day}-{random_suffix}"
            
            # Check if code already exists
            result = await self.db.execute(
                select(Certificate).where(
                    Certificate.verification_code == verification_code
                )
            )
            
            if result.scalar_one_or_none() is None:
                return verification_code
        
        # If we couldn't generate a unique code after max_attempts
        raise RuntimeError("Failed to generate unique verification code")
    
    def _format_test_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> str:
        """
        Format test period for display.
        
        Args:
            start_date: Test start date
            end_date: Test end date
            
        Returns:
            str: Formatted period (e.g., "Jan 1 - Jan 31, 2025")
        """
        # If same year, show: "Jan 1 - Jan 31, 2025"
        if start_date.year == end_date.year:
            return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        
        # If different years, show: "Dec 15, 2024 - Jan 15, 2025"
        return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
    
    def _build_share_url(self, verification_code: str, frontend_base_url: Optional[str] = None) -> str:
        """
        Build the share URL for certificate verification.
        
        Args:
            verification_code: Unique verification code for the certificate
            frontend_base_url: Optional frontend base URL from request (e.g., http://localhost:3000)
                             If not provided, falls back to settings.CERTIFICATE_SHARE_BASE_URL
        
        Returns:
            Full URL to the verification page (e.g., http://localhost:3000/verify/abc123)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if frontend_base_url:
            base = frontend_base_url.rstrip("/")
            # Ensure it includes /verify path
            if not base.endswith("/verify"):
                base = f"{base}/verify"
            logger.info(f"Building share URL with frontend_base_url: {base}/{verification_code}")
        else:
            # Fallback to settings
            base = settings.CERTIFICATE_SHARE_BASE_URL.rstrip("/")
            logger.warning(f"Using fallback settings URL: {base}/{verification_code}")
        
        return f"{base}/{verification_code}"
    
    def _build_pdf_bytes(
        self,
        *,
        agent_name: str,
        model: str,
        mode: str,
        test_type: str,
        asset: str,
        pnl_pct,
        win_rate,
        total_trades,
        max_drawdown_pct,
        sharpe_ratio,
        duration_display: str,
        test_period: str,
        verification_code: str,
        share_url: str,
        issued_at: datetime,
    ) -> bytes:
        return self.pdf_generator.generate_certificate(
            agent_name=agent_name,
            model=model,
            mode=mode,
            test_type=test_type,
            asset=asset,
            pnl_pct=pnl_pct,
            win_rate=win_rate,
            total_trades=total_trades,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            duration_display=duration_display,
            test_period=test_period,
            verification_code=verification_code,
            share_url=share_url,
            issued_at=issued_at,
        )
    
    def _generate_qr_code(self, url: str) -> bytes:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#00D4FF", back_color="#0A0A0F")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
