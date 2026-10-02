"""Check engine profile structure and explicit evidence state, not factual accuracy."""
import argparse,re
from pathlib import Path
REQ=("Identification","Tools","Workflow","Limitations","Sources")
ALIASES={"Identification":("Identification",),"Tools":("Tools","Tooling","مصفوفة الأدوات"),"Workflow":("Workflow","Safe route","Safe route", "خط العمل المثبت"),"Limitations":("Limitations","Acceptance", "قيود"),"Sources":("Sources","المصادر")}
def main():
 p=argparse.ArgumentParser();p.add_argument("path",type=Path);a=p.parse_args();bad=0
 for f in sorted(a.path.glob("*.md")):
  if f.name in {"README.md","ENGINE_PROFILE_TEMPLATE.md"}: continue
  text=f.read_text(encoding="utf-8")
  if not re.search(r"^Evidence state:\s*`(?:candidate|documented-external|verified-project)`",text,re.M):
   print(f"ERROR {f}: missing explicit evidence state");bad+=1
  for h in REQ:
   sections=[m for alias in ALIASES[h] for m in re.finditer(r"^##\s*.*"+re.escape(alias)+r".*$",text,re.M|re.I)]
   if not sections:
    print(f"ERROR {f}: missing {h}");bad+=1
   elif not any(text[m.end():].split("\n## ",1)[0].strip() for m in sections):
    print(f"ERROR {f}: empty {h}");bad+=1
 print("ENGINE_PROFILE_STRUCTURE=PASS (content and compatibility unverified)" if not bad else "ENGINE_PROFILE_STRUCTURE=FAIL")
 return bad>0
if __name__=="__main__":raise SystemExit(int(main()))
