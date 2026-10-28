import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "renpy-reference"


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


class PipelineWalkthrough(unittest.TestCase):
    """Drive the reference game through every gate, as an agent would."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)
        self.game = self.dir / "game"
        shutil.copytree(REFERENCE, self.game)
        self.project_file = self.dir / "PROJECT.yaml"
        shutil.copyfile(ROOT / "PROJECT.yaml", self.project_file)
        self.units = self.dir / "units"
        self.units.mkdir()
        self.state = self.dir / "state" / "pipeline.json"
        self.qa = self.dir / "LQA.csv"
        self.qa.write_text("id,severity,status\ncase-1,major,not-run\n", encoding="utf-8")
        self.plan = self.dir / "PLAN.md"
        self.plan.write_text("# خطة\n\n## الدفعات\n<!-- مثال: - [ ] batch-x -->\n\n## القرارات\n- [ ] not a batch\n",
                             encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def run_loc(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loc.main(list(argv))
        return code, out.getvalue()

    def project_args(self):
        return ["--project", str(self.project_file), "--units", str(self.units),
                "--state", str(self.state), "--qa", str(self.qa), "--plan", str(self.plan)]

    def gate(self, check=False):
        return self.run_loc("gate", *(["--check"] if check else []), *self.project_args())

    def phase(self):
        return json.loads(self.state.read_text(encoding="utf-8"))["phase"] if self.state.exists() else "intake"

    def edit_project(self, **sections):
        data = yaml.safe_load(self.project_file.read_text(encoding="utf-8"))
        for section, values in sections.items():
            data.setdefault(section, {}).update(values)
        self.project_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    def answer_intake(self):
        self.edit_project(
            game={"name": "Station", "install_path": str(self.game)},
            workflow={"install_to_user_copy": "yes", "image_scope": "no", "runtime": "claude-code",
                      "subscription": "Claude Pro 20$", "subagent_mode": "economic", "review_mode": "separate"},
        )

    def units_file(self):
        return self.units / "game.jsonl"

    def test_template_starts_blocked_at_intake(self):
        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("TODO اسم اللعبة محدد", out)
        self.assertEqual(self.phase(), "intake")

    def test_full_walkthrough(self):
        self.answer_intake()
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "discovery")

        self.assertEqual(self.gate()[0], 1)
        self.edit_project(workflow={"engine_profile": "renpy", "adapter": str(ROOT / "adapters" / "renpy.py")})
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "extraction")

        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("PASS contract round-trip", out)
        self.assertIn("TODO توجد وحدات مستخرجة في units/", out)
        self.run_loc("extract", "--adapter", str(ROOT / "adapters" / "renpy.py"), "--game", str(self.game),
                     "--out", str(self.units_file()))
        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("TODO خطة الدفعات كاملة مكتوبة في PLAN.md", out)
        self.plan.write_text(self.plan.read_text(encoding="utf-8").replace(
            "## الدفعات\n", "## الدفعات\n- [ ] pilot — القائمة والإعدادات وأول مشهد — translator-1 / proofreader-1\n"
                            "- [ ] batch-001 — الكل — translator-1 / proofreader-1\n"), encoding="utf-8")
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "pilot")

        code, out = self.gate()
        self.assertIn("TODO دفعة التجربة محددة", out)
        rows = [json.loads(line) for line in self.units_file().read_text(encoding="utf-8").splitlines()]
        for index, row in enumerate(rows):
            row["target"] = "عربي " + row["source"]
            row["batch"] = "pilot" if index < 2 else "batch-001"
        self.units_file().write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        ids = [r["id"] for r in rows]
        pilot, rest = ids[:2], ids[2:]
        path = ["--path", str(self.units_file())]
        for status, flag in (("translated", ["--by", "translator-1"]), ("proofread", ["--by", "proofreader-1"]),
                             ("integrated", ["--evidence", "pilot build p1"])):
            self.assertEqual(self.run_loc("mark", *path, "--ids", *pilot, "--status", status, *flag)[0], 0)
        code, out = self.gate()
        self.assertIn("PASS دفعة التجربة مترجمة ومدققة ومثبتة", out)
        self.assertIn("TODO تأكيدك أن العربي يظهر صحيحًا", out)
        self.assertEqual(self.run_loc("pilot-ok", "--note", "user: menu and scene 1 read right to left, joined",
                                      *self.project_args())[0], 0)
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "localization")

        code, out = self.gate()
        self.assertIn("TODO كل وحدة قابلة للترجمة مدققة لغويًا (المتبقي: 6)", out)
        self.assertEqual(self.run_loc("mark", *path, "--ids", *rest, "--status", "translated", "--by", "translator-1")[0], 0)
        self.assertEqual(self.run_loc("mark", *path, "--ids", *rest, "--status", "proofread", "--by", "proofreader-1")[0], 0)
        code, out = self.gate()
        self.assertIn("TODO كل دفعات PLAN.md مؤشّرة ☑ (المتبقي: 2)", out)
        self.plan.write_text(self.plan.read_text(encoding="utf-8").replace("- [ ] ", "- [x] "), encoding="utf-8")
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "integration")

        self.assertEqual(self.gate()[0], 1)
        self.assertEqual(self.run_loc("mark", *path, "--ids", *ids, "--status", "integrated", "--evidence", "build r1")[0], 0)
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "playtest")

        code, out = self.gate()
        self.assertIn("TODO قبولك للنسخة مسجل", out)
        self.assertEqual(self.run_loc("accept", "--note", "user accepted r1", *self.project_args())[0], 0)
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "handoff")

        code, out = self.gate()
        self.assertIn("TODO ملف الخبرات مبني بعد قبولك", out)
        lessons = self.dir / "experiences.jsonl"
        self.assertEqual(self.run_loc("lesson", "add", "--type", "limit", "--what", "w", "--evidence", "e",
                                      "--path", str(lessons))[0], 0)
        code, out = self.run_loc("experiences", "--out", str(self.dir), "--lessons", str(lessons), *self.project_args())
        self.assertEqual(code, 0, out)
        self.assertIn("https://discord.gg/", out)
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.phase(), "release")
        history = json.loads(self.state.read_text(encoding="utf-8"))["history"]
        self.assertEqual([h["phase"] for h in history if h["event"] == "passed"],
                         ["intake", "discovery", "extraction", "pilot", "localization", "integration", "playtest", "handoff"])
        blocked = [h for h in history if h["event"] == "blocked"]
        self.assertTrue(blocked, "a refused gate is recorded")
        self.assertEqual(len(blocked), len({(h["phase"], h["missing"]) for h in blocked}), "once per shortfall")

    def test_changed_game_text_invalidates_the_recorded_contract(self):
        self.answer_intake()
        self.edit_project(workflow={"engine_profile": "renpy", "adapter": str(ROOT / "adapters" / "renpy.py")})
        self.gate()
        self.gate()
        self.run_loc("extract", "--adapter", str(ROOT / "adapters" / "renpy.py"), "--game", str(self.game),
                     "--out", str(self.units_file()))
        self.gate()  # records a passing contract, advances to localization
        tl = self.game / "game" / "tl" / "arabic" / "script.rpy"
        tl.write_text(tl.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        project = pipeline.Project(project_file=self.project_file, units_dir=self.units, state_file=self.state, qa_file=self.qa)
        checks = pipeline.check_extraction(project, project.settings(), project.state())
        self.assertFalse(checks[0][0])

    def test_check_does_not_advance(self):
        self.answer_intake()
        code, out = self.gate(check=True)
        self.assertEqual(code, 0)
        self.assertIn("GATE intake: READY", out)
        self.assertEqual(self.phase(), "intake")

    def test_reopen_and_accept_rules(self):
        self.answer_intake()
        self.gate()
        code, out = self.run_loc("accept", "--note", "x", *self.project_args())
        self.assertEqual(code, 2)
        code, _ = self.run_loc("reopen", "extraction", "--reason", "later phase", *self.project_args())
        self.assertEqual(code, 2)
        code, _ = self.run_loc("reopen", "intake", "--reason", "user changed the install target", *self.project_args())
        self.assertEqual(code, 0)
        self.assertEqual(self.phase(), "intake")

    def test_plan_batches_reads_only_the_batches_section(self):
        self.plan.write_text("## الدفعات\n- [x] a\n* [ ] b\n- not a box\n## القرارات\n- [ ] c\n", encoding="utf-8")
        project = pipeline.Project(plan_file=self.plan)
        self.assertEqual(pipeline.plan_batches(project), [True, False])

    def test_open_critical_defect_blocks_playtest(self):
        self.qa.write_text("id,severity,status\ncase-9,critical,fail\n", encoding="utf-8")
        project = pipeline.Project(project_file=self.project_file, units_dir=self.units, state_file=self.state, qa_file=self.qa)
        checks = pipeline.check_playtest(project, project.settings(), {"acceptance": {"note": "x"}})
        self.assertIn((False, "لا أخطاء حرجة مفتوحة في qa/LQA_MATRIX.csv (case-9)"), checks)

    def test_images_in_scope_need_an_inventory_or_a_reason(self):
        settings = {"workflow": {"image_scope": "yes"}}
        self.assertEqual(pipeline.image_inventory({"workflow": {"image_scope": "no"}}, {}, []), [])
        self.assertFalse(pipeline.image_inventory(settings, {}, [{"kind": "text"}])[0][0])
        self.assertTrue(pipeline.image_inventory(settings, {}, [{"kind": "image"}])[0][0])
        project = pipeline.Project(root=self.dir, state_file=self.state)
        with self.assertRaises(ValueError):
            pipeline.no_images(project, " ")
        pipeline.no_images(project, "searched game/gui and every archive: no PNG/DDS with text")
        self.assertTrue(pipeline.image_inventory(settings, project.state(), [])[0][0])

    def test_translated_image_regions_need_a_passing_manifest(self):
        project = pipeline.Project(root=self.dir)
        image = {"kind": "image", "id": "i1", "asset": "gui/title.png"}
        self.assertEqual(pipeline.image_review(project, [{"kind": "image", "decision": "keep"}]), [])
        self.assertFalse(pipeline.image_review(project, [image])[0][0])
        folder = self.dir / "work" / "images"
        folder.mkdir(parents=True)
        (folder / "attempts.json").write_text("{}", encoding="utf-8")
        (folder / "regions.json").write_text('{"images": "wrong"}', encoding="utf-8")
        ok, message = pipeline.image_review(project, [image])[0]
        self.assertFalse(ok)
        self.assertIn("images must be an array", message)
        (folder / "regions.json").write_text('{"images": []}', encoding="utf-8")
        ok, message = pipeline.image_review(project, [image])[0]
        self.assertFalse(ok)
        self.assertIn("title.png", message)
        checker = load_script("check_image_regions")
        original = checker.validate
        checker.validate = lambda path: []
        try:
            (folder / "regions.json").write_text('{"images": [{"image": "title.png"}]}', encoding="utf-8")
            self.assertTrue(pipeline.image_review(project, [image])[0][0])
        finally:
            checker.validate = original

    def test_pilot_confirmation_rules(self):
        project = pipeline.Project(state_file=self.state)
        with self.assertRaises(ValueError):
            pipeline.confirm_pilot(project, "too early")
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text(json.dumps({"schema_version": 1, "phase": "pilot", "history": []}), encoding="utf-8")
        pipeline.confirm_pilot(project, "user saw joined Arabic in the menu")
        state = project.state()
        state["phase"] = "integration"
        project.save(state)
        pipeline.reopen(project, "localization", "typo pass")
        self.assertIn("pilot", project.state())
        pipeline.reopen(project, "pilot", "font broke after a game update")
        self.assertNotIn("pilot", project.state())

    def test_working_setup_questions(self):
        flow = {"runtime": "both", "subscription": "ask", "subagent_mode": "fast", "subagent_concurrency": 0,
                "review_mode": "self"}
        failed = [m for ok, m in pipeline.working_setup(flow) if not ok]
        self.assertEqual(len(failed), 3)  # runtime_root, subscription, concurrency
        flow.update(runtime_root="claude-code", subscription="ChatGPT Plus 20$", subagent_concurrency=2)
        self.assertTrue(all(ok for ok, _ in pipeline.working_setup(flow)))
        economic = {"runtime": "codex", "subscription": "x", "subagent_mode": "economic", "review_mode": "separate"}
        self.assertTrue(all(ok for ok, _ in pipeline.working_setup(economic)))

    def test_self_review_is_refused_when_review_is_separate(self):
        unit = {"proofread_by": "self-review:translator-1", "translated_by": "translator-1"}
        self.assertFalse(pipeline.review_separation({"workflow": {"review_mode": "separate"}}, [unit])[0][0])
        self.assertEqual(pipeline.review_separation({"workflow": {"review_mode": "self"}}, [unit]), [])

    def test_next_reports_phase_and_route(self):
        code, out = self.run_loc("next", *self.project_args())
        self.assertEqual(code, 0)
        self.assertIn("PHASE 1/9: intake", out)
        self.assertIn("LOAD: references/project-run.md", out)


if __name__ == "__main__":
    unittest.main()
