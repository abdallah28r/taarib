import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


check_agent_policy = load_script("check_agent_policy")
make_subagent_brief = load_script("make_subagent_brief")


class AgentPolicyTests(unittest.TestCase):
    def test_policy_and_active_surfaces_are_consistent(self):
        self.assertEqual(check_agent_policy.validate(ROOT), [])

    def test_brief_inherits_safety_and_route(self):
        policy = make_subagent_brief.load_policy(ROOT / "config" / "agent-policy.json")
        brief = make_subagent_brief.build_brief(
            policy,
            "contextual_translation",
            "Translate one scene",
            "target/scene-01.json",
            "write",
            "Updated scene plus QA result",
        )
        self.assertIn("gpt-6-sol", brief)
        self.assertIn("Reasoning effort: medium", brief)
        self.assertIn("Local language models: prohibited", brief)
        self.assertIn("independent bounded work", brief)
        self.assertIn("sole writer", brief)


if __name__ == "__main__":
    unittest.main()
