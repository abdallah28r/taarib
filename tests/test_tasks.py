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
pipeline = load_script("loc_pipeline")
board = pipeline.tasks


class TaskBoardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)
        self.state = self.dir / "state" / "pipeline.json"
        self.plan = self.dir / "PLAN.md"
        self.plan.write_text("# خطة\n\n## الدفعات\n- [x] batch-001 — menus — t1 / p1\n"
                             "- [ ] batch-002 — scene 1 — t1 / p1 — unfinished: 40/90\n"
                             "- [ ] batch-003 — scene 2 — t2 / p1\n\n## القرارات\n- [ ] not a batch\n",
                             encoding="utf-8")
        self.project = pipeline.Project(state_file=self.state, units_dir=self.dir / "units",
                                        qa_file=self.dir / "qa.csv", plan_file=self.plan)

    def tearDown(self):
        self.temporary.cleanup()

    def run_loc(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loc.main([argv[0], "--state", str(self.state), "--plan", str(self.plan),
                             "--units", str(self.dir / "units"), "--qa", str(self.dir / "qa.csv"), *argv[1:]])
        return code, out.getvalue()

    def test_columns_need_evidence_or_reason(self):
        ident = board.add(self.state, "Wrap menu labels", "fix", "intake")
        with self.assertRaises(ValueError):
            board.move(self.state, ident, "done")
        with self.assertRaises(ValueError):
            board.move(self.state, ident, "waiting")
        with self.assertRaises(ValueError):
            board.move(self.state, ident, "dropped")
        board.move(self.state, ident, "waiting", reason="Which width?")
        task = board.move(self.state, ident, "done", evidence="validate: 0 errors")
        self.assertEqual([h["status"] for h in task["history"]], ["next", "waiting", "done"])

    def test_gate_refuses_a_phase_with_open_tasks(self):
        def task_check():
            return [c for c in pipeline.evaluate(self.project)[1] if "في لوحة المهام" in c[1]]
        self.assertEqual(task_check(), [], "no criterion while the phase has no tasks")
        ident = board.add(self.state, "Find the save folder", "research", "intake", "later")
        self.assertFalse(task_check()[0][0], "a task for later still blocks its phase")
        board.defer(self.state, ident, "discovery", "needs the game files", pipeline.PHASES, "intake")
        self.assertEqual(task_check(), [], "deferred to discovery, it no longer blocks intake")
        with self.assertRaises(ValueError):
            board.defer(self.state, ident, "intake", "back", pipeline.PHASES, "discovery")
        self.assertFalse(board.gate_checks(self.state, "discovery")[0][0])

    def test_refused_gate_is_recorded_once(self):
        for _ in range(3):
            pipeline.advance(self.project)
        blocked = [h for h in self.project.state()["history"] if h["event"] == "blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["phase"], "intake")

    def test_fix_lane_opens_and_closes_its_task(self):
        ident = pipeline.open_fix(self.project, "Clipped label", "cut", "whole", "rest", ["a"], {})
        task = board.linked(self.state, "fix", ident)
        self.assertEqual(task["status"], "doing")
        pipeline.close_fix(self.project, ident, "failed", "still clipped", {}, {})
        self.assertEqual(board.linked(self.state, "fix", ident)["status"], "next", "a failed fix leaves work open")

    def test_plan_batches_become_read_only_cards(self):
        cards = board.plan_batch_cards(self.plan)
        self.assertEqual([(c["id"], c["status"]) for c in cards],
                         [("batch-001", "done"), ("batch-002", "doing"), ("batch-003", "next")])
        self.assertEqual((cards[1]["title"], cards[1]["who"], cards[1]["progress"]),
                         ("scene 1", "t1 / p1", "40/90"))

    def test_cli_and_page(self):
        code, out = self.run_loc("task", "add", "Ask about the city name", "--kind", "question")
        self.assertEqual(code, 0, out)
        code, out = self.run_loc("task", "move", "T-001", "waiting", "--reason", "transliterate or translate?")
        self.assertEqual(code, 0, out)
        code, out = self.run_loc("task", "move", "T-001", "done")
        self.assertEqual(code, 2)
        self.assertIn("evidence", out)
        code, out = self.run_loc("next")
        self.assertIn("TASK T-001 [waiting]", out)
        page = loc.render_tasks(board.load(self.state), board.plan_batch_cards(self.plan), "Station", "")
        self.assertIn("transliterate or translate?", page)
        self.assertIn("batch-002", page)
        self.assertIn('href="dashboard.html"', page)
        summary = loc.tasks_summary_html(board.load(self.state), [], "tasks.html")
        self.assertIn("بانتظارك (1)", summary)

    def test_watch_runs_and_stops(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(loc.main(["watch", "--interval", "0", "--cycles", "2"]), 0)
        self.assertIn("WATCHING", out.getvalue())


if __name__ == "__main__":
    unittest.main()
