"""Back up one existing file in a unique transaction, then replace atomically."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("target", type=Path)
    p.add_argument("replacement", type=Path)
    p.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    if not a.yes: raise SystemExit("refusing to replace without --yes")
    root = a.root.resolve()
    target = (a.target if a.target.is_absolute() else root / a.target).resolve()
    replacement = a.replacement.resolve()
    if root not in target.parents or not target.is_file() or not replacement.is_file():
        raise SystemExit("target must be an existing file inside root; replacement must be a file")
    rel = target.relative_to(root)
    if (root / "backups").is_symlink() or (root / "backups" / "safe-replace").is_symlink():
        raise SystemExit("backup directory must not be a symlink")
    transaction = root / "backups" / "safe-replace" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    backup = transaction / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    if digest(backup) != digest(target): raise SystemExit("backup verification failed")
    record = {"target": rel.as_posix(), "backup": str(backup.relative_to(root).as_posix()),
              "original_sha256": digest(backup), "replacement_sha256": digest(replacement)}
    (transaction / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    temp = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=target.parent) as handle:
            with replacement.open("rb") as source: shutil.copyfileobj(source, handle)
            temp = Path(handle.name)
        if digest(temp) != record["replacement_sha256"]: raise RuntimeError("replacement staging verification failed")
        temp.replace(target)
    finally:
        if temp is not None and temp.exists(): temp.unlink()
    print(json.dumps(record))
    return 0


if __name__ == "__main__": raise SystemExit(main())
