import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("format_qa", ROOT / "scripts" / "format_qa.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FormatStructureTests(unittest.TestCase):
    def test_translated_icu_branch_text_is_not_a_protected_token(self):
        source = "{count, plural, one {One file} other {# files}}"
        target = "{count, plural, one {ملف واحد} other {# ملفات}}"
        errors, _ = MODULE.check_pair(source, target, "plural")
        self.assertEqual(errors, [])

    def test_icu_requires_original_branches_and_nested_variables(self):
        source = "{count, plural, one {{player} has one} other {{player} has many}}"
        target = "{count, plural, one {{player} لديه واحد} other {لديه الكثير}}"
        errors, _ = MODULE.check_pair(source, target, "plural")
        self.assertTrue(any("protected-token mismatch" in error for error in errors))
        errors, _ = MODULE.check_pair(source, "{count, plural, other {{player} كثير}}", "plural")
        self.assertTrue(any("missing ICU branch" in error for error in errors))

    def test_xliff_inline_identity_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "sample.xlf"
            source.write_text("<xliff><file><unit><segment><source>Open <ph id='code1'/> now</source>"
                              "<target>افتح <ph id='code2'/> الآن</target></segment></unit></file></xliff>",
                              encoding="utf-8")
            self.assertFalse(next(MODULE.xliff_pairs(source))[3])
            source.write_text(source.read_text(encoding="utf-8").replace("code2", "code1"), encoding="utf-8")
            self.assertTrue(next(MODULE.xliff_pairs(source))[3])

    def test_icu_controls_and_xliff_codes_may_reorder(self):
        source = "{a, select, other {A}} {b, select, other {B}}"
        target = "{b, select, other {ب}} {a, select, other {أ}}"
        self.assertEqual(MODULE.check_pair(source, target, "reorder")[0], [])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "moved.xlf"
            path.write_text("<xliff><file><unit><segment>"
                            "<source><ph id='a'/> and <ph id='b'/></source>"
                            "<target><ph id='b'/> و<ph id='a'/></target>"
                            "</segment></unit></file></xliff>", encoding="utf-8")
            self.assertTrue(next(MODULE.xliff_pairs(path))[3])


if __name__ == "__main__": unittest.main()
