"""Report localization CSV coverage and duplication without modifying files."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def csv_files(path: Path):
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.csv"))


def analyze(path: Path) -> dict:
    rows = translated = unchanged = arabic = 0
    ids: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    files = []
    for file in csv_files(path):
        file_rows = file_translated = 0
        with file.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "source" not in reader.fieldnames:
                continue
            for row in reader:
                rows += 1
                file_rows += 1
                ident = (row.get("id") or row.get("key") or "").strip()
                source = row.get("source") or ""
                target = row.get("target") or ""
                if ident:
                    ids[ident] += 1
                sources[source] += 1
                if target.strip():
                    translated += 1
                    file_translated += 1
                    unchanged += target == source
                    arabic += bool(ARABIC.search(target))
        files.append({"file": str(file), "rows": file_rows, "translated": file_translated})
    return {
        "files": files,
        "summary": {
            "files": len(files),
            "rows": rows,
            "translated": translated,
            "untranslated": rows - translated,
            "coverage_percent": round(100 * translated / rows, 2) if rows else 0,
            "unique_source_strings": len(sources),
            "duplicate_source_rows": sum(n - 1 for n in sources.values() if n > 1),
            "duplicate_ids": sum(1 for n in ids.values() if n > 1),
            "unchanged_nonempty_targets": unchanged,
            "targets_with_arabic": arabic,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args(argv)
    result = analyze(args.path)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if args.json_path:
        args.json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["summary"]["files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

