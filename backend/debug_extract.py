from pathlib import Path

import pdfplumber

from app.services.card_extractor import (
    _card_box,
    _extract_name_address,
    _extract_stand,
    _pitch,
    _stand_anchors,
    _words_to_text,
)
from app.services.extraction_service import extract_records_from_pdf
from app.services.text_normalizer import normalize_pdf_text

pdf_path = Path(
    r"c:\Users\suloc\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm"
    r"\LocalState\sessions\0341AC50AF746F155114AA3CD69E006EEBC0EFB4\transfers"
    r"\2026-27\ASTA LAKSHMI ARCH TATU ID CARD.pdf"
)

records = extract_records_from_pdf(pdf_path, pdf_path.name)
print("count", len(records))
for r in records[:10]:
    print("-" * 70)
    print("name:", r.name)
    print("address:", r.address)
    print("stand:", repr(r.stand))

# Inspect stand/address text for a few cards on page 1
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words(x_tolerance=1, y_tolerance=1, use_text_flow=False) or []
    anchors = _stand_anchors(words)
    pitch_x, pitch_y = _pitch(anchors)
    for i, stand_xy in enumerate(anchors[:5]):
        box = _card_box(stand_xy, pitch_x, pitch_y, page.width, page.height)
        cropped = page.crop(box)
        card_words = cropped.extract_words(x_tolerance=1, y_tolerance=1, use_text_flow=False) or []
        text = normalize_pdf_text(
            cropped.extract_text(x_tolerance=1, y_tolerance=1) or _words_to_text(card_words)
        )
        name, address = _extract_name_address(card_words, text)
        stand = _extract_stand(
            card_words, text, float(cropped.width or 1), float(cropped.height or 1)
        )
        print("\n=== CARD", i + 1, "===")
        print("RAW TEXT:\n", text)
        print("stand words:", [w for w in card_words if "stand" in w["text"].lower() or "kothapet" in w["text"].lower() or "ashta" in w["text"].lower()])
        print("parsed stand:", repr(stand))
        print("parsed address:", repr(address))
