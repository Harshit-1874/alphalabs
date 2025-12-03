"""
Export domain model for data export jobs.

This module contains the model for user data export operations:
- Export: Tracks data export job status and provides download URLs
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    CheckConstraint, DECIMAL, ForeignKey, Index, 
    Integer, String, Text, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, TimestampMixin


class Export(Base, UUIDMixin, TimestampMixin):
    """
    Data export job tracking model.
    
    Tracks the status of user data export requests. When a user requests
    an export, a job is created with status "processing". A background task
    collects all requested data (agents, results, trades, settings) and
    packages it into a downloadable archive. Once complete, the download_url
    is populated and status changes to "ready".
    
    Export packages expire after a configurable time period (default 24 hours)
    to avoid storage bloat.
    
    Relationships:
    - user: Many-to-one with User (export owner)
    
    Example:
        export = Export(
            user_id=user.id,
            status="processing",
            progress_pct=0,
            format="zip"
        )
    """
    __tablename__ = "exports"
    __table_args__ = (
        Index('idx_exports_user', 'user_id'),
        Index('idx_exports_status', 'user_id', 'status'),
        Index('idx_exports_created', 'user_id', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed', 'expired')",
            name="check_export_status_values"
        ),
        CheckConstraint(
            "format IN ('json', 'zip')",
            name="check_export_format_values"
        ),
        CheckConstraint(
            "progress_pct BETWEEN 0 AND 100",
            name="check_progress_pct_range"
        ),
    )
    
    # Foreign Key
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who requested the export"
    )
    
    # Export Configuration
    format: Mapped[str] = mapped_column(
        String(10),
        server_default="zip",
        nullable=False,
        comment="Export format: 'json' or 'zip'"
    )
    
    # Job Status
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="processing",
        nullable=False,
        comment="Export job status: 'processing', 'ready', 'failed', or 'expired'"
    )
    
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Export generation progress percentage (0-100)"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Error message if export failed"
    )
    
    # Download Information
    download_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="URL to download the export package"
    )
    
    size_mb: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2),
        comment="Size of export package in megabytes"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Expiration timestamp for download URL"
    )
    
    # Relationship
    user: Mapped["User"] = relationship(
        "User",
        back_populates="exports"
    )
    
    def __repr__(self) -> str:
        return f"<Export(id={self.id}, user_id={self.user_id}, status={self.status}, progress={self.progress_pct}%)>"
