"""Filter extracted strings into translation candidates with explicit reasons."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
PATH_RE = re.compile(r"(?:^[A-Za-z]:[\\/]|[/\\].+[/\\]|\.(?:png|jpg|ogg|wav|dll|exe|json|asset)$)", re.I)
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:/-]*$")
# Performance overlays and hardware readouts seen in screenshots, never game text.
COUNTER_RE = re.compile(r"^(?:FPS|CPU|GPU|RAM|VRAM|MS|TEMP)\b.*\d|\d\s*(?:FPS|MHz|GHz|MB|GB|°C|°F)(?!\w)", re.I)


def classify(text: str) -> tuple[bool, str]:
    value = text.strip()
    if len(value) < 2:
        return False, "too-short"
    letters = LETTER_RE.findall(value)
    digits = re.findall(r"\d", value)
    if len(digits) > len(letters):
        return False, "mostly-numeric"
    if len(letters) < 2:
        return False, "too-few-letters"
    if COUNTER_RE.search(value) and len(value.split()) <= 4:
        return False, "performance-counter"
    if PATH_RE.search(value) and not re.search(r"\s", value):
        return False, "path-or-filename"
    if IDENTIFIER_RE.fullmatch(value) and (
        "_" in value or "." in value
    ):
        return False, "probable-identifier"
    return True, "candidate"


def iter_lines(path: Path | None):
    stream = path.open("r", encoding="utf-8-sig") if path else sys.stdin
    try:
        for line in stream:
            yield line.rstrip("\r\n")
    finally:
        if path:
            stream.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        writer = csv.writer(output)
        writer.writerow(["text", "accepted", "reason"])
        for text in iter_lines(args.input):
            accepted, reason = classify(text)
            writer.writerow([text, str(accepted).lower(), reason])
    finally:
        if args.output:
            output.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
