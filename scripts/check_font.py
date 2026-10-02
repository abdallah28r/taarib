"""Check that a TTF/OTF font maps characters required by Arabic localization text."""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    parser.add_argument("--text-file", type=Path, help="UTF-8 localized text or export")
    parser.add_argument("--text", default="")
    args = parser.parse_args(argv)

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

    font = TTFont(args.font, lazy=True)
    cmap = set()
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

