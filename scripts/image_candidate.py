"""Generative image candidates through Codex, and their confinement to the text region.

    python scripts/image_candidate.py codex --source <png> --box x0 y0 x1 y1 --text "<approved Arabic>" [--mask <png>] [--dry-run]
    python scripts/image_candidate.py composite --source <png> --raw <png> (--mask <png> | --box x0 y0 x1 y1) --out <png>

`codex` asks Codex's built-in image tool to edit one source image and copy the
result to work/images/raw/. It works from either runtime: Claude Code calls it
to reach OpenAI image editing, which it has no tool for. The built-in tool
takes no mask and no output size, so its output is only raw material:
`composite` resizes it to the source and copies back only the pixels inside
the mask (or box). Everything outside stays the untouched source, then
check_image_regions.py and a visual review decide.

Each source image gets at most `image_localization.max_generative_attempts`
Codex calls (PROJECT.yaml, default 5), counted in work/images/attempts.json.
At the cap the script refuses; keep the source or mark the region REVIEW.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "work" / "images"
ATTEMPTS = IMAGES / "attempts.json"
DEFAULT_CAP = 5

PROMPT = """Edit one game image for Arabic localization. Load the first attached image with view_image if needed;
it is the edit target ({name}, {width}x{height}).{mask_line}
Replace only the lettering inside the box x0={x0} y0={y0} x1={x1} y1={y1} with exactly this Arabic text,
in logical order, correctly joined, right to left: {text}
Match the source lettering: placement, baseline, size, weight, fill, opacity, perspective, texture, and any
outline, shadow, or glow (or their absence). Add no new outline, shadow, glow, panel, caption, or text.
Change nothing outside the box: subjects, colors, lighting, framing, background, and image size stay as they are.
Use the built-in image editing tool once. Copy the result to {raw} (create the folder), then print exactly:
RESULT {raw}
If you cannot edit or save, print RESULT failed <short reason>. Do nothing else."""


def cap() -> int:
    try:
        import yaml
        data = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}
        value = (data.get("image_localization") or {}).get("max_generative_attempts")
        return value if isinstance(value, int) and value > 0 else DEFAULT_CAP
    except (OSError, ImportError):
        return DEFAULT_CAP


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attempts(path: Path = ATTEMPTS) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def find_codex() -> str | None:
    """codex on PATH, then CODEX_EXE, then the CLI bundled with the Codex desktop app on Windows."""
    found = shutil.which("codex") or os.environ.get("CODEX_EXE")
    if found:
        return found
    if os.name != "nt":
        return None
    try:  # WindowsApps cannot be listed, so ask for the package's install folder
        folder = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 "(Get-AppxPackage -Name OpenAI.Codex).InstallLocation"],
                                capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    exe = Path(folder[-1]) / "app" / "resources" / "codex.exe" if folder else None
    return str(exe) if exe and exe.is_file() else None


def prompt(source: Path, box: list[int], text: str, raw: Path, mask: Path | None) -> str:
    from PIL import Image
    with Image.open(source) as im:
        width, height = im.size
    mask_line = ("\nThe second attached image is a mask: white marks the lettering to replace." if mask else "")
    return PROMPT.format(name=source.name, width=width, height=height, mask_line=mask_line, x0=box[0], y0=box[1],
                         x1=box[2], y1=box[3], text=text, raw=raw.relative_to(ROOT).as_posix())


def cmd_codex(args) -> int:
    source = args.source.resolve()
    key = sha256(source)
    log = attempts(args.attempts)
    used, limit = len(log.get(key, {}).get("raw", [])), cap()
    if used >= limit:
        print(f"REFUSED {source.name}: {used}/{limit} generative attempts used; keep the source or mark the region "
              "REVIEW (raise image_localization.max_generative_attempts only on the user's word)")
        return 3
    raw = IMAGES / "raw" / f"{source.stem}.attempt{used + 1}.png"
    text = prompt(source, args.box, args.text, raw, args.mask)
    command = [args.codex or find_codex() or "codex", "exec", "-s", "workspace-write", "--skip-git-repo-check",
               "-C", str(ROOT), "-i", str(source)] + (["-i", str(args.mask.resolve())] if args.mask else []) + [text]
    if args.dry_run:
        print(json.dumps(command, ensure_ascii=False, indent=1))
        return 0
    if not command[0] or (not Path(command[0]).is_file() and not shutil.which(command[0])):
        print("ERROR Codex CLI not found; install Codex or set CODEX_EXE")
        return 2
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    entry = log.setdefault(key, {"image": source.name, "raw": []})
    entry["raw"].append(raw.relative_to(ROOT).as_posix())
    args.attempts.parent.mkdir(parents=True, exist_ok=True)
    args.attempts.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not raw.is_file():
        tail = [line for line in (result.stdout + result.stderr).splitlines() if line.strip()][-3:]
        print(f"FAILED attempt {used + 1}/{limit}: no image at {raw}")
        for line in tail:
            print(f"  {line}")
        return 1
    print(f"RAW={raw} ATTEMPT={used + 1}/{limit}")
    print("NEXT: python scripts/image_candidate.py composite --source ... --raw ... --mask|--box ... --out ...")
    return 0


def composite(source: Path, raw: Path, out: Path, box: list[int] | None = None, mask: Path | None = None) -> str:
    """Write the source with only the masked (or boxed) pixels taken from raw; return the output's SHA-256."""
    from PIL import Image, ImageDraw
    with Image.open(source) as im:
        base = im.copy()
    with Image.open(raw) as im:
        edit = im.convert(base.mode).resize(base.size, Image.LANCZOS) if im.size != base.size else im.convert(base.mode)
    if mask is not None:
        with Image.open(mask) as im:
            area = im.convert("L").point(lambda value: 255 if value else 0)
        if area.size != base.size:
            raise ValueError("mask dimensions differ from the source")
    else:
        area = Image.new("L", base.size, 0)
        ImageDraw.Draw(area).rectangle(tuple(box), fill=255)
    base.paste(edit, (0, 0), area)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.save(out)
    return sha256(out)


def cmd_composite(args) -> int:
    if not args.mask and not args.box:
        print("ERROR give --mask or --box")
        return 2
    try:
        digest = composite(args.source, args.raw, args.out, args.box, args.mask)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print(f"CANDIDATE={args.out} SHA256={digest}")
    print("NEXT: record it in the region manifest, run check_image_regions.py, then open source and candidate")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("codex", help="one Codex image edit of a source image, within the attempt cap")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--box", type=int, nargs=4, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    p.add_argument("--text", required=True, help="the approved Arabic text, exactly")
    p.add_argument("--mask", type=Path, help="white = lettering to replace; attached for Codex to see")
    p.add_argument("--codex", help="path to the codex CLI (default: PATH, CODEX_EXE, or the desktop app's copy)")
    p.add_argument("--attempts", type=Path, default=ATTEMPTS, help=argparse.SUPPRESS)
    p.add_argument("--dry-run", action="store_true", help="print the command without calling Codex")
    p.set_defaults(run=cmd_codex)
    p = sub.add_parser("composite", help="confine a raw edit to the mask or box over the untouched source")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mask", type=Path)
    p.add_argument("--box", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"))
    p.set_defaults(run=cmd_composite)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
