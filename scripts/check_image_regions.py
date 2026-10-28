"""Check lightweight image-region decisions and review-only candidates.

Usage: python scripts/check_image_regions.py path/to/image_regions.json
Pillow is needed only when invoking this image-specific tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


DECISIONS = {"TRANSLATE", "KEEP", "REVIEW"}
REVIEW_STATES = {"pending", "approved", "rejected"}


def _path(value: str, base: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _region_mask(region: dict, box: list[int], size: tuple[int, int], base: Path,
                 area: str, errors: list[str]) -> Image.Image:
    """The region's pixels: its tight mask when one is given (it must stay inside the box), else the box."""
    result = Image.new("1", size, 0)
    mask_value = region.get("mask")
    if not mask_value:
        ImageDraw.Draw(result).rectangle(tuple(box), fill=1)
        return result
    mask_path = _path(str(mask_value), base)
    if not mask_path.is_file():
        errors.append(f"{area}: mask file missing")
        return result
    with Image.open(mask_path) as im:
        mask_image = im.convert("L")
    if mask_image.size != size:
        errors.append(f"{area}: mask dimensions differ")
        return result
    tight_mask = mask_image.point(lambda value: 255 if value else 0).convert("1")
    ImageDraw.Draw(result).rectangle(tuple(box), fill=1)
    if ImageChops.logical_xor(tight_mask, ImageChops.logical_and(tight_mask, result)).getbbox():
        errors.append(f"{area}: mask extends beyond box")
    return tight_mask


def _alpha_class(image: Image.Image) -> str:
    """opaque, binary (only 0 and 255), or gradient: a candidate must keep the source's kind."""
    if "A" not in image.getbands():
        return "opaque"
    alpha = image.getchannel("A")
    if alpha.getextrema() == (255, 255):
        return "opaque"
    values = {value for _, value in alpha.getcolors(256)}
    return "binary" if values <= {0, 255} else "gradient"


def validate(manifest_path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = data.get("images") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return ["images must be an array"]
    for index, item in enumerate(rows):
        label = f"images[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected object")
            continue
        name = item.get("image")
        source_value = item.get("source")
        if not isinstance(name, str) or not name or not isinstance(source_value, str):
            errors.append(f"{label}: image and source are required")
            continue
        source = _path(source_value, manifest_path.parent)
        if source.name != name or not source.is_file():
            errors.append(f"{label}: source is missing or name does not match")
            continue
        if _sha256(source).lower() != str(item.get("source_sha256", "")).lower():
            errors.append(f"{label}: source_sha256 mismatch")
        regions = item.get("regions")
        if not isinstance(regions, list) or not regions:
            errors.append(f"{label}: regions must be nonempty")
            continue
        with Image.open(source) as im:
            source_image = im.copy()
        allowed = Image.new("1", source_image.size, 0)
        kept = Image.new("1", source_image.size, 0)
        for region_index, region in enumerate(regions):
            area = f"{label}.regions[{region_index}]"
            if not isinstance(region, dict):
                errors.append(f"{area}: expected object")
                continue
            box = region.get("box")
            if (
                not isinstance(box, list)
                or len(box) != 4
                or any(type(v) is not int for v in box)
                or not (0 <= box[0] < box[2] <= source_image.width)
                or not (0 <= box[1] < box[3] <= source_image.height)
            ):
                errors.append(f"{area}: invalid box")
                continue
            decision = region.get("decision")
            if decision not in DECISIONS or not str(region.get("reason", "")).strip():
                errors.append(f"{area}: decision and reason are required")
                continue
            if decision == "TRANSLATE":
                allowed = ImageChops.logical_or(allowed, _region_mask(
                    region, box, source_image.size, manifest_path.parent, area, errors))
                state = region.get("review_status")
                if state not in REVIEW_STATES or not str(region.get("target_text", "")).strip():
                    errors.append(f"{area}: target_text and valid review_status required")
                if state == "approved":
                    if not item.get("candidate") or not region.get("method"):
                        errors.append(f"{area}: approved translation needs candidate and method")
                    if not item.get("candidate_sha256"):
                        errors.append(f"{area}: approved translation needs candidate_sha256")
                    if region.get("visual_reviewed") is not True or region.get("technical_qa") != "pass":
                        errors.append(f"{area}: approval needs direct visual review and technical pass")
                    review = region.get("visual_review")
                    if (not isinstance(review, dict) or review.get("reviewer") != "agent"
                            or review.get("source_opened") is not True
                            or review.get("candidate_opened") is not True
                            or not str(review.get("findings", "")).strip()):
                        errors.append(f"{area}: approval needs an agent visual-review record")
            elif decision == "KEEP":
                kept = ImageChops.logical_or(kept, _region_mask(
                    region, box, source_image.size, manifest_path.parent, area, errors))
        if ImageChops.logical_and(allowed, kept).getbbox():
            errors.append(f"{label}: TRANSLATE and KEEP regions overlap")
        candidate_value = item.get("candidate")
        if candidate_value is None:
            if any(r.get("review_status") == "approved" for r in regions if isinstance(r, dict)):
                errors.append(f"{label}: approved image has no candidate")
            continue
        if not isinstance(candidate_value, str):
            errors.append(f"{label}: candidate must be a path")
            continue
        candidate = _path(candidate_value, manifest_path.parent)
        if not candidate.is_file():
            errors.append(f"{label}: candidate file missing")
            continue
        if item.get("candidate_sha256") and _sha256(candidate).lower() != str(item["candidate_sha256"]).lower():
            errors.append(f"{label}: candidate_sha256 mismatch")
        with Image.open(candidate) as im:
            candidate_image = im.copy()
        if candidate_image.size != source_image.size or candidate_image.mode != source_image.mode:
            errors.append(f"{label}: candidate dimensions or mode differ")
            continue
        if _alpha_class(source_image) != _alpha_class(candidate_image):
            errors.append(f"{label}: transparency changed ({_alpha_class(source_image)} -> "
                          f"{_alpha_class(candidate_image)}); keep the source's alpha kind")
        diff = ImageChops.difference(source_image, candidate_image)
        bands = diff.split()
        changed = bands[0]
        for band in bands[1:]:
            changed = ImageChops.lighter(changed, band)
        outside = ImageChops.multiply(changed, ImageChops.invert(allowed.convert("L")))
        if outside.getbbox():
            errors.append(f"{label}: pixels changed outside TRANSLATE boxes")
        if not allowed.getbbox() and changed.getbbox():
            errors.append(f"{label}: KEEP/REVIEW-only image was altered")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate(args.manifest)
    for error in errors:
        print("ERROR", error)
    print("IMAGE_REGION_STRUCTURE=PASS" if not errors else "IMAGE_REGION_STRUCTURE=FAIL")
    print("SCOPE=hashes, dimensions, mode, decision records, and changed-pixel boundaries only; visual/OCR/native-format QA remains required")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
