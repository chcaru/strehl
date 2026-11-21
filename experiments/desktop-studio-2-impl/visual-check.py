"""Render the application's stations offscreen and set each beside its mockup reference.

    python experiments/desktop-studio-2-impl/visual-check.py --exe <Strehl.exe or strehl-ui.exe> --out <scratch dir>

Copies the owner's catalog to the scratch folder (the original is never written), renders each
route at 1680 x 1050 with --offscreen-screenshot, and writes NAME-compare.png: the application on
the left, the mockup reference on the right. The references come from
experiments/desktop-studio-2026-11-20/mockups/render-reference.py (they hold private pictures and
are not in Git). Prints chrome measurements from the application render: the heights of the top
bar and hint bar and the inspector's left edge, found by scanning for the theme's hairlines.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
# Git-ignored (private pictures); worktrees can point at the main checkout's copy with --reference.
REFERENCE = ROOT / "experiments" / "desktop-studio-2026-11-20" / "mockups" / "outputs" / "reference"
RUN = r"C:\Users\chris\Pictures\Strehl\strehl-1793781369068-68052-3"
# name: (extra arguments, reference image)
ROUTES = {
    "library": (["--route", "library"], "library.png"),
    "library-instrument": (["--route", "library", "--theme", "instrument"], "library.png"),
    "library-lightbox": (["--route", "library", "--theme", "lightbox"], "library.png"),
    # Without a name: the open stack's subject, else the most developed one.
    "subject": (["--route", "subject"], "subject.png"),
    "subject-lightbox": (["--route", "subject", "--theme", "lightbox"], "subject.png"),
    "stack": (["--open-run", RUN, "--route", "stack"], "stack.png"),
    "engine": (["--open-run", RUN, "--route", "engine"], "engine-room.png"),
    "develop": (["--open-run", RUN, "--route", "develop"], "develop.png"),
    "export": (["--open-run", RUN, "--route", "export"], "export.png"),
    "capture": (["--route", "capture"], "capture-plan.png"),
    # The Capture station from fabricated states: no camera host is reached.
    "capture-plan": (["--route", "capture", "--capture-fixture", "plan"], "capture-plan.png"),
    "capture-flight": (["--route", "capture", "--capture-fixture", "flight"], "capture-flight.png"),
    "glance": (["--route", "capture", "--capture-fixture", "glance"], "glance.png"),
    "capture-flight-lightbox": (["--route", "capture", "--capture-fixture", "flight", "--theme", "lightbox"],
                                "capture-flight-lightbox.png"),
    "capture-plan-instrument": (["--route", "capture", "--capture-fixture", "plan", "--theme", "instrument"],
                                "capture-plan.png"),
    "capture-plan-lightbox": (["--route", "capture", "--capture-fixture", "plan", "--theme", "lightbox"],
                              "capture-plan.png"),
    "engine-lightbox": (["--open-run", RUN, "--route", "engine", "--theme", "lightbox"], "engine-room.png"),
    "develop-instrument": (["--open-run", RUN, "--route", "develop", "--theme", "instrument"], "develop.png"),
    "develop-lightbox": (["--open-run", RUN, "--route", "develop", "--theme", "lightbox"], "develop.png"),
    "export-lightbox": (["--open-run", RUN, "--route", "export", "--theme", "lightbox"], "export.png"),
    "glance-lightbox": (["--route", "capture", "--capture-fixture", "glance", "--theme", "lightbox"], "glance.png"),
    # The shell's own surfaces over a station (no reference: compare across themes).
    "projects-drawer": (["--open-run", RUN, "--route", "develop", "--overlay", "projects"], "develop.png"),
    "projects-drawer-lightbox": (["--open-run", RUN, "--route", "develop", "--overlay", "projects",
                                  "--theme", "lightbox"], "develop.png"),
    "projects-drawer-instrument": (["--open-run", RUN, "--route", "develop", "--overlay", "projects",
                                    "--theme", "instrument"], "develop.png"),
    "activity-drawer-lightbox": (["--open-run", RUN, "--route", "develop", "--overlay", "activity",
                                  "--theme", "lightbox"], "develop.png"),
    "agent-drawer-lightbox": (["--open-run", RUN, "--route", "develop", "--overlay", "agent",
                               "--theme", "lightbox"], "develop.png"),
    "palette": (["--route", "library", "--overlay", "palette"], "stack-palette.png"),
    "palette-lightbox": (["--route", "library", "--overlay", "palette", "--theme", "lightbox"], "stack-palette.png"),
    "preferences-instrument": (["--route", "library", "--overlay", "preferences", "--theme", "instrument"],
                               "library.png"),
    "stack-instrument": (["--open-run", RUN, "--route", "stack", "--theme", "instrument"], "stack-instrument.png"),
    "stack-lightbox": (["--open-run", RUN, "--route", "stack", "--theme", "lightbox"], "stack-lightbox.png"),
    "stack-plane-held": (["--open-run", RUN, "--route", "stack", "--plane-hold", "128"], "stack-plane-held.png"),
}


def chrome(image):
    """Rows and columns where a full-length hairline differs from its neighbours."""
    px = image.convert("RGB").load()
    w, h = image.size

    def row_is_rule(y):
        a = px[w // 2, y]
        return all(px[x, y] == a for x in range(w // 4, 3 * w // 4, 37))

    rows = [y for y in range(1, h - 1) if row_is_rule(y) and px[w // 2, y] != px[w // 2, y - 1]]
    top = next((y for y in rows if 30 <= y <= 60), None)
    hint = next((h - y for y in reversed(rows) if 15 <= h - y <= 40), None)
    return {"top_bar": top, "hint_bar": hint}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--size", default="1680x1050", help="window size, e.g. 1280x800")
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    catalog_source = Path(os.environ["LOCALAPPDATA"]) / "Strehl" / "projects.json"
    for name in args.names or list(ROUTES):
        extra, reference = ROUTES[name]
        png = args.out / f"{name}.png"
        for stale in (png, args.out / f"{name}.png.log"):
            if stale.exists():
                stale.unlink()
        catalog = args.out / f"{name}.projects.json"
        shutil.copyfile(catalog_source, catalog)
        # A fresh capture settings path keeps every route away from the owner's rig.
        settings = args.out / f"{name}.capture.json"
        if settings.exists():
            settings.unlink()
        command = [str(args.exe), "--offscreen-screenshot", str(png), "--catalog", str(catalog),
                   "--capture-settings", str(settings),
                   "--output-dir", str(args.out / "results"), "--size", args.size, *extra]
        started = time.time()
        with open(args.out / f"{name}.log", "wb") as log:
            try:
                code = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=120).returncode
            except subprocess.TimeoutExpired:
                code = "timeout"
        if not png.exists():
            print(name, "FAILED", code)
            continue
        app = Image.open(png).convert("RGB")
        measured = chrome(app)
        ref_path = args.reference / reference
        if ref_path.exists():
            ref = Image.open(ref_path).convert("RGB").resize(app.size)
            sheet = Image.new("RGB", (app.width * 2 + 8, app.height), (80, 0, 80))
            sheet.paste(app, (0, 0))
            sheet.paste(ref, (app.width + 8, 0))
            sheet.save(args.out / f"{name}-compare.png")
        print(name, "ok", code, f"{time.time() - started:.1f}s", measured)
    return 0


if __name__ == "__main__":
    sys.exit(main())
