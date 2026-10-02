"""Create a timestamped, hash-verified backup inside a game root."""
from __future__ import annotations
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
def main():
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("paths",nargs="+",type=Path);a=p.parse_args();root=a.root.resolve()
 if not root.is_dir(): raise SystemExit("root does not exist")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ");out=root/"backups"/(stamp+"-"+uuid4().hex);out.mkdir(parents=True)
 manifest={}
 for src in a.paths:
  s=(src if src.is_absolute() else root/src).resolve()
  if root not in s.parents and s!=root: raise SystemExit(f"refusing path outside root: {s}")
  if s==root or root/"backups" in s.parents: raise SystemExit("refusing to back up the root or its backups directory")
  if not s.exists(): raise SystemExit(f"missing: {s}")
  rel=s.relative_to(root);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
  if s.is_dir():shutil.copytree(s,dest)
  else:shutil.copy2(s,dest)
  for f in ([dest] if dest.is_file() else dest.rglob("*")):
   if f.is_file():manifest[str(f.relative_to(out))]=hashlib.sha256(f.read_bytes()).hexdigest()
 (out/"manifest.json").write_text(json.dumps({"created_utc":stamp,"files":manifest},indent=2),encoding="utf-8")
 print(out);return 0
if __name__=="__main__":raise SystemExit(main())
