"""Commission orch_abdiff.py: a null and a planted positive.

A differ that draws a montage for identical inputs is worthless, and a differ
that finds a difference is not thereby shown to find it in the RIGHT PLACE.
Both arms are required. The positive arm plants a disc of known amplitude at a
known coordinate and requires the top-ranked site to land on it, which is the
part a "did it detect something" check would miss -- tonight a lane's magenta
counter passed a planted-displacement control and then ranked the wrong subject
7x above the one a human actually saw, because sensitivity was commissioned and
specificity never was.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\bee-1-cpl.tiff"
TOOL = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\orch_abdiff.py"
OUTDIR = r"D:\strehl-out\ORCH-EYE\abdiff-commission"

PLANT_R, PLANT_DN = 60, 900.0


def choose_plant_site(arr, radius, amplitude):
    """Find a site with real headroom, by measurement rather than by guess.

    The first hand-picked site (y=2400, x=3600 on `bee-1-cpl`) had exactly 0 DN
    of headroom -- a bee against a blown white ground -- and the tool refused,
    correctly, because a plant that clips measures clipping and not detection.
    Choosing the site by search is the fix; hard-erroring when no site qualifies
    is what keeps the arm honest if the whole frame is blown.
    """
    full = int(np.iinfo(arr.dtype).max)
    h, w = arr.shape[:2]
    step = 200
    best = None
    for y in range(radius + step, h - radius - step, step):
        for x in range(radius + step, w - radius - step, step):
            win = arr[y - radius:y + radius, x - radius:x + radius, :3]
            head = full - int(win.max())
            if head < amplitude * 1.5:
                continue
            # Prefer a site with some local structure, so the montage shows the
            # plant sitting on real content rather than on a featureless field.
            spread = float(win.std())
            score = spread
            if best is None or score > best[0]:
                best = (score, y, x, head)
    if best is None:
        raise SystemExit(
            "REFUSED: no %dx%d window in this image has %.0f DN of headroom, so "
            "no plant can be made that is not measuring clipping. Choose a "
            "different subject." % (2 * radius, 2 * radius, amplitude * 1.5))
    _score, y, x, head = best
    return y, x, head


def run(a, b, out, extra=()):
    proc = subprocess.run(
        [sys.executable, TOOL, a, b, out] + list(extra),
        capture_output=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).decode("utf-8", "replace")


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("REFUSED: source master not found: %s" % SRC)
    os.makedirs(OUTDIR, exist_ok=True)

    # --- ARM 1: NULL ------------------------------------------------------
    null_out = os.path.join(OUTDIR, "null.jpg")
    if os.path.exists(null_out):
        os.remove(null_out)
    rc, out = run(SRC, SRC, null_out)
    null_ok = ("bit-identical" in out) and (not os.path.exists(null_out)) and rc == 0
    print("=== ARM 1 NULL (A vs A) ===")
    print(out.strip()[-700:])
    print("montage written: %s   (must be False)" % os.path.exists(null_out))
    print("NULL %s" % ("PASS" if null_ok else "FAIL"))
    print()

    # --- ARM 2: PLANTED POSITIVE -----------------------------------------
    arr = tifffile.imread(SRC)
    planted = arr.copy()
    h, w = arr.shape[:2]
    PLANT_Y, PLANT_X, headroom = choose_plant_site(arr, PLANT_R, PLANT_DN)
    yy, xx = np.ogrid[:h, :w]
    disc = (yy - PLANT_Y) ** 2 + (xx - PLANT_X) ** 2 <= PLANT_R ** 2
    print("=== ARM 2 PLANTED POSITIVE ===")
    print("plant: disc r=%d at y=%d x=%d, +%.0f DN, %d px"
          % (PLANT_R, PLANT_Y, PLANT_X, PLANT_DN, int(disc.sum())))
    if not disc.any():
        raise SystemExit("PLANT TARGET NOT FOUND: disc is empty; image is %dx%d" % (h, w))

    print("headroom at site: %d DN (plant is %.0f) -- site chosen by search, "
          "not by hand" % (headroom, PLANT_DN))

    for c in range(3):
        ch = planted[:, :, c]
        ch[disc] = np.clip(ch[disc].astype(np.int64) + int(PLANT_DN),
                           0, np.iinfo(arr.dtype).max).astype(arr.dtype)

    tmp = os.path.join(tempfile.gettempdir(), "abdiff_planted.tiff")
    tifffile.imwrite(tmp, planted)
    pos_out = os.path.join(OUTDIR, "planted.jpg")
    rc, out = run(SRC, tmp, pos_out, ["--sites", "3", "--label-a", "clean",
                                      "--label-b", "planted"])
    print(out.strip()[-1400:])

    top = None
    for line in out.splitlines():
        if line.startswith("site 0:"):
            parts = line.replace("=", " ").split()
            top = (int(parts[parts.index("y") + 1]), int(parts[parts.index("x") + 1]))
    hit = False
    dist = None
    if top is not None:
        dist = ((top[0] - PLANT_Y) ** 2 + (top[1] - PLANT_X) ** 2) ** 0.5
        hit = dist <= 12.0
    print()
    print("top-ranked site: %r   plant centre: (%d, %d)   distance: %s px"
          % (top, PLANT_Y, PLANT_X, "n/a" if dist is None else "%.1f" % dist))
    print("localises to the plant CENTRE (within 12 px): %s" % hit)
    print("  (the criterion is the centre, not merely inside the disc: a box "
          "filter over a uniform disc is a plateau, and an unrefined argmax "
          "lands on its first raster element %d px away, which would still be "
          "'inside' and would still put every crop off the feature)"
          % (PLANT_R - 8))
    pos_ok = rc == 0 and os.path.exists(pos_out) and hit
    print("POSITIVE %s" % ("PASS" if pos_ok else "FAIL"))

    os.remove(tmp)
    print()
    if null_ok and pos_ok:
        print("VERDICT: GREEN -- silent on identical input, and localises a "
              "planted +%.0f DN disc to its exact centre (within 12 px) as its "
              "top-ranked site." % PLANT_DN)
        return 0
    print("VERDICT: RED -- null_ok=%s positive_ok=%s" % (null_ok, pos_ok))
    return 1


if __name__ == "__main__":
    sys.exit(main())
