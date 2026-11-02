"""Check that a game patch may be built as a shareable package.

A package for the user's own copy needs nothing here. A shareable one needs
`release-clearance.yaml`, filled from the user's own words: the permission to
publish and the content review (references/release.md). This records what the
user stated; it proves nothing and is not legal clearance.

    python scripts/release_clearance.py
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PERMISSION_TYPES = ("publisher-written", "published-policy")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def filled(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def missing(clearance: dict) -> list[str]:
    """What still stops a shareable package, in the words the user sees."""
    permission = clearance.get("permission") or {}
    review = clearance.get("content_review") or {}
    gaps = []
    if permission.get("type") not in PERMISSION_TYPES:
        gaps.append("إذن صاحب اللعبة غير مسجل (release-clearance.yaml: permission.type)")
    if not filled(permission.get("source")):
        gaps.append("مصدر الإذن غير مسجل (release-clearance.yaml: permission.source)")
    if not (isinstance(permission.get("date"), str) and DATE_RE.fullmatch(permission["date"])):
        gaps.append("تاريخ الإذن غير مسجل بصيغة YYYY-MM-DD (release-clearance.yaml: permission.date)")
    if not filled(review.get("target_country")):
        gaps.append("بلد النشر غير مسجل (release-clearance.yaml: content_review.target_country)")
    if not filled(review.get("official_age_rating")):
        gaps.append("التصنيف العمري الرسمي غير مسجل، أو اكتب none (release-clearance.yaml: content_review.official_age_rating)")
    if not isinstance(review.get("sensitive_content"), list):
        gaps.append("قائمة المحتوى الحساس غير مسجلة (release-clearance.yaml: content_review.sensitive_content)")
    if review.get("reviewed_by_user") is not True:
        gaps.append("لم يؤكد المستخدم مراجعة المحتوى (release-clearance.yaml: content_review.reviewed_by_user)")
    return gaps


def load(path: Path) -> dict:
    import yaml
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clearance", type=Path, default=ROOT / "release-clearance.yaml")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    gaps = missing(load(args.clearance))
    for gap in gaps:
        print(f"TODO {gap}")
    print("RELEASE_CLEARANCE=" + ("BLOCKED" if gaps else "RECORDED"))
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
