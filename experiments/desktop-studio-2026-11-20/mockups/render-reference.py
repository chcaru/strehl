"""Render the built mockup's screens as 1680 x 1050 reference images, with their geometry.

    python render-reference.py            (after build.py; needs Chrome or Edge)

Writes outputs/reference/NAME.png, one per screen state, showing only the application
stage at 1:1, and outputs/reference/metrics.json: for each state, the rectangle
[x, y, width, height] of the main parts (top bar, control strip, canvas, photograph,
rail, filmstrip, inspector, hint bar and so on) in stage pixels. An implementer lays an
offscreen render of the real application beside the matching image and reads sizes from
the JSON. The images contain the owner's pictures: outputs/ is ignored by Git.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
BUILT = HERE / "outputs" / "strehl-studio-2-mockups.html"
OUT = HERE / "outputs" / "reference"
CANDIDATES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
# name: (screen, state commands, theme)
STATES = {
    "library": ("library", "", ""),
    "library-rig": ("library", "pop:rig", ""),
    "subject": ("subject", "", ""),
    "capture-plan": ("capture", "", ""),
    "capture-flight": ("flight", "", ""),
    "capture-flight-jobs": ("flight", "pop:jobs", ""),
    "glance": ("glance", "", ""),
    "stack": ("stack", "", ""),
    "stack-core-sample-live": ("stack", "hover:0.36,0.40", ""),
    "stack-plane-peek": ("stack", "peek:128", ""),
    "stack-plane-held": ("stack", "hold:128", ""),
    "stack-plane-held-64px": ("stack", "hold:128;size:5", ""),
    "stack-lens-depth": ("stack", "lens:depth", ""),
    "stack-lens-soft": ("stack", "lens:soft", ""),
    "stack-recipe": ("stack", "tab:recipe", ""),
    "stack-renders": ("stack", "tab:renders", ""),
    "stack-palette": ("stack", "pop:palette", ""),
    "engine-room": ("engine", "", ""),
    "develop": ("develop", "", ""),
    "develop-layers": ("develop", "tab:layers", ""),
    "develop-versions": ("develop", "tab:versions", ""),
    "export": ("export", "", ""),
    "stack-instrument": ("stack", "", "instrument"),
    "stack-lightbox": ("stack", "hover:0.36,0.40", "lightbox"),
    "capture-flight-lightbox": ("flight", "", "lightbox"),
}


def chrome(browser, *args):
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                               "--virtual-time-budget=3000", "--window-size=1680,1050", *args],
                              capture_output=True, timeout=120).stdout.decode("utf-8", "replace")


def main():
    browser = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if browser is None or not BUILT.exists():
        print("Needs a Chromium browser and a built mockup (run build.py first)")
        return 1
    wanted = sys.argv[1:] or list(STATES)
    OUT.mkdir(parents=True, exist_ok=True)
    metrics_path = OUT / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    for name in wanted:
        screen, do, theme = STATES[name]
        query = "?bare=1&theme=" + theme + "&do=" + quote(do, safe=":;,.")
        png = OUT / f"{name}.png"
        chrome(browser, f"--screenshot={png}", BUILT.as_uri() + query + "#" + screen)
        dom = chrome(browser, "--dump-dom", BUILT.as_uri() + query + "&dump=1#" + screen)
        found = re.search(r'<pre id="dump">(.*?)</pre>', dom, re.S)
        if found:
            metrics[name] = json.loads(found.group(1).replace("&quot;", '"'))
        print(name, "ok" if png.exists() else "FAILED", len(metrics.get(name, {})), "parts measured")
    metrics_path.write_text(json.dumps(metrics, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
