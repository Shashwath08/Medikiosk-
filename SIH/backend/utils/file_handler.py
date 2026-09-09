import re
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from backend.config import settings

def sanitize_filename(filename: str) -> str:
    """Removes path separators and dangerous characters from filenames."""
    # Strip paths
    base_name = Path(filename).name
    # Keep only alphanumeric, dash, dot, underscore
    clean = re.sub(r"[^\w\-.]", "_", base_name)
    return clean or "document"

async def save_uploaded_file(file: UploadFile) -> tuple[str, str, int]:
    """
    Validates and stores an uploaded document securely.
    Returns: (document_id, saved_file_path, file_size_bytes)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    # Validate Content Type
    content_type = file.content_type or ""
    if content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed types: PDF, JPEG, PNG, WEBP."
        )

    # Read content and enforce size limits
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    clean_name = sanitize_filename(file.filename)
    unique_filename = f"{document_id}_{clean_name}"
    target_path = Path(settings.UPLOAD_FOLDER) / unique_filename

    target_path.write_bytes(content)
    return document_id, str(target_path), file_size
