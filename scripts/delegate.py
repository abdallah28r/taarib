"""Run one written brief in the other runtime, when the project uses Codex and Claude Code together.

    python scripts/delegate.py --brief work/batches/batch-003.translator.md [--to codex|claude-code] [--dry-run]

PROJECT.yaml `workflow.runtime: both` names the main agent in `runtime_root`;
the other runtime does the delegated work (translation and proofreading batches,
research, image sets). Default `--to` is that other runtime. The brief file is
the whole task: write it first with `loc.py brief` or `make_subagent_brief.py`.
One call is one delegated agent; run several in the background for
`subagent_concurrency`, each on a disjoint brief. The delegated agent changes
files only through the commands its brief names; the root agent then checks
the result as it would any subagent's.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PROMPT = ("You are a delegated agent in the Arabic localization project at {root}. Read only {brief} and do "
          "exactly what it says, nothing more. Do not read other project files unless the brief names them. "
          "End with a report of at most 8 lines: what you did, the ids left for a decision with one question "
          "each, and the result of the last check the brief asked for.")


def settings() -> dict:
    import yaml
    return yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}


def other_runtime(flow: dict) -> str | None:
    if flow.get("runtime") != "both" or flow.get("runtime_root") not in ("codex", "claude-code"):
        return None
    return "codex" if flow["runtime_root"] == "claude-code" else "claude-code"


def command(target: str, brief: Path) -> list[str]:
    text = PROMPT.format(root=ROOT, brief=brief.relative_to(ROOT).as_posix())
    if target == "codex":
        from image_candidate import find_codex
        return [find_codex() or "codex", "exec", "-s", "workspace-write", "--skip-git-repo-check", "-C", str(ROOT),
                text]
    return [shutil.which("claude") or "claude", "-p", text, "--permission-mode", "acceptEdits",
            "--allowedTools", "Read", "Edit", "Write", "Bash(python scripts/loc.py:*)"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--to", choices=("codex", "claude-code"), help="default: the runtime that is not runtime_root")
    parser.add_argument("--dry-run", action="store_true", help="print the command without running it")
    args = parser.parse_args(argv)
    brief = args.brief.resolve()
    if not brief.is_file() or ROOT not in brief.parents:
        print("ERROR the brief must be a file inside this project")
        return 2
    target = args.to or other_runtime(settings().get("workflow") or {})
    if target is None:
        print("ERROR give --to, or set workflow.runtime: both and workflow.runtime_root in PROJECT.yaml")
        return 2
    cmd = command(target, brief)
    if args.dry_run:
        print(json.dumps(cmd, ensure_ascii=False, indent=1))
        return 0
    if not Path(cmd[0]).is_file() and not shutil.which(cmd[0]):
        print(f"ERROR {target} CLI not found")
        return 2
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    for line in lines[-12:]:
        print(line)
    if result.returncode:
        print(f"FAILED {target} exit={result.returncode}: " + " | ".join(result.stderr.strip().splitlines()[-3:]))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
