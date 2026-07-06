"""Build Excel workbooks from extracted records."""

from pathlib import Path

from openpyxl import Workbook

from app.core.config import settings
from app.models.schemas import ExtractedRecord

EXCEL_HEADERS = [
    ("S.No", "s_no"),
    ("Name", "name"),
    ("Address", "address"),
    ("Aadhaar No", "aadhaar"),
    ("DL No", "dl_number"),
    ("Phone No", "phone"),
    ("Stand", "stand"),
    ("SL No", "sl_no"),
    ("PDF File Name", "pdf_name"),
]


def write_drivers_excel(
    records: list[ExtractedRecord],
    filename: str = "Drivers.xlsx",
) -> Path:
    """Write records to Drivers.xlsx and return its path."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Drivers"

    sheet.append([header for header, _ in EXCEL_HEADERS])

    for index, record in enumerate(records, start=1):
        data = record.model_dump()
        data["s_no"] = index
        sheet.append([data.get(field, "") for _, field in EXCEL_HEADERS])

    output_path = settings.output_path / filename
    workbook.save(output_path)
    return output_path
