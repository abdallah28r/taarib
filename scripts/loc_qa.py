"""Non-destructive localization QA."""
import argparse,csv,json,re,unicodedata
from collections import Counter
from pathlib import Path
PRINTF_RE=re.compile(r"%(?:(?:[0-9]+)\$)?[-+# 0']*(?:[0-9]+|\*)?(?:\.[0-9]+|\.\*)?(?:hh|h|ll|l|L|z|j|t)?[diuoxXfFeEgGaAcspn%]")
SIMPLE_RE=re.compile(r"\$\([^()\r\n]+\)|</?[A-Za-z][^<>\r\n]*>|\\(?:[nrt\\\"']|u[0-9A-Fa-f]{4}|x[0-9A-Fa-f]{2})|\[/?(?:b|i|u|s|color|size|font|url|img|sprite|icon)(?:=[^\]\r\n]+)?\]",re.I)
PROFILE_RES={
 "rpgmaker":re.compile(r"\\[A-Za-z]+\[[^\]\r\n]*\]|\\[{}$.|!><^]"),
 "paradox":re.compile(r"\[[^\[\]\r\n]*\]|\$[^$\r\n]*\$|@[A-Za-z0-9_:.]+!|#[A-Za-z][A-Za-z0-9_;]*|#!"),
 "renpy":re.compile(r"\[[^\]\r\n]+\]"),
}
ARABIC_RE=re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
LATIN_WORD_RE=re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
MOJIBAKE=("ï»¿","Ø§","Ù„","ï¿½","�")
def _braces(s):
 out=[];start=None;depth=0
 for i,c in enumerate(s or ""):
  if c=="{" and depth==0:start=i
  if c=="{":depth+=1
  elif c=="}" and depth:
   depth-=1
   if depth==0 and start is not None:out.append(s[start:i+1]);start=None
 return out
def tokens(text,profile="generic"):
 found=[];masked=list(text or "");cursor=0
 for item in _braces(text or ""):
  found.append(item);first=(text or "").find(item,cursor);cursor=first+len(item)
  for i in range(first,first+len(item)):masked[i]=" "
 clean="".join(masked)
 found += [m.group(0) for m in PRINTF_RE.finditer(clean) if m.group(0)!="%%"]
 found += [m.group(0) for m in SIMPLE_RE.finditer(clean)]
 found += re.findall(r"%[0-9]+",clean)
 if profile in PROFILE_RES:found += [m.group(0) for m in PROFILE_RES[profile].finditer(clean)]
 return Counter(found)
def iter_files(path):
 if path.is_file():yield path;return
 for p in ("*.csv","*.tsv","*.json","*.yaml","*.yml"):yield from sorted(path.rglob(p))
def read_text(path):
 data=path.read_bytes()
 if b"\x00" in data[:4096]:raise ValueError("binary/UTF-16 input; convert explicitly")
 return data.decode("utf-8-sig")
def check_table(path,a):
 e=w=r=0;d="\t" if path.suffix.lower()==".tsv" else ",";reader=csv.DictReader(read_text(path).splitlines(keepends=True),delimiter=d)
 miss={a.id_column,a.source_column,a.target_column}-set(reader.fieldnames or [])
 if miss:print(f"ERROR {path}: missing columns {sorted(miss)}");return 1,0,0
 seen={}
 for ln,row in enumerate(reader,2):
  r+=1;ident=(row.get(a.id_column) or "").strip();src=row.get(a.source_column) or "";tgt=row.get(a.target_column) or "";label=ident or f"line {ln}"
  if not ident:e+=1;print(f"ERROR {path}:{ln} empty ID")
  elif ident in seen:e+=1;print(f"ERROR {path}:{ln} duplicate ID {ident!r}")
  else:seen[ident]=ln
  if not tgt.strip():w+=1;print(f"WARN  {path}:{ln} [{label}] untranslated");continue
  st,tt=tokens(src,a.profile),tokens(tgt,a.profile)
  if st!=tt:e+=1;print(f"ERROR {path}:{ln} [{label}] token mismatch missing={dict(st-tt)} extra={dict(tt-st)}")
  if unicodedata.normalize("NFC",tgt)!=tgt:w+=1;print(f"WARN  {path}:{ln} [{label}] target is not NFC-normalized")
  if any("\uFB50"<=c<="\uFDFF" or "\uFE70"<=c<="\uFEFF" for c in tgt):w+=1;print(f"WARN  {path}:{ln} [{label}] Arabic presentation forms")
  if "\u0640" in tgt:w+=1;print(f"WARN  {path}:{ln} [{label}] tatweel used")
  if any(c in tgt for c in "\u202A\u202B\u202D\u202E"):w+=1;print(f"WARN  {path}:{ln} [{label}] BiDi override; prefer isolates")
  if any(x in tgt for x in MOJIBAKE):e+=1;print(f"ERROR {path}:{ln} [{label}] possible mojibake")
  if a.require_arabic and not ARABIC_RE.search(tgt) and src!=tgt:w+=1;print(f"WARN  {path}:{ln} [{label}] target has no Arabic letters")
  if "linebreaks" in a.checks and src.count("\n")!=tgt.count("\n"):w+=1;print(f"WARN  {path}:{ln} [{label}] line-break count changed {src.count(chr(10))}->{tgt.count(chr(10))}")
  if "latin" in a.checks:
   source_words={x.lower() for x in LATIN_WORD_RE.findall(src)};target_words={x.lower() for x in LATIN_WORD_RE.findall(tgt)};extra=sorted(target_words-source_words)
   if extra:w+=1;print(f"WARN  {path}:{ln} [{label}] Latin words not present in source: {extra}")
  if "unchanged" in a.checks and src.strip()==tgt.strip() and ARABIC_RE.search(src) is None:w+=1;print(f"WARN  {path}:{ln} [{label}] target is unchanged from source")
  if "article" in a.checks and re.search(r"(?:^|\s)ال(?:\s|$)",tgt):w+=1;print(f"WARN  {path}:{ln} [{label}] detached Arabic article")
  if len(src)>=8 and len(tgt)/len(src)>a.max_expansion:w+=1;print(f"WARN  {path}:{ln} [{label}] expansion exceeds {a.max_expansion:g}x")
 return e,w,r
def check_structured(path):
 text=read_text(path)
 if path.suffix.lower()==".json":json.loads(text)
 else:
  try:import yaml;yaml.safe_load(text)
  except ImportError:return 0,1,0
 return 0,0,0
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("path",type=Path);p.add_argument("--profile",choices=["generic",*PROFILE_RES],default="generic");p.add_argument("--id-column",default="id");p.add_argument("--source-column",default="source");p.add_argument("--target-column",default="target");p.add_argument("--require-arabic",action="store_true");p.add_argument("--max-expansion",type=float,default=3);p.add_argument("--checks",default="linebreaks,latin,unchanged,article",help="comma-separated warning checks: linebreaks,latin,unchanged,article");a=p.parse_args(argv);a.checks={x.strip() for x in a.checks.split(",") if x.strip()}
 if not a.path.exists():print(f"ERROR path does not exist: {a.path}");return 2
 e=w=r=f=0
 for x in iter_files(a.path):
  f+=1
  try:y,z,q=check_table(x,a) if x.suffix.lower() in (".csv",".tsv") else check_structured(x)
  except (UnicodeDecodeError,csv.Error,json.JSONDecodeError,ValueError) as ex:y,z,q=1,0,0;print(f"ERROR {x}: {ex}")
  e+=y;w+=z;r+=q
 if not f:print(f"ERROR no supported files found under {a.path}");return 2
 print(f"FILES={f} ROWS={r} ERRORS={e} WARNINGS={w}");return 1 if e else 0
if __name__=="__main__":raise SystemExit(main())
