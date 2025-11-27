"""Attachment endpoints"""
import io
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.models.review import Review
from ...core.models.attachment import Attachment, ContentCategory
from ...core.security import validate_file
from ...core.security.content_validator import sanitize_filename
from ...core.file_storage import get_storage_manager
from ..dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_content_category(content_type: str) -> str:
    """Detect content category from MIME type."""
    if content_type.startswith("text/"):
        return ContentCategory.TEXT.value
    elif content_type.startswith("image/"):
        return ContentCategory.IMAGE.value
    elif content_type.startswith("audio/"):
        return ContentCategory.AUDIO.value
    elif content_type.startswith("video/"):
        return ContentCategory.VIDEO.value
    elif content_type == "application/pdf":
        return ContentCategory.DOCUMENT.value
    else:
        return ContentCategory.OTHER.value


@router.post("/reviews/{review_id}/attachments", status_code=201)
async def upload_attachment(
    review_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Query(None, description="Optional description"),
    session: AsyncSession = Depends(get_session),
):
    """Upload an attachment to a review."""
    try:
        # Check if review exists
        result = await session.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Detect content category
        content_category = _detect_content_category(file.content_type or "application/octet-stream")

        # Validate file
        is_valid, error, validation_metadata = validate_file(
            content,
            file.content_type or "application/octet-stream",
            content_category
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"File validation failed: {error}")

        # Get checksum from validation metadata
        checksum = validation_metadata.get("checksum")

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename or "unnamed")

        # Generate storage key
        storage_key = f"reviews/{review_id}/attachments/{uuid4()}/{safe_filename}"

        # Upload to storage
        storage = get_storage_manager().get()
        await storage.upload(
            file=io.BytesIO(content),
            key=storage_key,
            content_type=file.content_type or "application/octet-stream",
            metadata={"review_id": review_id, "file_name": safe_filename},
        )

        # Get URLs
        preview_url = await storage.get_url(storage_key, expires_in=3600, download=False)
        download_url = await storage.get_url(storage_key, expires_in=3600, download=True)

        # For text files, store inline content
        inline_content = None
        if content_category == ContentCategory.TEXT.value and file_size < 1024 * 1024:  # < 1MB
            inline_content = content.decode("utf-8", errors="replace")

        # Create attachment record
        attachment = Attachment(
            review_id=review_id,
            file_name=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            content_category=content_category,
            file_size=file_size,
            storage_key=storage_key,
            storage_provider="local",
            inline_content=inline_content,
            preview_url=preview_url,
            download_url=download_url,
            description=description,
            checksum=checksum,
            file_metadata={
                "original_filename": file.filename,
                "sanitized_filename": safe_filename,
                "upload_method": "api",
                "validation": validation_metadata,
            },
        )

        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)

        return attachment

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error uploading attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/{review_id}/attachments")
async def list_attachments(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """List all attachments for a review."""
    try:
        # Check if review exists
        result = await session.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        # Get attachments
        result = await session.execute(
            select(Attachment)
            .where(Attachment.review_id == review_id)
            .order_by(Attachment.uploaded_at.desc())
        )
        attachments = list(result.scalars().all())

        return {"review_id": review_id, "attachments": attachments, "count": len(attachments)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get attachment metadata."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        return attachment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    disposition: str = Query("inline", description="Content disposition: inline or attachment"),
    session: AsyncSession = Depends(get_session),
):
    """Download attachment file."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        # Download from storage
        storage = get_storage_manager().get()
        content = await storage.download(attachment.storage_key)

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(content),
            media_type=attachment.content_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{attachment.file_name}"',
                "Content-Length": str(len(content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete an attachment."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        # Delete from storage
        storage = get_storage_manager().get()
        await storage.delete(attachment.storage_key)

        # Delete from database
        await session.delete(attachment)
        await session.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

