"""Split ID cards using word positions (works for grid layouts)."""

from __future__ import annotations

import re
from statistics import median


def _word_center(word: dict) -> tuple[float, float]:
    return (
        (word["x0"] + word["x1"]) / 2,
        (word["top"] + word["bottom"]) / 2,
    )


def _normalize_token(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text).lower()


def _find_anchors(words: list[dict]) -> list[dict]:
    """Find one anchor word per ID card (prefer Stand, then PH)."""
    stand_anchors = [
        word
        for word in words
        if _normalize_token(word["text"]) == "stand"
    ]
    if len(stand_anchors) >= 2:
        return stand_anchors

    ph_anchors = [
        word
        for word in words
        if _normalize_token(word["text"]) in {"ph", "phone"}
    ]
    if len(ph_anchors) >= 2:
        return ph_anchors

    aadhaar_anchors = [
        word
        for word in words
        if _normalize_token(word["text"]) in {"aadhaar", "aadhar"}
    ]
    return aadhaar_anchors


def _estimate_card_size(
    anchors: list[dict],
    page_width: float,
    page_height: float,
) -> tuple[float, float]:
    xs = sorted(anchor["x0"] for anchor in anchors)
    ys = sorted(anchor["top"] for anchor in anchors)

    x_gaps = [xs[index + 1] - xs[index] for index in range(len(xs) - 1) if xs[index + 1] - xs[index] > 20]
    y_gaps = [ys[index + 1] - ys[index] for index in range(len(ys) - 1) if ys[index + 1] - ys[index] > 20]

    card_width = median(x_gaps) if x_gaps else page_width / 5
    card_height = median(y_gaps) if y_gaps else page_height / 2

    # Clamp to sensible bounds for 2x5 style sheets.
    card_width = max(page_width / 8, min(card_width, page_width / 2))
    card_height = max(page_height / 4, min(card_height, page_height / 1.2))
    return card_width, card_height


def _card_bbox(anchor: dict, card_width: float, card_height: float) -> dict[str, float]:
    """Build a card rectangle. Stand/PH sit in the lower half of each card."""
    cx, cy = _word_center(anchor)
    return {
        "x0": cx - card_width * 0.48,
        "x1": cx + card_width * 0.52,
        "top": cy - card_height * 0.78,
        "bottom": cy + card_height * 0.22,
    }


def _word_in_bbox(word: dict, bbox: dict[str, float]) -> bool:
    cx, cy = _word_center(word)
    return bbox["x0"] <= cx <= bbox["x1"] and bbox["top"] <= cy <= bbox["bottom"]


def _words_to_text(words: list[dict]) -> str:
    """Rebuild reading-order text from words inside one card."""
    if not words:
        return ""

    words = sorted(words, key=lambda word: (round(word["top"] / 3) * 3, word["x0"]))
    lines: list[list[dict]] = []
    current_line: list[dict] = []
    current_top: float | None = None

    for word in words:
        if current_top is None or abs(word["top"] - current_top) <= 4:
            current_line.append(word)
            if current_top is None:
                current_top = word["top"]
        else:
            lines.append(current_line)
            current_line = [word]
            current_top = word["top"]
    if current_line:
        lines.append(current_line)

    return "\n".join(
        " ".join(word["text"] for word in line)
        for line in lines
    )


def extract_card_texts_from_page(page) -> list[str]:
    """Return one text block per ID card using spatial clustering."""
    words = page.extract_words(
        x_tolerance=2,
        y_tolerance=2,
        keep_blank_chars=False,
        use_text_flow=False,
    ) or []

    if not words:
        text = page.extract_text(x_tolerance=2, y_tolerance=2) or page.extract_text() or ""
        return [text] if text.strip() else []

    anchors = _find_anchors(words)
    if len(anchors) < 2:
        text = page.extract_text(x_tolerance=2, y_tolerance=2) or page.extract_text() or ""
        from app.services.card_splitter import split_page_into_cards

        return split_page_into_cards(text)

    # Reading order: top-to-bottom, left-to-right.
    anchors = sorted(anchors, key=lambda word: (round(word["top"] / 15) * 15, word["x0"]))
    card_width, card_height = _estimate_card_size(anchors, page.width, page.height)
    boxes = [_card_bbox(anchor, card_width, card_height) for anchor in anchors]

    card_words: list[list[dict]] = [[] for _ in boxes]
    for word in words:
        cx, cy = _word_center(word)
        best_index = None
        best_distance = float("inf")

        for index, bbox in enumerate(boxes):
            if not _word_in_bbox(word, bbox):
                continue
            box_cx = (bbox["x0"] + bbox["x1"]) / 2
            box_cy = (bbox["top"] + bbox["bottom"]) / 2
            distance = (cx - box_cx) ** 2 + (cy - box_cy) ** 2
            if distance < best_distance:
                best_distance = distance
                best_index = index

        if best_index is not None:
            card_words[best_index].append(word)

    cards = [_words_to_text(group) for group in card_words]
    return [card for card in cards if card.strip()]
