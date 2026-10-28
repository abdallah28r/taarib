"""texts.html and images.html: the game's text and images before and after localization (library for loc.py).

loc.py rebuilds both pages when their sources change, beside dashboard.html:

- texts.html: every unit's source and Arabic target, with status, batch, file,
  speaker, problem codes and proofreading findings; search, filters, and pages
  of 200 lines, rendered in the browser from data embedded in the page.
- images.html: each image's source, its current candidate with a comparison
  slider, and every version tried (work/images/attempts.json) with its verdict
  and reason. Images flagged as spoilers (`image_candidate.py spoiler`, or
  `"spoiler"` in a region manifest) are blurred until clicked, as
  PROJECT.yaml → reporting.spoilers says: flagged (default), all, or none.

Both pages hold the game's own text and art: they stay on this computer, are
ignored by git, and never enter a release or the experiences package.
Thumbnails go to work/images/preview/.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

STATUS_LABELS = {"extracted": "مستخرجة", "translated": "مترجمة", "proofread": "مدققة", "integrated": "مدمجة",
                 "tested": "مختبرة"}
METHOD_LABELS = {"typeset": "تنضيد بالخط", "codex-raw": "Codex خام", "composite": "Codex داخل الصندوق",
                 "codex": "Codex", "manual": "يدوي"}
DECISION_LABELS = {"translate": "تُعرَّب", "keep": "تبقى كما هي", "review": "تنتظر مراجعة"}
SPOILER_MODES = ("flagged", "all", "none")
PAGE_SIZE = 200
THUMB_WIDTH = 640


def _json_for_script(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _head(title: str, style: str, extra_style: str) -> str:
    esc = html.escape
    return ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{esc(title)}</title><style>{style}{extra_style}</style></head><body>")


def _nav(links: list[tuple[str, str]]) -> str:
    return '<nav class="pages">' + "".join(f'<a href="{h}">{html.escape(t)}</a>' for h, t in links) + "</nav>"


# ----- texts.html -------------------------------------------------------------

TEXTS_STYLE = """
main.wide{max-width:1400px}.filters{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.filters input,.filters select{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;
background:var(--card);color:var(--ink)}.filters input{flex:1 1 240px}
.unit{display:grid;grid-template-columns:1fr 1fr;gap:12px;background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:10px 12px;margin-bottom:8px}.unit .meta{grid-column:1/-1;color:var(--muted);font-size:.85rem}
.unit p{margin:0}.unit .lbl{display:block;font-size:.75rem;color:var(--muted)}
.unit .src{border-inline-start:1px solid var(--line);padding-inline-start:12px}
.unit .src p{direction:ltr;text-align:left;unicode-bidi:plaintext}.unit .tgt p{unicode-bidi:plaintext}
.unit .empty{color:var(--muted);font-style:italic}.notes{grid-column:1/-1;font-size:.9rem;margin:0;padding-inline-start:20px}
.notes li.open{color:#c0392b}.chip{display:inline-block;padding:0 8px;border-radius:999px;border:1px solid var(--line);
margin-inline-end:4px}.pager{display:flex;gap:8px;align-items:center;margin:12px 0}
.pager button{font:inherit;padding:4px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);
color:var(--ink)}@media (max-width:640px){.unit{grid-template-columns:1fr}.unit .src{border:0;padding:0}}
"""

TEXTS_SCRIPT = """
const D=DATA, $=s=>document.querySelector(s), S=STATUS, PAGE=%d;
const SEV={blocker:"مانع",critical:"حرج",major:"كبير",minor:"ثانوي"},
  RES={applied:"صُحّح",needs_decision:"ينتظر قرارًا",rejected:"سُحبت الملاحظة"};
let page=0;
function fill(id,values,label){const el=$(id);el.innerHTML=`<option value="">${label}</option>`+
  values.map(v=>`<option value="${esc(v)}">${esc(S[v]||v)}</option>`).join("");}
function esc(t){return String(t??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
const uniq=k=>[...new Set(D.map(u=>u[k]).flat().filter(Boolean))].sort();
fill("#status",Object.keys(S).filter(s=>D.some(u=>u.s===s)),"كل الحالات");
fill("#batch",uniq("b"),"كل الدفعات"); fill("#file",uniq("f"),"كل الملفات"); fill("#problem",uniq("p"),"كل المشكلات");
function matches(u){const q=$("#q").value.trim().toLowerCase();
  return (!q||[u.id,u.src,u.tgt,u.sp].some(v=>String(v||"").toLowerCase().includes(q)))
    &&(!$("#status").value||u.s===$("#status").value)&&(!$("#batch").value||u.b===$("#batch").value)
    &&(!$("#file").value||u.f===$("#file").value)&&(!$("#problem").value||(u.p||[]).includes($("#problem").value))
    &&(!$("#notes").checked||(u.n&&u.n.length)||(u.p&&u.p.length));}
function render(){const list=D.filter(matches), pages=Math.max(1,Math.ceil(list.length/PAGE));
  page=Math.min(page,pages-1);
  $("#count").textContent=`${list.length} من ${D.length} جملة — صفحة ${page+1} من ${pages}`;
  $("#list").innerHTML=list.slice(page*PAGE,(page+1)*PAGE).map(u=>`<article class="unit">
    <p class="meta"><bdi>${esc(u.id)}</bdi> · <span class="chip">${esc(S[u.s]||u.s)}</span>${u.b?` · ${esc(u.b)}`:""}
    · <bdi>${esc(u.f)}</bdi>${u.sp?` · المتحدث: <bdi>${esc(u.sp)}</bdi>`:""}
    ${(u.p||[]).map(p=>`<span class="chip">${esc(p)}</span>`).join("")}</p>
    <div class="tgt"><span class="lbl">الترجمة</span><p>${u.tgt?esc(u.tgt):'<span class="empty">لم تُترجم بعد</span>'}</p></div>
    <div class="src"><span class="lbl">الأصل</span><p>${esc(u.src)}</p></div>
    ${u.n&&u.n.length?`<ul class="notes">${u.n.map(n=>`<li class="${n.r==="needs_decision"?"open":""}">
      ${esc(SEV[n.sev]||n.sev)} · <bdi>${esc(n.cat)}</bdi> — ${esc(n.issue)}${n.r?` (${esc(RES[n.r]||n.r)})`:""}</li>`).join("")}</ul>`:""}
  </article>`).join("")||'<p class="muted">لا جمل تطابق التصفية.</p>';}
document.querySelectorAll(".filters input,.filters select").forEach(el=>el.addEventListener("input",()=>{page=0;render();}));
$("#prev").onclick=()=>{page=Math.max(0,page-1);render();scrollTo(0,0);};
$("#next").onclick=()=>{page++;render();scrollTo(0,0);};
render();
"""


def texts_data(all_units: list[dict], problems: dict[str, list[str]], findings: list[dict]) -> list[dict]:
    notes: dict[str, list[dict]] = {}
    for finding in findings:
        notes.setdefault(str(finding.get("id")), []).append(
            {"sev": finding.get("severity", ""), "cat": finding.get("category", ""), "issue": finding.get("issue", ""),
             "r": finding.get("resolution", "")})
    rows = []
    for unit in all_units:
        if unit.get("kind") != "text":
            continue
        row = {"id": unit.get("id"), "f": unit.get("file", ""), "s": unit.get("status", ""), "src": unit.get("source", ""),
               "tgt": unit.get("target", ""), "b": unit.get("batch", ""),
               "sp": (unit.get("context") or {}).get("speaker", "")}
        if problems.get(unit.get("id")):
            row["p"] = problems[unit["id"]]
        if notes.get(str(unit.get("id"))):
            row["n"] = notes[str(unit["id"])]
        rows.append({k: v for k, v in row.items() if v not in ("", None)})
    return rows


def render_texts(rows: list[dict], title: str, style: str, links: list[tuple[str, str]]) -> str:
    esc = html.escape
    return "".join([
        _head(f"{title} — النصوص قبل وبعد", style, TEXTS_STYLE),
        f'<main class="wide"><h1>{esc(title)} — النصوص قبل وبعد</h1>',
        '<p class="muted">كل جملة في اللعبة: ترجمتها بجانب أصلها، مع حالتها وملاحظات التدقيق. '
        "تُولَّد آليًا من units/ ولا تغادر هذا الجهاز. حدّث الصفحة لترى آخر تغيير.</p>",
        _nav(links),
        '<div class="filters"><input id="q" type="search" placeholder="ابحث في الأصل أو الترجمة أو المعرّف">'
        '<select id="status"></select><select id="batch"></select><select id="file"></select>'
        '<select id="problem"></select><label><input id="notes" type="checkbox"> فيها ملاحظات أو مشكلات</label></div>',
        '<p class="muted" id="count"></p><div id="list"></div>',
        '<div class="pager"><button id="prev">السابقة</button><button id="next">التالية</button></div></main>',
        f"<script>const DATA={_json_for_script(rows)};const STATUS={_json_for_script(STATUS_LABELS)};",
        TEXTS_SCRIPT % PAGE_SIZE, "</script></body></html>\n",
    ])


# ----- images.html ------------------------------------------------------------

IMAGES_STYLE = """
main.wide{max-width:1200px}.img{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;
margin-bottom:16px}.img h2{margin:0 0 4px;font-size:1rem}.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.pair figure,.versions figure{margin:0}.pair img,.versions img,.compare img{max-width:100%;display:block;border-radius:8px;
border:1px solid var(--line)}figcaption{font-size:.85rem;color:var(--muted);margin-top:4px}
.compare{max-width:100%;margin-top:10px}.compare .stage{position:relative;display:inline-block;max-width:100%}
.compare .stage img{max-width:100%}.compare .stage .top{position:absolute;inset:0;width:100%;height:100%}
.compare input{width:100%}.compare p{margin:0;font-size:.85rem;color:var(--muted)}
.versions{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-top:10px}
.versions .rejected .verdict{color:#c0392b}.versions .accepted .verdict{color:var(--fill)}
.none{display:flex;align-items:center;justify-content:center;min-height:120px;border:1px dashed var(--line);
border-radius:8px;color:var(--muted);text-align:center;padding:8px}
.regions{font-size:.9rem}.regions .src{unicode-bidi:plaintext}
.spoiler{position:relative;cursor:pointer}.spoiler.hidden>.content{filter:blur(22px);pointer-events:none;
user-select:none}.spoiler .veil{display:none}.spoiler.hidden .veil{display:flex;position:absolute;inset:0;
align-items:center;justify-content:center;text-align:center;padding:16px;font-weight:600;z-index:2}
.spoiler.hidden .veil span{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:8px 16px}
@media (max-width:640px){.pair{grid-template-columns:1fr}}
"""

IMAGES_SCRIPT = """
document.querySelectorAll(".spoiler").forEach(el=>el.addEventListener("click",()=>el.classList.remove("hidden")));
// The localized image covers the source from the right edge, as far as the slider says.
document.querySelectorAll(".compare").forEach(box=>{const top=box.querySelector(".top"),range=box.querySelector("input");
  const set=()=>{top.style.clipPath=`inset(0 0 0 ${100-range.value}%)`;};range.addEventListener("input",set);set();});
"""


def thumbnail(image: Path, root: Path) -> str | None:
    """A small PNG copy under work/images/preview/, reused while the image is unchanged; its page-relative path."""
    if not image.is_file():
        return None
    stat = image.stat()
    key = hashlib.sha1(f"{image.resolve()}|{stat.st_mtime_ns}|{stat.st_size}".encode("utf-8")).hexdigest()[:16]
    out = root / "work" / "images" / "preview" / f"{key}.png"
    if not out.is_file():
        try:
            from PIL import Image
            with Image.open(image) as im:
                im = im.convert("RGBA")
                if im.width > THUMB_WIDTH:
                    im = im.resize((THUMB_WIDTH, round(im.height * THUMB_WIDTH / im.width)))
                out.parent.mkdir(parents=True, exist_ok=True)
                im.save(out)
        except Exception:  # an unreadable image is shown as missing, never breaks the page
            return None
    return out.relative_to(root).as_posix()


def collect_images(root: Path, all_units: list[dict], game_root: Path | None) -> list[dict]:
    """One record per image: source, candidate, versions, regions, spoiler reason."""
    images: dict[str, dict] = {}

    def entry(name: str) -> dict:
        return images.setdefault(name, {"name": name, "source": None, "candidate": None, "versions": [],
                                        "regions": [], "spoiler": ""})

    folder = root / "work" / "images"
    for manifest in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if manifest.name == "attempts.json":
            continue
        try:
            rows = json.loads(manifest.read_text(encoding="utf-8")).get("images") or []
        except (ValueError, AttributeError):
            continue
        for row in rows:
            if not isinstance(row, dict) or not row.get("image"):
                continue
            item = entry(Path(str(row["image"])).name)
            if row.get("source"):
                path = Path(row["source"])
                item["source"] = path if path.is_absolute() else manifest.parent / path
            if row.get("candidate"):
                path = Path(row["candidate"])
                item["candidate"] = path if path.is_absolute() else manifest.parent / path
            item["spoiler"] = item["spoiler"] or str(row.get("spoiler") or "")
    log_file = folder / "attempts.json"
    log = json.loads(log_file.read_text(encoding="utf-8")) if log_file.is_file() else {}
    for record in log.values():
        item = entry(Path(str(record.get("image", "?"))).name)
        if record.get("source") and item["source"] is None:
            item["source"] = root / record["source"] if not Path(record["source"]).is_absolute() else Path(record["source"])
        item["versions"] = record.get("versions") or []
        item["spoiler"] = item["spoiler"] or str(record.get("spoiler") or "")
    for unit in all_units:
        if unit.get("kind") != "image":
            continue
        asset = Path(str(unit.get("asset") or unit.get("file") or "?"))
        item = entry(asset.name)
        item["regions"].append(unit)
        if item["source"] is None and game_root is not None:
            candidate = asset if asset.is_absolute() else game_root / asset
            if candidate.is_file():
                item["source"] = candidate
        if (unit.get("context") or {}).get("spoiler") and not item["spoiler"]:
            item["spoiler"] = str(unit["context"]["spoiler"])
    for item in images.values():
        if item["candidate"] is None:
            accepted = [v for v in item["versions"] if v.get("verdict") == "accepted"]
            if accepted:
                item["candidate"] = root / accepted[-1]["path"]
    return sorted(images.values(), key=lambda i: (not i["regions"], i["name"]))


def _figure(src: str | None, caption: str, missing: str = "لا صورة متاحة") -> str:
    body = (f'<img src="{html.escape(src)}" alt="" loading="lazy">' if src
            else f'<div class="none">{html.escape(missing)}</div>')
    return f"<figure>{body}<figcaption>{caption}</figcaption></figure>"


def render_images(items: list[dict], root: Path, mode: str, title: str, style: str,
                  links: list[tuple[str, str]], local_time) -> str:
    esc = html.escape
    mode = mode if mode in SPOILER_MODES else "flagged"
    cards = []
    for item in items:
        source = thumbnail(item["source"], root) if item["source"] else None
        candidate = thumbnail(item["candidate"], root) if item["candidate"] else None
        # As on texts.html: the localized version on the right, the source on the left.
        parts = [f'<div class="pair">{_figure(candidate, "المعرّبة", "لم تُعرَّب بعد")}'
                 f'{_figure(source, "الأصل", "الصورة الأصلية غير موجودة في مسار اللعبة")}</div>']
        if source and candidate:
            parts.append(f'<div class="compare"><div class="stage"><img src="{esc(source)}" alt="">'
                         f'<img class="top" src="{esc(candidate)}" alt=""></div>'
                         '<input type="range" min="0" max="100" value="50" aria-label="قارن بين الأصل والمعرّبة">'
                         '<p>حرّك الشريط: المعرّبة من اليمين، والأصل من اليسار.</p></div>')
        if item["regions"]:
            rows = "".join(f'<li><bdi class="src">{esc(str(u.get("source", "")))}</bdi> ← '
                           f'{esc(str(u.get("target") or "—"))} '
                           f'<span class="muted">({esc(STATUS_LABELS.get(u.get("status"), u.get("status", "")))}'
                           f'، {esc(DECISION_LABELS.get(u.get("decision") or "translate", str(u.get("decision"))))})'
                           f'</span></li>' for u in item["regions"])
            parts.append(f'<ul class="regions">{rows}</ul>')
        if item["versions"]:
            shown = []
            for version in item["versions"]:
                thumb = thumbnail(root / version["path"], root) if not Path(version["path"]).is_absolute() \
                    else thumbnail(Path(version["path"]), root)
                verdict = {"accepted": "مقبولة", "rejected": "مرفوضة"}.get(version.get("verdict"), "بلا حكم بعد")
                method = METHOD_LABELS.get(version.get("method", ""), version.get("method", ""))
                caption = (f'النسخة {version["n"]} · {esc(method)} · {local_time(version.get("at", ""))}<br>'
                           f'<b class="verdict">{verdict}</b>{esc(" — " + version["reason"]) if version.get("reason") else ""}')
                shown.append(f'<div class="{esc(version.get("verdict", ""))}">{_figure(thumb, caption)}</div>')
            parts.append(f'<p class="muted">كل النسخ المجرَّبة ({len(item["versions"])})</p>'
                         f'<div class="versions">{"".join(shown)}</div>')
        body = "".join(parts)
        hide = mode == "all" or (mode == "flagged" and item["spoiler"])
        if hide:
            body = (f'<div class="spoiler hidden"><div class="veil"><span>قد تحرق الأحداث — اضغط للإظهار</span></div>'
                    f'<div class="content">{body}'
                    + (f'<p class="muted">سبب الإخفاء: {esc(item["spoiler"])}</p>' if item["spoiler"] else "")
                    + "</div></div>")
        cards.append(f'<section class="img"><h2><bdi>{esc(item["name"])}</bdi></h2>{body}</section>')
    note = {"flagged": "الصور التي علّمها الوكيل بأنها تحرق الأحداث مخفية حتى تضغط عليها.",
            "all": "كل الصور مخفية حتى تضغط عليها (reporting.spoilers: all).",
            "none": "لا إخفاء (reporting.spoilers: none)."}[mode]
    return "".join([
        _head(f"{title} — الصور قبل وبعد", style, IMAGES_STYLE),
        f'<main class="wide"><h1>{esc(title)} — الصور قبل وبعد</h1>',
        f'<p class="muted">كل صورة فيها نص: الأصل، والمعرّبة مع شريط للمقارنة، وكل نسخة جُرّبت مع حكمها وسببه. {note} '
        "تبقى على هذا الجهاز ولا تُرفع.</p>",
        _nav(links),
        "".join(cards) or '<p class="muted">لا صور في نطاق التعريب بعد.</p>',
        f"</main><script>{IMAGES_SCRIPT}</script></body></html>\n",
    ])
