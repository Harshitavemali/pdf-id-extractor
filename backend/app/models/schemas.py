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


class ExtractResponse(BaseModel):
    success: bool = True
    records: list[ExtractedRecord] = Field(default_factory=list)


class DownloadExcelRequest(BaseModel):
    records: list[ExtractedRecord]


class HealthResponse(BaseModel):
    status: str
