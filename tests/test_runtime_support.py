import importlib.util
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


sync_runtime_skills = load_script("sync_runtime_skills")


class RuntimeSupportTests(unittest.TestCase):
    def test_claude_skills_mirror_codex_skills(self):
        self.assertEqual(sync_runtime_skills.differences(), [])

    def test_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "a"
            target = Path(directory) / "b"
            (source / "skill").mkdir(parents=True)
            (source / "skill" / "SKILL.md").write_text("new", encoding="utf-8")
            sync_runtime_skills.sync(source, target)
            self.assertEqual(sync_runtime_skills.differences(source, target), [])
            (target / "skill" / "SKILL.md").write_text("old", encoding="utf-8")
            (target / "extra.md").write_text("x", encoding="utf-8")
            self.assertEqual(
                sync_runtime_skills.differences(source, target),
                ["changed skill/SKILL.md", "stale extra.md"],
            )

    def test_claude_entry_imports_shared_instructions(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", text)
        self.assertNotIn("GUIDE.md` كاملًا", text)

    def test_release_includes_claude_skills(self):
        patterns = (ROOT / ".releaseinclude").read_text(encoding="utf-8").splitlines()
        self.assertIn(".claude/skills/**", patterns)


if __name__ == "__main__":
    unittest.main()
