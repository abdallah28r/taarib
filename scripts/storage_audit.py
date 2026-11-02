"""Report storage use in a template copy; clean only verified template-owned temporary files.

    python scripts/storage_audit.py report <project-root> [--json]
    python scripts/storage_audit.py clean-temp <project-root>
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path

import patch_v3
import review_pages
import original_store
from storage_core import digest, is_link, no_link_components


def category(rel: Path, root: Path, original_records: dict) -> str:
    parts = [part.casefold() for part in rel.parts]
    if parts[:2] == ["backups", "originals"]:
        if parts == ["backups", "originals", "manifest.json"] and original_records:
            return "original-store-metadata"
        if parts[:3] == ["backups", "originals", "files"]:
            name = Path(*rel.parts[3:]).as_posix()
            expected = original_records.get(name, {}).get("sha256")
            if isinstance(expected, str) and digest(root / rel) == expected:
                return "verified-originals"
        return "original-store-unknown"
    if parts[:2] in (["backups", ".transactions"], ["backups", ".byte-patch"],
                     [".install-state", "pending"]):
        return "recoverable-transaction"
    if parts[:1] == [".tools"]:
        return "tools"
    if parts[:3] == ["work", "images", "preview"]:
        path = root / rel
        sidecar = path if path.suffix.casefold() == ".json" else path.with_suffix(".json")
        try:
            marker = json.loads(sidecar.read_text(encoding="utf-8"))
            if marker.get("owner") == "taarib-preview-v1" and not is_link(sidecar):
                if path == sidecar or (path.suffix.casefold() == ".png" and
                                       isinstance(marker.get("preview_sha256"), str)):
                    return "template-preview"
        except (OSError, ValueError, TypeError):
            pass
        return "preview-unknown"
    if parts[:1] in (["builds"], ["build"], ["releases"]):
        return "build-or-release"
    if parts[:2] == ["work", "images"]:
        return "image-work"
    if parts[:1] == ["work"]:
        return "work-unknown"
    if parts[:1] == ["reports"]:
        return "reports-unknown"
    if parts[:1] == ["backups"]:
        return "legacy-or-unknown-backup"
    return "other-or-unknown"


def report(root: Path) -> dict:
    no_link_components(root)
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root missing: {root}")
    categories: dict[str, dict[str, int]] = defaultdict(lambda: {"bytes": 0, "files": 0})
    folders: dict[str, dict[str, int]] = defaultdict(lambda: {"bytes": 0, "files": 0})
    links: list[str] = []
    try:
        original_records = original_store.load(root)["files"]
    except (OSError, ValueError, TypeError, KeyError):
        original_records = {}
    legacy_candidates: list[tuple[int, str]] = []
    legacy_count = 0
    stack = [root]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                path = Path(entry.path)
                rel = path.relative_to(root)
                if is_link(path):
                    links.append(rel.as_posix())
                elif entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    label = category(rel, root, original_records)
                    bucket = categories[label]
                    bucket["bytes"] += size
                    bucket["files"] += 1
                    if label == "legacy-or-unknown-backup" and path.name.casefold() != "readme.md":
                        legacy_count += 1
                        legacy_candidates.append((size, rel.as_posix()))
                    top = rel.parts[0]
                    folders[top]["bytes"] += size
                    folders[top]["files"] += 1
    return {"root": str(root), "total_bytes": sum(row["bytes"] for row in categories.values()),
            "categories": dict(sorted(categories.items())),
            "folders": dict(sorted(folders.items(), key=lambda item: -item[1]["bytes"])),
            "legacy_candidates_for_review": [{"path": name, "bytes": size, "verified_original": False}
                                             for size, name in sorted(legacy_candidates, reverse=True)],
            "legacy_candidate_count": legacy_count,
            "links_skipped": links}


def clean_temp(root: Path) -> dict:
    no_link_components(root)
    root = root.resolve()
    before = report(root)["total_bytes"]
    page = root / "images.html"
    html = page.read_text(encoding="utf-8") if page.is_file() else ""
    previews = review_pages.clean_previews(root, html) if page.is_file() else 0
    transactions = patch_v3.clean_committed(root)
    orphaned = original_store.clean_orphan_transactions(root)
    after = report(root)["total_bytes"]
    return {"previews_removed": previews, "committed_transactions_removed": transactions,
            "orphaned_replacements_removed": orphaned,
            "bytes_reclaimed": max(0, before - after)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["report", "clean-temp"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", help="print machine-readable report")
    args = parser.parse_args(argv)
    try:
        result = report(args.root) if args.command == "report" else clean_temp(args.root)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    if args.json or args.command == "clean-temp":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"TOTAL {result['total_bytes']} bytes")
        for name, row in result["folders"].items():
            print(f"{row['bytes']:>14} bytes  {row['files']:>7} files  {name}")
        for name, row in result["categories"].items():
            print(f"CATEGORY {name}: {row['bytes']} bytes")
        if result["links_skipped"]:
            print(f"LINKS SKIPPED: {len(result['links_skipped'])}")
        if result["legacy_candidate_count"]:
            print(f"LEGACY CANDIDATES FOR REVIEW (unverified): {result['legacy_candidate_count']}")
            for item in result["legacy_candidates_for_review"][:20]:
                print(f"  {item['bytes']:>14} bytes  {item['path']}")
            if result["legacy_candidate_count"] > 20:
                print("  Use --json to see every candidate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
