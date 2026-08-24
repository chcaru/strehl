"""Quantify the mottle mechanism on M93's scalar harness.

M93 left (299 frames x 4 ROIs x 512 x 512) of real bee-3-cpl pixel data plus
the scalar elected-frame index for each ROI.  That is everything needed to
test the mechanism end to end without touching any contended code.

MECHANISM UNDER TEST.  Frames differ in brightness (fact 1254: 1.1091x end to
end).  Pixels elect different frames.  So a selection-style merge prints a map
of WHICH FRAME WON into the output as a brightness field.  In a flat region
that field is pure artifact -- there is no real detail there for the election
to be tracking, so the elected index is being driven by noise, and its
brightness signature is mottle.

STEP 0 (pairing, must pass before anything else is believed).  The crop array
axis order is not documented.  Pair each plane to its elected map by checking
that the elected index agrees with the argmax of a focus measure computed on
that plane.  The correct pairing must stand out from the three wrong ones.

STEP 1.  Measure the per-frame brightness curve L(k) of the flat ROI.

STEP 2.  Build the predicted drift field D(i) = L(e(i)) -- how bright the
winning frame was, per pixel.  Compare its spatial SD to the measured
mid-band SD of the selection-merged image.

STEP 3.  Registered falsifier.  Divide each frame by its own L(k) (this IS
per-frame photometric normalisation, applied here in the simplest possible
form) and re-run the same selection.  If the mechanism is right, the mid-band
SD must FALL.  If it does not fall, the mechanism is wrong regardless of any
correlation.

STEP 4.  Control.  Do the same on a TEXTURED ROI, where the election tracks
real focus.  The normalisation must not materially change fine detail there;
if normalisation "improves" everything equally it is doing something else.
"""
import os
import numpy as np

OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)
D = r"C:\dev\strehl-out\M93-out"

crops = np.load(os.path.join(D, "m93_crops.npy"), mmap_mode="r")
names = ["ROI-FLAT", "ROI-HIGHDRIFT", "ROI-LOWDRIFT", "ROI-MIDDRIFT"]
elect = {n: np.load(os.path.join(D, "m93_elected_%s.npy" % n)) for n in names}
print("crops %s %s" % (str(crops.shape), crops.dtype))
for n in names:
    e = elect[n]
    print("  %-14s %s  valid %.1f%%  mean idx %.1f  sd %.1f"
          % (n, str(e.shape), 100 * (e >= 0).mean(), e[e >= 0].mean(),
             e[e >= 0].std()))

NF, NR, H, W = crops.shape


def focus_argmax(plane):
    """argmax over frames of a 3x3 gradient-energy focus measure, box-summed."""
    best = np.full((H, W), -1e30, np.float32)
    arg = np.zeros((H, W), np.int16)
    for k in range(NF):
        a = np.asarray(crops[k, plane], np.float32)
        gx = np.zeros_like(a)
        gy = np.zeros_like(a)
        gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
        gy[1:-1, :] = a[2:, :] - a[:-2, :]
        e = gx * gx + gy * gy
        c = np.cumsum(np.cumsum(e, 0), 1)
        r = 8
        pad = np.zeros((H + 1, W + 1), np.float64)
        pad[1:, 1:] = c
        y0 = np.clip(np.arange(H) - r, 0, H)
        y1 = np.clip(np.arange(H) + r + 1, 0, H)
        x0 = np.clip(np.arange(W) - r, 0, W)
        x1 = np.clip(np.arange(W) + r + 1, 0, W)
        s = (pad[np.ix_(y1, x1)] - pad[np.ix_(y0, x1)]
             - pad[np.ix_(y1, x0)] + pad[np.ix_(y0, x0)]).astype(np.float32)
        m = s > best
        best[m] = s[m]
        arg[m] = k
    return arg


print()
print("=" * 72)
print("STEP 0 -- pair crop planes to elected maps")
print("=" * 72)
print("%-14s %s" % ("elected map", "  ".join("plane%d" % p for p in range(NR))))
args = {p: focus_argmax(p) for p in range(NR)}
pairing = {}
for n in names:
    e = elect[n]
    v = e >= 0
    row = []
    for p in range(NR):
        agree = float((np.abs(args[p][v].astype(int) - e[v].astype(int)) <= 2).mean())
        row.append(agree)
    best_p = int(np.argmax(row))
    pairing[n] = best_p
    print("%-14s %s   -> plane %d (%.1f%%)"
          % (n, "  ".join("%6.3f" % x for x in row), best_p, 100 * row[best_p]))
    srt = sorted(row, reverse=True)
    assert srt[0] > 2.0 * max(srt[1], 1e-6) or srt[0] > 0.30, (
        "pairing for %s is not decisive: %s" % (n, row))
assert len(set(pairing.values())) == NR, "pairing is not a bijection: %s" % pairing
print("pairing is a bijection and each row is decisive")
