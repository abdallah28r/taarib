"""Generate expanded or pseudo-RTL previews while preserving protected syntax."""
import argparse,csv,re
TOKEN=re.compile(r"\{[^{}\r\n]+\}|%\d*\$?[+#0\- ]*\d*(?:\.\d+)?[a-zA-Z%]|</?[A-Za-z][^<>\r\n]*>|\\[nrt\\]|\[[^\]\r\n]+\]|\$\([^()\r\n]+\)")
def pseudo(s,mode):
 parts=[];last=0
 for m in TOKEN.finditer(s):
  chunk=s[last:m.start()]
  parts.append(''.join(ch*2 if mode=='expanded' and ch.isalpha() else ch for ch in chunk))
  parts.append(m.group(0));last=m.end()
 chunk=s[last:];parts.append(''.join(ch*2 if mode=='expanded' and ch.isalpha() else ch for ch in chunk))
 out=''.join(parts)
 return '\u2067'+out+'\u2069' if mode=='rtl' else out
def main():
 p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("output");p.add_argument("--mode",choices=["expanded","rtl"],default="expanded");a=p.parse_args()
 with open(a.input,encoding="utf-8-sig",newline="") as i,open(a.output,"w",encoding="utf-8",newline="") as o:
  r=csv.DictReader(i);w=csv.DictWriter(o,fieldnames=r.fieldnames);w.writeheader()
  for row in r:
   row["target"]=pseudo(row.get("source",""),a.mode);w.writerow(row)
if __name__=="__main__":main()
