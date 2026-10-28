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
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = "save_manifest.json"


def manifest(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def refuse_sandbox(path: Path) -> None:
    parts = [part.lower() for part in path.resolve().parts]
    if "packages" in parts and "appdata" in parts:
        raise SystemExit(f"refusing a store-app sandbox: {path}")


def snapshot(saves: Path, out: Path) -> dict:
    refuse_sandbox(saves)
    if not saves.is_dir():
        raise SystemExit(f"no save folder: {saves}")
    if out.exists():
        raise SystemExit(f"snapshot exists, choose a new folder: {out}")
    shutil.copytree(saves, out / "files")
    record = {"source": str(saves.resolve()), "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "files": manifest(out / "files")}
    if record["files"] != manifest(saves):
        raise SystemExit("the save folder changed while copying; close the game and retry")
    (out / MANIFEST).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def changes(saves: Path, out: Path) -> dict[str, list[str]]:
    before = json.loads((out / MANIFEST).read_text(encoding="utf-8"))["files"]
    now = manifest(saves)
    return {"changed": sorted(k for k in before.keys() & now.keys() if before[k] != now[k]),
            "added": sorted(now.keys() - before.keys()), "removed": sorted(before.keys() - now.keys())}


def restore(saves: Path, out: Path) -> Path:
    refuse_sandbox(saves)
    record = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    if manifest(out / "files") != record["files"]:
        raise SystemExit("snapshot is damaged; nothing restored")
    aside = saves.with_name(saves.name + ".before-restore-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    if saves.exists():
        shutil.move(str(saves), str(aside))
    shutil.copytree(out / "files", saves)
    return aside


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["snapshot", "verify", "restore"])
    parser.add_argument("saves", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
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
