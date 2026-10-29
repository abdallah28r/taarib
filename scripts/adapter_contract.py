"""Run the adapter contract: prove extract -> rebuild -> read back on a copy.

    python scripts/adapter_contract.py --adapter adapters/renpy.py --game examples/renpy-reference

Checks, in order:
  rtl            the adapter declares how the engine shows Arabic; pre-shaping keeps code intact
  inventory      files exist under the game root
  extract        units validate, ids are unique, every unit's file is in the inventory
  deterministic  a second extract returns identical units
  read-back      the untouched game shows each unit's source
  identity       rebuilding with no targets changes no file
  round-trip     pseudo-Arabic targets rebuilt onto a copy read back exactly,
                 with the same ids and untouched files left byte-identical
  isolation      the game root is byte-identical after every step

All work happens in temporary directories, and only the adapter's inventory
files are copied or hashed, so a multi-gigabyte game stays cheap. A pass proves the adapter on this
game's files; it does not prove the game renders Arabic correctly.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage_core import digest, require_space

ROOT = Path(__file__).resolve().parents[1]


def load_base():
    if "loc_adapter_base" not in sys.modules:
        spec = importlib.util.spec_from_file_location("loc_adapter_base", ROOT / "adapters" / "base.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["loc_adapter_base"] = module
        spec.loader.exec_module(module)
    return sys.modules["loc_adapter_base"]


base = load_base()
loc_units = base.loc_units

PSEUDO_PREFIX = "تجربة «"
PSEUDO_SUFFIX = "» \"\\ نهاية"


def pseudo(source: str) -> str:
    """Arabic text that keeps every token and exercises quote/backslash escaping."""
    return f"{PSEUDO_PREFIX}{source}{PSEUDO_SUFFIX}"


def listing(root: Path) -> dict[str, tuple[int, int]]:
    """Size and modification time of every file: cheap enough for a multi-GB game."""
    found = {}
    for path in root.rglob("*"):
        if path.is_file():
            stat = path.stat()
            found[path.relative_to(root).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return found


def file_hashes(root: Path, paths) -> dict[str, str]:
    return {rel: digest(root / rel) for rel in paths if (root / rel).is_file()}


def same_bytes(first: Path, second: Path) -> bool:
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as left, second.open("rb") as right:
        while block := left.read(1 << 20):
            if block != right.read(len(block)):
                return False
    return True


class Result:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((name, ok, detail))
        return ok

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def run_contract(adapter_path: Path, game_root: Path, options: dict | None = None) -> Result:
    """Run every check; an exception inside the adapter fails the step it happened in."""
    result = Result()
    game_root = Path(game_root).resolve()
    before = listing(game_root)
    hashed: dict[str, str] = {}
    try:
        _run_checks(result, adapter_path, game_root, options, hashed)
    except Exception as exc:  # the adapter is untrusted code under test
        names = ("rtl", "inventory", "extract", "deterministic", "read-back", "identity", "round-trip")
        step = names[len(result.checks)] if len(result.checks) < len(names) else "contract"
        result.add(step, False, f"{type(exc).__name__}: {exc}")
    after = listing(game_root)
    changed = sorted(set(before) ^ set(after)) + [p for p in before if p in after and before[p] != after[p]]
    changed += [p for p, digest in file_hashes(game_root, hashed).items() if hashed[p] != digest]
    result.add("isolation", not changed, "" if not changed else f"game root was modified: {sorted(set(changed))[:3]}")
    return result


def _run_checks(result: Result, adapter_path: Path, game_root: Path, options: dict | None, hashed: dict) -> None:
    adapter = base.load_adapter(adapter_path, game_root, options)

    rtl_problem = ""
    if adapter.rtl not in ("native", "needs_preshape"):
        rtl_problem = f"rtl is {adapter.rtl!r}; declare native or needs_preshape from discovery evidence"
    elif adapter.rtl == "needs_preshape":
        sample = pseudo("Hello {name}, press [key] now")
        rendered = adapter.render(sample)
        if loc_units.tokens(rendered, adapter.token_profile) != loc_units.tokens(sample, adapter.token_profile):
            rtl_problem = "render() changed placeholders or tags"
        elif any("\u0621" <= ch <= "\u064A" for ch in rendered):
            rtl_problem = "render() left unshaped Arabic letters"
    if not result.add("rtl", not rtl_problem, rtl_problem or adapter.rtl):
        return

    inventory = adapter.inventory()
    missing = [p for p in inventory if not (game_root / p).is_file()]
    if not result.add("inventory", bool(inventory) and not missing,
                      f"{len(inventory)} files" if not missing else f"missing {missing[:3]}"):
        return
    hashed.update(file_hashes(game_root, inventory))

    units = adapter.extract()
    report = loc_units.validate([loc_units.UnitFile(Path("<extract>"), units)], adapter.token_profile)
    outside = sorted({u.get("file") for u in units} - set(inventory))
    problems = report.errors[:3] + ([f"files outside inventory: {outside[:3]}"] if outside else [])
    if not result.add("extract", bool(units) and not problems, f"{len(units)} units" if not problems else "; ".join(problems)):
        return

    result.add("deterministic", adapter.extract() == units, "second extract differs" if adapter.extract() != units else "")

    sources = {u["id"]: u["source"] for u in units}
    shown = adapter.read_back(game_root)
    result.add("read-back", shown == sources, "" if shown == sources else _diff(sources, shown))

    blank = [{**u, "target": ""} for u in units]
    inventory_bytes = sum((game_root / rel).stat().st_size for rel in inventory)
    with tempfile.TemporaryDirectory() as temporary:
        require_space(Path(temporary), inventory_bytes)
        out = Path(temporary) / "out"
        out.mkdir()
        written = adapter.rebuild(blank, out)
        changed = [p for p in written if not same_bytes(out / p, game_root / p)]
        result.add("identity", not changed, "" if not changed else f"changed without targets: {changed[:3]}")

    translatable = [u for u in units if loc_units.decision(u) != "keep"]
    targets = {u["id"]: pseudo(u["source"]) for u in translatable}
    with tempfile.TemporaryDirectory() as temporary:
        require_space(Path(temporary), inventory_bytes * 3)
        out, copy = Path(temporary) / "out", Path(temporary) / "game"
        out.mkdir()
        for rel in inventory:
            (copy / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(game_root / rel, copy / rel)
        written = adapter.rebuild([{**u, "target": targets.get(u["id"], "")} for u in units], out)
        escaped = [p for p in written if not (out / p).resolve().is_relative_to(out.resolve())]
        for rel in written:
            (copy / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / rel, copy / rel)
        expected = {**sources, **{ident: adapter.render(text) for ident, text in targets.items()}}
        shown = adapter.read_back(copy)
        after_ids = [u["id"] for u in base.load_adapter(adapter_path, copy, options).extract()]
        copied = file_hashes(copy, inventory)
        untouched = [p for p in inventory if p not in written and copied.get(p) != hashed[p]]
        problems = []
        if escaped:
            problems.append(f"wrote outside out_dir: {escaped[:3]}")
        if shown != expected:
            problems.append(_diff(expected, shown))
        if after_ids != [u["id"] for u in units]:
            problems.append("ids changed after rebuild")
        if untouched:
            problems.append(f"unwritten files changed: {untouched[:3]}")
        result.add("round-trip", not problems, f"{len(targets)} targets, {len(written)} files" if not problems else "; ".join(problems))


def _diff(expected: dict, actual: dict) -> str:
    missing = [k for k in expected if k not in actual]
    wrong = [k for k in expected if k in actual and actual[k] != expected[k]]
    extra = [k for k in actual if k not in expected]
    parts = [f"{label}={ids[:3]}" for label, ids in (("missing", missing), ("wrong", wrong), ("extra", extra)) if ids]
    return "read-back mismatch " + " ".join(parts)


def parse_options(values: list[str]) -> dict:
    options = {}
    for value in values:
        key, sep, item = value.partition("=")
        if not sep:
            raise argparse.ArgumentTypeError(f"--option needs key=value, got {value!r}")
        options[key] = item
    return options


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--option", action="append", default=[], help="adapter option key=value")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
    result = run_contract(args.adapter, args.game, parse_options(args.option))
    for name, ok, detail in result.checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
    print(f"ADAPTER_CONTRACT={'PASS' if result.ok else 'FAIL'}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
