"""Translation units: the one record shared by text and image localization.

Each line of a ``units/**/*.jsonl`` file is one unit: a player-visible string
or one text region inside an image. A unit's ``status`` only moves forward
through STATUSES; each stage implies the previous ones. This module loads,
validates, normalizes, and writes units; ``loc.py`` is the command line.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS_DIR = ROOT / "units"

STATUSES = ("extracted", "translated", "proofread", "integrated", "tested")
KINDS = ("text", "image")
DECISIONS = ("translate", "keep", "review")
# Arabic verbs, adjectives, and pronouns agree with the addressee, so the brief carries them.
ADDRESSEE_GENDERS = ("m", "f", "mixed", "unknown")
ADDRESSEE_NUMBERS = ("singular", "dual", "plural")
REQUIRED = ("id", "kind", "file", "source", "source_hash", "status")
# Stable key order keeps one-line-per-unit diffs readable in Git.
KEY_ORDER = (
    "id", "kind", "file", "key", "asset", "box", "source", "target", "status",
    "decision", "batch", "context", "max_length", "translated_by", "proofread_by",
    "evidence", "notes", "term_exceptions", "previous_target", "proofread_hash", "source_hash",
)
# Evidence a unit must carry before it may claim these stages.
STAGE_EVIDENCE = {"integrated": "integrated_build", "tested": "tested"}


def _load_token_counter():
    spec = importlib.util.spec_from_file_location("loc_qa_for_units", ROOT / "scripts" / "loc_qa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.tokens


tokens = _load_token_counter()


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def stage(unit: dict) -> int:
    """Index of the unit's status in STATUSES, or -1 when invalid."""
    status = unit.get("status")
    return STATUSES.index(status) if status in STATUSES else -1


def decision(unit: dict) -> str:
    return unit.get("decision", "translate")


def canonical(unit: dict) -> dict:
    ordered = {key: unit[key] for key in KEY_ORDER if key in unit}
    ordered.update({key: value for key, value in unit.items() if key not in ordered})
    return ordered


class UnitFile:
    """The units of one JSONL file and the line number of each."""

    def __init__(self, path: Path, units: list[dict] | None = None, lines: list[int] | None = None):
        self.path = path
        self.units = units if units is not None else []
        self.lines = lines if lines is not None else list(range(1, len(self.units) + 1))


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []


def unit_paths(target: Path = UNITS_DIR) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.jsonl")) if target.is_dir() else []


def load(target: Path = UNITS_DIR, report: Report | None = None) -> list[UnitFile]:
    """Read unit files; parse errors go to ``report`` instead of raising."""
    report = report if report is not None else Report()
    files = []
    for path in unit_paths(target):
        unit_file = UnitFile(path, [], [])
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                report.errors.append(f"{path}:{number}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(value, dict):
                report.errors.append(f"{path}:{number}: a unit must be a JSON object")
                continue
            unit_file.units.append(value)
            unit_file.lines.append(number)
        files.append(unit_file)
    return files


def all_units(files: list[UnitFile]) -> list[dict]:
    return [unit for unit_file in files for unit in unit_file.units]


def write(unit_file: UnitFile) -> None:
    text = "".join(json.dumps(canonical(u), ensure_ascii=False) + "\n" for u in unit_file.units)
    unit_file.path.write_text(text, encoding="utf-8", newline="\n")


def check_unit(unit: dict, where: str, profile: str, report: Report) -> None:
    missing = [key for key in REQUIRED if key not in unit]
    if missing:
        report.errors.append(f"{where}: missing {', '.join(missing)}")
        return
    label = f"{where} [{unit['id']}]"
    if unit["kind"] not in KINDS:
        report.errors.append(f"{label}: kind must be one of {KINDS}")
    context = unit.get("context") or {}
    for key, allowed in (("addressee_gender", ADDRESSEE_GENDERS), ("addressee_number", ADDRESSEE_NUMBERS)):
        if key in context and context[key] not in allowed:
            report.errors.append(f"{label}: context.{key} must be one of {allowed}")
    if unit["status"] not in STATUSES:
        report.errors.append(f"{label}: status must be one of {STATUSES}")
        return
    if decision(unit) not in DECISIONS:
        report.errors.append(f"{label}: decision must be one of {DECISIONS}")
        return
    if not isinstance(unit["source"], str):
        report.errors.append(f"{label}: source must be a string")
        return
    if unit["source_hash"] != source_hash(unit["source"]):
        report.errors.append(
            f"{label}: source changed since the unit was recorded; review the target, "
            "reset status to extracted, then run loc.py normalize"
        )

    target = unit.get("target") or ""
    reached = stage(unit)
    if decision(unit) != "keep" and reached >= STATUSES.index("translated") and not target.strip():
        report.errors.append(f"{label}: status {unit['status']} requires a target")
    if target and unit["kind"] == "text" and tokens(unit["source"], profile) != tokens(target, profile):
        missing_tokens = dict(tokens(unit["source"], profile) - tokens(target, profile))
        extra_tokens = dict(tokens(target, profile) - tokens(unit["source"], profile))
        report.errors.append(f"{label}: token mismatch missing={missing_tokens} extra={extra_tokens}")

    for status, key in STAGE_EVIDENCE.items():
        if reached >= STATUSES.index(status) and not (unit.get("evidence") or {}).get(key):
            report.errors.append(f"{label}: status {unit['status']} requires evidence.{key}")
    if decision(unit) != "keep" and reached >= STATUSES.index("proofread"):
        if "proofread_hash" not in unit:
            report.errors.append(f"{label}: status {unit['status']} requires proofreading (no proofread_hash); "
                                 "mark it proofread with loc.py first")
        elif unit["proofread_hash"] != source_hash(target):
            report.errors.append(f"{label}: target changed after proofreading; proofread this unit again")
    translator, proofreader = unit.get("translated_by"), unit.get("proofread_by")
    if translator and proofreader and translator == proofreader:
        report.errors.append(f"{label}: proofreader must differ from translator ({translator})")

    if unit["kind"] == "image":
        box = unit.get("box")
        if not unit.get("asset"):
            report.errors.append(f"{label}: image unit requires asset")
        if not (isinstance(box, list) and len(box) == 4 and all(isinstance(v, int) and v >= 0 for v in box)
                and box[2] > 0 and box[3] > 0):
            report.errors.append(f"{label}: image unit requires box [x, y, width, height]")

    if decision(unit) == "review" and reached > STATUSES.index("translated"):
        report.warnings.append(f"{label}: marked review but already {unit['status']}")
    limit = unit.get("max_length")
    if isinstance(limit, int) and len(target) > limit:
        report.warnings.append(f"{label}: target length {len(target)} exceeds max_length {limit}")


def validate(files: list[UnitFile], profile: str = "generic", report: Report | None = None) -> Report:
    report = report if report is not None else Report()
    seen: dict[str, str] = {}
    for unit_file in files:
        for unit, line in zip(unit_file.units, unit_file.lines):
            where = f"{unit_file.path}:{line}"
            check_unit(unit, where, profile, report)
            ident = unit.get("id")
            if isinstance(ident, str):
                if ident in seen:
                    report.errors.append(f"{where}: duplicate id {ident!r} (first at {seen[ident]})")
                else:
                    seen[ident] = where
    return report


def new_unit(ident: str, file: str, source: str, kind: str = "text", **fields) -> dict:
    """Build an extracted unit; adapters should create units through this."""
    unit = {"id": ident, "kind": kind, "file": file, "source": source, "status": "extracted"}
    unit.update(fields)
    unit["source_hash"] = source_hash(source)
    return canonical(unit)
