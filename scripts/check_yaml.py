"""Strictly load project YAML files and reject keys that PyYAML would corrupt.

PyYAML follows YAML 1.1: unquoted Yes/No/On/Off/Y/N/True/False keys become
booleans, numbers become ints/floats, and a repeated key silently overwrites
the earlier one. In a glossary that means lost terms with no error. This check
fails on any non-string mapping key and on any duplicate key.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [
    "PROJECT.yaml",
    "glossary.yaml",
    "config/image-localization-policy.yaml",
    "loc-kit/CHARACTERS.yaml",
]


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that records problems instead of silently coercing keys."""

    def __init__(self, stream):
        super().__init__(stream)
        self.problems: list[str] = []

    def construct_mapping(self, node, deep=False):
        seen: dict[object, int] = {}
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            line = key_node.start_mark.line + 1
            if not isinstance(key, str):
                self.problems.append(
                    f"line {line}: key {key_node.value!r} loads as {type(key).__name__} {key!r}; quote it"
                )
            try:
                if key in seen:
                    self.problems.append(
                        f"line {line}: duplicate key {key_node.value!r} (first at line {seen[key]})"
                    )
                else:
                    seen[key] = line
            except TypeError:
                self.problems.append(f"line {line}: unhashable key {key_node.value!r}")
        return super().construct_mapping(node, deep=deep)


def check_file(path: Path) -> list[str]:
    loader = StrictLoader(path.read_text(encoding="utf-8-sig"))
    try:
        loader.get_single_data()
    except yaml.YAMLError as exc:
        return [f"parse error: {exc}"]
    finally:
        loader.dispose()
    return loader.problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="defaults to the template's YAML files")
    args = parser.parse_args(argv)
    paths = args.paths or [ROOT / name for name in DEFAULT_FILES]
    failed = 0
    for path in paths:
        if not path.is_file():
            print(f"ERROR {path}: missing")
            failed += 1
            continue
        problems = check_file(path)
        for problem in problems:
            print(f"ERROR {path}: {problem}")
        failed += bool(problems)
    print(f"YAML_FILES={len(paths)} FAILED={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
