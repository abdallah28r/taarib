"""Generate Claude Code files from the canonical, runtime-neutral sources.

Codex reads .agents/skills/ directly. Claude Code reads .claude/skills/ and
.claude/agents/. This script regenerates both from the canonical sources:

- .agents/skills/** is copied to .claude/skills/** unchanged.
- .agents/roles/<role>.md is rendered to .claude/agents/<role>.md, with the
  model taken from the role's route tier in config/agent-policy.json.

Codex uses the same roles through `make_subagent_brief.py --role <role>`.
Edit only the canonical sources. Plain copies are used instead of symlinks
because Windows checkouts often turn symlinks into text files. Run with
--check to fail when the generated files differ.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
ROLES = ROOT / ".agents" / "roles"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
POLICY = ROOT / "config" / "agent-policy.json"
GENERATED_NOTE = "<!-- Generated from .agents/roles/{name}.md by scripts/sync_runtime.py; edit the source. -->"


def files_under(base: Path) -> dict[str, Path]:
    if not base.is_dir():
        return {}
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def load_role(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing frontmatter")
    header, body = text[4:].split("\n---\n", 1)
    meta = yaml.safe_load(header) or {}
    for key in ("name", "description", "route", "skill", "tools"):
        if not meta.get(key):
            raise ValueError(f"{path.name}: frontmatter needs {key}")
    if meta["name"] != path.stem:
        raise ValueError(f"{path.name}: name must match the file name")
    return meta, body.lstrip("\n")


def roles(source: Path = ROLES) -> dict[str, tuple[dict, str]]:
    return {path.stem: load_role(path) for path in sorted(source.glob("*.md"))} if source.is_dir() else {}


def render_claude_agent(meta: dict, body: str, policy: dict, skills: Path = SKILLS) -> str:
    route = policy["routing"].get(meta["route"])
    if route is None:
        raise ValueError(f"role {meta['name']}: unknown route {meta['route']}")
    if not (skills / meta["skill"] / "SKILL.md").is_file():
        raise ValueError(f"role {meta['name']}: unknown skill {meta['skill']}")
    model = policy["runtimes"]["claude-code"]["tiers"][route["tier"]]
    header = {
        "name": meta["name"],
        "description": json.dumps(meta["description"], ensure_ascii=False),
        "tools": ", ".join(meta["tools"]),
        "model": model,
    }
    front = "".join(f"{key}: {value}\n" for key, value in header.items())
    note = GENERATED_NOTE.format(name=meta["name"])
    skill_line = f"Skill: `.claude/skills/{meta['skill']}/SKILL.md`. Reasoning effort: {route['effort']}."
    return f"---\n{front}---\n\n{note}\n\n{skill_line}\n\n{body}"


def expected(policy: dict | None = None, skills: Path = SKILLS, role_dir: Path = ROLES) -> dict[str, bytes]:
    """Every generated file, keyed by its path relative to the repository root."""
    policy = policy or json.loads(POLICY.read_text(encoding="utf-8"))
    wanted = {f".claude/skills/{name}": normalized(path.read_bytes()) for name, path in files_under(skills).items()}
    for name, (meta, body) in roles(role_dir).items():
        wanted[f".claude/agents/{name}.md"] = render_claude_agent(meta, body, policy, skills).encode("utf-8")
    return wanted


def present(root: Path = ROOT) -> dict[str, bytes]:
    found = {}
    for base, prefix in ((root / ".claude" / "skills", ".claude/skills"), (root / ".claude" / "agents", ".claude/agents")):
        for name, path in files_under(base).items():
            found[f"{prefix}/{name}"] = normalized(path.read_bytes())
    return found


def differences(wanted: dict[str, bytes], found: dict[str, bytes]) -> list[str]:
    problems = [f"missing {name}" for name in wanted if name not in found]
    problems += [f"stale {name}" for name in found if name not in wanted]
    problems += [f"changed {name}" for name in wanted if name in found and wanted[name] != found[name]]
    return sorted(problems)


def write_all(wanted: dict[str, bytes], root: Path = ROOT) -> int:
    for folder in (root / ".claude" / "skills", root / ".claude" / "agents"):
        if folder.exists():
            shutil.rmtree(folder)
    for name, data in wanted.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(wanted)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)
    try:
        wanted = expected()
    except (ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"ERROR {exc}")
        return 2
    if args.check:
        problems = differences(wanted, present())
        for problem in problems:
            print(f"ERROR {problem}; run python scripts/sync_runtime.py")
        print(f"RUNTIME_DRIFT={len(problems)}")
        return 1 if problems else 0
    print(f"GENERATED_FILES={write_all(wanted)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
