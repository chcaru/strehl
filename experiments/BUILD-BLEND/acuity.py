"""Is the clamped arm as crisp as ORCH's rung B?

ORCH's anti-gaming clause: a fix that makes the zero-count go green by softening
the subject is a regression.  Any candidate must show the ink "at least as crisp
as rung B does" at (6136, 1360) on dry-erase-marker-head-cpl.

Judging that by eye is necessary but not sufficient, so this puts a number on it.
Two acuity statistics, both computed identically on both arms:

  * **edge acuity** -- the 99.9th percentile of gradient magnitude.  An edge that
    has been softened cannot retain its steepest slopes, so this falls first.
  * **fine-band energy** -- RMS of the crop minus a 2 px blur.  Broadband detail
    loss shows here even where no single edge dominates.

One trap this has to avoid.  The clipped pixels in rung B are *themselves* hard
edges: a solid black block against white paper has an enormous gradient, so a
naive acuity score would REWARD the artifact and report the damaged arm as
sharper.  Both statistics are therefore computed twice -- once over the whole
crop, and once with the clipped pixels and their 8-neighbourhood excluded, so the
comparison is made on the parts of the picture that are actually photograph.
"""

import sys

import numpy as np
import tifffile
from scipy import ndimage

X, Y, S = 6136, 1360, 600


def crop(img):
    return img[Y - S // 2:Y + S // 2, X - S // 2:X + S // 2].astype(np.float64)


def luma(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def stats(y, mask):
    gy, gx = np.gradient(y)
    g = np.hypot(gx, gy)
    fine = y - ndimage.uniform_filter(y, 5)
    return (np.percentile(g[mask], 99.9), np.sqrt((fine[mask] ** 2).mean()))


def main():
    pb, pa = sys.argv[1], sys.argv[2]
    B, A = crop(tifffile.imread(pb)), crop(tifffile.imread(pa))
    yb, ya = luma(B), luma(A)

    # Pixels clipped in EITHER arm, dilated, are excluded from the fair test.
    clip = ((B == 0).any(axis=2)) | ((A == 0).any(axis=2))
    grown = ndimage.binary_dilation(clip, np.ones((3, 3)))
    fair = ~grown
    print(f"crop {S}x{S} at ({X},{Y})")
    print(f"clipped in either arm : {100.0 * clip.mean():.3f}%  "
          f"excluded after dilation : {100.0 * grown.mean():.3f}%")

    for name, m in (("WHOLE crop (clipped blocks INCLUDED - flatters the damaged arm)", 
                     np.ones_like(fair, bool)),
                    ("FAIR   (clipped blocks and their neighbours excluded)", fair)):
        eb, fb = stats(yb, m)
        ea, fa = stats(ya, m)
        print(f"\n{name}")
        print(f"  edge acuity  p99.9 |grad|   BEFORE {eb:9.1f}   AFTER {ea:9.1f}   "
              f"ratio {ea / eb:6.3f}")
        print(f"  fine-band RMS (2 px hp)     BEFORE {fb:9.1f}   AFTER {fa:9.1f}   "
              f"ratio {fa / fb:6.3f}")

    # The clipped blocks carry ringing fringes wider than a 1 px dilation, and
    # that ringing is high-frequency energy credited to the DAMAGED arm.  If the
    # fine-band deficit is contamination it converges toward 1.0 as the excluded
    # neighbourhood grows; if it is genuine softening it plateaus below 1.0.
    # Sweeping is the only way to tell those apart, and reading the sweep is not
    # the same as tuning the mask until it passes.
    print("\nEXCLUSION SWEEP -- does the deficit converge or plateau?")
    print(f"{'dilate':>7} {'excluded':>10} {'edge ratio':>11} {'fine ratio':>11}")
    for r in (1, 2, 3, 5, 8, 12, 16, 24):
        g = ndimage.binary_dilation(clip, np.ones((2 * r + 1, 2 * r + 1)))
        m = ~g
        if m.sum() < 1000:
            break
        eb2, fb2 = stats(yb, m)
        ea2, fa2 = stats(ya, m)
        print(f"{r:>7} {100.0 * g.mean():>9.2f}% {ea2 / eb2:>11.3f} {fa2 / fb2:>11.3f}")

    eb, fb = stats(yb, fair)
    ea, fa = stats(ya, fair)
    ok = (ea / eb) >= 0.98 and (fa / fb) >= 0.98
    print(f"\nANTI-GAMING VERDICT (1 px mask, >= 0.98 on both): "
          f"{'PASS - not softened' if ok else 'FAIL at this mask radius - read the sweep'}")


if __name__ == "__main__":
    main()
