"""Check selected-font and user-install records, without certifying licenses."""
from __future__ import annotations

import argparse
from storage_core import digest
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
FONT_ID = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")
RIGHTS = ("render_into_images", "development_use", "redistribute_font_file")
DECISIONS = {"allowed", "denied", "unverified"}
USES = {"game-text", "image"}
TEST_STATES = {"pass", "pending", "fail"}


def _inside(root: Path, value: object, directory: str) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:2] != ("fonts", directory):
        return None
    base = (root / "fonts" / directory).resolve()
    raw = root / rel
    candidate = raw.resolve()
    return candidate if root.resolve() in base.parents and base in candidate.parents and not raw.is_symlink() else None


def validate(root: Path) -> list[str]:
    root = root.resolve()
    font_doc = json.loads((root / "fonts/FONT_USAGE.json").read_text(encoding="utf-8"))
    install_doc = json.loads((root / "fonts/SYSTEM_INSTALLS.json").read_text(encoding="utf-8"))
    if not isinstance(font_doc, dict) or font_doc.get("schema") != 1 or not isinstance(font_doc.get("fonts"), list):
        return ["FONT_USAGE: invalid schema"]
    if not isinstance(install_doc, dict) or install_doc.get("schema") != 1 or not isinstance(install_doc.get("installations"), list):
        return ["SYSTEM_INSTALLS: invalid schema"]
    errors, found = [], {}
    for index, item in enumerate(font_doc["fonts"]):
        label = f"font {index}"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected object")
            continue
        ident = item.get("id")
        if not isinstance(ident, str) or not FONT_ID.fullmatch(ident) or ident in found:
            errors.append(f"{label}: invalid or duplicate id")
            continue
        found[ident] = item
        origin = item.get("origin")
        if origin not in {"external", "game-shipped"}:
            errors.append(f"{label}: origin must be external or game-shipped")
        for field in ("family", "version_or_commit", "decision_note"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}: missing {field}")
        checksum = item.get("sha256")
        if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
            errors.append(f"{label}: invalid sha256")
        if origin == "external":
            for field in ("publisher", "source_url", "license_id"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f"{label}: missing {field}")
            if not isinstance(item.get("source_url"), str) or not item["source_url"].startswith("https://"):
                errors.append(f"{label}: source_url must be HTTPS")
            font_path = _inside(root, item.get("font_file"), "selected")
            license_path = _inside(root, item.get("license_file"), "licenses")
            if font_path is None or not font_path.is_file():
                errors.append(f"{label}: selected font file missing or unsafe")
            if license_path is None or not license_path.is_file():
                errors.append(f"{label}: license file missing or unsafe")
            if isinstance(checksum, str) and SHA256.fullmatch(checksum) and font_path is not None and font_path.is_file():
                actual = digest(font_path)
                if actual.lower() != checksum.lower():
                    errors.append(f"{label}: font hash mismatch")
        elif origin == "game-shipped":
            game_asset = item.get("game_asset")
            if not isinstance(game_asset, str) or not game_asset.strip() or Path(game_asset).is_absolute() or ".." in Path(game_asset).parts:
                errors.append(f"{label}: game-shipped font needs a game-relative asset path")
            if item.get("font_file") or item.get("license_file"):
                errors.append(f"{label}: do not copy a shipped game font or assert an external license file")
        rights = item.get("rights")
        if not isinstance(rights, dict) or any(rights.get(key) not in DECISIONS for key in RIGHTS):
            errors.append(f"{label}: three distinct rights decisions required")
        uses = item.get("uses")
        if not isinstance(uses, list) or not uses:
            errors.append(f"{label}: at least one use required")
            continue
        for use in uses:
            if not isinstance(use, dict) or use.get("kind") not in USES or not isinstance(use.get("target"), str) or not use["target"].strip():
                errors.append(f"{label}: invalid game-text/image use")
                continue
            if use.get("test_status") not in TEST_STATES or not isinstance(use.get("test_note"), str) or not use["test_note"].strip():
                errors.append(f"{label}: test status and note required for each use")
            if isinstance(rights, dict) and ((origin == "external" and rights.get("development_use") != "allowed")
                                             or (use["kind"] == "image" and rights.get("render_into_images") != "allowed")):
                errors.append(f"{label}: use lacks verified rights")
    seen_install = set()
    for index, item in enumerate(install_doc["installations"]):
        label = f"installation {index}"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected object")
            continue
        ident = item.get("font_id")
        if ident not in found:
            errors.append(f"{label}: unknown selected font")
        elif found[ident].get("origin") != "external":
            errors.append(f"{label}: cannot install a copied game font into Windows")
        if ident in seen_install and item.get("status") != "removed":
            errors.append(f"{label}: duplicate active installation")
        seen_install.add(ident)
        if item.get("scope") != "current-user" or item.get("preexisting") is not False:
            errors.append(f"{label}: current-user scope and no preexisting font required")
        if item.get("status") not in {"planned", "installed", "removed"}:
            errors.append(f"{label}: invalid status")
        for field in ("installed_file", "registry_key", "registry_value_name", "rollback_steps", "source_sha256"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}: missing {field}")
        key = item.get("registry_key")
        if (not isinstance(key, str) or key.casefold() !=
                r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts".casefold()):
            errors.append(f"{label}: registry key must be the current-user Fonts key")
        destination = item.get("installed_file")
        if isinstance(destination, str) and os.name == "nt":
            local_data = os.environ.get("LOCALAPPDATA")
            expected_dir = Path(local_data) / "Microsoft/Windows/Fonts" if local_data else None
            actual = Path(os.path.expandvars(destination)).resolve()
            if not expected_dir or not actual.is_relative_to(expected_dir.resolve()) or actual == expected_dir.resolve():
                errors.append(f"{label}: installed file must be under this user's font directory")
        if ident in found and item.get("source_sha256", "").lower() != found[ident].get("sha256", "").lower():
            errors.append(f"{label}: source hash differs from selected font")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        errors = validate(args.root)
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print("ERROR", error)
    print("FONT_RECORDS=" + ("FAIL" if errors else "STRUCTURE_PASS"))
    print("SCOPE=records and selected-file hashes only; font safety, license interpretation, visual and in-game QA are separate")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
