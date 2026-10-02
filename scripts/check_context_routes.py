"""Validate progressive-disclosure routes and their critical coverage."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def validate():
    data=json.loads((ROOT/"config/context-routes.json").read_text(encoding="utf-8"));errors=[]
    if data.get("schema_version")!=1: errors.append("schema_version must be 1")
    for name,item in data.get("routes",{}).items():
        for path in [*data.get("always",[]),item.get("skill",""),*item.get("required",[])]:
            if not path or ("<engine>" not in path and not (ROOT/path).is_file()): errors.append(f"{name}: missing {path}")
    must={
      "discovery":{"references/project-run.md","references/discovery.md"},
      "mod-research":{"references/localization-mods.md","LEGAL_AND_CLEAN_ROOM_POLICY.md"},
      "translation-ui":{"glossary.yaml","references/translation-core.md","references/ui-style.md"},
      "translation-dialogue":{"glossary.yaml","references/translation-core.md","references/dialogue-style.md"},
      "subtitles":{"references/subtitles-style.md"},
      "qa-rendering":{"references/arabic-rendering.md","references/qa-strategy.md"},
      "delegation":{"MODEL_AND_SUBAGENT_POLICY.md","config/agent-policy.json"},
      "application-research":{"LEGAL_AND_CLEAN_ROOM_POLICY.md"},
      "release":{"references/release.md","RELEASE_COMPLIANCE.md"}
    }
    for route,paths in must.items():
        actual=set(data["routes"][route]["required"])
        for path in paths-actual: errors.append(f"{route}: critical context missing {path}")
    return errors
def main():
    errors=validate()
    for error in errors: print("ERROR",error)
    print(f"CONTEXT_ROUTES={'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0
if __name__=="__main__":raise SystemExit(main())
