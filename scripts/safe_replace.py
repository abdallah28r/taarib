"""Atomically replace one game file while retaining only its verified original."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from file_ops import replace_file  # noqa: E402
from original_store import _remove_transaction, begin_replace, ensure, original, reconcile  # noqa: E402
from storage_core import digest, no_link_components, require_space, within  # noqa: E402


def install(root: Path, target: Path, replacement: Path) -> dict:
    no_link_components(root)
    no_link_components(target)
    no_link_components(replacement)
    root, target, replacement = root.resolve(), target.resolve(), replacement.resolve()
    if not root.is_dir() or not within(target, root) or target == root or not target.is_file() or not replacement.is_file():
        raise ValueError("target must be an existing file inside root; replacement must be a file")
    rel = target.relative_to(root)
    legacy_state = root / ".install-state"
    no_link_components(legacy_state, root)
    active_file = legacy_state / "active.json"
    no_link_components(active_file, legacy_state)
    if active_file.is_file():
        active = json.loads(active_file.read_text(encoding="utf-8"))
        if any(str(item.get("path", "")).casefold() == rel.as_posix().casefold()
               for item in active.get("files", [])):
            raise ValueError(f"file belongs to an installed package: {rel}")
    if legacy_state.is_dir():
        for record in legacy_state.glob("*/install-state.json"):
            no_link_components(record, root)
            transaction = json.loads(record.read_text(encoding="utf-8"))
            if transaction.get("status") in {"prepared", "installed"} and any(
                str(item.get("path", "")).casefold() == rel.as_posix().casefold()
                for item in transaction.get("files", [])
            ):
                raise ValueError(f"file belongs to a legacy installed package: {rel}")
    backup, _ = ensure(root, rel, target)
    item = reconcile(root, rel, target)
    old_hash, new_hash = digest(target), digest(replacement)
    if old_hash != item["active_sha256"]:
        raise ValueError(f"active file changed outside the template: {rel}")
    if old_hash == new_hash:
        return {"target": rel.as_posix(), "backup": str(backup.relative_to(root)),
                "original_sha256": item["sha256"], "replacement_sha256": new_hash,
                "status": "already-installed"}

    transaction_root = root / "backups" / ".transactions"
    no_link_components(transaction_root, root)
    require_space(transaction_root, target.stat().st_size + replacement.stat().st_size)
    transaction = transaction_root / uuid4().hex
    transaction.mkdir(parents=True)
    (transaction / "owner.json").write_text('{"owner":"taarib-safe-replace-v1"}\n', encoding="utf-8")
    previous = transaction / "current"
    staged = transaction / "replacement"
    pending = False
    try:
        begin_replace(root, rel, old_hash, new_hash, previous)
        pending = True
        shutil.copy2(target, previous)
        if digest(previous) != old_hash:
            raise ValueError("previous-file staging failed")
        with staged.open("xb") as handle:
            with replacement.open("rb") as source:
                shutil.copyfileobj(source, handle)
        if digest(staged) != new_hash:
            raise ValueError("replacement staging hash mismatch")
        replace_file(staged, target)
        if digest(target) != new_hash:
            raise ValueError("installed file hash mismatch")
        reconcile(root, rel, target)
        pending = False
    except Exception:
        if pending:
            actual = digest(target) if target.is_file() else None
            if actual == new_hash and previous.is_file():
                replace_file(previous, target)
            if target.is_file() and digest(target) == old_hash:
                reconcile(root, rel, target)
                pending = False
        raise
    finally:
        if not pending and transaction.exists():
            try:
                _remove_transaction(root, transaction)
            except (OSError, ValueError):
                pass
    return {"target": rel.as_posix(), "backup": str(backup.relative_to(root)),
            "original_sha256": item["sha256"], "replacement_sha256": new_hash,
            "status": "installed"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("target", type=Path)
    p.add_argument("replacement", nargs="?", type=Path)
    p.add_argument("--restore", action="store_true", help="restore the verified pre-localization original")
    p.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    if not a.yes: raise SystemExit("refusing to replace without --yes")
    no_link_components(a.root)
    root = a.root.resolve()
    raw_target = a.target if a.target.is_absolute() else root / a.target
    no_link_components(raw_target)
    target = raw_target.resolve()
    try:
        if a.restore:
            if a.replacement is not None:
                raise ValueError("--restore does not take a replacement")
            replacement = original(root, target.relative_to(root))
            if not replacement.is_file():
                raise ValueError("no verified original to restore")
        else:
            if a.replacement is None:
                raise ValueError("replacement is required unless --restore is used")
            replacement = a.replacement
        record = install(root, target, replacement)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(record))
    return 0


if __name__ == "__main__": raise SystemExit(main())
