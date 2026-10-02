"""Verify exact originals and install added/replaced files with rollback state."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from build_patch_package import has_symlink_component


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_copy(source: Path, target: Path) -> None:
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=target.parent) as handle:
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, handle)
            temporary = Path(handle.name)
        if digest(temporary) != digest(source):
            raise RuntimeError(f"staging hash mismatch: {target}")
        temporary.replace(target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("package", type=Path)
    p.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    if not a.yes:
        raise SystemExit("refusing install without --yes")
    root, package = a.root.resolve(), a.package.resolve()
    if (not root.is_dir() or not package.is_dir() or root == package
            or root in package.parents or package in root.parents):
        raise SystemExit("root and package must be separate directories")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    schema = manifest.get("schema", 1)
    items = manifest.get("files", [])
    if schema not in (1, 2) or not isinstance(items, list) or not items:
        raise SystemExit("unsupported or empty package manifest")
    staged, seen = [], set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise SystemExit("invalid package entry")
        rel = Path(item["path"])
        key = rel.as_posix().casefold()
        if (not rel.parts or rel.is_absolute() or ".." in rel.parts or key in seen
                or rel.parts[0].lower() == ".install-state" or rel.as_posix().lower() == "manifest.json"
                or has_symlink_component(root, rel) or has_symlink_component(package, rel)):
            raise SystemExit(f"invalid or duplicate package path: {rel}")
        seen.add(key)
        target, source = (root / rel).resolve(), (package / rel).resolve()
        if root not in target.parents or package not in source.parents or not source.is_file():
            raise SystemExit(f"missing or invalid patch: {rel}")
        action = item.get("action", "replace" if schema == 1 else None)
        if action not in {"add", "replace"}:
            raise SystemExit(f"unsupported action: {rel}")
        if not item.get("patch_sha256") or digest(source) != item["patch_sha256"]:
            raise SystemExit(f"patch hash mismatch: {rel}")
        if action == "replace":
            if (not target.is_file() or not item.get("original_sha256")
                    or digest(target) != item["original_sha256"]):
                raise SystemExit(f"original hash mismatch: {rel}")
        elif target.exists() or target.is_symlink():
            raise SystemExit(f"added path already exists: {rel}")
        staged.append((rel, target, source, action, item))
    state_root = root / ".install-state"
    if state_root.is_symlink():
        raise SystemExit("install-state must not be a symlink")
    transaction = state_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    backup = transaction / "originals"
    transaction.mkdir(parents=True)
    for rel, target, _, action, _ in staged:
        if action == "replace":
            destination = backup / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
            if digest(destination) != digest(target):
                raise SystemExit(f"backup verification failed: {rel}")
    record = {"schema": 2, "status": "prepared", "files": [
        {"path": rel.as_posix(), "action": action, "patch_sha256": item["patch_sha256"],
         "original_sha256": item.get("original_sha256")}
        for rel, _, _, action, item in staged]}
    state_file = transaction / "install-state.json"
    state_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    installed = []
    try:
        for rel, target, source, action, _ in staged:
            _atomic_copy(source, target)
            installed.append((rel, target, action))
        record["status"] = "installed"
        state_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    except Exception:
        for rel, target, action in reversed(installed):
            if action == "add":
                target.unlink()
            else:
                _atomic_copy(backup / rel, target)
        raise
    print(f"INSTALLED={len(installed)} BACKUP={transaction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
