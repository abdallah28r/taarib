"""Export approved, identified CSV translation pairs to a TMX 1.4 memory."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path


XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def inputs(path: Path):
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.csv"))


def export(path: Path, output: Path, source_lang: str, target_lang: str, game: str) -> int:
    root = ET.Element("tmx", version="1.4")
    ET.SubElement(
        root,
        "header",
        creationtool="arabic-loc-template",
        creationtoolversion="1",
        segtype="sentence",
        adminlang="en",
        srclang=source_lang,
        datatype="PlainText",
        creationdate=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )
    body = ET.SubElement(root, "body")
    seen = set()
    for file in inputs(path):
        with file.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"id", "source", "target", "status"}.issubset(reader.fieldnames):
                continue
            for row in reader:
                source, target = row.get("source", "").strip(), row.get("target", "").strip()
                context = row.get("context", "") or row.get("note", "")
                if (not row.get("id", "").strip() or not source or not target or source == target
                        or row.get("status", "").strip().lower() != "approved"):
                    continue
                identity = (source, target, context)
                if identity in seen:
                    continue
                seen.add(identity)
                tu = ET.SubElement(body, "tu", tuid=row.get("id", ""))
                ET.SubElement(tu, "prop", type="x-game").text = game
                ET.SubElement(tu, "prop", type="x-file").text = (str(file.relative_to(path)) if path.is_dir() else file.name)
                ET.SubElement(tu, "prop", type="x-status").text = "approved"
                if context:
                    ET.SubElement(tu, "prop", type="x-context").text = context
                src_tuv = ET.SubElement(tu, "tuv", {XML_LANG: source_lang})
                ET.SubElement(src_tuv, "seg").text = source
                tgt_tuv = ET.SubElement(tu, "tuv", {XML_LANG: target_lang})
                ET.SubElement(tgt_tuv, "seg").text = target
    ET.indent(root)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return len(seen)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-lang", default="en")
    parser.add_argument("--target-lang", default="ar")
    parser.add_argument("--game", default="unknown")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"ERROR output exists; use --force to replace it: {args.output}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = export(args.path, args.output, args.source_lang, args.target_lang, args.game)
    print(f"TMX_UNITS={count} OUTPUT={args.output}")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
