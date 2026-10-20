"""Unit-based helpers behind loc.py update | tmx | estimate | pseudo.

They replace the old CSV-only scripts (merge_game_update, export_tmx,
estimate_tokens, pseudo_localize) so every tool works on the same records.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import math
import re
import sys
import xml.etree.ElementTree as ET
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

# ----- game updates ---------------------------------------------------------

POSITION_FIELDS = ("file", "key", "asset", "box")


def merge_update(current: list[dict], fresh: list[dict], inventory: set[str]) -> tuple[list[dict], dict]:
    """Merge a fresh adapter extract into existing units by stable id.

    A translation is carried only when the id, source, and context are all
    unchanged. A changed unit goes back to `extracted` with its old Arabic kept
    as `previous_target` for the translator. Units the adapter does not own
    (image regions, files outside its inventory) are kept untouched.
    """
    old_by_id = {u["id"]: u for u in current}
    fresh_ids = {u["id"] for u in fresh}
    report = {"unchanged": 0, "changed": [], "added": [], "removed": [], "kept_other": 0}
    merged = []
    for new in fresh:
        old = old_by_id.get(new["id"])
        if old is None:
            merged.append(new)
            report["added"].append(new["id"])
        elif old["source_hash"] == new["source_hash"] and old.get("context") == new.get("context"):
            kept = dict(old)
            kept.update({k: new[k] for k in POSITION_FIELDS if k in new})
            merged.append(units.canonical(kept))
            report["unchanged"] += 1
        else:
            changed = dict(new)
            if old.get("target"):
                changed["previous_target"] = old["target"]
            changed["notes"] = "source or context changed in a game update; review previous_target"
            merged.append(units.canonical(changed))
            report["changed"].append(new["id"])
    for old in current:
        if old["id"] in fresh_ids:
            continue
        if old.get("kind") == "text" and old.get("file") in inventory:
            report["removed"].append(old["id"])
        else:
            merged.append(old)
            report["kept_other"] += 1
    return merged, report


# ----- translation memory ---------------------------------------------------

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def tmx(all_units: list[dict], min_status: str, source_lang: str, target_lang: str, game: str) -> ET.ElementTree:
    """A TMX 1.4 memory of translated units at or past `min_status`."""
    floor = units.STATUSES.index(min_status)
    root = ET.Element("tmx", version="1.4")
    ET.SubElement(root, "header", creationtool="arabic-loc-template", creationtoolversion="2",
                  segtype="sentence", adminlang="en", srclang=source_lang, datatype="PlainText",
                  creationdate=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    body = ET.SubElement(root, "body")
    for unit in all_units:
        target = (unit.get("target") or "").strip()
        if units.stage(unit) < floor or units.decision(unit) != "translate" or not target:
            continue
        tu = ET.SubElement(body, "tu", tuid=unit["id"])
        ET.SubElement(tu, "prop", type="x-game").text = game
        ET.SubElement(tu, "prop", type="x-file").text = unit.get("file", "")
        ET.SubElement(tu, "prop", type="x-status").text = unit["status"]
        speaker = (unit.get("context") or {}).get("speaker")
        if speaker:
            ET.SubElement(tu, "prop", type="x-speaker").text = speaker
        for lang, text in ((source_lang, unit["source"]), (target_lang, target)):
            ET.SubElement(ET.SubElement(tu, "tuv", {XML_LANG: lang}), "seg").text = text
    return ET.ElementTree(root)


# ----- cost estimate ----------------------------------------------------------

CJK_RE = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def estimate_text(text: str) -> int:
    """Conservative heuristic; Arabic and CJK cost more tokens per character than Latin."""
    cjk = len(CJK_RE.findall(text))
    arabic = len(ARABIC_RE.findall(text))
    other = max(0, len(text) - cjk - arabic)
    return max(1, math.ceil(cjk / 1.5 + arabic / 2.5 + other / 3.5))


def estimate(all_units: list[dict], batch_tokens: int, overhead: int, output_ratio: float) -> dict:
    pending = [u for u in all_units if units.decision(u) == "translate" and not u.get("target")]
    source = sum(estimate_text(u["source"]) for u in pending)
    batches = math.ceil(source / max(1, batch_tokens)) if pending else 0
    return {
        "units_to_translate": len(pending),
        "estimated_source_tokens": source,
        "estimated_arabic_output_tokens": math.ceil(source * output_ratio),
        "estimated_batches": batches,
        "estimated_prompt_overhead_tokens": batches * overhead,
        "note": "Planning estimate only; the provider's tokenizer is authoritative.",
    }


# ----- pseudo-localization ----------------------------------------------------

PSEUDO_PREFIX = "نص عربي تجريبي: "


def pseudo_targets(all_units: list[dict]) -> list[dict]:
    """Arabic-looking, longer targets that keep every token, for testing rendering before translating."""
    return [{**u, "target": PSEUDO_PREFIX + u["source"]} if units.decision(u) != "keep" else u for u in all_units]


# ----- glossary conformance ---------------------------------------------------

TASHKEEL_RE = re.compile(r"[\u064B-\u0652\u0670\u0640]")
ARTICLE_RE = re.compile(r"^(?:[وفبك]?ال|لل)(?=\w{2})")


def normalize_arabic(text: str) -> str:
    """Fold spelling variants so a glossary form matches inflected text."""
    text = TASHKEEL_RE.sub("", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))
    return " ".join(ARTICLE_RE.sub("", word) for word in text.split())


def glossary_entries(glossary: dict) -> list[tuple[str, list[str], str]]:
    """(English term, accepted Arabic forms, 'translate' | 'keep_latin'), longest terms first."""
    entries: dict[str, set[str]] = {}
    for section in ("general", "game_specific", "names"):
        for term, arabic in (glossary.get(section) or {}).items():
            if isinstance(term, str) and isinstance(arabic, str) and arabic.strip() and not term.startswith("["):
                entries.setdefault(term, set()).add(arabic)
    for rule in glossary.get("context_rules") or []:
        forms = {v for v in (rule.get("contexts") or {}).values() if isinstance(v, str)}
        if rule.get("term") and forms:
            entries[rule["term"]] = forms  # any documented context form is acceptable
    result = [(term, sorted(forms), "translate") for term, forms in entries.items()]
    result += [(term, [term], "keep_latin") for term in glossary.get("keep_latin") or []
               if isinstance(term, str) and not term.startswith("[")]
    return sorted(result, key=lambda entry: -len(entry[0]))


def check_terms(all_units: list[dict], glossary: dict) -> list[tuple[str, str, str]]:
    """(unit id, term, expected) for every translated unit whose target misses an approved term."""
    entries = glossary_entries(glossary)
    patterns = [(re.compile(rf"(?<![\w]){re.escape(term)}(?![\w])", re.IGNORECASE), term, forms, kind)
                for term, forms, kind in entries]
    problems = []
    for unit in all_units:
        target = unit.get("target") or ""
        if not target or units.decision(unit) != "translate" or units.stage(unit) < 1:
            continue
        exceptions = set(unit.get("term_exceptions") or [])
        source = unit["source"]
        folded_target = normalize_arabic(target)
        for pattern, term, forms, kind in patterns:
            match = pattern.search(source)
            if not match or term in exceptions:
                continue
            source = source[:match.start()] + " " * len(match.group(0)) + source[match.end():]
            if kind == "keep_latin":
                ok = term in target
            else:
                ok = any(normalize_arabic(form) in folded_target for form in forms)
            if not ok:
                problems.append((unit["id"], term, " | ".join(forms)))
    return problems
