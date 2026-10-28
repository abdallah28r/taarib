"""Learn what a game can show without playing it: engine, fonts, Arabic preview, logs.

    python scripts/loc.py probe --game <game_root>                              # engine + fonts + known logs
    python scripts/loc.py probe --game <root> --preview --font <ttf> --size 24 --width 600 [--text file]
    python scripts/loc.py probe --game <root> --since-minutes 20 [--record]      # find logs written by a launch
    python scripts/loc.py probe --game <root> --launch <exe> [--seconds 45]       # only with allow_launch_game

Read-only on the game folder. It reports:

- **engine**: `detect_engine.py`'s verdict and existing mod loaders.
- **fonts**: every TTF/OTF/TTC, BMFont `.fnt`, and font-like asset in the
  game; for TTF/OTF whether it has Arabic letters, presentation forms, and an
  Arabic shaping table (`GSUB` with the `arab` script); for text `.fnt` how
  many Arabic characters it holds. A font without Arabic means a fallback,
  extension, or replacement (references/arabic-rendering.md).
- **preview** (`--preview`): draws sample lines the way a left-to-right
  engine would (shaped, wrapped by `--width`, reversed per line) with the
  game's own font into `work/probe/preview.png`, and lists lines wider than the
  box and characters the font lacks. Lines come from `--text` or translated
  units. This replaces neither the pilot nor the user's eyes.
- **logs**: first the engine's known log paths (boot_verdict.py and the
  engine profile); if none is known or none is fresh, it searches the game
  folder and the usual user folders (LocalLow, AppData, Documents, Saved
  Games) for log files written in the last `--since-minutes`. `--record`
  writes a discovered path into `engines/<engine>.md` under `## Logs`, as a
  candidate, so the next game on the engine finds it directly. Each log gets
  boot_verdict's judgement (crash, new errors, missing Arabic glyphs).
- **launch** (`--launch <exe>`): starts the game, waits `--seconds`, closes
  it, and reads its logs; refused unless PROJECT.yaml
  `workflow.allow_launch_game` is true.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_EXT = {".ttf", ".otf", ".ttc", ".fnt", ".laf", ".nut", ".font", ".spritefont"}
FONT_NAME = re.compile(r"font|sdf|glyph", re.I)
LOG_NAME = re.compile(r"(?:\.log$|log.*\.txt$|^(?:player|output|errors?|traceback|emulog|crash).*\.txt$)", re.I)
SEARCH_ROOTS = ["%USERPROFILE%/AppData/LocalLow", "%APPDATA%", "%LOCALAPPDATA%",
                "%USERPROFILE%/Documents", "%USERPROFILE%/Saved Games"]
SAMPLE = ["اضغط F لفتح الباب", "المستوى ٢٥ — RTX 4080", "حصلت على 50% من الذهب (رائع!)",
          "قال {name}: لا إله إلا الله، شيء جميل في هذا اليوم الطويل جدًا"]


def _load(name: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def font_report(path: Path) -> dict:
    info: dict = {"path": str(path), "kind": path.suffix.lower().lstrip(".") or "asset"}
    suffix = path.suffix.lower()
    try:
        if suffix in {".ttf", ".otf", ".ttc"}:
            from fontTools.ttLib import TTFont
            font = TTFont(str(path), lazy=True, fontNumber=0)
            cmap = set(font.getBestCmap())
            letters = sum(0x0621 <= c <= 0x064A for c in cmap)
            forms = sum(0xFE70 <= c <= 0xFEFF for c in cmap)
            scripts = set()
            if "GSUB" in font:
                scripts = {r.ScriptTag for r in font["GSUB"].table.ScriptList.ScriptRecord}
            info.update(arabic_letters=letters, presentation_forms=forms, shapes_arabic="arab" in scripts,
                        verdict="arabic" if letters >= 36 else "partial-arabic" if letters else "no-arabic")
        elif suffix == ".fnt" and path.stat().st_size < 4_000_000:
            text = path.read_text(encoding="utf-8", errors="ignore")
            ids = {int(x) for x in re.findall(r"char\s+id=\"?(\d+)", text)}
            arabic = sum(0x0600 <= c <= 0x06FF or 0xFB50 <= c <= 0xFEFF for c in ids)
            info.update(chars=len(ids), arabic_chars=arabic, verdict="arabic" if arabic >= 36 else
                        "partial-arabic" if arabic else "no-arabic" if ids else "binary-or-unknown")
        else:
            info["verdict"] = "inspect-with-engine-tools"
    except Exception as error:  # a damaged or unusual font is a finding, not a crash
        info["verdict"] = f"unreadable: {type(error).__name__}"
    return info


def find_fonts(game: Path, limit: int = 200) -> list[dict]:
    found = []
    for base, dirs, files in os.walk(game):
        dirs[:] = [d for d in dirs if d.lower() not in {".git", "backups", "__pycache__"}]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() in FONT_EXT or (FONT_NAME.search(name) and path.suffix.lower() in {".dds", ".png", ".xnb", ".asset"}):
                found.append(font_report(path))
                if len(found) >= limit:
                    return found
    return found


def preview(font: Path, size: float, width: float, lines: list[str], out: Path) -> dict:
    from PIL import Image, ImageDraw, ImageFont
    from fontTools.ttLib import TTFont
    shaping = _load("arabic_shaping")
    cmap = set(TTFont(str(font), lazy=True).getBestCmap())
    measure = shaping.font_measure(font, size)
    pil_font = ImageFont.truetype(str(font), int(size), layout_engine=ImageFont.Layout.BASIC)  # no BiDi: draw like the engine
    rendered = [shaping.render(line, max_width=width, measure=measure).split("\n") for line in lines]
    rows = [row for block in rendered for row in block + [""]]
    line_height = int(size * 1.6)
    image = Image.new("RGB", (int(width) + 40, line_height * len(rows) + 20), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 0, 20 + width, image.height], outline="#c00")
    for index, row in enumerate(rows):
        draw.text((20, 10 + index * line_height), row, font=pil_font, fill="black")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    too_wide = [row for row in rows if row and measure(row) > width]
    missing = sorted({c for row in rows for c in row if not c.isspace() and ord(c) not in cmap})
    return {"png": str(out), "lines": len(lines), "too_wide": too_wide[:10],
            "missing_glyphs": [f"U+{ord(c):04X} {c}" for c in missing][:40]}


def _expand(pattern: str) -> str | None:
    value = os.path.expandvars(pattern)
    return None if "%" in value else value


def discover_logs(game: Path, since: float, depth: int = 4) -> list[Path]:
    """Log-like files modified after `since` in the game folder and the usual user folders."""
    roots = [game] + [Path(p) for p in map(_expand, SEARCH_ROOTS) if p]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        base_depth = len(root.parts)
        for base, dirs, files in os.walk(root):
            if len(Path(base).parts) - base_depth >= depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if d.lower() not in {"backups", ".git", "node_modules", "cache", "temp"}]
            for name in files:
                path = Path(base) / name
                try:
                    if LOG_NAME.search(name) and path.stat().st_mtime >= since:
                        found.append(path)
                except OSError:
                    continue
    return sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)


def belongs(path: Path, game: Path) -> bool:
    """In the game folder, or a user-folder path naming the game (a word of 4+ letters from its folder name)."""
    if game in path.parents:
        return True
    words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", game.name)]
    return any(w in str(path).lower() for w in words)


def generalize(path: Path, game: Path) -> str:
    try:
        return "{game}/" + path.relative_to(game).as_posix()
    except ValueError:
        pass
    text = str(path)
    for var in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        value = os.environ.get(var)
        if value and text.lower().startswith(value.lower()):
            return f"%{var}%" + text[len(value):].replace("\\", "/")
    return text


def record_log(engine: str, pattern: str) -> bool:
    profile = ROOT / "engines" / f"{engine}.md"
    if not profile.is_file():
        return False
    text = profile.read_text(encoding="utf-8")
    if pattern in text:
        return False
    line = f"- Discovered by `loc.py probe` on {date.today().isoformat()} (candidate): `{pattern}`\n"
    if "\n## Logs\n" in text:
        head, tail = text.split("\n## Logs\n", 1)
        body, sep, rest = tail.partition("\n## ")
        text = head + "\n## Logs\n" + body.rstrip("\n") + "\n" + line + (sep + rest if sep else "")
    else:
        text = text.rstrip("\n") + "\n\n## Logs\n\n" + line
    profile.write_text(text, encoding="utf-8")
    return True


def launch_allowed() -> bool:
    import yaml
    flow = (yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}).get("workflow") or {}
    return flow.get("allow_launch_game") is True


def launch(exe: Path, seconds: float) -> dict:
    started = time.time()
    process = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        process.wait(timeout=seconds)
        state = f"exited by itself with code {process.returncode}"
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        else:
            process.kill()
        state = f"closed after {seconds:g} s"
    return {"exe": str(exe), "started": started, "state": state}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loc.py probe", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--engine", help="engine id; default: detect_engine.py's verdict")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--font", type=Path, help="TTF/OTF for --preview (the game's own font when possible)")
    parser.add_argument("--size", type=float, default=24)
    parser.add_argument("--width", type=float, default=600, help="text box width in pixels")
    parser.add_argument("--text", type=Path, help="UTF-8 file, one logical Arabic line per line")
    parser.add_argument("--since-minutes", type=float, default=30, help="logs older than this are not from this launch")
    parser.add_argument("--record", action="store_true", help="write discovered log paths into engines/<engine>.md")
    parser.add_argument("--launch", type=Path, help="game executable to start and close (needs allow_launch_game)")
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "probe")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not args.game.is_dir():
        print(f"ERROR not a folder: {args.game}")
        return 2

    detection = _load("detect_engine").detect(args.game)
    engine = args.engine or detection["engine"]
    report: dict = {"engine": engine, "confidence": detection["confidence"],
                    "loaders": sorted(detection["existing_loaders"]), "fonts": find_fonts(args.game)}

    since = time.time() - args.since_minutes * 60
    if args.launch:
        if not launch_allowed():
            print("ERROR PROJECT.yaml workflow.allow_launch_game is not true; ask the user to start the game instead")
            return 2
        report["launch"] = launch(args.launch, args.seconds)
        since = report["launch"]["started"] - 5

    if args.preview:
        if not args.font:
            print("ERROR --preview needs --font (a TTF/OTF; take the game's own from the fonts list)")
            return 2
        lines = SAMPLE
        if args.text:
            lines = [line for line in args.text.read_text(encoding="utf-8").splitlines() if line.strip()]
        report["preview"] = preview(args.font, args.size, args.width, lines[:60], args.out / "preview.png")

    boot = _load("boot_verdict")
    key = "stardew-valley" if engine == "stardew-valley" else engine
    known = boot.candidates(key, args.game) if key in boot.LOG_PATTERNS else []
    fresh_known = [p for p in known if p.stat().st_mtime >= since]
    other: list[Path] = []
    if fresh_known:
        logs, source = fresh_known, "engine profile"
    else:
        recent = discover_logs(args.game, since)
        logs, source = [p for p in recent if belongs(p, args.game.resolve())], "discovered"
        other = [p for p in recent if p not in logs]
    report["logs"] = {"source": source, "files": [str(p) for p in logs[:10]],
                      "other_recent_logs_ignored": len(other)}  # other programs' logs: count only, never listed
    if logs:
        report["boot"] = boot.judge(logs[:5], args.since_minutes + 1)
        if source == "discovered" and args.record and engine != "unknown":
            report["logs"]["recorded"] = [g for g in dict.fromkeys(generalize(p, args.game) for p in logs[:3])
                                          if record_log(engine, g)]
    else:
        report["logs"]["next"] = ("No fresh log: ask the user to start the game, or use --launch when "
                                  "allow_launch_game is true, then run probe again.")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
