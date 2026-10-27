import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("image_candidate", ROOT / "scripts" / "image_candidate.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["image_candidate"] = MODULE
SPEC.loader.exec_module(MODULE)


class CompositeTests(unittest.TestCase):
    def test_only_masked_pixels_come_from_the_resized_raw_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, raw, mask, out = (folder / n for n in ("s.png", "raw.png", "m.png", "c.png"))
            Image.new("RGBA", (20, 10), (0, 0, 255, 255)).save(source)
            Image.new("RGB", (40, 20), (255, 0, 0)).save(raw)
            area = Image.new("L", (20, 10), 0)
            ImageDraw.Draw(area).rectangle((2, 2, 5, 5), fill=255)
            area.save(mask)
            MODULE.composite(source, raw, out, mask=mask)
            with Image.open(out) as im:
                self.assertEqual((im.size, im.mode), ((20, 10), "RGBA"))
                self.assertEqual(im.getpixel((3, 3)), (255, 0, 0, 255))
                self.assertEqual(im.getpixel((10, 8)), (0, 0, 255, 255))
            MODULE.composite(source, raw, out, box=[0, 0, 1, 1])
            with Image.open(out) as im:
                self.assertEqual(im.getpixel((3, 3)), (0, 0, 255, 255))


class AttemptCapTests(unittest.TestCase):
    def test_codex_is_refused_at_the_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "s.png"
            Image.new("RGB", (8, 8)).save(source)
            log = folder / "attempts.json"
            log.write_text(json.dumps({MODULE.sha256(source): {"image": "s.png", "raw": ["a"] * MODULE.cap()}}),
                           encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = MODULE.main(["codex", "--source", str(source), "--box", "0", "0", "4", "4", "--text", "خروج",
                                    "--attempts", str(log), "--dry-run"])
            self.assertEqual(code, 3)
            self.assertIn("REFUSED", out.getvalue())

    def test_prompt_names_the_box_text_and_raw_path(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "s.png"
            Image.new("RGB", (8, 6)).save(source)
            text = MODULE.prompt(source, [1, 2, 3, 4], "خروج", MODULE.IMAGES / "raw" / "s.attempt1.png", None)
        self.assertIn("8x6", text)
        self.assertIn("x0=1 y0=2 x1=3 y1=4", text)
        self.assertIn("خروج", text)
        self.assertIn("work/images/raw/s.attempt1.png", text)


if __name__ == "__main__":
    unittest.main()
