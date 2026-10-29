"""Experiences: what a game project taught us, packed for the template's developer.

During the work the agent records lessons with ``loc.py lesson add`` into
``work/experiences.jsonl``. At the handoff phase ``loc.py experiences`` packs
them, with facts the code collects itself and the engine/adapter knowledge, into
one ``experiences-<game>-<date>.zip`` that the user sends to the developer.

The package leaves the user's machine, so everything in it is sanitized: no game
text or game files, user-identifying paths become placeholders, secrets are
redacted, and every free-text field is capped. Nothing is ever sent
automatically; the user decides.
"""
from __future__ import annotations

import hashlib
from storage_core import digest
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS_FILE = ROOT / "work" / "experiences.jsonl"
FEEDBACK_FILE = ROOT / "config" / "feedback.json"

LESSON_TYPES = {
    "template-bug": "خطأ في القالب",
    "limit": "حدّ اكتُشف",
    "lesson": "درس مستفاد",
    "engine": "ملاحظة محرك",
    "translation": "خبرة في التعريب",
    "tool": "أداة",
    "workflow": "سير العمل",
}
FIELD_LIMIT = 800
TEXT_SUFFIXES = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".ps1", ".csv"}

USER_DIR_RE = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'`]+|/(?:home|Users)/[^/\s\"'`]+")
SECRET_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})")
ASSIGNED_SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|token|password|secret)(\s*[:=]\s*)[^\s,;]+")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Sanitizer:
    """Replace known paths with placeholders, then any user folder and anything that looks like a secret."""

    def __init__(self, paths: dict[str, str]):
        variants = []
        for placeholder, path in paths.items():
            if path:
                for form in {str(path), str(path).replace("\\", "/"), str(path).replace("/", "\\")}:
                    variants.append((form.rstrip("\\/"), placeholder))
        self.paths = sorted(variants, key=lambda item: -len(item[0]))

    def text(self, value: str, limit: int | None = None) -> str:
        for form, placeholder in self.paths:
            if form:
                value = re.sub(re.escape(form), placeholder, value, flags=re.I)
        value = USER_DIR_RE.sub("<HOME>", value)
        value = SECRET_RE.sub("<SECRET>", value)
        value = ASSIGNED_SECRET_RE.sub(r"\1\2<SECRET>", value)
        if limit and len(value) > limit:
            value = value[:limit] + " …"
        return value

    def data(self, value):
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {k: self.data(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.data(v) for v in value]
        return value


def load_lessons(path: Path = LESSONS_FILE) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_lesson(kind: str, what: str, evidence: str, suggest: str = "", file: str = "", by: str = "",
               path: Path = LESSONS_FILE) -> dict:
    if kind not in LESSON_TYPES:
        raise ValueError(f"type must be one of {', '.join(LESSON_TYPES)}")
    if not what.strip() or not evidence.strip():
        raise ValueError("a lesson needs --what and --evidence")
    lessons = load_lessons(path)
    lesson = {"id": f"E-{len(lessons) + 1:03d}", "type": kind, "what": what.strip(), "evidence": evidence.strip(),
              "suggest": suggest.strip(), "file": file.strip(), "by": by.strip(), "at": now()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(lesson, ensure_ascii=False) + "\n")
    return lesson


def lesson_key(lesson: dict) -> str:
    """A stable id across users and copies, so the developer applies a lesson once."""
    basis = json.dumps([lesson.get("type"), lesson.get("what"), lesson.get("suggest")], ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def feedback() -> dict:
    return json.loads(FEEDBACK_FILE.read_text(encoding="utf-8")) if FEEDBACK_FILE.is_file() else {}


def send_message(zip_name: str, contact: dict | None = None) -> str:
    contact = feedback() if contact is None else contact
    discord, x = contact.get("discord", {}), contact.get("x", "")
    lines = [f"ملف الخبرات جاهز: {zip_name}",
             "لا يحتوي نصوص اللعبة ولا ملفاتها ولا مسارات جهازك. أرسله إلى مطوّر القالب بنفسك:"]
    if discord.get("invite"):
        lines.append(f"- سيرفر Discord «{discord.get('name', '')}»: {discord['invite']}")
    if x:
        lines.append(f"- أو تواصل معه على X (تويتر): {x}")
    return "\n".join(lines)


def summary_md(lessons: list[dict], facts: dict) -> str:
    game = facts.get("game", {})
    lines = [f"# خبرات تعريب: {game.get('name') or 'لعبة'}", "",
             f"- المحرك: {game.get('engine') or 'غير محدد'} — المحوّل: {game.get('adapter') or 'غير محدد'}",
             f"- آخر مرحلة: {facts.get('phase', '')} — نسخة القالب: {facts.get('template', '')}",
             f"- الوحدات: {facts.get('units', {}).get('total', 0)} — الإصلاحات: {len(facts.get('fixes', []))}"
             f" — المراحل المعاد فتحها: {len(facts.get('reopened', []))}", ""]
    if not lessons:
        lines.append("لم تُسجَّل دروس في هذا المشروع.")
    for kind, label in LESSON_TYPES.items():
        group = [lesson for lesson in lessons if lesson["type"] == kind]
        if group:
            lines += [f"## {label} ({len(group)})", ""]
            for lesson in group:
                lines.append(f"- **{lesson['what']}**")
                lines.append(f"  - الدليل: {lesson['evidence']}")
                if lesson.get("suggest"):
                    lines.append(f"  - المقترح: {lesson['suggest']}" + (f" (`{lesson['file']}`)" if lesson.get("file") else ""))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def pack(lessons: list[dict], facts: dict, files: dict[str, Path], out_dir: Path, game: str,
         sanitizer: Sanitizer, day: str | None = None) -> Path:
    """Write experiences-<game>-<date>.zip: lessons, facts, an Arabic summary, and sanitized knowledge files."""
    clean = [{**{k: sanitizer.text(str(v), FIELD_LIMIT) for k, v in lesson.items() if k != "key"},
              "key": lesson_key(lesson)} for lesson in lessons]
    facts = sanitizer.data(facts)
    slug = re.sub(r"[^\w-]+", "-", game, flags=re.U).strip("-").lower() or "game"
    day = day or datetime.now().strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"experiences-{slug}-{day}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("lessons.jsonl", "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in clean))
        archive.writestr("facts.json", json.dumps(facts, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("summary.md", summary_md(clean, facts))
        for name, source in sorted(files.items()):
            if source.is_file() and source.suffix.lower() in TEXT_SUFFIXES:
                archive.writestr(f"files/{name}", sanitizer.text(source.read_text(encoding="utf-8", errors="replace")))
    return target


def sha256(path: Path) -> str:
    return digest(path)
