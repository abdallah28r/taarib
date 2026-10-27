import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


experiences = load("loc_experiences", ROOT / "scripts" / "loc_experiences.py")
importer = load("import_experiences", ROOT / "scripts" / "maintainer" / "import_experiences.py")


class LessonTests(unittest.TestCase):
    def test_lessons_are_numbered_and_need_type_what_and_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "e.jsonl"
            first = experiences.add_lesson("limit", "Unity 6 TMP needs a new atlas", "batch-002 screenshot", path=path)
            second = experiences.add_lesson("template-bug", "x", "y", "fix z", "scripts/loc.py", path=path)
            self.assertEqual((first["id"], second["id"]), ("E-001", "E-002"))
            self.assertEqual(len(experiences.load_lessons(path)), 2)
            with self.assertRaises(ValueError):
                experiences.add_lesson("gossip", "x", "y", path=path)
            with self.assertRaises(ValueError):
                experiences.add_lesson("lesson", "x", " ", path=path)

    def test_key_is_stable_across_copies(self):
        a = {"id": "E-001", "type": "limit", "what": "w", "suggest": "s", "at": "1"}
        b = {"id": "E-009", "type": "limit", "what": "w", "suggest": "s", "at": "2"}
        self.assertEqual(experiences.lesson_key(a), experiences.lesson_key(b))


class SanitizerTests(unittest.TestCase):
    def test_paths_users_and_secrets_are_removed(self):
        clean = experiences.Sanitizer({"<GAME>": r"D:\Games\Station", "<PROJECT>": r"C:\Work\Station"}).text(
            r"read D:\Games\Station\game\script.rpy and C:/Work/Station/units, home C:\Users\abd\Desktop, "
            r"/home/sam/x key sk-abcdefghijklmnopqrstuvwx and api_key=12345")
        for leaked in ("Games", "Work", "abd", "sam", "sk-abc", "12345"):
            self.assertNotIn(leaked, clean)
        self.assertIn("<GAME>", clean)
        self.assertIn("<PROJECT>", clean)
        self.assertIn("<HOME>", clean)
        self.assertIn("api_key=<SECRET>", clean)

    def test_free_text_is_capped(self):
        self.assertTrue(experiences.Sanitizer({}).text("x" * 5000, 800).endswith(" …"))


class PackTests(unittest.TestCase):
    def test_package_holds_lessons_facts_summary_and_clean_files(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            engine = folder / "unity.md"
            engine.write_text(r"Tested at D:\Games\Station with token=abc", encoding="utf-8")
            lesson = {"id": "E-001", "type": "engine", "what": r"atlas in D:\Games\Station", "evidence": "e" * 2000,
                      "suggest": "add a check", "file": "references/arabic-rendering.md", "by": "", "at": "t"}
            sanitizer = experiences.Sanitizer({"<GAME>": r"D:\Games\Station"})
            target = experiences.pack([lesson], {"game": {"name": "Station", "engine": "unity"},
                                                 "install": r"D:\Games\Station"},
                                      {"engines/unity.md": engine}, folder, "Station: Deluxe", sanitizer, "20261027")
            self.assertEqual(target.name, "experiences-station-deluxe-20261027.zip")
            with zipfile.ZipFile(target) as archive:
                names = set(archive.namelist())
                body = {n: archive.read(n).decode("utf-8") for n in names}
        self.assertEqual(names, {"lessons.jsonl", "facts.json", "summary.md", "files/engines/unity.md"})
        packed = json.loads(body["lessons.jsonl"])
        self.assertEqual(packed["key"], experiences.lesson_key(lesson))
        self.assertLess(len(packed["evidence"]), 900)
        self.assertNotIn("Games", "".join(body.values()))
        self.assertIn("token=<SECRET>", body["files/engines/unity.md"])
        self.assertIn("## ملاحظة محرك (1)", body["summary.md"])

    def test_send_message_names_the_server_and_x(self):
        text = experiences.send_message("experiences-x.zip")
        contact = experiences.feedback()
        self.assertIn(contact["discord"]["invite"], text)
        self.assertIn(contact["discord"]["name"], text)
        self.assertIn(contact["x"], text)


class ImportTests(unittest.TestCase):
    def test_only_expected_members_are_unpacked_and_decided_lessons_drop_out(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            zip_path = folder / "experiences-a-1.zip"
            lesson = {"key": "abc123", "type": "limit", "what": "w", "suggest": "s"}
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("lessons.jsonl", json.dumps(lesson) + "\n" + json.dumps(lesson) + "\n")
                archive.writestr("files/engines/unity.md", "ok")
                archive.writestr("../escape.txt", "no")
                archive.writestr("files/engines/../../x.md", "no")
                archive.writestr("files/other/run.py", "no")
            inbox, ledger = folder / "inbox", folder / "ledger.json"
            unpacked, refused = importer.unpack(zip_path, inbox)
            self.assertEqual(sorted(refused), ["../escape.txt", "files/engines/../../x.md", "files/other/run.py"])
            self.assertTrue((unpacked / "files" / "engines" / "unity.md").is_file())
            self.assertFalse((folder / "escape.txt").exists())
            self.assertEqual(len(importer.pending(inbox, ledger)), 1)
            importer.decide("abc123", "applied", "added the check", ledger)
            self.assertEqual(importer.pending(inbox, ledger), [])


if __name__ == "__main__":
    unittest.main()
