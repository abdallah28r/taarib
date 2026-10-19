import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


hooks = load_script("claude_hooks")
units = load_script("loc_units")


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "workspace"
        self.game = Path(self.temporary.name) / "My Game"
        (self.root / "units").mkdir(parents=True)
        (self.root / "backups").mkdir()
        (self.game / "Data").mkdir(parents=True)
        self.file = self.game / "Data" / "text.json"
        self.file.write_text("{}", encoding="utf-8")
        (self.root / "PROJECT.yaml").write_text(
            f"game:\n  install_path: {json.dumps(str(self.game))}\n", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def pre(self, tool, **tool_input):
        return hooks.pre_tool({"tool_name": tool, "tool_input": tool_input}, self.root)

    def test_game_file_needs_a_backup(self):
        self.assertIn("No backup of game file", self.pre("Edit", file_path=str(self.file)))
        backup = self.game / "backups" / "20261019T000000Z-abc" / "Data" / "text.json"
        backup.parent.mkdir(parents=True)
        backup.write_text("{}", encoding="utf-8")
        self.assertIsNone(self.pre("Edit", file_path=str(self.file)))

    def test_workspace_backup_counts(self):
        backup = self.root / "backups" / "2026-10-19" / "Data" / "text.json"
        backup.parent.mkdir(parents=True)
        backup.write_text("{}", encoding="utf-8")
        self.assertIsNone(self.pre("Write", file_path=str(self.file)))

    def test_new_game_file_and_outside_files_are_allowed(self):
        self.assertIsNone(self.pre("Write", file_path=str(self.game / "Data" / "new_ar.json")))
        self.assertIsNone(self.pre("Edit", file_path=str(self.root / "glossary.yaml")))

    def test_backups_are_read_only(self):
        self.assertIn("read-only", self.pre("Write", file_path=str(self.root / "backups" / "x" / "a.txt")))
        self.assertIn("read-only", self.pre("Edit", file_path=str(self.game / "backups" / "x" / "a.txt")))

    def test_shell_writes_into_game_are_blocked(self):
        forward = str(self.game).replace("\\", "/")
        self.assertIsNotNone(self.pre("Bash", command=f'cp out/text.json "{forward}/Data/text.json"'))
        self.assertIsNotNone(self.pre("PowerShell", command=f'Copy-Item out\\text.json "{self.game}\\Data\\text.json"'))
        self.assertIsNotNone(self.pre("Bash", command=f'echo x > "{forward}/Data/text.json"'))

    def test_git_bash_spelling_is_recognised(self):
        spellings = hooks.path_spellings(r"c:\games\my game")
        self.assertIn("/c/games/my game", spellings)

    def test_reads_and_backup_first_tools_are_allowed(self):
        forward = str(self.game).replace("\\", "/")
        self.assertIsNone(self.pre("Bash", command=f'ls "{forward}/Data"'))
        self.assertIsNone(self.pre("Bash", command=f'python scripts/safe_replace.py "{forward}" Data/text.json out.json --yes'))
        self.assertIsNone(self.pre("Bash", command="cp a b"))

    def test_no_install_path_means_no_game_guard(self):
        (self.root / "PROJECT.yaml").write_text('game:\n  install_path: "[المسار الكامل للعبة]"\n', encoding="utf-8")
        self.assertIsNone(self.pre("Edit", file_path=str(self.file)))

    def test_post_tool_reports_invalid_units(self):
        unit = units.new_unit("a", "f", "Save", status="translated")
        path = self.root / "units" / "a.jsonl"
        path.write_text(json.dumps(unit) + "\n", encoding="utf-8")
        reason = hooks.post_tool({"tool_input": {"file_path": str(path)}}, self.root)
        self.assertIn("requires a target", reason)

    def test_post_tool_flags_generated_files(self):
        reason = hooks.post_tool({"tool_input": {"file_path": str(self.root / ".claude" / "agents" / "x.md")}}, self.root)
        self.assertIn("is generated", reason)

    def test_cli_exit_codes(self):
        script = ROOT / "scripts" / "claude_hooks.py"
        event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "backups" / "x.txt")}})
        result = subprocess.run([sys.executable, str(script), "pre-tool"], input=event, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("read-only", result.stderr)
        result = subprocess.run([sys.executable, str(script), "session-start"], text=True, capture_output=True,
                                encoding="utf-8")
        self.assertEqual(result.returncode, 0)
        self.assertIn("PHASE", result.stdout)

    def test_settings_wire_every_mode(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
        commands = {event: settings[event][0]["hooks"][0]["command"] for event in settings}
        self.assertTrue(commands["PreToolUse"].endswith("pre-tool"))
        self.assertTrue(commands["PostToolUse"].endswith("post-tool"))
        self.assertTrue(commands["SessionStart"].endswith("session-start"))
        self.assertEqual(settings["PreToolUse"][0]["hooks"][0]["onFailure"], "block")
        self.assertIn("PowerShell", settings["PreToolUse"][0]["matcher"])


if __name__ == "__main__":
    unittest.main()
