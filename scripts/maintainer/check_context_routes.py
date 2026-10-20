"""Validate progressive-disclosure routes and their critical coverage."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def validate():
    data=json.loads((ROOT/"config/context-routes.json").read_text(encoding="utf-8"));errors=[]
    if data.get("schema_version")!=1: errors.append("schema_version must be 1")
    for name,item in data.get("routes",{}).items():
        for path in [*data.get("always",[]),item.get("skill",""),*item.get("required",[]),*item.get("optional",[])]:
            if not path or ("<engine>" not in path and not (ROOT/path).is_file()): errors.append(f"{name}: missing {path}")
    aliases=json.loads((ROOT/"config/engine-profile-aliases.json").read_text(encoding="utf-8"))
    spec=importlib.util.spec_from_file_location("detect_engine_for_routes",ROOT/"scripts/detect_engine.py")
    detector=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    for engine in detector.MARKERS:
        profile=aliases.get(engine,engine)
        if not (ROOT/"engines"/f"{profile}.md").is_file():
            errors.append(f"{engine}: no engine profile for detected ID")
    must={
      "discovery":{"references/project-run.md","references/discovery.md"},
      "mod-research":{"references/localization-mods.md","LEGAL_AND_CLEAN_ROOM_POLICY.md"},
      "translation-ui":{"glossary.yaml","references/translation-core.md","references/ui-style.md"},
      "translation-dialogue":{"glossary.yaml","references/translation-core.md","references/dialogue-style.md"},
      "subtitles":{"references/subtitles-style.md"},
      "proofreading":{"glossary.yaml","references/translation-core.md",".agents/skills/arabic-proofreading/references/proofreading-checklist.md"},
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
