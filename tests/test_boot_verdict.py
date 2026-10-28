import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("boot_verdict", ROOT / "scripts" / "boot_verdict.py")
boot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boot)

START = "Initialize engine version: 2022.3.21f1\n"


class BootVerdictTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def log(self, text, name="Player.log", age_minutes=0):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        stamp = time.time() - age_minutes * 60
        os.utime(path, (stamp, stamp))
        return path

    def verdict(self, *paths, baseline=None):
        return boot.judge(list(paths), 120, baseline)["verdict"]

    def test_clean_boot(self):
        self.assertEqual(self.verdict(self.log(START + "Loading game\n")), "booted_clean")

    def test_crash_wins_over_everything(self):
        text = START + "The character with Unicode value \\u0627 was not found\nCrash!!!\n"
        self.assertEqual(self.verdict(self.log(text)), "crashed")
        self.assertEqual(self.verdict(self.log(START, "log.txt"), self.log("Exception\n", "traceback.txt")), "crashed")

    def test_missing_arabic_glyph_from_textmeshpro(self):
        text = START + ("The character with Unicode value \\uFEB3 was not found in the [LiberationSans SDF] font "
                        "asset or any potential fallbacks. It was replaced by Unicode character \\u25A1.\n")
        report = boot.judge([self.log(text)], 120)
        self.assertEqual(report["verdict"], "missing_arabic_glyphs")
        self.assertIn("FEB3", report["evidence"][0])
        latin = START + "The character with Unicode value \\u00E9 was not found in the [X] font asset\n"
        self.assertEqual(self.verdict(self.log(latin)), "booted_clean")

    def test_errors_already_in_a_clean_boot_are_ignored(self):
        baseline = self.log(START + "NullReferenceException at Foo 0x1234\n", "before.log")
        after = self.log(START + "NullReferenceException at Foo 0x9999\n")
        self.assertEqual(self.verdict(after, baseline=baseline), "booted_clean")
        new = self.log(START + "NullReferenceException at Foo 0x9999\nIOException: font.ttf\n", "after.log")
        self.assertEqual(self.verdict(new, baseline=baseline), "booted_with_errors")

    def test_missing_stale_and_unknown_logs(self):
        self.assertEqual(self.verdict(), "no_log")
        self.assertEqual(self.verdict(self.log(START, age_minutes=600)), "stale_log")
        self.assertEqual(self.verdict(self.log("hello\n")), "no_boot_evidence")

    def test_finds_logs_in_the_game_folder_and_exit_codes(self):
        game = self.dir / "Game"
        (game / "BepInEx").mkdir(parents=True)
        (game / "Game_Data").mkdir()
        (game / "BepInEx" / "LogOutput.log").write_text(START, encoding="utf-8")
        self.assertIn(game / "BepInEx" / "LogOutput.log", boot.candidates("unity", game))
        self.assertEqual(boot.main(["--engine", "unity", "--game", str(game)]), 0)
        self.assertEqual(boot.main(["--log", str(self.log(START + "Fatal error!\n"))]), 2)


if __name__ == "__main__":
    unittest.main()
