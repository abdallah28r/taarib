import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


translation_map_stats = load_script("translation_map_stats")


class MaintenanceToolTests(unittest.TestCase):
    def test_json_map_stats_detects_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "a.json").write_text('{"menu#1": "حفظ", "menu#2": ""}', encoding="utf-8")
            (tmp / "b.json").write_text('{"menu#1": "تحميل"}', encoding="utf-8")
            stats = translation_map_stats.analyze(tmp)["summary"]
            self.assertEqual(stats["unique_keys"], 2)
            self.assertEqual(stats["conflicting_keys"], 1)
            self.assertEqual(stats["empty_entries"], 1)


if __name__ == "__main__":
    unittest.main()
