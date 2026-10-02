import csv
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


merge_game_update = load_script("merge_game_update")
export_tmx = load_script("export_tmx")
project_stats = load_script("project_stats")
translation_map_stats = load_script("translation_map_stats")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "source", "target", "note", "status"])
        writer.writeheader()
        writer.writerows(rows)


class MaintenanceToolTests(unittest.TestCase):
    def test_update_merge_marks_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            old_source, new_source, old_target = tmp / "old.csv", tmp / "new.csv", tmp / "target.csv"
            write_csv(old_source, [{"id": "1", "source": "Save", "target": "", "note": "", "status": ""}])
            write_csv(new_source, [{"id": "1", "source": "Save game", "target": "", "note": "", "status": ""}])
            write_csv(old_target, [{"id": "1", "source": "Save", "target": "حفظ", "note": "", "status": "approved"}])
            rows, _, counts = merge_game_update.merge(old_source, new_source, old_target, "id")
            self.assertEqual(rows[0]["status"], "review_source_changed")
            self.assertEqual(rows[0]["previous_target"], "حفظ")
            self.assertEqual(rows[0]["target"], "")
            self.assertEqual(counts["changed_source"], 1)

    def test_tmx_and_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            table, output = tmp / "target.csv", tmp / "memory.tmx"
            write_csv(table, [{"id": "1", "source": "Save", "target": "حفظ", "note": "menu", "status": "approved"}])
            self.assertEqual(export_tmx.export(table, output, "en", "ar", "test"), 1)
            self.assertEqual(len(ET.parse(output).findall("./body/tu")), 1)
            stats = project_stats.analyze(table)["summary"]
            self.assertEqual(stats["translated"], 1)
            self.assertEqual(stats["coverage_percent"], 100.0)

    def test_update_merge_does_not_carry_draft_or_changed_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            old_source, new_source, old_target = tmp / "old.csv", tmp / "new.csv", tmp / "target.csv"
            write_csv(old_source, [{"id": "1", "source": "Case", "note": "menu", "target": "", "status": ""},
                                   {"id": "2", "source": "Save", "note": "menu", "target": "", "status": ""}])
            write_csv(new_source, [{"id": "1", "source": "Case", "note": "courtroom", "target": "", "status": ""},
                                   {"id": "2", "source": "Save", "note": "menu", "target": "", "status": ""}])
            write_csv(old_target, [{"id": "1", "source": "Case", "note": "menu", "target": "قضية", "status": "approved"},
                                   {"id": "2", "source": "Save", "note": "menu", "target": "احفظ", "status": "draft"}])
            rows, _, counts = merge_game_update.merge(old_source, new_source, old_target, "id")
            self.assertEqual([row["target"] for row in rows], ["", ""])
            self.assertEqual([row["status"] for row in rows], ["review_context_changed", "review_unapproved"])
            self.assertEqual(counts["changed_context"], 1)
            self.assertEqual(counts["unapproved"], 1)

    def test_tmx_rejects_unapproved_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            table, output = tmp / "target.csv", tmp / "memory.tmx"
            write_csv(table, [{"id": "1", "source": "Save", "target": "حفظ", "note": "", "status": "approved"},
                              {"id": "2", "source": "Load", "target": "تحميل", "note": "", "status": "draft"}])
            self.assertEqual(export_tmx.export(table, output, "en", "ar", "test"), 1)
            self.assertEqual([unit.attrib["tuid"] for unit in ET.parse(output).findall("./body/tu")], ["1"])

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
