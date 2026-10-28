"""Read-only game-engine fingerprinting from filenames and directory layout."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


MARKERS = {
    "unity": {
        "unityplayer.dll": 5,
        "globalgamemanagers": 4,
        "resources.assets": 3,
        "gameassembly.dll": 2,
        "global-metadata.dat": 2,
    },
    "unreal": {
        ".pak": 2,
        ".utoc": 4,
        ".ucas": 4,
        ".uasset": 2,
        ".locres": 3,
        "binaries/win64": 2,
    },
    "renpy": {"renpy": 4, ".rpy": 3, ".rpyc": 2, ".rpa": 2},
    "rpg-maker-mz": {"rmmz_core.js": 8, "js/plugins.js": 2, "data/system.json": 2},
    "rpg-maker-mv": {"rpg_core.js": 8, "js/plugins.js": 2, "data/system.json": 2},
    "godot": {"project.godot": 8, ".pck": 3, ".tscn": 2, ".tres": 2},
    "source": {"gameinfo.txt": 6, ".vpk": 3},
    "gamemaker": {"data.win": 8, ".yyz": 4},
    "paradox-clausewitz": {"launcher-settings.json": 4, "fonts.font": 3, "_l_english.yml": 4},
    "bannerlord": {"submodule.xml": 6, "language_data.xml": 4, "bannerlordconfig.txt": 3},
    # Weights beat the generic markers these games also carry (Unity for RimWorld, .NET for Stardew).
    "age-of-empires-ii": {"aoe2de_s.exe": 10, "key-value-strings-utf8.txt": 6, "aok hd.exe": 10, "resources/_common": 2},
    "stardew-valley": {"stardew valley.dll": 12, "stardew valley.exe": 12, "content/fonts": 2, "stardewmoddingapi.exe": 3},
    "monogame-xna": {"monogame.framework.dll": 8, "fna.dll": 8, ".xnb": 3, "runtimeconfig.json": 1},
    "scumm-scummvm": {"speech.info": 6, "uitext.info": 6, "monkey1.000": 8, "monkey2.000": 8, "comi.la0": 8,
                      "language.tab": 4, ".nut": 2},
    "grime-emi": {"grimfandango.exe": 8, "monkey4.exe": 8, ".m4b": 4, ".lab": 3, "script.tab": 4},
    "telltale": {".ttarch": 8, ".ttarch2": 8, ".langdb": 4, ".d3dtx": 2},
    "dinky": {"ggpack": 8, "text_en.tsv": 3},
    "android-apk": {".apk": 8, "androidmanifest.xml": 6, "classes.dex": 4},
    "ps1": {".cue": 4, "system.cnf": 2},
    "ps2": {".iso": 4, "system.cnf": 2},
    "rimworld": {"rimworldwin64_data": 10, "data/core/languages": 4, "data/core/defs": 2},
}

LOADERS = {
    "bepinex": ("bepinex", "winhttp.dll", "doorstop_config.ini"),
    "ue4ss": ("ue4ss", "ue4ss.dll", "ue4ss-settings.ini"),
    "melonloader": ("melonloader", "version.dll"),
    "reipatcher": ("reipatcher",),
    "smapi": ("stardewmoddingapi.exe", "smapi-internal"),
}


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
