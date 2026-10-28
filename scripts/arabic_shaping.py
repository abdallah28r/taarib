"""Pre-shape and visually order Arabic for engines that cannot render it themselves.

Only adapters that declare `rtl = "needs_preshape"` use this, and only when the
build is written: units always keep logical Unicode Arabic. The contextual
forms come from the Unicode database (the decompositions of the Arabic
Presentation Forms), so there is no hand-made table and no dependency.

`render(text)` shapes each line, then reverses it for display while keeping
Latin words, numbers (Western and Arabic-Indic), code spans ({...}, [...],
<...>, %s) and escapes (\\n) intact and in reading order, keeps paired tags
such as <b>...</b> valid, and mirrors paired brackets. Ordering follows the
Unicode Bidi Algorithm for a right-to-left paragraph: "50%" stays "50%", a
sign before a number ("+25") stays outside the number as a native renderer
shows it.

Give `render` a `max_width` and a `measure` to wrap: the logical text is
wrapped by the width of what will be drawn (shaped glyphs), and only then is
each line shaped and reversed. Reversing a whole paragraph and letting the
engine wrap it puts its last words on the first line.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable

TATWEEL = "ـ"
LAM = "ل"
ALEFS = "آأإا"  # only lam + alef is a required ligature in Arabic
MIRROR = str.maketrans("()[]{}«»<>‹›", ")(][}{»«><›‹")


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
CODE_RE = re.compile(r"\{[^}]*\}|\[[^\]]*\]|<[^>]*>|%\w+|\\.", re.S)
LTR = r"A-Za-z0-9À-ɏ"
ARABIC_DIGITS = r"٠-٩۰-۹"
MARKS = r"ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۤۧۨ-ۭ"
# A currency or percent sign touching a Western number joins it (UBA rule W5): "50%", "$5", "20°".
UNIT_SIGNS = r"%#$°‰₠-⃏¢-¥"
ATOM_RE = re.compile(
    CODE_RE.pattern
    + rf"|[{UNIT_SIGNS}]*[{LTR}](?:[{LTR} .,:'/_+-]*[{LTR}])?[{UNIT_SIGNS}]*"  # a left-to-right run
    + rf"|[{ARABIC_DIGITS}](?:[{ARABIC_DIGITS}٫٬.,:/]*[{ARABIC_DIGITS}])?"  # Arabic-Indic number
    + rf"|.[{MARKS}]+"  # a letter keeps its diacritics after it when the line is reversed
    + r"|.", re.S)
TAG_RE = re.compile(r"([<\[{])(/?)([A-Za-z][\w-]*)")
CLOSE_OF = {"<": ">", "[": "]", "{": "}"}


def _transparent(char: str) -> bool:
    return unicodedata.category(char) == "Mn"


def _joins_forward(char: str | None) -> bool:
    """Does this character connect to the letter after it?"""
    return char == TATWEEL or (char in FORMS and ("initial" in FORMS[char] or "medial" in FORMS[char]))


def _joins_back(char: str | None) -> bool:
    """Can this character connect to the letter before it? Hamza and other isolated-only letters cannot."""
    return char == TATWEEL or (char in FORMS and ("final" in FORMS[char] or "medial" in FORMS[char]))


def shape(text: str, *, strip_harakat: bool = False, lam_alef: bool = True,
          transparent: re.Pattern | None = None) -> str:
    """Replace logical Arabic letters with their contextual presentation forms.

    strip_harakat drops diacritics for fonts that lack them (a missing mark
    shows as a box). lam_alef=False keeps lam and alef as two letters for a
    font without the ligature. Code spans matching `transparent` (an engine's
    pause or colour code inside a word) are kept byte for byte and do not break
    the joining of the letters around them; other code spans do.
    """
    if strip_harakat:
        text = "".join(c for c in text if not _transparent(c))
    pieces: list[str] = []
    if transparent is None:
        pieces = list(text)
    else:
        pos = 0
        for match in transparent.finditer(text):
            pieces += list(text[pos:match.start()]) + [match.group(0)]
            pos = match.end()
        pieces += list(text[pos:])
    skip = lambda p: len(p) > 1 or _transparent(p)  # noqa: E731 (marks and transparent codes)
    out = []
    i = 0
    while i < len(pieces):
        char = pieces[i]
        if char not in FORMS:
            out.append(char)
            i += 1
            continue
        prev = next((c for c in reversed(pieces[:i]) if not skip(c)), None)
        j = i + 1
        while j < len(pieces) and skip(pieces[j]):
            j += 1
        following = pieces[j] if j < len(pieces) else None
        joined_before = _joins_forward(prev)
        if lam_alef and char == LAM and following in LAM_ALEF:
            ligature = LAM_ALEF[following]
            out.append(ligature.get("final" if joined_before else "isolated", char + following))
            out.extend(pieces[i + 1:j])  # marks between lam and alef
            i = j + 1
            continue
        joins_after = _joins_forward(char) and _joins_back(following)
        tag = ("medial" if joined_before and joins_after else "initial" if joins_after
               else "final" if joined_before else "isolated")
        out.append(FORMS[char].get(tag) or FORMS[char].get("isolated", char))
        i += 1
    return "".join(out)


def glyphs_used(texts) -> set[str]:
    """Characters the font or glyph bank must contain to draw these rendered texts."""
    return {c for text in texts for c in CODE_RE.sub("", text) if not c.isspace()}


def _tag_partners(atoms: list[str]) -> dict[int, str]:
    """For each paired tag, the text of its partner: <b>/</b>, [color=x]/[/color], {i}/{/i}."""
    partners: dict[int, str] = {}
    open_tags: list[tuple[int, str, str]] = []
    for index, atom in enumerate(atoms):
        match = TAG_RE.match(atom)
        if not match or len(atom) < 3 or atom[-1] != CLOSE_OF[match.group(1)] or atom.endswith("/>"):
            continue
        bracket, closing, name = match.groups()
        if not closing:
            open_tags.append((index, bracket, name.lower()))
            continue
        for depth in range(len(open_tags) - 1, -1, -1):
            start, start_bracket, start_name = open_tags[depth]
            if start_bracket == bracket and start_name == name.lower():
                partners[start], partners[index] = atom, atoms[start]
                del open_tags[depth:]
                break
    return partners


def reorder(line: str, codes: re.Pattern | None = None) -> str:
    """Visual order for a left-to-right renderer: reverse the line, keep LTR runs, numbers and code intact.

    A tag pair is reversed with its text, so each tag takes its partner's place
    to stay opening-before-closing: <b>نص</b> becomes <b>صن</b>, not </b>صن<b>.
    `codes` adds engine codes (e.g. a pause like ^5) that must stay whole.
    """
    atoms, pos = [], 0
    for match in (codes.finditer(line) if codes else ()):
        atoms += ATOM_RE.findall(line[pos:match.start()]) + [match.group(0)]
        pos = match.end()
    atoms += ATOM_RE.findall(line[pos:])
    partners = _tag_partners(atoms)
    out = []
    for index in range(len(atoms) - 1, -1, -1):
        atom = partners.get(index, atoms[index])
        out.append(atom.translate(MIRROR) if len(atom) == 1 else atom)
    return "".join(out)


WORD_RE = re.compile(CODE_RE.pattern + r"|\S", re.S)


def _words(paragraph: str) -> list[str]:
    """Words split on spaces, never inside a code span."""
    words, current, pos = [], "", 0
    for match in WORD_RE.finditer(paragraph):
        if match.start() > pos and current:  # whitespace since the last piece
            words.append(current)
            current = ""
        current += match.group(0)
        pos = match.end()
    if current:
        words.append(current)
    return words


def _greedy(words: list[str], limit: float, fits: Callable[[str], float]) -> list[str]:
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and fits(candidate) > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


def wrap(text: str, max_width: float, measure: Callable[[str], float], *, balanced: bool = True,
         **shape_options) -> list[str]:
    """Logical lines that each fit max_width once shaped. Hard line breaks are kept.

    measure(shaped_text) returns what the engine will draw: character count for
    a fixed-pitch box (`len`), or pixels from the game's own font
    (`font_measure`). A word wider than the box stays alone on its line.
    balanced=True keeps the same number of lines but evens them out, so a long
    line is not followed by a one-word last line.
    """
    width = lambda s: measure(shape(s, **shape_options))  # noqa: E731
    out: list[str] = []
    for paragraph in text.split("\n"):
        if width(paragraph) <= max_width:
            out.append(paragraph)
            continue
        words = _words(paragraph)
        lines = _greedy(words, max_width, width)
        if balanced and len(lines) > 1:
            low, high = 0.0, float(max_width)
            for _ in range(20):  # the narrowest limit that still gives the same number of lines
                middle = (low + high) / 2
                trial = _greedy(words, middle, width)
                if len(trial) <= len(lines) and all(width(line) <= max_width for line in trial):
                    lines, high = trial, middle
                else:
                    low = middle
        out.extend(lines)
    return out


def font_measure(font_path, size: float) -> Callable[[str], float]:
    """Pixel width of shaped text in a TTF/OTF at `size` px, from its advance widths (needs fontTools).

    No kerning: leave a small margin in max_width. A character the font lacks
    is measured as the font's .notdef glyph, the box the player would see.
    """
    from fontTools.ttLib import TTFont
    font = TTFont(str(font_path), lazy=True)
    cmap, metrics = font.getBestCmap(), font["hmtx"].metrics
    scale = size / font["head"].unitsPerEm
    notdef = metrics.get(".notdef", (font["head"].unitsPerEm // 2, 0))[0]
    advance = {}

    def measure(text: str) -> float:
        total = 0
        for char in CODE_RE.sub("", text):
            if char not in advance:
                glyph = cmap.get(ord(char))
                advance[char] = metrics[glyph][0] if glyph in metrics else notdef
            total += advance[char]
        return total * scale
    return measure


MARK_RE = re.compile(f"[{MARKS}]")


def shift_marks(visual: str) -> str:
    """Move each diacritic one character later, for engines that draw marks one position early.

    A mark with no following character lands on an added space.
    """
    chars = list(visual)
    i = 0
    while i < len(chars):
        if not MARK_RE.fullmatch(chars[i]):
            i += 1
            continue
        j = i
        while j < len(chars) and MARK_RE.fullmatch(chars[j]):
            j += 1
        if j == len(chars):
            chars.append(" ")
        chars[i:j + 1] = [chars[j]] + chars[i:j]
        i = j + 1
    return "".join(chars)


def unrender(visual: str) -> str:
    """Logical Unicode Arabic from text that was shaped and reversed for display (line by line).

    For importing Arabic already shipped in a game or an older fan translation;
    check the result by eye, because an isolated form cannot tell whether its
    word was split on purpose.
    """
    def base(char: str) -> str:
        return unicodedata.normalize("NFKC", char) if "ﭐ" <= char <= "﻿" else char
    return "\n".join("".join(base(c) for c in reorder(line)) for line in visual.split("\n"))


def render(text: str, *, max_width: float | None = None, measure: Callable[[str], float] | None = None,
           line_sep: str = "\n", marks_one_later: bool = False, **shape_options) -> str:
    """Shape, then order each line for display; wrap first when a width and a measure are given.

    marks_one_later=True suits engines that draw a diacritic one letter early.
    """
    if max_width is not None and measure is not None:
        lines = wrap(text, max_width, measure, **shape_options)
    else:
        lines = text.split("\n")
    codes = shape_options.get("transparent")
    out = [reorder(shape(line, **shape_options), codes) for line in lines]
    return line_sep.join(shift_marks(line) if marks_one_later else line for line in out)
