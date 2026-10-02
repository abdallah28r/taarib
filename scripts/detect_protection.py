"""Conservative filename-only protection/anti-cheat preflight.

This scanner never opens binaries. A clean result is not proof that a game is
unprotected; a hit is a stop signal for modification until the user decides.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path


SIGNATURES = {
    "Easy Anti-Cheat": ("easyanticheat*", "easyanticheat_eos*"),
    "BattlEye": ("battleye", "beservice*", "beclient*"),
    "EA AntiCheat": ("eaanticheat*",),
    "Riot Vanguard": ("vgc*", "vgk*"),
    "nProtect GameGuard": ("gameguard", "npgg*", "nprotect*"),
    "XIGNCODE": ("xigncode*", "xhunter*"),
    "Denuvo marker": ("denuvo*",),
    "VMProtect marker": ("vmprotect*",),
}


def scan(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for base, dirs, files in os.walk(root):
        names = dirs + files
        for product, patterns in SIGNATURES.items():
            for name in names:
                if any(fnmatch.fnmatch(name.lower(), pattern) for pattern in patterns):
                    rel = (Path(base) / name).relative_to(root).as_posix()
                    hits.setdefault(product, []).append(rel)
    return {key: sorted(set(value)) for key, value in sorted(hits.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.game_root.is_dir():
        print(f"ERROR not a directory: {args.game_root}")
        return 3
    hits = scan(args.game_root)
    report = {
        "root": str(args.game_root.resolve()),
        "verdict": "stop-and-review" if hits else "no-filename-marker-found",
        "hits": hits,
        "warning": "Filename-only helper. It neither detects every protection system nor authorizes bypassing one.",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 2 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
