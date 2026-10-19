"""Project phases and the exit criteria that gate each one.

A game project moves through PHASES in order. The current phase lives in
``state/pipeline.json``. ``loc.py next`` lists what still blocks the current
phase; ``loc.py gate`` re-checks it and advances only when every criterion
passes. Criteria read files (PROJECT.yaml, units, the LQA matrix, the recorded
adapter contract), never an agent's claim.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


units = _load("loc_units", ROOT / "scripts" / "loc_units.py")

PHASES = ("intake", "discovery", "extraction", "localization", "integration", "playtest", "release")
ROUTES = {
    "intake": "references/project-run.md (ask the grouped intake questions once)",
    "discovery": "python scripts/context_plan.py discovery, then mod-research",
    "extraction": "python scripts/context_plan.py extraction (write/prove the adapter, then loc.py extract)",
    "localization": "python scripts/context_plan.py translation-ui|translation-dialogue, then proofreading",
    "integration": "python scripts/context_plan.py integration (loc.py rebuild, back up, install, mark integrated)",
    "playtest": "hand the build to the user; fix reports with qa-rendering; record acceptance only on the user's words",
    "release": "python scripts/context_plan.py release",
}
PLACEHOLDER = "["
SEVERE = ("blocker", "critical")


class Project:
    """Paths and settings one gate evaluation reads; tests point these at temp files."""

    def __init__(self, root: Path = ROOT, project_file: Path | None = None, units_dir: Path | None = None,
                 state_file: Path | None = None, qa_file: Path | None = None):
        self.root = Path(root)
        self.project_file = project_file or self.root / "PROJECT.yaml"
        self.units_dir = units_dir or self.root / "units"
        self.state_file = state_file or self.root / "state" / "pipeline.json"
        self.qa_file = qa_file or self.root / "qa" / "LQA_MATRIX.csv"

    def settings(self) -> dict:
        import yaml
        return yaml.safe_load(self.project_file.read_text(encoding="utf-8")) or {}

    def state(self) -> dict:
        if self.state_file.is_file():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {"schema_version": 1, "phase": PHASES[0], "history": []}

    def save(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def resolve(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.root / path


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def yes_no(value) -> str | None:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return value if value in ("yes", "no") else None


def filled(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith(PLACEHOLDER)


def digest_files(root: Path, paths) -> str:
    sha = hashlib.sha256()
    for rel in sorted(paths):
        sha.update(rel.encode("utf-8") + b"\0")
        sha.update(hashlib.sha256((root / rel).read_bytes()).digest())
    return sha.hexdigest()[:16]


# ----- criteria: each returns a list of (ok, message) -----------------------

def check_intake(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    game, flow = settings.get("game", {}), settings.get("workflow", {})
    images = settings.get("image_localization", {}).get("external_image_editing", {})
    path = game.get("install_path", "")
    checks = [
        (filled(game.get("name")), "PROJECT.yaml game.name is set"),
        (filled(path) and Path(path).is_dir(), "PROJECT.yaml game.install_path is set and exists"),
        (yes_no(flow.get("install_to_user_copy")) is not None, "workflow.install_to_user_copy answered yes/no"),
        (yes_no(flow.get("subagent_preference")) is not None, "workflow.subagent_preference answered yes/no"),
        (yes_no(flow.get("image_scope")) is not None, "workflow.image_scope answered yes/no"),
        (isinstance(flow.get("allow_launch_game"), bool), "workflow.allow_launch_game is true/false"),
    ]
    if yes_no(flow.get("image_scope")) == "yes":
        checks.append((yes_no(images.get("enabled")) is not None,
                       "image_localization.external_image_editing.enabled answered yes/no"))
    return checks


def adapter_fingerprint(project: Project, settings: dict) -> dict | None:
    """Identity of the adapter and the game text it was proven on, or None if unknown."""
    flow = settings.get("workflow", {})
    adapter, game = flow.get("adapter", ""), settings.get("game", {}).get("install_path", "")
    if not (filled(adapter) and project.resolve(adapter).is_file() and filled(game)):
        return None
    base = _load("loc_adapter_base", ROOT / "adapters" / "base.py")
    instance = base.load_adapter(project.resolve(adapter), Path(game), flow.get("adapter_options") or {})
    inventory = instance.inventory()
    return {
        "adapter": adapter,
        "adapter_sha": hashlib.sha256(project.resolve(adapter).read_bytes()).hexdigest()[:16],
        "inventory_sha": digest_files(Path(game), inventory),
    }


def check_discovery(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    flow = settings.get("workflow", {})
    adapter = flow.get("adapter", "")
    return [
        (filled(flow.get("engine_profile")), "workflow.engine_profile is set"),
        (filled(adapter) and project.resolve(adapter).is_file(), "workflow.adapter names an existing adapter file"),
    ]


def unit_report(project: Project, settings: dict):
    report = units.Report()
    files = units.load(project.units_dir, report)
    units.validate(files, settings.get("game", {}).get("token_profile", "generic") or "generic", report)
    return units.all_units(files), report


def check_extraction(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    recorded = state.get("contract") or {}
    try:
        current = adapter_fingerprint(project, settings)
    except Exception as exc:  # an adapter that cannot even list files fails this gate
        current, recorded = None, {}
        error = f" ({type(exc).__name__}: {exc})"
    else:
        error = ""
    proven = bool(current) and recorded.get("passed") and all(recorded.get(k) == v for k, v in current.items())
    all_units, report = unit_report(project, settings)
    return [
        (bool(proven), "adapter contract passed on the current adapter and game text" + error),
        (bool(all_units), "units/ holds extracted units"),
        (not report.errors, f"loc.py validate has no errors ({len(report.errors)} now)"),
    ]


def check_localization(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    all_units, report = unit_report(project, settings)
    pending = [u for u in all_units if units.decision(u) == "translate" and units.stage(u) < 2]
    review = [u for u in all_units if units.decision(u) == "review"]
    return [
        (bool(all_units), "units/ holds units"),
        (not report.errors, f"loc.py validate has no errors ({len(report.errors)} now)"),
        (not pending, f"every translatable unit is proofread ({len(pending)} not yet)"),
        (not review, f"no unit waits on a decision ({len(review)} marked review)"),
    ]


def check_integration(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    all_units, report = unit_report(project, settings)
    pending = [u for u in all_units if units.decision(u) != "keep" and units.stage(u) < 3]
    return [
        (not report.errors, f"loc.py validate has no errors ({len(report.errors)} now)"),
        (not pending, f"every unit is integrated into a build ({len(pending)} not yet)"),
    ]


def open_severe_defects(project: Project) -> list[str]:
    if not project.qa_file.is_file():
        return []
    with project.qa_file.open(encoding="utf-8-sig", newline="") as stream:
        return [row.get("id", "?") for row in csv.DictReader(stream)
                if (row.get("status") or "").strip().lower() in ("fail", "failed", "open")
                and (row.get("severity") or "").strip().lower() in SEVERE]


def check_playtest(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    _, report = unit_report(project, settings)
    severe = open_severe_defects(project)
    return [
        (not report.errors, f"loc.py validate has no errors ({len(report.errors)} now)"),
        (not severe, f"no open blocker/critical defect in qa/LQA_MATRIX.csv ({', '.join(severe[:3]) or 'none'})"),
        (bool(state.get("acceptance")), "the user's acceptance is recorded (loc.py accept)"),
    ]


def check_release(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    return [(False, "release is the final phase; follow references/release.md")]


CRITERIA = {
    "intake": check_intake, "discovery": check_discovery, "extraction": check_extraction,
    "localization": check_localization, "integration": check_integration,
    "playtest": check_playtest, "release": check_release,
}


def evaluate(project: Project, phase: str | None = None) -> tuple[str, list[tuple[bool, str]]]:
    state = project.state()
    phase = phase or state["phase"]
    return phase, CRITERIA[phase](project, project.settings(), state)


def record_contract(project: Project, passed: bool) -> dict:
    """Store the contract result with the fingerprint it was proven against."""
    state = project.state()
    fingerprint = adapter_fingerprint(project, project.settings()) or {}
    state["contract"] = {**fingerprint, "passed": passed, "at": now()}
    project.save(state)
    return state["contract"]


def advance(project: Project) -> tuple[bool, str, list[tuple[bool, str]]]:
    state = project.state()
    phase, checks = evaluate(project)
    if not all(ok for ok, _ in checks) or phase == PHASES[-1]:
        return False, phase, checks
    following = PHASES[PHASES.index(phase) + 1]
    state["history"].append({"event": "passed", "phase": phase, "at": now()})
    state["phase"] = following
    project.save(state)
    return True, following, checks


def reopen(project: Project, phase: str, reason: str) -> None:
    state = project.state()
    if PHASES.index(phase) >= PHASES.index(state["phase"]):
        raise ValueError(f"can only reopen an earlier phase than {state['phase']}")
    state["history"].append({"event": "reopened", "phase": phase, "from": state["phase"], "reason": reason, "at": now()})
    state["phase"] = phase
    state.pop("acceptance", None)
    project.save(state)


def accept(project: Project, note: str) -> None:
    state = project.state()
    if state["phase"] != "playtest":
        raise ValueError("acceptance is recorded only during the playtest phase")
    state["acceptance"] = {"note": note, "at": now()}
    project.save(state)
