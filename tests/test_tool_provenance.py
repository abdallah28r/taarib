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

    def test_every_catalog_tool_is_named_where_the_agent_reads(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "tools" / "open-source-tools.json").read_text(encoding="utf-8"))
        text = "\n".join(p.read_text(encoding="utf-8").lower() for p in
                         [*root.glob("engines/*.md"), *root.glob("references/*.md"), *root.glob(".agents/**/*.md")])
        unnamed = [t["id"] for t in catalog["tools"]
                   if t["id"] not in text and t["name"].lower().split(" /")[0].split(" (")[0] not in text]
        self.assertEqual(unnamed, [])
        for engine, profiles in catalog["engines"].items():
            profile_file = root / "engines" / f"{engine}.md"
            self.assertTrue(profile_file.is_file(), engine)
            body = profile_file.read_text(encoding="utf-8")
            for tool in catalog["tools"]:
                if set(tool["profiles"]) & set(profiles):
                    self.assertIn(f"`{tool['id']}`", body, f"{tool['id']} missing from engines/{engine}.md")

    def test_the_engineering_skill_tells_the_agent_how_to_get_tools(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / ".agents" / "skills" / "game-localization-engineering" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("tool_doctor.py", "--engine <engine-id>", "tools/selected-tools.json", "check_tool_provenance.py", ".tools/"):
            self.assertIn(name, skill)


if __name__ == "__main__":
    unittest.main()
