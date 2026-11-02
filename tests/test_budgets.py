"""Size and shape budgets for the instruction files every session loads.

Longer instruction files are followed less reliably, Codex silently stops
reading AGENTS.md at 32 KiB, and a skill description that summarizes its steps
lets the agent follow the summary and skip the body. These tests fail before
any of that can creep back in.
"""
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
INSTRUCTION_LINE_LIMIT = 200
CODEX_AGENTS_MD_LIMIT = 32 * 1024
SKILL_LINE_LIMIT = 500
NAME_LIMIT = 64
DESCRIPTION_LIMIT = 1024


def frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    header, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(header), body


class InstructionBudgetTests(unittest.TestCase):
    def test_agents_md_fits_both_runtimes(self):
        data = (ROOT / "AGENTS.md").read_bytes()
        lines = data.decode("utf-8").count("\n")
        self.assertLess(lines, INSTRUCTION_LINE_LIMIT, "AGENTS.md: move detail into a reference or skill")
        self.assertLess(len(data), CODEX_AGENTS_MD_LIMIT * 0.75, "AGENTS.md is nearing Codex's 32 KiB cut-off")

    def test_claude_md_stays_small(self):
        lines = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").count("\n")
        self.assertLess(lines, INSTRUCTION_LINE_LIMIT)


class SkillShapeTests(unittest.TestCase):
    def skills(self):
        paths = sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))
        self.assertTrue(paths)
        return paths

    def test_names_match_folders(self):
        for path in self.skills():
            meta, _ = frontmatter(path)
            self.assertEqual(meta["name"], path.parent.name, path)
            self.assertLessEqual(len(meta["name"]), NAME_LIMIT, path)

    def test_descriptions_say_when_not_how(self):
        for path in self.skills():
            description = frontmatter(path)[0]["description"]
            self.assertLessEqual(len(description), DESCRIPTION_LIMIT, path)
            self.assertTrue(description.startswith("Use "), f"{path}: start with 'Use when ...'")
            self.assertIn("Triggers:", description, f"{path}: list Arabic trigger words")

    def test_skill_bodies_stay_short(self):
        for path in self.skills():
            _, body = frontmatter(path)
            self.assertLess(body.count("\n"), SKILL_LINE_LIMIT, path)

    def test_role_descriptions_fit(self):
        for path in sorted((ROOT / ".agents" / "roles").glob("*.md")):
            meta, _ = frontmatter(path)
            self.assertLessEqual(len(meta["description"]), DESCRIPTION_LIMIT, path)


if __name__ == "__main__":
    unittest.main()
