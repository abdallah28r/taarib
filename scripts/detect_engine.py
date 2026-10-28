"""Read-only game-engine fingerprinting from filenames and directory layout."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


MARKERS_FILE = Path(__file__).resolve().parents[1] / "config" / "engine-markers.json"
_CONFIG = json.loads(MARKERS_FILE.read_text(encoding="utf-8"))
MARKERS: dict[str, dict[str, int]] = _CONFIG["engines"]  # edit config/engine-markers.json, not this file
LOADERS: dict[str, tuple[str, ...]] = {name: tuple(markers) for name, markers in _CONFIG["loaders"].items()}


def inventory(root: Path, max_files: int = 250_000) -> list[str]:
    items: list[str] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in {".git", "__pycache__"}]
        base_path = Path(base)
        for name in dirs + files:
            try:
                rel = (base_path / name).relative_to(root).as_posix().lower()
            except ValueError:
                continue
            items.append(rel)
            if len(items) >= max_files:
                return items
    return items


def _matches(path: str, marker: str) -> bool:
    if marker.startswith("."):
        return path.endswith(marker)
    return marker in path or Path(path).name == marker


def detect(root: Path) -> dict:
    paths = inventory(root)
    scores: dict[str, int] = defaultdict(int)
    evidence: dict[str, list[str]] = defaultdict(list)
    for engine, markers in MARKERS.items():
        for marker, weight in markers.items():
            hits = [path for path in paths if _matches(path, marker)]
            if hits:
                scores[engine] += weight
                evidence[engine].extend(hits[:3])

    # SYSTEM.CNF says which PlayStation: BOOT2 = PS2, BOOT = PS1.
    cnf = next((root / p for p in paths if Path(p).name == "system.cnf"), None)
    if cnf and cnf.is_file():
        text = cnf.read_bytes()[:512].upper()
        scores["ps2" if b"BOOT2" in text else "ps1"] += 6
    ranked = sorted(scores, key=lambda name: (-scores[name], name))
    winner = ranked[0] if ranked and scores[ranked[0]] >= 4 else "unknown"
    confidence = "unknown"
    if winner != "unknown":
        confidence = "high" if scores[winner] >= 8 else "medium"
        if len(ranked) > 1 and scores[ranked[0]] - scores[ranked[1]] < 2:
            confidence = "low"

    loaders: dict[str, list[str]] = {}
    for name, markers in LOADERS.items():
        hits = sorted({path for path in paths for marker in markers if _matches(path, marker)})
        if hits:
            loaders[name] = hits[:10]

    backend = None
    if winner == "unity":
        names = {Path(path).name for path in paths}
        if "gameassembly.dll" in names and "global-metadata.dat" in names:
            backend = "il2cpp"
        elif any("/managed/" in f"/{path}/" for path in paths):
            backend = "mono"

    return {
        "root": str(root.resolve()),
        "engine": winner,
        "confidence": confidence,
        "scripting_backend": backend,
        "scores": dict(sorted(scores.items(), key=lambda item: (-item[1], item[0]))),
        "evidence": {key: sorted(set(value)) for key, value in evidence.items()},
        "existing_loaders": loaders,
        "files_examined": len(paths),
        "warning": "Filename/layout fingerprinting only; confirm with format evidence before modifying files.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.game_root.is_dir():
        print(f"ERROR not a directory: {args.game_root}")
        return 2
    report = detect(args.game_root)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
