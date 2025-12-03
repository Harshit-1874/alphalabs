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
import secrets
import string

from models import Certificate, TestResult, Agent


class CertificateService:
    """Service for managing certificates."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the certificate service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def generate_certificate(
        self, 
        user_id: UUID, 
        result_id: UUID
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
        existing_cert = await self.db.execute(
            select(Certificate).where(Certificate.result_id == result_id)
        )
        if existing_cert.scalar_one_or_none():
            raise ValueError("Certificate already exists for this result")
        
        # Generate unique verification code
        verification_code = await self._generate_verification_code()
        
        # Format test period for display
        test_period = self._format_test_period(
            test_result.start_date,
            test_result.end_date
        )
        
        # Create share URL (base URL should come from config)
        share_url = f"https://alphalab.io/verify/{verification_code}"
        
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
        
        self.db.add(new_certificate)
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
