"""Install or update a complete schema 3 patch while preserving rollback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from file_ops import replace_file
from storage_core import digest, no_link_components
import patch_v3


def _atomic_copy(source: Path, target: Path) -> None:
    """Legacy uninstaller helper; existing transactions retain their format."""
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=target.parent) as handle:
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, handle)
            temporary = Path(handle.name)
        if digest(temporary) != digest(source):
            raise RuntimeError(f"staging hash mismatch: {target}")
        replace_file(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not args.yes:
        raise SystemExit("refusing install without --yes")
    no_link_components(args.root)
    no_link_components(args.package)
    root, package = args.root.resolve(), args.package.resolve()
    if (not root.is_dir() or not package.is_dir() or root == package
            or root in package.parents or package in root.parents):
        raise SystemExit("root and package must be separate directories")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema", 1) in (1, 2):
        raise SystemExit("legacy package installation is disabled; rebuild a complete schema 3 package")
    if manifest.get("schema") != 3:
        raise SystemExit("unsupported package schema")
    try:
        result = patch_v3.apply(root, package, manifest)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"INSTALLED={len(result['files'])} STATE_ID={result['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
