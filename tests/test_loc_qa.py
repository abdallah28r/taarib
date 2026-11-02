import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("loc_qa", ROOT / "scripts" / "loc_qa.py")
loc_qa = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(loc_qa)


class LocalizationQATests(unittest.TestCase):
    def test_token_extraction(self):
        text = r"Welcome {player}; HP=%1$d <b>OK</b>\n[sprite=1]"
        found = loc_qa.tokens(text)
        for token in ("{player}", "%1$d", "<b>", "</b>", r"\n", "[sprite=1]"):
            self.assertEqual(found[token], 1)

    def test_arabic_means_letters(self):
        self.assertIsNone(loc_qa.ARABIC_RE.search("Ready?؟ ٣، ok"))
        self.assertIsNotNone(loc_qa.ARABIC_RE.search("جاهز"))

    def test_engine_profile_tokens(self):
        rpg = loc_qa.tokens(r"\C[4]Name \I[12]", "rpgmaker")
        self.assertEqual(rpg[r"\C[4]"], 1)
        self.assertEqual(rpg[r"\I[12]"], 1)
        paradox = loc_qa.tokens("[Character.GetName] $VALUE$ @gold! #bold", "paradox")
        for token in ("[Character.GetName]", "$VALUE$", "@gold!", "#bold"):
            self.assertEqual(paradox[token], 1)
        renpy = loc_qa.tokens("Hello [player] {w=0.5}", "renpy")
        self.assertEqual(renpy["[player]"], 1)
        self.assertEqual(renpy["{w=0.5}"], 1)

    def test_good_and_bad_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.csv"
            good.write_text('id,source,target,note\n1,"Hello {name}","مرحبًا {name}",\n', encoding="utf-8")
            self.assertEqual(loc_qa.main([str(good), "--require-arabic"]), 0)
            bad = Path(tmp) / "bad.csv"
            bad.write_text('id,source,target,note\n1,"Hello {name}","مرحبًا",\n', encoding="utf-8")
            self.assertEqual(loc_qa.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
