"""Mirror the canonical skills in .agents/skills/ to .claude/skills/.

Codex reads .agents/skills/ and Claude Code reads .claude/skills/. The
.agents copy is the only one to edit; this script regenerates the Claude copy.
A plain copy is used instead of a symlink because Windows checkouts often turn
symlinks into text files. Run with --check to fail when the copies differ.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills"
TARGET = ROOT / ".claude" / "skills"


def files_under(base: Path) -> dict[str, Path]:
    if not base.is_dir():
        return {}
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def differences(source: Path = SOURCE, target: Path = TARGET) -> list[str]:
    wanted, present = files_under(source), files_under(target)
    problems = [f"missing {name}" for name in wanted if name not in present]
    problems += [f"stale {name}" for name in present if name not in wanted]
    problems += [
        f"changed {name}"
        for name in wanted
        if name in present and normalized(wanted[name]) != normalized(present[name])
    ]
    return sorted(problems)


def sync(source: Path = SOURCE, target: Path = TARGET) -> int:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return len(files_under(target))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)
    if not SOURCE.is_dir():
        print(f"ERROR missing {SOURCE}")
        return 2
    if args.check:
        problems = differences()
        for problem in problems:
            print(f"ERROR .claude/skills: {problem}; run python scripts/sync_runtime_skills.py")
        print(f"SKILL_DRIFT={len(problems)}")
        return 1 if problems else 0
    print(f"SYNCED_FILES={sync()} TARGET={TARGET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
