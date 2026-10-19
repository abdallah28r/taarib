"""Work with translation units: validate, normalize, search, mark, and report progress.

    python scripts/loc.py validate [units/]
    python scripts/loc.py normalize [units/]
    python scripts/loc.py search "Save" [--kind image]
    python scripts/loc.py mark --batch batch-003 --status integrated --evidence "build 1.2 patch r4"
    python scripts/loc.py findings work/proofreading/batch-003.jsonl
    python scripts/loc.py extract --adapter adapters/renpy.py --game <game_root> --out units/game.jsonl
    python scripts/loc.py rebuild --adapter adapters/renpy.py --game <game_root> --out builds/r1
    python scripts/loc.py next                  # current phase, what blocks it, what to load
    python scripts/loc.py gate [--check]        # advance when every exit criterion passes
    python scripts/loc.py reopen extraction --reason "game update 1.1"
    python scripts/loc.py accept --note "user accepted build r3 on 2026-11-02"
    python scripts/loc.py progress --format chat|md|html [--out PATH]

Progress is computed only from unit statuses and qa/LQA_MATRIX.csv, never from
an agent's estimate.
"""
from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path=None):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path or ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


units = _load("loc_units")
adapter_base = _load("loc_adapter_base", ROOT / "adapters" / "base.py")
pipeline = _load("loc_pipeline")

LABELS = {
    "extracted": "مستخرج",
    "translated": "مترجم",
    "proofread": "مدقق لغويًا",
    "integrated": "مدمج في اللعبة",
    "tested": "مختبر داخل اللعبة",
}
KIND_LABELS = {"all": "الكل", "text": "النصوص", "image": "نصوص الصور"}
DEFAULT_OUT = {"md": ROOT / "reports" / "PROGRESS.md", "html": ROOT / "reports" / "progress.html"}
QA_MATRIX = ROOT / "qa" / "LQA_MATRIX.csv"
MEANING_NOTE = (
    "مترجم = النص العربي موجود في الملفات. مدمج = أصبح جزءًا من نسخة اللعبة. "
    "مختبر = تأكدنا من ظهوره وعمله داخل اللعبة. ترجمة 100% لا تعني أن اللعبة جاهزة."
)


def token_profile() -> str:
    try:
        import yaml
        project = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8"))
        return project.get("game", {}).get("token_profile", "generic") or "generic"
    except Exception:
        return "generic"


# ----- progress model -------------------------------------------------------

def compute(all_units: list[dict]) -> dict:
    groups = {}
    for kind in ("all", "text", "image"):
        members = [u for u in all_units if kind == "all" or u.get("kind") == kind]
        applicable = [u for u in members if units.decision(u) != "keep"]
        reached = {
            status: sum(1 for u in applicable if units.stage(u) >= index)
            for index, status in enumerate(units.STATUSES)
        }
        groups[kind] = {
            "total": len(members),
            "applicable": len(applicable),
            "keep": len(members) - len(applicable),
            "review": sum(1 for u in members if units.decision(u) == "review"),
            "reached": reached,
        }
    return groups


def qa_cases(path: Path = QA_MATRIX) -> dict:
    counts = {"total": 0, "passed": 0, "failed": 0, "not_run": 0}
    if not path.is_file():
        return counts
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            status = (row.get("status") or "").strip().lower()
            counts["total"] += 1
            if status in ("pass", "passed"):
                counts["passed"] += 1
            elif status in ("fail", "failed"):
                counts["failed"] += 1
            elif status in ("", "not-run", "not run", "n/a"):
                counts["not_run"] += 1
    return counts


def percent(part: int, whole: int) -> int | None:
    return round(100 * part / whole) if whole else None


def pct_text(part: int, whole: int) -> str:
    value = percent(part, whole)
    return "—" if value is None else f"{value}%"


def bar(part: int, whole: int, width: int = 20) -> str:
    filled = round(width * part / whole) if whole else 0
    return "█" * filled + "░" * (width - filled)


def qa_line(qa: dict) -> str:
    if not qa["total"]:
        return "حالات الاختبار: لا توجد حالات في qa/LQA_MATRIX.csv"
    executed = qa["total"] - qa["not_run"]
    return (f"حالات الاختبار: نُفذ {executed} من {qa['total']} "
            f"({pct_text(executed, qa['total'])})، نجح {qa['passed']}، فشل {qa['failed']}")


def extra_lines(group: dict) -> list[str]:
    lines = []
    if group["review"]:
        lines.append(f"تحتاج قرارًا (review): {group['review']}")
    if group["keep"]:
        lines.append(f"تُترك دون ترجمة عمدًا (keep): {group['keep']} — خارج النسب")
    return lines


# ----- renderers ------------------------------------------------------------

def render_chat(groups: dict, qa: dict) -> str:
    g = groups["all"]
    if not g["total"]:
        return "لا توجد وحدات ترجمة بعد.\n" + qa_line(qa) + "\n"
    lines = [f"تقدم التعريب — عدد الوحدات: {g['total']} (النصوص: {groups['text']['total']}، مناطق الصور: {groups['image']['total']})"]
    for status in units.STATUSES:
        done = g["reached"][status]
        lines.append(f"- {LABELS[status]}: {pct_text(done, g['applicable'])} ({done} من {g['applicable']})")
    lines.append(qa_line(qa))
    lines += extra_lines(g)
    return "\n".join(lines) + "\n"


def render_md(groups: dict, qa: dict, generated: str) -> str:
    g = groups["all"]
    out = [
        "# تقرير تقدم التعريب",
        "",
        f"> مولَّد من `units/` و`qa/LQA_MATRIX.csv` بالأمر `python scripts/loc.py progress --format md` في {generated}. لا تعدّله يدويًا.",
        "",
        f"> {MEANING_NOTE}",
        "",
    ]
    if not g["total"]:
        out += ["لا توجد وحدات ترجمة بعد.", "", qa_line(qa), ""]
        return "\n".join(out)
    out += ["## الكل", "", "| المرحلة | التقدم | النسبة | العدد |", "|---|---|---|---|"]
    for status in units.STATUSES:
        done = g["reached"][status]
        out.append(f"| {LABELS[status]} | `{bar(done, g['applicable'])}` | {pct_text(done, g['applicable'])} | {done} من {g['applicable']} |")
    out += ["", "## حسب النوع", "", "| المرحلة | النصوص | نصوص الصور |", "|---|---|---|"]
    for status in units.STATUSES:
        cells = [
            f"{pct_text(groups[k]['reached'][status], groups[k]['applicable'])} ({groups[k]['reached'][status]}/{groups[k]['applicable']})"
            for k in ("text", "image")
        ]
        out.append(f"| {LABELS[status]} | {cells[0]} | {cells[1]} |")
    out += ["", "## الاختبار والقرارات", "", f"- {qa_line(qa)}"]
    out += [f"- {line}" for line in extra_lines(g)]
    return "\n".join(out) + "\n"


HTML_STYLE = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--track:#e6e6e1;--fill:#2f6f5e;--line:#ddddd6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161615;--card:#20201f;--ink:#ececea;--muted:#a3a39d;--track:#33332f;--fill:#5fb39a;--line:#3a3a36}}
:root[data-theme="dark"]{--bg:#161615;--card:#20201f;--ink:#ececea;--muted:#a3a39d;--track:#33332f;--fill:#5fb39a;--line:#3a3a36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,"Segoe UI",Tahoma,sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px}h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:28px 0 12px}
.muted{color:var(--muted);font-size:.9rem}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.row{display:grid;grid-template-columns:9rem 1fr 4.5rem;gap:12px;align-items:center;padding:6px 0}
.track{height:12px;background:var(--track);border-radius:6px;overflow:hidden}.fill{height:100%;background:var(--fill)}
.num{text-align:left;font-variant-numeric:tabular-nums}table{width:100%;border-collapse:collapse}
td,th{padding:8px;border-bottom:1px solid var(--line);text-align:right}ul{padding-inline-start:20px}
@media (max-width:480px){.row{grid-template-columns:6.5rem 1fr 3.5rem}}
"""


def render_html(groups: dict, qa: dict, generated: str) -> str:
    g = groups["all"]
    esc = html.escape
    parts = [
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>تقدم التعريب</title><style>{HTML_STYLE}</style></head><body><main>",
        "<h1>تقدم التعريب</h1>",
        f'<p class="muted">مولَّد من units/ وqa/LQA_MATRIX.csv في {esc(generated)}. {esc(MEANING_NOTE)}</p>',
    ]
    if not g["total"]:
        parts.append(f'<div class="card"><p>لا توجد وحدات ترجمة بعد.</p><p>{esc(qa_line(qa))}</p></div>')
    else:
        parts.append(f'<h2>الكل — عدد الوحدات: {g["total"]}</h2><div class="card">')
        for status in units.STATUSES:
            done = g["reached"][status]
            width = percent(done, g["applicable"]) or 0
            parts.append(
                f'<div class="row"><span>{LABELS[status]}</span>'
                f'<div class="track" role="progressbar" aria-valuenow="{width}" aria-valuemin="0" aria-valuemax="100">'
                f'<div class="fill" style="width:{width}%"></div></div>'
                f'<span class="num">{pct_text(done, g["applicable"])}</span></div>'
            )
        parts.append("</div><h2>حسب النوع</h2><div class=\"card\"><table><tr><th>المرحلة</th><th>النصوص</th><th>نصوص الصور</th></tr>")
        for status in units.STATUSES:
            cells = "".join(
                f"<td>{pct_text(groups[k]['reached'][status], groups[k]['applicable'])} "
                f"<span class=\"muted\">({groups[k]['reached'][status]}/{groups[k]['applicable']})</span></td>"
                for k in ("text", "image")
            )
            parts.append(f"<tr><td>{LABELS[status]}</td>{cells}</tr>")
        parts.append("</table></div>")
        items = "".join(f"<li>{esc(line)}</li>" for line in [qa_line(qa), *extra_lines(g)])
        parts.append(f'<h2>الاختبار والقرارات</h2><div class="card"><ul>{items}</ul></div>')
    parts.append("</main></body></html>\n")
    return "".join(parts)


# ----- commands -------------------------------------------------------------

def load_checked(path: Path):
    report = units.Report()
    files = units.load(path, report)
    units.validate(files, token_profile(), report)
    return files, report


def print_report(report) -> None:
    for line in report.errors:
        print(f"ERROR {line}")
    for line in report.warnings:
        print(f"WARN  {line}")


def cmd_validate(args) -> int:
    files, report = load_checked(args.path)
    print_report(report)
    print(f"FILES={len(files)} UNITS={len(units.all_units(files))} "
          f"ERRORS={len(report.errors)} WARNINGS={len(report.warnings)}")
    return 1 if report.errors else 0


def cmd_normalize(args) -> int:
    report = units.Report()
    files = units.load(args.path, report)
    if report.errors:
        print_report(report)
        return 1
    refused = 0
    for unit_file in files:
        for unit in unit_file.units:
            current = units.source_hash(unit.get("source", ""))
            if "source_hash" not in unit or unit.get("status") == "extracted":
                unit["source_hash"] = current
            elif unit["source_hash"] != current:
                refused += 1
                print(f"ERROR {unit_file.path} [{unit.get('id')}]: source changed after {unit.get('status')}; "
                      "review it and mark it extracted first")
        units.write(unit_file)
    print(f"NORMALIZED_FILES={len(files)} REFUSED={refused}")
    return 1 if refused else 0


def cmd_search(args) -> int:
    report = units.Report()
    needle = args.query.casefold()
    hits = 0
    for unit in units.all_units(units.load(args.path, report)):
        if args.kind and unit.get("kind") != args.kind:
            continue
        fields = {"source": [unit.get("source", "")], "target": [unit.get("target", "")],
                  "both": [unit.get("source", ""), unit.get("target", "")]}[args.field]
        if any(needle in (value or "").casefold() for value in fields):
            hits += 1
            where = unit.get("asset") or unit.get("file")
            print(f"{unit.get('id')}\t{unit.get('kind')}\t{unit.get('status')}\t{where}\t"
                  f"{unit.get('source', '')}\t{unit.get('target', '')}")
    print_report(report)
    print(f"MATCHES={hits}")
    return 0


def cmd_mark(args) -> int:
    report = units.Report()
    files = units.load(args.path, report)
    if report.errors:
        print_report(report)
        return 1
    wanted = units.STATUSES.index(args.status)
    evidence_key = units.STAGE_EVIDENCE.get(args.status)
    if evidence_key and not args.evidence:
        print(f"ERROR status {args.status} requires --evidence (stored as evidence.{evidence_key})")
        return 2
    if args.status == "proofread" and not args.by:
        print("ERROR status proofread requires --by with the proofreader's role label")
        return 2
    before = set(units.validate(files, token_profile()).errors)
    ids = set(args.ids or [])
    changed = 0
    for unit in units.all_units(files):
        selected = (unit.get("id") in ids or (args.batch and unit.get("batch") == args.batch)
                    or (args.file and unit.get("file") == args.file))
        if not selected:
            continue
        if units.stage(unit) > wanted and not args.force:
            print(f"ERROR [{unit.get('id')}]: {unit.get('status')} -> {args.status} moves backward; use --force")
            return 1
        unit["status"] = args.status
        if evidence_key:
            unit.setdefault("evidence", {})[evidence_key] = args.evidence
        if args.by and args.status == "translated":
            unit["translated_by"] = args.by
        if args.status == "proofread":
            unit["proofread_by"] = args.by
            unit["proofread_hash"] = units.source_hash(unit.get("target") or "")
        elif wanted < units.STATUSES.index("proofread"):
            unit.pop("proofread_by", None)
            unit.pop("proofread_hash", None)
        changed += 1
    introduced = [e for e in units.validate(files, token_profile()).errors if e not in before]
    if introduced:
        for line in introduced:
            print(f"ERROR {line}")
        print("NOT_WRITTEN: this change would introduce the errors above")
        return 1
    for unit_file in files:
        units.write(unit_file)
    print(f"MARKED={changed} STATUS={args.status}")
    return 0 if changed else 1


SEVERITIES = ("blocker", "critical", "major", "minor")
CATEGORIES = ("meaning", "omission", "context", "terminology", "grammar", "spelling",
              "punctuation", "style", "voice", "length", "numbers")
RESOLUTIONS = ("applied", "needs_decision", "rejected", "resolved")


def check_findings(findings: list[tuple[str, dict]], by_id: dict) -> tuple[list[str], dict]:
    """Validate proofreading findings against the units they refer to."""
    errors: list[str] = []
    last_change: dict[str, tuple[str, str]] = {}
    open_items: dict[str, str] = {}
    for where, item in findings:
        missing = [k for k in ("id", "severity", "category", "issue", "resolution", "by") if not item.get(k)]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        ident = item["id"]
        unit = by_id.get(ident)
        if unit is None:
            errors.append(f"{where}: unknown unit id {ident!r}")
            continue
        for key, allowed in (("severity", SEVERITIES), ("category", CATEGORIES), ("resolution", RESOLUTIONS)):
            if item[key] not in allowed:
                errors.append(f"{where} [{ident}]: {key} must be one of {allowed}")
        if item["by"] == unit.get("translated_by"):
            errors.append(f"{where} [{ident}]: finding signed by the unit's translator ({item['by']})")
        resolution = item["resolution"]
        if resolution in ("applied", "resolved"):
            if "after" not in item or (resolution == "applied" and "before" not in item):
                errors.append(f"{where} [{ident}]: {resolution} needs before/after")
            else:
                last_change[ident] = (where, item["after"])
        if resolution == "needs_decision":
            open_items[ident] = where
        elif resolution == "resolved":
            open_items.pop(ident, None)
    for ident, (where, after) in last_change.items():
        if (by_id[ident].get("target") or "") != after:
            errors.append(f"{where} [{ident}]: unit target no longer matches the recorded 'after'")
    for ident, where in open_items.items():
        if units.stage(by_id[ident]) >= units.STATUSES.index("proofread"):
            errors.append(f"{where} [{ident}]: marked {by_id[ident]['status']} with an open needs_decision finding")
    summary = {
        key: {value: sum(1 for _, f in findings if f.get(key) == value) for value in allowed}
        for key, allowed in (("severity", SEVERITIES), ("category", CATEGORIES), ("resolution", RESOLUTIONS))
    }
    summary["open"] = sorted(open_items)
    return errors, summary


def parse_options(values: list[str]) -> dict:
    options = {}
    for value in values:
        key, sep, item = value.partition("=")
        if not sep:
            raise SystemExit(f"ERROR --option needs key=value, got {value!r}")
        options[key] = item
    return options


def cmd_extract(args) -> int:
    adapter = adapter_base.load_adapter(args.adapter, args.game, parse_options(args.option))
    out = args.out or units.UNITS_DIR / f"{Path(args.game).resolve().name}.jsonl"
    if out.exists() and not args.force:
        print(f"ERROR {out} exists; use --force to replace it (game updates are merged, not re-extracted)")
        return 1
    extracted = adapter.extract()
    report = units.validate([units.UnitFile(out, extracted)], adapter.token_profile)
    if report.errors:
        print_report(report)
        print("NOT_WRITTEN: the adapter produced invalid units")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    units.write(units.UnitFile(out, extracted))
    translated = sum(1 for u in extracted if u.get("target"))
    print(f"EXTRACTED={len(extracted)} ALREADY_TRANSLATED={translated} OUT={out}")
    return 0


def cmd_rebuild(args) -> int:
    game, out = Path(args.game).resolve(), Path(args.out).resolve()
    if out == game or out.is_relative_to(game):
        print("ERROR --out must be outside the game folder; install from it with backups as a separate step")
        return 2
    files, report = load_checked(args.path)
    if report.errors:
        print_report(report)
        print("NOT_BUILT: fix unit errors first")
        return 1
    minimum = units.STATUSES.index(args.min_status)
    selected, held_back = [], 0
    for unit in units.all_units(files):
        ready = (units.stage(unit) >= minimum and units.decision(unit) == "translate"
                 and bool(unit.get("target")))
        held_back += bool(unit.get("target")) and not ready
        selected.append({**unit, "target": unit.get("target", "") if ready else ""})
    adapter = adapter_base.load_adapter(args.adapter, game, parse_options(args.option))
    out.mkdir(parents=True, exist_ok=True)
    written = adapter.rebuild(selected, out)
    for rel in written:
        print(f"WROTE {rel}")
    included = sum(1 for u in selected if u["target"])
    print(f"REBUILT_FILES={len(written)} UNITS_INCLUDED={included} HELD_BACK={held_back} "
          f"MIN_STATUS={args.min_status} OUT={out}")
    return 0


def project_of(args):
    return pipeline.Project(project_file=args.project, units_dir=args.units, state_file=args.state, qa_file=args.qa)


def print_checks(checks) -> None:
    for ok, message in checks:
        print(f"{'PASS' if ok else 'TODO'} {message}")


def cmd_next(args) -> int:
    project = project_of(args)
    phase, checks = pipeline.evaluate(project)
    index = pipeline.PHASES.index(phase)
    print(f"PHASE {index + 1}/{len(pipeline.PHASES)}: {phase}")
    blocking = [(ok, m) for ok, m in checks if not ok]
    print_checks(blocking or checks)
    print(f"LOAD: {pipeline.ROUTES[phase]}")
    if not blocking and phase != pipeline.PHASES[-1]:
        print("READY: run python scripts/loc.py gate")
    return 0


def cmd_gate(args) -> int:
    project = project_of(args)
    phase = project.state()["phase"]
    if phase == "extraction":
        settings = project.settings()
        flow, game = settings.get("workflow", {}), settings.get("game", {}).get("install_path", "")
        if pipeline.filled(flow.get("adapter", "")) and pipeline.filled(game):
            contract = _load("adapter_contract")
            result = contract.run_contract(project.resolve(flow["adapter"]), Path(game), flow.get("adapter_options") or {})
            for name, ok, detail in result.checks:
                print(f"{'PASS' if ok else 'FAIL'} contract {name}{': ' + detail if detail else ''}")
            if not args.check:
                pipeline.record_contract(project, result.ok)
    if args.check:
        phase, checks = pipeline.evaluate(project)
        print_checks(checks)
        ready = all(ok for ok, _ in checks)
        print(f"GATE {phase}: {'READY' if ready else 'BLOCKED'}")
        return 0 if ready else 1
    moved, now_phase, checks = pipeline.advance(project)
    print_checks(checks)
    if moved:
        print(f"GATE {phase}: PASSED -> {now_phase}")
        return 0
    print(f"GATE {phase}: BLOCKED")
    return 1


def cmd_reopen(args) -> int:
    try:
        pipeline.reopen(project_of(args), args.phase, args.reason)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print(f"REOPENED {args.phase}")
    return 0


def cmd_accept(args) -> int:
    try:
        pipeline.accept(project_of(args), args.note)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print("ACCEPTANCE_RECORDED")
    return 0


def cmd_findings(args) -> int:
    report = units.Report()
    by_id = {u.get("id"): u for u in units.all_units(units.load(args.path, report))}
    findings = []
    for file in args.files:
        for number, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                findings.append((f"{file}:{number}", json.loads(line)))
            except json.JSONDecodeError as exc:
                report.errors.append(f"{file}:{number}: invalid JSON: {exc.msg}")
    errors, summary = check_findings(findings, by_id)
    report.errors += errors
    print_report(report)
    for key in ("severity", "category", "resolution"):
        counts = ", ".join(f"{k}={v}" for k, v in summary[key].items() if v)
        print(f"{key.upper()}: {counts or 'none'}")
    print(f"OPEN_DECISIONS={len(summary['open'])} {' '.join(summary['open'])}".rstrip())
    print(f"FINDINGS={len(findings)} ERRORS={len(report.errors)}")
    return 1 if report.errors else 0


def cmd_progress(args) -> int:
    report = units.Report()
    all_units = units.all_units(units.load(args.path, report))
    groups, qa = compute(all_units), qa_cases(args.qa)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.format == "chat":
        print(render_chat(groups, qa), end="")
        return 0
    text = render_md(groups, qa, generated) if args.format == "md" else render_html(groups, qa, generated)
    out = args.out or DEFAULT_OUT[args.format]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"PROGRESS_REPORT={out}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def with_path(p):
        p.add_argument("path", nargs="?", type=Path, default=units.UNITS_DIR)
        return p

    with_path(sub.add_parser("validate", help="check every unit")).set_defaults(run=cmd_validate)
    with_path(sub.add_parser("normalize", help="fill hashes and canonical key order")).set_defaults(run=cmd_normalize)

    p = sub.add_parser("search", help="find text in sources and targets, including image text")
    p.add_argument("query")
    with_path(p)
    p.add_argument("--field", choices=("both", "source", "target"), default="both")
    p.add_argument("--kind", choices=units.KINDS)
    p.set_defaults(run=cmd_search)

    p = sub.add_parser("mark", help="advance the status of selected units")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--status", required=True, choices=units.STATUSES)
    p.add_argument("--ids", nargs="+")
    p.add_argument("--batch")
    p.add_argument("--file")
    p.add_argument("--evidence", help="required for integrated (build) and tested (what was observed)")
    p.add_argument("--by", help="agent or person label for translated/proofread")
    p.add_argument("--force", action="store_true", help="allow moving a unit backward")
    p.set_defaults(run=cmd_mark)

    p = sub.add_parser("extract", help="write units from a game through an adapter")
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--game", required=True, type=Path)
    p.add_argument("--out", type=Path, help="default units/<game folder name>.jsonl")
    p.add_argument("--option", action="append", default=[], help="adapter option key=value")
    p.add_argument("--force", action="store_true")
    p.set_defaults(run=cmd_extract)

    p = sub.add_parser("rebuild", help="write localized game files to a separate folder")
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--game", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--min-status", choices=units.STATUSES[1:], default="proofread",
                   help="lowest status whose target is built (default proofread)")
    p.add_argument("--option", action="append", default=[], help="adapter option key=value")
    p.set_defaults(run=cmd_rebuild)

    def with_project(p):
        p.add_argument("--project", type=Path, default=ROOT / "PROJECT.yaml", help=argparse.SUPPRESS)
        p.add_argument("--units", type=Path, default=units.UNITS_DIR, help=argparse.SUPPRESS)
        p.add_argument("--state", type=Path, default=ROOT / "state" / "pipeline.json", help=argparse.SUPPRESS)
        p.add_argument("--qa", type=Path, default=QA_MATRIX, help=argparse.SUPPRESS)
        return p

    with_project(sub.add_parser("next", help="show the current phase and what blocks it")).set_defaults(run=cmd_next)
    p = with_project(sub.add_parser("gate", help="advance the phase when every exit criterion passes"))
    p.add_argument("--check", action="store_true", help="evaluate without advancing or recording")
    p.set_defaults(run=cmd_gate)
    p = with_project(sub.add_parser("reopen", help="return to an earlier phase"))
    p.add_argument("phase", choices=pipeline.PHASES)
    p.add_argument("--reason", required=True)
    p.set_defaults(run=cmd_reopen)
    p = with_project(sub.add_parser("accept", help="record the user's acceptance of the playtest build"))
    p.add_argument("--note", required=True, help="the user's words, build, and date")
    p.set_defaults(run=cmd_accept)

    p = sub.add_parser("findings", help="validate and summarize proofreading findings")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.set_defaults(run=cmd_findings)

    p = sub.add_parser("progress", help="report progress as chat text, Markdown, or HTML")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--format", choices=("chat", "md", "html"), default="chat")
    p.add_argument("--out", type=Path)
    p.add_argument("--qa", type=Path, default=QA_MATRIX)
    p.set_defaults(run=cmd_progress)

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.command == "mark" and not (args.ids or args.batch or args.file):
        parser.error("mark needs --ids, --batch, or --file")
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
