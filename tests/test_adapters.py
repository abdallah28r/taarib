import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "renpy-reference"
RENPY = ROOT / "adapters" / "renpy.py"


def load_script(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load_script("adapter_contract")
loc = load_script("loc")
base = contract.base

BROKEN = """
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("renpy_under_test", {renpy!r})
renpy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renpy)
{body}
"""


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = loc.main(list(argv))
    return code, out.getvalue()


class TempGame(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)
        self.game = self.dir / "game-root"
        shutil.copytree(REFERENCE, self.game)

    def tearDown(self):
        self.temporary.cleanup()

    def broken_adapter(self, body):
        path = self.dir / "broken.py"
        path.write_text(BROKEN.format(renpy=str(RENPY), body=body), encoding="utf-8")
        return path

    def checks(self, adapter_path):
        return {name: ok for name, ok, _ in contract.run_contract(adapter_path, self.game).checks}


class RenpyAdapterTests(TempGame):
    def test_contract_passes_on_reference_game(self):
        result = contract.run_contract(RENPY, REFERENCE)
        self.assertTrue(result.ok, result.checks)
        self.assertEqual([name for name, _, _ in result.checks],
                         ["inventory", "extract", "deterministic", "read-back", "identity", "round-trip", "isolation"])

    def test_extracted_units(self):
        units = base.load_adapter(RENPY, self.game).extract()
        by_key = {u["key"]: u for u in units if u["key"] != "strings"}
        strings = [u for u in units if u["key"] == "strings"]
        self.assertEqual(len(units), 8)
        self.assertEqual(sorted(u["source"] for u in strings), ["Open the door", "Saved", "Wait here"])
        self.assertEqual(by_key["start_3d9b07a4"]["context"]["speaker"], "narrator")
        self.assertEqual(by_key["start_8a2f6c1e"]["context"],
                         {"speaker": "e", "source_location": "game/script.rpy:7", "label": "start"})
        self.assertEqual(by_key["open_door_5f0a9d33"]["source"], 'The door is "locked" from the inside.')
        self.assertTrue(all(u["status"] == "extracted" and "target" not in u for u in units))

    def test_existing_translation_is_picked_up(self):
        path = self.game / "game" / "tl" / "arabic" / "script.rpy"
        text = path.read_text(encoding="utf-8").replace('new "Saved"', 'new "تم الحفظ"')
        path.write_text(text, encoding="utf-8")
        saved = [u for u in base.load_adapter(RENPY, self.game).extract() if u["source"] == "Saved"][0]
        self.assertEqual((saved["target"], saved["status"], saved["translated_by"]),
                         ("تم الحفظ", "translated", "existing-tl"))

    def test_unsupported_multiline_string_fails_loudly(self):
        path = self.game / "game" / "tl" / "arabic" / "script.rpy"
        text = path.read_text(encoding="utf-8").replace('"We wait. Then we run."\n', '"We wait.\n', 1)
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"script\.rpy:\d+"):
            base.load_adapter(RENPY, self.game).extract()


class ContractCatchesBrokenAdapters(TempGame):
    def test_missing_escaping_fails_round_trip(self):
        path = self.broken_adapter("renpy.escape = lambda text: text\nADAPTER = renpy.RenpyAdapter")
        checks = self.checks(path)
        self.assertFalse(checks.get("round-trip", True))

    def test_writing_into_game_root_fails_isolation(self):
        body = (
            "class Leaky(renpy.RenpyAdapter):\n"
            "    def rebuild(self, units, out_dir):\n"
            "        (self.game_root / 'leak.txt').write_text('x')\n"
            "        return super().rebuild(units, out_dir)\n"
            "ADAPTER = Leaky\n"
        )
        checks = self.checks(self.broken_adapter(body))
        self.assertFalse(checks["isolation"])

    def test_unstable_ids_fail(self):
        body = (
            "import itertools\n"
            "counter = itertools.count()\n"
            "class Unstable(renpy.RenpyAdapter):\n"
            "    def extract(self):\n"
            "        units = super().extract()\n"
            "        units[0] = {**units[0], 'id': f'random-{next(counter)}'}\n"
            "        return units\n"
            "ADAPTER = Unstable\n"
        )
        self.assertFalse(self.checks(self.broken_adapter(body))["deterministic"])


class ExtractRebuildCommandTests(TempGame):
    def test_extract_then_rebuild_only_proofread_units(self):
        units_file = self.dir / "units" / "ref.jsonl"
        self.assertEqual(run("extract", "--adapter", str(RENPY), "--game", str(self.game),
                             "--out", str(units_file))[0], 0)
        rows = [json.loads(line) for line in units_file.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            if row["source"] == "Open the door":
                row.update(target="افتح الباب", status="translated", translated_by="translator-1")
            if row["source"] == "Wait here":
                row.update(target="انتظر هنا", status="translated", translated_by="translator-1")
        units_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        open_door = next(r["id"] for r in rows if r["source"] == "Open the door")
        self.assertEqual(run("mark", "--path", str(units_file), "--ids", open_door,
                             "--status", "proofread", "--by", "proofreader-1")[0], 0)

        out = self.dir / "build"
        code, text = run("rebuild", "--adapter", str(RENPY), "--game", str(self.game),
                         "--out", str(out), "--path", str(units_file))
        self.assertEqual(code, 0, text)
        self.assertIn("UNITS_INCLUDED=1 HELD_BACK=1", text)
        built = (out / "game" / "tl" / "arabic" / "script.rpy").read_text(encoding="utf-8")
        self.assertIn('new "افتح الباب"', built)
        self.assertIn('new "Wait here"', built)

    def test_extract_refuses_to_overwrite(self):
        units_file = self.dir / "ref.jsonl"
        units_file.write_text("", encoding="utf-8")
        code, _ = run("extract", "--adapter", str(RENPY), "--game", str(self.game), "--out", str(units_file))
        self.assertEqual(code, 1)

    def test_rebuild_refuses_output_inside_game(self):
        code, _ = run("rebuild", "--adapter", str(RENPY), "--game", str(self.game),
                      "--out", str(self.game / "build"), "--path", str(self.dir / "none"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
