"""The agent's task board: what it will do, is doing, waits on, and has done (library for loc.py task).

Tasks live in ``state/tasks.json`` beside ``state/pipeline.json`` and are changed
only through ``loc.py task``; ``tasks.html`` shows them as columns. A task
belongs to a phase, and ``loc.py gate`` refuses to close that phase while one
of its tasks is still open, so nothing planned is forgotten. A task reaches
``done`` only with evidence, and ``waiting`` or ``dropped`` only with a reason.

PLAN.md's batch checklist is shown on the board as read-only cards; PLAN.md
stays the only place batches are written.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("later", "next", "doing", "waiting", "verify", "done", "dropped")
OPEN = STATUSES[:5]
LABELS = {"later": "لاحقًا", "next": "التالي", "doing": "قيد العمل", "waiting": "بانتظارك",
          "verify": "للتحقق", "done": "منجزة", "dropped": "أُلغيت"}
KINDS = ("translation", "fix", "research", "question", "tool", "qa", "integration", "other")
KIND_LABELS = {"translation": "ترجمة", "fix": "إصلاح", "research": "بحث", "question": "سؤال", "tool": "أداة",
               "qa": "فحص", "integration": "دمج", "other": "أخرى"}
NEEDS_REASON = ("waiting", "dropped")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tasks_file(state_file: Path) -> Path:
    return Path(state_file).parent / "tasks.json"


def load(state_file: Path) -> list[dict]:
    path = tasks_file(state_file)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def save(state_file: Path, tasks: list[dict]) -> None:
    path = tasks_file(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find(tasks: list[dict], ident: str) -> dict:
    task = next((t for t in tasks if t["id"] == ident), None)
    if task is None:
        raise ValueError(f"no task {ident} (loc.py task list)")
    return task


def add(state_file: Path, title: str, kind: str, phase: str, status: str = "next", origin: str = "",
        links: dict | None = None, note: str = "") -> str:
    if not title.strip():
        raise ValueError("a task needs a title")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if status not in OPEN:
        raise ValueError(f"a new task starts in one of {OPEN}")
    tasks = load(state_file)
    ident = f"T-{len(tasks) + 1:03d}"
    tasks.append({"id": ident, "title": title.strip(), "kind": kind, "phase": phase, "status": status,
                  "origin": origin, "links": links or {}, "created": now(),
                  "history": [{"status": status, "at": now(), "note": note}]})
    save(state_file, tasks)
    return ident


def move(state_file: Path, ident: str, status: str, note: str = "", evidence: str = "", reason: str = "") -> dict:
    """Move a task to a column. done needs evidence; waiting and dropped need a reason."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if status == "done" and not evidence.strip():
        raise ValueError("done needs --evidence: the command output, file, or verdict that shows it")
    if status in NEEDS_REASON and not reason.strip():
        raise ValueError(f"{status} needs --reason ({'the question for the user' if status == 'waiting' else 'why'})")
    tasks = load(state_file)
    task = find(tasks, ident)
    task["status"] = status
    if evidence:
        task["evidence"] = evidence.strip()
    if reason:
        task["reason"] = reason.strip()
    task["history"].append({"status": status, "at": now(), "note": (note or reason or evidence).strip()})
    save(state_file, tasks)
    return task


def defer(state_file: Path, ident: str, to_phase: str, reason: str, phases: tuple, current: str) -> dict:
    """Hand a task to a later phase, so it stops blocking this one without being forgotten."""
    if to_phase not in phases or phases.index(to_phase) <= phases.index(current):
        raise ValueError(f"defer only to a phase after {current}")
    if not reason.strip():
        raise ValueError("defer needs --reason")
    tasks = load(state_file)
    task = find(tasks, ident)
    task.update(phase=to_phase, status="later" if task["status"] in OPEN else task["status"])
    task["history"].append({"status": task["status"], "at": now(), "note": f"→ {to_phase}: {reason.strip()}"})
    save(state_file, tasks)
    return task


def linked(state_file: Path, key: str, value: str) -> dict | None:
    return next((t for t in load(state_file) if t.get("links", {}).get(key) == value), None)


def open_in_phase(state_file: Path, phase: str) -> list[dict]:
    return [t for t in load(state_file) if t["phase"] == phase and t["status"] in OPEN]


def gate_checks(state_file: Path, phase: str) -> list[tuple[bool, str]]:
    """One gate criterion when this phase has tasks: none may still be open."""
    if not any(t["phase"] == phase for t in load(state_file)):
        return []
    left = open_in_phase(state_file, phase)
    shown = "، ".join(t["id"] for t in left[:5]) or "لا شيء"
    return [(not left, f"كل مهام المرحلة منجزة أو مؤجلة بسبب (loc.py task list؛ المفتوحة: {len(left)} — {shown})")]


BATCH_LINE = re.compile(r"^\s*[-*] \[( |x|X)\]\s+(.+)$")


def plan_batch_cards(plan_file: Path) -> list[dict]:
    """PLAN.md's batch checklist as read-only cards: [x] done, '— unfinished' doing, else next."""
    if not Path(plan_file).is_file():
        return []
    cards, inside = [], False
    for line in Path(plan_file).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## الدفعات"
            continue
        match = BATCH_LINE.match(line) if inside else None
        if match:
            text = match.group(2).strip()
            status = "done" if match.group(1).lower() == "x" else "doing" if "unfinished" in text else "next"
            cards.append({"id": text.split()[0], "title": text, "kind": "translation", "status": status,
                          "from_plan": True})
    return cards
