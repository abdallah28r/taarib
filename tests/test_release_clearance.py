"""A shareable game patch needs the user's recorded permission and content review."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("release_clearance", ROOT / "scripts" / "release_clearance.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CLEARED = {
    "permission": {"type": "publisher-written", "source": "Email from publisher", "date": "2026-11-02"},
    "content_review": {"target_country": "SA", "official_age_rating": "18+",
                       "sensitive_content": [], "reviewed_by_user": True},
}


class MissingTests(unittest.TestCase):
    def test_the_template_default_blocks(self):
        self.assertEqual(len(MODULE.missing(MODULE.load(ROOT / "release-clearance.yaml"))), 6)

    def test_a_complete_record_passes(self):
        self.assertEqual(MODULE.missing(CLEARED), [])

    def test_no_permission_is_not_a_permission_type(self):
        settings = json.loads(json.dumps(CLEARED))
        settings["permission"]["type"] = "none"
        self.assertEqual(len(MODULE.missing(settings)), 1)

    def test_the_user_must_confirm_the_review(self):
        settings = json.loads(json.dumps(CLEARED))
        settings["content_review"]["reviewed_by_user"] = False
        self.assertEqual(len(MODULE.missing(settings)), 1)


class BuildTests(unittest.TestCase):
    def build(self, folder: Path, name: str, *extra: str) -> subprocess.CompletedProcess:
        root, changed = folder / "game", folder / "changed"
        for base in (root, changed):
            base.mkdir(exist_ok=True)
        (root / "text.txt").write_text("Save", encoding="utf-8")
        (changed / "text.txt").write_text("حفظ", encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "build_patch_package.py"),
                               str(root), str(folder / name), "text.txt", "--patch-root", str(changed), *extra],
                              capture_output=True, text=True, encoding="utf-8",
                              env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})

    def test_a_private_package_needs_no_clearance(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            self.assertEqual(self.build(folder, "out").returncode, 0)
            manifest = json.loads((folder / "out" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["distribution"], "private")

    def test_a_shareable_package_is_refused_without_clearance(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            result = self.build(folder, "out", "--shareable", "--clearance", str(folder / "none.yaml"))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / "out").exists())

    def test_a_shareable_package_is_marked_with_clearance(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            record = folder / "clearance.yaml"
            record.write_text(yaml.safe_dump(CLEARED), encoding="utf-8")
            result = self.build(folder, "out", "--shareable", "--clearance", str(record))
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((folder / "out" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["distribution"], "shareable")


if __name__ == "__main__":
    unittest.main()
