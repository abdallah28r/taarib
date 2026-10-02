import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sbom = load("generate_sbom")


class ReleaseAndSafetyTests(unittest.TestCase):
    def test_release_allowlist_omits_notes_and_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "template.zip"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "build_release.py"), str(archive)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
            self.assertIn("AGENTS.md", names)
            self.assertIn(".releaseinclude", names)
            self.assertNotIn("work/NOTES.md", names)
            self.assertFalse(any(name.startswith("reports/") for name in names))
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))

    def test_sbom_inventory_matches_actual_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            archive = temporary / "artifact.zip"
            with zipfile.ZipFile(archive, "w") as package: package.writestr("a.txt", "hello")
            bom = sbom.build(archive, temporary / "sbom.json")
            self.assertEqual([item["name"] for item in bom["components"]], ["a.txt"])
            self.assertEqual(bom["components"][0]["hashes"][0]["content"], hashlib.sha256(b"hello").hexdigest())

    def test_safe_replace_preserves_each_previous_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root = temporary / "game"
            target = root / "data" / "text.txt"
            target.parent.mkdir(parents=True)
            target.write_text("one", encoding="utf-8")
            replacement = temporary / "new.txt"
            script = ROOT / "scripts" / "safe_replace.py"
            for value in ("two", "three"):
                replacement.write_text(value, encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(script), str(root), "data/text.txt", str(replacement), "--yes"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "three")
            originals = sorted((root / "backups" / "safe-replace").rglob("text.txt"))
            self.assertEqual(sorted(path.read_text(encoding="utf-8") for path in originals), ["one", "two"])

    def test_patch_install_requires_existing_exact_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, package = temporary / "game", temporary / "pkg"
            root.mkdir()
            package.mkdir()
            (package / "x").write_bytes(b"new")
            (package / "manifest.json").write_text(json.dumps({"files": [{"path": "x",
                "original_sha256": hashlib.sha256(b"old").hexdigest(),
                "patch_sha256": hashlib.sha256(b"new").hexdigest()}]}), encoding="utf-8")
            script = ROOT / "scripts" / "apply_patch_package.py"
            result = subprocess.run([sys.executable, "-B", str(script), str(root), str(package), "--yes"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "x").exists())

    def test_build_install_and_restore_on_a_synthetic_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, changed, package = temporary / "game", temporary / "changed", temporary / "package"
            (root / "data").mkdir(parents=True)
            (changed / "data").mkdir(parents=True)
            (root / "data" / "text.txt").write_text("Save", encoding="utf-8")
            (changed / "data" / "text.txt").write_text("حفظ", encoding="utf-8")
            build = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "build_patch_package.py"),
                                    str(root), str(package), "data/text.txt", "--patch-root", str(changed)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            install = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "apply_patch_package.py"),
                                      str(root), str(package), "--yes"], capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            self.assertEqual((root / "data" / "text.txt").read_text(encoding="utf-8"), "حفظ")
            snapshots = list((root / ".install-state").glob("*/originals/data/text.txt"))
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0].read_text(encoding="utf-8"), "Save")


if __name__ == "__main__": unittest.main()
