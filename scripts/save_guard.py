"""Protect the player's own save files around a test of the patched game.

    python scripts/save_guard.py snapshot <save_folder> backups/saves-<date>
    python scripts/save_guard.py verify   <save_folder> backups/saves-<date>
    python scripts/save_guard.py restore  <save_folder> backups/saves-<date>    # only on the user's words

Saves live outside the game folder (Documents, AppData, Saved Games), so
safe_backup.py does not cover them. Take a snapshot before the first launch of
a patched build: a localization can change save data (dialogue history, names,
cached text). `verify` lists files changed since the snapshot; `restore` puts
the snapshot back and keeps the current saves beside it, never deleting them.
A snapshot folder is never overwritten. Store-app sandboxes (`Packages/`) are
refused: copying them can break the app's save sync.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from storage_core import digest, files_without_links, no_link_components, require_space, within

MANIFEST = "save_manifest.json"


def manifest(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): digest(p) for p in files_without_links(root)}


def copy_checked_tree(source: Path, destination: Path, files: list[Path] | None = None) -> None:
    """Copy an inventoried tree without following links introduced during copying."""
    chosen = files if files is not None else files_without_links(source)
    destination.mkdir(parents=True)
    for file in chosen:
        no_link_components(file, source)
        rel = file.relative_to(source)
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target, follow_symlinks=False)
        if target.is_symlink() or getattr(target, "is_junction", lambda: False)():
            raise ValueError(f"source changed to a link while copying: {file}")


def refuse_sandbox(path: Path) -> None:
    parts = [part.lower() for part in path.resolve().parts]
    if "packages" in parts and "appdata" in parts:
        raise SystemExit(f"refusing a store-app sandbox: {path}")


def snapshot(saves: Path, out: Path) -> dict:
    refuse_sandbox(saves)
    no_link_components(saves)
    no_link_components(out)
    if not saves.is_dir():
        raise SystemExit(f"no save folder: {saves}")
    if within(out, saves):
        raise SystemExit("snapshot destination must be outside the save folder")
    if out.exists():
        raise SystemExit(f"snapshot exists, choose a new folder: {out}")
    source_files = files_without_links(saves)
    require_space(out, sum(path.stat().st_size for path in source_files))
    temporary = out.with_name(out.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.mkdir(parents=True)
        copy_checked_tree(saves, temporary / "files", source_files)
        record = {"source": str(saves.resolve()), "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "files": manifest(temporary / "files")}
        if record["files"] != manifest(saves):
            raise SystemExit("the save folder changed while copying; close the game and retry")
        (temporary / MANIFEST).write_text(json.dumps(record, indent=2), encoding="utf-8")
        os.replace(temporary, out)
        return record
    finally:
        if temporary.exists() and temporary.parent.resolve() == out.parent.resolve() and not temporary.is_symlink():
            shutil.rmtree(temporary)


def changes(saves: Path, out: Path) -> dict[str, list[str]]:
    before = json.loads((out / MANIFEST).read_text(encoding="utf-8"))["files"]
    now = manifest(saves)
    return {"changed": sorted(k for k in before.keys() & now.keys() if before[k] != now[k]),
            "added": sorted(now.keys() - before.keys()), "removed": sorted(before.keys() - now.keys())}


def restore(saves: Path, out: Path) -> Path:
    refuse_sandbox(saves)
    no_link_components(saves)
    no_link_components(out)
    if within(out, saves) or within(saves, out):
        raise SystemExit("save folder and snapshot must be separate")
    record = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    if manifest(out / "files") != record["files"]:
        raise SystemExit("snapshot is damaged; nothing restored")
    aside = saves.with_name(saves.name + ".before-restore-" + datetime.now().strftime("%Y%m%d%H%M%S")
                            + "-" + uuid4().hex)
    staged = saves.with_name(saves.name + ".restore-tmp-" + uuid4().hex)
    require_space(staged, sum(path.stat().st_size for path in files_without_links(out / "files")))
    try:
        copy_checked_tree(out / "files", staged)
        if manifest(staged) != record["files"]:
            raise SystemExit("staged save restore failed verification")
        if saves.exists():
            shutil.move(str(saves), str(aside))
        try:
            os.replace(staged, saves)
        except Exception:
            if aside.exists() and not saves.exists():
                os.replace(aside, saves)
            raise
    finally:
        if staged.exists() and staged.parent.resolve() == saves.parent.resolve() and not staged.is_symlink():
            shutil.rmtree(staged)
    return aside


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["snapshot", "verify", "restore"])
    parser.add_argument("saves", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args(argv)
    getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
    if args.command == "snapshot":
        print(f"SNAPSHOT files={len(snapshot(args.saves, args.snapshot)['files'])} -> {args.snapshot}")
        return 0
    if args.command == "verify":
        diff = changes(args.saves, args.snapshot)
        print(json.dumps(diff, ensure_ascii=False, indent=2))
        return 1 if any(diff.values()) else 0
    print(f"RESTORED; current saves kept at {restore(args.saves, args.snapshot)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
