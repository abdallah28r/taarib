"""Merge localization CSVs after a game update using stable IDs and source text."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load(path: Path, id_column: str) -> tuple[list[dict], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or id_column not in reader.fieldnames or "source" not in reader.fieldnames:
            raise ValueError(f"{path}: requires {id_column!r} and 'source' columns")
        rows = list(reader)
    ids = [row[id_column] for row in rows]
    duplicates = sorted(ident for ident, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"{path}: duplicate IDs: {duplicates[:10]}")
    return rows, list(reader.fieldnames)


def merge(old_source: Path, new_source: Path, old_target: Path, id_column: str):
    old_src_rows, _ = load(old_source, id_column)
    new_rows, new_fields = load(new_source, id_column)
    old_tgt_rows, _ = load(old_target, id_column)
    old_src = {r[id_column]: r for r in old_src_rows}
    old_tgt = {r[id_column]: r for r in old_tgt_rows}
    output = []
    counts = {"unchanged": 0, "changed_source": 0, "changed_context": 0,
              "unapproved": 0, "new": 0, "removed": 0, "conflicts": 0}
    for row in new_rows:
        ident = row[id_column]
        prior_source = old_src.get(ident)
        prior_target = old_tgt.get(ident)
        merged = dict(row)
        merged.setdefault("target", "")
        merged["status"] = "new"
        merged["previous_target"] = ""
        context_fields = ("context", "note", "speaker", "scene")
        context_changed = bool(prior_source) and any(
            field in prior_source or field in row
            for field in context_fields
        ) and any((prior_source.get(field) or "") != (row.get(field) or "")
                  for field in context_fields)
        approved_context_changed = bool(prior_target) and any(
            field in prior_target and (prior_target.get(field) or "") != (row.get(field) or "")
            for field in context_fields)
        if prior_source and prior_source.get("source") != row.get("source"):
            merged["previous_target"] = (prior_target or {}).get("target", "")
            merged["target"] = ""
            merged["status"] = "review_source_changed"
            counts["changed_source"] += 1
        elif context_changed or approved_context_changed:
            merged["previous_target"] = (prior_target or {}).get("target", "")
            merged["target"] = ""
            merged["status"] = "review_context_changed"
            counts["changed_context"] += 1
        elif prior_source:
            old_text = (prior_target or {}).get("target", "")
            if old_text.strip() and (prior_target or {}).get("status", "").strip().lower() == "approved":
                merged["target"] = old_text
                merged["status"] = "carried"
                counts["unchanged"] += 1
            elif old_text.strip():
                merged["previous_target"] = old_text
                merged["target"] = ""
                merged["status"] = "review_unapproved"
                counts["unapproved"] += 1
            else:
                counts["new"] += 1
        else:
            counts["new"] += 1
        if prior_target and prior_source and prior_target.get("source") not in ("", prior_source.get("source")):
            merged["status"] = "conflict_old_target_source"
            merged["previous_target"] = prior_target.get("target", "")
            merged["target"] = ""
            counts["conflicts"] += 1
        output.append(merged)
    counts["removed"] = len(set(old_src) - {r[id_column] for r in new_rows})
    fields = list(dict.fromkeys(new_fields + ["target", "status", "previous_target"]))
    return output, fields, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_source", type=Path)
    parser.add_argument("new_source", type=Path)
    parser.add_argument("old_target", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--id-column", default="id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"ERROR output exists; use --force to replace it: {args.output}")
        return 2
    try:
        rows, fields, counts = merge(args.old_source, args.new_source, args.old_target, args.id_column)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    report = args.report or args.output.with_suffix(args.output.suffix + ".report.json")
    report.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))
    return 1 if counts["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
