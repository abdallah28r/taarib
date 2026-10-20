import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
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


loc = load_script("loc")
tools = load_script("loc_tools")
units = load_script("loc_units")


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = loc.main(list(argv))
    return code, out.getvalue()


class MergeUpdateTests(unittest.TestCase):
    def unit(self, ident, source, **fields):
        return units.new_unit(ident, "f.txt", source, **fields)

    def test_merge_rules(self):
        current = [
            self.unit("same", "Save", target="حفظ", status="translated", translated_by="t"),
            self.unit("changed", "Load", target="تحميل", status="translated", translated_by="t"),
            self.unit("context", "Back", target="رجوع", status="translated", context={"speaker": "a"}),
            self.unit("gone", "Old line", target="سطر قديم", status="translated"),
            units.new_unit("img#1", "title.png", "START", kind="image", asset="title.png", box=[0, 0, 5, 5]),
        ]
        fresh = [
            self.unit("same", "Save"),
            self.unit("changed", "Load game"),
            self.unit("context", "Back", context={"speaker": "b"}),
            self.unit("new", "New line"),
        ]
        merged, report = tools.merge_update(current, fresh, {"f.txt"})
        by_id = {u["id"]: u for u in merged}
        self.assertEqual(by_id["same"]["target"], "حفظ")
        self.assertEqual(by_id["changed"]["status"], "extracted")
        self.assertEqual(by_id["changed"]["previous_target"], "تحميل")
        self.assertNotIn("target", by_id["changed"])
        self.assertEqual(by_id["context"]["previous_target"], "رجوع")
        self.assertIn("img#1", by_id)
        self.assertNotIn("gone", by_id)
        self.assertEqual((report["unchanged"], report["changed"], report["added"], report["removed"], report["kept_other"]),
                         (1, ["changed", "context"], ["new"], ["gone"], 1))
        self.assertEqual(units.validate([units.UnitFile(Path("m.jsonl"), merged)]).errors, [])

    def test_update_command_on_reference_game(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            game = directory / "game"
            shutil.copytree(REFERENCE, game)
            path = directory / "u.jsonl"
            run("extract", "--adapter", str(RENPY), "--game", str(game), "--out", str(path))
            tl = game / "game" / "tl" / "arabic" / "script.rpy"
            tl.write_text(tl.read_text(encoding="utf-8").replace("Then we run.", "Then we hide."), encoding="utf-8")
            code, out = run("update", "--adapter", str(RENPY), "--game", str(game), "--path", str(path), "--dry-run")
            self.assertEqual(code, 0, out)
            self.assertIn("UNCHANGED=7 CHANGED=1 ADDED=0 REMOVED=0", out)
            self.assertIn("DRY_RUN", out)


class OtherToolTests(unittest.TestCase):
    def test_estimate_counts_arabic_heavier_than_latin(self):
        self.assertGreater(tools.estimate_text("مرحبا بك"), tools.estimate_text("abcdefgh"))
        pending = [units.new_unit("a", "f", "Hello world"), units.new_unit("b", "f", "Hi", target="أهلًا")]
        report = tools.estimate(pending, 4000, 1200, 1.35)
        self.assertEqual(report["units_to_translate"], 1)
        self.assertEqual(report["estimated_batches"], 1)

    def test_tmx_exports_only_proofread_units(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "m.tmx"
            code, text = run("tmx", "--path", str(ROOT / "tests" / "fixtures" / "units"), "--out", str(out))
            self.assertEqual(code, 0, text)
            tus = ET.parse(out).getroot().find("body").findall("tu")
        self.assertEqual(sorted(tu.get("tuid") for tu in tus), ["dlg/ch1#001", "ui/menu#continue", "ui/menu#new_game"])

    def test_pseudo_build_keeps_tokens_and_stays_outside_the_game(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            game = directory / "game"
            shutil.copytree(REFERENCE, game)
            code, _ = run("pseudo", "--adapter", str(RENPY), "--game", str(game), "--out", str(game / "x"))
            self.assertEqual(code, 2)
            code, _ = run("pseudo", "--adapter", str(RENPY), "--game", str(game), "--out", str(directory / "p"))
            self.assertEqual(code, 0)
            text = (directory / "p" / "game" / "tl" / "arabic" / "script.rpy").read_text(encoding="utf-8")
        self.assertIn('e "نص عربي تجريبي: Welcome to the station, [player_name]."', text)


class DashboardTests(unittest.TestCase):
    def test_dashboard_combines_phase_progress_and_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            plan = directory / "PLAN.md"
            plan.write_text("# خطة\n\n## القرارات\n- [x] Case = القضية\n<!-- PRIVATE-NOTE-XYZ -->\n<b>x</b>\n", encoding="utf-8")
            project = loc.pipeline.Project(units_dir=ROOT / "tests" / "fixtures" / "units",
                                           state_file=directory / "state.json", qa_file=directory / "qa.csv")
            out = loc.write_dashboard(project.units_dir, project.qa_file, directory / "d.html", project, plan)
            page = out.read_text(encoding="utf-8")
        self.assertIn('<meta http-equiv="refresh" content="15">', page)
        self.assertIn('<li class="now">الاستقبال</li>', page)
        self.assertIn('aria-valuenow="83"', page)
        self.assertIn("<li>☑ Case = القضية</li>", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)
        self.assertNotIn("PRIVATE-NOTE-XYZ", page)

    def test_auto_dashboard_ignores_test_paths(self):
        before = loc.DASHBOARD.stat().st_mtime_ns if loc.DASHBOARD.exists() else None
        loc.auto_dashboard(Path(tempfile.gettempdir()) / "elsewhere.jsonl")
        after = loc.DASHBOARD.stat().st_mtime_ns if loc.DASHBOARD.exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
