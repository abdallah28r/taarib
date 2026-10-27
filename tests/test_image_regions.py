from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_image_regions", ROOT / "scripts" / "check_image_regions.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ImageRegionChecks(unittest.TestCase):
    def test_approved_candidate_is_confined_to_translate_box(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            candidate = root / "candidate.png"
            manifest = root / "regions.json"
            Image.new("RGBA", (8, 8), (0, 0, 255, 255)).save(source)
            image = Image.open(source)
            image.putpixel((2, 2), (255, 0, 0, 255))
            image.save(candidate)
            data = {
                "images": [{
                    "image": source.name,
                    "source": source.name,
                    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "candidate": candidate.name,
                    "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    "regions": [{
                        "box": [1, 1, 4, 4],
                        "decision": "TRANSLATE",
                        "reason": "player-facing nameplate",
                        "target_text": "اسم",
                        "method": "deterministic",
                        "review_status": "approved",
                        "visual_reviewed": True,
                        "visual_review": {"reviewer": "agent", "source_opened": True,
                                          "candidate_opened": True, "findings": "Matched source typography; background unchanged."},
                        "technical_qa": "pass",
                    }]
                }]
            }
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MODULE.validate(manifest), [])
            data["images"][0]["regions"][0]["visual_review"].pop("candidate_opened")
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(any("agent visual-review record" in error for error in MODULE.validate(manifest)))
            data["images"][0]["regions"][0]["visual_review"]["candidate_opened"] = True
            mask = root / "mask.png"
            mask_image = Image.new("L", (8, 8), 0)
            mask_image.putpixel((2, 2), 255)
            mask_image.save(mask)
            data["images"][0]["regions"][0]["mask"] = mask.name
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MODULE.validate(manifest), [])
            keep_mask = root / "keep.png"
            keep_image = Image.new("L", (8, 8), 0)
            keep_image.putpixel((3, 3), 255)
            keep_image.save(keep_mask)
            keep = {"box": [1, 1, 4, 4], "decision": "KEEP", "reason": "logo beside the label", "mask": keep_mask.name}
            data["images"][0]["regions"].append(keep)
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MODULE.validate(manifest), [])
            keep_image.putpixel((2, 2), 255)
            keep_image.save(keep_mask)
            self.assertTrue(any("regions overlap" in error for error in MODULE.validate(manifest)))
            data["images"][0]["regions"].pop()
            mask_image.putpixel((2, 2), 0)
            mask_image.save(mask)
            self.assertTrue(any("outside TRANSLATE boxes" in error for error in MODULE.validate(manifest)))
            data["images"][0]["regions"][0].pop("mask")
            data["images"][0]["regions"][0]["box"] = [5, 5, 7, 7]
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(any("outside TRANSLATE boxes" in error for error in MODULE.validate(manifest)))

    def test_keep_image_must_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            candidate = root / "candidate.png"
            manifest = root / "regions.json"
            Image.new("RGBA", (8, 8), (0, 0, 255, 255)).save(source)
            Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(candidate)
            manifest.write_text(json.dumps({"images": [{
                "image": source.name,
                "source": source.name,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "candidate": candidate.name,
                "regions": [{"box": [0, 0, 8, 8], "decision": "KEEP", "reason": "design text"}]
            }]}), encoding="utf-8")
            self.assertTrue(any("KEEP/REVIEW-only" in error for error in MODULE.validate(manifest)))


if __name__ == "__main__":
    unittest.main()
