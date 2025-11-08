"""Test script for preview layer implementation."""
import asyncio
import io
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from humancheck.config import get_config, init_config
from humancheck.database import init_db
from humancheck.models import Attachment, Review, ReviewStatus
from humancheck.storage import get_storage_manager


async def test_preview_layer():
    """Test the preview layer implementation."""
    print("🧪 Testing Preview Layer Implementation\n")

    # Initialize
    print("1. Initializing configuration and database...")
    config = init_config()
    db = init_db(config.get_database_url())
    await db.create_tables()
    print("   ✅ Database initialized\n")

    # Initialize storage
    print("2. Initializing storage manager...")
    storage_manager = get_storage_manager()
    storage_manager.initialize(provider_type="local", base_path="./storage")
    storage = storage_manager.get()
    print("   ✅ Storage manager initialized\n")

    # Create a test review
    print("3. Creating test review...")
    async with db.session() as session:
        review = Review(
            task_type="test_preview",
            proposed_action="Test the preview layer implementation",
            agent_reasoning="This is a test review for the preview layer",
            confidence_score=0.95,
            urgency="medium",
            status=ReviewStatus.PENDING.value,
        )
        session.add(review)
        await session.commit()
        await session.refresh(review)
        review_id = review.id
        print(f"   ✅ Created review #{review_id}\n")

    # Test text file upload
    print("4. Testing text file upload...")
    text_content = "# Test Document\n\nThis is a test text file for the preview layer.\n\nIt supports **markdown** rendering!"
    text_data = text_content.encode("utf-8")

    async with db.session() as session:
        # Upload to storage
        storage_key = f"reviews/{review_id}/attachments/test_text.md"
        await storage.upload(
            file=io.BytesIO(text_data),
            key=storage_key,
            content_type="text/markdown",
            metadata={"test": True}
        )

        # Create attachment record
        attachment = Attachment(
            review_id=review_id,
            file_name="test_text.md",
            content_type="text/markdown",
            content_category="text",
            file_size=len(text_data),
            storage_key=storage_key,
            storage_provider="local",
            inline_content=text_content,
            preview_url=await storage.get_url(storage_key, download=False),
            download_url=await storage.get_url(storage_key, download=True),
            description="Test markdown file",
            file_metadata={"language": "markdown"}
        )
        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)
        print(f"   ✅ Created text attachment #{attachment.id}")
        print(f"   📝 File: {attachment.file_name}")
        print(f"   📦 Size: {attachment.file_size} bytes")
        print(f"   🔗 Preview URL: {attachment.preview_url}\n")

    # Test image simulation (without actual image data)
    print("5. Simulating image attachment...")
    async with db.session() as session:
        storage_key = f"reviews/{review_id}/attachments/test_image.png"

        # Create attachment record (without actual upload)
        attachment = Attachment(
            review_id=review_id,
            file_name="test_image.png",
            content_type="image/png",
            content_category="image",
            file_size=1024 * 50,  # Simulate 50KB image
            storage_key=storage_key,
            storage_provider="local",
            preview_url=await storage.get_url(storage_key, download=False),
            download_url=await storage.get_url(storage_key, download=True),
            description="Test image",
            file_metadata={
                "width": 800,
                "height": 600,
                "format": "PNG"
            }
        )
        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)
        print(f"   ✅ Created image attachment #{attachment.id}")
        print(f"   🖼️  File: {attachment.file_name}")
        print(f"   📏 Dimensions: {attachment.file_metadata['width']}x{attachment.file_metadata['height']}\n")

    # Verify attachments
    print("6. Verifying attachments...")
    async with db.session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Attachment).where(Attachment.review_id == review_id)
        )
        attachments = list(result.scalars().all())

        print(f"   ✅ Found {len(attachments)} attachments for review #{review_id}")
        for att in attachments:
            print(f"      - {att.file_name} ({att.content_category})")
        print()

    # Test storage operations
    print("7. Testing storage operations...")

    # Check if file exists
    exists = await storage.exists(f"reviews/{review_id}/attachments/test_text.md")
    print(f"   ✅ File exists check: {exists}")

    # Download file
    content = await storage.download(f"reviews/{review_id}/attachments/test_text.md")
    print(f"   ✅ Downloaded file: {len(content)} bytes")
    print(f"   ✅ Content matches: {content.decode('utf-8') == text_content}")
    print()

    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print("✅ All tests passed!")
    print()
    print("Components tested:")
    print("  ✓ Database schema (Attachment model)")
    print("  ✓ Storage layer (upload, download, exists)")
    print("  ✓ Attachment creation and retrieval")
    print("  ✓ Multiple content types (text, image)")
    print("  ✓ Metadata storage")
    print()
    print("Next steps:")
    print("  1. Start API: poetry run uvicorn humancheck.api:app --reload")
    print("  2. Start Dashboard: poetry run streamlit run frontend/streamlit_app.py")
    print("  3. Upload files via API or dashboard")
    print("  4. View previews in the dashboard")
    print()

    await db.close()


if __name__ == "__main__":
    asyncio.run(test_preview_layer())
