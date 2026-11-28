"""Render the built mockup's screens as PNG files showing only the application stage.

    python render.py [names]      (after build.py; needs Edge or Chrome)

Writes outputs/reference/NAME.png at 1680 x 1050, the size the stage is drawn at. The pictures
are the owner's captures: outputs/ is ignored by Git.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILT = HERE / "outputs" / "setup-page-mockups.html"
OUT = HERE / "outputs" / "reference"
CANDIDATES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
SCREENS = ["equipment", "first", "not-dark", "dark", "bright", "levels", "scale", "motion", "by-hand", "chain", "summary"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    browser = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if browser is None or not BUILT.exists():
        print("Needs a Chromium browser and a built mockup (run build.py first)")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name in args.names or SCREENS:
        png = OUT / f"{name}.png"
        if png.exists():
            png.unlink()
        with tempfile.TemporaryDirectory() as profile:
            subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={profile}", "--virtual-time-budget=3000",
                            "--window-size=1680,1050", f"--screenshot={png}",
                            BUILT.as_uri() + "?bare=1#" + name],
                           capture_output=True, timeout=120)
        print(name, "ok" if png.exists() else "FAILED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
