"""Validate PO, XLIFF inline codes, and common ICU message structures."""
from __future__ import annotations

import argparse
from collections import Counter
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loc_qa import tokens  # noqa: E402

ARABIC = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
ICU_KIND = re.compile(r"\{\s*[A-Za-z_][\w.]*\s*,\s*(plural|selectordinal|select)\s*,")
SELECTOR = re.compile(r"(=?[\w.-]+)\s*\{")
INLINE = {"ph", "pc", "sc", "ec", "mrk", "g", "x", "bx", "ex", "bpt", "ept", "it"}


def balanced(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "{": depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0: return False
    return depth == 0


def _closing(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0: return index
    raise ValueError("unbalanced ICU braces")


def _parts(content: str) -> list[str]:
    parts, start, depth = [], 0, 0
    for index, char in enumerate(content):
        if char == "{": depth += 1
        elif char == "}": depth -= 1
        elif char == "," and depth == 0 and len(parts) < 2:
            parts.append(content[start:index].strip())
            start = index + 1
    parts.append(content[start:].strip())
    return parts


def _message(text: str):
    """Return protected literal tokens and ordered ICU controls; branch text is translatable."""
    protected, controls = Counter(), []
    index, literal_start = 0, 0
    while index < len(text):
        if text[index] == "}": raise ValueError("unbalanced ICU braces")
        if text[index] != "{":
            index += 1
            continue
        protected.update(tokens(text[literal_start:index]))
        end = _closing(text, index)
        content = text[index + 1:end]
        parts = _parts(content)
        if len(parts) >= 3 and parts[1] in {"plural", "selectordinal", "select"}:
            options = {}
            body = parts[2]
            offset = ""
            match = re.match(r"offset\s*:\s*(\d+)\s*", body)
            if match:
                offset = match.group(1)
                body = body[match.end():]
            cursor = 0
            while cursor < len(body):
                while cursor < len(body) and body[cursor].isspace(): cursor += 1
                if cursor == len(body): break
                selector = SELECTOR.match(body, cursor)
                if not selector: raise ValueError("invalid ICU branch")
                key = selector.group(1)
                if key in options: raise ValueError(f"duplicate ICU branch: {key}")
                opening = selector.end() - 1
                close = _closing(body, opening)
                options[key] = _message(body[opening + 1:close])
                cursor = close + 1
            if "other" not in options: raise ValueError("ICU control lacks mandatory 'other' branch")
            controls.append((parts[0], parts[1], offset, options))
        else:
            protected.update(["{" + content + "}"])
        index = end + 1
        literal_start = index
    protected.update(tokens(text[literal_start:]))
    return protected, controls


def _compare(source, target, label: str, errors: list[str]):
    if source[0] != target[0]: errors.append(f"{label}: protected-token mismatch")
    if len(source[1]) != len(target[1]):
        errors.append(f"{label}: ICU control count mismatch")
        return
    remaining = list(target[1])
    for index, left in enumerate(source[1]):
        matches = [right for right in remaining if right[:3] == left[:3]]
        if not matches:
            errors.append(f"{label}: ICU argument/type/offset mismatch [{index}]")
            continue
        right = matches[0]
        remaining.remove(right)
        for key, branch in left[3].items():
            if key not in right[3]:
                errors.append(f"{label}: missing ICU branch {key!r}")
            else:
                _compare(branch, right[3][key], f"{label}/{key}", errors)


def check_pair(source: str, target: str, label: str, require_arabic=False):
    errors, warnings = [], []
    if ICU_KIND.search(source) or ICU_KIND.search(target):
        try: _compare(_message(source), _message(target), label, errors)
        except ValueError as exc: errors.append(f"{label}: {exc}")
    else:
        if tokens(source) != tokens(target): errors.append(f"{label}: protected-token mismatch")
        if not balanced(target): errors.append(f"{label}: unbalanced ICU braces")
    if require_arabic and target.strip() and not ARABIC.search(target):
        warnings.append(f"{label}: no Arabic letters")
    return errors, warnings


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _inline_signature(element):
    return Counter((_local(child.tag), child.get("id"), child.get("rid"))
                   for child in element.iter() if child is not element and _local(child.tag) in INLINE)


def xliff_pairs(path: Path):
    root = ET.parse(path).getroot()
    for index, unit in enumerate(root.iter(), 1):
        if _local(unit.tag) not in {"trans-unit", "segment"}: continue
        source = target = None
        for child in unit:
            if _local(child.tag) == "source": source = child
            elif _local(child.tag) == "target": target = child
        if source is not None and target is not None:
            yield "".join(source.itertext()), "".join(target.itertext()), unit.attrib.get("id", str(index)), _inline_signature(source) == _inline_signature(target)


def po_pairs(path: Path):
    try: import polib
    except ImportError as exc: raise RuntimeError("polib is required for PO validation") from exc
    po = polib.pofile(str(path))
    for entry in po:
        if entry.obsolete: continue
        if entry.msgid_plural:
            for key, target in entry.msgstr_plural.items():
                yield entry.msgid_plural, target, f"{entry.linenum}:plural[{key}]", True
        else:
            yield entry.msgid, entry.msgstr, str(entry.linenum), True


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path)
    p.add_argument("--require-arabic", action="store_true")
    a = p.parse_args(argv)
    files = [a.path] if a.path.is_file() else sorted([*a.path.rglob("*.po"), *a.path.rglob("*.xlf"), *a.path.rglob("*.xliff")])
    if not files: print("ERROR no PO/XLIFF files found"); return 2
    errors, warnings, units = [], [], 0
    for file in files:
        try:
            pairs = po_pairs(file) if file.suffix.lower() == ".po" else xliff_pairs(file)
            for src, tgt, label, inline_ok in pairs:
                if not tgt: continue
                units += 1
                e, w = check_pair(src, tgt, f"{file}:{label}", a.require_arabic)
                errors += e
                warnings += w
                if not inline_ok: errors.append(f"{file}:{label}: XLIFF inline-code mismatch")
        except (OSError, ET.ParseError, RuntimeError, ValueError) as exc:
            errors.append(f"{file}: {exc}")
    for x in errors: print("ERROR", x)
    for x in warnings: print("WARN ", x)
    print(f"FILES={len(files)} UNITS={units} ERRORS={len(errors)} WARNINGS={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__": raise SystemExit(main())
