"""Validate the localization subagent policy and active tool surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "config" / "agent-policy.json"
CATALOG = ROOT / "tools" / "open-source-tools.json"
SETUP = ROOT / "scripts" / "setup_tools.ps1"
FORBIDDEN_ACTIVE_IDS = {"ollama", "argos-translate", "libretranslate", "localai", "llama.cpp"}
REQUIRED_RUNTIMES = ("codex", "claude-code")
TIERS = ("light", "standard", "deep")


def validate(root: Path = ROOT, policy_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    policy_path = policy_path or root / "config" / "agent-policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load policy: {exc}"]

    if policy.get("schema_version") != 1:
        errors.append("agent policy schema_version must be 1")
    auth = policy.get("authorization", {})
    if auth.get("subagents") != "allowed_by_default":
        errors.append("subagents must be allowed by default")
    if auth.get("permission_persists") is not True:
        errors.append("default subagent permission must persist")
    if auth.get("concurrency_policy") != "at_most_PROJECT_yaml_workflow_subagent_concurrency":
        errors.append("subagent concurrency must come from the user's PROJECT.yaml answer")
    if "max_concurrent_subagents" in auth:
        errors.append("a fixed max_concurrent_subagents must not be present; the user sets it per project")
    if auth.get("single_writer_per_file") is not True:
        errors.append("single_writer_per_file must be true")
    if auth.get("nested_delegation") != "allowed_when_bounded_and_policy_compliant":
        errors.append("bounded policy-compliant nested delegation must be allowed")

    providers = policy.get("providers", {})
    if providers.get("local_language_models") != "prohibited":
        errors.append("local language models must be prohibited")
    if providers.get("local_machine_translation") != "prohibited":
        errors.append("local machine translation must be prohibited")
    if providers.get("local_ocr_or_stt") != "explicit_user_authorization_per_current_task":
        errors.append("local OCR/STT must require explicit current-task authorization")

    runtimes = policy.get("runtimes", {})
    for name in REQUIRED_RUNTIMES:
        if name not in runtimes:
            errors.append(f"missing runtime: {name}")
        elif "tiers" in runtimes[name]:
            errors.append(f"runtime {name} names models; tiers stay descriptions and the agent picks a live model")
    tiers = policy.get("tiers", {})
    for tier in TIERS:
        if not tiers.get(tier):
            errors.append(f"tier {tier} needs a description")
    if policy.get("mixed_runtime", {}).get("single_writer_per_file_across_runtimes") is not True:
        errors.append("single writer per file must hold across runtimes")

    routing = policy.get("routing", {})
    for route in ("mechanical", "scoped_edit", "ui_translation", "contextual_translation",
                  "proofreading", "research", "image_work", "deep_review", "architecture", "exceptional"):
        if route not in routing:
            errors.append(f"missing routing entry: {route}")
        elif routing[route].get("tier") not in TIERS:
            errors.append(f"routing entry {route} must use a tier from {TIERS}")

    try:
        catalog = json.loads((root / "tools" / "open-source-tools.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load tool catalog: {exc}")
    else:
        if "local-mt" in catalog.get("profiles", {}):
            errors.append("tool catalog must not expose a local-mt profile")
        ids = {tool.get("id", "").lower() for tool in catalog.get("tools", [])}
        active = sorted(ids.intersection(FORBIDDEN_ACTIVE_IDS))
        if active:
            errors.append("prohibited local AI tools remain active in catalog: " + ", ".join(active))

    try:
        setup_text = (root / "scripts" / "setup_tools.ps1").read_text(encoding="utf-8").lower()
    except OSError as exc:
        errors.append(f"cannot load setup script: {exc}")
    else:
        if "local-mt" in setup_text or "argostranslate" in setup_text or "libretranslate" in setup_text:
            errors.append("setup script still exposes local machine translation")
        if "@('ocr','all')" in setup_text or '@("ocr","all")' in setup_text:
            errors.append("the all profile must not download local OCR model data")
        all_lines = [line for line in setup_text.splitlines() if "'all'" in line and "{ @(" in line]
        if any("tesseract" in line or "'ocr'" in line for line in all_lines):
            errors.append("the all profile must not install or activate local OCR models")

    if (root / "requirements" / "local-mt.txt").exists():
        errors.append("active requirements/local-mt.txt must be removed")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve(), args.policy)
    report = {"ok": not errors, "errors": errors}
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
