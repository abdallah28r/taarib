"""Build a public template ZIP from an explicit allowlist."""
from __future__ import annotations
import argparse, fnmatch, json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def patterns(path): return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
def included(rel,pats):
    value=rel.as_posix()
    return any(fnmatch.fnmatch(value,p) or (p.endswith("/**") and value.startswith(p[:-2])) for p in pats)
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("output",type=Path);p.add_argument("--force",action="store_true");a=p.parse_args(argv)
    out=a.output.resolve()
    if out.exists() and not a.force: print("ERROR output exists; use --force");return 2
    project=(ROOT/"PROJECT.yaml").read_text(encoding="utf-8")
    if 'name: "[اسم اللعبة]"' not in project or 'install_path: "[المسار الكامل للعبة]"' not in project:
        print("ERROR public template release requires unfilled game name and path");return 2
    for name, field in (("FONT_USAGE.json", "fonts"), ("SYSTEM_INSTALLS.json", "installations")):
        data = json.loads((ROOT / "fonts" / name).read_text(encoding="utf-8"))
        if data.get(field):
            print(f"ERROR public template release requires an empty {name}");return 2
    context_csv=(ROOT/"loc-kit"/"STRING_CONTEXT.csv").read_text(encoding="utf-8-sig").splitlines()
    if len(context_csv)!=1:
        print("ERROR public template release requires an empty STRING_CONTEXT.csv");return 2
    pats=patterns(ROOT/".releaseinclude");files=[]
    for file in sorted(ROOT.rglob("*")):
        if not file.is_file() or file.resolve()==out:continue
        rel=file.relative_to(ROOT)
        if not included(rel,pats):continue
        if "__pycache__" in rel.parts or file.suffix==".pyc":continue
        if file.is_symlink():print(f"ERROR release file is a symlink: {rel}");return 2
        files.append((file,rel))
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for file,rel in files:z.write(file,rel.as_posix())
    print(f"FILES={len(files)} OUTPUT={out}");return 0
if __name__=="__main__":raise SystemExit(main())
