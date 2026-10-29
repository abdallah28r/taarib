"""Schema 3 patch transactions: one original, one active payload, no history copies."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from original_store import ensure, entry, original
from storage_core import digest, is_link, no_link_components, require_space, within
from file_ops import remove_file, replace_file


def state_root(root: Path) -> Path:
    path = root / ".install-state"
    no_link_components(path, root)
    return path


def active_path(root: Path) -> Path:
    return state_root(root) / "active.json"


def read_active(root: Path) -> dict | None:
    path = active_path(root)
    no_link_components(path, root)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 3 or not isinstance(data.get("files"), list):
        raise ValueError("invalid active patch state")
    seen: set[str] = set()
    for item in data["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("invalid active patch entry")
        rel = _rel(root, item["path"])
        key = rel.as_posix().casefold()
        if key in seen or item.get("action") not in {"replace", "add"} or not isinstance(item.get("patch_sha256"), str):
            raise ValueError("invalid or duplicate active patch entry")
        seen.add(key)
    return data


def write_active(root: Path, data: dict | None) -> None:
    path = active_path(root)
    if data is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _rel(root: Path, name: str) -> Path:
    rel = Path(name)
    if (not rel.parts or rel.is_absolute() or ".." in rel.parts
            or rel.parts[0].casefold() in {".install-state", "backups"}
            or rel.as_posix().casefold() == "manifest.json"):
        raise ValueError(f"invalid package path: {name}")
    no_link_components(root / rel, root)
    if not within(root / rel, root):
        raise ValueError(f"package path leaves game root: {name}")
    return rel


def package_files(root: Path, package: Path, manifest: dict) -> list[dict]:
    if manifest.get("schema") != 3 or not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValueError("unsupported or empty schema 3 package")
    seen: set[str] = set()
    out = []
    for item in manifest["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("invalid package entry")
        rel = _rel(root, item["path"])
        key = rel.as_posix().casefold()
        if key in seen:
            raise ValueError(f"duplicate package path: {rel}")
        seen.add(key)
        source = package / rel
        no_link_components(source, package)
        if not source.is_file() or not within(source, package):
            raise ValueError(f"missing package file: {rel}")
        if item.get("action") not in {"add", "replace"} or not isinstance(item.get("patch_sha256"), str):
            raise ValueError(f"invalid package action or hash: {rel}")
        if digest(source) != item["patch_sha256"]:
            raise ValueError(f"package hash mismatch: {rel}")
        if item["action"] == "replace" and not isinstance(item.get("original_sha256"), str):
            raise ValueError(f"missing original hash: {rel}")
        if item["action"] == "add" and item.get("original_sha256") is not None:
            raise ValueError(f"added file cannot have an original hash: {rel}")
        out.append({"path": rel.as_posix(), "action": item["action"],
                    "patch_sha256": item["patch_sha256"],
                    "original_sha256": item.get("original_sha256")})
    return out


def _legacy_active(root: Path) -> bool:
    folder = state_root(root)
    if not folder.is_dir():
        return False
    for path in folder.glob("*/install-state.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("status") in {"installed", "prepared"}:
                return True
        except (OSError, ValueError):
            return True
    return False


def _hash(path: Path) -> str | None:
    return digest(path) if path.is_file() else None


def _atomic_copy(source: Path, target: Path, staging: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=staging) as handle:
            temporary = Path(handle.name)
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, handle)
        if digest(temporary) != digest(source):
            raise ValueError(f"staging hash mismatch: {target}")
        replace_file(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _delete_pending(root: Path, folder: Path) -> None:
    base = state_root(root) / "pending"
    no_link_components(base, root)
    if folder.parent.resolve() != base.resolve() or not within(folder, base):
        raise ValueError("refusing to remove an unknown pending directory")
    no_link_components(folder, base)
    marker = folder / "owner.json"
    if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")) != {"owner": "taarib-patch-v3"}:
        raise ValueError("pending directory is not owned by patch_v3")
    # These names are registered by patch_v3 before any game file changes.
    # A partial JSON file means the process stopped before journal commit, so
    # it is safe to discard the registered staging while retaining unknown
    # names and directories.
    allowed_files = {"owner.json", "prepare.json", "prepare.tmp", "journal.json", "journal.tmp"}
    allowed_dirs = set()
    expected_hashes = {}
    prepare = None
    for candidate in (folder / "prepare.json", folder / "prepare.tmp"):
        if not candidate.is_file():
            continue
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if value.get("schema") != 3 or not isinstance(value.get("paths"), list):
            continue
        prepare = value
        break
    if prepare is not None:
        allowed_dirs.add("previous")
        for row in prepare["paths"]:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise ValueError("invalid patch preparation path")
            rel = _rel(root, row["path"])
            wanted = row.get("sha256")
            if wanted is None:
                continue
            if not isinstance(wanted, str):
                raise ValueError("invalid patch preparation hash")
            name = (Path("previous") / rel).as_posix()
            allowed_files.add(name)
            expected_hashes[name] = wanted
            parent = Path(name).parent
            while parent != Path("."):
                allowed_dirs.add(parent.as_posix())
                parent = parent.parent
    journal = None
    journal_path = folder / "journal.json"
    if journal_path.is_file():
        try:
            value = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            value = None
        if isinstance(value, dict) and value.get("schema") == 3 and isinstance(value.get("paths"), list):
            journal = value
    if journal is not None:
        allowed_dirs.update({"previous", "staging"})
        for row in journal["paths"]:
            rel = _rel(root, row["path"])
            if row["sha256"] is None:
                continue
            name = (Path("previous") / rel).as_posix()
            allowed_files.add(name)
            expected_hashes[name] = row["sha256"]
            parent = Path(name).parent
            while parent != Path("."):
                allowed_dirs.add(parent.as_posix())
                parent = parent.parent
    stack = [folder]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                name = path.relative_to(folder).as_posix()
                if is_link(path):
                    raise ValueError(f"pending directory contains a link: {name}")
                if entry.is_dir(follow_symlinks=False):
                    if name not in allowed_dirs:
                        raise ValueError(f"pending directory contains an unknown folder: {name}")
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    if name not in allowed_files or (name in expected_hashes and digest(path) != expected_hashes[name]):
                        raise ValueError(f"pending directory contains an unknown or changed file: {name}")
                else:
                    raise ValueError(f"pending directory contains an unknown entry: {name}")
    shutil.rmtree(folder)


def _desired_hash(root: Path, item: dict | None, rel: Path, removed_action: str | None = None) -> str | None:
    if item:
        return item["patch_sha256"]
    if removed_action == "replace":
        backup_item = entry(root, rel)
        if not backup_item:
            raise ValueError(f"verified original missing: {rel}")
        return backup_item["sha256"]
    return None


def _verify_state(root: Path, state: dict | None, all_paths: set[str], previous: dict | None = None) -> bool:
    files = {item["path"]: item for item in (state or {}).get("files", [])}
    old = {item["path"]: item for item in (previous or {}).get("files", [])}
    return all(_hash(root / _rel(root, rel)) == _desired_hash(root, files.get(rel), Path(rel),
                                                              old.get(rel, {}).get("action"))
               for rel in all_paths)


def _restore_previous(root: Path, folder: Path, journal: dict) -> None:
    previous = folder / "previous"
    for row in journal["paths"]:
        rel = _rel(root, row["path"])
        target = root / rel
        wanted = row["sha256"]
        saved = previous / rel
        if wanted is None:
            if target.exists():
                remove_file(target)
        else:
            no_link_components(saved, folder)
            if not saved.is_file() or digest(saved) != wanted:
                raise ValueError(f"temporary rollback copy missing or damaged: {rel}")
            _atomic_copy(saved, target, folder / "staging")
    if not all(_hash(root / _rel(root, row["path"])) == row["sha256"] for row in journal["paths"]):
        raise ValueError("rollback verification failed")


def recover(root: Path) -> None:
    pending = state_root(root) / "pending"
    no_link_components(pending, root)
    if not pending.is_dir():
        return
    for folder in sorted(pending.iterdir()):
        no_link_components(folder, pending)
        if not folder.is_dir() or folder.is_symlink() or getattr(folder, "is_junction", lambda: False)():
            raise ValueError(f"unknown pending state: {folder}")
        marker = folder / "owner.json"
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")) != {"owner": "taarib-patch-v3"}:
            raise ValueError(f"unknown pending directory: {folder}")
        journal_file = folder / "journal.json"
        if not journal_file.is_file():
            # Nothing is changed before the journal is written.
            _delete_pending(root, folder)
            continue
        journal = json.loads(journal_file.read_text(encoding="utf-8"))
        paths = {_rel(root, row["path"]).as_posix() for row in journal["paths"]}
        active = read_active(root)
        if active == journal["new"]:
            if not _verify_state(root, active, paths, journal["old"]):
                raise ValueError("installed files changed after interrupted commit")
            _delete_pending(root, folder)
        elif active == journal["old"]:
            before = {row["path"]: row["sha256"] for row in journal["paths"]}
            new = {item["path"]: item for item in (journal["new"] or {}).get("files", [])}
            old_actions = {item["path"]: item["action"] for item in (journal["old"] or {}).get("files", [])}
            for name in paths:
                actual = _hash(root / name)
                if actual not in {before[name], _desired_hash(root, new.get(name), Path(name), old_actions.get(name))}:
                    raise ValueError(f"interrupted transaction has an unknown file version: {name}")
            _restore_previous(root, folder, journal)
            _delete_pending(root, folder)
        else:
            raise ValueError("active state changed during interrupted transaction")


def clean_committed(root: Path) -> int:
    """Discard only a fully committed, verified transaction's temporary files."""
    pending = state_root(root) / "pending"
    no_link_components(pending, root)
    if not pending.is_dir():
        return 0
    count = 0
    for folder in sorted(pending.iterdir()):
        journal_file = folder / "journal.json"
        marker = folder / "owner.json"
        if not journal_file.is_file() or not marker.is_file():
            continue
        if json.loads(marker.read_text(encoding="utf-8")) != {"owner": "taarib-patch-v3"}:
            continue
        journal = json.loads(journal_file.read_text(encoding="utf-8"))
        if read_active(root) != journal.get("new"):
            continue
        paths = {_rel(root, row["path"]).as_posix() for row in journal["paths"]}
        if not _verify_state(root, journal["new"], paths, journal["old"]):
            continue
        try:
            _delete_pending(root, folder)
        except (OSError, ValueError):
            continue
        count += 1
    return count


def apply(root: Path, package: Path | None, manifest: dict | None = None) -> dict | None:
    no_link_components(root)
    root = root.resolve()
    recover(root)
    old = read_active(root)
    if old is None and _legacy_active(root):
        raise ValueError("uninstall the legacy transaction before a schema 3 install")
    new_files = package_files(root, package, manifest) if package is not None else []
    if package is None and old is None:
        raise ValueError("no active patch to uninstall")
    new = {"schema": 3, "id": uuid4().hex, "files": new_files} if package is not None else None
    old_items = {item["path"]: item for item in (old or {}).get("files", [])}
    new_items = {item["path"]: item for item in new_files}
    all_names = set(old_items) | set(new_items)

    for name, item in old_items.items():
        if _hash(root / name) != item["patch_sha256"]:
            raise ValueError(f"installed file changed; refusing update: {name}")
    for name, item in new_items.items():
        rel = _rel(root, name)
        prior = old_items.get(name)
        if prior:
            if prior["action"] != item["action"] or prior.get("original_sha256") != item.get("original_sha256"):
                raise ValueError(f"package original changed: {name}")
        elif item["action"] == "replace":
            if _hash(root / name) != item["original_sha256"]:
                raise ValueError(f"original hash mismatch: {name}")
            existing = entry(root, rel)
            if existing and existing.get("active_sha256") != existing["sha256"]:
                raise ValueError(f"file belongs to a standalone replacement: {name}")
            ensure(root, rel, expected=item["original_sha256"])
        elif (root / name).exists():
            raise ValueError(f"added path already exists: {name}")
        if item["action"] == "replace":
            saved = entry(root, rel)
            if not saved or saved["sha256"] != item["original_sha256"]:
                raise ValueError(f"verified original missing: {name}")

    pending_root = state_root(root) / "pending"
    no_link_components(pending_root, root)
    old_bytes = sum((root / name).stat().st_size for name in all_names if (root / name).is_file())
    new_bytes = sum((package / name).stat().st_size for name in new_items) if package else 0
    require_space(pending_root, old_bytes + new_bytes)
    folder = pending_root / uuid4().hex
    folder.mkdir(parents=True)
    (folder / "owner.json").write_text('{"owner":"taarib-patch-v3"}\n', encoding="utf-8")
    rows = []
    committed = False
    try:
        for name in sorted(all_names):
            target = root / name
            rows.append({"path": name, "sha256": _hash(target)})
        prepare = {"schema": 3, "paths": rows}
        prepare_tmp = folder / "prepare.tmp"
        prepare_tmp.write_text(json.dumps(prepare, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(prepare_tmp, folder / "prepare.json")
        for name in sorted(all_names):
            target = root / name
            previous_hash = next(row["sha256"] for row in rows if row["path"] == name)
            if previous_hash is not None:
                saved = folder / "previous" / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                if digest(saved) != previous_hash:
                    raise ValueError(f"temporary rollback copy failed: {name}")
        journal = {"schema": 3, "old": old, "new": new, "paths": rows}
        journal_tmp = folder / "journal.tmp"
        journal_tmp.write_text(json.dumps(journal, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(journal_tmp, folder / "journal.json")
        for name in sorted(all_names):
            target = root / name
            if name in new_items:
                _atomic_copy(package / name, target, folder / "staging")
            elif old_items[name]["action"] == "replace":
                _atomic_copy(original(root, Path(name)), target, folder / "staging")
            else:
                remove_file(target)
        if not _verify_state(root, new, all_names, old):
            raise ValueError("installed files failed final verification")
        write_active(root, new)
        committed = True
        try:
            _delete_pending(root, folder)
        except (OSError, ValueError):
            # State and files are verified; a registered staging directory can
            # be removed by clean-temp or by recovery on the next operation.
            pass
    except Exception:
        if not committed:
            if folder.exists() and (folder / "journal.json").is_file():
                _restore_previous(root, folder, journal)
            if folder.exists():
                _delete_pending(root, folder)
        raise
    return new
