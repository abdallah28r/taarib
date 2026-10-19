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
FIXTURE = ROOT / "tests" / "fixtures" / "units"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


units = load_script("loc_units")
loc = load_script("loc")


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = loc.main(list(argv))
    return code, out.getvalue()


def errors_for(unit):
    files = [units.UnitFile(Path("x.jsonl"), [unit])]
    return units.validate(files).errors


class UnitValidationTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        code, out = run("validate", str(FIXTURE))
        self.assertEqual(code, 0, out)
        self.assertIn("UNITS=7 ERRORS=0", out)

    def test_translated_requires_target(self):
        unit = units.new_unit("a", "f", "Save", status="translated")
        self.assertTrue(any("requires a target" in e for e in errors_for(unit)))

    def test_keep_does_not_require_target(self):
        unit = units.new_unit("a", "f", "ACME", kind="image", asset="x.png", box=[0, 0, 4, 4],
                              decision="keep", status="tested", evidence={"integrated_build": "b", "tested": "seen"})
        self.assertEqual(errors_for(unit), [])

    def test_token_mismatch_is_an_error(self):
        unit = units.new_unit("a", "f", "Hi {player}", target="مرحبًا", status="translated")
        self.assertTrue(any("token mismatch" in e for e in errors_for(unit)))

    def test_changed_source_is_detected(self):
        unit = units.new_unit("a", "f", "Save")
        unit["source"] = "Save game"
        self.assertTrue(any("source changed" in e for e in errors_for(unit)))

    def test_integrated_and_tested_need_evidence(self):
        integrated = units.new_unit("a", "f", "Save", target="حفظ", status="integrated")
        tested = units.new_unit("b", "f", "Load", target="تحميل", status="tested",
                                evidence={"integrated_build": "1.0"})
        self.assertTrue(any("evidence.integrated_build" in e for e in errors_for(integrated)))
        self.assertTrue(any("evidence.tested" in e for e in errors_for(tested)))

    def test_proofreader_must_differ_from_translator(self):
        unit = units.new_unit("a", "f", "Save", target="حفظ", status="proofread",
                              translated_by="agent-1", proofread_by="agent-1")
        self.assertTrue(any("proofreader must differ" in e for e in errors_for(unit)))

    def test_image_unit_needs_asset_and_box(self):
        unit = units.new_unit("a", "f", "START", kind="image", box=[0, 0, 0, 5])
        found = errors_for(unit)
        self.assertTrue(any("requires asset" in e for e in found))
        self.assertTrue(any("requires box" in e for e in found))

    def test_duplicate_ids_across_files(self):
        first = units.UnitFile(Path("a.jsonl"), [units.new_unit("dup", "f", "A")])
        second = units.UnitFile(Path("b.jsonl"), [units.new_unit("dup", "f", "B")])
        self.assertTrue(any("duplicate id" in e for e in units.validate([first, second]).errors))


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.groups = loc.compute(units.all_units(units.load(FIXTURE)))

    def test_keep_is_excluded_and_stages_are_cumulative(self):
        everything = self.groups["all"]
        self.assertEqual(everything["total"], 7)
        self.assertEqual(everything["keep"], 1)
        self.assertEqual(everything["applicable"], 6)
        self.assertEqual(everything["reached"],
                         {"extracted": 6, "translated": 5, "proofread": 3, "integrated": 2, "tested": 1})
        self.assertEqual(everything["review"], 1)

    def test_split_by_kind(self):
        self.assertEqual(self.groups["text"]["applicable"], 5)
        self.assertEqual(self.groups["image"]["reached"]["translated"], 1)
        self.assertEqual(self.groups["image"]["keep"], 1)

    def test_chat_output(self):
        code, out = run("progress", "--path", str(FIXTURE), "--format", "chat")
        self.assertEqual(code, 0)
        self.assertIn("مترجم: 83% (5 من 6)", out)
        self.assertIn("مختبر داخل اللعبة: 17% (1 من 6)", out)

    def test_md_and_html_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            md = Path(directory) / "p.md"
            page = Path(directory) / "p.html"
            self.assertEqual(run("progress", "--path", str(FIXTURE), "--format", "md", "--out", str(md))[0], 0)
            self.assertEqual(run("progress", "--path", str(FIXTURE), "--format", "html", "--out", str(page))[0], 0)
            text, markup = md.read_text(encoding="utf-8"), page.read_text(encoding="utf-8")
        self.assertIn("| مدمج في اللعبة |", text)
        self.assertIn("ترجمة 100% لا تعني", text)
        self.assertIn('dir="rtl"', markup)
        self.assertIn('aria-valuenow="83"', markup)

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as directory:
            code, out = run("progress", "--path", directory, "--qa", str(Path(directory) / "none.csv"))
        self.assertEqual(code, 0)
        self.assertIn("لا توجد وحدات ترجمة بعد", out)

    def test_qa_matrix_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            matrix = Path(directory) / "m.csv"
            matrix.write_text("id,status\n1,pass\n2,fail\n3,not-run\n", encoding="utf-8")
            self.assertEqual(loc.qa_cases(matrix), {"total": 3, "passed": 1, "failed": 1, "not_run": 1})


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.units = Path(self.directory.name) / "units"
        shutil.copytree(FIXTURE, self.units)

    def tearDown(self):
        self.directory.cleanup()

    def unit(self, ident):
        for line in (self.units / "sample.jsonl").read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            if value["id"] == ident:
                return value
        raise KeyError(ident)

    def test_search_finds_image_text(self):
        code, out = run("search", "press", str(self.units), "--kind", "image")
        self.assertEqual(code, 0)
        self.assertIn("img/title.png#r1", out)
        self.assertIn("MATCHES=1", out)

    def test_mark_batch_integrated_with_evidence(self):
        code, out = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#001",
                        "--status", "integrated", "--evidence", "build 1.0.3 r2")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.unit("dlg/ch1#001")["evidence"]["integrated_build"], "build 1.0.3 r2")

    def test_mark_requires_evidence_for_tested(self):
        code, _ = run("mark", "--path", str(self.units), "--ids", "ui/menu#continue", "--status", "tested")
        self.assertEqual(code, 2)

    def test_mark_refuses_backward_and_invalid_moves(self):
        code, _ = run("mark", "--path", str(self.units), "--ids", "ui/menu#new_game", "--status", "translated")
        self.assertEqual(code, 1)
        code, out = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#003", "--status", "translated")
        self.assertEqual(code, 1)
        self.assertIn("NOT_WRITTEN", out)
        self.assertEqual(self.unit("dlg/ch1#003")["status"], "extracted")

    def test_mark_proofread_records_reviewer(self):
        code, out = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#002",
                        "--status", "proofread", "--by", "proofreader-2")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.unit("dlg/ch1#002")["proofread_by"], "proofreader-2")

    def test_normalize_refuses_changed_source_after_translation(self):
        path = self.units / "sample.jsonl"
        text = path.read_text(encoding="utf-8").replace('"Watch out."', '"Watch out!"')
        path.write_text(text, encoding="utf-8")
        code, out = run("normalize", str(self.units))
        self.assertEqual(code, 1)
        self.assertIn("source changed", out)

    def test_proofread_stores_target_hash_and_requires_by(self):
        code, _ = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#002", "--status", "proofread")
        self.assertEqual(code, 2)
        run("mark", "--path", str(self.units), "--ids", "dlg/ch1#002", "--status", "proofread", "--by", "proofreader-2")
        unit = self.unit("dlg/ch1#002")
        self.assertEqual(unit["proofread_hash"], units.source_hash(unit["target"]))

    def test_integrated_without_proofreading_is_refused(self):
        code, out = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#002",
                        "--status", "integrated", "--evidence", "build 2")
        self.assertEqual(code, 1)
        self.assertIn("requires proofreading", out)

    def test_backward_force_clears_proofreading(self):
        code, _ = run("mark", "--path", str(self.units), "--ids", "dlg/ch1#001", "--status", "translated", "--force")
        self.assertEqual(code, 0)
        self.assertNotIn("proofread_hash", self.unit("dlg/ch1#001"))


class ProofreadingTests(unittest.TestCase):
    def setUp(self):
        self.by_id = {u["id"]: u for u in units.all_units(units.load(FIXTURE))}

    def finding(self, **fields):
        base = {"id": "dlg/ch1#002", "severity": "minor", "category": "spelling", "issue": "x",
                "resolution": "applied", "before": "أنتبه.", "after": "انتبه.", "by": "proofreader-1"}
        base.update(fields)
        return base

    def check(self, *items):
        return loc.check_findings([(f"f:{n}", item) for n, item in enumerate(items, 1)], self.by_id)

    def test_changed_target_after_proofreading_fails_validation(self):
        unit = dict(self.by_id["dlg/ch1#001"])
        unit["target"] = "أهلًا يا {player}!"
        self.assertTrue(any("changed after proofreading" in e for e in errors_for(unit)))

    def test_valid_findings_summarize(self):
        errors, summary = self.check(self.finding())
        self.assertEqual(errors, [])
        self.assertEqual(summary["severity"]["minor"], 1)
        self.assertEqual(summary["resolution"]["applied"], 1)

    def test_translator_cannot_sign_findings(self):
        errors, _ = self.check(self.finding(by="translator-2"))
        self.assertTrue(any("signed by the unit's translator" in e for e in errors))

    def test_applied_change_must_match_current_target(self):
        errors, _ = self.check(self.finding(after="احذر."))
        self.assertTrue(any("no longer matches" in e for e in errors))

    def test_open_decision_blocks_proofread_unit(self):
        item = self.finding(id="dlg/ch1#001", category="context", resolution="needs_decision")
        errors, summary = self.check(item)
        self.assertEqual(summary["open"], ["dlg/ch1#001"])
        self.assertTrue(any("open needs_decision" in e for e in errors))
        resolved = self.finding(id="dlg/ch1#001", resolution="resolved", after="مرحبًا يا {player}!")
        errors, summary = self.check(item, resolved)
        self.assertEqual(errors, [])
        self.assertEqual(summary["open"], [])

    def test_unknown_id_and_bad_enum(self):
        errors, _ = self.check(self.finding(id="nope"), self.finding(severity="huge"))
        self.assertTrue(any("unknown unit id" in e for e in errors))
        self.assertTrue(any("severity must be" in e for e in errors))

    def test_findings_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch-002.jsonl"
            path.write_text(json.dumps(self.finding(), ensure_ascii=False) + "\n", encoding="utf-8")
            code, out = run("findings", str(path), "--path", str(FIXTURE))
        self.assertEqual(code, 0, out)
        self.assertIn("SEVERITY: minor=1", out)
        self.assertIn("FINDINGS=1 ERRORS=0", out)


if __name__ == "__main__":
    unittest.main()
