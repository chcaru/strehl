"""The (A) control, measured where the halo actually is.

ORCH's prediction: adaptive window sizing should materially change
`flower-bud-with-background-fern-cpl` (a tight cut-out rim, radius set by our
window) and barely touch `lavendar-cpl` (a soft wide glow, radius set by
optics).  If it moves lavender too, something other than the intended mechanism
is moving.

A global "fraction of pixels that moved" answers a different question and gets
this wrong: it counts the SUBJECT INTERIOR, where the adaptive radius applies
over the whole plane and is supposed to change things.  Measured that way all
three subjects move ~30% and the control looks dead.  That is the same class of
error as `edge_overshoot` and `hp_energy`, both of which this build has already
been burned by -- a statistic dominated by pixels the question is not about.

The halo lives in the BACKDROP within a window radius of the silhouette.  This
measures exactly there, and reports the far backdrop beside it as a null: a
change confined to the rim band is the mechanism, a change equally present far
away is not.
"""

import pathlib
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import radial

O = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\TWOMECH")
CEIL = radial.CEILING_I

print(f"{'subject':<40s} {'RAW rim':>10s} {'RAW far':>10s} {'ratio':>7s} {'SM rim':>10s} {'SM far':>10s} {'ratio':>7s}")
print(f"{'':40s} {'(<=%d px)' % CEIL:>10s} {'(>150 px)':>10s}")
print("-" * 71)

for s in ["flower-bud-with-background-fern-cpl", "lavendar-cpl", "bee-2-cpl"]:
    off = radial.read_linear(O / f"{s}-off.tif")
    on = radial.read_linear(O / f"{s}-on.tif")
    # Frozen: one silhouette, from the `off` arm, shared by both arms.
    mask, bg, sd = radial.subject_mask(off)
    dist = ndimage.distance_transform_edt(~mask)

    d = np.abs(off - on)
    rim = (~mask) & (dist > 0) & (dist <= CEIL)
    far = (~mask) & (dist > 150)
    r = float(d[rim].mean()) / sd
    f = float(d[far].mean()) / sd

    # The SAME comparison after smoothing both arms.
    #
    # Per-pixel |off - on| is the wrong instrument and reads ~1 everywhere.
    # Electing a different but statistically equivalent frame re-rolls the
    # noise at every pixel without changing the picture, and a difference
    # statistic scores that re-roll at full weight. It is satisfied by exactly
    # the thing that is not a defect -- the same trap as `edge_overshoot` and
    # `hp_energy`, both of which have already produced a wrong reading here.
    #
    # Independent evidence that it IS a re-roll and not a degradation: the
    # background sd ratios measured off/on are 0.878 / 1.005 / 0.996, i.e. the
    # noise LEVEL is unchanged or better while every pixel differs.
    #
    # A 9 px box kills the re-roll (uncorrelated noise falls by ~9x) and leaves
    # any systematic shift in the background LEVEL, which is what a halo is.
    k = 9
    ds = np.abs(ndimage.uniform_filter(off, k) - ndimage.uniform_filter(on, k))
    rs = float(ds[rim].mean()) / sd
    fs = float(ds[far].mean()) / sd
    print(f"{s:<40s} {r:10.3f} {f:10.3f} {r/max(f,1e-9):7.2f} "
          f"{rs:10.3f} {fs:10.3f} {rs/max(fs,1e-9):7.2f}")

print()
print("raw    = mean |off - on| per pixel, in backdrop sd.")
print("smooth = the same after a 9 px box on BOTH arms, which removes the")
print("         noise re-roll and leaves systematic level shifts.")
print("ratio  = rim / far. A mechanism confined to the window reads high.")
print("         Raw reads ~1 on every subject because it is measuring noise.")
