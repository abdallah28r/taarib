"""Bounded-memory file and path checks shared by storage-sensitive commands."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat


def digest(path: Path, chunk_size: int = 1 << 20) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(chunk_size), b""):
            result.update(block)
    return result.hexdigest()


def is_link(path: Path) -> bool:
    """Include Windows junctions, which Path.is_symlink may not identify."""
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return True
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except (AttributeError, OSError):
        return False


def no_link_components(path: Path, stop: Path | None = None) -> None:
    current = path.absolute()
    boundary = stop.absolute() if stop else None
    while True:
        if is_link(current):
            raise ValueError(f"refusing a link or junction: {current}")
        if current == boundary or current.parent == current:
            break
        current = current.parent


def files_without_links(path: Path) -> list[Path]:
    """Inventory a source before creating a destination; never follow links."""
    no_link_components(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"missing source: {path}")
    files: list[Path] = []
    stack = [path]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                child = Path(entry.path)
                if is_link(child):
                    raise ValueError(f"refusing a link or junction in source: {child}")
                if entry.is_dir(follow_symlinks=False):
                    stack.append(child)
                elif entry.is_file(follow_symlinks=False):
                    files.append(child)
    return sorted(files)


def require_space(destination: Path, needed: int) -> None:
    existing = destination.absolute()
    while not existing.exists():
        if existing.parent == existing:
            raise ValueError(f"no existing parent for {destination}")
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    if needed > free:
        raise OSError(f"not enough disk space: need {needed} bytes, free {free} bytes near {destination}")


def within(path: Path, root: Path) -> bool:
    resolved, base = path.resolve(), root.resolve()
    return resolved == base or base in resolved.parents
