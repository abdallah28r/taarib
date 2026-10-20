import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
registry = load_script("check_project_scripts")

GLOSSARY = {
    "general": {"Save": "حفظ", "Settings": "الإعدادات", "Main Menu": "القائمة الرئيسية", "Load Game": "تحميل لعبة",
                "Load": "تحميل", "Yes": "نعم"},
    "names": {"Mara": "مارا"},
    "keep_latin": ["ACME", "[عنوان اللعبة]"],
    "context_rules": [{"term": "Continue", "contexts": {"menu_resume": "استئناف", "menu_story": "متابعة"}}],
}


def unit(ident, source, target, **fields):
    return units.new_unit(ident, "f", source, target=target, status="translated", **fields)


class GlossaryConformanceTests(unittest.TestCase):
    def problems(self, *rows):
        return [(i, t) for i, t, _ in tools.check_terms(list(rows), GLOSSARY)]

    def test_inflected_and_article_forms_match(self):
        self.assertEqual(self.problems(
            unit("a", "Open Settings", "افتح الإعدادات"),
            unit("b", "Back to the Main Menu", "عودة للقائمة الرئيسية"),
            unit("c", "Settings", "بالإعداداتِ"),
        ), [])

    def test_wrong_term_is_reported(self):
        self.assertEqual(self.problems(unit("a", "Save your game", "خزّن لعبتك")), [("a", "Save")])

    def test_longest_term_wins_and_context_forms_are_accepted(self):
        self.assertEqual(self.problems(
            unit("a", "Load Game", "تحميل لعبة"),
            unit("b", "Continue", "استئناف"),
            unit("c", "Continue", "متابعة"),
        ), [])

    def test_word_boundaries_and_case(self):
        self.assertEqual(self.problems(unit("a", "Saved", "تم"), unit("b", "SAVE", "حفظ")), [])

    def test_names_and_keep_latin(self):
        self.assertEqual(self.problems(
            unit("a", "Mara waits", "مارا تنتظر"),
            unit("b", "ACME store", "متجر ACME"),
            unit("c", "ACME store", "متجر أكمي"),
        ), [("c", "ACME")])

    def test_exceptions_and_untranslated_units_are_skipped(self):
        self.assertEqual(self.problems(
            unit("a", "Save", "احفظ", term_exceptions=["Save"]),
            units.new_unit("b", "f", "Save"),
            unit("c", "Save", "x", decision="keep"),
        ), [])

    def test_allow_command_records_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "u.jsonl"
            units.write(units.UnitFile(path, [unit("a", "Back", "ارجع")]))
            glossary = Path(directory) / "g.yaml"
            glossary.write_text('general:\n  Back: رجوع\n', encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(loc.main(["terms", "--path", str(path), "--glossary", str(glossary)]), 1)
                self.assertEqual(loc.main(["terms", "--path", str(path), "--allow", "a", "Back"]), 0)
                self.assertEqual(loc.main(["terms", "--path", str(path), "--glossary", str(glossary)]), 0)
            self.assertIn("TERM_PROBLEMS=1", out.getvalue())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["term_exceptions"], ["Back"])


class ScriptRegistryTests(unittest.TestCase):
    def test_template_registry_is_valid_and_empty(self):
        self.assertEqual(registry.validate(), [])
        self.assertEqual(registry.summary(), [])

    def test_entries_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "work" / "tools").mkdir(parents=True)
            (root / "work" / "tools" / "pack.py").write_text("print(1)\n", encoding="utf-8")
            good = {"name": "pack", "path": "work/tools/pack.py", "purpose": "repack archives",
                    "usage": "python work/tools/pack.py <dir>", "tested": "ran on chapter 1", "reusable": False}
            path = root / "registry.json"
            path.write_text(json.dumps({"scripts": [good]}), encoding="utf-8")
            self.assertEqual(registry.validate(path, root), [])
            self.assertEqual(registry.summary(path), ["- pack: repack archives → python work/tools/pack.py <dir>"])
            bad = [dict(good, path="C:/elsewhere/x.py"), dict(good, name="b", path="work/tools/missing.py"),
                   {"name": "c", "path": "work/tools/pack.py"}]
            path.write_text(json.dumps({"scripts": bad}), encoding="utf-8")
            errors = registry.validate(path, root)
        self.assertTrue(any("must be under" in e for e in errors))
        self.assertTrue(any("does not exist" in e for e in errors))
        self.assertTrue(any("missing purpose" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
