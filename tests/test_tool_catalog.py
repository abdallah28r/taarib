import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tool_doctor", ROOT / "scripts" / "tool_doctor.py")
tool_doctor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(tool_doctor)


class ToolCatalogTests(unittest.TestCase):
    def test_catalog_schema_and_unique_ids(self):
        catalog = tool_doctor.load_catalog(ROOT / "tools" / "open-source-tools.json")
        ids = [tool["id"] for tool in catalog["tools"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 30)
        profiles = set(catalog["profiles"])
        for tool in catalog["tools"]:
            self.assertTrue(tool["url"].startswith("https://"))
            self.assertTrue(tool["profiles"])
            self.assertFalse(set(tool["profiles"]) - profiles, tool["id"])
            self.assertIn(tool["tier"], {"core", "recommended", "conditional"})

    def test_unverified_licenses_are_conditional(self):
        catalog = tool_doctor.load_catalog(ROOT / "tools" / "open-source-tools.json")
        for tool in catalog["tools"]:
            if "verify" in tool["license"].lower():
                self.assertEqual(tool["tier"], "conditional", tool["id"])


if __name__ == "__main__":
    unittest.main()
