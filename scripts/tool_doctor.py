"""Inspect which cataloged open-source localization tools are available."""

from __future__ import annotations

import argparse
import glob
import importlib.util
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "tools" / "open-source-tools.json"


def load_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("tools"), list):
        raise ValueError("unsupported tool catalog schema")
    return data


def version_for(command: str) -> str:
    for flag in ("--version", "-version", "-V"):
        try:
            proc = subprocess.run([command, flag], capture_output=True, text=True,
                                  timeout=4, errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (proc.stdout or proc.stderr).strip().splitlines()
        if text:
            return text[0][:200]
    return "available"


def inspect(tool: dict, package_map: dict | None = None) -> dict:
    found_commands = []
    for command in tool.get("commands", []):
        path = shutil.which(command)
        if path:
            found_commands.append({"command": command, "path": path,
                                   "version": version_for(command)})
    for candidate in tool.get("paths", []):
        expanded = os.path.expandvars(candidate)
        if not Path(expanded).is_absolute():
            expanded = str(ROOT / expanded)
        for path in glob.glob(expanded):
            if Path(path).is_file() and not any(item["path"].lower() == path.lower() for item in found_commands):
                found_commands.append({"command": Path(path).stem, "path": path,
                                       "version": version_for(path)})
    package_map = package_map or {}
    found_modules = []
    for name in tool.get("modules", []):
        if importlib.util.find_spec(name) is None:
            continue
        distributions = package_map.get(name, [])
        details = []
        for distribution in distributions:
            try:
                details.append({"distribution": distribution,
                                "version": importlib.metadata.version(distribution)})
            except importlib.metadata.PackageNotFoundError:
                details.append({"distribution": distribution, "version": "unknown"})
        found_modules.append({"module": name, "distributions": details})
    has_checks = bool(tool.get("commands") or tool.get("modules") or tool.get("paths"))
    status = "installed" if found_commands or found_modules else ("missing" if has_checks else "catalog-only")
    return {"id": tool["id"], "name": tool["name"], "profiles": tool["profiles"],
            "tier": tool["tier"], "status": status, "commands": found_commands,
            "modules": found_modules, "url": tool["url"], "note": tool["note"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args(argv)
    catalog = load_catalog(args.catalog)
    profiles = set(args.profile)
    known = set(catalog["profiles"])
    unknown = profiles - known - {"all"}
    if unknown:
        parser.error("unknown profiles: " + ", ".join(sorted(unknown)))
    selected = [t for t in catalog["tools"] if not profiles or "all" in profiles
                or profiles.intersection(t["profiles"])]
    package_map = (importlib.metadata.packages_distributions()
                   if any(tool.get("modules") for tool in selected) else {})
    results = [inspect(tool, package_map) for tool in selected]
    summary = {state: sum(r["status"] == state for r in results)
               for state in ("installed", "missing", "catalog-only")}
    report = {"python": sys.version.split()[0], "profiles": sorted(profiles) or ["all"],
              "summary": summary, "tools": results}
    for item in results:
        print(f"{item['status'].upper():12} {item['id']:24} {item['name']}")
    print(json.dumps(summary, ensure_ascii=False))
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
