import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


class SafeDefaultTests(unittest.TestCase):
    """Only the deliberate standing defaults grant permission; everything else stays off."""

    def test_standing_defaults(self):
        project = load_yaml("PROJECT.yaml")
        self.assertEqual(project["workflow"]["install_to_user_copy"], "yes")
        self.assertEqual(project["workflow"]["subagent_preference"], "yes")
        self.assertIs(project["workflow"]["allow_subagents"], True)
        self.assertEqual(project["image_localization"]["external_image_editing"]["enabled"], "yes")
        self.assertEqual(project["workflow"]["image_scope"], "ask")
        self.assertIs(project["workflow"]["allow_launch_game"], False)

    def test_image_policy_does_not_enable_editing_itself(self):
        policy = load_yaml("config/image-localization-policy.yaml")
        self.assertNotIn("enabled", policy["external_image_editing"])
        self.assertTrue(policy["external_image_editing"]["enabled_by"].startswith("PROJECT.yaml:"))


if __name__ == "__main__":
    unittest.main()
