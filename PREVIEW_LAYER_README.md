# Preview Layer Implementation

This document describes the newly implemented preview layer for the Humancheck platform, which enables rich multi-modal content attachments for review requests.

## Overview

The preview layer adds the ability to attach files (images, videos, audio, documents, text) to review requests and preview them directly in the dashboard. This transforms Humancheck from a simple approval API into a comprehensive human-informed evaluation platform.

## Features Implemented

### 1. Database Schema (`src/humancheck/models.py`)

Added new `Attachment` model with the following features:
- File metadata (name, type, size, category)
- Storage information (key, provider)
- Preview URLs for different content types
- Security features (checksum, virus scanning placeholders)
- Relationship with Review model

### 2. Storage Abstraction Layer (`src/humancheck/storage/`)

**Files:**
- `base.py` - Abstract storage provider interface
- `local.py` - Local filesystem implementation
- `manager.py` - Storage manager for provider initialization

**Features:**
- Upload/download files
- Generate access URLs
- Delete files
- Check file existence
- Store metadata

**Extensibility:**
Ready for cloud storage providers (S3, GCS, Azure Blob) by implementing the `StorageProvider` interface.

### 3. REST API Endpoints (`src/humancheck/api.py`)

**New Endpoints:**

```
POST   /reviews/{review_id}/attachments     - Upload attachment
GET    /reviews/{review_id}/attachments     - List attachments
GET    /attachments/{attachment_id}         - Get attachment metadata
GET    /attachments/{attachment_id}/download - Download attachment
DELETE /attachments/{attachment_id}         - Delete attachment
```

**Features:**
- File validation and security checks
- Automatic content category detection
- Checksum calculation
- Filename sanitization
- Storage integration

### 4. Preview Components (`src/humancheck/dashboard/preview.py`)

**Supported Content Types:**
- **Text**: Syntax highlighting for code (Python, JavaScript, JSON, YAML, SQL, Markdown)
- **Images**: Full-resolution preview with metadata (dimensions, format, size)
- **Audio**: Audio player with waveform visualization placeholders
- **Video**: Video player with metadata (duration, resolution, codec)
- **Documents**: PDF viewer with page count

**Features:**
- Multi-attachment selector
- Content-specific rendering
- Metadata display
- Download functionality

### 5. Dashboard Integration (`frontend/streamlit_app.py`)

**Updates:**
- Added attachment fetching from database
- Integrated preview panel into review expander
- Shows attachment count badge
- Displays all attachments with appropriate previews

### 6. Security Validation (`src/humancheck/security/`)

**Files:**
- `content_validator.py` - File validation and security checks

**Security Features:**
- Content type validation (whitelist)
- File size limits by category
- Executable detection (PE, ELF headers)
- Script injection prevention in images
- Malicious PDF detection (JavaScript)
- Filename sanitization (path traversal prevention)
- Checksum calculation for integrity

**Size Limits:**
- Text: 10 MB
- Images: 50 MB
- Audio: 100 MB
- Video: 500 MB
- Documents: 100 MB

## Usage

### 1. Start the API Server

```bash
cd /Users/shashikumarp/sideprojects/humancheck
poetry run uvicorn humancheck.api:app --reload
```

### 2. Start the Dashboard

```bash
cd /Users/shashikumarp/sideprojects/humancheck
poetry run streamlit run frontend/streamlit_app.py
```

### 3. Upload Attachments via API

```bash
# Create a review first
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "document_review",
    "proposed_action": "Review attached document",
    "urgency": "medium"
  }'

# Upload an attachment (review_id from previous response)
curl -X POST http://localhost:8000/reviews/1/attachments \
  -F "file=@/path/to/document.pdf" \
  -F "description=Contract to review"
```

### 4. View in Dashboard

1. Navigate to http://localhost:8501
2. Find the review in the queue
3. Expand the review card
4. See the "Attachments" section with preview

## Architecture

```
┌─────────────────┐
│  Review Request │
└────────┬────────┘
         │
         ├─── Attachments ────┐
         │                     │
         │              ┌──────▼──────┐
         │              │ File Upload │
         │              └──────┬──────┘
         │                     │
         │              ┌──────▼──────────┐
         │              │ Security Check  │
         │              │ - Type validate │
         │              │ - Size check    │
         │              │ - Scan content  │
         │              └──────┬──────────┘
         │                     │
         │              ┌──────▼──────┐
         │              │   Storage   │
         │              │ (Local/S3)  │
         │              └──────┬──────┘
         │                     │
         │              ┌──────▼──────────┐
         │              │ Database Record │
         │              │ - Metadata      │
         │              │ - URLs          │
         │              │ - Checksum      │
         │              └──────┬──────────┘
         │                     │
         └─────────────────────┘
                               │
                        ┌──────▼────────┐
                        │ Preview Panel │
                        │ - Text viewer │
                        │ - Image view  │
                        │ - Media play  │
                        │ - PDF render  │
                        └───────────────┘
```

## File Structure

```
src/humancheck/
├── models.py                      # Added Attachment model
├── api.py                         # Added attachment endpoints
├── storage/
│   ├── __init__.py
│   ├── base.py                   # Storage provider interface
│   ├── local.py                  # Local storage implementation
│   └── manager.py                # Storage manager
├── security/
│   ├── __init__.py
│   └── content_validator.py      # File validation
└── dashboard/
    ├── __init__.py
    └── preview.py                # Preview components

frontend/
└── streamlit_app.py              # Updated with preview integration
```

## Database Migration

After implementing the preview layer, you need to update the database schema:

```bash
# The database will auto-create tables on startup
# Or manually trigger:
poetry run python -c "
from humancheck.config import get_config
from humancheck.database import init_db
import asyncio

config = get_config()
db = init_db(config.get_database_url())
asyncio.run(db.create_tables())
"
```

## Testing

### Test File Upload

```python
import requests

# Create review
response = requests.post("http://localhost:8000/reviews", json={
    "task_type": "content_review",
    "proposed_action": "Review the attached content",
    "urgency": "medium"
})
review_id = response.json()["id"]

# Upload text file
with open("test.txt", "rb") as f:
    response = requests.post(
        f"http://localhost:8000/reviews/{review_id}/attachments",
        files={"file": ("test.txt", f, "text/plain")},
        params={"description": "Test text file"}
    )
    print(response.json())

# Upload image
with open("image.png", "rb") as f:
    response = requests.post(
        f"http://localhost:8000/reviews/{review_id}/attachments",
        files={"file": ("image.png", f, "image/png")}
    )
    print(response.json())
```

## Security Considerations

### Implemented
- ✅ Content type validation (whitelist)
- ✅ File size limits
- ✅ Filename sanitization
- ✅ Executable detection
- ✅ Script injection prevention
- ✅ Basic malware detection

### To Implement (Production)
- [ ] Virus scanning integration (ClamAV, VirusTotal)
- [ ] Image metadata stripping (EXIF)
- [ ] PDF sanitization (remove JavaScript)
- [ ] Rate limiting on uploads
- [ ] Access control (user-based permissions)
- [ ] Signed URLs with expiration
- [ ] Content Security Policy headers
- [ ] Storage encryption at rest

## Future Enhancements

### Phase 2 Features
1. **Thumbnail Generation**
   - Generate thumbnails for images
   - Video frame capture
   - PDF first page preview

2. **Metadata Extraction**
   - Image dimensions, EXIF data
   - Video duration, codec info
   - Audio bitrate, sample rate
   - Document page count

3. **Background Processing**
   - Celery/RQ integration
   - Async thumbnail generation
   - Virus scanning queue
   - Video transcoding

4. **Advanced Preview**
   - Diff viewer for text files
   - Annotation tools
   - Side-by-side comparison
   - Zoom and pan for images

5. **Cloud Storage**
   - AWS S3 provider
   - Google Cloud Storage
   - Azure Blob Storage
   - Signed URL generation

## API Documentation

### Upload Attachment

```http
POST /reviews/{review_id}/attachments
Content-Type: multipart/form-data

file: <binary>
description: <string> (optional)
```

**Response:**
```json
{
  "id": 1,
  "review_id": 1,
  "file_name": "document.pdf",
  "content_type": "application/pdf",
  "content_category": "document",
  "file_size": 1048576,
  "storage_key": "reviews/1/attachments/uuid/document.pdf",
  "preview_url": "/api/attachments/download/...",
  "download_url": "/api/attachments/download/...",
  "checksum": "sha256...",
  "uploaded_at": "2025-01-06T12:00:00Z"
}
```

### List Attachments

```http
GET /reviews/{review_id}/attachments
```

**Response:**
```json
{
  "review_id": 1,
  "count": 2,
  "attachments": [...]
}
```

### Download Attachment

```http
GET /attachments/{attachment_id}/download?disposition=inline
```

**Query Parameters:**
- `disposition`: `inline` (preview) or `attachment` (download)

## Troubleshooting

### Issue: Files not uploading
- Check file size limits
- Verify content type is allowed
- Check storage directory permissions (`./storage/`)

### Issue: Preview not showing
- Ensure API server is running on port 8000
- Check browser console for CORS errors
- Verify attachment URLs are correct

### Issue: Database errors
- Run database migrations
- Check SQLAlchemy models are imported
- Verify foreign key constraints

## Support

For issues or questions:
1. Check the architecture document: `architecture/preview-layer-implementation.md`
2. Review the API logs
3. Check Streamlit console output

## License

Same as Humancheck project license.
