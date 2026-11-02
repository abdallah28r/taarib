import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


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


def load_script_from(path):
    spec = importlib.util.spec_from_file_location(f"loaded_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shaping = load_script("arabic_shaping")
contract = load_script("adapter_contract")
loc = load_script("loc")
tools = load_script("loc_tools")
units = load_script("loc_units")
pipeline = load_script("loc_pipeline")

SUBCLASS = """
import importlib.util
spec = importlib.util.spec_from_file_location("renpy_under_test", {renpy!r})
renpy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renpy)
class Variant(renpy.RenpyAdapter):
    rtl = {rtl!r}
{body}
ADAPTER = Variant
"""


def codepoints(text):
    return [hex(ord(c)) for c in text]


class ShapingTests(unittest.TestCase):
    def test_contextual_forms_come_from_unicode(self):
        self.assertEqual(codepoints(shaping.shape("سلام")), ["0xfeb3", "0xfefc", "0xfee1"])  # lam-alef ligature

    def test_hamza_does_not_join_back(self):
        self.assertEqual(codepoints(shaping.shape("شيء")), ["0xfeb7", "0xfef2", "0xfe80"])

    def test_diacritics_are_kept_and_do_not_break_joining(self):
        self.assertEqual(codepoints(shaping.shape("بِسْمِ")), ["0xfe91", "0x650", "0xfeb4", "0x652", "0xfee2", "0x650"])

    def test_render_keeps_code_and_latin_and_line_order(self):
        rendered = shaping.render("اضغط [key] على Start (الآن)\nسطر")
        first, second = rendered.split("\n")
        self.assertTrue(first.startswith("("))  # the closing bracket now comes first, mirrored
        self.assertIn("[key]", first)
        self.assertIn("Start", first)
        self.assertEqual(second, shaping.shape("سطر")[::-1])
        self.assertFalse(any("ء" <= ch <= "ي" for ch in rendered))

    def test_numbers_stay_whole_and_signs_follow_the_bidi_algorithm(self):
        self.assertIn("٢٥", shaping.render("المستوى ٢٥ الآن"))
        self.assertIn("50%", shaping.render("حصلت على 50% من الذهب"))
        self.assertIn("3:26", shaping.render("الوقت 3:26"))
        self.assertIn("MEMORY CARD 1", shaping.render("بطاقة MEMORY CARD 1 جاهزة"))
        self.assertTrue(shaping.render("+25 هجوم").endswith("25+"))  # as a renderer that supports Arabic shows it

    def test_paired_tags_stay_opening_before_closing(self):
        rendered = shaping.render("اضغط <color=red>زر البدء</color> الآن")
        self.assertLess(rendered.index("<color=red>"), rendered.index("</color>"))
        self.assertEqual(rendered[rendered.index(">") + 1:rendered.index("</")], shaping.shape("زر البدء")[::-1])
        nested = shaping.render("<b>تحذير <i>مهم</i></b>")
        self.assertTrue(nested.startswith("<b><i>") and nested.endswith("</b>"))
        self.assertIn("[key]", shaping.render("بعد [b]قليل[/b] [key]"))

    def test_shape_options(self):
        pause = __import__("re").compile(r"\^\d")
        self.assertEqual(codepoints(shaping.shape("اسم^5ك", transparent=pause))[-1], "0xfeda")  # kaf stays joined
        self.assertIn("^5", shaping.render("اسم^5ك", transparent=pause))
        self.assertEqual(codepoints(shaping.shape("بِسْمِ", strip_harakat=True)), ["0xfe91", "0xfeb4", "0xfee2"])
        self.assertEqual(len(shaping.shape("لا", lam_alef=False)), 2)
        self.assertEqual(shaping.glyphs_used(["ﻻ {name}"]), {"ﻻ"})

    def test_wrap_measures_shaped_text_keeps_reading_order_and_balances(self):
        text = " ".join(f"كلمة{i}" for i in range(1, 31))
        lines = shaping.wrap(text, 40, len)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(len(shaping.shape(line)) <= 40 for line in lines))
        self.assertTrue(lines[0].startswith("كلمة1 ") and lines[-1].endswith("كلمة30"))
        self.assertEqual(" ".join(lines), text)
        self.assertGreater(len(lines[-1].split()), 1)  # no lone last word
        self.assertEqual(shaping.wrap("قصير\nثانٍ", 40, len), ["قصير", "ثانٍ"])
        self.assertEqual(shaping.wrap("قال {player name} مرحبا", 6, len)[1], "{player name}")  # codes never split

    def test_adapter_render_wraps_with_its_options(self):
        base = load_script_from(ROOT / "adapters" / "base.py")

        class Boxed(base.Adapter):
            rtl = "needs_preshape"
        adapter = Boxed(Path("."), {"line_width": 8, "boxes": {"choice": 40}, "line_sep": "|"})
        self.assertEqual(adapter.render("سطر أول طويل جدا هنا").count("|"), 2)
        self.assertNotIn("|", adapter.render("سطر أول طويل جدا هنا", box="choice"))
        self.assertNotIn("|", Boxed(Path("."), {}).render("سطر أول طويل جدا هنا"))

    def test_render_wraps_before_reversing(self):
        rendered = shaping.render("سطر أول طويل جدا هنا", max_width=8, measure=len, line_sep="|")
        first = rendered.split("|")[0]
        self.assertEqual(first, shaping.reorder(shaping.shape("سطر أول")))


class RtlContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def adapter(self, rtl, body="    pass"):
        path = self.dir / f"variant_{rtl}.py"
        path.write_text(SUBCLASS.format(renpy=str(RENPY), rtl=rtl, body=body), encoding="utf-8")
        return path

    def test_preshaped_adapter_passes_the_whole_contract(self):
        result = contract.run_contract(self.adapter("needs_preshape"), REFERENCE)
        self.assertTrue(result.ok, result.checks)

    def test_undeclared_capability_fails_first(self):
        result = contract.run_contract(self.adapter("unknown"), REFERENCE)
        self.assertFalse(result.ok)
        self.assertEqual(result.checks[0][:2], ("rtl", False))

    def test_render_that_breaks_tokens_fails(self):
        body = "    def render(self, target):\n        return target.replace('{', '(').replace('}', ')')"
        result = contract.run_contract(self.adapter("needs_preshape", body), REFERENCE)
        self.assertIn(("rtl", False, "render() changed placeholders or tags"), result.checks)


class DiscoveryGateTests(unittest.TestCase):
    def test_discovery_requires_a_declared_rtl_capability(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            adapter = folder / "variant.py"
            adapter.write_text(SUBCLASS.format(renpy=str(RENPY), rtl="unknown", body="    pass"), encoding="utf-8")
            project_file = folder / "PROJECT.yaml"
            data = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8"))
            data.setdefault("workflow", {})["adapter"] = str(adapter)
            project_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            project = pipeline.Project(project_file=project_file, state_file=folder / "s.json")
            checks = pipeline.check_discovery(project, project.settings(), project.state())
            self.assertIn((False, "المحوّل يعلن طريقة عرض العربية من دليل الاكتشاف: native أو needs_preshape "
                                  "(الآن: unknown)"), checks)
            data["workflow"]["adapter"] = str(RENPY)
            project_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            checks = pipeline.check_discovery(project, project.settings(), project.state())
            self.assertTrue(checks[-1][0], checks)


class NeedsRewriteTests(unittest.TestCase):
    def test_changed_source_with_old_arabic_is_flagged_and_counted(self):
        unit = units.new_unit("u", "f", "Open the gate", status="extracted", previous_target="افتح الباب")
        self.assertIn("needs_rewrite", tools.unit_problems([unit], None, "generic", "western").get("u", []))
        self.assertEqual(loc.compute([unit])["all"]["rewrite"], 1)


class DashboardFixesTests(unittest.TestCase):
    def test_fixes_are_listed_on_the_phase_card(self):
        state = {"phase": "playtest", "history": [],
                 "fixes": [{"id": "F-001", "title": "سطر مقصوص", "status": "open", "ids": ["u"]},
                           {"id": "F-002", "title": "تحية", "status": "closed", "verdict": "verified", "ids": ["v"]}]}
        page = loc.phase_html(state, [])
        self.assertIn("الإصلاحات السريعة", page)
        self.assertIn("F-001 — سطر مقصوص — مفتوح", page)
        self.assertIn("F-002 — تحية — verified", page)


if __name__ == "__main__":
    unittest.main()
