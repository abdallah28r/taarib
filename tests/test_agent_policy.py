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
        self.assertIn("Model tier: standard (a middle model the active runtime offers at work time)", brief)
        self.assertIn("Reasoning effort: medium", brief)
        self.assertIn("Local language models: prohibited", brief)
        self.assertIn("independent bounded work", brief)
        self.assertIn("sole writer", brief)

    def test_model_choice_is_free(self):
        policy = make_subagent_brief.load_policy(ROOT / "config" / "agent-policy.json")
        self.assertEqual(policy["authorization"]["model_selection"], "free_choice_by_root_agent_routes_are_suggestions")
        brief = make_subagent_brief.build_brief(policy, "mechanical", "Count rows", "source/", runtime="claude-code",
                                                tier="deep", effort="high")
        self.assertIn("Model tier: deep (the strongest model the active runtime offers at work time)", brief)
        self.assertIn("Reasoning effort: high", brief)
        text = (ROOT / "MODEL_AND_SUBAGENT_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("There is no lightest-first rule", text)
        self.assertNotIn("Choose the lightest", text)

    def test_brief_can_target_one_runtime(self):
        policy = make_subagent_brief.load_policy(ROOT / "config" / "agent-policy.json")
        brief = make_subagent_brief.build_brief(
            policy, "mechanical", "Count rows", "source/", runtime="claude-code")
        self.assertIn("Model tier: light (the lightest model", brief)

    def test_model_names_are_rejected_and_tiers_need_descriptions(self):
        import json, tempfile
        policy = json.loads((ROOT / "config" / "agent-policy.json").read_text(encoding="utf-8"))
        policy["runtimes"]["claude-code"]["tiers"] = {"deep": "some-model"}
        del policy["tiers"]["deep"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(policy), encoding="utf-8")
            errors = check_agent_policy.validate(ROOT, path)
        self.assertTrue(any("claude-code names models" in e for e in errors), errors)
        self.assertTrue(any("tier deep needs a description" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
