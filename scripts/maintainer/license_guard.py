"""Validate research-source handling and release licensing metadata.

This is a conservative policy check, not a legal opinion. It never downloads or
inspects binaries and makes no network calls.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_HANDLING = {
    "permissive-notices",
    "external-tool-only",
    "clean-room-only",
    "rejected",
}
PERMISSIVE_PREFIXES = ("MIT", "Apache-2.0", "BSD-")
COPYLEFT_MARKERS = ("GPL", "AGPL")
UNSAFE_LICENSE_MARKERS = ("unknown", "proprietary", "no-license", "claimed")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_application_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, app in enumerate(catalog.get("applications", []), 1):
        prefix = f"applications[{index}]"
        app_id = str(app.get("id", "")).strip()
        license_id = str(app.get("license", "")).strip()
        handling = str(app.get("handling", "")).strip()
        status = str(app.get("license_status", "")).strip().lower()

        if not app_id:
            errors.append(f"{prefix}: missing id")
        elif app_id in seen:
            errors.append(f"{prefix}: duplicate id {app_id!r}")
        seen.add(app_id)
        if handling not in ALLOWED_HANDLING:
            errors.append(f"{app_id}: invalid handling {handling!r}")
        if not str(app.get("url", "")).startswith(("https://", "about:")):
            errors.append(f"{app_id}: source URL must be https:// or about:")

        upper_license = license_id.upper()
        if handling == "permissive-notices":
            if not license_id.startswith(PERMISSIVE_PREFIXES):
                errors.append(f"{app_id}: non-permissive license cannot use permissive-notices")
            if "verified-upstream" not in status:
                errors.append(f"{app_id}: permissive reuse requires a verified upstream license")
        if any(marker in upper_license for marker in COPYLEFT_MARKERS) and handling == "permissive-notices":
            errors.append(f"{app_id}: copyleft code cannot enter the permissive core")
        if any(marker in license_id.lower() for marker in UNSAFE_LICENSE_MARKERS):
            if handling not in {"clean-room-only", "rejected"}:
                errors.append(f"{app_id}: uncertain/proprietary source must be clean-room-only or rejected")
        if status in {"no-current-permission", "expired", "permission-expired"}:
            if handling not in {"clean-room-only", "rejected"}:
                errors.append(f"{app_id}: expired or absent permission cannot authorize copying")
    if not catalog.get("applications"):
        errors.append("catalog contains no applications")
    return errors


def validate_tool_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, tool in enumerate(catalog.get("tools", []), 1):
        tool_id = str(tool.get("id", "")).strip()
        license_id = str(tool.get("license", "")).strip()
        tier = str(tool.get("tier", "")).strip()
        if not tool_id:
            errors.append(f"tools[{index}]: missing id")
        elif tool_id in seen:
            errors.append(f"tools[{index}]: duplicate id {tool_id!r}")
        seen.add(tool_id)
        if not license_id:
            errors.append(f"{tool_id}: missing license")
        if "verify" in license_id.lower() and tier != "conditional":
            errors.append(f"{tool_id}: unverified license must remain conditional")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--applications",
        type=Path,
        default=ROOT / "compliance" / "RESEARCH_SOURCE_REGISTER.json",
    )
    parser.add_argument(
        "--tools",
        type=Path,
        default=ROOT / "tools" / "open-source-tools.json",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    try:
        errors.extend(validate_application_catalog(load_json(args.applications)))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read application catalog: {exc}")
    try:
        errors.extend(validate_tool_catalog(load_json(args.tools)))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read tool catalog: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        print(f"LICENSE_GUARD=FAIL ERRORS={len(errors)}")
        return 1
    print("LICENSE_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
