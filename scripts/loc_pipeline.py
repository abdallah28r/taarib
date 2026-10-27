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
import re
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
tools = _load("loc_tools", ROOT / "scripts" / "loc_tools.py")

PHASES = ("intake", "discovery", "extraction", "pilot", "localization", "integration", "playtest", "handoff", "release")
ROUTES = {
    "intake": "references/project-run.md (a bare «عرّب اللعبة» starts it: ask the grouped intake questions once)",
    "discovery": "python scripts/context_plan.py discovery, then mod-research",
    "extraction": "python scripts/context_plan.py extraction (write/prove the adapter, then loc.py extract)",
    "pilot": "translate, proofread, build and install batch pilot (main menu, settings, first scene), then ask the "
             "user to check the Arabic in the game; record loc.py pilot-ok only on their words",
    "localization": "python scripts/context_plan.py translation-ui|translation-dialogue, then proofreading",
    "integration": "python scripts/context_plan.py integration (loc.py rebuild, back up, install, mark integrated)",
    "playtest": "hand the build to the user; fix reports with qa-rendering; record acceptance only on the user's words",
    "handoff": "python scripts/loc.py experiences, then give the user the file and where to send it",
    "release": "python scripts/context_plan.py release (only if the user asked for a shareable package)",
}
PLACEHOLDER = "["
SEVERE = ("blocker", "critical")


class Project:
    """Paths and settings one gate evaluation reads; tests point these at temp files."""

    def __init__(self, root: Path = ROOT, project_file: Path | None = None, units_dir: Path | None = None,
                 state_file: Path | None = None, qa_file: Path | None = None, plan_file: Path | None = None):
        self.root = Path(root)
        self.project_file = project_file or self.root / "PROJECT.yaml"
        self.units_dir = units_dir or self.root / "units"
        self.state_file = state_file or self.root / "state" / "pipeline.json"
        self.qa_file = qa_file or self.root / "qa" / "LQA_MATRIX.csv"
        self.glossary_file = self.root / "glossary.yaml"
        self.plan_file = plan_file or self.root / "PLAN.md"

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
    path = game.get("install_path", "")
    checks = [
        (filled(game.get("name")), "اسم اللعبة محدد (game.name)"),
        (filled(path) and Path(path).is_dir(), "مسار اللعبة محدد وموجود (game.install_path)"),
        (yes_no(flow.get("image_scope")) is not None, "أُجيب سؤال تعريب الصور بنعم/لا (image_scope)"),
        (isinstance(flow.get("allow_launch_game"), bool), "حُدد السماح بتشغيل اللعبة (allow_launch_game)"),
        *working_setup(flow),
    ]
    return checks


RUNTIMES = ("codex", "claude-code", "both")
SUBAGENT_MODES = ("economic", "balanced", "fast")
REVIEW_MODES = ("separate", "self")


def working_setup(flow: dict) -> list[tuple[bool, str]]:
    """The intake answers about runtimes, usage, and review that change how the work is run."""
    runtime, mode = flow.get("runtime"), flow.get("subagent_mode")
    concurrency = flow.get("subagent_concurrency")
    checks = [(runtime in RUNTIMES, "حُددت بيئة العمل: codex أو claude-code أو both (runtime)")]
    if runtime == "both":
        checks.append((flow.get("runtime_root") in ("codex", "claude-code"),
                       "حُدد النموذج الأساسي عند استخدام الاثنين (runtime_root)"))
    checks += [
        (filled(flow.get("subscription")) and flow.get("subscription") != "ask", "سُجل نوع الاشتراك (subscription)"),
        (mode in SUBAGENT_MODES, "حُدد نمط استخدام الوكلاء الفرعيين: economic أو balanced أو fast (subagent_mode)"),
    ]
    if mode in ("balanced", "fast"):
        checks.append((isinstance(concurrency, int) and not isinstance(concurrency, bool) and concurrency >= 1,
                       f"حُدد عدد الوكلاء المتزامنين (subagent_concurrency؛ الآن: {concurrency})"))
    checks.append((flow.get("review_mode") in REVIEW_MODES, "حُددت طريقة التدقيق: separate أو self (review_mode)"))
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
    exists = filled(adapter) and project.resolve(adapter).is_file()
    rtl = "unknown"
    if exists:
        try:
            base = _load("loc_adapter_base", ROOT / "adapters" / "base.py")
            rtl = base.load_adapter(project.resolve(adapter), Path("."), flow.get("adapter_options") or {}).rtl
        except Exception as exc:  # a broken adapter cannot pass discovery
            rtl = f"error: {exc}"
    return [
        (filled(flow.get("engine_profile")), "المحرك محدد (engine_profile)"),
        (exists, "المحوّل محدد وملفه موجود (workflow.adapter)"),
        (rtl in ("native", "needs_preshape"),
         f"المحوّل يعلن طريقة عرض العربية من دليل الاكتشاف: native أو needs_preshape (الآن: {rtl})"),
    ]


def unit_report(project: Project, settings: dict):
    report = units.Report()
    files = units.load(project.units_dir, report)
    units.validate(files, settings.get("game", {}).get("token_profile", "generic") or "generic", report)
    return units.all_units(files), report


BATCHES_HEADING = "## الدفعات"
BATCH_ITEM = re.compile(r"^\s*[-*] \[( |x|X)\]\s+\S")


def plan_batches(project: Project) -> list[bool]:
    """Done flags of the checklist items under PLAN.md's batches section."""
    if not project.plan_file.is_file():
        return []
    flags, inside = [], False
    for line in project.plan_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == BATCHES_HEADING
            continue
        match = BATCH_ITEM.match(line) if inside else None
        if match:
            flags.append(match.group(1).lower() == "x")
    return flags


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
        (bool(proven), "عقد المحوّل نجح على المحوّل الحالي ونصوص اللعبة الحالية" + error),
        (bool(all_units), "توجد وحدات مستخرجة في units/"),
        (not report.errors, f"فحص الوحدات بلا أخطاء (الآن: {len(report.errors)})"),
        (bool(plan_batches(project)), f"خطة الدفعات كاملة مكتوبة في PLAN.md تحت «الدفعات» (الآن: {len(plan_batches(project))})"),
        *image_inventory(settings, state, all_units),
    ]


def image_inventory(settings: dict, state: dict, all_units: list[dict]) -> list[tuple[bool, str]]:
    """With images in scope, extraction needs image units or a recorded reason there are none."""
    if yes_no((settings.get("workflow") or {}).get("image_scope")) != "yes":
        return []
    images = sum(1 for u in all_units if u.get("kind") == "image")
    return [(bool(images) or bool(state.get("images_none")),
             f"الصور ذات النص مجرودة وحدات kind: image، أو سُجّل أن لا صور (loc.py no-images؛ الآن: {images})")]


def image_manifests(project: Project) -> list[Path]:
    folder = project.root / "work" / "images"
    return sorted(p for p in folder.glob("*.json") if p.name != "attempts.json") if folder.is_dir() else []


def image_review(project: Project, all_units: list[dict]) -> list[tuple[bool, str]]:
    """Translated image regions need region manifests in work/images/ that list them and pass check_image_regions."""
    wanted = {Path(str(u.get("asset", ""))).name for u in all_units
              if u.get("kind") == "image" and units.decision(u) == "translate"}
    if not wanted:
        return []
    errors, listed = [], set()
    checker = _load("check_image_regions", ROOT / "scripts" / "check_image_regions.py")
    for path in image_manifests(project):
        errors += [f"{path.name}: {e}" for e in checker.validate(path)]
        try:
            rows = json.loads(path.read_text(encoding="utf-8")).get("images")
            listed |= {Path(str(r.get("image", ""))).name for r in rows if isinstance(r, dict)}
        except (ValueError, AttributeError, TypeError):
            pass
    missing = sorted(wanted - listed)
    detail = "، ".join(filter(None, [f"صور بلا سجل: {len(missing)} ({', '.join(missing[:3])})" if missing else "",
                                     f"أخطاء: {len(errors)}، أولها {errors[0]}" if errors else ""])) or "سليم"
    return [(not missing and not errors, f"كل صورة مترجمة مسجلة في work/images/*.json وفحص مناطقها ناجح ({detail})")]


PILOT_BATCH = "pilot"


def check_pilot(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    """A small batch reaches the user's game and the user confirms the Arabic shows correctly before bulk work."""
    all_units, report = unit_report(project, settings)
    pilot = [u for u in all_units if u.get("batch") == PILOT_BATCH]
    pending = [u for u in pilot if units.decision(u) == "translate" and units.stage(u) < 3]
    return [
        (bool(pilot), f"دفعة التجربة محددة: وحدات batch: {PILOT_BATCH} من القائمة الرئيسية والإعدادات وأول مشهد "
                      f"(الآن: {len(pilot)})"),
        (not report.errors, f"فحص الوحدات بلا أخطاء (الآن: {len(report.errors)})"),
        (bool(pilot) and not pending, f"دفعة التجربة مترجمة ومدققة ومثبتة في اللعبة (المتبقي: {len(pending)})"),
        (bool(state.get("pilot")), "تأكيدك أن العربي يظهر صحيحًا في اللعبة مسجل (loc.py pilot-ok)"),
    ]


def check_localization(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    all_units, report = unit_report(project, settings)
    pending = [u for u in all_units if units.decision(u) == "translate" and units.stage(u) < 2]
    review = [u for u in all_units if units.decision(u) == "review"]
    import yaml
    glossary = yaml.safe_load(project.glossary_file.read_text(encoding="utf-8")) if project.glossary_file.is_file() else {}
    digits = settings.get("game", {}).get("digits") or "western"
    overrides = (settings.get("qa") or {}).get("levels") or {}
    profile = settings.get("game", {}).get("token_profile", "generic") or "generic"
    counts = tools.problem_counts(tools.unit_problems(all_units, glossary or {}, profile, digits), overrides)
    errors = {code: n for code, n in counts.items() if tools.level(code, overrides) == "error"}
    batches = plan_batches(project)
    return [
        (bool(all_units), "توجد وحدات في units/"),
        (not report.errors, f"فحص الوحدات بلا أخطاء (الآن: {len(report.errors)})"),
        (not pending, f"كل وحدة قابلة للترجمة مدققة لغويًا (المتبقي: {len(pending)})"),
        (not review, f"لا وحدة تنتظر قرارًا (بانتظار قرار: {len(review)})"),
        (not errors, "لا مشكلات من مستوى الخطأ، ومنها المسرد والصيغ الممنوعة ("
                     + ("، ".join(f"{c}={n}" for c, n in errors.items()) or "لا شيء") + ")"),
        (bool(batches) and all(batches), f"كل دفعات PLAN.md مؤشّرة ☑ (المتبقي: {batches.count(False)})"),
        *image_review(project, all_units),
        *review_separation(settings, all_units),
    ]


def review_separation(settings: dict, all_units: list[dict]) -> list[tuple[bool, str]]:
    """With review_mode separate, no unit may carry a self-review."""
    if ((settings.get("workflow") or {}).get("review_mode") or "separate") != "separate":
        return []
    own = sum(1 for u in all_units if str(u.get("proofread_by") or "").startswith(units.SELF_REVIEW))
    return [(not own, f"التدقيق منفصل كما اخترت: لا وحدة دققها مترجمها (الآن: {own})")]


def check_integration(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    all_units, report = unit_report(project, settings)
    pending = [u for u in all_units if units.decision(u) != "keep" and units.stage(u) < 3]
    return [
        (not report.errors, f"فحص الوحدات بلا أخطاء (الآن: {len(report.errors)})"),
        (not pending, f"كل الوحدات مدمجة في بناء (المتبقي: {len(pending)})"),
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
        (not report.errors, f"فحص الوحدات بلا أخطاء (الآن: {len(report.errors)})"),
        (not severe, f"لا أخطاء حرجة مفتوحة في qa/LQA_MATRIX.csv ({', '.join(severe[:3]) or 'لا شيء'})"),
        (not open_fixes(state), f"لا إصلاحات مفتوحة (loc.py fix list؛ المفتوحة: {len(open_fixes(state))})"),
        (bool(state.get("acceptance")), "قبولك للنسخة مسجل (loc.py accept)"),
    ]


def open_fixes(state: dict) -> list[dict]:
    return [f for f in state.get("fixes", []) if f.get("status") == "open"]


def check_handoff(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    packed = state.get("experiences") or {}
    path = project.resolve(packed["path"]) if packed.get("path") else None
    after = packed.get("at", "") >= (state.get("acceptance") or {}).get("at", "")
    return [
        (bool(path) and path.is_file() and after,
         "ملف الخبرات مبني بعد قبولك ومسلَّم لك (loc.py experiences)"),
    ]


def record_experiences(project: Project, path: Path, digest: str, lessons: int) -> None:
    state = project.state()
    try:
        shown = str(path.resolve().relative_to(project.root.resolve()))
    except ValueError:
        shown = str(path)
    state["experiences"] = {"path": shown, "sha256": digest, "lessons": lessons, "at": now()}
    project.save(state)


def check_release(project: Project, settings: dict, state: dict) -> list[tuple[bool, str]]:
    return [(False, "النشر هو المرحلة الأخيرة؛ اتبع references/release.md")]


CRITERIA = {
    "intake": check_intake, "discovery": check_discovery, "extraction": check_extraction, "pilot": check_pilot,
    "localization": check_localization, "integration": check_integration,
    "playtest": check_playtest, "handoff": check_handoff, "release": check_release,
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
    if PHASES.index(phase) <= PHASES.index("pilot"):
        state.pop("pilot", None)
    project.save(state)


FIX_VERDICTS = ("verified", "partial", "failed")


def open_fix(project: Project, title: str, current: str, expected: str, unchanged: str, ids: list[str],
             snapshot: dict[str, str]) -> str:
    """Record a small fix (current / expected / must-not-change) and freeze the other units' text."""
    state = project.state()
    fixes = state.setdefault("fixes", [])
    ident = f"F-{len(fixes) + 1:03d}"
    folder = project.state_file.parent / "fixes"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{ident}.snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    fixes.append({"id": ident, "title": title, "current": current, "expected": expected, "unchanged": unchanged,
                  "ids": ids, "status": "open", "opened_at": now()})
    project.save(state)
    return ident


def close_fix(project: Project, ident: str, verdict: str, evidence: str, snapshot_now: dict[str, str],
              stages: dict[str, int]) -> list[str]:
    """Close a fix. 'verified' is refused if text outside the fix changed or a fixed unit is not proofread."""
    state = project.state()
    fix = next((f for f in state.get("fixes", []) if f["id"] == ident), None)
    if fix is None or fix.get("status") != "open":
        return [f"{ident} is not an open fix"]
    if verdict not in FIX_VERDICTS:
        return [f"verdict must be one of {FIX_VERDICTS}"]
    problems = []
    if verdict == "verified":
        frozen = json.loads((project.state_file.parent / "fixes" / f"{ident}.snapshot.json").read_text(encoding="utf-8"))
        changed = sorted(i for i, digest in frozen.items() if snapshot_now.get(i) != digest)
        if changed:
            problems.append(f"text outside the fix changed: {' '.join(changed[:20])}")
        stale = [i for i in fix["ids"] if stages.get(i, 0) < 2]
        if stale:
            problems.append(f"fixed units are not proofread again: {' '.join(stale[:20])}")
        if not evidence.strip():
            problems.append("a verified fix needs --evidence (what was checked, where)")
    if problems:
        return problems
    fix.update(status="closed", verdict=verdict, evidence=evidence, closed_at=now())
    project.save(state)
    return []


def no_images(project: Project, reason: str) -> None:
    """Record that a game with images in scope has no baked text worth an image unit."""
    if not reason.strip():
        raise ValueError("give the reason there are no text images (what was searched)")
    state = project.state()
    state["images_none"] = {"reason": reason.strip(), "at": now()}
    project.save(state)


def confirm_pilot(project: Project, note: str) -> None:
    state = project.state()
    if state["phase"] != "pilot":
        raise ValueError("the pilot check is recorded only during the pilot phase")
    state["pilot"] = {"note": note, "at": now()}
    project.save(state)


def accept(project: Project, note: str) -> None:
    state = project.state()
    if state["phase"] != "playtest":
        raise ValueError("acceptance is recorded only during the playtest phase")
    state["acceptance"] = {"note": note, "at": now()}
    project.save(state)
