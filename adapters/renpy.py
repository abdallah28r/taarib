"""Ren'Py adapter for native translation files (``game/tl/<language>/**/*.rpy``).

Works on the files Ren'Py's "Generate Translations" writes, so translation
identifiers always come from Ren'Py itself and the original scripts are never
modified. Supported blocks:

- dialogue: ``translate <lang> <identifier>:`` with the original statement in a
  ``# who "what"`` comment followed by the active ``who "what"`` line;
- strings: ``translate <lang> strings:`` with ``old "..."`` / ``new "..."`` pairs.

A dialogue line whose active text equals the original (Ren'Py's default) or is
empty counts as untranslated. Only double-quoted, single-line strings are
supported; anything else raises ValueError with the file and line, rather than
guessing. ``voice`` statements are skipped.

Option: ``language`` (default ``arabic``).
"""
from __future__ import annotations

import re
from pathlib import Path

from loc_adapter_base import Adapter, loc_units

TRANSLATE = re.compile(r"^translate\s+(\w+)\s+([\w.]+)\s*:\s*$")
LOCATION = re.compile(r"^#\s*(\S+\.rpy:\d+)\s*$")


def find_string(line: str, where: str) -> tuple[str, int, int] | None:
    """(prefix, start, end) of the first double-quoted string; start/end exclude quotes."""
    quote = line.find('"')
    if quote < 0:
        return None
    index = quote + 1
    while index < len(line):
        char = line[index]
        if char == "\\":
            index += 2
            continue
        if char == '"':
            return line[:quote], quote + 1, index
        index += 1
    raise ValueError(f"{where}: unterminated or multi-line string")


def unescape(raw: str) -> str:
    out, index = [], 0
    while index < len(raw):
        char = raw[index]
        if char == "\\" and index + 1 < len(raw):
            following = raw[index + 1]
            out.append("\n" if following == "n" else following)
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Entry:
    def __init__(self, ident, key, source, active, line_index, start, end, context):
        self.ident, self.key, self.source, self.active = ident, key, source, active
        self.line_index, self.start, self.end, self.context = line_index, start, end, context


class RenpyAdapter(Adapter):
    engine = "renpy"
    token_profile = "renpy"
    # Ren'Py shapes Arabic itself when the game sets `config.rtl = True` (HarfBuzz in Ren'Py 8);
    # confirm it on each game in the playtest and switch to needs_preshape if letters come out broken.
    rtl = "native"

    @property
    def language(self) -> str:
        return self.options.get("language", "arabic")

    def _tl_files(self, root: Path) -> list[str]:
        base = root / "game" / "tl" / self.language
        return sorted(p.relative_to(root).as_posix() for p in base.rglob("*.rpy")) if base.is_dir() else []

    def inventory(self) -> list[str]:
        return self._tl_files(self.game_root)

    def _parse(self, root: Path, rel: str) -> tuple[list[Entry], list[str], bool]:
        data = (root / rel).read_bytes()
        bom = data.startswith(b"\xef\xbb\xbf")
        lines = data.decode("utf-8-sig").splitlines(keepends=True)
        entries: list[Entry] = []
        block = None
        location = ""
        originals: list[tuple[str, str]] = []
        pending_old = None
        count = 0
        for index, line in enumerate(lines):
            where = f"{rel}:{index + 1}"
            text = line.rstrip("\r\n")
            stripped = text.strip()
            if not stripped:
                continue
            if not text[:1].isspace():
                match = TRANSLATE.match(text)
                if match and match.group(1) == self.language:
                    block, originals, pending_old, count = match.group(2), [], None, 0
                else:
                    if originals:
                        raise ValueError(f"{where}: original statement without a translated line")
                    block = None
                    location_match = LOCATION.match(text)
                    if location_match:
                        location = location_match.group(1)
                continue
            if block is None:
                continue
            location_match = LOCATION.match(stripped)
            if location_match:
                location = location_match.group(1)
                continue
            if block == "strings":
                if stripped.startswith("#"):
                    continue
                found = find_string(text, where)
                keyword = stripped.split(None, 1)[0]
                if keyword == "old" and found:
                    pending_old = unescape(text[found[1]:found[2]])
                elif keyword == "new" and found and pending_old is not None:
                    ident = f"{rel}#strings:{loc_units.source_hash(pending_old)}"
                    context = {"source_location": location, "function": "string"}
                    entries.append(Entry(ident, "strings", pending_old, unescape(text[found[1]:found[2]]),
                                         index, found[1], found[2], context))
                    pending_old = None
                else:
                    raise ValueError(f"{where}: expected old/new string pair")
                continue
            is_comment = stripped.startswith("#")
            statement = stripped[1:].strip() if is_comment else text
            found = find_string(statement, where)
            if not found or found[0].strip().split()[:1] == ["voice"]:
                continue
            who = found[0].strip().split()[0] if found[0].strip() else ""
            value = unescape(statement[found[1]:found[2]])
            if is_comment:
                originals.append((who, value))
                continue
            if not originals:
                raise ValueError(f"{where}: translated line without an original comment")
            speaker, source = originals.pop(0)
            ident = f"{rel}#{block}" + (f"#{count}" if count else "")
            count += 1
            context = {"speaker": speaker or "narrator", "source_location": location,
                       "label": block.rsplit("_", 1)[0]}
            entries.append(Entry(ident, block, source, value, index, found[1], found[2], context))
        if originals:
            raise ValueError(f"{rel}: original statement without a translated line at end of file")
        return entries, lines, bom

    def extract(self) -> list[dict]:
        units = []
        for rel in self.inventory():
            entries, _, _ = self._parse(self.game_root, rel)
            for entry in entries:
                translated = entry.active if entry.active and entry.active != entry.source else ""
                fields = {"key": entry.key, "context": entry.context}
                if translated:
                    fields.update(target=translated, status="translated", translated_by="existing-tl")
                units.append(loc_units.new_unit(entry.ident, rel, entry.source, **fields))
        return units

    def rebuild(self, units: list[dict], out_dir: Path) -> list[str]:
        targets: dict[str, dict[str, str]] = {}
        for unit in units:
            if unit.get("target"):
                targets.setdefault(unit["file"], {})[unit["id"]] = unit["target"]
        written = []
        for rel, by_id in sorted(targets.items()):
            entries, lines, bom = self._parse(self.game_root, rel)
            known = {entry.ident: entry for entry in entries}
            unknown = sorted(set(by_id) - set(known))
            if unknown:
                raise ValueError(f"{rel}: unit ids not found in the file: {unknown[:3]}")
            for ident, target in by_id.items():
                entry = known[ident]
                line = lines[entry.line_index]
                lines[entry.line_index] = line[:entry.start] + escape(self.render(target)) + line[entry.end:]
            path = Path(out_dir) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + "".join(lines).encode("utf-8"))
            written.append(rel)
        return written

    def read_back(self, root: Path) -> dict[str, str]:
        shown = {}
        for rel in self._tl_files(Path(root)):
            for entry in self._parse(Path(root), rel)[0]:
                shown[entry.ident] = entry.active or entry.source
        return shown


ADAPTER = RenpyAdapter
