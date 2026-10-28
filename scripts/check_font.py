"""Check that a TTF/OTF font maps the characters Arabic text needs, and optionally shape a sample.

    python scripts/check_font.py <font> [--text-file <utf-8 text>] [--text "..."]   # cmap coverage (fontTools)
    python scripts/check_font.py <font> --shape [--text "..."]                       # HarfBuzz smoke test (uharfbuzz)

Neither proves the game uses this font or this renderer path.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path


SHAPE_SAMPLE = "العربية لا لغة رائعة 123 HP"


def shape(font_path: Path, text: str) -> int:
    try:
        import uharfbuzz as hb
    except ImportError:
        print("ERROR uharfbuzz is required: python -m pip install uharfbuzz")
        return 2
    font = hb.Font(hb.Face(font_path.read_bytes()))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)
    glyphs = [info.codepoint for info in buf.glyph_infos]
    missing = sum(1 for glyph in glyphs if glyph == 0)
    print(json.dumps({"font": str(font_path), "direction": buf.direction, "script": buf.script,
                      "characters": len(text), "glyphs": len(glyphs), "missing_glyphs": missing},
                     ensure_ascii=False))
    return 1 if missing else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    parser.add_argument("--text-file", type=Path, help="UTF-8 localized text or export")
    parser.add_argument("--text", default="")
    parser.add_argument("--shape", action="store_true", help="shape the text with HarfBuzz and count .notdef glyphs")
    args = parser.parse_args(argv)
    if args.shape:
        return shape(args.font, args.text or SHAPE_SAMPLE)

    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("ERROR fontTools is required: python -m pip install fonttools")
        return 2

    sample = args.text
    if args.text_file:
        sample += args.text_file.read_text(encoding="utf-8-sig")
    if not sample:
        sample = "ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأؤإئىةًٌٍَُِّْ،؛؟…٪٠١٢٣٤٥٦٧٨٩"

    cmap = set()
    with TTFont(args.font, lazy=True) as font:
        for table in font["cmap"].tables:
            if table.isUnicode():
                cmap.update(table.cmap)

    required = sorted({ord(ch) for ch in sample if not ch.isspace()})
    missing = [cp for cp in required if cp not in cmap]
    for cp in missing:
        print(f"MISSING U+{cp:04X} {chr(cp)} {unicodedata.name(chr(cp), 'UNKNOWN')}")
    print(f"FONT={args.font} REQUIRED={len(required)} MISSING={len(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

