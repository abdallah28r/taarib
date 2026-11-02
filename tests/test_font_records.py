import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_font_records", ROOT / "scripts/check_font_records.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FontRecordTests(unittest.TestCase):
    def test_empty_template_is_valid(self):
        self.assertEqual(MODULE.validate(ROOT), [])

    def test_selected_font_use_and_separate_user_install_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            selected = project / "fonts/selected/test.ttf"
            license_file = project / "fonts/licenses/OFL.txt"
            selected.parent.mkdir(parents=True)
            license_file.parent.mkdir(parents=True)
            selected.write_bytes(b"synthetic-font-fixture")
            license_file.write_text("synthetic fixture license", encoding="utf-8")
            digest = hashlib.sha256(selected.read_bytes()).hexdigest()
            font = {
                "id": "test-font", "origin": "external", "family": "Fixture", "publisher": "Fixture designer",
                "version_or_commit": "1.0", "source_url": "https://example.invalid/fixture",
                "font_file": "fonts/selected/test.ttf", "sha256": digest,
                "license_id": "test-only", "license_file": "fonts/licenses/OFL.txt",
                "decision_note": "synthetic test", "rights": {
                    "render_into_images": "allowed", "development_use": "allowed",
                    "redistribute_font_file": "unverified"},
                "uses": [{"kind": "game-text", "target": "UI heading slot", "test_status": "pass",
                          "test_note": "synthetic rendering fixture"},
                         {"kind": "image", "target": "ui/title/*.png", "test_status": "pending",
                          "test_note": "visual comparison pending"}]
            }
            usage = project / "fonts/FONT_USAGE.json"
            installs = project / "fonts/SYSTEM_INSTALLS.json"
            usage.write_text(json.dumps({"schema": 1, "fonts": [font]}), encoding="utf-8")
            installs.write_text(json.dumps({"schema": 1, "installations": []}), encoding="utf-8")
            self.assertEqual(MODULE.validate(project), [])
            font["rights"]["render_into_images"] = "unverified"
            usage.write_text(json.dumps({"schema": 1, "fonts": [font]}), encoding="utf-8")
            self.assertTrue(any("use lacks verified rights" in e for e in MODULE.validate(project)))
            font["rights"]["render_into_images"] = "allowed"
            usage.write_text(json.dumps({"schema": 1, "fonts": [font]}), encoding="utf-8")
            install = {"font_id": "test-font", "scope": "all-users", "preexisting": False,
                       "status": "planned", "installed_file": "C:\\Windows\\Fonts\\test.ttf",
                       "registry_key": "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
                       "registry_value_name": "Fixture", "rollback_steps": "remove only fixture",
                       "source_sha256": digest}
            installs.write_text(json.dumps({"schema": 1, "installations": [install]}), encoding="utf-8")
            errors = MODULE.validate(project)
            self.assertTrue(any("current-user scope" in e for e in errors))
            self.assertTrue(any("current-user Fonts key" in e for e in errors))
            self.assertTrue(any("user's font directory" in e for e in errors))
            install["scope"] = "current-user"
            install["registry_key"] = r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
            install["installed_file"] = str(Path(os.environ.get("LOCALAPPDATA", str(project))) / "Microsoft/Windows/Fonts/test.ttf")
            installs.write_text(json.dumps({"schema": 1, "installations": [install]}), encoding="utf-8")
            self.assertEqual(MODULE.validate(project), [])
            shipped = {
                "id": "shipped-ui", "origin": "game-shipped", "family": "Original UI",
                "version_or_commit": "game-build-1", "game_asset": "assets/fonts/ui.font",
                "sha256": hashlib.sha256(b"synthetic-shipped-font").hexdigest(),
                "decision_note": "retain source look", "rights": {
                    "render_into_images": "unverified", "development_use": "unverified",
                    "redistribute_font_file": "denied"},
                "uses": [{"kind": "game-text", "target": "UI labels", "test_status": "pass",
                          "test_note": "synthetic fixture"}]
            }
            usage.write_text(json.dumps({"schema": 1, "fonts": [font, shipped]}), encoding="utf-8")
            self.assertEqual(MODULE.validate(project), [])
            install["font_id"] = "shipped-ui"
            install["source_sha256"] = shipped["sha256"]
            installs.write_text(json.dumps({"schema": 1, "installations": [install]}), encoding="utf-8")
            self.assertTrue(any("cannot install a copied game font" in e for e in MODULE.validate(project)))


if __name__ == "__main__":
    unittest.main()
