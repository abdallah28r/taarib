import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    if not path.exists():
        path = ROOT / "scripts" / "maintainer" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


check_context_routes = load_script("check_context_routes")
context_plan = load_script("context_plan")


class ContextRouteTests(unittest.TestCase):
    def test_all_routes_are_valid(self):
        self.assertEqual(check_context_routes.validate(), [])

    def test_translation_route_excludes_unrelated_policy(self):
        required, _ = context_plan.resolve("translation-ui")
        self.assertNotIn("LEGAL_AND_CLEAN_ROOM_POLICY.md", required)
        self.assertNotIn("MODEL_AND_SUBAGENT_POLICY.md", required)
        self.assertNotIn("GUIDE.md", required)
        self.assertNotIn("STYLE.md", required)

    def test_skill_file_is_not_read_twice(self):
        required, _ = context_plan.resolve("proofreading")
        self.assertFalse(any(path.endswith("SKILL.md") for path in required))

    def test_release_route_has_compliance_without_translation_style(self):
        required, _ = context_plan.resolve("release")
        self.assertIn("LEGAL_AND_CLEAN_ROOM_POLICY.md", required)
        self.assertIn("RELEASE_COMPLIANCE.md", required)
        self.assertNotIn("references/translation-core.md", required)

    def test_common_translation_context_is_small(self):
        required, _ = context_plan.resolve("translation-ui")
        _, estimated_tokens = context_plan.estimate(required)
        self.assertLess(estimated_tokens, 5000)

    def test_detected_engine_aliases_resolve_to_real_profiles(self):
        for engine, expected in (("rpg-maker-mz", "rpg-maker.md"),
                                 ("rpg-maker-mv", "rpg-maker.md"),
                                 ("source", "source-engine.md")):
            _, optional = context_plan.resolve("integration", engine)
            self.assertIn("engines/" + expected, optional)
            self.assertTrue((ROOT / "engines" / expected).is_file())
        with self.assertRaises(ValueError):
            context_plan.resolve("integration", "../outside")


if __name__ == "__main__":
    unittest.main()
