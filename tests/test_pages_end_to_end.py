"""Drive the commands an agent uses, then check every record lands in the right place on each page."""
import contextlib
import importlib.util
import io
import json
import re
import shutil
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


loc = load_script("loc")
pipeline = load_script("loc_pipeline")
candidate = load_script("image_candidate")


def section(page: str, opening: str, closing: str = "</section>") -> str:
    start = page.index(opening)
    return page[start:page.index(closing, start)]


class PagesEndToEnd(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        game = self.root / "game"
        from PIL import Image
        for name, color in (("title.png", "#234"), ("ending.png", "#400")):
            (game / "ui").mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (600, 200), color).save(game / "ui" / name)
        settings = yaml.safe_load((ROOT / "PROJECT.yaml").read_text(encoding="utf-8"))
        settings["game"].update(name="Station", install_path=str(game))
        (self.root / "PROJECT.yaml").write_text(yaml.safe_dump(settings, allow_unicode=True), encoding="utf-8")
        self.units = self.root / "units"
        self.units.mkdir()
        rows = [
            {"id": "dlg#1", "kind": "text", "file": "ch1.rpy", "source": "The Reactor is offline.",
             "target": "الـ Reactor متوقف.", "status": "translated", "batch": "batch-002",
             "context": {"speaker": "Mara"}},
            {"id": "dlg#2", "kind": "text", "file": "ch1.rpy", "source": "We run.", "target": "نهرب.",
             "status": "proofread", "batch": "batch-002"},
            {"id": "img#title", "kind": "image", "file": "ui/title.png", "asset": "ui/title.png",
             "source": "STATION", "target": "المحطة", "status": "proofread", "decision": "translate"},
            {"id": "img#end", "kind": "image", "file": "ui/ending.png", "asset": "ui/ending.png",
             "source": "THE TRAITOR", "target": "الخائن", "status": "proofread", "decision": "translate"},
        ]
        (self.units / "game.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                               encoding="utf-8")
        self.state = self.root / "state" / "pipeline.json"
        self.qa = self.root / "qa.csv"
        self.qa.write_text("id,severity,status\n", encoding="utf-8")
        self.plan = self.root / "PLAN.md"
        self.plan.write_text("# خطة\n\n## الدفعات\n- [ ] batch-002 — الفصل الأول — t1 / p1\n", encoding="utf-8")
        self.attempts = self.root / "work" / "images" / "attempts.json"
        self.project = pipeline.Project(root=self.root, units_dir=self.units, state_file=self.state,
                                        qa_file=self.qa, plan_file=self.plan)
        self.loc("normalize", str(self.units))

    def tearDown(self):
        self.temporary.cleanup()

    def loc(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loc.main(list(argv))
        self.assertEqual(code, 0, out.getvalue())
        return out.getvalue()

    def task(self, *argv):
        return self.loc("task", "--state", str(self.state), "--project", str(self.root / "PROJECT.yaml"),
                        "--units", str(self.units), "--qa", str(self.qa), "--plan", str(self.plan), *argv)

    def image(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = candidate.main([*map(str, argv), "--attempts", str(self.attempts)])
        self.assertEqual(code, 0, out.getvalue())

    def test_every_record_reaches_its_place(self):
        # The agent's records, through the same commands it uses.
        self.task("add", "Ask: translate or keep «Reactor»?", "--kind", "question")
        self.task("move", "T-001", "waiting", "--reason", "Reactor: المفاعل أم يبقى؟")
        self.task("add", "Measure the dialogue box width", "--kind", "research")
        self.task("move", "T-002", "done", "--evidence", "probe preview: 600 px fits 42 chars")
        self.task("add", "Check fonts in the settings menu", "--kind", "qa", "--later")
        self.loc("fix", "--state", str(self.state), "open", "--title", "Clipped label", "--current", "cut",
                 "--expected", "whole", "--unchanged", "rest", "--ids", "dlg#2", "--path", str(self.units))
        pipeline.advance(self.project)  # refused: the intake answers are missing
        (self.root / "work" / "proofreading").mkdir(parents=True)
        (self.root / "work" / "proofreading" / "batch-002.jsonl").write_text(json.dumps(
            {"id": "dlg#1", "severity": "major", "category": "terminology", "issue": "Reactor غير مترجم",
             "resolution": "needs_decision", "by": "proofreader-1"}, ensure_ascii=False) + "\n", encoding="utf-8")
        (self.root / "work" / "probe").mkdir(parents=True)
        (self.root / "work" / "probe" / "last.json").write_text(json.dumps(
            {"at": "2026-10-28 18:00", "engine": "renpy", "fonts": {"total": 3, "arabic": 1},
             "boot": "booted_clean"}), encoding="utf-8")
        game = self.root / "game" / "ui"
        work = self.root / "work" / "images"
        from PIL import Image
        work.mkdir(parents=True, exist_ok=True)
        for name in ("title.v1.png", "title.v2.png", "ending.v1.png"):
            Image.new("RGB", (600, 200), "#555").save(work / name)
        self.image("record", "--source", game / "title.png", "--candidate", work / "title.v1.png", "--method", "typeset")
        self.image("record", "--source", game / "title.png", "--candidate", work / "title.v2.png", "--method", "manual")
        self.image("verdict", "--source", game / "title.png", "--version", 1, "--verdict", "rejected",
                   "--reason", "letters not joined")
        self.image("verdict", "--source", game / "title.png", "--version", 2, "--verdict", "accepted",
                   "--reason", "joined, background intact")
        self.image("spoiler", "--source", game / "title.png", "--none")
        self.image("record", "--source", game / "ending.png", "--candidate", work / "ending.v1.png", "--method", "typeset")
        self.image("spoiler", "--source", game / "ending.png", "--reason", "names the traitor")

        out = self.root / "dashboard.html"
        loc.write_dashboard(self.units, self.qa, out, self.project, self.plan)
        loc.write_texts(self.root / "texts.html", self.units, self.project)
        loc.write_images(self.root / "images.html", self.units, self.project)
        dashboard = out.read_text(encoding="utf-8")
        tasks = (self.root / "tasks.html").read_text(encoding="utf-8")
        texts = (self.root / "texts.html").read_text(encoding="utf-8")
        images = (self.root / "images.html").read_text(encoding="utf-8")

        # dashboard.html: what waits on the user at the top, then counts, events, and the last probe.
        waiting = section(dashboard, '<div class="card wait">', "</div>")
        self.assertIn("Ask: translate or keep «Reactor»?", waiting)
        self.assertIn("Reactor: المفاعل أم يبقى؟", waiting)
        self.assertLess(dashboard.index('class="card wait"'), dashboard.index("<h2>المرحلة</h2>"))
        self.assertIn("بانتظارك 1", dashboard)
        self.assertIn("محاولة عبور لم تكتمل في الاستقبال", section(dashboard, "آخر الأحداث", "</div>"))
        probe = section(dashboard, "آخر فحص للعبة", "</div>")
        self.assertIn("renpy", probe)
        self.assertIn("booted_clean", probe)
        for page in ("tasks.html", "texts.html", "images.html"):
            self.assertIn(f'href="{page}"', dashboard)

        # tasks.html: each card in its own column.
        self.assertIn("Ask: translate or keep", section(tasks, '<section class="col waiting">'))
        self.assertIn("F-001: Clipped label", section(tasks, '<section class="col doing">'))
        self.assertIn("الفصل الأول", section(tasks, '<section class="col next">'))
        self.assertIn("Check fonts in the settings menu", section(tasks, '<section class="col later">'))
        done = section(tasks, '<section class="col done">')
        self.assertIn("probe preview: 600 px fits 42 chars", done)
        self.assertNotIn("Ask: translate", done)

        # texts.html: text units only, each with its own status, speaker, problem codes and findings.
        data = json.loads(re.search(r"const DATA=(\[.*?\]);const STATUS", texts).group(1).replace("<\\/", "</"))
        by_id = {row["id"]: row for row in data}
        self.assertEqual(set(by_id), {"dlg#1", "dlg#2"})
        self.assertEqual((by_id["dlg#1"]["s"], by_id["dlg#1"]["sp"]), ("translated", "Mara"))
        self.assertEqual(by_id["dlg#1"]["n"][0]["r"], "needs_decision")
        self.assertIn("latin_leak", by_id["dlg#1"].get("p", []))
        self.assertNotIn("n", by_id["dlg#2"], "a finding stays with its own line")

        # images.html: the spoiler blurred with its reason inside, versions under their own image.
        ending = section(images, "<bdi>ending.png</bdi>")
        self.assertIn('class="spoiler hidden"', ending)
        self.assertIn("names the traitor", ending)
        title = section(images, "<bdi>title.png</bdi>")
        self.assertNotIn("spoiler hidden", title)
        self.assertIn("letters not joined", title)
        self.assertIn("joined, background intact", title)
        self.assertNotIn("letters not joined", ending)
        self.assertIn('class="compare"', title, "an accepted version gets the comparison slider")

        # The localization gate reads the same records: the ending still lacks an accepted version.
        all_units = loc.units.all_units(loc.units.load(self.units, loc.units.Report()))
        checks = pipeline.image_review(self.project, all_units)
        self.assertFalse(checks[1][0])
        self.assertIn("ending.png", checks[1][1])
        self.assertTrue(checks[2][0], "both images have a spoiler decision")


if __name__ == "__main__":
    unittest.main()
