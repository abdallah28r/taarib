import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    if not path.exists():
        path = ROOT / "scripts" / "maintainer" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sbom = load("generate_sbom")
release = load("build_release")


class ReleaseAndSafetyTests(unittest.TestCase):
    def test_public_template_release_refuses_populated_font_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fonts").mkdir()
            (root / "PROJECT.yaml").write_text('name: "[اسم اللعبة]"\ninstall_path: "[المسار الكامل للعبة]"\n', encoding="utf-8")
            (root / "fonts/FONT_USAGE.json").write_text(json.dumps({"schema": 1, "fonts": [{"id": "private"}]}), encoding="utf-8")
            (root / "fonts/SYSTEM_INSTALLS.json").write_text(json.dumps({"schema": 1, "installations": []}), encoding="utf-8")
            archive = root / "public.zip"
            with patch.object(release, "ROOT", root):
                self.assertEqual(release.main([str(archive)]), 2)
            self.assertFalse(archive.exists())

    def test_release_allowlist_omits_notes_and_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "template.zip"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "maintainer" / "build_release.py"), str(archive)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
            self.assertIn("AGENTS.md", names)
            self.assertIn(".releaseinclude", names)
            self.assertIn("fonts/FONT_USAGE.json", names)
            self.assertIn("fonts/SYSTEM_INSTALLS.json", names)
            self.assertIn("references/font-sourcing.md", names)
            self.assertFalse(any(name.startswith("fonts/selected/") and name.endswith((".ttf", ".otf")) for name in names))
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

    def test_package_add_replace_uninstall_and_reinstall(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, changed, package = temporary / "game", temporary / "changed", temporary / "package"
            (root / "data").mkdir(parents=True)
            (changed / "data").mkdir(parents=True)
            (root / "data" / "text.txt").write_text("Save", encoding="utf-8")
            (changed / "data" / "text.txt").write_text("حفظ", encoding="utf-8")
            (changed / "data" / "font.txt").write_text("licensed-font", encoding="utf-8")
            build = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "build_patch_package.py"),
                                    str(root), str(package), "data/text.txt", "data/font.txt",
                                    "--patch-root", str(changed)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual({x["path"]: x["action"] for x in manifest["files"]},
                             {"data/text.txt": "replace", "data/font.txt": "add"})
            install_cmd = [sys.executable, "-B", str(ROOT / "scripts" / "apply_patch_package.py"),
                           str(root), str(package), "--yes"]
            self.assertEqual(subprocess.run(install_cmd, capture_output=True).returncode, 0)
            self.assertEqual((root / "data" / "text.txt").read_text(encoding="utf-8"), "حفظ")
            self.assertTrue((root / "data" / "font.txt").exists())
            transaction = next((root / ".install-state").iterdir()).name
            uninstall_cmd = [sys.executable, "-B", str(ROOT / "scripts" / "uninstall_patch_package.py"),
                             str(root), transaction, "--yes"]
            self.assertEqual(subprocess.run(uninstall_cmd, capture_output=True).returncode, 0)
            self.assertEqual((root / "data" / "text.txt").read_text(encoding="utf-8"), "Save")
            self.assertFalse((root / "data" / "font.txt").exists())
            self.assertNotEqual(subprocess.run(uninstall_cmd, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(install_cmd, capture_output=True).returncode, 0)

    def test_uninstall_refuses_a_user_changed_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, changed, package = temporary / "game", temporary / "changed", temporary / "package"
            root.mkdir()
            changed.mkdir()
            (changed / "ar.txt").write_text("Arabic", encoding="utf-8")
            build = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "build_patch_package.py"),
                                    str(root), str(package), "ar.txt", "--patch-root", str(changed)],
                                   capture_output=True)
            self.assertEqual(build.returncode, 0)
            install = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "apply_patch_package.py"),
                                      str(root), str(package), "--yes"], capture_output=True)
            self.assertEqual(install.returncode, 0)
            (root / "ar.txt").write_text("User changed", encoding="utf-8")
            transaction = next((root / ".install-state").iterdir()).name
            uninstall = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "uninstall_patch_package.py"),
                                        str(root), transaction, "--yes"], capture_output=True)
            self.assertNotEqual(uninstall.returncode, 0)
            self.assertEqual((root / "ar.txt").read_text(encoding="utf-8"), "User changed")

    def test_prepared_install_recovery_removes_added_file_and_restores_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, changed, package = temporary / "game", temporary / "changed", temporary / "package"
            root.mkdir()
            changed.mkdir()
            (root / "base.txt").write_bytes(b"old")
            (changed / "base.txt").write_bytes(b"new")
            (changed / "added.txt").write_bytes(b"arabic")
            build = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build_patch_package.py"),
                                    str(root), str(package), "base.txt", "added.txt", "--patch-root", str(changed)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            install = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/apply_patch_package.py"),
                                      str(root), str(package), "--yes"], capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            transaction = next((root / ".install-state").iterdir())
            state = transaction / "install-state.json"
            record = json.loads(state.read_text(encoding="utf-8"))
            record["status"] = "prepared"
            state.write_text(json.dumps(record), encoding="utf-8")
            uninstall = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/uninstall_patch_package.py"),
                                        str(root), transaction.name, "--yes"], capture_output=True, text=True)
            self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
            self.assertEqual((root / "base.txt").read_bytes(), b"old")
            self.assertFalse((root / "added.txt").exists())

    def test_patch_rejects_manifest_payload_and_casefold_duplicate(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root, changed, package = temporary / "game", temporary / "changed", temporary / "package"
            root.mkdir()
            changed.mkdir()
            for name in ("manifest.json", "A.txt", "a.txt"):
                (changed / name).write_text("x", encoding="utf-8")
            script = ROOT / "scripts/build_patch_package.py"
            for files in (("manifest.json",), ("A.txt", "a.txt")):
                result = subprocess.run([sys.executable, "-B", str(script), str(root), str(package),
                                         *files, "--patch-root", str(changed)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(package.exists())


if __name__ == "__main__": unittest.main()
