"""Parse identity fields from a single TATU-style ID card text block."""

from __future__ import annotations

import re

from app.services.text_normalizer import normalize_pdf_text

HEADER_NOISE = re.compile(
    r"TELANGANA|AUTO\s*MOTOR|DRIVERS|TRADE\s*UNION|BRTU|TATU|"
    r"REGD\.?\s*NO|STATE\s*PRESIDENT|AFFILIATED",
    re.IGNORECASE,
)

PHONE_RE = re.compile(r"(?i)PH\s*No\s*[:\s.-]*([6-9]\d{9})")
PHONE_FALLBACK_RE = re.compile(r"\b([6-9]\d{9})\b")
AADHAAR_LABEL_RE = re.compile(r"(?i)Aadhaar\s*No\s*[:\s.-]*([\d\s]{12,20})")
AADHAAR_FALLBACK_RE = re.compile(r"\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b")
DL_LABEL_RE = re.compile(r"(?i)DL\s*No\s*[:\s.-]*([A-Z][A-Z0-9/-]{5,})")
STAND_RE = re.compile(
    r"(?i)Stand\s*[:\s.-]*(.+?)(?:\n|SL\s*No|PH\s*No|Aadhaar|DL\s*No|$)"
)
SL_NO_RE = re.compile(r"(?i)SL\s*No\.?\s*[:\s.-]*([A-Z0-9/-]+)")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" :-")


def _normalize_aadhaar(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 12:
        return _clean(value)
    return f"{digits[:4]} {digits[4:8]} {digits[8:]}"


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits if len(digits) == 10 else _clean(value)


def _extract_name_and_address(card_text: str) -> tuple[str, str]:
    before_fields = re.split(
        r"(?i)(?:PH\s*No|Aadhaar\s*No|DL\s*No|Stand\s*:)",
        card_text,
        maxsplit=1,
    )[0]

    lines = [
        _clean(line)
        for line in before_fields.splitlines()
        if _clean(line) and not HEADER_NOISE.search(line)
    ]

    lines = [
        line
        for line in lines
        if not re.match(r"(?i)(stand|sl\s*no|dl\s*no|ph\s*no|aadhaar)\b", line)
        and not re.fullmatch(r"[\d\s./-]+", line)
    ]

    if not lines:
        return "", ""

    # Name is usually the most uppercase short line.
    name_index = None
    for index, candidate in enumerate(lines):
        letters = [char for char in candidate if char.isalpha()]
        if not letters:
            continue
        upper_ratio = sum(char.isupper() for char in letters) / len(letters)
        word_count = len(candidate.split())
        if upper_ratio >= 0.65 and 1 <= word_count <= 6:
            name_index = index

    if name_index is None:
        name_index = 0 if len(lines) == 1 else max(0, len(lines) - 2)

    name = lines[name_index]
    address = ", ".join(lines[name_index + 1 :]) if name_index + 1 < len(lines) else ""

    name = re.sub(r"\.{2,}", ".", name).strip(" .")
    address = re.sub(r"\.{2,}", ".", address).strip(" .")
    address = re.sub(r",\s*,", ",", address)
    return name, address


def parse_card_fields(card_text: str, pdf_name: str) -> dict[str, str]:
    """Extract fields from one ID card text block."""
    text = normalize_pdf_text(card_text)

    phone_match = PHONE_RE.search(text)
    phone = _normalize_phone(phone_match.group(1)) if phone_match else ""
    if not phone:
        phone_fallback = PHONE_FALLBACK_RE.search(text)
        if phone_fallback:
            phone = _normalize_phone(phone_fallback.group(1))

    aadhaar_match = AADHAAR_LABEL_RE.search(text)
    aadhaar = ""
    if aadhaar_match:
        aadhaar = _normalize_aadhaar(aadhaar_match.group(1))
    else:
        fallback = AADHAAR_FALLBACK_RE.search(text)
        if fallback:
            aadhaar = _normalize_aadhaar(fallback.group(1))

    dl_match = DL_LABEL_RE.search(text)
    dl_number = _clean(dl_match.group(1)).upper() if dl_match else ""
    if dl_number in {"-", "—", "NA", "N/A", "STAND"}:
        dl_number = ""

    stand_match = STAND_RE.search(text)
    stand = _clean(stand_match.group(1)) if stand_match else ""

    sl_no = ""
    sl_match = SL_NO_RE.search(text)
    if sl_match:
        field_anchor = re.search(r"(?i)(?:PH\s*No|Stand\s*:)", text)
        if field_anchor and sl_match.start() >= field_anchor.start():
            sl_no = _clean(sl_match.group(1))

    name, address = _extract_name_and_address(text)

    return {
        "name": name,
        "address": address,
        "aadhaar": aadhaar,
        "dl_number": dl_number,
        "phone": phone,
        "stand": stand,
        "sl_no": sl_no,
        "pdf_name": pdf_name,
    }


def is_valid_record(record: dict[str, str]) -> bool:
    """Keep only real person rows (drop partial/orphan fragments)."""
    name = (record.get("name") or "").strip()
    if len(name) < 3:
        return False

    # Reject label-like "names".
    if re.fullmatch(r"(?i)(ph|aadhaar|aadhar|dl|stand|sl|no|name|address)", name):
        return False

    has_detail = any(
        (record.get(field) or "").strip()
        for field in ("address", "aadhaar", "dl_number", "phone", "stand")
    )
    return has_detail
