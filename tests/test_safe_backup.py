import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "safe_backup.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


class SafeBackupTests(unittest.TestCase):
    def test_backup_copies_with_relative_path_and_hash_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "game"
            (root / "data").mkdir(parents=True)
            (root / "data" / "text.json").write_text('{"a": 1}', encoding="utf-8")
            result = run(root, "data/text.json")
            self.assertEqual(result.returncode, 0, result.stderr)
            out = Path(result.stdout.strip())
            copy = out / "data" / "text.json"
            self.assertEqual(copy.read_text(encoding="utf-8"), '{"a": 1}')
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["files"][str(Path("data/text.json"))], hashlib.sha256(b'{"a": 1}').hexdigest())

    def test_paths_outside_the_root_or_in_backups_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "game"
            (root / "backups").mkdir(parents=True)
            (Path(folder) / "elsewhere.txt").write_text("x", encoding="utf-8")
            (root / "backups" / "old.txt").write_text("x", encoding="utf-8")
            self.assertIn("outside root", run(root, Path(folder) / "elsewhere.txt").stderr)
            self.assertIn("backups directory", run(root, "backups/old.txt").stderr)
            self.assertIn("missing", run(root, "nope.txt").stderr)


if __name__ == "__main__":
    unittest.main()
