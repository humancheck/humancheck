"""Attachment model - moved from models.py"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.database import Base


class ContentCategory(str, Enum):
    """Category of attachment content."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class Attachment(Base):
    """File attachments for review requests."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # File metadata
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ContentCategory.OTHER.value, index=True
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes

    # Storage
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    storage_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local"
    )

    # Content (for small text/inline content)
    inline_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Preview URLs
    preview_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Additional metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Security
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    virus_scan_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    virus_scan_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, file_name='{self.file_name}', content_type='{self.content_type}')>"

