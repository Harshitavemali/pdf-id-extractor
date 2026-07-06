from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import ExtractResponse
from app.services.extraction_service import extract_records_from_pdfs
from app.utils.file_helpers import cleanup_paths, save_uploads, validate_pdfs

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_pdfs(files: list[UploadFile] = File(...)) -> ExtractResponse:
    """Accept one or more PDFs and return extracted ID card records as JSON."""
    validate_pdfs(files)

    saved = await save_uploads(files)
    paths = [path for path, _ in saved]

    try:
        records = extract_records_from_pdfs(saved)
        if not records:
            raise HTTPException(
                status_code=422,
                detail="No ID card records could be extracted from the uploaded PDFs.",
            )
        return ExtractResponse(success=True, records=records)
    finally:
        cleanup_paths(paths)
