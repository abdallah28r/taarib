"""Create a deterministic SHA-256 manifest for localization tools or release files."""

import argparse
import hashlib
import json
from pathlib import Path


EXCLUDED_DIRS = {".git", ".tools", ".venv", "__pycache__"}


def digest(path, chunk=1 << 20):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            value.update(block)
    return value.hexdigest()


def build(root, excluded):
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        resolved = path.resolve()
        relative = path.relative_to(root)
        if resolved in excluded or any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        files.append({"path": relative.as_posix(), "size": path.stat().st_size, "sha256": digest(path)})
    return {"root": str(root.resolve()), "files": files}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"ERROR not a directory: {args.root}"); return 2
    if args.output.exists() and not args.force:
        print(f"ERROR output exists; use --force: {args.output}"); return 2
    manifest = build(args.root, {args.output.resolve()})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FILES={len(manifest['files'])} OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
