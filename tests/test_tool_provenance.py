import json
from pathlib import Path
import tempfile
import unittest

from sys import path as sys_path

ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(ROOT / "scripts"))
from check_tool_provenance import validate


class ToolProvenanceTests(unittest.TestCase):
    def test_empty_template_is_valid_without_claiming_selected_tools(self):
        self.assertEqual(validate(ROOT / "tools/selected-tools.json"), [])

    def test_requires_exact_provenance_and_detects_changed_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file = root / "tool.bin"
            file.write_bytes(b"v1")
            lock = root / "selected.json"
            entry = {"id": "python", "version_or_commit": "test-fixture-v1",
                     "source_url": "https://example.invalid/test", "license": "test-license",
                     "decision_note": "synthetic test", "sha256": __import__("hashlib").sha256(b"v1").hexdigest(),
                     "local_file": str(file)}
            lock.write_text(json.dumps({"schema": 1, "selections": [entry]}), encoding="utf-8")
            self.assertEqual(validate(lock, verify_files=True), [])
            file.write_bytes(b"v2")
            self.assertTrue(any("hash mismatch" in error for error in validate(lock, verify_files=True)))


if __name__ == "__main__":
    unittest.main()
