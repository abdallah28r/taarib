import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


shaping = load("arabic_shaping")
font_bank = load("font_bank")
byte_patch = load("byte_patch")
save_guard = load("save_guard")
probe = load("game_probe")
detect = load("detect_engine")


class Temp(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def touch(self, *names):
        for name in names:
            path = self.dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()


class ShapingExtrasTests(unittest.TestCase):
    def test_diacritics_stay_after_their_letter_when_reversed(self):
        visual = shaping.render("بِسْمِ")
        self.assertEqual([hex(ord(c)) for c in visual], ["0xfee2", "0x650", "0xfeb4", "0x652", "0xfe91", "0x650"])

    def test_unrender_restores_logical_text(self):
        for text in ("مرحبا بك في اللعبة", "قال {name} (بهدوء): لا إله", "المستوى ٢٥ و 50%",
                     "<b>تحذير</b> هنا", "بِسْمِ اللهِ"):
            self.assertEqual(shaping.unrender(shaping.render(text)), text)

    def test_marks_one_later(self):
        self.assertEqual(shaping.shift_marks("بِت"), "بتِ")
        self.assertEqual(shaping.shift_marks("بِ"), "ب ِ")
        self.assertEqual(shaping.render("بِت", marks_one_later=True), shaping.shift_marks(shaping.render("بِت")))


class FontBankTests(Temp):
    def test_assign_skips_used_and_command_bytes_and_keeps_the_seed(self):
        bank = font_bank.assign_bank(["ﺍ", "ﺏ"], used_bytes={0x80}, start=0x80)
        self.assertEqual(bank, {"ﺍ": 0x81, "ﺏ": 0x82})
        with self.assertRaises(SystemExit):
            font_bank.assign_bank(["x"] * 200, set())
        text, seed = self.dir / "build.txt", self.dir / "bank.json"
        text.write_text("ﺍﺏ", encoding="utf-8")
        self.assertEqual(font_bank.main(["assign", "--text", str(text), "--seed", str(seed)]), 0)
        first = json.loads(seed.read_text(encoding="utf-8"))
        text.write_text("ﺕﺍﺏ", encoding="utf-8")  # a new letter must not move the old ones
        font_bank.main(["assign", "--text", str(text), "--seed", str(seed)])
        second = json.loads(seed.read_text(encoding="utf-8"))
        self.assertEqual({k: second[k] for k in first}, first)
        self.assertNotIn("FE", second.values())

    def test_dte_counts_pairs(self):
        self.assertEqual(font_bank.suggest_dte("abab", 1), [("ab", 2)])


class BytePatchTests(Temp):
    def test_make_apply_and_refuse_other_versions(self):
        original, built, target = self.dir / "a.bin", self.dir / "b.bin", self.dir / "game.bin"
        original.write_bytes(b"HELLO WORLD" * 50)
        built.write_bytes(b"HELLO WORLD" * 20 + b"HELLO ARABI" + b"HELLO WORLD" * 29 + b"TAIL")
        target.write_bytes(original.read_bytes())
        byte_patch.make_patch(original, built, self.dir / "p.arpatch")
        self.assertTrue(byte_patch.apply_patch(self.dir / "p.arpatch", target).startswith("installed"))
        self.assertEqual(target.read_bytes(), built.read_bytes())
        self.assertTrue((self.dir / "game.bin.ar_old").is_file())
        self.assertEqual(byte_patch.apply_patch(self.dir / "p.arpatch", target), "already-installed")
        other = self.dir / "other.bin"
        other.write_bytes(b"something else")
        with self.assertRaises(RuntimeError):
            byte_patch.apply_patch(self.dir / "p.arpatch", other)

    def test_guarded_edit(self):
        path = self.dir / "x.bin"
        path.write_bytes(bytes.fromhex("00112233"))
        self.assertEqual(byte_patch.patch_bytes(path, 1, b"\x11\x22", b"\xaa\xbb"), "applied")
        self.assertEqual(byte_patch.patch_bytes(path, 1, b"\x11\x22", b"\xaa\xbb"), "already-applied")
        with self.assertRaises(RuntimeError):
            byte_patch.patch_bytes(path, 1, b"\x11\x22", b"\xcc\xdd")


class SaveGuardTests(Temp):
    def test_snapshot_verify_restore_keeps_current_saves(self):
        saves, snap = self.dir / "Saves", self.dir / "snap"
        saves.mkdir()
        (saves / "slot1.sav").write_bytes(b"v1")
        save_guard.snapshot(saves, snap)
        with self.assertRaises(SystemExit):
            save_guard.snapshot(saves, snap)  # never overwritten
        (saves / "slot1.sav").write_bytes(b"v2")
        (saves / "slot2.sav").write_bytes(b"new")
        self.assertEqual(save_guard.changes(saves, snap), {"changed": ["slot1.sav"], "added": ["slot2.sav"], "removed": []})
        aside = save_guard.restore(saves, snap)
        self.assertEqual((saves / "slot1.sav").read_bytes(), b"v1")
        self.assertEqual((aside / "slot2.sav").read_bytes(), b"new")

    def test_refuses_store_sandbox(self):
        with self.assertRaises(SystemExit):
            save_guard.refuse_sandbox(Path("C:/Users/x/AppData/Local/Packages/Game/LocalState"))


class ProbeTests(Temp):
    def test_fonts_logs_and_recording(self):
        (self.dir / "Fonts").mkdir()
        (self.dir / "Fonts" / "ui.fnt").write_text('info face="x"\nchar id=1575 x=0\nchar id=65 x=0\n', encoding="utf-8")
        (self.dir / "Player.log").write_text("Initialize engine version\n", encoding="utf-8")
        fonts = probe.find_fonts(self.dir)
        self.assertEqual(fonts[0]["arabic_chars"], 1)
        self.assertEqual(fonts[0]["verdict"], "partial-arabic")
        logs = probe.discover_logs(self.dir, since=0)
        self.assertIn(self.dir / "Player.log", logs)
        self.assertTrue(probe.belongs(self.dir / "Player.log", self.dir))
        self.assertEqual(probe.generalize(self.dir / "Player.log", self.dir), "{game}/Player.log")

    def test_record_log_writes_once_into_the_profile(self):
        profile = ROOT / "engines" / "telltale.md"
        before = profile.read_text(encoding="utf-8")
        try:
            self.assertTrue(probe.record_log("telltale", "{game}/test-only.log"))
            self.assertFalse(probe.record_log("telltale", "{game}/test-only.log"))
            text = profile.read_text(encoding="utf-8")
            self.assertIn("`{game}/test-only.log`", text.split("## Logs", 1)[1].split("\n## ", 1)[0])
        finally:
            profile.write_text(before, encoding="utf-8")

    def test_launch_needs_permission(self):
        self.assertFalse(probe.launch_allowed())  # the template ships with allow_launch_game: false
        code = probe.main(["--game", str(self.dir), "--launch", str(self.dir / "game.exe")])
        self.assertEqual(code, 2)


class ProbeNamesAndProfilesTests(Temp):
    def test_unity_names_give_the_exact_log_path(self):
        game = self.dir / "Some Game"
        (game / "SomeGame_Data").mkdir(parents=True)
        (game / "SomeGame_Data" / "app.info").write_text("Acme Studio\nStarfall Tale\n", encoding="utf-8")
        log = self.dir / "AppData" / "LocalLow" / "Acme Studio" / "Starfall Tale" / "Player.log"
        log.parent.mkdir(parents=True)
        log.write_text("Initialize engine version\n", encoding="utf-8")
        old = os.environ.get("USERPROFILE")
        os.environ["USERPROFILE"] = str(self.dir)
        try:
            names = probe.game_names(game)
            self.assertEqual((names["unity_company"], names["unity_product"]), ("Acme Studio", "Starfall Tale"))
            self.assertIn(log, probe.exact_candidates(names))
            self.assertTrue(probe.belongs(log, game, probe.name_words(names)))  # folder name alone would miss it
        finally:
            if old is None:
                del os.environ["USERPROFILE"]
            else:
                os.environ["USERPROFILE"] = old

    def test_aliases_and_paths_recorded_in_a_profile(self):
        self.assertEqual(probe.profile_name("rpg-maker-mv"), "rpg-maker")
        self.assertEqual(probe.profile_name("source"), "source-engine")
        profile = ROOT / "engines" / "telltale.md"
        before = profile.read_text(encoding="utf-8")
        (self.dir / "logs").mkdir()
        (self.dir / "logs" / "game.log").write_text("x", encoding="utf-8")
        try:
            probe.record_log("telltale", "{game}/logs/game.log")
            self.assertEqual(probe.profile_log_paths("telltale", self.dir), [self.dir / "logs" / "game.log"])
        finally:
            profile.write_text(before, encoding="utf-8")

    def test_new_engine_profile_passes_the_structure_check_and_joins_the_catalog(self):
        engine = "zz-test-engine"
        profile = ROOT / "engines" / f"{engine}.md"
        catalog = ROOT / "tools" / "open-source-tools.json"
        before = catalog.read_text(encoding="utf-8")
        try:
            probe.create_profile(engine, {"scores": {"unity": 3}}, [])
            self.assertTrue(profile.is_file())
            self.assertEqual(json.loads(catalog.read_text(encoding="utf-8"))["engines"][engine], [])
            knowledge = load("check_knowledge")
            import contextlib, io
            folder = self.dir / "engines"
            folder.mkdir()
            (folder / profile.name).write_text(profile.read_text(encoding="utf-8"), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sys.argv = ["check_knowledge", str(folder)]
                self.assertFalse(knowledge.main())
            self.assertTrue(probe.record_log(engine, "{game}/output.log"))
            with self.assertRaises(ValueError):
                probe.create_profile("Bad Name", {"scores": {}}, [])
        finally:
            profile.unlink(missing_ok=True)
            catalog.write_text(before, encoding="utf-8")


class ScriptsIndexTests(unittest.TestCase):
    def test_every_script_has_a_line_in_the_index(self):
        index = (ROOT / "references" / "scripts.md").read_text(encoding="utf-8")
        scripts = [p.name for p in (ROOT / "scripts").glob("*.py")]
        scripts += ["maintainer/" + p.name for p in (ROOT / "scripts" / "maintainer").glob("*.py")]
        self.assertEqual([s for s in scripts if f"`{s}`" not in index], [], "add a line to references/scripts.md")
        self.assertIn("references/scripts.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))


class EngineMarkersConfigTests(unittest.TestCase):
    def test_markers_file_is_valid(self):
        config = json.loads((ROOT / "config" / "engine-markers.json").read_text(encoding="utf-8"))
        for engine, markers in config["engines"].items():
            self.assertRegex(engine, r"^[a-z0-9][a-z0-9-]+$")
            self.assertTrue(markers and all(isinstance(w, int) and w > 0 for w in markers.values()), engine)
            self.assertTrue(all(m == m.lower() for m in markers), f"{engine}: markers are lowercase")
        self.assertEqual(detect.MARKERS, config["engines"])


class NewEngineDetectionTests(Temp):
    def test_each_new_engine_is_recognized(self):
        layouts = {
            "monogame-xna": ["MonoGame.Framework.dll", "Content/a.xnb", "Game.runtimeconfig.json"],
            "scumm-scummvm": ["audio/speech.info", "localization/uiText.info", "Monkey1.pak"],
            "grime-emi": ["Monkey4.exe", "artAll.m4b"],
            "telltale": ["Pack/1_data.ttarch", "english.langdb"],
            "dinky": ["Weird.ggpack1a", "Weird.ggpack2a"],
            "android-apk": ["game.apk"],
            "ps1": ["game.cue", "SYSTEM.CNF"],
            "ps2": ["SYSTEM.CNF", "SLUS_123.45"],
        }
        for engine, files in layouts.items():
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in files:
                    (root / name).parent.mkdir(parents=True, exist_ok=True)
                    (root / name).touch()
                cnf = root / "SYSTEM.CNF"
                if cnf.exists():
                    cnf.write_text("BOOT2 = cdrom0:\\SLUS_123.45;1\n" if engine == "ps2" else "BOOT = cdrom:\\SLUS_000.01;1\n")
                self.assertEqual(detect.detect(root)["engine"], engine)


class ImageAlphaTests(Temp):
    def test_transparency_kind(self):
        from PIL import Image
        regions = load("check_image_regions")
        self.assertEqual(regions._alpha_class(Image.new("RGB", (2, 2))), "opaque")
        binary = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        binary.putpixel((1, 0), (0, 0, 0, 255))
        self.assertEqual(regions._alpha_class(binary), "binary")
        binary.putpixel((0, 0), (0, 0, 0, 128))
        self.assertEqual(regions._alpha_class(binary), "gradient")


if __name__ == "__main__":
    unittest.main()
