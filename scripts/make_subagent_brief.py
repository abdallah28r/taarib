"""Generate a bounded localization subagent brief from the project policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "agent-policy.json"


def load_policy(path: Path = DEFAULT_POLICY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_brief(policy: dict, route_name: str, task: str, scope: str,
                write_mode: str = "read-only", deliverable: str = "Return findings and evidence.") -> str:
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
        f"- Requested route: {route_name}",
        f"- Model class: {route['model_class']} (current example: {route['current_example']})",
        f"- Reasoning effort: {route['effort']}",
        "",
        "## Binding constraints",
        "",
        "- Use only an OpenAI-hosted model exposed by the runtime. If the requested model is unavailable or cannot be selected per agent, report that fact; do not substitute a local or third-party model.",
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
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    policy = load_policy()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True, choices=sorted(policy["routing"]))
    parser.add_argument("--task", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--write-mode", choices=("read-only", "write"), default="read-only")
    parser.add_argument("--deliverable", default="Return findings and evidence.")
    args = parser.parse_args(argv)
    print(build_brief(policy, args.route, args.task, args.scope, args.write_mode, args.deliverable), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
