"""Full-page screenshots of the demo project's pages for the site (Windows, Microsoft Edge).

    python docs/_tools/capture.py <demo folder> [--out docs/assets/screens]

Serves the demo folder on localhost, captures each page with headless Edge at 1280 px wide, and trims
the empty space below the content. Run make_demo.py first.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import subprocess
import tempfile
import threading
from pathlib import Path

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PAGES = ("dashboard", "tasks", "texts", "images")


def trim(path: Path, margin: int = 32) -> None:
    """Cut the uniform background below the last row that differs from it."""
    from PIL import Image, ImageChops
    with Image.open(path) as image:
        image = image.convert("RGB")
        background = Image.new("RGB", image.size, image.getpixel((2, image.height - 2)))
        box = ImageChops.difference(image, background).getbbox()
        if box:
            image.crop((0, 0, image.width, min(image.height, box[3] + margin))).save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("demo", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "screens")
    parser.add_argument("--height", type=int, default=6000)
    args = parser.parse_args()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.demo))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        for page in PAGES:
            target = args.out / f"{page}.png"
            shot = Path(profile) / f"{page}.png"  # Edge does not write to a path with spaces
            subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--blink-settings=preferredColorScheme=1",  # light, like the site
                            "--virtual-time-budget=4000", f"--window-size=1280,{args.height}", f"--user-data-dir={profile}",
                            f"--screenshot={shot}", f"http://127.0.0.1:{server.server_port}/{page}.html"],
                           capture_output=True, check=False)
            if not shot.is_file():
                raise SystemExit(f"Edge wrote no screenshot for {page}")
            shot.replace(target)
            trim(target)
            print(f"SCREEN={target}")
    server.shutdown()


if __name__ == "__main__":
    main()
