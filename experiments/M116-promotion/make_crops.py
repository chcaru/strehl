"""Before/after crops for campaign 6: --photometric OFF vs ON.

The deliverable for this milestone is a report AND pictures. A number the owner
cannot see is not evidence he can act on.

Three crop regions, chosen from the measurement rather than by eye so that the
selection cannot be accused of being curated:

  worst   the background window where --photometric raised fine-scale structure
          most (x=400, y=656, +25.7 percent). If the correction has a visible
          cost, it is here.
  best    the background window where it helped most (x=656, y=1552, -6.2
          percent). Showing only the worst window would be a curated set, so
          the arm's best case gets equal billing at equal size.
  detail  a subject region, because the thing that would make a background win
          worthless is detail lost on the bee itself.

Both arms of every pair are stretched with ONE shared mapping computed from the
OFF arm. Per-image autostretch would rescale the two arms differently and
manufacture a difference from nothing -- the single most common way an A/B crop
lies.

Writes PNGs to C:/dev/strehl-out/M116/. Reads nothing on D:.
"""

import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = r"C:\dev\strehl-out\M116\invariant"
OUT = r"C:\dev\strehl-out\M116"
S = 256

REGIONS = [
    ("worst", 400, 656, "background window with the LARGEST harm (+25.7% fine structure)"),
    ("best", 656, 1552, "background window with the LARGEST gain (-6.2% fine structure)"),
    ("detail", 1552, 1680, "subject detail -- the region a background win must not cost"),
]


def guard(cond, msg):
    if not cond:
        print("GUARD: " + msg)
        sys.exit(3)


def load(path):
    a = tifffile.imread(path)
    guard(a.dtype == np.uint16,
          "%s read as %s, expected uint16 (fact 1615)" % (os.path.basename(path), a.dtype))
    return a


def shared_stretch(ref_win):
    """One mapping, computed from the OFF arm, applied to both arms.

    Percentile endpoints rather than min/max so a single hot pixel cannot set
    the scale for the whole crop.
    """
    lo = float(np.percentile(ref_win, 0.5))
    hi = float(np.percentile(ref_win, 99.5))
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def to8(win, lo, hi):
    x = (win.astype(np.float64) - lo) / (hi - lo)
    return np.clip(x * 255.0, 0, 255).astype(np.uint8)


def label(img, text, sub):
    w, h = img.size
    canvas = Image.new("RGB", (w, h + 46), (18, 18, 18))
    canvas.paste(img, (0, 46))
    d = ImageDraw.Draw(canvas)
    d.text((8, 6), text, fill=(255, 255, 255))
    d.text((8, 24), sub, fill=(170, 170, 170))
    return canvas


def main():
    p0 = load(os.path.join(SRC, "bee-3-cpl__P0-default.tif"))
    p1 = load(os.path.join(SRC, "bee-3-cpl__P1-photometric.tif"))
    guard(p0.shape == p1.shape, "arms differ in shape")
    os.makedirs(OUT, exist_ok=True)

    manifest = []
    for name, x, y, why in REGIONS:
        guard(y + S <= p0.shape[0] and x + S <= p0.shape[1],
              "region %s at (%d,%d) falls outside %s" % (name, x, y, p0.shape))
        w0 = p0[y:y + S, x:x + S, :3]
        w1 = p1[y:y + S, x:x + S, :3]

        lo, hi = shared_stretch(w0)
        a = Image.fromarray(to8(w0, lo, hi)).resize((S * 2, S * 2), Image.NEAREST)
        b = Image.fromarray(to8(w1, lo, hi)).resize((S * 2, S * 2), Image.NEAREST)

        a = label(a, "OFF  (shipped default)", "%s  (%d,%d) 256px @2x" % (name, x, y))
        b = label(b, "ON   (--photometric)", why)

        pair = Image.new("RGB", (a.width + b.width + 12, a.height), (18, 18, 18))
        pair.paste(a, (0, 0))
        pair.paste(b, (a.width + 12, 0))
        path = os.path.join(OUT, "PHOTOMETRIC-%s-OFF-vs-ON.png" % name)
        pair.save(path)

        # Report the stretch endpoints: a reader must be able to confirm both
        # halves were mapped identically.
        manifest.append({"region": name, "x": x, "y": y,
                         "stretch_lo": lo, "stretch_hi": hi,
                         "shared_stretch_from": "P0 (OFF arm)", "path": path})
        print("wrote %s   shared stretch [%.0f, %.0f] from the OFF arm"
              % (os.path.basename(path), lo, hi))

    with open(os.path.join(OUT, "photometric-crops.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)


if __name__ == "__main__":
    main()
