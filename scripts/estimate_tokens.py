"""Deterministically estimate source tokens and batch count before bulk work."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def estimate_text(text: str) -> int:
    """Conservative heuristic; provider tokenizers remain authoritative."""
    cjk = len(CJK_RE.findall(text))
    other = max(0, len(text) - cjk)
    return max(1, math.ceil(cjk / 1.5 + other / 3.5))


def read_sources(path: Path, source_column: str) -> list[str]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        if source_column not in (reader.fieldnames or []):
            raise ValueError(f"missing source column {source_column!r}")
        return [row.get(source_column, "") or "" for row in reader]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("table", type=Path)
    parser.add_argument("--source-column", default="source")
    parser.add_argument("--batch-source-tokens", type=int, default=4_000)
    parser.add_argument("--prompt-overhead", type=int, default=1_200)
    parser.add_argument("--output-ratio", type=float, default=1.35)
    args = parser.parse_args(argv)
    try:
        rows = read_sources(args.table, args.source_column)
    except (OSError, csv.Error, ValueError) as exc:
        print(f"ERROR {exc}")
        return 2
    source_tokens = sum(estimate_text(text) for text in rows)
    batches = max(1, math.ceil(source_tokens / max(1, args.batch_source_tokens)))
    report = {
        "rows": len(rows),
        "estimated_source_tokens": source_tokens,
        "estimated_output_tokens": math.ceil(source_tokens * args.output_ratio),
        "estimated_batches": batches,
        "estimated_prompt_overhead_tokens": batches * args.prompt_overhead,
        "batch_source_token_target": args.batch_source_tokens,
        "warning": "Heuristic planning estimate only; actual tokenizer and provider accounting may differ.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
