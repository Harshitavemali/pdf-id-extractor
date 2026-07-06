from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import DownloadExcelRequest
from app.services.excel_writer import write_drivers_excel

router = APIRouter()


@router.post("/download-excel")
async def download_excel(payload: DownloadExcelRequest) -> FileResponse:
    """Build Drivers.xlsx from provided records and return the file."""
    if not payload.records:
        raise HTTPException(status_code=400, detail="At least one record is required")

    excel_path = write_drivers_excel(payload.records, filename="Drivers.xlsx")

    return FileResponse(
        path=excel_path,
        filename="Drivers.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
