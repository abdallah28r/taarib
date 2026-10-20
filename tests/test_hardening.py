import csv, hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    s=importlib.util.spec_from_file_location(name,ROOT/"scripts"/f"{name}.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
capture=load("capture_filter");fmt=load("format_qa")

class HardeningTests(unittest.TestCase):
    def test_visible_short_labels_are_candidates(self):
        self.assertTrue(capture.classify("HP")[0]);self.assertTrue(capture.classify("Save/Load")[0])
    def test_icu_requires_other(self):
        errors,_=fmt.check_pair("{n, plural, one {one} other {many}}","{n, plural, one {واحد}}","x")
        self.assertTrue(any("other" in x for x in errors))
    def test_patch_hash_is_enforced(self):
        script=ROOT/"scripts"/"apply_patch_package.py"
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);root=d/"game";pkg=d/"pkg";root.mkdir();pkg.mkdir();(root/"x").write_bytes(b"old");(pkg/"x").write_bytes(b"wrong")
            manifest={"files":[{"path":"x","original_sha256":hashlib.sha256(b"old").hexdigest(),"patch_sha256":hashlib.sha256(b"expected").hexdigest()}]}
            (pkg/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            result=subprocess.run([sys.executable,str(script),str(root),str(pkg),"--yes"])
            self.assertNotEqual(result.returncode,0);self.assertEqual((root/"x").read_bytes(),b"old")

if __name__=="__main__":unittest.main()
