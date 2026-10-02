"""Verify exact originals and install a patch with a unique rollback snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("package", type=Path)
    p.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    if not a.yes: raise SystemExit("refusing install without --yes")
    root, package = a.root.resolve(), a.package.resolve()
    if not root.is_dir() or not package.is_dir() or root == package or root in package.parents:
        raise SystemExit("root and package must be separate directories")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    items = manifest.get("files", [])
    if not isinstance(items, list) or not items: raise SystemExit("manifest contains no files")
    staged, seen = [], set()
    for item in items:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts or rel in seen:
            raise SystemExit(f"invalid or duplicate package path: {rel}")
        seen.add(rel)
        target, source = (root / rel).resolve(), (package / rel).resolve()
        if root not in target.parents or package not in source.parents or not source.is_file() or not target.is_file():
            raise SystemExit(f"missing or invalid original/patch: {rel}")
        if not item.get("patch_sha256") or digest(source) != item["patch_sha256"]:
            raise SystemExit(f"patch hash mismatch: {rel}")
        if not item.get("original_sha256") or digest(target) != item["original_sha256"]:
            raise SystemExit(f"original hash mismatch: {rel}")
        staged.append((rel, target, source))
    if (root / ".install-state").is_symlink(): raise SystemExit("install-state must not be a symlink")
    transaction = root / ".install-state" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    backup = transaction / "originals"
    for rel, target, _ in staged:
        destination = backup / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination)
        if digest(destination) != digest(target): raise SystemExit(f"backup verification failed: {rel}")
    (transaction / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    installed = []
    try:
        for rel, target, source in staged:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile("wb", delete=False, dir=target.parent) as handle:
                    with source.open("rb") as input_file: shutil.copyfileobj(input_file, handle)
                    temporary = Path(handle.name)
                if digest(temporary) != digest(source): raise RuntimeError(f"staging hash mismatch: {rel}")
                temporary.replace(target)
                installed.append((rel, target))
            finally:
                if temporary is not None and temporary.exists(): temporary.unlink()
    except Exception:
        for rel, target in reversed(installed): shutil.copy2(backup / rel, target)
        raise
    print(f"INSTALLED={len(installed)} BACKUP={transaction}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
