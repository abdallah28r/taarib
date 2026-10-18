import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


check_yaml = load_script("check_yaml")


class YamlKeyTests(unittest.TestCase):
    def check_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.yaml"
            path.write_text(text, encoding="utf-8")
            return check_yaml.check_file(path)

    def test_template_yaml_files_are_clean(self):
        self.assertEqual(check_yaml.main([]), 0)

    def test_glossary_keeps_boolean_like_terms(self):
        general = yaml.safe_load((ROOT / "glossary.yaml").read_text(encoding="utf-8"))["general"]
        self.assertEqual(general["Yes"], "نعم")
        self.assertEqual(general["No"], "لا")
        self.assertEqual(general["On"], "تشغيل")
        self.assertEqual(general["Off"], "إيقاف")

    def test_unquoted_boolean_key_is_rejected(self):
        problems = self.check_text("general:\n  Yes: نعم\n  On: تشغيل\n")
        self.assertTrue(any("bool" in p for p in problems))
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_duplicate_string_key_is_rejected(self):
        problems = self.check_text("general:\n  Save: حفظ\n  Save: احفظ\n")
        self.assertTrue(any("duplicate key 'Save'" in p for p in problems))

    def test_quoted_keys_pass(self):
        self.assertEqual(self.check_text('general:\n  "Yes": نعم\n  "Off": إيقاف\n'), [])


if __name__ == "__main__":
    unittest.main()
