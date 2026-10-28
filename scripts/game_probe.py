"""Learn what a game can show without playing it: engine, fonts, Arabic preview, logs.

    python scripts/loc.py probe --game <game_root>                              # engine + fonts + known logs
    python scripts/loc.py probe --game <root> --preview --font <ttf> --size 24 --width 600 [--text file]
    python scripts/loc.py probe --game <root> --since-minutes 20 [--record]      # find logs written by a launch
    python scripts/loc.py probe --game <root> --engine <new-id> --record          # start a profile for an unknown engine
    python scripts/loc.py probe --game <root> --deep-fonts                        # also fonts inside Unity assets
    python scripts/loc.py probe --game <root> --save-baseline                     # after a launch of the unpatched game
    python scripts/loc.py probe --game <root> --launch <exe> [--seconds 45]       # only with allow_launch_game

Read-only on the game folder (it writes only under `--out`, default work/probe,
and, with --record, into engines/ and the tool catalog). It reports:

- **engine**: `detect_engine.py`'s verdict, its profile file, and existing mod loaders.
- **fonts**: every loose TTF/OTF/TTC, BMFont `.fnt`, and font-like asset in
  the game; for TTF/OTF whether it has Arabic letters, presentation forms, and
  an Arabic shaping table (`GSUB` with the `arab` script); for text `.fnt` how
  many Arabic characters it holds. `--deep-fonts` also reads Unity assets and
  saves each embedded font to `<out>/fonts/` for the preview; the last entry
  says how many asset files were read. Fonts inside other engines' archives
  need that engine's tools. A font without Arabic means a fallback,
  extension, or replacement (references/arabic-rendering.md).
- **preview** (`--preview --font <file>`): draws lines in the game's font at
  the box width into `<out>/preview.png` and lists lines wider than the box
  and characters the font lacks. Default: as a `needs_preshape` engine shows
  them (shaped, wrapped, reversed per line, drawn left to right); `--native`:
  as an engine that shapes Arabic itself (logical text through HarfBuzz).
  Lines come from `--text`, else translated units (pilot first), else samples.
  This replaces neither the pilot nor the user's eyes.
- **logs**: first the exact paths from the game's own names (Unity's
  `app.info` company/product, Unreal's project folder), the paths written in
  the engine profile's `## Logs`, and boot_verdict.py's engine patterns; if
  none is fresh, it searches the game
  folder and the usual user folders (LocalLow, AppData, Documents, Saved
  Games) for log files written in the last `--since-minutes`. `--record`
  writes a discovered path into `engines/<engine>.md` under `## Logs`, as a
  candidate, so the next game on the engine finds it directly. Each log gets
  boot_verdict's judgement (crash, new errors, missing Arabic glyphs). Most
  games log some errors on every start: run once with `--save-baseline` after
  a launch of the unpatched game, and later runs count only new errors.
- **launch** (`--launch <exe>`): starts the game, waits `--seconds`, force-
  closes it, and reads its logs; refused unless PROJECT.yaml
  `workflow.allow_launch_game` is true. Snapshot the saves first
  (`save_guard.py`): a forced close can interrupt a save.
"""
from __future__ import annotations

import argparse
import glob
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
LOG_NAME = re.compile(r"(?:\.log$|^(?:log|player|output|errors?|traceback|emulog|crash|smapi)[^/\\]*\.txt$)", re.I)
# Words too common to tie a log to one game (company words such as "studio" match unrelated programs).
STOP_WORDS = {"game", "games", "launcher", "setup", "unitycrashhandler", "unins", "redist", "vcredist", "dxsetup",
              "studio", "studios", "interactive", "entertainment", "software", "edition", "definitive",
              "remastered", "windows", "shipping", "binaries", "content"}
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


def font_report(path: Path, data: bytes | None = None) -> dict:
    """Arabic support of one font file, or of font bytes taken out of an asset (`data`)."""
    info: dict = {"path": str(path), "kind": path.suffix.lower().lstrip(".") or "asset"}
    suffix = ".ttf" if data else path.suffix.lower()
    try:
        if suffix in {".ttf", ".otf", ".ttc"}:
            import io
            from fontTools.ttLib import TTFont
            with TTFont(io.BytesIO(data) if data else str(path), lazy=True, fontNumber=0) as font:
                cmap = set(font.getBestCmap())
                scripts = set()
                script_list = getattr(font["GSUB"].table, "ScriptList", None) if "GSUB" in font else None
                if script_list is not None:  # some fonts carry a GSUB table without a script list
                    scripts = {r.ScriptTag for r in script_list.ScriptRecord}
            letters = sum(0x0621 <= c <= 0x064A for c in cmap)
            forms = sum(0xFE70 <= c <= 0xFEFF for c in cmap)
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
        info["verdict"] = (f"unreadable by fontTools ({type(error).__name__}: {str(error)[:80]}); "
                           "the game may still load it, check with the engine's tools")
    return info


def unity_fonts(game: Path, out: Path, max_files: int = 80, max_mb: int = 1024) -> list[dict]:
    """Fonts inside Unity assets and bundles (needs UnityPy): Font assets get the TTF check and are
    saved to `out/fonts/` so `--preview --font` can use the game's own face; TextMeshPro font assets
    are counted by the Arabic characters in their character table. Files most likely to hold fonts
    are read first; the last entry says how many files were read and skipped."""
    try:
        import UnityPy
    except ImportError:
        return [{"path": "-", "kind": "unity", "verdict": "UnityPy is not installed (engines/unity.md); fonts inside assets not read"}]
    data = next(game.glob("*_Data"), None)
    if not data:
        return []
    candidates = [p for p in data.rglob("*") if p.is_file() and p.name not in {"app.info", "boot.config"}
                  and p.suffix.lower() in {".assets", ".bundle", ".unity3d", ""}]

    def priority(path: Path) -> tuple:
        name = path.name.lower()
        return (0 if "font" in name else 1 if name.startswith(("resources", "sharedassets", "data.unity3d")) else 2,
                path.stat().st_size)
    candidates.sort(key=priority)
    too_big = [p for p in candidates if p.stat().st_size > max_mb * 1_048_576]
    files = [p for p in candidates if p not in too_big][:max_files]
    found = []
    for path in files:
        try:
            env = UnityPy.load(str(path))
        except Exception:
            continue
        for obj in env.objects:
            kind = obj.type.name
            try:
                if kind == "Font":
                    font = obj.read()
                    raw = bytes(getattr(font, "m_FontData", b"") or b"")
                    info = {"path": f"{path.name}:{getattr(font, 'm_Name', '?')}", "kind": "unity-font"}
                    if raw:
                        info.update({k: v for k, v in font_report(path, raw).items() if k not in {"path", "kind"}})
                        safe = re.sub(r"[^\w.-]+", "_", str(getattr(font, "m_Name", "font")))
                        saved = out / "fonts" / f"{safe}.{'otf' if raw[:4] == b'OTTO' else 'ttf'}"
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        saved.write_bytes(raw)
                        info["extracted"] = str(saved)
                    else:
                        info["verdict"] = "no embedded font data (built-in or OS font)"
                    found.append(info)
                elif kind == "MonoBehaviour":
                    tree = obj.read_typetree()
                    table = tree.get("m_CharacterTable") if isinstance(tree, dict) else None
                    if table is not None:
                        codes = [c.get("m_Unicode", 0) for c in table]
                        arabic = sum(0x0600 <= c <= 0x06FF or 0xFB50 <= c <= 0xFEFF for c in codes)
                        found.append({"path": f"{path.name}:{tree.get('m_Name', '?')}", "kind": "tmp-font-asset",
                                      "chars": len(codes), "arabic_chars": arabic,
                                      "verdict": "arabic" if arabic >= 36 else "partial-arabic" if arabic else "no-arabic"})
            except Exception:
                continue
    found.append({"path": "-", "kind": "unity-coverage", "verdict": f"read {len(files)} of {len(candidates)} asset files; "
                  f"skipped {len(candidates) - len(files)} ({len(too_big)} over {max_mb} MB)"})
    return found


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


def unit_lines(limit: int = 60) -> list[str]:
    """Translated targets from units/ (pilot batch first), for a preview of the real text."""
    rows = []
    for path in sorted((ROOT / "units").rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                unit = json.loads(line)
            except ValueError:
                continue
            if unit.get("target") and unit.get("status") != "extracted":
                rows.append((unit.get("batch") != "pilot", unit["target"]))
    return [target for _, target in sorted(rows, key=lambda r: r[0])][:limit]


def preview(font: Path, size: float, width: float, lines: list[str], out: Path, native: bool = False) -> dict:
    """Draw lines in the game's font at the box width.

    Default: as a left-to-right engine shows pre-shaped text (`needs_preshape`):
    shaped, wrapped by measure, reversed per line, drawn without BiDi.
    native=True: as an engine that shapes Arabic itself (`native`): logical text
    drawn right to left with HarfBuzz (Pillow with raqm), so the font needs
    Arabic letters and its shaping table, not presentation forms.
    """
    from PIL import Image, ImageDraw, ImageFont, features
    from fontTools.ttLib import TTFont
    shaping = _load("arabic_shaping")
    with TTFont(str(font), lazy=True, fontNumber=0) as opened:
        cmap = set(opened.getBestCmap())
    measure = shaping.font_measure(font, size, keep_codes=True)  # the image draws {name} as written
    if native and not features.check("raqm"):
        return {"error": "Pillow on this machine has no raqm (HarfBuzz layout); native preview unavailable"}
    layout = ImageFont.Layout.RAQM if native else ImageFont.Layout.BASIC  # BASIC: no BiDi, like the engine
    pil_font = ImageFont.truetype(str(font), int(round(size)), layout_engine=layout)
    if native:
        rows = [row for line in lines for row in shaping.wrap(line, width, measure) + [""]]
        too_wide = [row for row in rows if row and measure(shaping.shape(row)) > width]
    else:
        rows = [row for line in lines for row in shaping.render(line, max_width=width, measure=measure).split("\n") + [""]]
        too_wide = [row for row in rows if row and measure(row) > width]
    line_height = int(size * 1.6)
    image = Image.new("RGB", (int(width) + 40, line_height * len(rows) + 20), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 0, 20 + width, image.height], outline="#c00")
    for index, row in enumerate(rows):
        y = 10 + index * line_height
        if native:  # right-aligned in the box, as an Arabic UI would be
            draw.text((20 + width, y), row, font=pil_font, fill="black", direction="rtl", anchor="ra")
        else:
            draw.text((20, y), row, font=pil_font, fill="black")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    drawn = {c for row in rows for c in row if not c.isspace()}
    missing = sorted(c for c in drawn if ord(c) not in cmap and not shaping.CODE_RE.fullmatch(c))
    return {"png": str(out), "mode": "native" if native else "needs_preshape", "lines": len(lines),
            "too_wide": too_wide[:10], "missing_glyphs": [f"U+{ord(c):04X} {c}" for c in missing][:40]}


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


def game_names(game: Path) -> dict:
    """Names a game uses for its user folders: Unity's company/product (`<Name>_Data/app.info`),
    Unreal's project folder (the one holding `Binaries`), executable names, and the folder name."""
    names = {"folder": game.name, "exe": sorted(p.stem for p in game.glob("*.exe"))}
    info = next(game.glob("*_Data/app.info"), None)
    if info:
        lines = info.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) >= 2:
            names["unity_company"], names["unity_product"] = lines[0].strip(), lines[1].strip()
    project = _load("boot_verdict").unreal_project(game)
    if project:
        names["unreal_project"] = project
    return names


def name_words(names: dict) -> set[str]:
    """Words that tie a user-folder path to this game: product, project, executable, and folder names
    (never the company alone, which other programs share)."""
    values = [names.get(k) for k in ("folder", "unity_product", "unreal_project") if names.get(k)]
    values += list(names.get("exe", []))
    return {w.lower() for v in values for w in re.findall(r"[A-Za-z]{4,}", v)} - STOP_WORDS


def exact_candidates(names: dict) -> list[Path]:
    """Log paths derived from the game's own names (exact, unlike a search). Player-prev.log is
    the run before, so it is never judged as this launch."""
    found = []
    if "unity_product" in names:
        base = _expand("%USERPROFILE%/AppData/LocalLow")
        if base:
            found.append(Path(base) / names["unity_company"] / names["unity_product"] / "Player.log")
    if "unreal_project" in names:
        base = _expand("%LOCALAPPDATA%")
        if base:
            found += sorted((Path(base) / names["unreal_project"] / "Saved" / "Logs").glob("*.log"))
    return [p for p in found if p.is_file()]


def belongs(path: Path, game: Path, words: set[str] | None = None) -> bool:
    """In the game folder, or a user-folder path naming the game (Unity/Unreal names, exe, folder)."""
    if game in path.parents:
        return True
    words = words if words is not None else name_words(game_names(game))
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


ENGINE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
PATH_IN_TICKS = re.compile(r"`([^`]*(?:/|\\)[^`]*\.(?:log|txt))`", re.I)


def profile_name(engine: str) -> str:
    """detect_engine ids such as rpg-maker-mv map to their profile file (config/engine-profile-aliases.json)."""
    aliases = json.loads((ROOT / "config" / "engine-profile-aliases.json").read_text(encoding="utf-8"))
    return aliases.get(engine, engine)


def profile_log_paths(profile: str, game: Path) -> list[Path]:
    """Log paths written in engines/<profile>.md under `## Logs` (by hand or by --record)."""
    path = ROOT / "engines" / f"{profile}.md"
    if not path.is_file() or "\n## Logs\n" not in path.read_text(encoding="utf-8"):
        return []
    section = path.read_text(encoding="utf-8").split("\n## Logs\n", 1)[1].split("\n## ", 1)[0]
    found = []
    for pattern in PATH_IN_TICKS.findall(section):
        if "<" in pattern:  # a placeholder such as <package> cannot be expanded
            continue
        expanded = _expand(pattern.replace("{game}", glob.escape(str(game))))
        if expanded:
            found += [Path(p) for p in glob.glob(expanded)]
    return [p for p in found if p.is_file()]


def create_profile(engine: str, detection: dict, fonts: list[dict]) -> Path:
    """A minimal engines/<engine>.md for an engine the template does not know, plus its catalog entry."""
    if not ENGINE_ID.match(engine) or engine == "unknown":
        raise ValueError(f"engine id {engine!r}: name the engine with lowercase letters, digits, and hyphens")
    profile = ROOT / "engines" / f"{engine}.md"
    if profile.exists():
        return profile
    scores = ", ".join(f"{k} {v}" for k, v in list(detection["scores"].items())[:3]) or "none"
    font_kinds = ", ".join(sorted({f["kind"] for f in fonts})) or "none found as loose files"
    profile.write_text(f"""# {engine} profile

Evidence state: `candidate`; created by `loc.py probe` on {date.today().isoformat()} for an engine the
template did not know. Replace every line below with evidence from this game.

## Identification

- detect_engine.py scores at creation: {scores}.
- Add this engine's file and folder markers to `config/engine-markers.json`
  (an extension such as `.pak`, or a file name), then confirm with
  `python scripts/detect_engine.py <game_root>`.

## Localization locations

Unknown yet: record where the text, fonts ({font_kinds}), and images live.

## Workflow

Discovery is read-only; extract a small sample, prove a no-change round trip,
then decide the adapter and whether the renderer shows Arabic (native or
needs_preshape) in the pilot.

## Tools

Catalog tools: none yet. Details: `python scripts/tool_doctor.py --engine {engine}`. Install rules: step 4 of
`game-localization-engineering`. Add tools to `tools/open-source-tools.json`
with this engine's profile and name them here.

## Logs

## Limitations

Nothing is verified for this engine.

## Sources

Record the game, build, and every source used.
""", encoding="utf-8")
    catalog = ROOT / "tools" / "open-source-tools.json"
    text = catalog.read_text(encoding="utf-8")
    data = json.loads(text)
    if engine not in data.get("engines", {}):
        start = text.index('"engines": {')
        end = text.index("\n  }", start)
        text = text[:end] + f',\n    "{engine}": []' + text[end:]
        json.loads(text)
        catalog.write_text(text, encoding="utf-8")
    return profile


def record_log(engine: str, pattern: str, game_name: str = "") -> bool:
    profile = ROOT / "engines" / f"{profile_name(engine)}.md"
    if not profile.is_file():
        return False
    text = profile.read_text(encoding="utf-8")
    if pattern in text:
        return False
    seen = f" on {game_name}" if game_name else ""
    line = f"- Discovered by `loc.py probe`{seen}, {date.today().isoformat()} (candidate): `{pattern}`\n"
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
        if time.time() - started < 15:
            state += ("; it may have handed over to a launcher (Steam, Epic) and the game may still be "
                      "running: ask the user to close it")
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
    parser.add_argument("--native", action="store_true",
                        help="preview as an engine that shapes Arabic itself (logical text, HarfBuzz) instead of pre-shaped")
    parser.add_argument("--font", type=Path, help="TTF/OTF for --preview (the game's own font when possible)")
    parser.add_argument("--size", type=float, default=24)
    parser.add_argument("--width", type=float, default=600, help="text box width in pixels")
    parser.add_argument("--text", type=Path, help="UTF-8 file, one logical Arabic line per line "
                        "(default: translated units, pilot first; else built-in samples)")
    parser.add_argument("--save-baseline", action="store_true",
                        help="store this launch's log as the clean baseline (run on the unpatched game); later runs "
                             "ignore errors the baseline already had")
    parser.add_argument("--since-minutes", type=float, default=30, help="logs older than this are not from this launch")
    parser.add_argument("--record", action="store_true",
                        help="write discovered log paths into engines/<engine>.md; with --engine <new-id> for an "
                             "unknown engine, create that profile first")
    parser.add_argument("--deep-fonts", action="store_true", help="also read fonts inside Unity assets (UnityPy; slower)")
    parser.add_argument("--launch", type=Path, help="game executable to start and close (needs allow_launch_game)")
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "probe")
    args = parser.parse_args(argv)
    getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
    if not args.game.is_dir():
        print(f"ERROR not a folder: {args.game}")
        return 2

    detection = _load("detect_engine").detect(args.game)
    engine = args.engine or detection["engine"]
    profile = profile_name(engine)
    names = game_names(args.game)
    report: dict = {"engine": engine, "profile": f"engines/{profile}.md", "confidence": detection["confidence"],
                    "loaders": sorted(detection["existing_loaders"]), "names": names, "fonts": find_fonts(args.game)}
    if args.deep_fonts:
        report["fonts"] += unity_fonts(args.game, args.out)
    if engine != "unknown" and not (ROOT / "engines" / f"{profile}.md").is_file():
        if args.record:
            try:
                report["profile_created"] = str(create_profile(engine, detection, report["fonts"]).relative_to(ROOT))
            except ValueError as error:
                print(f"ERROR {error}")
                return 2
        else:
            report["profile_missing"] = f"engines/{profile}.md does not exist; rerun with --record to create it"
    elif engine == "unknown":
        report["next_engine"] = ("Engine not recognized: inspect the files, add markers to config/engine-markers.json, "
                                 "or rerun with --engine <new-id> --record to start a profile")

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
        if args.text:
            lines, origin = [l for l in args.text.read_text(encoding="utf-8").splitlines() if l.strip()], str(args.text)
        else:
            lines, origin = unit_lines(), "translated units"
            if not lines:
                lines, origin = SAMPLE, "built-in samples (no translated units yet)"
        report["preview"] = preview(args.font, args.size, args.width, lines[:60], args.out / "preview.png", args.native)
        report["preview"]["text_from"] = origin

    boot = _load("boot_verdict")
    known = exact_candidates(names) + profile_log_paths(profile, args.game)
    words = name_words(names)
    game_root = args.game.resolve()
    # Engine patterns with a wildcard outside the game folder must still name this game.
    known += [p for p in (boot.candidates(profile, args.game) if profile in boot.LOG_PATTERNS else [])
              if belongs(p, game_root, words)]
    fresh_known = list(dict.fromkeys(p for p in known if p.stat().st_mtime >= since))
    other: list[Path] = []
    if fresh_known:
        logs, source = fresh_known, "known paths (game names, engine profile)"
    else:
        recent = discover_logs(args.game, since)
        logs, source = [p for p in recent if belongs(p, game_root, words)], "discovered"
        other = [p for p in recent if p not in logs]
    report["logs"] = {"source": source, "files": [str(p) for p in logs[:10]],
                      "other_recent_logs_ignored": len(other)}  # other programs' logs: count only, never listed
    baseline = args.out / "baseline.log"
    if logs:
        if args.save_baseline:
            args.out.mkdir(parents=True, exist_ok=True)
            text = "".join(p.read_text(encoding="utf-8", errors="replace") for p in logs[:5])
            baseline.write_text(text, encoding="utf-8")
            report["logs"]["baseline_saved"] = str(baseline)
        use = baseline if baseline.is_file() and not args.save_baseline else None
        report["boot"] = boot.judge(logs[:5], args.since_minutes + 1, use, direct_launch=bool(args.launch))
        report["boot"]["baseline"] = str(use) if use else "none: errors the game always logs count as new"
        if source == "discovered" and args.record and (ROOT / "engines" / f"{profile}.md").is_file():
            report["logs"]["recorded"] = [g for g in dict.fromkeys(generalize(p, args.game) for p in logs[:3])
                                          if record_log(engine, g, args.game.name)]
    else:
        report["logs"]["next"] = ("No fresh log: ask the user to start the game, or use --launch when "
                                  "allow_launch_game is true, then run probe again.")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # A short summary for dashboard.html (loc.py rebuilds it after probe).
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "last.json").write_text(json.dumps({
        "at": time.strftime("%Y-%m-%d %H:%M"), "game": args.game.name, "engine": engine,
        "fonts": {"total": len(report["fonts"]),
                  "arabic": sum(f.get("verdict") == "arabic" for f in report["fonts"])},
        "boot": (report.get("boot") or {}).get("verdict", ""),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
