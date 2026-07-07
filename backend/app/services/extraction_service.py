"""Orchestrate multi-PDF ID card extraction."""

import gc
from pathlib import Path

from app.models.schemas import ExtractedRecord, FileResult
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

            # pdfplumber caches each page's extracted objects/images in
            # memory and normally only releases them when the whole PDF
            # closes. These ID card sheets can have dozens of embedded
            # photos per page across many pages, so that cache adds up
            # fast on a memory-limited instance. Flush it as soon as we're
            # done with this page instead of waiting for the file to close.
            page.flush_cache()

    return records


def extract_records_from_pdfs(
    pdf_paths: list[tuple[Path, str]],
) -> tuple[list[ExtractedRecord], list[FileResult]]:
    """Extract records from many PDFs.

    Each PDF is processed independently: if one file is unreadable or
    yields nothing, it's reported as a failed FileResult rather than
    aborting the whole batch or silently dropping out of the response.
    """
    all_records: list[ExtractedRecord] = []
    file_results: list[FileResult] = []

    for pdf_path, pdf_name in pdf_paths:
        try:
            records = extract_records_from_pdf(pdf_path, pdf_name)
        except Exception as exc:  # noqa: BLE001 - report per-file, keep going
            file_results.append(
                FileResult(
                    pdf_name=pdf_name,
                    record_count=0,
                    success=False,
                    message=f"Could not read this file: {exc}",
                )
            )
            continue

        all_records.extend(records)
        file_results.append(
            FileResult(
                pdf_name=pdf_name,
                record_count=len(records),
                success=len(records) > 0,
                message=""
                if records
                else "No ID card records could be extracted from this PDF.",
            )
        )
        gc.collect()

    return all_records, file_results