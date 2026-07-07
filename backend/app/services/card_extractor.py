"""Extract front-side TATU ID cards from real PDF layout."""

from __future__ import annotations

import re
from statistics import median

from app.services.text_normalizer import collapse_doubled_characters, normalize_pdf_text

HEADER_NOISE = re.compile(
    r"TELANGANA|AUTO\s*MOTOR|DRIVERS|TRADE\s*UNION|BRTU|TATU|TRSKV|"
    r"REGD|STATE\s*PRESIDENT|AFFILIATED|ID\s*CARD|VICE-?PRESIDENT|"
    r"UNION|RAADEE|UUNNIIOONN|^MEMBER$|^ADVISOR$|^TRAINEE$|"
    r"^SECRETARY$|^TREASURER$|^PRESIDENT$|^DESIG\s*:?.*",
    re.IGNORECASE,
)

BACKSIDE_MARKERS = re.compile(
    r"Issue\s*Date|Validity|VICE-?PRESIDENT|Banjara\s*Hills|"
    r"tatu\.union@gmail|Telangana\s*Bhavan|etaD|ytidilaV",
    re.IGNORECASE,
)

ADDRESS_HINTS = re.compile(
    r"(?i)\b("
    r"h\.?\s*no|plot\s*no|flat\s*no|black\s*no|bl\s*no|p\.?\s*no|"
    r"colony|nagar|road|street|hyd|hyderabad|saidabad|malakpet|"
    r"meerpet|saroor|uppal|khaja\s*bagh|bagh"
    r")\b|"
    r"\d{1,3}\s*[-/]\s*\d|"
    r"\d{6}"
)


def _center(item: dict) -> tuple[float, float]:
    return ((item["x0"] + item["x1"]) / 2, (item["top"] + item["bottom"]) / 2)


def _token(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text or "").lower()


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" :-.,")


def _label_hit(token: str, labels: set[str]) -> bool:
    return token in labels or any(token.startswith(label) for label in labels)


def _in_bbox(item: dict, bbox: dict[str, float], pad: float = 0) -> bool:
    cx, cy = _center(item)
    return (
        bbox["x0"] - pad <= cx <= bbox["x1"] + pad
        and bbox["top"] - pad <= cy <= bbox["bottom"] + pad
    )


def _is_doubled_garbage(line: str) -> bool:
    collapsed = collapse_doubled_characters(line)
    return len(collapsed) <= max(3, int(len(line) * 0.65))


def _is_backside_page(text: str) -> bool:
    if re.search(r"Issue\s*Date|\betaD\b|ytidilaV", text, re.IGNORECASE) and re.search(
        r"Validity|VICE-?PRESIDENT", text, re.IGNORECASE
    ):
        return True
    if BACKSIDE_MARKERS.search(text) and not re.search(r"\bStand\s*:", text, re.IGNORECASE):
        return True
    return False


def _stand_anchors(words: list[dict]) -> list[tuple[float, float]]:
    points = [_center(word) for word in words if _token(word["text"]) == "stand"]
    if len(points) < 2:
        return points

    xs = sorted(p[0] for p in points)
    ys = sorted(p[1] for p in points)
    x_gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1) if xs[i + 1] - xs[i] > 40]
    y_gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1) if ys[i + 1] - ys[i] > 40]
    pitch_x = median(x_gaps) if x_gaps else 170
    pitch_y = median(y_gaps) if y_gaps else 250
    radius = min(pitch_x, pitch_y) * 0.25

    kept: list[tuple[float, float]] = []
    for point in sorted(points, key=lambda item: (item[1], item[0])):
        if any(abs(point[0] - k[0]) <= radius and abs(point[1] - k[1]) <= radius for k in kept):
            continue
        kept.append(point)
    return kept


def _header_anchors(words: list[dict]) -> list[tuple[float, float]]:
    """Locate each card by its 'ID CARD' header when there's no Stand field.

    Some union templates (e.g. TRSKV/BRTU membership cards) never print a
    'Stand :' line, so `_stand_anchors` finds nothing. Those cards still
    print 'ID' immediately followed by 'CARD' at the top of every card, so
    we anchor on that pair instead.
    """
    id_words = sorted(
        (word for word in words if _token(word["text"]) == "id"),
        key=lambda word: (word["top"], word["x0"]),
    )
    card_words = [word for word in words if _token(word["text"]) == "card"]

    points: list[tuple[float, float]] = []
    for id_word in id_words:
        match = next(
            (
                card_word
                for card_word in card_words
                if abs(card_word["top"] - id_word["top"]) <= 4
                and 0 <= card_word["x0"] - id_word["x1"] <= 25
            ),
            None,
        )
        if match is None:
            continue
        points.append(((id_word["x0"] + match["x1"]) / 2, (id_word["top"] + match["bottom"]) / 2))
    return points


def _label_anchors(words: list[dict], label: str) -> list[tuple[float, float]]:
    """Anchor on a literal field label (e.g. 'Name' in 'Name : X') as a last resort.

    Some templates split 'ID CARD' into odd tokens (e.g. 'ID' / 'CA' / 'RD')
    so `_header_anchors` finds nothing either. Those cards still print an
    explicit 'Name :' label once per card, so anchor on that instead.
    """
    return [_center(word) for word in words if _token(word["text"]) == label]


def _header_card_box(
    anchor_xy: tuple[float, float],
    pitch_x: float,
    pitch_y: float,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """'ID CARD' header sits near the top-left of each card.

    These fractions are set from measured word extents on real cards, not
    guessed: a card's own text (name/address/phone/aadhaar/DL) can start
    left of its 'ID CARD' anchor and the *next* card's own field labels
    can start well left of *its* anchor too, so a too-wide box picks up
    the neighboring card's labels and values. These margins keep every
    card's own content while stopping short of the neighbor's.
    """
    ax, ay = anchor_xy
    x0 = max(0.0, ax - pitch_x * 0.47)
    x1 = min(page_width, ax + pitch_x * 0.52)
    top = max(0.0, ay - pitch_y * 0.15)
    bottom = min(page_height, ay + pitch_y * 0.68)
    return (x0, top, x1, bottom)


def _cluster_1d(values: list[float], tolerance: float) -> list[float]:
    if not values:
        return []
    ordered = sorted(values)
    clusters: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - clusters[-1][-1] <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [median(cluster) for cluster in clusters]


def _complete_grid(
    anchors: list[tuple[float, float]],
    pitch_x: float,
    pitch_y: float,
) -> list[tuple[float, float]]:
    if len(anchors) < 2:
        return anchors

    col_centers = _cluster_1d([a[0] for a in anchors], pitch_x * 0.4)
    row_centers = _cluster_1d([a[1] for a in anchors], pitch_y * 0.4)

    all_cols_seen_overall = {
        min(col_centers, key=lambda c: abs(c - x)) for x, _ in anchors
    }

    grid: list[tuple[float, float]] = []
    for row in row_centers:
        for col in all_cols_seen_overall:
            grid.append((col, row))

    kept: list[tuple[float, float]] = list(anchors)
    radius = min(pitch_x, pitch_y) * 0.25
    for point in sorted(grid, key=lambda item: (item[1], item[0])):
        if any(abs(point[0] - k[0]) <= radius and abs(point[1] - k[1]) <= radius for k in kept):
            continue
        kept.append(point)
    return kept


def _pitch(points: list[tuple[float, float]]) -> tuple[float, float]:
    if len(points) < 2:
        return 170.0, 250.0
    xs = sorted(p[0] for p in points)
    ys = sorted(p[1] for p in points)
    x_gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1) if xs[i + 1] - xs[i] > 40]
    y_gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1) if ys[i + 1] - ys[i] > 40]
    return (
        float(median(x_gaps)) if x_gaps else 170.0,
        float(median(y_gaps)) if y_gaps else 250.0,
    )


def _card_box(
    stand_xy: tuple[float, float],
    pitch_x: float,
    pitch_y: float,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """Stand sits near bottom-left of each card."""
    sx, sy = stand_xy
    # Extend left so house numbers / address prefixes are not clipped.
    x0 = max(0.0, sx - pitch_x * 0.22)
    x1 = min(page_width, sx + pitch_x * 0.78)
    top = max(0.0, sy - pitch_y * 0.78)
    bottom = min(page_height, sy + pitch_y * 0.08)
    return (x0, top, x1, bottom)


def _line_groups(words: list[dict], tolerance: float = 4) -> list[list[dict]]:
    if not words:
        return []
    words = sorted(words, key=lambda word: (word["top"], word["x0"]))
    lines: list[list[dict]] = []
    current: list[dict] = []
    current_top: float | None = None
    for word in words:
        if current_top is None or abs(word["top"] - current_top) <= tolerance:
            current.append(word)
            current_top = word["top"] if current_top is None else current_top
        else:
            lines.append(sorted(current, key=lambda item: item["x0"]))
            current = [word]
            current_top = word["top"]
    if current:
        lines.append(sorted(current, key=lambda item: item["x0"]))
    return lines


def _words_to_text(words: list[dict]) -> str:
    return "\n".join(" ".join(word["text"] for word in line) for line in _line_groups(words))


def _value_after_labels(
    words: list[dict],
    labels: set[str],
    stop_labels: set[str],
    max_extra_lines: int = 1,
) -> str:
    for word in words:
        token = _token(word["text"])
        if not _label_hit(token, labels):
            continue

        line_top = word["top"]
        collected: list[str] = []
        for other in words:
            if abs(other["top"] - line_top) > 7:
                continue
            if other["x0"] + 1 < word["x0"]:
                continue
            other_token = _token(other["text"])
            if _label_hit(other_token, labels) or other_token in {"no", "number", "num"}:
                continue
            if other["text"].strip() in {":", "-", "."}:
                continue
            if _label_hit(other_token, stop_labels) or other_token in stop_labels:
                break
            collected.append(other["text"])

        if max_extra_lines:
            extra = 0
            for line in _line_groups(words):
                if not line or line[0]["top"] <= line_top + 7:
                    continue
                if extra >= max_extra_lines:
                    break
                line_tokens = {_token(item["text"]) for item in line}
                if any(_label_hit(token, stop_labels | labels) for token in line_tokens):
                    break
                if any(HEADER_NOISE.search(item["text"]) for item in line):
                    break
                line_text = " ".join(item["text"] for item in line)
                if re.search(r"\d{6,}", line_text):
                    break
                collected.extend(item["text"] for item in line)
                extra += 1

        value = _clean(" ".join(collected))
        if value:
            return value
    return ""


def _extract_phone(words: list[dict], text: str) -> str:
    value = _value_after_labels(
        words,
        labels={"ph", "phone", "cell"},
        stop_labels={"aadhaar", "adhaar", "aadhar", "adhar", "dl", "stand", "sl"},
        max_extra_lines=0,
    )
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 10 and digits[-10] in "6789":
        return digits[-10:]

    match = re.search(r"(?i)(?:PH|Phone|Cell)\s*(?:No)?\s*[:\s.-]*([6-9]\d{9})", text)
    return match.group(1) if match else ""


def _format_aadhaar(digits: str) -> str:
    digits = re.sub(r"\D", "", digits)
    if len(digits) < 12:
        return ""
    digits = digits[:12]
    return f"{digits[:4]} {digits[4:8]} {digits[8:]}"


def _extract_aadhaar(words: list[dict], text: str) -> str:
    value = _value_after_labels(
        words,
        labels={"aadhaar", "adhaar", "aadhar", "adhar"},
        stop_labels={"ph", "phone", "dl", "stand", "sl"},
        max_extra_lines=1,
    )
    formatted = _format_aadhaar(value)
    if formatted:
        return formatted

    for word in words:
        if not _label_hit(_token(word["text"]), {"aadhaar", "adhaar", "aadhar", "adhar"}):
            continue
        nums: list[str] = []
        for other in sorted(words, key=lambda item: (item["top"], item["x0"])):
            if other["top"] < word["top"] - 2 or other["top"] > word["top"] + 28:
                continue
            if other["top"] <= word["top"] + 8 and other["x1"] < word["x0"]:
                continue
            part = re.sub(r"\D", "", other["text"])
            if part:
                nums.append(part)
        formatted = _format_aadhaar("".join(nums))
        if formatted:
            return formatted

    match = re.search(
        r"(?i)aadha?a?r\s*no\.?\s*[:\s.-]*((?:\d[\s\-.]*){12})",
        text,
    )
    if match:
        formatted = _format_aadhaar(match.group(1))
        if formatted:
            return formatted

    # Empty "Aadhaar No :" with no digits should stay blank.
    if re.search(r"(?i)aadha?a?r\s*no\.?\s*[:\s.-]*$", text, re.MULTILINE):
        # still try 4-4-4 elsewhere on card
        pass

    phones = set(re.findall(r"[6-9]\d{9}", text))
    for match in re.finditer(r"(\d{4})[\s\-.]+(\d{4})[\s\-.]+(\d{4})", text):
        digits = match.group(1) + match.group(2) + match.group(3)
        if any(phone.find(digits) >= 0 or digits.find(phone) >= 0 for phone in phones):
            continue
        formatted = _format_aadhaar(digits)
        if formatted:
            return formatted
    return ""


def _extract_dl(words: list[dict], text: str) -> str:
    value = _value_after_labels(
        words,
        labels={"dl"},
        stop_labels={"ph", "phone", "aadhaar", "adhaar", "aadhar", "adhar", "stand", "sl"},
        max_extra_lines=0,
    )
    value = _clean(value).upper().replace(" ", "")
    if value and value not in {"NO", "NUMBER", "STAND", "NA", "N/A", "ASHTA", "LAXMI"}:
        if re.match(r"^[A-Z0-9/-]{5,}$", value):
            return value

    match = re.search(r"(?i)DL\s*No\s*[:\s.-]*([A-Z0-9/-]{5,})", text)
    if not match:
        return ""
    value = _clean(match.group(1)).upper()
    if value.startswith("ASHTA") or "LAXMI" in value:
        return ""
    return value


def _extract_stand(words: list[dict], text: str, box: tuple[float, float, float, float]) -> str:
    """Extract Stand value (often two lines: ASHTA LAXMI ARCH + KOTHAPET)."""
    x0, top, x1, bottom = box
    card_height = bottom - top

    # Words in lower half of this card (page coordinates).
    lower_words = [
        word
        for word in words
        if x0 <= word["x0"] <= x1 and word["top"] >= top + card_height * 0.45
    ]
    spatial_value = ""
    if any(_token(word["text"]) == "stand" for word in lower_words):
        spatial_value = _value_after_labels(
            lower_words,
            labels={"stand"},
            stop_labels={"ph", "phone", "aadhaar", "adhaar", "aadhar", "adhar", "dl", "sl", "tatu"},
            max_extra_lines=2,
        )
        spatial_value = re.sub(r"(?i)\b(tatu|state|president)\b", " ", spatial_value)
        spatial_value = _clean(spatial_value)

    # Text fallback — Stand is commonly split across two lines.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text_value = ""
    for index, line in enumerate(lines):
        if not re.search(r"(?i)^(?:Auto\s*)?Stand\s*:", line):
            continue

        value = re.sub(r"(?i)^(?:Auto\s*)?Stand\s*:\s*", "", line).strip()
        if index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            continuation = next_line
            tatu_match = re.match(r"(?i)^T\s*A\s*T\s*U\s*(.+)$", next_line)
            if tatu_match:
                continuation = tatu_match.group(1).strip()
            if (
                continuation
                and not re.search(
                    r"(?i)^(PH|Aadhaar|Aadhar|Adhar|DL|SL|TATU|State|Regd|ID\s*CARD)",
                    continuation,
                )
                and not re.search(r"\d{10}", continuation)
                and re.search(r"[A-Za-z]", continuation)
            ):
                value = f"{value} {continuation}".strip()
        text_value = value
        break

    value = text_value if len(text_value) >= len(spatial_value) else spatial_value
    if not value and not re.search(r"(?i)\bStand\s*:", text):
        return ""

    value = re.sub(r"(?i)\b(tatu|state|president)\b", " ", value)
    parts = value.split()
    deduped: list[str] = []
    for part in parts:
        if re.fullmatch(r"(?i)tu|ta|tat|u|atu", part):
            continue
        if deduped and part.upper() == deduped[-1].upper():
            continue
        deduped.append(part)
    value = _clean(" ".join(deduped))
    return value if len(value) >= 5 else ""





def _is_sl_noise(line: str) -> bool:
    line = _clean(line)
    if re.fullmatch(r"(?i)[LS]", line):
        return True
    if re.fullmatch(r"(?i)[lL][sS]", line):
        return True
    if re.fullmatch(r"(?i)\.?oNl?", line):
        return True
    if re.fullmatch(r"(?i):?\s*oNl?", line):
        return True
    if re.search(r"(?i)\d+\.oNl?$", line):
        return True
    if re.search(r"(?i)\d+\.oN\s*[lL]\s*[sS]", line):
        return True
    if re.fullmatch(r"\d{2,3}-\d{2,3}", line):
        return True
    if re.fullmatch(r"\d{3,6}", line):
        return True
    return False


def _is_stand_fragment(line: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b(station|metro|d-?mart|mart|kothapet|ashta|asta|lakshmi|laxmi|arch)\b",
            line,
        )
    )


def _first_name_from_text(text: str) -> str:
    started = False
    for line in text.splitlines():
        cleaned = _clean(line)
        if not cleaned:
            continue
        if re.search(r"(?i)\bID\s*CARD\b", cleaned):
            started = True
            continue
        if not started:
            continue
        if _looks_like_name(cleaned) and not _is_stand_fragment(cleaned):
            return cleaned
        if _looks_like_address(cleaned):
            break
    return ""


def _sanitize_address(address: str) -> str:
    if not address:
        return ""
    address = re.sub(r"(?i),\s*\d+\.oNL?\s*,?", ",", address)
    address = re.sub(r"(?i),\s*\d+\.oN\s*L\s*S", "", address)
    address = re.sub(r"(?i),\s*TATU\s*,?", ",", address)
    address = re.sub(r"(?i)\bTATU\b", "", address)
    address = re.sub(r"(?i),\s*(?:\d{1,2}\s*,?\s*)?[LS]\s*,?\s*[LS]\s*$", "", address)
    address = re.sub(r",\s*,+", ",", address)
    return _clean(address.strip(" ,."))

def _looks_like_address(line: str) -> bool:
    line = _clean(line)
    if not line or _is_sl_noise(line):
        return False
    if ADDRESS_HINTS.search(line):
        return True
    if re.search(r"(?i)\bno\.?\s*[:\-]?\s*\d", line):
        return True
    return sum(char.isdigit() for char in line) >= 3


def _looks_like_name(line: str) -> bool:
    line = _clean(line)
    if len(line) < 3 or len(line) > 50:
        return False
    if _is_doubled_garbage(line) or _looks_like_address(line):
        return False
    if HEADER_NOISE.search(line):
        return False
    if re.search(r"(?i)\b(ph|aadhaar|adhaar|aadhar|adhar|dl|stand|sl|no|cell|office|state|president)\b", line):
        return False
    if re.search(r"\d", line):
        return False
    if re.search(r"\.oN\b|^\d+\.oN", line):
        return False
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 3:
        return False
    upper_ratio = sum(char.isupper() for char in letters) / len(letters)
    words = [part for part in re.split(r"[\s.]+", line) if part]
    return upper_ratio >= 0.55 and 1 <= len(words) <= 6


_LABELED_FIELD_STARTS = re.compile(
    r"(?i)^(desig|s/?o\.?\s*name|address|adhaar|aadhaar|aadhar|adhar|"
    r"phone|ph|state|dl)\b"
)


def _extract_labeled_fields(text: str) -> tuple[str, str]:
    """Parse templates with explicit 'Name :' / 'Address :' style labels.

    These don't follow the row/column card layout the spatial heuristic
    (`_extract_name_address`) expects, so they get their own simple,
    label-driven line scan instead.
    """
    name_parts: list[str] = []
    address_parts: list[str] = []
    mode: str | None = None

    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue

        match = re.match(r"(?i)^name\s*:\s*(.*)$", line)
        if match:
            name_parts = [match.group(1)] if match.group(1) else []
            mode = "name"
            continue

        match = re.match(r"(?i)^address\s*:\s*(.*)$", line)
        if match:
            address_parts = [match.group(1)] if match.group(1) else []
            mode = "address"
            continue

        if _LABELED_FIELD_STARTS.match(line) or HEADER_NOISE.search(line):
            mode = None
            continue

        if mode == "name" and _looks_like_name(line):
            name_parts.append(line)
        elif mode == "address":
            address_parts.append(line)

    name = _clean(" ".join(name_parts))
    address = _sanitize_address(_clean(", ".join(address_parts)))
    return name, address


def _extract_name_address(words: list[dict], text: str) -> tuple[str, str]:
    field_labels = {"ph", "phone", "aadhaar", "adhaar", "aadhar", "adhar", "dl", "stand", "sl", "no"}
    useful: list[str] = []

    for line in _line_groups(words, tolerance=5):
        joined = _clean(" ".join(word["text"] for word in line))
        if not joined:
            continue
        tokens = {_token(word["text"]) for word in line}
        if any(_label_hit(token, field_labels - {"no"}) for token in tokens):
            break
        if _is_doubled_garbage(joined) or HEADER_NOISE.search(joined):
            continue
        if _is_sl_noise(joined) or re.search(r"State President|^[LS]$", joined):
            continue
        if all(
            _token(word["text"]) in field_labels or word["text"] in {":", "-", "."}
            for word in line
        ):
            continue
        useful.append(joined)

    name_parts: list[str] = []
    address_parts: list[str] = []
    for line in useful:
        if _looks_like_address(line):
            address_parts.append(line)
            continue
        if _looks_like_name(line) and not address_parts:
            name_parts.append(line)
            continue
        if address_parts or name_parts:
            address_parts.append(line)

    name = _clean(" ".join(name_parts))
    address = _clean(", ".join(address_parts))

    if not name or _looks_like_address(name) or _is_stand_fragment(name):
        name = _first_name_from_text(text)
    if not name or _looks_like_address(name) or _is_stand_fragment(name):
        for line in text.splitlines():
            cleaned = _clean(line)
            if _looks_like_name(cleaned) and not _is_stand_fragment(cleaned):
                name = cleaned
                break

    name = re.sub(r"(?i)^name\s*:\s*", "", name).strip()
    address = re.sub(r"(?i)^(s/?o\.?\s*name|address)\s*:\s*", "", address).strip()
    address = re.sub(r"(?i),?\s*s/?o\.?(?:name)?\s*:\s*", ", ", address).strip(" ,")

    if name and name in address:
        address = _clean(address.replace(name, ""))

    # Text fallback keeps full address including H.No / Plot No prefixes.
    if name:
        match = re.search(
            rf"(?is){re.escape(name)}\s*(.*?)\s*(?=(?:PH|Phone)\s*No|Aadhaar\s*No|Adhaar\s*No|Aadhar\s*No|Adhar\s*No|DL\s*No|Stand\s*:)",
            text,
        )
        if match:
            fallback = _sanitize_address(_clean(match.group(1).replace("\n", ", ")))
            if len(fallback) > len(address):
                address = fallback

    return name, _sanitize_address(address)


YEAR_SL = {"2023", "2024", "2025", "2026"}


def _normalize_sl_digits(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 3 or digits in YEAR_SL:
        return ""
    return digits


def _reverse_sl_digits(value: str) -> str:
    digits = _normalize_sl_digits(value)
    if not digits:
        return ""
    return _normalize_sl_digits(digits[::-1])


def _parse_sl_from_text(text: str) -> str:
    """
    Parse SL No from card text or vertical glyph runs.

    Formats seen across PDFs:
      - SL No. 20010
      - 1002.oN / L / S  (reversed vertical)
      - 01812 : oNL S     (reversed vertical, colon variant)
      - S LNo :21810      (reversed column readout)
    """
    if not text:
        return ""

    for match in re.finditer(r"(?i)SL\s*No\.?\s*[:\s.-]*(\d{3,6})", text):
        sl = _normalize_sl_digits(match.group(1))
        if sl:
            return sl

    for match in re.finditer(r"(?i)S\s*L\s*No\s*:?\s*(\d{3,6})", text):
        sl = _normalize_sl_digits(match.group(1))
        if sl:
            return sl

    compact = re.sub(r"\s+", "", text)
    for source in (compact, compact[::-1]):
        match = re.search(r"(?i)slno\.?(\d{4,6})", source)
        if match:
            sl = _normalize_sl_digits(match.group(1))
            if sl:
                return sl

    colon_patterns = (
        r"(?is)([\d-]{3,10})\s*:?\s*\.?\s*oNl?\s*[lL]?\s*[sS]",
        r"(?is)([\d-]{3,10})\s*\n\s*:?\s*\.?\s*oNl?\s*\n?\s*[lL]?\s*[sS]",
        r"(?is)(\d{3,6})\s*:?\s*\.?oNl?\s*[lL]?\s*[sS]",
        r"(?is)(\d{3,6})\s*\n\s*:?\s*\.?oNl?\s*\n?\s*[lL]?\s*[sS]",
        r"(?is)(\d{4,6})\.oN\s*[lL]\s*[sS]",
        r"(?is)(\d{4,6})\.oNl?\s*[sS]",
    )
    for pattern in colon_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1)
            if "-" in raw:
                reversed_raw = raw[::-1]
                if re.fullmatch(r"\d{1,4}-\d{1,4}", reversed_raw):
                    return reversed_raw
            sl = _reverse_sl_digits(raw)
            if sl:
                return sl

    match = re.search(r"(\d{4,6})\.oNLS", compact, re.IGNORECASE)
    if match:
        sl = _reverse_sl_digits(match.group(1))
        if sl:
            return sl

    match = re.search(r"(?is)(\d?)\s*(\d{4})\.oN\s*L\s*S", text)
    if match:
        sl = _normalize_sl_digits((match.group(1) + match.group(2))[::-1])
        if sl:
            return sl

    rev = text[::-1]
    match = re.search(r"(?i)S\s*L\s*No\s*:?\s*(\d{3,6})", rev)
    if match:
        sl = _normalize_sl_digits(match.group(1))
        if sl:
            return sl

    return ""


def _extract_sl_no(
    page,
    box: tuple[float, float, float, float],
    stand_xy: tuple[float, float],
    pitch_x: float,
    pitch_y: float,
    card_text: str,
) -> str:
    # 1) From this card's text only (reversed vertical run).
    sl_no = _parse_sl_from_text(card_text)
    if sl_no:
        return sl_no

    # 2) Rotated glyphs in a narrow strip right of the photo for THIS card only.
    sx, sy = stand_xy
    zone = {
        "x0": sx + pitch_x * 0.32,
        "x1": sx + pitch_x * 0.82,
        "top": sy - pitch_y * 0.78,
        "bottom": sy - pitch_y * 0.18,
    }

    chars = [char for char in (page.chars or []) if _in_bbox(char, zone)]
    rotated = [char for char in chars if not char.get("upright", True)]
    use_chars = rotated if len(rotated) >= 3 else chars
    if not use_chars:
        return ""

    columns: dict[int, list[dict]] = {}
    for char in use_chars:
        columns.setdefault(int(round(char["x0"] / 3) * 3), []).append(char)

    texts: list[str] = []
    for column in sorted(columns.values(), key=len, reverse=True)[:4]:
        by_top = sorted(column, key=lambda item: item["top"])
        forward = re.sub(r"\s+", " ", _clean("".join(char["text"] for char in by_top)))
        backward = re.sub(r"\s+", " ", _clean("".join(char["text"] for char in reversed(by_top))))
        if forward:
            texts.extend([forward, forward[::-1]])
        if backward:
            texts.extend([backward, backward[::-1]])

    seen: set[str] = set()
    for text in texts:
        if text in seen:
            continue
        seen.add(text)
        sl_no = _parse_sl_from_text(text)
        if sl_no:
            return sl_no
    return ""



def _is_regular_grid(points: list[tuple[float, float]], tol_ratio: float = 0.25) -> bool:
    """Sanity-check that anchor points line up into a consistent grid.

    Used to prefer 'ID CARD' header anchors over 'Stand' anchors when a
    template's Stand/Auto-Stand field isn't laid out as cleanly (variable
    label width throws its x-position off from card to card), which would
    otherwise misplace every card's crop box.
    """
    if len(points) < 2:
        return False
    xs = sorted(p[0] for p in points)
    ys = sorted(p[1] for p in points)
    x_gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1) if xs[i + 1] - xs[i] > 40]
    y_gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1) if ys[i + 1] - ys[i] > 40]

    def _consistent(gaps: list[float]) -> bool:
        if not gaps:
            return True
        m = median(gaps)
        return m > 0 and all(abs(g - m) <= m * tol_ratio for g in gaps)

    return _consistent(x_gaps) and _consistent(y_gaps)


def extract_records_from_page(page, pdf_name: str) -> list[dict[str, str]]:
    words = page.extract_words(
        x_tolerance=1,
        y_tolerance=1,
        keep_blank_chars=False,
        use_text_flow=False,
    ) or []
    if not words:
        return []

    page_text = " ".join(word["text"] for word in words)
    if _is_backside_page(page_text):
        return []

    header_anchor_candidates = _header_anchors(words)
    stand_anchor_candidates = _stand_anchors(words)

    anchors = []
    anchor_mode = "stand"
    if stand_anchor_candidates and _is_regular_grid(stand_anchor_candidates):
        anchors = stand_anchor_candidates
        anchor_mode = "stand"
    elif len(header_anchor_candidates) >= 2:
        anchors = header_anchor_candidates
        anchor_mode = "header"
    elif stand_anchor_candidates:
        anchors = stand_anchor_candidates
        anchor_mode = "stand"
    if not anchors:
        anchors = header_anchor_candidates
        anchor_mode = "header"
    if not anchors:
        anchors = _label_anchors(words, "name")
        anchor_mode = "labeled"
    if not anchors:
        return []

    pitch_x, pitch_y = _pitch(anchors)
    anchors = _complete_grid(anchors, pitch_x, pitch_y)
    records: list[dict[str, str]] = []
    seen_phones: set[str] = set()

    for stand_xy in anchors:
        if anchor_mode == "stand":
            box = _card_box(stand_xy, pitch_x, pitch_y, page.width, page.height)
        elif anchor_mode == "labeled":
            box = _header_card_box(
                (stand_xy[0], stand_xy[1] - pitch_y * 0.15),
                pitch_x,
                pitch_y,
                page.width,
                page.height,
            )
        else:
            box = _header_card_box(stand_xy, pitch_x, pitch_y, page.width, page.height)
        try:
            cropped = page.crop(box)
        except Exception:
            continue

        card_words = cropped.extract_words(
            x_tolerance=1,
            y_tolerance=1,
            keep_blank_chars=False,
            use_text_flow=False,
        ) or []
        if len(card_words) < 4:
            continue

        text = normalize_pdf_text(
            cropped.extract_text(x_tolerance=1, y_tolerance=1) or _words_to_text(card_words)
        )
        if BACKSIDE_MARKERS.search(text):
            continue

        if anchor_mode == "labeled":
            name, address = _extract_labeled_fields(text)
        else:
            name, address = _extract_name_address(card_words, text)
        phone = _extract_phone(card_words, text)
        aadhaar = _extract_aadhaar(card_words, text)
        dl_number = _extract_dl(card_words, text)
        stand = _extract_stand(card_words, text, box)
        if anchor_mode == "stand":
            sl_no = _extract_sl_no(page, box, stand_xy, pitch_x, pitch_y, text)
        else:
            sl_no = _parse_sl_from_text(text)

        # One row per person card. Name is required; other fields may be blank.
        if not name:
            continue
        if _is_doubled_garbage(name) or HEADER_NOISE.search(name):
            continue

        name = re.sub(r"\s+[LS]$", "", name).strip()

        if phone and phone in seen_phones:
            continue
        if phone:
            seen_phones.add(phone)

        records.append(
            {
                "name": name,
                "address": address,
                "aadhaar": aadhaar,
                "dl_number": dl_number,
                "phone": phone,
                "stand": stand,
                "sl_no": sl_no,
                "pdf_name": pdf_name,
            }
        )

    return records