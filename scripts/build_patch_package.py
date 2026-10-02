"""Build a hash-checked replacement package from selected changed files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("files", nargs="+")
    p.add_argument("--patch-root", type=Path)
    a = p.parse_args(argv)
    root = a.root.resolve()
    patch = (a.patch_root or a.root).resolve()
    output = a.output.resolve()
    if (not root.is_dir() or not patch.is_dir() or output.exists()
            or output == root or root in output.parents
            or output == patch or patch in output.parents):
        raise SystemExit("output must be a new directory outside both source roots")
    if len(set(a.files)) != len(a.files): raise SystemExit("duplicate files")
    staged = []
    for name in a.files:
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts: raise SystemExit(f"invalid file: {name}")
        original, changed = (root / rel).resolve(), (patch / rel).resolve()
        if root not in original.parents or not original.is_file():
            raise SystemExit(f"invalid original: {name}")
        if patch not in changed.parents or not changed.is_file():
            raise SystemExit(f"missing patch file: {name}")
        staged.append((rel, original, changed))
    items = []
    for rel, original, changed in staged:
        destination = output / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(changed, destination)
        items.append({"path": rel.as_posix(), "original_sha256": digest(original),
                      "patch_sha256": digest(changed)})
    (output / "manifest.json").write_text(json.dumps({"schema": 1, "files": items}, indent=2), encoding="utf-8")
    print(f"FILES={len(items)} OUTPUT={output}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
