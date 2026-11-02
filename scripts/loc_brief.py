"""Build a self-contained, cache-friendly brief for one translation or proofreading batch.

Layer 1 (rules, role, project conventions, output contract) is byte-identical
for every batch of a project and role, so a runtime can cache it as a prompt
prefix. Layer 2 (character cards and the glossary slice) changes only with the
characters and terms a batch uses. Layer 3 holds the batch itself: continuity
lines and the units. A subagent needs nothing else to do its job: layer 1
also carries the style and review rules (STYLE_REFERENCES), so a delegated
translator or proofreader reads no route, PROJECT.yaml, PLAN.md, or the full
glossary.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LAYER_MARKS = ("<!-- layer 1: identical for every batch -->",
               "<!-- layer 2: characters and terms used by this batch -->",
               "<!-- layer 3: this batch -->")
STYLE_REFERENCES = {
    "translator": ("references/translation-core.md", "references/ui-style.md", "references/dialogue-style.md",
                   "references/subtitles-style.md"),
    "proofreader": ("references/translation-core.md", "references/ui-style.md", "references/dialogue-style.md",
                    "references/subtitles-style.md",
                    ".agents/skills/arabic-proofreading/references/proofreading-checklist.md",
                    "references/problem-codes.md"),
}
PROJECT_RULE_KEYS = ("register", "dialect_policy", "tone", "digits", "dates", "time_format", "quotation_marks",
                     "diacritics", "profanity_policy", "units_policy")
OUTPUT_CONTRACT = {
    "translator": [
        "Write one JSON object keyed by unit id: {\"<id>\": \"<Arabic target>\"} with exactly one non-empty entry",
        "for every unit in layer 3, nothing else. Save it to work/batches/<batch>.json and run",
        "`python scripts/loc.py apply work/batches/<batch>.json --batch <batch> --by <your label>`.",
        "Use each unit's speaker card and addressee gender/number for agreement; if a gender is `unknown` and the",
        "Arabic must choose, give your best target and list that id with one question in your report.",
    ],
    "proofreader": [
        "Record findings in work/proofreading/<batch>.jsonl (format in the proofreading checklist), read flagged",
        "units first, change a target only for clear-cut errors or findings of severity major or above, then run",
        "`python scripts/loc.py findings work/proofreading/<batch>.jsonl` and mark clean units proofread.",
        "Zero findings is a valid result; do not polish for taste.",
    ],
}
SELF_REVIEW_OUTPUT = [
    "Review mode is self: after apply, reread every unit of this batch once against the proofreading checklist",
    "in this brief, fix only clear-cut errors by applying the corrected answer again, list anything that needs a",
    "decision with one question, then run `python scripts/loc.py mark --batch <batch> --status proofread",
    "--self-review`. Do not mark units you listed for a decision.",
]


def characters(path: Path) -> dict[str, dict]:
    """Character cards keyed by id from loc-kit/CHARACTERS.yaml (empty when missing)."""
    import yaml
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(c["id"]): c for c in data.get("characters") or [] if isinstance(c, dict) and c.get("id")}


def glossary_slice(sources: list[str], glossary: dict, entries) -> list[str]:
    """Glossary lines whose English term occurs in this batch, plus every forbidden form."""
    text = "\n".join(sources)
    lines = []
    for term, forms, kind in entries:
        if re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", text, re.IGNORECASE):
            lines.append(f"- {term} → keep in Latin" if kind == "keep_latin" else f"- {term} → {' | '.join(forms)}")
    for form, note in (glossary.get("forbidden") or {}).items():
        lines.append(f"- never: {form} ({note})")
    return lines


def style_text(role: str, root: Path) -> str:
    """The role's style and review references, inlined in a fixed order so layer 1 stays byte-identical."""
    parts = []
    for name in STYLE_REFERENCES[role]:
        path = root / name
        if path.is_file():
            parts += [f"<!-- {name} -->", path.read_text(encoding="utf-8").replace("\r\n", "\n").strip(), ""]
    return "\n".join(parts)


def layer_one(role: str, constraints: str, game: dict, style: str = "", self_review: bool = False) -> str:
    rules = [f"- {key}: {game[key]}" for key in PROJECT_RULE_KEYS if game.get(key)]
    return "\n".join([
        LAYER_MARKS[0],
        constraints.strip().replace("# Subagent brief", f"# {role.capitalize()} brief", 1),
        "",
        "## Project conventions",
        *(rules or ["- see PROJECT.yaml"]),
        "",
        "## Output",
        *OUTPUT_CONTRACT[role],
        *(SELF_REVIEW_OUTPUT if self_review else []),
        "",
        *(["## Style and review rules", "", style] if style else []),
        "",
    ])


def card_line(card: dict) -> str:
    parts = [f"{card.get('id')}", card.get("name") or "", f"gender {card.get('gender') or 'unknown'}"]
    for key in ("role", "voice", "formality", "pronouns"):
        if card.get(key):
            parts.append(f"{key}: {card[key]}")
    return "- " + " — ".join(p for p in parts if p)


def unit_record(unit: dict, role: str, problems: list[str]) -> dict:
    context = unit.get("context") or {}
    record = {"id": unit["id"]}
    for key in ("speaker", "addressee", "addressee_gender", "addressee_number", "scene", "label", "location",
                "function"):
        if context.get(key):
            record[key] = context[key]
    record["source"] = unit["source"]
    for key in ("max_length", "notes", "previous_target"):
        if unit.get(key):
            record[key] = unit[key]
    if role == "proofreader":
        record["target"] = unit.get("target", "")
        if problems:
            record["problems"] = problems
    return record


def build(role: str, batch: str, batch_units: list[dict], file_units: list[dict], constraints: str,
          game: dict, cards: dict[str, dict], glossary: dict, entries, problems: dict[str, list[str]],
          continuity: int = 5, style: str = "", self_review: bool = False) -> str:
    """The full brief text: layer 1, layer 2, layer 3."""
    speakers = sorted({(u.get("context") or {}).get(k) for u in batch_units for k in ("speaker", "addressee")} - {None})
    known = [card_line(cards[s]) for s in speakers if s in cards]
    unknown = [s for s in speakers if s not in cards and s not in ("narrator", "player")]
    ids = {u["id"] for u in batch_units}
    first = next((i for i, u in enumerate(file_units) if u["id"] in ids), 0)
    before = [u for u in file_units[:first] if u.get("target") and u.get("status") != "extracted"][-continuity:]
    layer_two = [
        LAYER_MARKS[1],
        "## Characters",
        *(known or ["- (no character cards yet; see loc-kit/CHARACTERS.yaml)"]),
        *([f"- not in loc-kit/CHARACTERS.yaml (treat gender as unknown): {', '.join(unknown)}"] if unknown else []),
        "",
        "## Glossary for this batch",
        *(glossary_slice([u["source"] for u in batch_units], glossary, entries) or ["- (no glossary terms occur)"]),
        "",
    ]
    layer_three = [
        LAYER_MARKS[2],
        f"## Batch {batch}: {len(batch_units)} units",
        "",
        "Continuity (approved lines just before this batch, read-only):",
        *([f"- {u['source']} → {u['target']}" for u in before] or ["- (none)"]),
        "",
        "```jsonl",
        *[json.dumps(unit_record(u, role, problems.get(u["id"], [])), ensure_ascii=False) for u in batch_units],
        "```",
        "",
    ]
    return layer_one(role, constraints, game, style) +"\n".join(layer_two) + "\n".join(layer_three)
