"""Remove one installed patch transaction after verifying the installed hashes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

from apply_patch_package import _atomic_copy, digest
from build_patch_package import has_symlink_component
from file_ops import remove_file


TRANSACTION = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{32}\Z")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("transaction_id", help="final directory name printed by the installer")
    p.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    if not a.yes:
        raise SystemExit("refusing uninstall without --yes")
    root = a.root.resolve()
    if not root.is_dir() or not TRANSACTION.fullmatch(a.transaction_id):
        raise SystemExit("invalid root or transaction ID")
    state_root = root / ".install-state"
    if state_root.is_symlink():
        raise SystemExit("install-state must not be a symlink")
    transaction = state_root / a.transaction_id
    if transaction.is_symlink() or not transaction.is_dir():
        raise SystemExit("transaction not found or is a symlink")
    state_file = transaction / "install-state.json"
    record = json.loads(state_file.read_text(encoding="utf-8"))
    if record.get("schema") != 2 or record.get("status") not in {"installed", "prepared"}:
        raise SystemExit("transaction is not installed or recoverable")
    prepared = record["status"] == "prepared"
    staged, seen = [], set()
    for item in record.get("files", []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise SystemExit("invalid transaction entry")
        rel = Path(item["path"])
        key = rel.as_posix().casefold()
        if (not rel.parts or rel.is_absolute() or ".." in rel.parts or key in seen
                or rel.parts[0].lower() == ".install-state"
                or has_symlink_component(root, rel)
                or has_symlink_component(transaction / "originals", rel)):
            raise SystemExit(f"invalid transaction path: {rel}")
        seen.add(key)
        target = (root / rel).resolve()
        current_hash = digest(target) if target.is_file() else None
        allowed_hashes = {item.get("patch_sha256")}
        if prepared and item.get("action") == "replace":
            allowed_hashes.add(item.get("original_sha256"))
        if prepared and item.get("action") == "add":
            allowed_hashes.add(None)
        if root not in target.parents or current_hash not in allowed_hashes:
            raise SystemExit(f"installed file changed; refusing uninstall: {rel}")
        action = item.get("action")
        backup = (transaction / "originals" / rel).resolve()
        if action == "replace":
            if (transaction not in backup.parents or not backup.is_file()
                    or digest(backup) != item.get("original_sha256")):
                raise SystemExit(f"backup hash mismatch: {rel}")
        elif action != "add":
            raise SystemExit(f"invalid action: {rel}")
        staged.append((rel, target, backup, action, current_hash))
    if not staged:
        raise SystemExit("transaction has no files")
    undo = transaction / "uninstall-rollback"
    for rel, target, _, _, current_hash in staged:
        if current_hash is None:
            continue
        saved = undo / rel
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved)
        if digest(saved) != digest(target):
            raise SystemExit(f"uninstall staging failed: {rel}")
    changed = []
    try:
        for rel, target, backup, action, current_hash in staged:
            if action == "add":
                if current_hash is not None:
                    remove_file(target)
            else:
                _atomic_copy(backup, target)
            if current_hash is not None:
                changed.append((rel, target))
        record["status"] = "uninstalled"
        state_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    except Exception:
        for rel, target in reversed(changed):
            _atomic_copy(undo / rel, target)
        raise
    print(f"UNINSTALLED={len(changed)} STATE={transaction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
