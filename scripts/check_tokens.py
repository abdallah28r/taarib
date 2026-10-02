"""Backward-compatible entry point. Prefer scripts/loc_qa.py for new work."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loc_qa import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
