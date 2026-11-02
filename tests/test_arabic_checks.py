import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tools = load_script("loc_tools")
units = load_script("loc_units")
pipeline = load_script("loc_pipeline")


def codes(source, target, glossary=None, digits="western", **fields):
    unit = units.new_unit("u", "f", source, target=target, status="translated", **fields)
    return tools.unit_problems([unit], glossary, "generic", digits).get("u", [])


class ArabicCheckTests(unittest.TestCase):
    def test_digits_follow_the_project_policy(self):
        self.assertIn("digit_style", codes("Score 1500", "النتيجة ١٥٠٠"))
        self.assertNotIn("digit_style", codes("Score 1500", "النتيجة 1500"))
        self.assertIn("digit_style", codes("Score 1500", "النتيجة 1500", digits="arabic-indic"))
        self.assertNotIn("digit_style", codes("Score 1500", "النتيجة ١٥٠٠", digits="arabic-indic"))

    def test_numbers_must_survive_but_small_ones_may_be_words(self):
        self.assertIn("number_mismatch", codes("Lose 25 HP", "تخسر 30 نقطة صحة"))
        self.assertNotIn("number_mismatch", codes("Take 3 keys", "خذ ثلاثة مفاتيح"))
        self.assertNotIn("number_mismatch", codes("Costs 1,500 gold", "يكلف 1500 ذهبة"))
        self.assertNotIn("number_mismatch", codes("Costs 1500 gold", "يكلف ١٥٠٠ ذهبة"))

    def test_reversed_text(self):
        self.assertIn("reversed_text", codes("The table is on the book", "باتكلا ىلع ةلواطلا"))
        self.assertNotIn("reversed_text", codes("The table is on the book", "الطاولة على الكتاب في المدرسة"))

    def test_endings(self):
        self.assertIn("end_punctuation", codes("Ready?", "جاهز."))
        self.assertNotIn("end_punctuation", codes("Ready?", "جاهز؟"))
        self.assertNotIn("end_punctuation", codes("Wait...", "انتظر…"))
        self.assertNotIn("end_punctuation", codes('He said "go."', "قال «اذهب.»"))
        self.assertIn("end_punctuation", codes("Start", "ابدأ."))

    def test_latin_punctuation_next_to_arabic(self):
        self.assertIn("latin_punctuation", codes("Yes, go", "نعم, اذهب"))
        self.assertNotIn("latin_punctuation", codes("Yes, go", "نعم، اذهب"))
        self.assertNotIn("latin_punctuation", codes("Costs 1,500", "يكلف 1,500"))

    def test_whitespace(self):
        self.assertIn("whitespace", codes("Save", "حفظ "))
        self.assertIn("whitespace", codes("Hello.", "مرحبًا ."))
        self.assertIn("whitespace", codes("Go home", "اذهب  للبيت"))
        self.assertNotIn("whitespace", codes("Hello, {player}!", "مرحبًا يا {player}!"))
        self.assertNotIn("whitespace", codes(" Indented", " مزاح"))

    def test_doubled_words_and_invisible_characters(self):
        self.assertIn("doubled_word", codes("Go now", "اذهب اذهب الآن"))
        self.assertNotIn("doubled_word", codes("No no no", "لا لا لا"))
        self.assertIn("invisible_chars", codes("Wait", "انتظر​"))

    def test_forbidden_terms_and_their_exception(self):
        glossary = {"forbidden": {"قام ب": "use the verb directly"}}
        self.assertIn("forbidden_term", codes("Close", "قام بإغلاق الباب", glossary))
        self.assertNotIn("forbidden_term", codes("Close", "أغلق الباب", glossary))
        self.assertNotIn("forbidden_term", codes("Close", "قام بإغلاق الباب", glossary, term_exceptions=["قام ب"]))
        self.assertEqual(tools.level("forbidden_term"), "error")

    def test_level_overrides(self):
        self.assertEqual(tools.level("latin_leak"), "warning")
        self.assertEqual(tools.level("latin_leak", {"latin_leak": "error"}), "error")
        self.assertEqual(tools.level("glossary_term_missing", {"glossary_term_missing": "nonsense"}), "error")

    def test_every_code_is_documented(self):
        reference = (ROOT / "references" / "problem-codes.md").read_text(encoding="utf-8")
        missing = [code for code in tools.PROBLEM_CODES if f"`{code}`" not in reference]
        self.assertEqual(missing, [])


class GateTests(unittest.TestCase):
    def test_promoted_warning_blocks_localization(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            unit_dir = directory / "units"
            unit_dir.mkdir()
            unit = units.new_unit("a", "f", "Open the door", target="افتح door", status="proofread",
                                  translated_by="t", proofread_by="p")
            unit["proofread_hash"] = units.source_hash(unit["target"])
            units.write(units.UnitFile(unit_dir / "u.jsonl", [unit]))
            project_file = directory / "PROJECT.yaml"
            plan = directory / "PLAN.md"
            plan.write_text("## الدفعات\n- [x] b1\n", encoding="utf-8")
            project_file.write_text(yaml.safe_dump({"game": {}, "qa": {"levels": {}}}), encoding="utf-8")
            project = pipeline.Project(project_file=project_file, units_dir=unit_dir,
                                       state_file=directory / "s.json", qa_file=directory / "q.csv", plan_file=plan)
            ok = lambda: all(passed for passed, _ in pipeline.check_localization(project, project.settings(), {}))
            self.assertTrue(ok())
            project_file.write_text(yaml.safe_dump({"game": {}, "qa": {"levels": {"latin_leak": "error"}}}),
                                    encoding="utf-8")
            self.assertFalse(ok())
            messages = [m for passed, m in pipeline.check_localization(project, project.settings(), {}) if not passed]
            self.assertIn("latin_leak=1", messages[0])


if __name__ == "__main__":
    unittest.main()
