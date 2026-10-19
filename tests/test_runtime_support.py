import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


sync_runtime = load_script("sync_runtime")
make_subagent_brief = load_script("make_subagent_brief")
POLICY = json.loads((ROOT / "config" / "agent-policy.json").read_text(encoding="utf-8"))

ROLE = """---
name: helper
description: Does one thing.
route: proofreading
skill: arabic-proofreading
tools: [Read, Bash]
---

Do the thing.
"""


class RuntimeSupportTests(unittest.TestCase):
    def test_generated_claude_files_are_current(self):
        self.assertEqual(sync_runtime.differences(sync_runtime.expected(), sync_runtime.present()), [])

    def test_drift_is_reported(self):
        wanted = {"a": b"new", "b": b"same"}
        found = {"a": b"old", "b": b"same", "c": b"x"}
        self.assertEqual(sync_runtime.differences(wanted, found), ["changed a", "stale c"])

    def test_role_renders_as_claude_agent_with_tier_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "helper.md"
            path.write_text(ROLE, encoding="utf-8")
            meta, body = sync_runtime.load_role(path)
        text = sync_runtime.render_claude_agent(meta, body, POLICY)
        self.assertTrue(text.startswith("---\nname: helper\n"))
        self.assertIn("model: sonnet\n", text)
        self.assertIn("tools: Read, Bash\n", text)
        self.assertIn(".claude/skills/arabic-proofreading/SKILL.md", text)
        self.assertTrue(text.endswith("Do the thing.\n"))

    def test_role_with_unknown_route_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "helper.md"
            path.write_text(ROLE.replace("route: proofreading", "route: nope"), encoding="utf-8")
            meta, body = sync_runtime.load_role(path)
        with self.assertRaises(ValueError):
            sync_runtime.render_claude_agent(meta, body, POLICY)

    def test_shipped_roles(self):
        roles = sync_runtime.roles()
        self.assertEqual(sorted(roles), ["proofreader", "translator"])
        self.assertEqual(roles["proofreader"][0]["skill"], "arabic-proofreading")
        self.assertEqual(roles["translator"][0]["route"], "contextual_translation")

    def test_codex_brief_carries_role_instructions(self):
        role = make_subagent_brief.load_roles()["proofreader"]
        brief = make_subagent_brief.build_brief(POLICY, role[0]["route"], "Proofread batch-1", "units/a.jsonl",
                                                "write", runtime="codex", role=role)
        self.assertIn("- Role: proofreader (skill: arabic-proofreading)", brief)
        self.assertIn("Model tier: standard (codex: gpt-6-sol)", brief)
        self.assertIn("## Role instructions", brief)
        self.assertIn("another agent translated", brief)

    def test_claude_entry_imports_shared_instructions(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", text)
        self.assertNotIn("GUIDE.md` كاملًا", text)

    def test_release_includes_claude_files(self):
        patterns = (ROOT / ".releaseinclude").read_text(encoding="utf-8").splitlines()
        self.assertIn(".claude/skills/**", patterns)
        self.assertIn(".claude/agents/**", patterns)


if __name__ == "__main__":
    unittest.main()
