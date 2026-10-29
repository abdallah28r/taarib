"""Guarded byte edits and byte-range patches for large game files.

    python scripts/byte_patch.py edit <copy> --offset 0x41F8C8 --expected 8B4508 --new 8B450C
    python scripts/byte_patch.py make <original> <built> <out.arpatch>
    python scripts/byte_patch.py apply <out.arpatch> <target> --root <game-folder>

For archives or disc images too large to ship whole: `make` stores only the
changed ranges with the original and result SHA-256; `apply` refuses any other
file version, writes a temporary copy, checks the result hash, then swaps,
keeping one verified original in the game backup store. `edit` changes bytes in place only when
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
import sys
import tempfile
import zlib
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_replace import install as install_replacement  # noqa: E402
from storage_core import digest, no_link_components, require_space  # noqa: E402

SIGNATURE = "ARPATCH1"


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    return digest(path, chunk)


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
    no_link_components(original)
    no_link_components(built)
    no_link_components(out)
    if out.resolve() in {original.resolve(), built.resolve()}:
        raise ValueError("patch output must differ from both source files")
    # Scan in blocks, but store only the exact changed byte runs.
    source_size, result_size = original.stat().st_size, built.stat().st_size
    require_space(out.parent, 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    ranges: list[list[int]] = []
    payload_hash = hashlib.sha256()
    with tempfile.TemporaryFile(dir=out.parent) as payload, original.open("rb") as source, built.open("rb") as result:
        common = min(source_size, result_size)
        offset = 0
        while offset < common:
            length = min(4096, common - offset)
            before, after = source.read(length), result.read(length)
            if before != after:
                require_space(out.parent, sum(a != b for a, b in zip(before, after)))
                position = 0
                while position < len(after):
                    while position < len(after) and before[position] == after[position]:
                        position += 1
                    start = position
                    while position < len(after) and before[position] != after[position]:
                        position += 1
                    if start == position:
                        continue
                    run_offset = offset + start
                    changed = after[start:position]
                    if ranges and ranges[-1][0] + ranges[-1][1] == run_offset:
                        ranges[-1][1] += len(changed)
                    else:
                        ranges.append([run_offset, len(changed)])
                    payload.write(changed)
                    payload_hash.update(changed)
            offset += length
        if result_size > common:
            ranges.append([common, result_size - common])
            while block := result.read(1 << 20):
                require_space(out.parent, len(block))
                payload.write(block)
                payload_hash.update(block)
        manifest = {
            "signature": SIGNATURE,
            "source": {"size": source_size, "sha256": sha256(original)},
            "result": {"size": result_size, "sha256": sha256(built)},
            "ranges": ranges,
            "payload_sha256": payload_hash.hexdigest(),
        }
        blob = json.dumps(manifest).encode()
        staged = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=out.parent,
                                             prefix=".taarib-bytepatch-") as patch:
                staged = Path(patch.name)
                require_space(out.parent, len(blob) + 4)
                patch.write(len(blob).to_bytes(4, "little") + blob)
                compressor = zlib.compressobj(9)
                payload.seek(0)
                while block := payload.read(1 << 20):
                    encoded = compressor.compress(block)
                    require_space(out.parent, len(encoded))
                    patch.write(encoded)
                encoded = compressor.flush()
                require_space(out.parent, len(encoded))
                patch.write(encoded)
            os.replace(staged, out)
        finally:
            if staged is not None and staged.exists():
                staged.unlink()
    return manifest


def apply_patch(patch: Path, target: Path, root: Path | None = None) -> str:
    no_link_components(patch)
    no_link_components(target)
    no_link_components(root or target.parent)
    with patch.open("rb") as input_file:
        size_bytes = input_file.read(4)
        if len(size_bytes) != 4:
            raise RuntimeError("truncated byte patch")
        size = int.from_bytes(size_bytes, "little")
        if size > 16 << 20:
            raise RuntimeError("byte patch header too large")
        manifest = json.loads(input_file.read(size))
        if manifest.get("signature") != SIGNATURE:
            raise RuntimeError("not a byte_patch file")
        ranges = manifest["ranges"]
        if not isinstance(ranges, list) or any(not isinstance(row, list) or len(row) != 2 for row in ranges):
            raise RuntimeError("invalid byte patch ranges")
        last = 0
        for offset, length in ranges:
            if not isinstance(offset, int) or not isinstance(length, int) or offset < last or length < 0:
                raise RuntimeError("invalid byte patch ranges")
            last = offset + length
        if last > manifest["result"]["size"]:
            raise RuntimeError("byte patch range exceeds result size")
        needed = sum(length for _, length in ranges)
        require_space(target.parent, target.stat().st_size + needed)
        with tempfile.TemporaryFile(dir=target.parent) as payload:
            decoder = zlib.decompressobj()
            payload_hash = hashlib.sha256()
            written = 0
            while block := input_file.read(1 << 20):
                compressed = block
                while compressed:
                    raw = decoder.decompress(compressed, 1 << 20)
                    compressed = decoder.unconsumed_tail
                    if written + len(raw) > needed:
                        raise RuntimeError("byte patch payload too large")
                    written += len(raw)
                    payload.write(raw)
                    payload_hash.update(raw)
                    if decoder.eof:
                        if decoder.unused_data or compressed or input_file.read(1):
                            raise RuntimeError("unexpected bytes after byte patch payload")
                        break
                if decoder.eof:
                    break
            if not decoder.eof or written != needed or payload_hash.hexdigest() != manifest["payload_sha256"]:
                raise RuntimeError("patch payload corrupted")
            return _apply_verified_payload(manifest, payload, target, root)


def _apply_verified_payload(manifest: dict, payload, target: Path, root: Path | None) -> str:
    if manifest.get("signature") != SIGNATURE:
        raise RuntimeError("not a byte_patch file")
    current = sha256(target)
    if current == manifest["result"]["sha256"]:
        return "already-installed"
    if current != manifest["source"]["sha256"]:
        raise RuntimeError("unsupported file version (hash mismatch); nothing written")
    no_link_components(target)
    no_link_components(root or target.parent)
    game_root = (root or target.parent).resolve()
    if game_root not in target.resolve().parents:
        raise RuntimeError("target must be inside the game root")
    require_space(target.parent, target.stat().st_size * 2)
    staging_root = game_root / "backups" / ".byte-patch"
    no_link_components(staging_root, game_root)
    transaction = staging_root / uuid4().hex
    transaction.mkdir(parents=True)
    (transaction / "owner.json").write_text('{"owner":"taarib-byte-patch-v1"}\n', encoding="utf-8")
    temporary = transaction / "candidate"
    try:
        shutil.copyfile(target, temporary)
        with temporary.open("r+b") as handle:
            handle.truncate(manifest["result"]["size"])
            payload.seek(0)
            for offset, length in manifest["ranges"]:
                handle.seek(offset)
                remaining = length
                while remaining:
                    block = payload.read(min(remaining, 1 << 20))
                    if not block:
                        raise RuntimeError("patch payload truncated")
                    handle.write(block)
                    remaining -= len(block)
        if sha256(temporary) != manifest["result"]["sha256"]:
            raise RuntimeError("result hash mismatch; original untouched")
        record = install_replacement(game_root, target, temporary)
        return f"installed (backup: {record['backup']})"
    finally:
        if temporary.exists():
            temporary.unlink()
        if transaction.exists():
            (transaction / "owner.json").unlink()
            transaction.rmdir()


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
    a.add_argument("--root", type=Path, help="game root for the single verified original (defaults to target parent)")
    args = parser.parse_args(argv)
    try:
        if args.command == "edit":
            print(patch_bytes(args.file, args.offset, args.expected, args.new))
        elif args.command == "make":
            manifest = make_patch(args.original, args.built, args.out)
            print(f"PATCH ranges={len(manifest['ranges'])} -> {args.out}")
        else:
            print(apply_patch(args.patch, args.target, args.root))
    except (RuntimeError, ValueError) as error:
        print(f"ERROR {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
