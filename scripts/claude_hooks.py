"""Claude Code hooks for this workspace (wired in .claude/settings.json).

    pre-tool       before Edit/Write/MultiEdit/NotebookEdit/Bash/PowerShell
    post-tool      after Edit/Write/MultiEdit
    session-start  at session start

pre-tool blocks (exit 2):
  - a file-tool write to an existing file inside PROJECT.yaml game.install_path
    unless a backup of that exact relative path exists (safe_backup.py,
    safe_replace.py, or the workspace backups/ folder);
  - any file-tool write inside a backups folder;
  - a shell command that names the game folder together with a write verb,
    unless it runs one of the template's backup-first tools.
The shell check is a heuristic safety net, not a security boundary.

post-tool re-validates what was just written: units (loc.py validate rules),
proofreading findings, project YAML files; and regenerates .claude/skills and
.claude/agents after a canonical skill or role edit. Problems go back to
Claude (exit 2) so it fixes them in the same turn.

session-start prints the current phase and its blockers (loc.py next).

Codex has no equivalent hooks; there the same rules stay instructions, and the
phase gates in loc.py remain the enforced checkpoint for both runtimes.
"""
from __future__ import annotations

import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
SANCTIONED = ("safe_backup.py", "safe_replace.py", "apply_patch_package.py", "uninstall_patch_package.py")
WRITE_VERB = re.compile(
    r"(?<![\w-])(cp|mv|rm|rmdir|rd|del|erase|copy|move|xcopy|robocopy|ren|rename|tee|truncate|dd|"
    r"copy-item|move-item|remove-item|rename-item|set-content|add-content|out-file|new-item|clear-content)(?![\w-])"
    r"|sed\s+-i|>{1,2}",
    re.IGNORECASE,
)
YAML_FILES = {"PROJECT.yaml", "glossary.yaml", "config/image-localization-policy.yaml", "loc-kit/CHARACTERS.yaml"}


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def norm(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder.rstrip("\\/") + os.sep)


def install_path(root: Path = ROOT) -> str | None:
    try:
        import yaml
        value = (yaml.safe_load((root / "PROJECT.yaml").read_text(encoding="utf-8")) or {}).get("game", {}).get("install_path", "")
    except Exception:
        return None
    if not isinstance(value, str) or not value.strip() or value.strip().startswith("["):
        return None
    return norm(value)


def path_spellings(folder: str) -> list[str]:
    """How a Windows folder may appear in a Bash or PowerShell command, lowercased."""
    plain = folder.lower()
    forward = plain.replace("\\", "/")
    spellings = {plain, forward, plain.replace("\\", "\\\\")}
    if re.match(r"^[a-z]:/", forward):
        spellings.add(f"/{forward[0]}{forward[2:]}")
    return sorted(spellings)


def backup_exists(rel: str, game: str, root: Path = ROOT) -> bool:
    pattern = glob.escape(rel.replace("\\", "/"))
    bases = [(Path(game) / "backups", ("*", "safe-replace/*")), (root / "backups", ("**",))]
    for base, prefixes in bases:
        for prefix in prefixes:
            if any(base.glob(f"{prefix}/{pattern}")):
                return True
    return False


def check_file_write(target: str, root: Path = ROOT) -> str | None:
    """A reason to block this file write, or None to allow it."""
    path = norm(target)
    game = install_path(root)
    backup_dirs = [norm(root / "backups")] + ([norm(Path(game) / "backups")] if game else [])
    if any(inside(path, folder) for folder in backup_dirs) and not path.endswith(os.sep + "readme.md"):
        return "Backups are read-only. Never edit or overwrite a file under backups/."
    if not game or not inside(path, game) or not os.path.isfile(path):
        return None
    rel = os.path.relpath(path, game)
    if backup_exists(rel, game, root):
        return None
    return (f"No backup of game file {rel} yet. Back it up first: "
            f"python scripts/safe_backup.py \"{game}\" \"{rel}\" (or use safe_replace.py / "
            "apply_patch_package.py, which back up before writing).")


def check_shell(command: str, root: Path = ROOT) -> str | None:
    game = install_path(root)
    if not game:
        return None
    text = command.lower()
    if not any(spelling in text for spelling in path_spellings(game)):
        return None
    if any(tool in text for tool in SANCTIONED):
        return None
    if WRITE_VERB.search(command):
        return ("This command writes inside the game folder without a backup-first tool. Use "
                "scripts/safe_replace.py, scripts/apply_patch_package.py, or back up first with "
                "scripts/safe_backup.py, then write with one of those tools.")
    return None


def pre_tool(event: dict, root: Path = ROOT) -> str | None:
    tool, data = event.get("tool_name", ""), event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        target = data.get("file_path") or data.get("notebook_path")
        return check_file_write(target, root) if target else None
    if tool in SHELL_TOOLS and data.get("command"):
        return check_shell(data["command"], root)
    return None


PLAN_MAX_LINES = 150


def post_tool(event: dict, root: Path = ROOT) -> str | None:
    """Check what was just written, refresh the pages if any project file changed, and return problems or None.

    Runs after shell commands too, so a file written from the terminal still reaches the dashboard.
    """
    problem = _post_tool_problem(event, root)
    if norm(root) == norm(ROOT):
        try:
            _load("loc", ROOT / "scripts" / "loc.py").refresh_if_stale()
        except Exception:  # the page is a convenience; never block an edit on it
            pass
    return problem


def _post_tool_problem(event: dict, root: Path) -> str | None:
    target = (event.get("tool_input") or {}).get("file_path")
    if not target:
        return None
    path = Path(target)
    try:
        rel = Path(os.path.relpath(os.path.abspath(path), os.path.abspath(root))).as_posix()
    except ValueError:  # another drive
        return None
    if rel.startswith("../"):
        return None
    if rel.startswith("units/") and rel.endswith(".jsonl"):
        units = _load("loc_units", ROOT / "scripts" / "loc_units.py")
        report = units.validate(units.load(root / "units"))
        if report.errors:
            return "loc.py validate found errors after this edit:\n" + "\n".join(report.errors[:10])
    elif rel.startswith("work/proofreading/") and rel.endswith(".jsonl"):
        loc = _load("loc", ROOT / "scripts" / "loc.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loc.main(["findings", str(path), "--path", str(root / "units")])
        if code:
            return "loc.py findings reported problems:\n" + out.getvalue()[-2000:]
    elif rel == "PLAN.md":
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > PLAN_MAX_LINES:
            return (f"PLAN.md has {lines} lines (limit {PLAN_MAX_LINES}). Remove finished items and anything "
                    "that lives elsewhere (counts, phase, backups, command logs) so every session reads less.")
    elif rel == "tools/project-scripts.json":
        registry = _load("check_project_scripts", ROOT / "scripts" / "check_project_scripts.py")
        errors = registry.validate(path, root)
        if errors:
            return "tools/project-scripts.json has problems:\n" + "\n".join(errors)
    elif rel in YAML_FILES:
        check_yaml = _load("check_yaml", ROOT / "scripts" / "check_yaml.py")
        problems = check_yaml.check_file(path)
        if problems:
            return f"{rel} has YAML key problems:\n" + "\n".join(problems)
    elif rel.startswith((".agents/skills/", ".agents/roles/")):
        sync = _load("sync_runtime", ROOT / "scripts" / "sync_runtime.py")
        with contextlib.redirect_stdout(io.StringIO()):
            code = sync.main([])
        if code:
            return "scripts/sync_runtime.py could not regenerate .claude/ files; run it and fix the error."
    elif rel.startswith((".claude/skills/", ".claude/agents/")):
        return (f"{rel} is generated. Edit the source under .agents/skills/ or .agents/roles/ instead; "
                "this change will be overwritten by scripts/sync_runtime.py.")
    return None


def session_start(root: Path = ROOT) -> str:
    loc = _load("loc", ROOT / "scripts" / "loc.py")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        loc.main(["next"])
        loc.main(["dashboard"])
    scripts = _load("check_project_scripts", ROOT / "scripts" / "check_project_scripts.py").summary()
    if scripts:
        out.write("Project scripts already written (reuse before writing new ones):\n" + "\n".join(scripts) + "\n")
    return "Localization project status (python scripts/loc.py next):\n" + out.getvalue()


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    mode = args[0] if args else ""
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    if mode == "session-start":
        try:
            print(session_start())
        except Exception as exc:  # status is a convenience; never block a session on it
            print(f"loc.py next unavailable: {exc}")
        return 0
    event = json.loads(sys.stdin.read() or "{}")
    if mode == "pre-tool":
        reason = pre_tool(event)
    elif mode == "post-tool":
        reason = post_tool(event)
    else:
        print(f"unknown hook mode {mode!r}", file=sys.stderr)
        return 1
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
