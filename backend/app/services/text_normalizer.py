"""Normalize noisy PDF text (e.g. doubled characters)."""

from __future__ import annotations

import re


def collapse_doubled_characters(text: str) -> str:
    """Collapse text where letters were extracted twice (TTEELL -> TEL)."""
    if not text:
        return text

    letters = [char for char in text if char.isalpha()]
    if len(letters) < 8:
        return text

    double_count = sum(
        1
        for index in range(len(text) - 1)
        if text[index] == text[index + 1] and text[index].isalpha()
    )
    if double_count / len(letters) < 0.35:
        return text

    # Only collapse doubled letters. Never touch digits (Aadhaar/DL/SL/phone).
    collapsed: list[str] = []
    index = 0
    while index < len(text):
        if (
            index + 1 < len(text)
            and text[index] == text[index + 1]
            and text[index].isalpha()
        ):
            collapsed.append(text[index])
            index += 2
        else:
            collapsed.append(text[index])
            index += 1
    return "".join(collapsed)


def normalize_pdf_text(text: str) -> str:
    """Clean extracted PDF text for field parsing."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = collapse_doubled_characters(cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
