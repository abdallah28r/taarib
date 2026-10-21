"""Generate a bounded localization subagent brief from the project policy."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "agent-policy.json"


def load_roles() -> dict:
    """Runtime-neutral roles from .agents/roles/, keyed by name."""
    spec = importlib.util.spec_from_file_location("sync_runtime_for_brief", ROOT / "scripts" / "sync_runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.roles()


def load_policy(path: Path = DEFAULT_POLICY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def model_line(policy: dict, tier: str, runtime: str | None) -> str:
    runtimes = policy["runtimes"]
    names = [runtime] if runtime else sorted(runtimes)
    examples = ", ".join(f"{name}: {runtimes[name]['tiers'][tier]}" for name in names)
    return f"- Model tier: {tier} ({examples})"


def build_brief(policy: dict, route_name: str, task: str, scope: str,
                write_mode: str = "read-only", deliverable: str = "Return findings and evidence.",
                runtime: str | None = None, role: tuple[dict, str] | None = None,
                tier: str | None = None, effort: str | None = None) -> str:
    """The route's tier and effort are suggestions; ``tier``/``effort`` record the root agent's own choice."""
    route = policy["routing"][route_name]
    auth = policy["authorization"]
    providers = policy["providers"]
    lines = [
        "# Subagent brief",
        "",
        f"- Objective: {task}",
        f"- Deliverable: {deliverable}",
        f"- Scope: {scope}",
        f"- Write mode: {write_mode}",
        *([f"- Role: {role[0]['name']} (skill: {role[0]['skill']})"] if role else []),
        f"- Requested route: {route_name}",
        model_line(policy, tier or route["tier"], runtime),
        f"- Reasoning effort: {effort or route['effort']}",
        "",
        "## Binding constraints",
        "",
        "- Use only a hosted frontier model exposed by the active runtime (Codex or Claude Code). If the requested tier is unavailable or cannot be selected per agent, report that fact; never substitute a local model.",
        f"- Local language models: {providers['local_language_models']}; local machine translation: {providers['local_machine_translation']}.",
        "- Do not install or download tools or models, contact an external AI service, launch the game, perform destructive actions, or expand scope.",
        f"- Nested delegation: {auth['nested_delegation']}. Create child agents only for independent bounded work and pass this full policy to them.",
        "- Read the relevant project style, glossary, protected-token, and format instructions before acting.",
        "- Preserve keys, placeholders, tags, escapes, meaningful line breaks, encoding, and file structure.",
        "- Report uncertainties, files changed, commands run, and acceptance-check results. Do not provide hidden chain-of-thought.",
    ]
    if write_mode == "read-only":
        lines.append("- Do not modify files.")
    else:
        lines.append("- Modify only the assigned files; one agent must be the sole writer for each file.")
    if role and runtime == "claude-code":
        # The .claude/agents/<role>.md subagent already carries these instructions.
        lines += ["", f"Role instructions: in the `{role[0]['name']}` subagent definition; not repeated here."]
    elif role:
        lines += ["", "## Role instructions", "", role[1].rstrip()]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    policy = load_policy()
    roles = load_roles()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=sorted(roles), help="runtime-neutral role from .agents/roles/")
    parser.add_argument("--route", choices=sorted(policy["routing"]), help="defaults to the role's route")
    parser.add_argument("--task", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--write-mode", choices=("read-only", "write"), default="read-only")
    parser.add_argument("--deliverable", default="Return findings and evidence.")
    parser.add_argument("--runtime", choices=sorted(policy["runtimes"]),
                        help="show only this runtime's model for the tier")
    parser.add_argument("--tier", choices=("light", "standard", "deep"),
                        help="any tier you choose; the route's tier is only a suggestion")
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"),
                        help="any reasoning effort you choose; the route's effort is only a suggestion")
    args = parser.parse_args(argv)
    role = roles[args.role] if args.role else None
    route = args.route or (role[0]["route"] if role else None)
    if not route:
        parser.error("give --role or --route")
    print(build_brief(policy, route, args.task, args.scope, args.write_mode, args.deliverable,
                      args.runtime, role, args.tier, args.effort), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
