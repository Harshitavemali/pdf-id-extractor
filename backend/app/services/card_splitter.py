"""Split a PDF page's text into individual ID card blocks."""

from __future__ import annotations

import re

from app.services.text_normalizer import normalize_pdf_text

PHONE_ANCHOR = re.compile(r"(?i)PH\s*No\s*:")
AADHAAR_ANCHOR = re.compile(r"(?i)Aadhaar\s*No\s*:")
CARD_TAIL = re.compile(r"(?i)(?:Stand\s*:.*(?:\n\s*SL\s*No\.?\s*:?\s*\S+)?)")


def split_page_into_cards(page_text: str) -> list[str]:
    """Split page text into one block per ID card."""
    text = normalize_pdf_text(page_text)
    if not text:
        return []

    # Prefer PH No as the per-card anchor (one phone label per card).
    anchors = list(PHONE_ANCHOR.finditer(text))
    if not anchors:
        anchors = list(AADHAAR_ANCHOR.finditer(text))
    if not anchors:
        return [text]

    cards: list[str] = []
    for index, match in enumerate(anchors):
        end = anchors[index + 1].start() if index + 1 < len(anchors) else len(text)

        if index == 0:
            start = max(0, match.start() - 180)
        else:
            prev_start = anchors[index - 1].start()
            between = text[prev_start : match.start()]
            stand_matches = list(CARD_TAIL.finditer(between))
            if stand_matches:
                start = prev_start + stand_matches[-1].end()
            else:
                start = max(prev_start, match.start() - 180)

        card_text = text[start:end].strip()
        if card_text:
            cards.append(card_text)

    return cards
