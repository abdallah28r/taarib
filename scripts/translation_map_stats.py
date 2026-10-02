"""Report coverage, duplicate keys, and conflicts in JSON translation maps."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def analyze(path: Path) -> dict:
    candidates = [path] if path.is_file() else sorted(path.rglob("*.json"))
    occurrences: dict[str, list[dict[str, str]]] = defaultdict(list)
    files, skipped, parse_errors = [], [], []
    raw_entries = empty_entries = 0

    for file in candidates:
        try:
            data = json.loads(file.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parse_errors.append({"file": str(file), "error": str(exc)})
            continue
        if not isinstance(data, dict) or not all(isinstance(k, str) for k in data):
            skipped.append({"file": str(file), "reason": "expected a top-level JSON object"})
            continue
        file_entries = 0
        for key, value in data.items():
            if value is None:
                value = ""
            if not isinstance(value, str):
                skipped.append({"file": str(file), "reason": f"non-string value at {key}"})
                continue
            file_entries += 1
            raw_entries += 1
            empty_entries += not value.strip()
            occurrences[key].append({"file": str(file), "value": value})
        files.append({"file": str(file), "entries": file_entries})

    conflicts = {}
    duplicate_key_occurrences = identical_duplicate_keys = 0
    for key, items in occurrences.items():
        if len(items) < 2:
            continue
        duplicate_key_occurrences += len(items) - 1
        if len({item["value"] for item in items}) == 1:
            identical_duplicate_keys += 1
        else:
            conflicts[key] = items

    summary = {
        "files": len(files),
        "raw_entries": raw_entries,
        "unique_keys": len(occurrences),
        "unique_nonempty": sum(any(item["value"].strip() for item in items) for items in occurrences.values()),
        "unique_with_arabic": sum(any(ARABIC.search(item["value"]) for item in items) for items in occurrences.values()),
        "empty_entries": empty_entries,
        "duplicate_key_occurrences": duplicate_key_occurrences,
        "identical_duplicate_keys": identical_duplicate_keys,
        "conflicting_keys": len(conflicts),
        "skipped_items": len(skipped),
        "parse_errors": len(parse_errors),
    }
    return {"files": files, "summary": summary, "conflicts": conflicts,
            "skipped": skipped, "parse_errors": parse_errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args(argv)
    result = analyze(args.path)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if args.json_path:
        args.json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["summary"]["files"]:
        return 2
    return 1 if result["summary"]["parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
