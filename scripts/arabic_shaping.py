"""Pre-shape and visually order Arabic for engines that cannot render it themselves.

Only adapters that declare `rtl = "needs_preshape"` use this, and only when the
build is written: units always keep logical Unicode Arabic. The contextual
forms come from the Unicode database (the decompositions of the Arabic
Presentation Forms), so there is no hand-made table and no dependency.

`render(text)` shapes each line, then reverses it for display while keeping
Latin words, numbers, code spans ({...}, [...], <...>, %s) and escapes (\\n) intact and in
reading order, and mirrors paired brackets. Wrap lines before rendering:
reversing a wrapped paragraph puts its lines in the wrong order.
"""
from __future__ import annotations

import re
import unicodedata

TATWEEL = "ـ"
LAM = "ل"
ALEFS = "آأإا"  # only lam + alef is a required ligature in Arabic
MIRROR = str.maketrans("()[]{}«»<>", ")(][}{»«><")


def _forms() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """(letter -> {isolated, final, initial, medial}, alef -> lam-alef {isolated, final})."""
    forms: dict[str, dict[str, str]] = {}
    lam_alef: dict[str, dict[str, str]] = {}
    # Presentation Forms-B first (the standard Arabic set), then -A for letters it lacks.
    for start, end in ((0xFE70, 0xFEFF), (0xFB50, 0xFDFF)):
        for code in range(start, end):
            parts = unicodedata.decomposition(chr(code)).split()
            if len(parts) < 2 or not parts[0].startswith("<"):
                continue
            tag = parts[0].strip("<>")
            if tag not in ("isolated", "final", "initial", "medial"):
                continue
            letters = "".join(chr(int(p, 16)) for p in parts[1:])
            if len(letters) == 1:
                forms.setdefault(letters, {}).setdefault(tag, chr(code))
            elif len(letters) == 2 and letters[0] == LAM and letters[1] in ALEFS and tag in ("isolated", "final"):
                lam_alef.setdefault(letters[1], {}).setdefault(tag, chr(code))
    return forms, lam_alef


FORMS, LAM_ALEF = _forms()
CODE_OR_LTR_RE = re.compile(
    r"\{[^}]*\}|\[[^\]]*\]|<[^>]*>|%\w+|\\."        # code spans and escapes stay whole
    r"|[A-Za-z0-9](?:[A-Za-z0-9 .,:'/_-]*[A-Za-z0-9])?"  # a left-to-right run
    r"|.", re.S)


def _transparent(char: str) -> bool:
    return unicodedata.category(char) == "Mn"


def _joins_forward(char: str | None) -> bool:
    """Does this character connect to the letter after it?"""
    return char == TATWEEL or (char in FORMS and ("initial" in FORMS[char] or "medial" in FORMS[char]))


def _joins_back(char: str | None) -> bool:
    """Can this character connect to the letter before it? Hamza and other isolated-only letters cannot."""
    return char == TATWEEL or (char in FORMS and ("final" in FORMS[char] or "medial" in FORMS[char]))


def shape(text: str) -> str:
    """Replace logical Arabic letters with their contextual presentation forms."""
    chars = list(text)
    out = []
    i = 0
    while i < len(chars):
        char = chars[i]
        if char not in FORMS:
            out.append(char)
            i += 1
            continue
        prev = next((c for c in reversed(chars[:i]) if not _transparent(c)), None)
        j = i + 1
        while j < len(chars) and _transparent(chars[j]):
            j += 1
        following = chars[j] if j < len(chars) else None
        joined_before = _joins_forward(prev)
        if char == LAM and following in LAM_ALEF:
            ligature = LAM_ALEF[following]
            out.append(ligature.get("final" if joined_before else "isolated", char + following))
            out.extend(chars[i + 1:j])  # marks between lam and alef
            i = j + 1
            continue
        joins_after = _joins_forward(char) and _joins_back(following)
        tag = ("medial" if joined_before and joins_after else "initial" if joins_after
               else "final" if joined_before else "isolated")
        out.append(FORMS[char].get(tag) or FORMS[char].get("isolated", char))
        i += 1
    return "".join(out)


def reorder(line: str) -> str:
    """Visual order for a left-to-right renderer: reverse the line, keep LTR runs and code intact."""
    atoms = CODE_OR_LTR_RE.findall(line)
    return "".join(atom.translate(MIRROR) if len(atom) == 1 else atom for atom in reversed(atoms))


def render(text: str) -> str:
    """Shape, then order each line for display. Lines are rendered independently."""
    return "\n".join(reorder(shape(line)) for line in text.split("\n"))
