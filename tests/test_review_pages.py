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


review = load_script("review_pages")
candidate = load_script("image_candidate")


def picture(path: Path, color: str) -> Path:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (900, 300), color).save(path)
    return path


class ReviewPagesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.attempts = self.root / "work" / "images" / "attempts.json"

    def tearDown(self):
        self.temporary.cleanup()

    def image_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = candidate.main([*map(str, argv), "--attempts", str(self.attempts)])
        return code, out.getvalue()

    def test_texts_page_embeds_units_findings_and_safe_script(self):
        units = [{"id": "a", "kind": "text", "file": "f", "source": "Hi </script><b>", "target": "مرحبًا",
                  "status": "proofread", "batch": "b1", "context": {"speaker": "Mara"}},
                 {"id": "img", "kind": "image", "file": "x.png", "source": "SIGN", "status": "extracted"}]
        rows = review.texts_data(units, {"a": ["latin_leak"]},
                                 [{"id": "a", "severity": "minor", "issue": "x", "resolution": "applied"}])
        self.assertEqual([r["id"] for r in rows], ["a"], "image regions belong to images.html")
        self.assertEqual((rows[0]["sp"], rows[0]["p"], rows[0]["n"][0]["r"]), ("Mara", ["latin_leak"], "applied"))
        page = review.render_texts(rows, "Station", "", [("dashboard.html", "لوحة التعريب")])
        self.assertNotIn("</script><b>", page, "game text cannot close the page's script")
        self.assertIn('href="dashboard.html"', page)

    def test_every_version_with_its_verdict_and_a_spoiler_flag(self):
        source = picture(self.root / "game" / "ending.png", "#300")
        first = picture(self.root / "work" / "images" / "c1.png", "#311")
        second = picture(self.root / "work" / "images" / "c2.png", "#322")
        self.assertEqual(self.image_cli("record", "--source", source, "--candidate", first, "--method", "typeset")[0], 0)
        self.image_cli("record", "--source", source, "--candidate", second, "--method", "manual")
        code, out = self.image_cli("verdict", "--source", source, "--version", 1, "--verdict", "rejected", "--reason", " ")
        self.assertEqual(code, 2, "a verdict needs its reason")
        self.image_cli("verdict", "--source", source, "--version", 1, "--verdict", "rejected", "--reason", "broken letters")
        self.image_cli("verdict", "--source", source, "--version", 2, "--verdict", "accepted", "--reason", "joined")
        self.assertEqual(self.image_cli("spoiler", "--source", source)[0], 2, "a spoiler flag needs its reason")
        self.image_cli("spoiler", "--source", source, "--reason", "reveals the traitor")
        log = json.loads(self.attempts.read_text(encoding="utf-8"))
        entry = next(iter(log.values()))
        self.assertEqual([(v["n"], v["verdict"]) for v in entry["versions"]], [(1, "rejected"), (2, "accepted")])
        self.assertEqual(entry["raw"], [], "recorded candidates do not use up Codex attempts")

        units = [{"id": "i1", "kind": "image", "file": "ending.png", "asset": "ending.png", "source": "THE END",
                  "target": "النهاية", "status": "proofread"}]
        items = review.collect_images(self.root, units, self.root / "game")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual((item["spoiler"], item["candidate"].name), ("reveals the traitor", "c2.png"))
        render = lambda mode: review.render_images(items, self.root, mode, "Station", "", [], lambda s: s)
        self.assertIn('class="spoiler hidden"', render("flagged"))
        self.assertNotIn('class="spoiler hidden"', render("none"))
        page = render("flagged")
        self.assertIn("broken letters", page)
        self.assertIn("النسخة 2", page)
        self.assertTrue(list((self.root / "work" / "images" / "preview").glob("*.png")), "thumbnails are made")

    def test_unflagged_images_blur_only_when_all_is_chosen(self):
        source = picture(self.root / "game" / "menu.png", "#123")
        units = [{"id": "m", "kind": "image", "file": "menu.png", "asset": "menu.png", "source": "MENU",
                  "status": "extracted"}]
        items = review.collect_images(self.root, units, self.root / "game")
        self.assertEqual(items[0]["source"], source)
        self.assertNotIn('class="spoiler hidden"', review.render_images(items, self.root, "flagged", "S", "", [], str))
        self.assertIn('class="spoiler hidden"', review.render_images(items, self.root, "all", "S", "", [], str))

    def test_game_content_pages_never_reach_git_or_a_release(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for entry in ("texts.html", "images.html", "work/images/", "work/proofreading/"):
            self.assertIn(entry, ignored)
        release = (ROOT / ".releaseinclude").read_text(encoding="utf-8")
        self.assertNotIn("texts.html", release)
        self.assertNotIn("images.html", release)


if __name__ == "__main__":
    unittest.main()
