"""Drive the built mockup's interactions with synthetic events in a headless browser.

    python check-interactions.py        (after build.py; needs Chrome or Edge)

Loads outputs/strehl-studio-2-mockups.html in a frame (src/check.html), dispatches
pointer and key events at the Stack screen and the shell, and prints one PASS or FAIL
line per check. Exit status 1 if any check fails or none ran. It needs the pictures
and data in outputs/assets: with placeholders the probe has nothing to read.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILT = HERE / "outputs" / "strehl-studio-2-mockups.html"
CANDIDATES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]


def main():
    browser = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if browser is None or not BUILT.exists():
        print("Needs a Chromium browser and a built mockup (run build.py first)")
        return 1
    page = (HERE / "src" / "check.html").read_text(encoding="utf-8").replace("MOCKUP", BUILT.as_uri())
    run = HERE / "outputs" / "check-run.html"
    run.write_text(page, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as profile:
            dom = subprocess.run([browser, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}",
                                  "--allow-file-access-from-files", "--virtual-time-budget=8000",
                                  "--window-size=1760,1400", "--dump-dom", run.as_uri()],
                                 capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    finally:
        run.unlink(missing_ok=True)
    found = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    lines = found.group(1).strip().splitlines() if found else []
    for line in lines:
        print(line.encode("ascii", "replace").decode("ascii"))
    passed = sum(line.startswith("PASS") for line in lines)
    print(f"{passed} of {len(lines)} checks passed")
    return 0 if lines and passed == len(lines) else 1


if __name__ == "__main__":
    sys.exit(main())
