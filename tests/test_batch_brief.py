import importlib.util
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
brief = load_script("loc_brief")
tools = load_script("loc_tools")
units = load_script("loc_units")

GLOSSARY = {"general": {"Save": "حفظ", "Load": "تحميل"}, "forbidden": {"قام ب": "use the verb"}}
CARDS = {"sara": {"id": "sara", "name": "Sara", "gender": "f", "voice": "dry humor"}}
GAME = {"register": "msa", "digits": "western"}


def unit(ident, source, batch, **fields):
    return units.new_unit(ident, "ch1.rpy", source, batch=batch, **fields)


def make(role, batch_units, file_units, problems=None):
    return brief.build(role, "b", batch_units, file_units, "# Subagent brief\n\n- rules", GAME, CARDS, GLOSSARY,
                       tools.glossary_entries(GLOSSARY), problems or {})


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.earlier = unit("a1", "Hi", "b0", target="أهلًا", status="proofread")
        self.one = unit("b1", "Save the game, Sara?", "b1",
                        context={"speaker": "sara", "addressee": "mo", "addressee_gender": "m",
                                 "addressee_number": "singular"})
        self.two = unit("c1", "Run!", "b2", context={"speaker": "narrator"}, target="اركض!", status="translated")
        self.file_units = [self.earlier, self.one, self.two]

    def test_layer_one_is_identical_across_batches(self):
        first = make("translator", [self.one], self.file_units)
        second = make("translator", [self.two], self.file_units)
        prefix = lambda text: text.split(brief.LAYER_MARKS[1])[0]
        self.assertEqual(prefix(first), prefix(second))
        self.assertLess(first.index(brief.LAYER_MARKS[0]), first.index(brief.LAYER_MARKS[1]))
        self.assertLess(first.index(brief.LAYER_MARKS[1]), first.index(brief.LAYER_MARKS[2]))
        self.assertIn("# Translator brief", first)
        self.assertNotIn("Subagent brief", first)

    def test_glossary_slice_and_characters(self):
        text = make("translator", [self.one], self.file_units)
        self.assertIn("- Save → حفظ", text)
        self.assertNotIn("Load", text)
        self.assertIn("- never: قام ب", text)
        self.assertIn("- sara — Sara — gender f — voice: dry humor", text)
        self.assertIn("treat gender as unknown): mo", text)
        self.assertIn('"addressee_gender": "m"', text)
        self.assertIn("- Hi → أهلًا", text)

    def test_proofreader_sees_targets_and_problems_translator_does_not(self):
        translator = make("translator", [self.two], self.file_units)
        proofreader = make("proofreader", [self.two], self.file_units, {"c1": ["latin_leak"]})
        self.assertNotIn('"target"', translator.split(brief.LAYER_MARKS[2])[1])
        self.assertIn('"target": "اركض!"', proofreader)
        self.assertIn('"problems": ["latin_leak"]', proofreader)

    def test_brief_command_reports_a_stable_prefix(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "u.jsonl"
            units.write(units.UnitFile(path, self.file_units))
            shas = []
            for batch in ("b1", "b2"):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = loc.main(["brief", "--batch", batch, "--path", str(path),
                                     "--out", str(Path(directory) / f"{batch}.md")])
                self.assertEqual(code, 0)
                shas.append(out.getvalue().split("CACHEABLE_PREFIX_SHA=")[1].strip())
            self.assertEqual(shas[0], shas[1])

    def test_brief_carries_the_style_rules_so_agents_read_nothing_else(self):
        translator, proofreader = brief.style_text("translator", ROOT), brief.style_text("proofreader", ROOT)
        self.assertIn("<!-- references/translation-core.md -->", translator)
        self.assertNotIn("proofreading-checklist", translator)
        self.assertIn("proofreading-checklist.md -->", proofreader)
        self.assertIn("<!-- references/problem-codes.md -->", proofreader)
        text = brief.build("translator", "b", [self.one], self.file_units, "# Subagent brief", GAME, CARDS,
                           GLOSSARY, tools.glossary_entries(GLOSSARY), {}, style=translator)
        self.assertLess(text.index("## Style and review rules"), text.index(brief.LAYER_MARKS[1]))

    def test_oversized_batch_is_flagged(self):
        many = [unit(f"u{i}", "word " * 40, "b") for i in range(3)]
        self.assertEqual(loc.batch_limits(many, {"max_batch_strings": 5, "max_batch_source_tokens": 4000}), [])
        warnings = loc.batch_limits(many, {"max_batch_strings": 2, "max_batch_source_tokens": 50})
        self.assertEqual(len(warnings), 2)
        self.assertIn("max_batch_strings=2", warnings[0])

    def test_addressee_fields_are_validated(self):
        bad = unit("x", "Hi", "b", context={"addressee_gender": "female", "addressee_number": "two"})
        errors = units.validate([units.UnitFile(Path("u.jsonl"), [bad])]).errors
        self.assertEqual(sum("context.addressee" in e for e in errors), 2)


class MqmTests(unittest.TestCase):
    def test_score(self):
        batch = [units.new_unit(f"u{i}", "f", "one two three four five") for i in range(4)]
        findings = [
            {"id": "u0", "severity": "major", "category": "context", "resolution": "applied"},
            {"id": "u0", "severity": "minor", "category": "spelling", "resolution": "applied"},
            {"id": "u1", "severity": "critical", "category": "meaning", "resolution": "rejected"},
            {"id": "u2", "severity": "minor", "category": "culture", "resolution": "needs_decision"},
        ]
        score = loc.mqm_score(findings, batch)
        self.assertEqual((score["flagged"], score["flag_rate"], score["penalty"], score["words"]), (2, 50, 7, 20))
        self.assertEqual(score["per_1000_words"], 350.0)
        self.assertEqual(score["dimensions"], {"accuracy": 1, "linguistic": 1, "audience": 1})

    def test_every_category_has_a_dimension(self):
        self.assertEqual(set(loc.CATEGORIES), set(loc.MQM_DIMENSION))
        checklist = (ROOT / ".agents/skills/arabic-proofreading/references/proofreading-checklist.md").read_text(
            encoding="utf-8")
        self.assertEqual([c for c in loc.CATEGORIES if f"| `{c}` |" not in checklist], [])


if __name__ == "__main__":
    unittest.main()
