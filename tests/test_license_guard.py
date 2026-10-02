import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "license_guard", ROOT / "scripts" / "license_guard.py"
)
license_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(license_guard)


class LicenseGuardTests(unittest.TestCase):
    def test_repository_catalogs_pass(self):
        self.assertEqual(license_guard.main([]), 0)

    def test_copyleft_cannot_be_marked_permissive(self):
        catalog = {
            "applications": [
                {
                    "id": "bad",
                    "url": "https://example.invalid/bad",
                    "license": "GPL-3.0",
                    "license_status": "verified-upstream",
                    "handling": "permissive-notices",
                }
            ]
        }
        errors = license_guard.validate_application_catalog(catalog)
        self.assertTrue(any("copyleft" in error for error in errors))

    def test_expired_permission_is_clean_room_only(self):
        catalog = {
            "applications": [
                {
                    "id": "expired",
                    "url": "about:expired",
                    "license": "proprietary",
                    "license_status": "no-current-permission",
                    "handling": "clean-room-only",
                }
            ]
        }
        self.assertEqual(license_guard.validate_application_catalog(catalog), [])


if __name__ == "__main__":
    unittest.main()
