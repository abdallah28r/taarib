"""One verified pre-localization original per game-relative path."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

from storage_core import digest, no_link_components, require_space, within

SCHEMA = 1


def location(root: Path) -> Path:
    return root / "backups" / "originals"


def _manifest_path(root: Path) -> Path:
    return location(root) / "manifest.json"


def _relative(root: Path, rel: Path) -> Path:
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or rel.parts[0].casefold() in {"backups", ".install-state"}:
        raise ValueError(f"invalid game-relative path: {rel}")
    target = root / rel
    no_link_components(target, root)
    if not within(target, root):
        raise ValueError(f"path leaves game root: {rel}")
    return rel


def load(root: Path) -> dict:
    path = _manifest_path(root)
    no_link_components(path, root)
    if not path.exists():
        return {"schema": SCHEMA, "files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("files"), dict):
        raise ValueError("unsupported original-store manifest")
    return data


def save(root: Path, data: dict) -> None:
    path = _manifest_path(root)
    no_link_components(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _legacy_present(root: Path, rel: Path) -> bool:
    # A live file in an older project may already be localized. Never label it
    # an original merely because the new manifest is absent.
    backups = root / "backups"
    no_link_components(backups, root)
    if backups.is_dir():
        for child in backups.iterdir():
            if child.name in {"originals", ".transactions", ".byte-patch", "README.md"}:
                continue
            # Older template copies often have timestamped folders without a
            # manifest. Their contents cannot establish the live file's origin.
            return True
    old = root / "backups" / "safe-replace"
    no_link_components(old, root)
    if old.is_dir():
        for record in old.glob("*/manifest.json"):
            try:
                if json.loads(record.read_text(encoding="utf-8")).get("target") == rel.as_posix():
                    return True
            except (OSError, ValueError):
                return True
    state = root / ".install-state"
    no_link_components(state, root)
    if state.is_dir():
        for record in state.glob("*/install-state.json"):
            try:
                data = json.loads(record.read_text(encoding="utf-8"))
                if data.get("status") in {"installed", "prepared"} and any(
                    item.get("path") == rel.as_posix() for item in data.get("files", [])
                ):
                    return True
            except (OSError, ValueError):
                return True
    return False


def _legacy_original(root: Path, rel: Path) -> Path | None:
    """Adopt only a legacy original whose recorded hash is unambiguous."""
    candidates: list[tuple[Path, str]] = []
    backups = root / "backups"
    no_link_components(backups, root)
    if backups.is_dir():
        old = backups / "safe-replace"
        no_link_components(old, root)
        if old.is_dir():
            for record in old.glob("*/manifest.json"):
                data = json.loads(record.read_text(encoding="utf-8"))
                if (data.get("target") == rel.as_posix()
                        and isinstance(data.get("original_sha256"), str)
                        and isinstance(data.get("replacement_sha256"), str)):
                    candidates.append((root / data["backup"], data["original_sha256"]))
    state = root / ".install-state"
    no_link_components(state, root)
    if state.is_dir():
        for record in state.glob("*/install-state.json"):
            data = json.loads(record.read_text(encoding="utf-8"))
            if data.get("status") not in {"installed", "prepared", "uninstalled"}:
                continue
            for item in data.get("files", []):
                if (item.get("path") == rel.as_posix() and item.get("action") == "replace"
                        and isinstance(item.get("original_sha256"), str)
                        and isinstance(item.get("patch_sha256"), str)):
                    candidates.append((record.parent / "originals" / rel, item["original_sha256"]))
    if backups.is_dir():
        recorded = {path.resolve() for path, _ in candidates}
        for child in backups.iterdir():
            if child.name in {"originals", ".transactions", ".byte-patch", "safe-replace", "README.md"}:
                continue
            no_link_components(child, root)
            possible = child / rel if child.is_dir() else child
            if not possible.exists() or (not child.is_dir() and child.name != rel.name):
                continue
            no_link_components(possible, root)
            if possible.is_file() and possible.resolve() not in recorded:
                raise ValueError(f"unrecorded legacy original needs review: {rel}")
    if not candidates:
        return None
    hashes = {expected for _, expected in candidates}
    if len(hashes) != 1:
        raise ValueError(f"legacy originals disagree; migration needs review: {rel}")
    for path, expected in candidates:
        no_link_components(path, root)
        if not within(path, root) or not path.is_file() or digest(path) != expected:
            raise ValueError(f"legacy original missing or damaged: {rel}")
    return candidates[0][0]


def _recorded_live_hashes(root: Path, rel: Path) -> set[str]:
    hashes: set[str] = set()
    active = root / ".install-state" / "active.json"
    no_link_components(active, root)
    if active.is_file():
        data = json.loads(active.read_text(encoding="utf-8"))
        hashes.update(item["patch_sha256"] for item in data.get("files", [])
                      if item.get("path") == rel.as_posix())
    old = root / "backups" / "safe-replace"
    no_link_components(old, root)
    if old.is_dir():
        for record in old.glob("*/manifest.json"):
            data = json.loads(record.read_text(encoding="utf-8"))
            if data.get("target") == rel.as_posix() and isinstance(data.get("replacement_sha256"), str):
                hashes.add(data["replacement_sha256"])
    state = root / ".install-state"
    no_link_components(state, root)
    if state.is_dir():
        for record in state.glob("*/install-state.json"):
            data = json.loads(record.read_text(encoding="utf-8"))
            if data.get("status") in {"installed", "prepared"}:
                hashes.update(item["patch_sha256"] for item in data.get("files", [])
                              if item.get("path") == rel.as_posix())
    return hashes


def original(root: Path, rel: Path) -> Path:
    rel = _relative(root, rel)
    return location(root) / "files" / rel


def entry(root: Path, rel: Path) -> dict | None:
    rel = _relative(root, rel)
    data = load(root)
    item = data["files"].get(rel.as_posix())
    if item is None:
        return None
    backup = original(root, rel)
    if not backup.is_file() or digest(backup) != item.get("sha256"):
        raise ValueError(f"original backup missing or damaged: {rel}")
    return item


def ensure(root: Path, rel: Path, source: Path | None = None, expected: str | None = None) -> tuple[Path, dict]:
    no_link_components(root)
    root = root.resolve()
    no_link_components(root / ".install-state", root)
    rel = _relative(root, rel)
    current = source or root / rel
    no_link_components(current)
    data = load(root)
    key = rel.as_posix()
    backup = original(root, rel)
    existing = data["files"].get(key)
    if existing is not None:
        if not backup.is_file() or digest(backup) != existing.get("sha256"):
            raise ValueError(f"original backup missing or damaged: {rel}")
        if expected and existing["sha256"] != expected:
            raise ValueError(f"original hash mismatch: {rel}")
        if current.is_file() and digest(current) not in {
            existing["sha256"], existing.get("active_sha256"),
            (existing.get("pending") or {}).get("new_sha256"), *_recorded_live_hashes(root, rel)
        }:
            raise ValueError(f"live file differs from every recorded version: {rel}")
        return backup, existing
    if backup.exists():
        raise ValueError(f"unregistered original backup needs review: {rel}")
    legacy = _legacy_original(root, rel)
    if legacy is None and _legacy_present(root, rel):
        raise ValueError(f"existing backup needs verified migration before use: {rel}")
    selected = legacy or current
    if not selected.is_file():
        raise ValueError(f"original source missing: {rel}")
    source_hash = digest(selected)
    live_hash = digest(current) if current.is_file() else None
    if live_hash is not None and live_hash not in {source_hash, *_recorded_live_hashes(root, rel)}:
        raise ValueError(f"live file differs from every recorded version: {rel}")
    if expected and source_hash != expected:
        raise ValueError(f"original hash mismatch: {rel}")
    require_space(backup, selected.stat().st_size)
    backup.parent.mkdir(parents=True, exist_ok=True)
    temporary = backup.with_name(backup.name + "." + uuid4().hex + ".tmp")
    try:
        shutil.copy2(selected, temporary)
        if digest(temporary) != source_hash:
            raise ValueError(f"backup verification failed: {rel}")
        os.replace(temporary, backup)
        data["files"][key] = {"sha256": source_hash, "size": selected.stat().st_size,
                              "active_sha256": live_hash or source_hash}
        save(root, data)
    finally:
        if temporary.exists():
            temporary.unlink()
    return backup, data["files"][key]


def update_active(root: Path, rel: Path, current_hash: str, new_hash: str) -> None:
    rel = _relative(root, rel)
    data = load(root)
    item = data["files"].get(rel.as_posix())
    if not item or item.get("active_sha256") != current_hash:
        raise ValueError(f"active file changed: {rel}")
    item["active_sha256"] = new_hash
    save(root, data)


def reconcile(root: Path, rel: Path, target: Path) -> dict:
    """Finish or cancel a replace interrupted after its intent was recorded."""
    rel = _relative(root, rel)
    data = load(root)
    item = data["files"].get(rel.as_posix())
    if item is None:
        raise ValueError(f"missing original backup: {rel}")
    pending = item.get("pending")
    if pending:
        old = pending.get("old_sha256")
        new = pending.get("new_sha256")
        actual = digest(target) if target.is_file() else None
        if actual == new:
            item["active_sha256"] = new
        elif actual != old:
            raise ValueError(f"interrupted replacement needs review: {rel}")
        saved = root / pending["temporary"]
        transaction = saved.parent
        if not within(saved, root / "backups" / ".transactions"):
            raise ValueError("invalid temporary backup path")
        item.pop("pending")
        save(root, data)
        try:
            _remove_transaction(root, transaction)
        except (OSError, ValueError):
            # The replacement is committed. Leave registered staging for a
            # later cleanup rather than reporting a failed install.
            pass
    return item


def _remove_transaction(root: Path, transaction: Path) -> None:
    base = root / "backups" / ".transactions"
    no_link_components(base, root)
    no_link_components(transaction, base)
    if transaction.parent.resolve() != base.resolve() or not within(transaction, base):
        raise ValueError("refusing to remove an unknown transaction")
    marker = transaction / "owner.json"
    if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")) != {"owner": "taarib-safe-replace-v1"}:
        raise ValueError("transaction is not owned by safe_replace")
    allowed = {"owner.json", "current", "replacement"}
    for child in transaction.iterdir():
        no_link_components(child, transaction)
        if child.name not in allowed or not child.is_file():
            raise ValueError("transaction contains an unknown file or directory")
    for child in transaction.iterdir():
        child.unlink()
    transaction.rmdir()


def clean_orphan_transactions(root: Path, minimum_age_seconds: int = 3600) -> int:
    """Remove owned staging no longer referenced by an in-flight replacement."""
    base = root / "backups" / ".transactions"
    no_link_components(base, root)
    if not base.is_dir():
        return 0
    data = load(root)
    referenced = {str((root / item["pending"]["temporary"]).parent.resolve())
                  for item in data["files"].values() if item.get("pending")}
    removed = 0
    now = time.time()
    for transaction in base.iterdir():
        if not transaction.is_dir() or str(transaction.resolve()) in referenced:
            continue
        if now - transaction.stat().st_mtime < minimum_age_seconds:
            continue
        try:
            _remove_transaction(root, transaction)
        except (OSError, ValueError):
            continue
        removed += 1
    return removed


def begin_replace(root: Path, rel: Path, old_hash: str, new_hash: str, temporary: Path) -> None:
    rel = _relative(root, rel)
    data = load(root)
    item = data["files"].get(rel.as_posix())
    if item is None or item.get("active_sha256") != old_hash or item.get("pending"):
        raise ValueError(f"active file changed or replacement pending: {rel}")
    if not within(temporary, root / "backups" / ".transactions"):
        raise ValueError("temporary backup must be inside backups/.transactions")
    item["pending"] = {"old_sha256": old_hash, "new_sha256": new_hash,
                       "temporary": temporary.relative_to(root).as_posix()}
    save(root, data)
