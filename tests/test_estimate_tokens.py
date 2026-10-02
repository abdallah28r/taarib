import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "estimate_tokens", ROOT / "scripts" / "estimate_tokens.py"
)
estimate_tokens = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(estimate_tokens)


class EstimateTokenTests(unittest.TestCase):
    def test_estimate_is_positive_and_cjk_costs_more_per_character(self):
        self.assertGreater(estimate_tokens.estimate_text("Hello world"), 0)
        self.assertGreater(
            estimate_tokens.estimate_text("日本語日本語"),
            estimate_tokens.estimate_text("abcdef"),
        )

    def test_reads_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("id,source,target\n1,Hello,\n", encoding="utf-8")
            self.assertEqual(estimate_tokens.read_sources(path, "source"), ["Hello"])


if __name__ == "__main__":
    unittest.main()
