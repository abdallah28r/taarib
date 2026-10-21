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
FIXTURE = ROOT / "tests" / "fixtures" / "units" / "sample.jsonl"


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


class BatchAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)
        self.units = self.dir / "u.jsonl"
        shutil.copyfile(FIXTURE, self.units)

    def tearDown(self):
        self.temporary.cleanup()

    def answer(self, data):
        path = self.dir / "answer.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def apply(self, data, *extra):
        return run("apply", str(self.answer(data)), "--path", str(self.units), "--by", "translator-9", *extra)

    def unit(self, ident):
        for line in self.units.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["id"] == ident:
                return row
        raise KeyError(ident)

    def test_missing_extra_and_empty_ids_reject_the_whole_batch(self):
        before = self.units.read_bytes()
        code, out = self.apply({"dlg/ch1#001": "مرحبًا يا {player}!", "dlg/ch1#002": "",
                                "ghost#9": "زائد"}, "--batch", "batch-002")
        self.assertEqual(code, 1)
        self.assertIn("MISSING (1): dlg/ch1#003", out)
        self.assertIn("EXTRA (1): ghost#9", out)
        self.assertIn("EMPTY (1): dlg/ch1#002", out)
        self.assertIn("NOT_WRITTEN", out)
        self.assertEqual(self.units.read_bytes(), before)

    def test_full_answer_is_applied_and_resets_changed_proofreading(self):
        code, out = self.apply([{"id": "dlg/ch1#001", "target": "أهلًا يا {player}!"},
                                {"id": "dlg/ch1#002", "target": "انتبه."},
                                {"id": "dlg/ch1#003", "target": "لم أقل ذلك قط."}], "--batch", "batch-002")
        self.assertEqual(code, 0, out)
        changed = self.unit("dlg/ch1#001")
        self.assertEqual((changed["status"], changed["translated_by"]), ("translated", "translator-9"))
        self.assertNotIn("proofread_hash", changed)
        self.assertEqual(self.unit("dlg/ch1#003")["target"], "لم أقل ذلك قط.")

    def test_unchanged_text_keeps_its_proofreading(self):
        code, _ = self.apply({"dlg/ch1#001": "مرحبًا يا {player}!"}, "--ids", "dlg/ch1#001")
        self.assertEqual(code, 0)
        self.assertEqual(self.unit("dlg/ch1#001")["status"], "proofread")

    def test_token_errors_are_refused(self):
        code, out = self.apply({"dlg/ch1#001": "مرحبًا!"}, "--ids", "dlg/ch1#001")
        self.assertEqual(code, 1)
        self.assertIn("token mismatch", out)

    def test_answer_format_errors(self):
        for bad in ('["x"]', '{"a": 1}', '"text"'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tools.parse_batch_output(bad)
        with self.assertRaises(ValueError):
            tools.parse_batch_output('[{"id": "a", "target": "x"}, {"id": "a", "target": "y"}]')


class ProblemCodeTests(unittest.TestCase):
    def codes(self, unit, glossary=None):
        return tools.unit_problems([unit], glossary).get(unit["id"], [])

    def test_each_warning_code(self):
        make = lambda source, target, **f: units.new_unit("u", "f", source, target=target, status="translated", **f)
        self.assertIn("untranslated", self.codes(make("Open the door", "Open the door")))
        self.assertIn("lost_newline", self.codes(make("Line one\nLine two", "سطر واحد")))
        self.assertIn("latin_leak", self.codes(make("Open the door", "افتح the باب")))
        self.assertNotIn("latin_leak", self.codes(make("Visit ACME", "زر ACME"), {"keep_latin": ["ACME"]}))
        self.assertNotIn("latin_leak", self.codes(make("Hi [player_name]", "أهلًا [player_name]")))
        self.assertIn("too_long", self.codes(make("Save", "حفظ اللعبة", max_length=3)))
        self.assertIn("unicode_form", self.codes(make("Save", "حفـظ")))
        self.assertIn("persian_letters", self.codes(make("Hello", "سلام دوستی")))
        self.assertIn("glossary_term_missing", self.codes(make("Save", "خزّن"), {"general": {"Save": "حفظ"}}))

    def test_error_codes_match_validation(self):
        broken = units.new_unit("u", "f", "Hi {name}", target="أهلًا", status="translated")
        empty = units.new_unit("e", "f", "Hi", status="translated")
        self.assertIn("token_mismatch", self.codes(broken))
        self.assertIn("missing_target", self.codes(empty))
        for code, (level, _) in tools.PROBLEM_CODES.items():
            self.assertIn(level, ("error", "warning"), code)

    def test_clean_fixture_has_no_errors(self):
        rows = units.all_units(units.load(FIXTURE))
        counts = tools.problem_counts(tools.unit_problems(rows))
        self.assertFalse([c for c in counts if tools.PROBLEM_CODES[c][0] == "error"], counts)

    def test_search_by_problem_lists_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "u.jsonl"
            units.write(units.UnitFile(path, [
                units.new_unit("leak", "f", "Open", target="افتح door", status="translated"),
                units.new_unit("fine", "f", "Open", target="افتح", status="translated"),
            ]))
            code, out = run("search", "--problem", "latin_leak", "--ids-only", "--path", str(path))
            self.assertEqual(code, 0)
            self.assertEqual(out.splitlines()[0], "leak")
            self.assertIn("MATCHES=1", out)
            code, out = run("search", "--problem", "nope", "--path", str(path))
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
