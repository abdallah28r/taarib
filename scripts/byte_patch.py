"""Guarded byte edits and byte-range patches for large game files.

    python scripts/byte_patch.py edit <copy> --offset 0x41F8C8 --expected 8B4508 --new 8B450C
    python scripts/byte_patch.py make <original> <built> <out.arpatch>
    python scripts/byte_patch.py apply <out.arpatch> <target>

For archives or disc images too large to ship whole: `make` stores only the
changed ranges with the original and result SHA-256; `apply` refuses any other
file version, writes a temporary copy, checks the result hash, then swaps,
keeping `<name>.ar_old` for restore. `edit` changes bytes in place only when
the expected old bytes are there (and does nothing if already applied).

Editing an executable or scripts is runtime code: only under "Protected
archives and runtime code" in references/extraction-integration.md, on a copy
first. Back up the target with safe_backup.py before `apply` on the user's
copy, as for any game file.

Adapted from `code/patch_tools.py` of the Arabic Game Localization Playbook
(MXIAUDIO and contributors, MIT License; notice in THIRD_PARTY_NOTICES.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zlib
from pathlib import Path

SIGNATURE = "ARPATCH1"


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def patch_bytes(path: Path, offset: int, expected: bytes, new: bytes) -> str:
    """Equal-length in-place edit that refuses an unknown file."""
    if len(expected) != len(new):
        raise ValueError("equal-length edits only; relocate the data otherwise")
    with open(path, "r+b") as handle:
        handle.seek(offset)
        old = handle.read(len(expected))
        if old == new:
            return "already-applied"
        if old != expected:
            raise RuntimeError(f"{path}@{offset:#x}: expected {expected.hex()} found {old.hex()}")
        handle.seek(offset)
        handle.write(new)
    return "applied"


def diff_ranges(a: bytes, b: bytes, merge_gap: int = 64) -> list[tuple[int, bytes]]:
    """Changed ranges of b against a; ranges closer than merge_gap merge; a longer b adds a tail."""
    out, i, n = [], 0, min(len(a), len(b))
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        last = j = i
        while j < n and j - last <= merge_gap:
            if a[j] != b[j]:
                last = j
            j += 1
        out.append((i, b[i:last + 1]))
        i = last + 1
    if len(b) > len(a):
        out.append((len(a), b[len(a):]))
    return out


def make_patch(original: Path, built: Path, out: Path) -> dict:
    a, b = original.read_bytes(), built.read_bytes()
    ranges = diff_ranges(a, b)
    payload = b"".join(data for _, data in ranges)
    manifest = {
        "signature": SIGNATURE,
        "source": {"size": len(a), "sha256": hashlib.sha256(a).hexdigest()},
        "result": {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()},
        "ranges": [[offset, len(data)] for offset, data in ranges],
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    blob = json.dumps(manifest).encode()
    out.write_bytes(len(blob).to_bytes(4, "little") + blob + zlib.compress(payload, 9))
    return manifest


def apply_patch(patch: Path, target: Path) -> str:
    raw = patch.read_bytes()
    size = int.from_bytes(raw[:4], "little")
    manifest = json.loads(raw[4:4 + size])
    if manifest.get("signature") != SIGNATURE:
        raise RuntimeError("not a byte_patch file")
    payload = zlib.decompress(raw[4 + size:])
    if hashlib.sha256(payload).hexdigest() != manifest["payload_sha256"]:
        raise RuntimeError("patch payload corrupted")
    current = sha256(target)
    if current == manifest["result"]["sha256"]:
        return "already-installed"
    if current != manifest["source"]["sha256"]:
        raise RuntimeError("unsupported file version (hash mismatch); nothing written")
    temporary = target.with_name(target.name + ".ar_tmp")
    shutil.copyfile(target, temporary)
    with open(temporary, "r+b") as handle:
        handle.truncate(manifest["result"]["size"])
        position = 0
        for offset, length in manifest["ranges"]:
            handle.seek(offset)
            handle.write(payload[position:position + length])
            position += length
    if sha256(temporary) != manifest["result"]["sha256"]:
        temporary.unlink()
        raise RuntimeError("result hash mismatch; original untouched")
    backup = target.with_name(target.name + ".ar_old")
    os.replace(target, backup)  # a crash here is recoverable from .ar_old
    os.replace(temporary, target)
    return f"installed (backup: {backup.name})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    e = sub.add_parser("edit")
    e.add_argument("file", type=Path)
    e.add_argument("--offset", type=lambda v: int(v, 0), required=True)
    e.add_argument("--expected", type=bytes.fromhex, required=True)
    e.add_argument("--new", type=bytes.fromhex, required=True)
    m = sub.add_parser("make")
    m.add_argument("original", type=Path)
    m.add_argument("built", type=Path)
    m.add_argument("out", type=Path)
    a = sub.add_parser("apply")
    a.add_argument("patch", type=Path)
    a.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "edit":
            print(patch_bytes(args.file, args.offset, args.expected, args.new))
        elif args.command == "make":
            manifest = make_patch(args.original, args.built, args.out)
            print(f"PATCH ranges={len(manifest['ranges'])} -> {args.out}")
        else:
            print(apply_patch(args.patch, args.target))
    except (RuntimeError, ValueError) as error:
        print(f"ERROR {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
