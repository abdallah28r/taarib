"""Validate exact tool choices; an empty catalog is not an installation claim."""
from __future__ import annotations

import argparse
from storage_core import digest
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def validate(lock_path: Path, verify_files: bool = False) -> list[str]:
    catalog = json.loads((ROOT / "tools/open-source-tools.json").read_text(encoding="utf-8"))
    known = {item["id"] for item in catalog["tools"]}
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema") != 1 or not isinstance(lock.get("selections"), list):
        return ["invalid selected-tool lock schema"]
    errors, seen = [], set()
    for index, item in enumerate(lock["selections"]):
        if not isinstance(item, dict):
            errors.append(f"selection {index}: expected object")
            continue
        tool_id = item.get("id")
        if tool_id not in known or tool_id in seen:
            errors.append(f"selection {index}: unknown or duplicate tool ID")
        seen.add(tool_id)
        for field in ("version_or_commit", "source_url", "license", "decision_note"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"selection {index}: missing {field}")
        checksum = item.get("sha256")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", checksum):
            errors.append(f"selection {index}: missing/invalid sha256")
        if verify_files:
            path = item.get("local_file")
            if not isinstance(path, str) or not path.strip():
                errors.append(f"selection {index}: missing local_file")
            else:
                local = Path(path)
                if not local.is_absolute():
                    local = ROOT / local
                if not local.is_file():
                    errors.append(f"selection {index}: local_file missing")
                elif isinstance(checksum, str) and digest(local).lower() != checksum.lower():
                    errors.append(f"selection {index}: local_file hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", nargs="?", type=Path, default=ROOT / "tools/selected-tools.json")
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    errors = validate(args.lock, args.verify_files)
    for error in errors:
        print("ERROR", error)
    print("TOOL_PROVENANCE=" + ("FAIL" if errors else "STRUCTURE_PASS"))
    print("SCOPE=metadata and optional file hash only; license and compatibility need review")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
