"""Storage growth and rollback regressions on small synthetic game files."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import patch_v3  # noqa: E402
import byte_patch  # noqa: E402
import original_store  # noqa: E402
import review_pages  # noqa: E402
import safe_replace  # noqa: E402
import save_guard  # noqa: E402
import storage_audit  # noqa: E402
from storage_core import digest  # noqa: E402


def command(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / script),
                           *map(str, args)], capture_output=True, text=True)


def directory_link(link: Path, target: Path) -> bool:
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, text=True)
            return result.returncode == 0
        return False


class StorageGrowthTests(unittest.TestCase):
    def test_save_snapshot_refuses_self_copy_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            saves = Path(folder) / "Saves"
            saves.mkdir()
            (saves / "slot.sav").write_bytes(b"original")
            with self.assertRaises(SystemExit):
                save_guard.snapshot(saves, saves / "backup")
            self.assertFalse((saves / "backup").exists())

    def test_backup_refuses_a_link_inside_source(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Path(folder) / "game"
            (game / "data").mkdir(parents=True)
            (game / "data" / "file.txt").write_text("original", encoding="utf-8")
            link = game / "data" / "loop"
            if not directory_link(link, game / "data"):
                self.skipTest("creating a directory link or junction is unavailable")
            result = command("safe_backup.py", game, "data")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((game / "backups").exists())

    def test_pending_junction_is_rejected_before_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, external = base / "game", base / "external"
            (game / ".install-state").mkdir(parents=True)
            external.mkdir()
            marker = external / "untouched"
            marker.write_bytes(b"keep")
            if not directory_link(game / ".install-state" / "pending", external):
                self.skipTest("creating a directory link or junction is unavailable")
            with self.assertRaises(ValueError):
                patch_v3.recover(game)
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_transaction_junction_is_rejected_before_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, external = base / "game", base / "external"
            (game / "backups").mkdir(parents=True)
            external.mkdir()
            marker = external / "untouched"
            marker.write_bytes(b"keep")
            if not directory_link(game / "backups" / ".transactions", external):
                self.skipTest("creating a directory link or junction is unavailable")
            with self.assertRaises(ValueError):
                original_store.clean_orphan_transactions(game, minimum_age_seconds=-1)
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_legacy_uninstall_refuses_linked_state_root(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, external = base / "game", base / "external"
            game.mkdir()
            external.mkdir()
            marker = external / "untouched"
            marker.write_bytes(b"keep")
            if not directory_link(game / ".install-state", external):
                self.skipTest("creating a directory link or junction is unavailable")
            result = command("uninstall_patch_package.py", game,
                             "20261029T000000Z-" + "a" * 32, "--yes")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_many_standalone_replacements_keep_one_original_and_refuse_external_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            game, replacement = Path(folder) / "game", Path(folder) / "new.bin"
            game.mkdir()
            target = game / "archive.bin"
            target.write_bytes(b"original" * 1000)
            for index in range(8):
                replacement.write_bytes(bytes([index]) * 8000)
                safe_replace.install(game, target, replacement)
            self.assertEqual((game / "backups" / "originals" / "files" / "archive.bin").read_bytes(), b"original" * 1000)
            self.assertEqual(len(list((game / "backups").rglob("archive.bin"))), 1)
            self.assertFalse(any((game / "backups" / ".transactions").iterdir()))
            target.write_bytes(b"user edit")
            with self.assertRaises(ValueError):
                safe_replace.install(game, target, replacement)
            self.assertEqual(target.read_bytes(), b"user edit")

    def test_standalone_replace_refuses_legacy_installed_package_file(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, replacement = base / "game", base / "replacement.bin"
            game.mkdir()
            target = game / "archive.bin"
            target.write_bytes(b"legacy installed")
            replacement.write_bytes(b"new")
            state = game / ".install-state" / "old-transaction"
            state.mkdir(parents=True)
            (state / "install-state.json").write_text(json.dumps({
                "schema": 2, "status": "installed", "files": [{"path": "ARCHIVE.BIN", "action": "replace",
                "patch_sha256": digest(target), "original_sha256": "unknown"}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "legacy installed package"):
                safe_replace.install(game, target, replacement)
            self.assertEqual(target.read_bytes(), b"legacy installed")
            self.assertFalse((game / "backups").exists())

    def test_full_package_upgrade_removes_old_addition_and_uninstall_restores_original(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, clean, first, second = (base / name for name in ("game", "clean", "first", "second"))
            for path in (game, clean, first, second):
                path.mkdir()
            (game / "text.bin").write_bytes(b"English")
            (clean / "text.bin").write_bytes(b"English")
            (first / "text.bin").write_bytes(b"Arabic v1")
            (first / "font.bin").write_bytes(b"font")
            (second / "text.bin").write_bytes(b"Arabic v2")
            package1, package2 = base / "package1", base / "package2"
            self.assertEqual(command("build_patch_package.py", clean, package1, "text.bin", "font.bin",
                                     "--patch-root", first).returncode, 0)
            self.assertEqual(command("build_patch_package.py", clean, package2, "text.bin",
                                     "--patch-root", second).returncode, 0)
            self.assertEqual(command("apply_patch_package.py", game, package1, "--yes").returncode, 0)
            self.assertEqual(command("apply_patch_package.py", game, package2, "--yes").returncode, 0)
            self.assertEqual((game / "text.bin").read_bytes(), b"Arabic v2")
            self.assertFalse((game / "font.bin").exists())
            active = json.loads((game / ".install-state" / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(command("uninstall_patch_package.py", game, active["id"], "--yes").returncode, 0)
            self.assertEqual((game / "text.bin").read_bytes(), b"English")
            self.assertEqual((game / "backups" / "originals" / "files" / "text.bin").read_bytes(), b"English")
            self.assertFalse((game / "font.bin").exists())
            self.assertFalse((game / ".install-state" / "active.json").exists())
            self.assertFalse(any((game / ".install-state" / "pending").iterdir()))

    def test_update_refuses_modified_installed_file(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, first, second = (base / name for name in ("game", "first", "second"))
            for path in (game, first, second):
                path.mkdir()
            target = game / "text.bin"
            target.write_bytes(b"English")
            (first / "text.bin").write_bytes(b"Arabic one")
            (second / "text.bin").write_bytes(b"Arabic two")
            original_hash = digest(target)
            def manifest(package):
                return {"schema": 3, "files": [{"path": "text.bin", "action": "replace",
                        "original_sha256": original_hash,
                        "patch_sha256": digest(package / "text.bin")}]}
            patch_v3.apply(game, first, manifest(first))
            target.write_bytes(b"external edit")
            with self.assertRaisesRegex(ValueError, "installed file changed"):
                patch_v3.apply(game, second, manifest(second))
            self.assertEqual(target.read_bytes(), b"external edit")
            self.assertFalse(any((game / ".install-state" / "pending").iterdir()))

    def test_added_file_uninstalls_even_if_old_unrelated_original_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, package = base / "game", base / "package"
            game.mkdir()
            package.mkdir()
            target = game / "optional.bin"
            target.write_bytes(b"old unrelated file")
            original_store.ensure(game, Path("optional.bin"))
            target.unlink()
            (package / "optional.bin").write_bytes(b"new add")
            manifest = {"schema": 3, "files": [{"path": "optional.bin", "action": "add",
                        "patch_sha256": digest(package / "optional.bin")}]}
            patch_v3.apply(game, package, manifest)
            patch_v3.apply(game, None)
            self.assertFalse(target.exists())
            self.assertTrue((game / "backups" / "originals" / "files" / "optional.bin").exists())

    def test_failed_package_install_restores_previous_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, package = base / "game", base / "package"
            game.mkdir()
            package.mkdir()
            (game / "a.bin").write_bytes(b"old")
            (package / "a.bin").write_bytes(b"new")
            (package / "b.bin").write_bytes(b"added")
            manifest = {"schema": 3, "files": [
                {"path": "a.bin", "action": "replace", "original_sha256": digest(game / "a.bin"),
                 "patch_sha256": digest(package / "a.bin")},
                {"path": "b.bin", "action": "add", "patch_sha256": digest(package / "b.bin")},
            ]}
            original_copy = patch_v3._atomic_copy
            calls = 0

            def fail_second(source, target, staging):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated interrupted install")
                return original_copy(source, target, staging)

            with patch.object(patch_v3, "_atomic_copy", side_effect=fail_second):
                with self.assertRaises(OSError):
                    patch_v3.apply(game, package, manifest)
            self.assertEqual((game / "a.bin").read_bytes(), b"old")
            self.assertFalse((game / "b.bin").exists())
            self.assertFalse((game / ".install-state" / "active.json").exists())

    def test_failure_while_preparing_rollback_cleans_registered_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, package = base / "game", base / "package"
            game.mkdir()
            package.mkdir()
            (game / "a.bin").write_bytes(b"old")
            (package / "a.bin").write_bytes(b"new")
            manifest = {"schema": 3, "files": [{"path": "a.bin", "action": "replace",
                        "original_sha256": digest(game / "a.bin"),
                        "patch_sha256": digest(package / "a.bin")}]}
            with patch.object(patch_v3.shutil, "copy2", side_effect=OSError("prepare copy failed")):
                with self.assertRaises(OSError):
                    patch_v3.apply(game, package, manifest)
            pending = game / ".install-state" / "pending"
            self.assertFalse(pending.exists() and any(pending.iterdir()))
            self.assertEqual((game / "a.bin").read_bytes(), b"old")

    def test_recovery_removes_partial_registered_journals_without_touching_game_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pending = root / ".install-state" / "pending" / "crashed"
            pending.mkdir(parents=True)
            (pending / "owner.json").write_text('{"owner":"taarib-patch-v3"}', encoding="utf-8")
            (pending / "prepare.tmp").write_text('{"schema":3,"paths": [', encoding="utf-8")
            (pending / "journal.tmp").write_text('{"schema":3,"old":', encoding="utf-8")
            (root / "game.bin").write_bytes(b"untouched")
            patch_v3.recover(root)
            self.assertFalse(pending.exists())
            self.assertEqual((root / "game.bin").read_bytes(), b"untouched")

    def test_crash_after_first_file_is_recovered_from_owned_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, package = base / "game", base / "package"
            game.mkdir()
            package.mkdir()
            (game / "a.bin").write_bytes(b"old")
            (package / "a.bin").write_bytes(b"new")
            (package / "b.bin").write_bytes(b"added")
            manifest = {"schema": 3, "files": [
                {"path": "a.bin", "action": "replace", "original_sha256": digest(game / "a.bin"),
                 "patch_sha256": digest(package / "a.bin")},
                {"path": "b.bin", "action": "add", "patch_sha256": digest(package / "b.bin")},
            ]}
            original_copy = patch_v3._atomic_copy
            calls = 0

            def crash_second(source, target, staging):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise KeyboardInterrupt
                return original_copy(source, target, staging)

            with patch.object(patch_v3, "_atomic_copy", side_effect=crash_second):
                with self.assertRaises(KeyboardInterrupt):
                    patch_v3.apply(game, package, manifest)
            self.assertEqual((game / "a.bin").read_bytes(), b"new")
            patch_v3.recover(game)
            self.assertEqual((game / "a.bin").read_bytes(), b"old")
            self.assertFalse((game / "b.bin").exists())
            self.assertFalse(any((game / ".install-state" / "pending").iterdir()))

    def test_unique_legacy_original_is_adopted_but_conflicts_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Path(folder) / "game"
            game.mkdir()
            target = game / "archive.bin"
            target.write_bytes(b"original")
            old = game / "backups" / "safe-replace" / "first"
            old.mkdir(parents=True)
            (old / "archive.bin").write_bytes(b"original")
            (old / "manifest.json").write_text(json.dumps({
                "target": "archive.bin", "backup": "backups/safe-replace/first/archive.bin",
                "original_sha256": digest(target), "replacement_sha256": digest(target)}),
                                                encoding="utf-8")
            self.assertEqual(command("safe_backup.py", game, "archive.bin").returncode, 0)
            self.assertEqual((game / "backups" / "originals" / "files" / "archive.bin").read_bytes(), b"original")

            other = game / "backups" / "safe-replace" / "second"
            other.mkdir()
            (other / "archive.bin").write_bytes(b"different")
            (other / "manifest.json").write_text(json.dumps({
                "target": "archive.bin", "backup": "backups/safe-replace/second/archive.bin",
                "original_sha256": digest(other / "archive.bin"), "replacement_sha256": digest(target)}),
                                                  encoding="utf-8")
            (game / "backups" / "originals" / "manifest.json").unlink()
            (game / "backups" / "originals" / "files" / "archive.bin").unlink()
            self.assertIn("legacy originals disagree", command("safe_backup.py", game, "archive.bin").stderr)

    def test_adopted_legacy_original_keeps_recorded_live_version(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            game, replacement = base / "game", base / "replacement.bin"
            game.mkdir()
            target = game / "archive.bin"
            target.write_bytes(b"localized one")
            old = game / "backups" / "safe-replace" / "previous"
            old.mkdir(parents=True)
            (old / "original.bin").write_bytes(b"English")
            (old / "manifest.json").write_text(json.dumps({
                "target": "archive.bin", "backup": "backups/safe-replace/previous/original.bin",
                "original_sha256": digest(old / "original.bin"),
                "replacement_sha256": digest(target)}), encoding="utf-8")
            self.assertEqual(command("safe_backup.py", game, "archive.bin").returncode, 0)
            replacement.write_bytes(b"localized two")
            safe_replace.install(game, target, replacement)
            self.assertEqual(target.read_bytes(), b"localized two")
            self.assertEqual((game / "backups" / "originals" / "files" / "archive.bin").read_bytes(), b"English")

    def test_unrecorded_old_backup_never_makes_live_file_an_original(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Path(folder) / "game"
            game.mkdir()
            (game / "archive.bin").write_bytes(b"possibly localized")
            old = game / "backups" / "20261003T093431Z"
            old.mkdir(parents=True)
            (old / "archive.bin").write_bytes(b"unknown old copy")
            (old / "manifest.json").write_text(json.dumps({
                "files": {"archive.bin": digest(old / "archive.bin")}}), encoding="utf-8")
            result = command("safe_backup.py", game, "archive.bin")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((game / "backups" / "originals").exists())

    def test_sparse_byte_patch_stores_only_changed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            original, built, patch_file = base / "original.bin", base / "built.bin", base / "p.arpatch"
            source = bytearray(1 << 20)
            changed = bytearray(source)
            for position in range(0, len(changed), 4096):
                changed[position] = 1
            original.write_bytes(source)
            built.write_bytes(changed)
            manifest = byte_patch.make_patch(original, built, patch_file)
            self.assertEqual(sum(length for _, length in manifest["ranges"]), 256)
            self.assertLess(patch_file.stat().st_size, 20000)
            with self.assertRaises(ValueError):
                byte_patch.make_patch(original, built, original)
            self.assertEqual(original.read_bytes(), source)

    def test_only_owned_unreferenced_previews_are_cleaned(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow unavailable")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "work" / "images").mkdir(parents=True)
            first, second = root / "one.png", root / "two.png"
            Image.new("RGB", (5, 5), "red").save(first)
            Image.new("RGB", (5, 5), "blue").save(second)
            keep = review_pages.thumbnail(first, root)
            remove = review_pages.thumbnail(second, root)
            unknown = root / "work" / "images" / "preview" / "unknown.png"
            unknown.write_bytes(b"user file")
            (root / "images.html").write_text(keep, encoding="utf-8")
            result = storage_audit.clean_temp(root)
            self.assertEqual(result["previews_removed"], 1)
            self.assertTrue((root / keep).exists())
            self.assertFalse((root / remove).exists())
            self.assertTrue(unknown.exists())

    def test_preview_link_cannot_write_or_clean_external_files(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow unavailable")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "project"
            outside = Path(folder) / "outside"
            (root / "work" / "images").mkdir(parents=True)
            outside.mkdir()
            image = root / "source.png"
            Image.new("RGB", (5, 5), "red").save(image)
            if not directory_link(root / "work" / "images" / "preview", outside):
                self.skipTest("creating a directory link or junction is unavailable")
            with self.assertRaises(ValueError):
                review_pages.thumbnail(image, root)
            self.assertEqual(review_pages.clean_previews(root, ""), 0)
            self.assertFalse(any(outside.iterdir()))

    def test_report_is_read_only_and_counts_unknown_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "backups" / "legacy").mkdir(parents=True)
            (root / "backups" / "legacy" / "save.bin").write_bytes(b"12345")
            (root / "reports").mkdir()
            (root / "reports" / "output.txt").write_bytes(b"123")
            before = {str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
                      for path in root.rglob("*") if path.is_file()}
            data = storage_audit.report(root)
            after = {str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
                     for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(data["total_bytes"], 8)
            self.assertEqual(data["categories"]["legacy-or-unknown-backup"]["bytes"], 5)
            self.assertEqual(len(data["legacy_candidates_for_review"]), data["legacy_candidate_count"])

    def test_report_marks_only_hash_verified_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "text.bin").write_bytes(b"English")
            backup, _ = original_store.ensure(root, Path("text.bin"))
            self.assertEqual(storage_audit.report(root)["categories"]["verified-originals"]["bytes"], 7)
            backup.write_bytes(b"changed")
            report = storage_audit.report(root)
            self.assertNotIn("verified-originals", report["categories"])
            self.assertEqual(report["categories"]["original-store-unknown"]["bytes"], 7)

    def test_cleanup_keeps_unknown_files_inside_owned_transactions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            transaction = root / "backups" / ".transactions" / "stale"
            transaction.mkdir(parents=True)
            (transaction / "owner.json").write_text('{"owner":"taarib-safe-replace-v1"}', encoding="utf-8")
            unknown = transaction / "user.txt"
            unknown.write_bytes(b"keep")
            self.assertEqual(original_store.clean_orphan_transactions(root, minimum_age_seconds=-1), 0)
            self.assertEqual(unknown.read_bytes(), b"keep")

            package = root / "package"
            package.mkdir()
            (root / "text.bin").write_bytes(b"English")
            (package / "text.bin").write_bytes(b"Arabic")
            manifest = {"schema": 3, "files": [{"path": "text.bin", "action": "replace",
                        "original_sha256": digest(root / "text.bin"),
                        "patch_sha256": digest(package / "text.bin")}]}
            with patch.object(patch_v3, "_delete_pending", side_effect=OSError("leave staging")):
                patch_v3.apply(root, package, manifest)
            pending = next((root / ".install-state" / "pending").iterdir())
            extra = pending / "user.txt"
            extra.write_bytes(b"keep")
            self.assertEqual(patch_v3.clean_committed(root), 0)
            self.assertEqual(extra.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
