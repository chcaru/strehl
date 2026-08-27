"""Cut TRUE 1:1 crops small enough that the viewer cannot resample them away.

V-EYES commissioned the image viewer with a 1 px grating: it resolved at 400 px
and had collapsed to a flat wash by 600 px. Every visual verdict I reported was
made on 1000 x 1000 crops, i.e. through a 2.5x reduction I did not know was
there. This cuts CROP=380 so the pixels shown are the pixels in the master.

No resize, no sharpening, no grade. 16 -> 8 bit by rounding only. If it looks
soft here it IS soft.
"""
import io
import os
import sys

import numpy as np
import tifffile
from PIL import Image

CROP = 380
SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
DST = r"C:\dev\strehl-out\ORCH-TRUE11"

# (stack, centre x, centre y, why this site)
SITES = [
    ("tweezers-cpl", 2128, 2000, "V-EYES called this one genuinely excellent"),
    ("lavendar-cpl", None, None, "dense trichomes: the hardest fine structure in the corpus"),
    ("bee-3-cpl", None, None, "299 frames, the deepest stack"),
    ("wrapped-text-1", None, None, "known geometry, curvature, printed type"),
]


def best_site(y):
    """Highest mean |Laplacian| tile, so the crop lands where detail exists.

    Deliberately NOT hand-picked: this is also where a stacking failure would
    show worst. The selection cuts both ways on purpose.
    """
    h, w = y.shape
    lap = np.abs(np.diff(y, 2, axis=0)[:, :-2]) + np.abs(np.diff(y, 2, axis=1)[:-2, :])
    s = 64
    hh, ww = lap.shape[0] // s, lap.shape[1] // s
    blk = lap[:hh * s, :ww * s].reshape(hh, s, ww, s).mean(axis=(1, 3))
    # stay clear of the frame edge so the crop is entirely inside the master
    m = CROP // s + 1
    blk[:m, :] = 0
    blk[-m:, :] = 0
    blk[:, :m] = 0
    blk[:, -m:] = 0
    i = int(np.argmax(blk))
    return (i % ww) * s + s // 2, (i // ww) * s + s // 2


def main():
    os.makedirs(DST, exist_ok=True)
    rows = []
    cut = missing = 0
    for name, cx, cy, why in SITES:
        p = None
        for cand in sorted(os.listdir(SRC)):
            if cand.startswith(name) and cand.endswith(".tiff"):
                p = os.path.join(SRC, cand)
                break
        if p is None:
            missing += 1
            rows.append("%-24s MISSING  no master found" % name)
            continue
        cut += 1
        a = tifffile.imread(p)
        y = a[..., 1].astype(np.float32) if a.ndim == 3 else a.astype(np.float32)
        if cx is None:
            cx, cy = best_site(y)
            src = "auto"
        else:
            src = "given"
        x0 = max(0, min(a.shape[1] - CROP, cx - CROP // 2))
        y0 = max(0, min(a.shape[0] - CROP, cy - CROP // 2))
        # A hand-given coordinate that gets clamped is no longer the site the
        # caller asked for. Silence there is how a crop lands 100 px away and
        # is still read as the requested one.
        moved = abs(x0 - (cx - CROP // 2)) + abs(y0 - (cy - CROP // 2))
        c = a[y0:y0 + CROP, x0:x0 + CROP]
        if c.dtype == np.uint16:
            # The clip is load-bearing: (65535 + 128) >> 8 == 256, and casting
            # that to uint8 wraps pure white to BLACK. Shipped unclipped until
            # V-H2H2 found it; it had put 308 black px in tweezers-cpl and 507
            # in lavendar-cpl, both sitting on specular highlights, in the very
            # crops used to judge sharpness. See true11_impact.py.
            c8 = np.clip((c.astype(np.uint32) + 128) >> 8, 0, 255).astype(np.uint8)
        else:
            c8 = np.clip(c, 0, 255).astype(np.uint8)
        out = os.path.join(DST, "%s_%d_%d.png" % (name, x0, y0))
        Image.fromarray(c8).save(out)
        rows.append("%-24s %5s (%5d,%5d) %dx%d%s  %s"
                    % (name, src, x0, y0, CROP, CROP,
                       "" if not moved else "  CLAMPED %d px off site" % moved,
                       why))
    print("\n".join(rows))
    print("\n  partition: cut %d + missing %d = %d of %d sites"
          % (cut, missing, cut + missing, len(SITES)))
    print("\nCROP=%d px, cut with slicing only. Viewer resolves 1px detail to "
          "~400px (V-EYES commissioning), so these are shown unresampled." % CROP)
    if missing:
        # A missing site used to print in the same table as a cut one and exit
        # 0. wrapped-text-1-cpl sat there for the whole campaign and was read
        # as a result. A skipped check must never look like a passed one.
        print("\nFAIL: %d site(s) produced no crop. Not a warning - nothing was "
              "measured there." % missing)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
