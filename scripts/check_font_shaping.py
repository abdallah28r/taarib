"""Shape an Arabic smoke-test with HarfBuzz and report glyph coverage."""
from __future__ import annotations
import argparse, json
from pathlib import Path

SAMPLE="العربية لا لغة رائعة 123 HP"
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("font",type=Path);p.add_argument("--text",default=SAMPLE);p.add_argument("--json",type=Path);a=p.parse_args(argv)
    try: import uharfbuzz as hb
    except ImportError: print("ERROR uharfbuzz is required");return 2
    data=a.font.read_bytes();face=hb.Face(data);font=hb.Font(face);buf=hb.Buffer();buf.add_str(a.text);buf.guess_segment_properties();hb.shape(font,buf)
    glyphs=[x.codepoint for x in buf.glyph_infos];missing=sum(x==0 for x in glyphs)
    report={"font":str(a.font.resolve()),"direction":buf.direction,"script":buf.script,"language":buf.language,"input_characters":len(a.text),"glyphs":len(glyphs),"missing_glyphs":missing,"warning":"Successful shaping does not prove the game uses this font or renderer path."}
    text=json.dumps(report,ensure_ascii=False,indent=2);print(text)
    if a.json:a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(text,encoding="utf-8")
    return 1 if missing else 0
if __name__=="__main__":raise SystemExit(main())
