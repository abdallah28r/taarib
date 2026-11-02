"""Swap or remove a file in the game folder when Windows briefly holds it (library).

A running game or launcher, an antivirus scan of a file just written, or the search indexer can keep a
handle open for a moment, and Windows then refuses to replace or delete the file (PermissionError).
These helpers retry for about two seconds; if the file stays locked they raise FileInUse, which names
the file and what to close, and nothing has been changed.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

ATTEMPTS = 8  # 0.05 + 0.1 + 0.2 + 0.4 + 0.5 * 3 seconds of waiting at most


class FileInUse(PermissionError):
    """The file stayed locked by another program; the operation did nothing."""


def _retry(action, path: Path, what: str) -> None:
    for attempt in range(ATTEMPTS):
        try:
            action()
            return
        except PermissionError as error:
            last = error
            if attempt < ATTEMPTS - 1:
                time.sleep(min(0.05 * 2 ** attempt, 0.5))
    raise FileInUse(f"cannot {what} {path}: another program has it open (the game, its launcher, or an "
                    f"antivirus scan). Close the game and its launcher, wait a moment, and run it again; "
                    f"nothing was changed. ({last})") from last


def replace_file(source: Path, target: Path) -> None:
    """os.replace(source, target), retried while Windows holds either file."""
    _retry(lambda: os.replace(source, target), Path(target), "replace")


def remove_file(path: Path) -> None:
    """Delete a file, retried while Windows holds it."""
    _retry(lambda: Path(path).unlink(), Path(path), "remove")
