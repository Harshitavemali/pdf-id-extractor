"""Low-level PDF page access with pdfplumber."""

from pathlib import Path


def iter_pdf_pages(pdf_path: Path):
    """Yield pdfplumber page objects for a PDF."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            yield page
