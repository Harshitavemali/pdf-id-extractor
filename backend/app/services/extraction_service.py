"""Orchestrate multi-PDF ID card extraction."""

from pathlib import Path

from app.models.schemas import ExtractedRecord
from app.services.card_extractor import extract_records_from_page


def extract_records_from_pdf(pdf_path: Path, pdf_name: str) -> list[ExtractedRecord]:
    """Extract all ID card records from a single PDF."""
    import pdfplumber

    records: list[ExtractedRecord] = []
    seen_phones: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for fields in extract_records_from_page(page, pdf_name):
                phone = fields.get("phone") or ""
                name = (fields.get("name") or "").lower()
                key = (name, phone)

                if phone and phone in seen_phones:
                    continue
                if key in seen_keys:
                    continue

                if phone:
                    seen_phones.add(phone)
                seen_keys.add(key)
                records.append(ExtractedRecord(**fields))

    return records


def extract_records_from_pdfs(
    pdf_paths: list[tuple[Path, str]],
) -> list[ExtractedRecord]:
    """Extract records from many PDFs."""
    all_records: list[ExtractedRecord] = []

    for pdf_path, pdf_name in pdf_paths:
        all_records.extend(extract_records_from_pdf(pdf_path, pdf_name))

    return all_records
