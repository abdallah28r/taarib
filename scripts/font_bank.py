"""Glyph banks for engines without Unicode, font coverage, and DTE suggestions.

    python scripts/font_bank.py assign --text build.txt --original original.txt --seed work/font_bank.json
    python scripts/font_bank.py coverage --font Arabic.ttf --text build.txt
    python scripts/font_bank.py dte --text build.txt [--top 40]

Old engines (SCUMM, GrimE, PS1/PS2, some ports) draw one byte per character
from their own glyph sheet. `assign` gives every shaped Arabic form the build
uses (`arabic_shaping.glyphs_used` of the rendered text) a free byte: never a
byte the original text uses, never an engine command byte (0xFE/0xFF by
default). The seed file keeps the mapping fixed between builds, because save
states and older builds cache the font. `coverage` lists the shaped forms a
TTF lacks and whether the base letter can stand in (NFKC). `dte` counts the
most frequent character pairs, for engines whose text tables compress pairs
(dual-tile encoding), when the byte budget is tight.

`assign_bank` and `coverage` are adapted from `code/font_tools.py` of the
Arabic Game Localization Playbook (MXIAUDIO and contributors, MIT License;
notice in THIRD_PARTY_NOTICES.md). The DTE idea follows asgore-undertale's
Asgore Studio (ideas only, no code copied).
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path


def assign_bank(needed: list[str], used_bytes: set[int], start: int = 0x80,
                forbidden: tuple[int, ...] = (0xFE, 0xFF), extra_free: tuple[int, ...] = ()) -> dict[str, int]:
    """Single-byte slot for each needed character, in the order given (keep that order stable)."""
    free = [b for b in list(range(start, 0x100)) + list(extra_free) if b not in used_bytes and b not in forbidden]
    if len(needed) > len(free):
        raise SystemExit(f"need {len(needed)} slots, only {len(free)} free")
    return {char: free[i] for i, char in enumerate(needed)}


def coverage(font_path: Path, chars: set[str]) -> dict[str, str]:
    """{missing char: its single-letter NFKC base if the font has it, else '!'}."""
    from fontTools.ttLib import TTFont
    with TTFont(str(font_path), lazy=True) as font:
        cmap = set(font.getBestCmap())
    missing = {}
    for char in sorted(chars):
        if ord(char) in cmap or char.isspace():
            continue
        base = unicodedata.normalize("NFKC", char)
        missing[char] = base if len(base) == 1 and ord(base) in cmap else "!"
    return missing


def suggest_dte(text: str, top: int = 40) -> list[tuple[str, int]]:
    """Most frequent adjacent character pairs, spaces included, controls excluded."""
    pairs = Counter(a + b for a, b in zip(text, text[1:]) if a.isprintable() and b.isprintable())
    return pairs.most_common(top)


def _read(paths: list[Path]) -> str:
    return "".join(p.read_text(encoding="utf-8") for p in paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("assign", help="map the build's non-ASCII characters to free bytes")
    a.add_argument("--text", type=Path, nargs="+", required=True, help="rendered build text (UTF-8)")
    a.add_argument("--original", type=Path, nargs="*", default=[], help="original text whose bytes stay reserved")
    a.add_argument("--original-encoding", default="cp1252")
    a.add_argument("--start", type=lambda v: int(v, 0), default=0x80)
    a.add_argument("--forbid", default="FE,FF", help="engine command bytes, hex, comma-separated")
    a.add_argument("--seed", type=Path, required=True, help="JSON mapping kept between builds (created if missing)")
    c = sub.add_parser("coverage", help="shaped forms a TTF/OTF lacks")
    c.add_argument("--font", type=Path, required=True)
    c.add_argument("--text", type=Path, nargs="+", required=True)
    d = sub.add_parser("dte", help="most frequent character pairs")
    d.add_argument("--text", type=Path, nargs="+", required=True)
    d.add_argument("--top", type=int, default=40)
    args = parser.parse_args(argv)
    getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")

    if args.command == "assign":
        seed = json.loads(args.seed.read_text(encoding="utf-8")) if args.seed.is_file() else {}
        original = _read(args.original) if args.original else ""
        used = {b for b in original.encode(args.original_encoding, "ignore") if b > 0x7F}
        # A character the original text already draws (é, …, ™) keeps its own byte: no new slot.
        native = {ch for ch in original if ord(ch) > 0x7F}
        needed = sorted({ch for ch in _read(args.text) if ord(ch) > 0x7F and not ch.isspace()} - native)
        forbidden = tuple(int(x, 16) for x in args.forbid.split(",") if x)
        kept = {ch: int(b, 16) for ch, b in seed.items()}
        new = [ch for ch in needed if ch not in kept]
        bank = {**kept, **assign_bank(new, used | set(kept.values()), args.start, forbidden)}
        args.seed.write_text(json.dumps({ch: f"{b:02X}" for ch, b in sorted(bank.items(), key=lambda kv: kv[1])},
                                        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"BANK slots={len(bank)} new={len(new)} reserved_original={len(used)} -> {args.seed}")
        return 0
    if args.command == "coverage":
        missing = coverage(args.font, set(_read(args.text)))
        for char, base in missing.items():
            print(f"U+{ord(char):04X} {char} -> {'no fallback' if base == '!' else 'base ' + base}")
        print(f"MISSING={len(missing)} UNRECOVERABLE={sum(v == '!' for v in missing.values())}")
        return 1 if any(v == "!" for v in missing.values()) else 0
    for pair, count in suggest_dte(_read(args.text), args.top):
        print(f"{count}\t{pair!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
