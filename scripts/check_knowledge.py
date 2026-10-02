"""Validate engine knowledge files have evidence and operational sections."""
import argparse,re
from pathlib import Path
REQ=("Identification","Tools","Workflow","Limitations","Sources")
ALIASES={"Identification":("Identification",),"Tools":("Tools","Tooling","مصفوفة الأدوات"),"Workflow":("Workflow","Safe route","Safe route", "خط العمل المثبت"),"Limitations":("Limitations","Acceptance", "قيود"),"Sources":("Sources","المصادر")}
def main():
 p=argparse.ArgumentParser();p.add_argument("path",type=Path);a=p.parse_args();bad=0
 for f in sorted(a.path.glob("*.md")):
  if f.name in {"README.md","ENGINE_PROFILE_TEMPLATE.md"}: continue
  text=f.read_text(encoding="utf-8")
  for h in REQ:
   if not any(re.search(r"^#+\s*.*"+re.escape(alias),text,re.M|re.I) for alias in ALIASES[h]):print(f"ERROR {f}: missing {h}");bad+=1
 return bad>0
if __name__=="__main__":raise SystemExit(int(main()))
