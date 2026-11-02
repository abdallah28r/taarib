import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("delegate", ROOT / "scripts" / "delegate.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DelegateTests(unittest.TestCase):
    def test_the_other_runtime_does_the_delegated_work(self):
        self.assertEqual(MODULE.other_runtime({"runtime": "both", "runtime_root": "claude-code"}), "codex")
        self.assertEqual(MODULE.other_runtime({"runtime": "both", "runtime_root": "codex"}), "claude-code")
        self.assertIsNone(MODULE.other_runtime({"runtime": "codex"}))
        self.assertIsNone(MODULE.other_runtime({"runtime": "both", "runtime_root": ""}))

    def test_commands_point_the_agent_at_the_brief_only(self):
        brief = ROOT / "work" / "batches" / "b1.translator.md"
        claude = MODULE.command("claude-code", brief)
        self.assertEqual(claude[1], "-p")
        self.assertIn("Read only work/batches/b1.translator.md", claude[2])
        self.assertIn("Bash(python scripts/loc.py:*)", claude)
        codex = MODULE.command("codex", brief)
        self.assertEqual(codex[1:4], ["exec", "-s", "workspace-write"])
        self.assertIn("Read only work/batches/b1.translator.md", codex[-1])

    def test_a_brief_outside_the_project_is_refused(self):
        self.assertEqual(MODULE.main(["--brief", str(Path(sys.executable)), "--to", "codex", "--dry-run"]), 2)


if __name__ == "__main__":
    unittest.main()
