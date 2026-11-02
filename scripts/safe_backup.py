"""Keep one verified pre-localization original for each game file."""
from __future__ import annotations

import argparse
from pathlib import Path

from original_store import ensure, location
from storage_core import files_without_links, no_link_components, within


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    no_link_components(args.root)
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit("root does not exist")

    # Validate every source before the first write. In particular, backups
    # itself must not be copied into a destination beneath backups.
    selected: dict[str, Path] = {}
    for requested in args.paths:
        raw = requested if requested.is_absolute() else root / requested
        no_link_components(raw)
        source = raw.resolve()
        if not within(source, root):
            raise SystemExit(f"refusing path outside root: {source}")
        if source == root or source == root / "backups" or root / "backups" in source.parents:
            raise SystemExit("refusing to back up the root or its backups directory")
        try:
            for file in files_without_links(source):
                rel = file.relative_to(root)
                selected[rel.as_posix()] = file
        except ValueError as error:
            raise SystemExit(str(error)) from error

    try:
        for key, file in selected.items():
            ensure(root, Path(key), file)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"ORIGINALS={len(selected)} STORE={location(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
