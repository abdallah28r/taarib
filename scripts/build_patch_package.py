"""Build a hash-checked package of added and replaced game files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from storage_core import digest as hash_file, is_link, no_link_components, require_space


def digest(path: Path) -> str:
    return hash_file(path)


def has_symlink_component(root: Path, rel: Path) -> bool:
    current = root
    for part in rel.parts:
        current = current / part
        if is_link(current):
            return True
    return False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path, help="unmodified reference game copy")
    p.add_argument("output", type=Path)
    p.add_argument("files", nargs="+", help="game-relative paths to add or replace")
    p.add_argument("--patch-root", type=Path, help="root containing the changed files")
    a = p.parse_args(argv)
    no_link_components(a.root)
    no_link_components(a.patch_root or a.root)
    no_link_components(a.output)
    root = a.root.resolve()
    patch = (a.patch_root or a.root).resolve()
    output = a.output.resolve()
    if (not root.is_dir() or not patch.is_dir() or output.exists()
            or output == root or root in output.parents
            or output == patch or patch in output.parents):
        raise SystemExit("output must be a new directory outside both source roots")
    staged = []
    seen = set()
    for name in a.files:
        rel = Path(name)
        key = rel.as_posix().casefold()
        if (not rel.parts or rel.is_absolute() or ".." in rel.parts or key in seen
                or rel.parts[0].lower() in {".install-state", "backups"}
                or rel.as_posix().lower() == "manifest.json"
                or has_symlink_component(root, rel) or has_symlink_component(patch, rel)):
            raise SystemExit(f"invalid or duplicate file: {name}")
        seen.add(key)
        original, changed = (root / rel).resolve(), (patch / rel).resolve()
        if root not in original.parents or patch not in changed.parents or not changed.is_file():
            raise SystemExit(f"invalid or missing patch file: {name}")
        if original.exists() and not original.is_file():
            raise SystemExit(f"original path is not a file: {name}")
        staged.append((rel, original, changed))
    require_space(output, sum(changed.stat().st_size for _, _, changed in staged))
    items = []
    for rel, original, changed in staged:
        destination = output / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(changed, destination)
        if digest(destination) != digest(changed):
            raise SystemExit(f"package copy changed during build: {rel}")
        item = {"path": rel.as_posix(), "action": "replace" if original.is_file() else "add",
                "patch_sha256": digest(destination)}
        if original.is_file():
            item["original_sha256"] = digest(original)
        items.append(item)
    (output / "manifest.json").write_text(
        json.dumps({"schema": 3, "files": items}, indent=2), encoding="utf-8")
    print(f"FILES={len(items)} OUTPUT={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
