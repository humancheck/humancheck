"""Content validation and security checks for file uploads."""
import hashlib
from typing import Tuple


# Allowed content types by category
ALLOWED_CONTENT_TYPES = {
    # Text
    "text/plain",
    "text/markdown",
    "text/html",
    "text/csv",
    "application/json",
    "application/xml",
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    # Video
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Maximum file sizes by category (in bytes)
MAX_FILE_SIZES = {
    "text": 10 * 1024 * 1024,  # 10 MB
    "image": 50 * 1024 * 1024,  # 50 MB
    "audio": 100 * 1024 * 1024,  # 100 MB
    "video": 500 * 1024 * 1024,  # 500 MB
    "document": 100 * 1024 * 1024,  # 100 MB
    "other": 50 * 1024 * 1024,  # 50 MB
}


def validate_content_type(content_type: str) -> Tuple[bool, str]:
    """
    Validate if content type is allowed.

    Args:
        content_type: MIME type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content_type:
        return False, "Content type is required"

    # Normalize content type (remove parameters like charset)
    normalized_type = content_type.split(";")[0].strip().lower()

    if normalized_type not in ALLOWED_CONTENT_TYPES:
        return False, f"Content type not allowed: {content_type}"

    return True, ""


def validate_file_size(file_size: int, category: str) -> Tuple[bool, str]:
    """
    Validate file size against limits.

    Args:
        file_size: Size of file in bytes
        category: Content category (text, image, audio, video, document, other)

    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size = MAX_FILE_SIZES.get(category, MAX_FILE_SIZES["other"])

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"File too large ({actual_mb:.2f} MB). Max size for {category}: {max_mb} MB"

    if file_size == 0:
        return False, "File is empty"

    return True, ""


def calculate_checksum(file_data: bytes) -> str:
    """
    Calculate SHA256 checksum of file.

    Args:
        file_data: File content as bytes

    Returns:
        SHA256 hexdigest
    """
    return hashlib.sha256(file_data).hexdigest()


def validate_file(
    file_data: bytes,
    declared_content_type: str,
    category: str,
    max_size: int = None,
) -> Tuple[bool, str, dict]:
    """
    Complete file validation including type, size, and checksum.

    Args:
        file_data: File content as bytes
        declared_content_type: Declared MIME type
        category: Content category
        max_size: Optional custom max size (overrides category default)

    Returns:
        Tuple of (is_valid, error_message, metadata_dict)
    """
    # Check declared content type
    valid, error = validate_content_type(declared_content_type)
    if not valid:
        return False, error, {}

    # Check file size
    file_size = len(file_data)

    if max_size:
        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File too large ({actual_mb:.2f} MB). Max size: {max_mb} MB", {}
    else:
        valid, error = validate_file_size(file_size, category)
        if not valid:
            return False, error, {}

    # Calculate checksum
    checksum = calculate_checksum(file_data)

    # Check for suspicious content (basic checks)
    suspicious, reason = check_suspicious_content(file_data, declared_content_type)
    if suspicious:
        return False, f"Suspicious content detected: {reason}", {}

    metadata = {
        "checksum": checksum,
        "validated_size": file_size,
        "validated": True,
    }

    return True, "", metadata


def check_suspicious_content(file_data: bytes, content_type: str) -> Tuple[bool, str]:
    """
    Check for suspicious content patterns.

    Args:
        file_data: File content as bytes
        content_type: Declared content type

    Returns:
        Tuple of (is_suspicious, reason)
    """
    # Check for executable signatures
    if file_data.startswith(b"MZ"):  # Windows executable
        return True, "Executable file detected"

    if file_data.startswith(b"\x7fELF"):  # Linux executable
        return True, "Executable file detected"

    # Check for script content in images
    if content_type.startswith("image/"):
        if b"<script" in file_data.lower() or b"javascript:" in file_data.lower():
            return True, "Script content in image"

    # Check for embedded executables in documents
    if content_type == "application/pdf":
        # Basic check for embedded JavaScript (PDFs can contain JS)
        # This is a simple check; production should use proper PDF parsing
        if b"/JavaScript" in file_data or b"/JS" in file_data:
            return True, "Potentially malicious PDF with JavaScript"

    # All checks passed
    return False, ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other issues.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove path separators and parent directory references
    filename = filename.replace("..", "").replace("/", "_").replace("\\", "_")

    # Remove non-alphanumeric characters except dots, dashes, and underscores
    filename = re.sub(r"[^\w\-.]", "_", filename)

    # Limit length
    if len(filename) > 255:
        # Keep extension
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")

    return filename
