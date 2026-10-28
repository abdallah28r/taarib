import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


detect_engine = load("detect_engine")
detect_protection = load("detect_protection")
capture_filter = load("capture_filter")


class DiscoveryToolTests(unittest.TestCase):
    def test_detects_unity_il2cpp_and_existing_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "UnityPlayer.dll").touch()
            (root / "GameAssembly.dll").touch()
            metadata = root / "Game_Data" / "il2cpp_data" / "Metadata"
            metadata.mkdir(parents=True)
            (metadata / "global-metadata.dat").touch()
            (root / "BepInEx").mkdir()
            report = detect_engine.detect(root)
            self.assertEqual(report["engine"], "unity")
            self.assertEqual(report["scripting_backend"], "il2cpp")
            self.assertIn("bepinex", report["existing_loaders"])

    def test_protection_marker_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "EasyAntiCheat").mkdir()
            hits = detect_protection.scan(root)
            self.assertIn("Easy Anti-Cheat", hits)

    def test_capture_filter(self):
        self.assertEqual(capture_filter.classify("ui_btn_ok"), (False, "probable-identifier"))
        self.assertEqual(capture_filter.classify("2560 x 1440"), (False, "mostly-numeric"))
        self.assertEqual(capture_filter.classify("Open the door"), (True, "candidate"))
        for overlay in ("FPS: 60", "CPU 45%", "GPU 72°C", "1.2 GHz"):
            self.assertEqual(capture_filter.classify(overlay), (False, "performance-counter"))
        self.assertEqual(capture_filter.classify("Save 5 GB of data now please"), (True, "candidate"))


if __name__ == "__main__":
    unittest.main()
