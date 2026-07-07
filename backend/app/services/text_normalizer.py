"""Normalize noisy PDF text (e.g. doubled characters)."""

from __future__ import annotations

import re
from collections import Counter


def collapse_doubled_characters(text: str) -> str:
    """Collapse text where letters were extracted repeated (TTEELL -> TEL).

    Some PDFs render corrupted text as doubled letters (AA -> A), others as
    tripled or more (AAA -> A). This detects the actual repetition
    multiplier from letter runs (2x, 3x, ...) and divides each repeated
    run's length by it, rather than always collapsing to one character -
    collapsing straight to 1 would also destroy a *legitimate* repeated
    digit (e.g. a real '66' inside a phone number becomes /'6666'/ under 2x
    corruption; dividing by the multiplier restores '66', collapsing to 1
    would wrongly leave just '6').

    Letters are used to *detect* corruption and the multiplier (digits
    repeat too often in legitimate numbers to be a reliable signal on
    their own). But once a line is confirmed corrupted by its letter
    doubling density, the same rendering artifact affected its digits too,
    so the fix is applied to digit runs as well.
    """
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

    # Find the dominant repeat-run length among letters only, to use as
    # the divisor (e.g. 2 for AA->A style doubling, 3 for AAA->A tripling).
    run_lengths: list[int] = []
    index = 0
    while index < len(text):
        if text[index].isalpha():
            end = index
            while end + 1 < len(text) and text[end + 1] == text[index]:
                end += 1
            run_len = end - index + 1
            if run_len >= 2:
                run_lengths.append(run_len)
            index = end + 1
        else:
            index += 1

    if not run_lengths:
        return text
    multiplier = Counter(run_lengths).most_common(1)[0][0]
    if multiplier < 2:
        multiplier = 2

    def _shrink(match: re.Match) -> str:
        run = match.group(0)
        keep = max(1, len(run) // multiplier)
        return run[0] * keep

    return re.sub(r"([A-Za-z0-9])\1+", _shrink, text)


def normalize_pdf_text(text: str) -> str:
    """Clean extracted PDF text for field parsing."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse per line: a card can have some clean lines (name) and some
    # heavily-doubled lines (a corrupted 'Aadhaar No :' row) at once - a
    # whole-block density check would dilute the doubled line's own ratio
    # below the threshold and miss it.
    cleaned = "\n".join(collapse_doubled_characters(line) for line in cleaned.split("\n"))
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()