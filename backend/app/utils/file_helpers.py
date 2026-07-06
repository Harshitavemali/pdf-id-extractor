import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


def validate_pdf(file: UploadFile) -> None:
    """Raise HTTPException if the upload is not an allowed PDF."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    extension = Path(file.filename).suffix.lower()
    if extension not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions_list)}",
        )


def validate_pdfs(files: list[UploadFile]) -> None:
    """Validate that at least one PDF was uploaded."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required")

    for file in files:
        validate_pdf(file)


async def save_upload(file: UploadFile) -> Path:
    """Persist an uploaded file under uploads/ and return its path."""
    extension = Path(file.filename or "upload.pdf").suffix.lower() or ".pdf"
    destination = settings.upload_path / f"{uuid.uuid4().hex}{extension}"

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    destination.write_bytes(content)
    return destination


async def save_uploads(files: list[UploadFile]) -> list[tuple[Path, str]]:
    """Save multiple uploads and return (path, original_filename) pairs."""
    saved: list[tuple[Path, str]] = []

    for file in files:
        path = await save_upload(file)
        saved.append((path, file.filename or path.name))

    return saved


def cleanup_paths(paths: list[Path]) -> None:
    """Delete temporary files if they still exist."""
    for path in paths:
        if path.exists():
            path.unlink()
