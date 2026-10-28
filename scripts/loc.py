"""Work with translation units: validate, normalize, search, mark, and report progress.

    python scripts/loc.py validate [units/]
    python scripts/loc.py normalize [units/]
    python scripts/loc.py search "Save" [--kind image]
    python scripts/loc.py mark --batch batch-003 --status integrated --evidence "build 1.2 patch r4"
    python scripts/loc.py brief --batch batch-003 --role translator --runtime claude-code
    python scripts/loc.py apply work/batches/batch-003.json --batch batch-003 --by translator-1
    python scripts/loc.py search --problem latin_leak --ids-only
    python scripts/loc.py findings work/proofreading/batch-003.jsonl
    python scripts/loc.py terms [--allow <id> <term>]   # glossary conformance
    python scripts/loc.py extract --adapter adapters/renpy.py --game <game_root> --out units/game.jsonl
    python scripts/loc.py rebuild --adapter adapters/renpy.py --game <game_root> --out builds/r1
    python scripts/loc.py update --adapter adapters/renpy.py --game <game_root> --path units/game.jsonl
    python scripts/loc.py estimate | tmx --out memory.tmx | pseudo --adapter ... --game ... --out builds/pseudo
    python scripts/loc.py fix open --title ... --current ... --expected ... --unchanged ... --ids <ids>
    python scripts/loc.py lesson add --type limit --what ... --evidence ... [--suggest ... --file ...]
    python scripts/loc.py experiences           # handoff: experiences-<game>-<date>.zip for the developer
    python scripts/loc.py next                  # current phase, what blocks it, what to load
    python scripts/loc.py gate [--check]        # advance when every exit criterion passes
    python scripts/loc.py reopen extraction --reason "game update 1.1"
    python scripts/loc.py accept --note "user accepted build r3 on 2026-11-02"
    python scripts/loc.py progress --format chat|md|html [--out PATH]
    python scripts/loc.py dashboard             # dashboard.html (also refreshed automatically)
    python scripts/loc.py probe --game <game_root> [--preview --font <ttf>] [--record] [--launch <exe>]

Progress is computed only from unit statuses and qa/LQA_MATRIX.csv, never from
an agent's estimate.
"""
from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
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
board = pipeline.tasks
tools = _load("loc_tools")
brief_tools = _load("loc_brief")
experiences = _load("loc_experiences")

LABELS = {
    "extracted": "مستخرج",
    "translated": "مترجم",
    "proofread": "مدقق لغويًا",
    "integrated": "مدمج في اللعبة",
    "tested": "مختبر داخل اللعبة",
}
KIND_LABELS = {"all": "الكل", "text": "النصوص", "image": "نصوص الصور"}
DEFAULT_OUT = {"md": ROOT / "reports" / "PROGRESS.md"}
QA_MATRIX = ROOT / "qa" / "LQA_MATRIX.csv"
MEANING_NOTE = (
    "مترجم = النص العربي موجود في الملفات. مدمج = أصبح جزءًا من نسخة اللعبة. "
    "مختبر = تأكدنا من ظهوره وعمله داخل اللعبة. ترجمة 100% لا تعني أن اللعبة جاهزة."
)


def review_mode() -> str:
    import yaml
    try:
        project = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}
    except OSError:
        return "separate"
    return (project.get("workflow") or {}).get("review_mode") or "separate"


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
            "rewrite": sum(1 for u in members if units.stage(u) == 0 and u.get("previous_target")),
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
    if group.get("rewrite"):
        lines.append(f"تحتاج إعادة كتابة بعد تحديث اللعبة: {group['rewrite']} (loc.py search --problem needs_rewrite)")
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
.card+.card{margin-top:12px}.phases{display:flex;flex-wrap:wrap;gap:6px;list-style:none;padding:0;margin:0 0 12px}
.phases li{padding:4px 10px;border-radius:999px;border:1px solid var(--line);font-size:.9rem;color:var(--muted)}
.phases li.done{color:var(--fill);border-color:var(--fill)}.phases li.now{background:var(--fill);color:var(--card);border-color:var(--fill)}
.plan h2,.plan h3,.plan h4{font-size:1rem;margin:16px 0 6px}.plan p{margin:4px 0}
.checks{list-style:none;padding:0;margin:0}.checks li{padding:4px 0}.checks li.ok{color:var(--fill)}
bdi{unicode-bidi:isolate}.checks li.err{color:#c0392b}
.card.wait{border-color:#c0392b}.pages{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.pages a{padding:6px 14px;border:1px solid var(--line);
border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none}.pages a:hover{border-color:var(--fill)}
td,th{padding:8px;border-bottom:1px solid var(--line);text-align:right}ul{padding-inline-start:20px}
@media (max-width:480px){.row{grid-template-columns:6.5rem 1fr 3.5rem}}
"""


PHASE_LABELS = {
    "intake": "الاستقبال", "discovery": "الاكتشاف", "extraction": "الاستخراج", "pilot": "التجربة الأولى",
    "localization": "التعريب", "integration": "الدمج", "playtest": "التجربة", "handoff": "التسليم",
    "release": "النشر",
}
# Ships with the template (an empty project's page) and lives in every game copy beside the map.
DASHBOARD = ROOT / "dashboard.html"
TASKS_PAGE = ROOT / "tasks.html"
EVENT_LABELS = {"passed": "عبرت بوابة", "reopened": "أُعيد فتح", "blocked": "محاولة عبور لم تكتمل في"}
MAP_PAGE = "template-map.html"
PLAN_FILE = ROOT / "PLAN.md"
PLAN_MAX_LINES = 150


def local_time(stamp: str) -> str:
    """A recorded UTC time (2026-10-28T13:52:37Z) in this computer's time, as the user reads a clock."""
    try:
        moment = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return html.escape(str(stamp or ""))
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def markdown_html(text: str) -> str:
    """Just enough Markdown for PLAN.md: headings, checklists, bullets, paragraphs. Everything is escaped."""
    esc, out, in_list = html.escape, [], False
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for raw in text.splitlines():
        line = raw.strip()
        item = re.match(r"^[-*] (\[( |x|X)\] )?(.*)$", line)
        if item and not in_list:
            out.append("<ul>")
            in_list = True
        if not item and in_list:
            out.append("</ul>")
            in_list = False
        if item:
            box = item.group(2)
            mark = "" if box is None else ("☑ " if box.lower() == "x" else "☐ ")
            out.append(f"<li>{mark}{esc(item.group(3))}</li>")
        elif line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")) + 1, 4)
            out.append(f"<h{level}>{esc(line.lstrip('#').strip())}</h{level}>")
        elif line:
            out.append(f"<p>{esc(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)


def progress_html(groups: dict, qa: dict, problems: dict | None = None) -> str:
    g, esc = groups["all"], html.escape
    if not g["total"]:
        return f'<div class="card"><p>لا توجد وحدات ترجمة بعد.</p><p>{esc(qa_line(qa))}</p></div>'
    parts = [f'<div class="card"><p class="muted">عدد الوحدات: {g["total"]}</p>']
    for status in units.STATUSES:
        done = g["reached"][status]
        width = percent(done, g["applicable"]) or 0
        parts.append(
            f'<div class="row"><span>{LABELS[status]}</span>'
            f'<div class="track" role="progressbar" aria-valuenow="{width}" aria-valuemin="0" aria-valuemax="100">'
            f'<div class="fill" style="width:{width}%"></div></div>'
            f'<span class="num">{pct_text(done, g["applicable"])}</span></div>'
        )
    parts.append('</div><div class="card"><table><tr><th>المرحلة</th><th>النصوص</th><th>نصوص الصور</th></tr>')
    for status in units.STATUSES:
        cells = "".join(
            f"<td>{pct_text(groups[k]['reached'][status], groups[k]['applicable'])} "
            f"<span class=\"muted\">({groups[k]['reached'][status]}/{groups[k]['applicable']})</span></td>"
            for k in ("text", "image")
        )
        parts.append(f"<tr><td>{LABELS[status]}</td>{cells}</tr>")
    items = "".join(f"<li>{esc(line)}</li>" for line in [qa_line(qa), *extra_lines(g)])
    parts.append(f'</table></div><div class="card"><ul>{items}</ul></div>')
    if problems:
        overrides = project_qa()[1]
        rows = "".join(f'<li class="{"err" if tools.level(c, overrides) == "error" else ""}"><bdi>{c}</bdi>: {n}</li>'
                       for c, n in problems.items())
        parts.append(f'<div class="card"><p class="muted">المشكلات حسب الكود (loc.py search --problem)</p>'
                     f'<ul class="checks">{rows}</ul></div>')
    return "".join(parts)


def experiences_html(state: dict, lessons: int) -> str:
    packed = state.get("experiences")
    if not lessons and not packed:
        return ""
    esc = html.escape
    rows = [f"<li>خبرات مسجلة لمطوّر القالب: {lessons} (loc.py lesson list)</li>"]
    if packed:
        rows += [f"<li>{esc(line)}</li>" for line in experiences.send_message(Path(packed["path"]).name).splitlines()]
    return f'<div class="card"><p class="muted">ملف الخبرات</p><ul>{"".join(rows)}</ul></div>'


def phase_html(state: dict, checks) -> str:
    esc, current = html.escape, state.get("phase", pipeline.PHASES[0])
    passed = {event["phase"] for event in state.get("history", []) if event.get("event") == "passed"}
    steps = []
    for phase in pipeline.PHASES:
        cls = "now" if phase == current else ("done" if phase in passed else "")
        steps.append(f'<li class="{cls}">{PHASE_LABELS[phase]}</li>')
    parts = [f'<ol class="phases">{"".join(steps)}</ol>']
    if checks:
        rows = "".join(f'<li class="{"ok" if ok else "todo"}">{"✓" if ok else "○"} <bdi>{esc(message)}</bdi></li>'
                       for ok, message in checks)
        parts.append(f'<div class="card"><p class="muted">شروط إغلاق مرحلة {PHASE_LABELS[current]}</p>'
                     f'<ul class="checks">{rows}</ul></div>')
    fixes = state.get("fixes", [])
    if fixes:
        rows = "".join(f'<li>{esc(f["id"])} — {esc(f["title"])} — '
                       f'{"مفتوح" if f["status"] == "open" else esc(f.get("verdict", ""))}</li>' for f in fixes[-8:])
        parts.append(f'<div class="card"><p class="muted">الإصلاحات السريعة (loc.py fix)</p><ul>{rows}</ul></div>')
    recent = state.get("history", [])[-5:]
    if recent:
        rows = "".join(
            f'<li>{local_time(e.get("at", ""))} — {esc(EVENT_LABELS.get(e.get("event"), e.get("event", "")))} '
            f'{PHASE_LABELS.get(e.get("phase"), "")}'
            f'{esc(" (ناقص " + str(e["missing"]) + ")") if e.get("missing") else ""}'
            f'{esc(" — " + e["reason"]) if e.get("reason") else ""}</li>'
            for e in reversed(recent)
        )
        parts.append(f'<div class="card"><p class="muted">آخر الأحداث</p><ul>{rows}</ul></div>')
    return "".join(parts)


def quality_html(quality: dict | None) -> str:
    if not quality:
        return ""
    dims = "، ".join(f"<bdi>{d}</bdi> {n}" for d, n in sorted(quality["dimensions"].items())) or "لا شيء"
    return ('<h2>جودة التدقيق (MQM)</h2><div class="card"><ul>'
            f'<li>وحدات عليها ملاحظات: {quality["flagged"]} من {quality["units"]} ({quality["flag_rate"]}%)</li>'
            f'<li>نقاط الخطأ لكل 1000 كلمة: {quality["per_1000_words"]} (ثانوي 1، كبير 5، حرج 10، مانع 25)</li>'
            f'<li>حسب البُعد: {dims}</li></ul></div>')


def tasks_summary_html(tasks: list[dict], cards: list[dict], page: str) -> str:
    counts = Counter(t["status"] for t in [*tasks, *cards])
    shown = "، ".join(f"{board.LABELS[s]} {counts[s]}" for s in board.STATUSES if counts[s]) or "لا مهام مسجلة بعد"
    waiting = [t for t in tasks if t["status"] == "waiting"]
    rows = "".join(f'<li class="err">{html.escape(t["title"])}'
                   f'{html.escape(" — " + t["reason"]) if t.get("reason") else ""}</li>' for t in waiting[:5])
    head = (f'<div class="card wait"><p><b>بانتظارك ({len(waiting)})</b></p><ul class="checks">{rows}</ul></div>'
            if waiting else "")
    return (f'{head}<div class="card"><p class="muted">مهام الوكيل — <a href="{page}">لوحة المهام</a></p>'
            f'<p>{html.escape(shown)}</p></div>')


def probe_html(probe: dict | None) -> str:
    """The last loc.py probe: engine, fonts with Arabic, and the boot verdict from the game's log."""
    if not probe:
        return ""
    esc = html.escape
    fonts = probe.get("fonts") or {}
    rows = [f'<li>المحرك: <bdi>{esc(str(probe.get("engine") or "?"))}</bdi></li>',
            f'<li>خطوط فيها حروف عربية: {fonts.get("arabic", 0)} من {fonts.get("total", 0)}</li>']
    if probe.get("boot"):
        rows.append(f'<li>حكم الإقلاع من السجل: <bdi>{esc(probe["boot"])}</bdi></li>')
    return (f'<div class="card"><p class="muted">آخر فحص للعبة (loc.py probe) — {esc(probe.get("at", ""))}</p>'
            f'<ul>{"".join(rows)}</ul></div>')


def task_card(t: dict) -> str:
    esc = html.escape
    tags = [board.KIND_LABELS.get(t.get("kind"), "")]
    if t.get("from_plan"):
        tags.append("دفعة")
    elif t.get("phase"):
        tags.append(PHASE_LABELS.get(t["phase"], t["phase"]))
    if t["status"] == "dropped":
        tags.append("أُلغيت")
    history = "".join(f'<li>{local_time(h["at"])} — {board.LABELS.get(h["status"], h["status"])}'
                      f'{esc(" — " + h["note"]) if h.get("note") else ""}</li>' for h in t.get("history", []))
    detail = (f'<details><summary>المراحل ({len(t["history"])})</summary><ul>{history}</ul></details>'
              if history else "")
    extra = "".join(f'<p class="muted">{label}: <bdi>{esc(t[key])}</bdi></p>'
                    for key, label in (("who", "يعمل عليها"), ("progress", "توقفت عند"), ("reason", "السبب"),
                                       ("evidence", "الدليل")) if t.get(key))
    return (f'<article class="task{" dropped" if t["status"] == "dropped" else ""}">'
            f'<p class="muted"><bdi>{esc(t["id"])}</bdi> · {" · ".join(esc(x) for x in tags if x)}</p>'
            f'<p>{esc(t["title"])}</p>{extra}{detail}</article>')


def render_tasks(tasks: list[dict], cards: list[dict], title: str, generated: str) -> str:
    """tasks.html: the agent's tasks and PLAN.md's batches as columns, with each task's history."""
    esc = html.escape
    columns = []
    for status in board.STATUSES[:-1]:  # dropped tasks are shown, struck through, among the done ones
        items = [t for t in [*cards, *tasks] if t["status"] in ((status, "dropped") if status == "done" else (status,))]
        shown = list(reversed(items))[:30] if status == "done" else items
        body = "".join(task_card(t) for t in shown) or '<p class="muted">لا شيء</p>'
        columns.append(f'<section class="col {status}"><h2>{board.LABELS[status]} '
                       f'<span class="muted">({len(items)})</span></h2>{body}</section>')
    return "".join([
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="refresh" content="15">',
        f"<title>{esc(title)} — لوحة المهام</title><style>{HTML_STYLE}{TASKS_STYLE}</style></head><body>",
        f'<main class="wide"><h1>{esc(title)} — لوحة المهام</h1>',
        '<p class="muted">ما ينوي الوكيل فعله، وما يعمل عليه، وما ينتظرك، وما أنجزه بدليل. تُولَّد آليًا وتتحدث كل 15 '
        'ثانية. لا تُغلق مرحلة وفيها مهمة مفتوحة. اضغط «المراحل» لترى مسار أي مهمة. '
        f'<a href="{DASHBOARD.name}">لوحة التعريب</a>'
        + (f" — آخر تغيير: {esc(generated)}" if generated else "") + "</p>",
        "".join(f'<div class="card wait"><p><b>بانتظارك:</b> {esc(t["title"])}</p>'
                f'<p class="muted">{esc(t.get("reason", ""))}</p></div>' for t in tasks if t["status"] == "waiting"),
        f'<div class="board">{"".join(columns)}</div></main></body></html>\n',
    ])


TASKS_STYLE = """
main.wide{max-width:1400px}.board{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;
margin-top:12px;align-items:start}.col{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}
.col h2{margin:0 0 8px;font-size:1rem}.task{border:1px solid var(--line);border-radius:10px;padding:8px 10px;
margin-bottom:8px;background:var(--bg)}.task p{margin:2px 0}.task.dropped p:not(.muted){text-decoration:line-through}
.col.waiting{border-color:#c0392b}.col.doing{border-color:var(--fill)}details{font-size:.85rem}
"""


def render_dashboard(groups: dict, qa: dict, generated: str, plan_text: str, state: dict, checks, title: str,
                     problems: dict | None = None, quality: dict | None = None, lessons: int = 0,
                     tasks_html: str = "", probe: str = "") -> str:
    esc = html.escape
    return "".join([
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="refresh" content="15">',
        f"<title>{esc(title)} — لوحة التعريب</title><style>{HTML_STYLE}</style></head><body><main>",
        f"<h1>{esc(title)}</h1>",
        f'<p class="muted">تُولَّد آليًا من ملفات هذا المجلد وتتحدث كل 15 ثانية. '
        + (f"آخر تغيير في بيانات المشروع: {esc(generated)}. " if generated
           else "لم يبدأ العمل بعد: افتح هذا المجلد مشروعًا في Claude Code أو Codex وقل «عرّب اللعبة». ")
        + f'{esc(MEANING_NOTE)} <a href="{MAP_PAGE}">خريطة القالب</a> تشرح ما تفعله أنت وكيف يعمل النظام.</p>',
        f'<nav class="pages"><a href="{TASKS_PAGE.name}">لوحة المهام</a><a href="{MAP_PAGE}">خريطة القالب</a></nav>',
        tasks_html, "<h2>المرحلة</h2>", phase_html(state, checks), probe, experiences_html(state, lessons),
        "<h2>التقدم</h2>", progress_html(groups, qa, problems),
        quality_html(quality),
        '<h2>الخطة والملاحظات</h2><div class="card plan">', markdown_html(plan_text), "</div>",
        "</main></body></html>\n",
    ])


def write_dashboard(units_dir: Path = units.UNITS_DIR, qa_file: Path = QA_MATRIX, out: Path = DASHBOARD,
                    project=None, plan_file: Path = PLAN_FILE) -> Path:
    """Regenerate the dashboard from units, state, the LQA matrix, and PLAN.md. Costs no model tokens."""
    project = project or pipeline.Project(units_dir=units_dir, qa_file=qa_file)
    all_units = units.all_units(units.load(units_dir, units.Report()))
    groups = compute(all_units)
    try:
        found, overrides = find_problems(all_units)
        problems = tools.problem_counts(found, overrides)
    except Exception:  # the page must render even with a broken glossary
        problems = {}
    state = project.state()
    try:
        _, checks = pipeline.evaluate(project)
    except Exception as exc:  # the page must still render with a broken setting
        checks = [(False, f"تعذر تقييم المرحلة: {exc}")]
    try:
        title = project.settings().get("game", {}).get("name") or ""
        title = title if pipeline.filled(title) else "مشروع التعريب"
    except Exception:
        title = "مشروع التعريب"
    plan_text = plan_file.read_text(encoding="utf-8") if plan_file.is_file() else ""
    unit_files = units.unit_paths(units_dir) if Path(units_dir).exists() else []
    task_file = board.tasks_file(project.state_file)
    data_files = [*unit_files, *(p for p in (project.state_file, task_file, plan_file, qa_file) if p.is_file())]
    # The time of the newest project data, not of this render, so an unchanged project gives the same page.
    changed = (datetime.fromtimestamp(max(p.stat().st_mtime for p in data_files)).strftime("%Y-%m-%d %H:%M:%S")
               if unit_files or project.state_file.is_file() or task_file.is_file() else "")
    finding_files = sorted((ROOT / "work" / "proofreading").glob("*.jsonl")) if units_dir == units.UNITS_DIR else []
    quality = None
    if finding_files:
        findings, _ = read_findings(finding_files)
        covered = [u for u in all_units if u.get("batch") in {f.stem for f in finding_files}]
        quality = mqm_score([f for _, f in findings], covered) if covered else None
    lessons = len(experiences.load_lessons()) if units_dir == units.UNITS_DIR else 0
    tasks, cards = board.load(project.state_file), board.plan_batch_cards(plan_file)
    tasks_out = out.with_name(TASKS_PAGE.name)
    probe_file = project.root / "work" / "probe" / "last.json"
    probe = json.loads(probe_file.read_text(encoding="utf-8")) if probe_file.is_file() else None
    page = render_dashboard(groups, qa_cases(qa_file), changed, plan_text, state, checks, str(title), problems,
                            quality, lessons, tasks_summary_html(tasks, cards, tasks_out.name), probe_html(probe))
    out.parent.mkdir(parents=True, exist_ok=True)
    tasks_out.write_text(render_tasks(tasks, cards, str(title), changed), encoding="utf-8", newline="\n")
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


# Everything the two pages are built from. One check after every loc.py command, in the Claude Code hook
# after every tool, and in loc.py watch: no command has to remember to refresh the pages.
PAGE_SOURCES = ("units/**/*.jsonl", "state/pipeline.json", "state/tasks.json", "PLAN.md", "qa/LQA_MATRIX.csv",
                "PROJECT.yaml", "glossary.yaml", "work/proofreading/*.jsonl", "work/experiences.jsonl",
                "work/probe/last.json")


def newest_source(root: Path = ROOT) -> float:
    return max((p.stat().st_mtime for pattern in PAGE_SOURCES for p in root.glob(pattern) if p.is_file()),
               default=0.0)


def refresh_if_stale(force: bool = False) -> bool:
    """Rebuild dashboard.html and tasks.html when any project source is newer than them (the real project only)."""
    pages = (DASHBOARD, TASKS_PAGE)
    try:
        if force or not all(p.is_file() for p in pages) or newest_source() > min(p.stat().st_mtime for p in pages):
            write_dashboard()
            return True
    except Exception as exc:  # never fail the real command because of the page
        print(f"WARN  dashboard not refreshed: {exc}", file=sys.stderr)
    return False


# ----- commands -------------------------------------------------------------

def load_checked(path: Path):
    report = units.Report()
    files = units.load(path, report)
    units.validate(files, token_profile(), report)
    return files, report


LINE_LIMIT = 20


def problem_kind(line: str) -> str:
    """The message without its file, line, and unit id, so repeated problems group together."""
    text = re.sub(r"^.*?\]: ", "", line)
    text = re.sub(r"^\S+:\d+: ", "", text)
    return re.split(r"[(:{=]", text, maxsplit=1)[0].strip()


def print_report(report, limit: int = LINE_LIMIT) -> None:
    """Print at most `limit` lines per level, then counts by kind: output stays small for any project size."""
    for level, lines in (("ERROR", report.errors), ("WARN ", report.warnings)):
        for line in lines[:limit]:
            print(f"{level} {line}")
        if len(lines) > limit:
            kinds = Counter(problem_kind(line) for line in lines)
            print(f"{level} ... {len(lines) - limit} more; by kind: "
                  + "; ".join(f"{count}x {kind}" for kind, count in kinds.most_common(8)))


def cmd_validate(args) -> int:
    files, report = load_checked(args.path)
    print_report(report, args.limit)
    found, overrides = find_problems(units.all_units(files))
    counts = tools.problem_counts(found, overrides)
    if counts:
        print("PROBLEMS: " + " ".join(f"{code}={n}" for code, n in counts.items())
              + "  (list them: loc.py search --problem <code>)")
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


def project_glossary() -> dict:
    path = ROOT / "glossary.yaml"
    return load_glossary(path) if path.is_file() else {}


def project_qa() -> tuple[str, dict]:
    """The digit policy and problem-level overrides from PROJECT.yaml."""
    try:
        import yaml
        settings = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        return "western", {}
    return settings.get("game", {}).get("digits") or "western", (settings.get("qa") or {}).get("levels") or {}


def find_problems(all_units: list[dict]) -> tuple[dict, dict]:
    """(problem codes per unit id, level overrides) with every project setting applied."""
    digits, overrides = project_qa()
    return tools.unit_problems(all_units, project_glossary(), token_profile(), digits), overrides


def cmd_search(args) -> int:
    report = units.Report()
    if args.path_option:
        args.path = args.path_option
    if not args.query and not args.problem:
        print("ERROR give a text query, --problem <code>, or both")
        return 2
    if args.problem and args.problem not in tools.PROBLEM_CODES:
        print("ERROR unknown problem code. Codes: " + ", ".join(tools.PROBLEM_CODES))
        return 2
    all_units = units.all_units(units.load(args.path, report))
    flagged = find_problems(all_units)[0] if args.problem else {}
    needle = (args.query or "").casefold()
    hits = 0
    for unit in all_units:
        if args.kind and unit.get("kind") != args.kind:
            continue
        if args.problem and args.problem not in flagged.get(unit.get("id"), []):
            continue
        fields = {"source": [unit.get("source", "")], "target": [unit.get("target", "")],
                  "both": [unit.get("source", ""), unit.get("target", "")]}[args.field]
        if any(needle in (value or "").casefold() for value in fields):
            hits += 1
            if hits > args.limit:
                continue
            if args.ids_only:
                print(unit.get("id"))
                continue
            where = unit.get("asset") or unit.get("file")
            print(f"{unit.get('id')}\t{unit.get('kind')}\t{unit.get('status')}\t{where}\t"
                  f"{unit.get('source', '')}\t{unit.get('target', '')}")
    print_report(report)
    shown = f" SHOWN={args.limit}" if hits > args.limit else ""
    print(f"MATCHES={hits}{shown}")
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
    if args.self_review and (args.status != "proofread" or review_mode() != "self"):
        print("ERROR --self-review is only for status proofread when PROJECT.yaml workflow.review_mode is self")
        return 2
    if args.status == "proofread" and not args.by and not args.self_review:
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
            unit["proofread_by"] = (units.SELF_REVIEW + str(unit.get("translated_by") or "")) if args.self_review else args.by
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
              "punctuation", "style", "voice", "length", "numbers", "dialect", "culture", "wordplay")
# MQM top-level dimension of each category, and the common MQM severity weights.
MQM_DIMENSION = {
    "meaning": "accuracy", "omission": "accuracy", "context": "accuracy", "numbers": "accuracy",
    "terminology": "terminology", "grammar": "linguistic", "spelling": "linguistic", "punctuation": "linguistic",
    "style": "style", "voice": "style", "dialect": "style", "culture": "audience", "wordplay": "audience",
    "length": "design",
}
SEVERITY_WEIGHT = {"minor": 1, "major": 5, "critical": 10, "blocker": 25}
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


def mqm_score(findings: list[dict], batch_units: list[dict]) -> dict:
    """Flag rate and MQM penalty points per 1,000 source words for one or more proofread batches."""
    counted = [f for f in findings if f.get("resolution") != "rejected" and f.get("severity") in SEVERITY_WEIGHT]
    batch_ids = {u["id"] for u in batch_units}
    flagged = {f["id"] for f in counted if f.get("id") in batch_ids}
    words = sum(len((u.get("source") or "").split()) for u in batch_units)
    penalty = sum(SEVERITY_WEIGHT[f["severity"]] for f in counted if f.get("id") in batch_ids)
    dimensions: dict[str, int] = {}
    for f in counted:
        dimension = MQM_DIMENSION.get(f.get("category"), "other")
        dimensions[dimension] = dimensions.get(dimension, 0) + 1
    return {
        "units": len(batch_units), "flagged": len(flagged),
        "flag_rate": round(100 * len(flagged) / len(batch_units)) if batch_units else None,
        "words": words, "penalty": penalty,
        "per_1000_words": round(1000 * penalty / words, 1) if words else None,
        "dimensions": dimensions,
    }


def read_findings(files) -> tuple[list[tuple[str, dict]], list[str]]:
    findings, errors = [], []
    for file in files:
        for number, line in enumerate(Path(file).read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                findings.append((f"{file}:{number}", json.loads(line)))
            except json.JSONDecodeError as exc:
                errors.append(f"{file}:{number}: invalid JSON: {exc.msg}")
    return findings, errors


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
    return pipeline.Project(project_file=args.project, units_dir=args.units, state_file=args.state, qa_file=args.qa,
                            plan_file=args.plan)


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
    order = ("doing", "waiting", "verify", "next", "later")
    open_tasks = sorted((t for t in board.load(project.state_file) if t["status"] in board.OPEN),
                        key=lambda t: (t["phase"] != phase, order.index(t["status"])))
    for task in open_tasks[:LINE_LIMIT]:
        print(f"TASK {task['id']} [{task['status']}] ({task['phase']}) {task['title']}")
    if open_tasks:
        print(f"TASKS_OPEN={len(open_tasks)} — resume doing/waiting first; loc.py task list")
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


def cmd_no_images(args) -> int:
    try:
        pipeline.no_images(project_of(args), args.reason)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print("NO_IMAGES_RECORDED")
    return 0


def cmd_pilot_ok(args) -> int:
    try:
        pipeline.confirm_pilot(project_of(args), args.note)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print("PILOT_CONFIRMED")
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
    every = units.all_units(units.load(args.path, report))
    by_id = {u.get("id"): u for u in every}
    findings, read_errors = read_findings(args.files)
    report.errors += read_errors
    errors, summary = check_findings(findings, by_id)
    report.errors += errors
    print_report(report)
    for key in ("severity", "category", "resolution"):
        counts = ", ".join(f"{k}={v}" for k, v in summary[key].items() if v)
        print(f"{key.upper()}: {counts or 'none'}")
    print(f"OPEN_DECISIONS={len(summary['open'])} {' '.join(summary['open'])}".rstrip())
    batches = {args.batch} if args.batch else {Path(f).stem for f in args.files}
    batch_units = [u for u in every if u.get("batch") in batches]
    if batch_units:
        score = mqm_score([f for _, f in findings], batch_units)
        print(f"MQM: flagged {score['flagged']}/{score['units']} units ({score['flag_rate']}%), "
              f"penalty {score['penalty']} = {score['per_1000_words']} per 1000 words; "
              + " ".join(f"{d}={n}" for d, n in sorted(score["dimensions"].items())))
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
    if args.format == "html":
        out = write_dashboard(args.path, args.qa, args.out or DASHBOARD)
        print(f"DASHBOARD={out}")
        return 0
    text = render_md(groups, qa, generated)
    out = args.out or DEFAULT_OUT[args.format]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"PROGRESS_REPORT={out}")
    return 0


def cmd_update(args) -> int:
    """Re-extract after a game update and merge into the existing units file."""
    adapter = adapter_base.load_adapter(args.adapter, args.game, parse_options(args.option))
    report = units.Report()
    files = units.load(args.path, report)
    if report.errors or len(files) != 1:
        print_report(report)
        print("ERROR --path must name one valid units file")
        return 1
    merged, summary = tools.merge_update(files[0].units, adapter.extract(), set(adapter.inventory()))
    print(f"UNCHANGED={summary['unchanged']} CHANGED={len(summary['changed'])} ADDED={len(summary['added'])} "
          f"REMOVED={len(summary['removed'])} KEPT_OTHER={summary['kept_other']}")
    for label in ("changed", "added", "removed"):
        if summary[label]:
            print(f"{label.upper()}: {' '.join(summary[label][:LINE_LIMIT])}"
                  + (" ..." if len(summary[label]) > LINE_LIMIT else ""))
    if args.dry_run:
        print("DRY_RUN: nothing written")
        return 0
    if summary["removed"]:
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        removed = ROOT / "work" / "updates" / f"removed-{stamp}.jsonl"
        removed.parent.mkdir(parents=True, exist_ok=True)
        gone = set(summary["removed"])
        units.write(units.UnitFile(removed, [u for u in files[0].units if u["id"] in gone]))
        print(f"REMOVED_UNITS_SAVED={removed}")
    units.write(units.UnitFile(files[0].path, merged))
    return 0


def cmd_tmx(args) -> int:
    files, report = load_checked(args.path)
    if report.errors:
        print_report(report)
        print("NOT_WRITTEN: fix unit errors first")
        return 1
    game = ""
    try:
        game = pipeline.Project().settings().get("game", {}).get("name") or ""
    except Exception:
        pass
    tree = tools.tmx(units.all_units(files), args.min_status, args.source_lang, args.target_lang, game)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.out, encoding="utf-8", xml_declaration=True)
    print(f"TMX_UNITS={len(tree.getroot().find('body'))} OUT={args.out}")
    return 0


def cmd_estimate(args) -> int:
    all_units = units.all_units(units.load(args.path, units.Report()))
    print(json.dumps(tools.estimate(all_units, args.batch_tokens, args.overhead, args.output_ratio),
                     ensure_ascii=False))
    return 0


def cmd_pseudo(args) -> int:
    game, out = Path(args.game).resolve(), Path(args.out).resolve()
    if out == game or out.is_relative_to(game):
        print("ERROR --out must be outside the game folder")
        return 2
    adapter = adapter_base.load_adapter(args.adapter, game, parse_options(args.option))
    out.mkdir(parents=True, exist_ok=True)
    written = adapter.rebuild(tools.pseudo_targets(adapter.extract()), out)
    print(f"PSEUDO_FILES={len(written)} OUT={out}")
    print("Install the files on a copy of the game to check Arabic rendering, RTL, and line length before translating.")
    return 0


def load_glossary(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def cmd_apply(args) -> int:
    """Write a translated batch only if its ids match the requested units exactly."""
    try:
        given = tools.parse_batch_output(args.answer.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"ERROR cannot read the batch answer: {exc}")
        return 2
    report = units.Report()
    files = units.load(args.path, report)
    if report.errors:
        print_report(report)
        return 1
    ids = set(args.ids or [])
    selected = [u for u in units.all_units(files)
                if (u.get("id") in ids or (args.batch and u.get("batch") == args.batch))
                and units.decision(u) != "keep"]
    expected = [u["id"] for u in selected]
    if not expected:
        print("ERROR no units selected; give --batch or --ids")
        return 2
    gaps = tools.alignment(expected, given)
    if any(gaps.values()):
        for label, values in gaps.items():
            if values:
                print(f"ERROR {label.upper()} ({len(values)}): {' '.join(values[:LINE_LIMIT])}"
                      + (" ..." if len(values) > LINE_LIMIT else ""))
        print(f"NOT_WRITTEN: the answer must contain exactly these {len(expected)} ids, each with a non-empty "
              "target, and nothing else. Re-run the whole batch; never pad or guess missing lines.")
        return 1
    locked = [u["id"] for u in selected
              if units.stage(u) >= units.STATUSES.index("proofread") and u.get("target") != given[u["id"]]]
    if locked:
        state = pipeline.Project(state_file=args.state).state()
        fix = next((f for f in pipeline.open_fixes(state) if f["id"] == args.fix), None)
        outside = [i for i in locked if not fix or i not in fix["ids"]]
        if outside:
            print(f"ERROR LOCKED ({len(outside)}): proofread text changes only through an open fix listing it: "
                  + " ".join(outside[:LINE_LIMIT]))
            print('NOT_WRITTEN: run loc.py fix open --title ... --ids <ids>, then apply with --fix F-xxx')
            return 1
    before = set(units.validate(files, token_profile()).errors)
    for unit in selected:
        if unit.get("target") == given[unit["id"]] and units.stage(unit) >= units.STATUSES.index("translated"):
            continue  # unchanged text keeps its status and any proofreading
        unit["target"] = given[unit["id"]]
        unit["status"] = "translated"
        unit["translated_by"] = args.by
        unit.pop("proofread_by", None)
        unit.pop("proofread_hash", None)
    introduced = [e for e in units.validate(files, token_profile()).errors if e not in before]
    if introduced:
        rejected = units.Report()
        rejected.errors = introduced
        print_report(rejected)
        print("NOT_WRITTEN: fix these units in the answer and apply the whole batch again")
        return 1
    for unit_file in files:
        units.write(unit_file)
    found, overrides = find_problems(selected)
    counts = tools.problem_counts(found, overrides)
    print(f"APPLIED={len(selected)} STATUS=translated BY={args.by}"
          + (" WARNINGS: " + " ".join(f"{c}={n}" for c, n in counts.items()) if counts else ""))
    return 0


def cmd_brief(args) -> int:
    """Write a self-contained brief for one batch: stable rules first, then characters and terms, then units."""
    import hashlib
    import yaml
    files = units.load(args.path, units.Report())
    every = units.all_units(files)
    ids = set(args.ids or [])
    batch_units = [u for u in every if u.get("id") in ids or (args.batch and u.get("batch") == args.batch)]
    if not batch_units:
        print("ERROR no units selected; give --batch or --ids")
        return 2
    label = args.batch or "selection"
    self_review = args.role == "translator" and review_mode() == "self"
    brief_module = _load("make_subagent_brief")
    policy, roles = brief_module.load_policy(), brief_module.load_roles()
    role = roles[args.role]
    constraints = brief_module.build_brief(
        policy, role[0]["route"], f"{'Translate' if args.role == 'translator' else 'Proofread'} the batch in layer 3",
        "the unit ids in layer 3",
        "write", "Follow the Output section.", args.runtime, role)
    settings = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8")) or {}
    glossary = project_glossary()
    found, _ = find_problems(batch_units) if args.role == "proofreader" else ({}, {})
    file_units = [u for u in every if u.get("file") == batch_units[0].get("file")]
    text = brief_tools.build(args.role, label, batch_units, file_units, constraints, settings.get("game") or {},
                             brief_tools.characters(ROOT / "loc-kit" / "CHARACTERS.yaml"), glossary,
                             tools.glossary_entries(glossary), found, args.continuity,
                             brief_tools.style_text("proofreader" if self_review else args.role, ROOT), self_review)
    out = args.out or ROOT / "work" / "batches" / f"{label}.{args.role}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    layer_one = text.split(brief_tools.LAYER_MARKS[1])[0]
    print(f"BRIEF={out} UNITS={len(batch_units)} ESTIMATED_TOKENS={round(len(text) / 3.5)} "
          f"CACHEABLE_PREFIX_SHA={hashlib.sha256(layer_one.encode('utf-8')).hexdigest()[:12]}")
    for warning in batch_limits(batch_units, settings.get("workflow") or {}):
        print(f"WARNING {warning}")
    return 0


def batch_limits(batch_units: list[dict], flow: dict) -> list[str]:
    """PROJECT.yaml batch ceilings a brief exceeds; an oversized batch should be split before delegation."""
    out = []
    strings, tokens = flow.get("max_batch_strings"), flow.get("max_batch_source_tokens")
    if isinstance(strings, int) and len(batch_units) > strings:
        out.append(f"batch has {len(batch_units)} units, over max_batch_strings={strings}; split it")
    source = sum(tools.estimate_text(u.get("source") or "") for u in batch_units)
    if isinstance(tokens, int) and source > tokens:
        out.append(f"batch source is ~{source} tokens, over max_batch_source_tokens={tokens}; split it")
    return out


def target_snapshot(all_units: list[dict], exclude: set[str]) -> dict[str, str]:
    return {u["id"]: units.source_hash(u.get("target") or "") for u in all_units if u.get("id") not in exclude}


def cmd_fix(args) -> int:
    """A light lane for small reported problems: open (assess), fix through apply, close (verify)."""
    project = pipeline.Project(state_file=args.state)
    if args.fix_command == "list":
        fixes = project.state().get("fixes", [])
        for fix in fixes:
            print(f"{fix['id']} [{fix['status']}{'/' + fix['verdict'] if fix.get('verdict') else ''}] "
                  f"{fix['title']} — ids: {' '.join(fix['ids'][:LINE_LIMIT])}")
        print(f"FIXES={len(fixes)} OPEN={len(pipeline.open_fixes(project.state()))}")
        return 0
    all_units = units.all_units(units.load(args.path, units.Report()))
    if args.fix_command == "open":
        known = {u["id"] for u in all_units}
        unknown = [i for i in args.ids if i not in known]
        if unknown:
            print(f"ERROR unknown unit ids: {' '.join(unknown[:LINE_LIMIT])}")
            return 2
        ident = pipeline.open_fix(project, args.title, args.current, args.expected, args.unchanged, args.ids,
                                  target_snapshot(all_units, set(args.ids)))
        print(f"FIX_OPENED={ident} — change the listed units with loc.py apply --fix {ident}, "
              f"have them proofread again, then loc.py fix close {ident} --verdict verified --evidence ...")
        return 0
    fixed = next((f for f in project.state().get("fixes", []) if f["id"] == args.id), None)
    exclude = set(fixed["ids"]) if fixed else set()
    problems = pipeline.close_fix(project, args.id, args.verdict, args.evidence or "",
                                  target_snapshot(all_units, exclude), {u["id"]: units.stage(u) for u in all_units})
    for problem in problems:
        print(f"ERROR {problem}")
    if problems:
        print("NOT_CLOSED: fix the above, or close honestly as partial or failed and open a follow-up")
        return 1
    print(f"FIX_CLOSED={args.id} VERDICT={args.verdict}")
    return 0


def cmd_terms(args) -> int:
    """Check approved glossary terms in translated units, or record a deliberate exception."""
    report = units.Report()
    files = units.load(args.path, report)
    if args.allow:
        ident, term = args.allow
        for unit_file in files:
            for unit in unit_file.units:
                if unit.get("id") == ident:
                    unit["term_exceptions"] = sorted(set(unit.get("term_exceptions") or []) | {term})
                    units.write(unit_file)
                    print(f"EXCEPTION_RECORDED {ident} {term}")
                    return 0
        print(f"ERROR unknown unit id {ident!r}")
        return 2
    glossary = load_glossary(args.glossary)
    all_units = units.all_units(files)
    problems = tools.check_terms(all_units, glossary)
    problems += [(u["id"], form, f"forbidden; use {(glossary.get('forbidden') or {})[form]}")
                 for u in all_units if u.get("target") and units.decision(u) == "translate"
                 for form in tools.forbidden_forms(u, glossary)]
    for ident, term, expected in problems[:args.limit]:
        print(f"WARN  [{ident}] {term!r} should read: {expected}")
    if len(problems) > args.limit:
        counts = Counter(term for _, term, _ in problems)
        print(f"WARN  ... {len(problems) - args.limit} more; by term: "
              + "; ".join(f"{n}x {t}" for t, n in counts.most_common(8)))
    print(f"TERM_PROBLEMS={len(problems)}")
    if problems:
        print("Fix the target, or if the variant is correct here: loc.py terms --allow <id> <term>")
    return 1 if problems else 0


def cmd_lesson(args) -> int:
    """Record what this project taught us for the template's developer; packed at handoff."""
    if args.lesson_command == "list":
        lessons = experiences.load_lessons(args.path)
        for lesson in lessons:
            print(f"{lesson['id']} [{lesson['type']}] {lesson['what']}")
        print(f"LESSONS={len(lessons)}")
        return 0
    try:
        lesson = experiences.add_lesson(args.type, args.what, args.evidence, args.suggest or "", args.file or "",
                                        args.by or "", args.path)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    print(f"LESSON_RECORDED={lesson['id']}")
    return 0


def experience_facts(project, all_units: list[dict]) -> dict:
    """What the code knows about this project without asking the agent."""
    settings, state = project.settings(), project.state()
    flow, game = settings.get("workflow", {}), settings.get("game", {})
    changelog = ROOT / "CHANGELOG.md"
    template = next((line[3:].strip() for line in changelog.read_text(encoding="utf-8").splitlines()
                     if line.startswith("## ")), "") if changelog.is_file() else ""
    try:
        found, overrides = find_problems(all_units)
        problems = tools.problem_counts(found, overrides)
    except Exception:
        problems = {}
    group = compute(all_units)["all"] if all_units else {"total": 0}
    return {
        "template": template,
        "phase": state.get("phase"),
        "game": {"name": game.get("name"), "engine": flow.get("engine_profile"),
                 "adapter": Path(flow.get("adapter") or "").name, "token_profile": game.get("token_profile"),
                 "image_scope": flow.get("image_scope")},
        "setup": {key: flow.get(key) for key in ("runtime", "runtime_root", "subscription", "subagent_mode",
                                                 "subagent_concurrency", "review_mode")},
        "contract": state.get("contract"),
        "units": {"total": group.get("total", 0), "reached": group.get("reached", {}),
                  "keep": group.get("keep", 0), "review": group.get("review", 0)},
        "problems": problems,
        "fixes": [{"title": f["title"], "status": f["status"], "verdict": f.get("verdict"), "units": len(f["ids"])}
                  for f in state.get("fixes", [])],
        "reopened": [{"phase": e["phase"], "from": e.get("from"), "reason": e.get("reason"), "at": e.get("at")}
                     for e in state.get("history", []) if e.get("event") == "reopened"],
        "phases": [{"phase": e["phase"], "at": e.get("at")} for e in state.get("history", []) if e.get("event") == "passed"],
    }


def cmd_experiences(args) -> int:
    """Pack lessons, facts, and engine/adapter knowledge into experiences-<game>-<date>.zip for the developer."""
    project = project_of(args)
    settings = project.settings()
    flow, game = settings.get("workflow", {}), settings.get("game", {})
    all_units = units.all_units(units.load(args.units, units.Report()))
    files = {}
    engine = flow.get("engine_profile") or ""
    if engine and (ROOT / "engines" / f"{engine}.md").is_file():
        files[f"engines/{engine}.md"] = ROOT / "engines" / f"{engine}.md"
    if pipeline.filled(flow.get("adapter", "")) and project.resolve(flow["adapter"]).is_file():
        files[f"adapters/{Path(flow['adapter']).name}"] = project.resolve(flow["adapter"])
    registry = ROOT / "tools" / "project-scripts.json"
    for entry in (json.loads(registry.read_text(encoding="utf-8")).get("scripts", []) if registry.is_file() else []):
        if entry.get("reusable") is True and (ROOT / entry["path"]).is_file():
            files[f"scripts/{Path(entry['path']).name}"] = ROOT / entry["path"]
    name = game.get("name") if pipeline.filled(game.get("name")) else ROOT.name
    sanitizer = experiences.Sanitizer({"<GAME>": game.get("install_path") if pipeline.filled(game.get("install_path")) else "",
                                       "<PROJECT>": str(ROOT), "<HOME>": str(Path.home())})
    lessons = experiences.load_lessons(args.lessons)
    target = experiences.pack(lessons, experience_facts(project, all_units), files, args.out, str(name), sanitizer)
    pipeline.record_experiences(project, target, experiences.sha256(target), len(lessons))
    print(f"EXPERIENCES={target}")
    print(f"LESSONS={len(lessons)} FILES={len(files)}")
    print(experiences.send_message(target.name))
    return 0


def cmd_task(args) -> int:
    """The agent's task board: add what it will do, move it through the columns, defer, list."""
    project = project_of(args)
    current = project.state()["phase"]
    try:
        if args.task_command == "add":
            status = "later" if args.later else args.status
            ident = board.add(args.state, args.title, args.kind, args.phase or current, status, args.origin or "",
                              note=args.note or "")
            print(f"TASK_ADDED={ident} [{status}] ({args.phase or current})")
        elif args.task_command == "move":
            task = board.move(args.state, args.id, args.status, args.note or "", args.evidence or "", args.reason or "")
            print(f"TASK_MOVED={task['id']} [{task['status']}]")
        elif args.task_command == "defer":
            task = board.defer(args.state, args.id, args.to_phase, args.reason, pipeline.PHASES, current)
            print(f"TASK_DEFERRED={task['id']} -> {task['phase']}")
        else:
            tasks = board.load(args.state)
            shown = tasks if args.all else [t for t in tasks if t["status"] in board.OPEN]
            for task in shown:
                print(f"{task['id']} [{task['status']}] ({task['phase']}, {task['kind']}) {task['title']}"
                      + (f" — {task['reason']}" if task.get("reason") and task["status"] == "waiting" else ""))
            left = board.open_in_phase(args.state, current)
            print(f"TASKS={len(tasks)} OPEN={sum(t['status'] in board.OPEN for t in tasks)} "
                  f"OPEN_IN_{current.upper()}={len(left)}")
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2
    return 0


def cmd_watch(args) -> int:
    """Keep dashboard.html and tasks.html current while anything works on the project (Codex too)."""
    import time
    print(f"WATCHING every {args.interval}s; rebuilds the pages when a project file changes. Ctrl+C stops.")
    cycles = 0
    try:
        while args.cycles is None or cycles < args.cycles:
            if refresh_if_stale():
                print(f"REFRESHED {datetime.now().strftime('%H:%M:%S')}")
            cycles += 1
            if args.cycles is None or cycles < args.cycles:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_dashboard(args) -> int:
    out = write_dashboard(args.units, args.qa, args.out, project_of(args))
    print(f"DASHBOARD={out}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["probe"]:  # its own options live in scripts/game_probe.py
        code = _load("game_probe").main(argv[1:])
        refresh_if_stale()
        return code
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def with_path(p):
        p.add_argument("path", nargs="?", type=Path, default=units.UNITS_DIR)
        return p

    p = with_path(sub.add_parser("validate", help="check every unit; after each batch and edit, zero errors before integration"))
    p.add_argument("--limit", type=int, default=LINE_LIMIT, help="lines shown per level (counts cover all)")
    p.set_defaults(run=cmd_validate)
    with_path(sub.add_parser("normalize", help="fill hashes and key order; after resetting a changed unit to extracted")).set_defaults(run=cmd_normalize)

    p = sub.add_parser("search", help="find text, or units with a problem code (--problem), including image text")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--problem", help="only units with this problem code, e.g. latin_leak (see references/translation-units.md)")
    p.add_argument("--ids-only", action="store_true", help="print ids only, one per line, for mark --ids or a re-translation brief")
    p.add_argument("--path", dest="path_option", type=Path, help="units file or folder (use this with --problem and no query)")
    with_path(p)
    p.add_argument("--field", choices=("both", "source", "target"), default="both")
    p.add_argument("--kind", choices=units.KINDS)
    p.add_argument("--limit", type=int, default=50, help="matches printed (the count covers all)")
    p.set_defaults(run=cmd_search)

    p = sub.add_parser("mark", help="set the status of selected units: translator, proofreader, after install, after a playtest observation")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--status", required=True, choices=units.STATUSES)
    p.add_argument("--ids", nargs="+")
    p.add_argument("--batch")
    p.add_argument("--file")
    p.add_argument("--evidence", help="required for integrated (build) and tested (what was observed)")
    p.add_argument("--by", help="agent or person label for translated/proofread")
    p.add_argument("--force", action="store_true", help="allow moving a unit backward")
    p.add_argument("--self-review", action="store_true",
                   help="the translator marks its own reviewed batch proofread; only when review_mode is self")
    p.set_defaults(run=cmd_mark)

    p = sub.add_parser("extract", help="write units from a game through an adapter, once the adapter contract passes")
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--game", required=True, type=Path)
    p.add_argument("--out", type=Path, help="default units/<game folder name>.jsonl")
    p.add_argument("--option", action="append", default=[], help="adapter option key=value")
    p.add_argument("--force", action="store_true")
    p.set_defaults(run=cmd_extract)

    p = sub.add_parser("rebuild", help="build localized game files from proofread units into a folder outside the game")
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
        p.add_argument("--plan", type=Path, default=PLAN_FILE, help=argparse.SUPPRESS)
        return p

    with_project(sub.add_parser("next", help="show the phase, its blockers, and what to load; at session start or when unsure")).set_defaults(run=cmd_next)
    p = sub.add_parser("lesson", help="record what this project taught us (template bug, limit, lesson, engine, translation, tool, workflow)")
    lesson_sub = p.add_subparsers(dest="lesson_command", required=True)
    q = lesson_sub.add_parser("add", help="one lesson: what happened, its evidence, and the change it suggests")
    q.add_argument("--type", required=True, choices=sorted(experiences.LESSON_TYPES))
    q.add_argument("--what", required=True, help="what happened or what was learned")
    q.add_argument("--evidence", required=True, help="command, unit id, screenshot name, or test that shows it")
    q.add_argument("--suggest", help="the change to the template it suggests")
    q.add_argument("--file", help="the template file that change touches")
    q.add_argument("--by", help="role label of the agent recording it")
    q.add_argument("--path", type=Path, default=experiences.LESSONS_FILE, help=argparse.SUPPRESS)
    q = lesson_sub.add_parser("list", help="every recorded lesson")
    q.add_argument("--path", type=Path, default=experiences.LESSONS_FILE, help=argparse.SUPPRESS)
    p.set_defaults(run=cmd_lesson)
    p = with_project(sub.add_parser("experiences", help="handoff: pack lessons and facts into experiences-<game>-<date>.zip for the developer"))
    p.add_argument("--out", type=Path, default=ROOT, help="folder for the zip (default: this project's folder)")
    p.add_argument("--lessons", type=Path, default=experiences.LESSONS_FILE, help=argparse.SUPPRESS)
    p.set_defaults(run=cmd_experiences)
    p = with_project(sub.add_parser("dashboard", help="regenerate dashboard.html; in Codex after editing PLAN.md or the LQA matrix"))
    p.add_argument("--out", type=Path, default=DASHBOARD)
    p.set_defaults(run=cmd_dashboard)
    p = with_project(sub.add_parser("gate", help="advance the phase when every exit criterion passes; when next says ready"))
    p.add_argument("--check", action="store_true", help="evaluate without advancing or recording")
    p.set_defaults(run=cmd_gate)
    p = with_project(sub.add_parser("reopen", help="return to an earlier phase after a game update or a finding that sends work back"))
    p.add_argument("phase", choices=pipeline.PHASES)
    p.add_argument("--reason", required=True)
    p.set_defaults(run=cmd_reopen)
    p = with_project(sub.add_parser("pilot-ok", help="record the user's word that the pilot batch shows correct Arabic in the game"))
    p.add_argument("--note", required=True, help="the user's words, what they checked, and the build")
    p.set_defaults(run=cmd_pilot_ok)
    p = with_project(sub.add_parser("accept", help="record the user's acceptance of the playtest build; only on their explicit words"))
    p.add_argument("--note", required=True, help="the user's words, build, and date")
    p.set_defaults(run=cmd_accept)
    p = with_project(sub.add_parser("task", help="the agent's task board (tasks.html): add, move, defer, list; "
                                                 "a phase's gate needs its tasks done or deferred"))
    task_sub = p.add_subparsers(dest="task_command", required=True)
    q = task_sub.add_parser("add", help="a piece of work worth a line: a batch step, fix, question, investigation, tool")
    q.add_argument("title")
    q.add_argument("--kind", choices=board.KINDS, default="other")
    q.add_argument("--status", choices=board.OPEN, default="next")
    q.add_argument("--later", action="store_true", help="for later in this phase (same as --status later)")
    q.add_argument("--phase", choices=pipeline.PHASES, help="default: the current phase")
    q.add_argument("--origin", help="what created it: the user's request, a finding, a failed gate")
    q.add_argument("--note")
    q = task_sub.add_parser("move", help="next, doing, waiting (--reason), verify, done (--evidence), dropped (--reason)")
    q.add_argument("id")
    q.add_argument("status", choices=board.STATUSES)
    q.add_argument("--evidence", help="required for done: command output, file, verdict")
    q.add_argument("--reason", help="required for waiting (the question) and dropped (why)")
    q.add_argument("--note")
    q = task_sub.add_parser("defer", help="hand an open task to a later phase, with the reason")
    q.add_argument("id")
    q.add_argument("--to-phase", required=True, choices=pipeline.PHASES)
    q.add_argument("--reason", required=True)
    q = task_sub.add_parser("list", help="open tasks (--all: with done and dropped)")
    q.add_argument("--all", action="store_true")
    p.set_defaults(run=cmd_task)
    p = sub.add_parser("watch", help="rebuild dashboard.html and tasks.html whenever a project file changes")
    p.add_argument("--interval", type=float, default=3)
    p.add_argument("--cycles", type=int, help=argparse.SUPPRESS)
    p.set_defaults(run=cmd_watch)
    sub.add_parser("probe", add_help=False,
                   help="engine, fonts and their Arabic, a font preview, and the game's logs, without playing (scripts/game_probe.py)")

    p = with_project(sub.add_parser("no-images", help="with images in scope, record that the game has no baked text images, and why"))
    p.add_argument("--reason", required=True, help="what was searched (folders, archives, formats)")
    p.set_defaults(run=cmd_no_images)

    p = sub.add_parser("apply", help="write a translator's batch answer (JSON keyed by unit id) only if every id matches")
    p.add_argument("answer", type=Path, help="JSON {id: target} or [{id, target}]")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--batch")
    p.add_argument("--ids", nargs="+")
    p.add_argument("--by", required=True, help="translator role label, e.g. translator-1")
    p.add_argument("--fix", help="open fix id (F-001) that allows changing already proofread units")
    p.add_argument("--state", type=Path, default=ROOT / "state" / "pipeline.json", help=argparse.SUPPRESS)
    p.set_defaults(run=cmd_apply)

    p = sub.add_parser("brief", help="write a self-contained, cache-friendly brief for one batch, before sending it to an agent")
    p.add_argument("--batch")
    p.add_argument("--ids", nargs="+")
    p.add_argument("--role", choices=("translator", "proofreader"), default="translator")
    p.add_argument("--runtime", choices=("codex", "claude-code"), default="codex",
                   help="claude-code omits role text already in the subagent definition")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--out", type=Path)
    p.add_argument("--continuity", type=int, default=5, help="approved lines before the batch to include")
    p.set_defaults(run=cmd_brief)

    p = sub.add_parser("fix", help="small reported problem: open with current/expected/unchanged, apply --fix, close with a verdict")
    p.add_argument("--state", type=Path, default=ROOT / "state" / "pipeline.json", help=argparse.SUPPRESS)
    fix_sub = p.add_subparsers(dest="fix_command", required=True)
    q = fix_sub.add_parser("open", help="assess: record what is wrong, what is expected, and what must not change")
    q.add_argument("--title", required=True)
    q.add_argument("--current", required=True, help="what happens now")
    q.add_argument("--expected", required=True, help="what should happen")
    q.add_argument("--unchanged", required=True, help="what must stay as it is")
    q.add_argument("--ids", nargs="+", required=True, help="the units this fix may change")
    q.add_argument("--path", type=Path, default=units.UNITS_DIR)
    q = fix_sub.add_parser("close", help="verify: verified (checked, nothing else changed), partial, or failed")
    q.add_argument("id")
    q.add_argument("--verdict", required=True, choices=pipeline.FIX_VERDICTS)
    q.add_argument("--evidence", help="what was checked and where (required for verified)")
    q.add_argument("--path", type=Path, default=units.UNITS_DIR)
    fix_sub.add_parser("list", help="every fix with its status and verdict")
    p.set_defaults(run=cmd_fix)

    p = sub.add_parser("terms", help="check glossary terms in translated units; proofreader first step, gate needs zero")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--glossary", type=Path, default=ROOT / "glossary.yaml")
    p.add_argument("--limit", type=int, default=LINE_LIMIT)
    p.add_argument("--allow", nargs=2, metavar=("ID", "TERM"),
                   help="record that this unit deliberately uses another form of TERM")
    p.set_defaults(run=cmd_terms)

    p = sub.add_parser("update", help="merge a new game version into a units file (try --dry-run), then reopen")
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--game", required=True, type=Path)
    p.add_argument("--path", required=True, type=Path, help="the units file this adapter produced")
    p.add_argument("--option", action="append", default=[], help="adapter option key=value")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(run=cmd_update)

    p = sub.add_parser("tmx", help="export translated units to a TMX memory for later games; at release")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--min-status", choices=units.STATUSES[1:], default="proofread")
    p.add_argument("--source-lang", default="en")
    p.add_argument("--target-lang", default="ar")
    p.set_defaults(run=cmd_tmx)

    p = sub.add_parser("estimate", help="estimate tokens and batches; before the first bulk translation batch")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--batch-tokens", type=int, default=4000)
    p.add_argument("--overhead", type=int, default=1200)
    p.add_argument("--output-ratio", type=float, default=1.35)
    p.set_defaults(run=cmd_estimate)

    p = sub.add_parser("pseudo", help="build pseudo-Arabic files outside the game to test rendering before translating")
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--game", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--option", action="append", default=[], help="adapter option key=value")
    p.set_defaults(run=cmd_pseudo)

    p = sub.add_parser("findings", help="validate and summarize a proofreading findings file; proofreader, before marking proofread")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--batch", help="batch for the MQM score (default: each file's name, e.g. batch-003)")
    p.set_defaults(run=cmd_findings)

    p = sub.add_parser("progress", help="report progress as chat text, Markdown, or HTML; when the user asks")
    p.add_argument("--path", type=Path, default=units.UNITS_DIR)
    p.add_argument("--format", choices=("chat", "md", "html"), default="chat")
    p.add_argument("--out", type=Path)
    p.add_argument("--qa", type=Path, default=QA_MATRIX)
    p.set_defaults(run=cmd_progress)

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
    if args.command == "mark" and not (args.ids or args.batch or args.file):
        parser.error("mark needs --ids, --batch, or --file")
    code = args.run(args)
    if args.command not in ("dashboard", "watch"):
        refresh_if_stale(force=args.command == "next")  # next runs at every session start
    return code


if __name__ == "__main__":
    raise SystemExit(main())
