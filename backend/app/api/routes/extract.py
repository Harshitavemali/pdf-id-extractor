from fastapi import APIRouter, File, UploadFile

from app.models.schemas import ExtractResponse
from app.services.extraction_service import extract_records_from_pdfs
from app.utils.file_helpers import cleanup_paths, save_uploads, validate_pdfs

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_pdfs(files: list[UploadFile] = File(...)) -> ExtractResponse:
    """Accept one or more PDFs and return extracted ID card records as JSON.

    Each file's outcome is reported individually in `file_results` so the
    UI can show which specific PDFs succeeded or failed, instead of only
    a single pass/fail for the whole batch.
    """
    validate_pdfs(files)

    saved = await save_uploads(files)
    paths = [path for path, _ in saved]

    try:
        records, file_results = extract_records_from_pdfs(saved)
        return ExtractResponse(success=True, records=records, file_results=file_results)
    finally:
        cleanup_paths(paths)