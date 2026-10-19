"""Run the template's deterministic checks in one command."""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(label: str, args: list[str]) -> dict:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {"name": label, "exit_code": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]}

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path)
    p.add_argument(
        "--release",
        action="store_true",
        help="also dry-run a public ZIP and a file-level SBOM in a temporary directory",
    )
    a = p.parse_args(argv)
    py = sys.executable
    checks = [
        ("unit-tests", [py, "-m", "unittest", "discover", "-s", "tests"]),
        ("compile", [py, "-m", "compileall", "-q", "scripts", "tests"]),
        ("yaml-keys", [py, "scripts/check_yaml.py"]),
        ("runtime-files", [py, "scripts/sync_runtime.py", "--check"]),
        ("translation-units", [py, "scripts/loc.py", "validate"]),
        ("agent-policy", [py, "scripts/check_agent_policy.py"]),
        ("context-routes", [py, "scripts/check_context_routes.py"]),
        ("license-guard", [py, "scripts/license_guard.py"]),
        ("engine-knowledge", [py, "scripts/check_knowledge.py", "engines"]),
        ("tool-provenance-structure", [py, "scripts/check_tool_provenance.py"]),
        ("font-records", [py, "scripts/check_font_records.py"]),
    ]
    results = [run(*item) for item in checks]
    if a.release:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "arabic-loc-template.zip"
            sbom = Path(temporary) / "SBOM.cdx.json"
            built = run("release-archive", [py, "scripts/build_release.py", str(archive)])
            results.append(built)
            if built["exit_code"] == 0:
                results.append(run("artifact-sbom", [py, "scripts/generate_sbom.py", str(sbom), "--artifact", str(archive)]))
    report = {"ok": all(x["exit_code"] == 0 for x in results), "checks": results}
    print(json.dumps({"ok": report["ok"], "checks": [(x["name"], x["exit_code"]) for x in results]}, ensure_ascii=False, indent=2))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
