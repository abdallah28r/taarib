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
