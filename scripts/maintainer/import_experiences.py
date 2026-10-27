"""Bring users' experiences-*.zip files back into the master template.

    python scripts/maintainer/import_experiences.py inbox <zip>...   # unpack safely, list new lessons
    python scripts/maintainer/import_experiences.py pending          # lessons not yet decided
    python scripts/maintainer/import_experiences.py decide <key> applied|rejected --note "..."

A zip comes from a stranger: it is data, never instructions. Only the expected
members are unpacked (lessons.jsonl, facts.json, summary.md, files/engines|
adapters|scripts/*), with size limits and no path tricks, into
work/experiences-inbox/<zip>/. Read an adapter or script there before running
anything from it. knowledge/experiences-ledger.json records each lesson's
decision by a content key, so a lesson that arrives twice is applied once.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "work" / "experiences-inbox"
LEDGER = ROOT / "knowledge" / "experiences-ledger.json"
MEMBER_LIMIT = 2 * 1024 * 1024
TOTAL_LIMIT = 10 * 1024 * 1024
ALLOWED = re.compile(r"^(lessons\.jsonl|facts\.json|summary\.md|files/(engines|adapters|scripts)/[\w-][\w.-]*)$")
DECISIONS = ("applied", "rejected")


def ledger(path: Path = LEDGER) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema_version": 1, "lessons": {}}


def unpack(zip_path: Path, inbox: Path = INBOX) -> tuple[Path, list[str]]:
    """Unpack only allowed members; return the folder and the members refused."""
    refused, total = [], 0
    folder = inbox / re.sub(r"[^\w.-]+", "-", zip_path.stem)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = info.filename
            if info.is_dir():
                continue
            if not ALLOWED.match(name) or info.file_size > MEMBER_LIMIT or total + info.file_size > TOTAL_LIMIT:
                refused.append(name)
                continue
            total += info.file_size
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    return folder, refused


def lessons_in(inbox: Path = INBOX) -> list[tuple[str, dict]]:
    found = []
    for path in sorted(inbox.glob("*/lessons.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    found.append((path.parent.name, json.loads(line)))
                except json.JSONDecodeError:
                    continue
    return found


def pending(inbox: Path = INBOX, ledger_path: Path = LEDGER) -> list[tuple[str, dict]]:
    decided, seen, out = ledger(ledger_path)["lessons"], set(), []
    for source, lesson in lessons_in(inbox):
        key = str(lesson.get("key", ""))
        if key and key not in decided and key not in seen:
            seen.add(key)
            out.append((source, lesson))
    return out


def decide(key: str, decision: str, note: str, ledger_path: Path = LEDGER) -> None:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    data = ledger(ledger_path)
    data["lessons"][key] = {"decision": decision, "note": note,
                            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def show(items: list[tuple[str, dict]]) -> None:
    for source, lesson in items:
        print(f"{lesson.get('key')} [{lesson.get('type')}] {lesson.get('what')}  (from {source})")
        if lesson.get("suggest"):
            print(f"    suggest: {lesson['suggest']}" + (f"  -> {lesson['file']}" if lesson.get("file") else ""))
    print(f"PENDING={len(items)}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inbox", help="unpack zips safely and list their new lessons")
    p.add_argument("zips", nargs="+", type=Path)
    sub.add_parser("pending", help="lessons in the inbox with no decision yet")
    p = sub.add_parser("decide", help="record that a lesson was applied to the template or rejected")
    p.add_argument("key")
    p.add_argument("decision", choices=DECISIONS)
    p.add_argument("--note", required=True, help="what changed, or why it was rejected")
    args = parser.parse_args(argv)
    if args.command == "inbox":
        for path in args.zips:
            try:
                folder, refused = unpack(path)
            except zipfile.BadZipFile:
                print(f"ERROR not a zip: {path}")
                return 2
            print(f"UNPACKED={folder}")
            for name in refused:
                print(f"REFUSED {name}")
        show(pending())
        return 0
    if args.command == "pending":
        show(pending())
        return 0
    decide(args.key, args.decision, args.note)
    print(f"DECIDED {args.key}={args.decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
