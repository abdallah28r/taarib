"""Print the smallest documented context set for a localization task route."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config"/"context-routes.json"
ALIASES=ROOT/"config"/"engine-profile-aliases.json"
def load(): return json.loads(CONFIG.read_text(encoding="utf-8"))
def profile_id(engine):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*",engine):
        raise ValueError(f"invalid engine ID: {engine}")
    aliases=json.loads(ALIASES.read_text(encoding="utf-8"))
    return aliases.get(engine,engine)
def resolve(route,engine=None):
    data=load();item=data["routes"][route];required=[*data["always"],item["skill"],*item["required"]];optional=item.get("optional",[])
    resolved_engine=profile_id(engine) if engine else None
    def sub(path): return path.replace("<engine>",resolved_engine) if resolved_engine else path
    return [sub(x) for x in required],[sub(x) for x in optional]
def estimate(paths):
    chars=sum((ROOT/p).read_text(encoding="utf-8-sig").__len__() for p in paths if "<engine>" not in p and (ROOT/p).is_file())
    return chars,round(chars/3.5)
def main(argv=None):
    data=load();p=argparse.ArgumentParser(description=__doc__);p.add_argument("route",choices=sorted(data["routes"]));p.add_argument("--engine");p.add_argument("--json",action="store_true");a=p.parse_args(argv)
    try: req,opt=resolve(a.route,a.engine)
    except ValueError as exc: p.error(str(exc))
    missing=[x for x in req if not (ROOT/x).is_file()]
    if a.engine: missing += [x for x in opt if x.startswith("engines/") and not (ROOT/x).is_file()]
    chars,tokens=estimate(req)
    report={"route":a.route,"required":req,"optional":opt,"missing":missing,"estimated_characters":chars,"estimated_tokens":tokens}
    if a.json: print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print("READ_REQUIRED")
        for x in req: print(x)
        if opt: print("READ_ONLY_IF_RELEVANT",*opt,sep="\n")
        print(f"ESTIMATED_CONTEXT_TOKENS={tokens}")
    return 1 if missing else 0
if __name__=="__main__":raise SystemExit(main())
