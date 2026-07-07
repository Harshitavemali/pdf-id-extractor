from pydantic import BaseModel, Field


class ExtractedRecord(BaseModel):
    """A single identity record extracted from an ID card."""

    name: str = ""
    address: str = ""
    aadhaar: str = ""
    dl_number: str = ""
    phone: str = ""
    stand: str = ""
    sl_no: str = ""
    pdf_name: str = ""


class FileResult(BaseModel):
    """Per-PDF extraction outcome, so the UI can show which files worked."""

    pdf_name: str = ""
    record_count: int = 0
    success: bool = False
    message: str = ""


class ExtractResponse(BaseModel):
    success: bool = True
    records: list[ExtractedRecord] = Field(default_factory=list)
    file_results: list[FileResult] = Field(default_factory=list)


class DownloadExcelRequest(BaseModel):
    records: list[ExtractedRecord]


class HealthResponse(BaseModel):
    status: str