"""Print the smallest documented context set for a localization task route."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config"/"context-routes.json"
def load(): return json.loads(CONFIG.read_text(encoding="utf-8"))
def resolve(route,engine=None):
    data=load();item=data["routes"][route];required=[*data["always"],item["skill"],*item["required"]];optional=item.get("optional",[])
    def sub(path): return path.replace("<engine>",engine) if engine else path
    return [sub(x) for x in required],[sub(x) for x in optional]
def estimate(paths):
    chars=sum((ROOT/p).read_text(encoding="utf-8-sig").__len__() for p in paths if "<engine>" not in p and (ROOT/p).is_file())
    return chars,round(chars/3.5)
def main(argv=None):
    data=load();p=argparse.ArgumentParser(description=__doc__);p.add_argument("route",choices=sorted(data["routes"]));p.add_argument("--engine");p.add_argument("--json",action="store_true");a=p.parse_args(argv)
    req,opt=resolve(a.route,a.engine);missing=[x for x in req if not (ROOT/x).is_file()];chars,tokens=estimate(req)
    report={"route":a.route,"required":req,"optional":opt,"missing":missing,"estimated_characters":chars,"estimated_tokens":tokens}
    if a.json: print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print("READ_REQUIRED")
        for x in req: print(x)
        if opt: print("READ_ONLY_IF_RELEVANT",*opt,sep="\n")
        print(f"ESTIMATED_CONTEXT_TOKENS={tokens}")
    return 1 if missing else 0
if __name__=="__main__":raise SystemExit(main())
