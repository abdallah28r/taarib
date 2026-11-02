"""Validate tools/project-scripts.json, the registry of scripts written during a project.

Every script an agent writes for this game is listed there so any later
session or model finds and reuses it instead of rebuilding it. Each entry
needs: name, path (an existing file under work/tools/, adapters/, or
scripts/), purpose, usage (an exact command), tested (how it was checked),
and reusable (true when it should be proposed for the template).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tools" / "project-scripts.json"
REQUIRED = ("name", "path", "purpose", "usage", "tested", "reusable")
ALLOWED_DIRS = ("work/tools/", "adapters/", "scripts/")


def validate(registry: Path = REGISTRY, root: Path = ROOT) -> list[str]:
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read {registry}: {exc}"]
    errors, names = [], set()
    for index, entry in enumerate(data.get("scripts", [])):
        label = entry.get("name") or f"entry {index}"
        missing = [key for key in REQUIRED if key not in entry or entry[key] in ("", None)]
        if missing:
            errors.append(f"{label}: missing {', '.join(missing)}")
            continue
        if label in names:
            errors.append(f"{label}: duplicate name")
        names.add(label)
        path = str(entry["path"]).replace("\\", "/")
        if not path.startswith(ALLOWED_DIRS):
            errors.append(f"{label}: path must be under {', '.join(ALLOWED_DIRS)}")
        elif not (root / path).is_file():
            errors.append(f"{label}: {path} does not exist")
        if not isinstance(entry["reusable"], bool):
            errors.append(f"{label}: reusable must be true or false")
    return errors


def summary(registry: Path = REGISTRY, limit: int = 10) -> list[str]:
    """One line per registered script, for the session-start status."""
    try:
        scripts = json.loads(registry.read_text(encoding="utf-8")).get("scripts", [])
    except (OSError, json.JSONDecodeError):
        return []
    lines = [f"- {s.get('name')}: {s.get('purpose')} → {s.get('usage')}" for s in scripts[:limit]]
    if len(scripts) > limit:
        lines.append(f"- ... {len(scripts) - limit} more in tools/project-scripts.json")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)
    errors = validate(args.registry)
    for error in errors:
        print(f"ERROR {error}")
    print(f"PROJECT_SCRIPTS={'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
