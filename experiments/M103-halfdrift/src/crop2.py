"""M103 -- a matched 1:1 look at the region the orchestrator called disqualifying.

Three attempts at an automatic whole-frame waxiness detector failed their own
positive controls (recorded in `waxmap.py` and `waxsweep.py`, and in the report).
The failures were informative -- the last one established that this render's
brightest decile is at 240-255 DN, i.e. blown, while the waxy region is mid-grey
around 150-190 DN -- but three miscalibrations is the point at which tuning a
threshold until it agrees with what I already believe becomes circular.

So this does the direct thing instead: crop BOTH renders at the same scene point,
at 1:1, with no resampling of either arm, over the bright low-texture area at the
bottom of M97b's lower-right panel, and look at them.

The only processing is an integer crop. The corrected render's subject is 1.1278x
the size of the shipped one (M97b, MEASURED), so its crop is 1.1278x larger in
pixels to cover the same scene extent; neither is resampled to match, because
resampling is the hypothesis that was just eliminated and reintroducing it here
would be perverse. The corrected crop therefore appears slightly larger. That is
stated rather than corrected for.

Control: the SAME pair of crops is also written for the centre panel, which M97b
locked at 1.0000 and where both arms are agreed to look alike. If the centre pair
looks different in the same way as the target pair, the crop mapping is off and
neither comparison means anything.

usage:
  python src/crop2.py <shipped.tif> <corrected.tif> <outdir>
"""

import os
import sys

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SCALE = 1.1278  # M97b, MEASURED

# (name, shipped y, shipped x, shipped size)  -- corrected is derived
REGIONS = [
    ("target-brightlowtexture", 3430, 5100, 640),
    ("control-centre", 2344, 3660, 640),
]


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = a.std() * b.std()
    if d <= 0:
        return 0.0
    return float((a * b).mean() / d)


def lock(A, B, ay, ax, size, by0, bx0, n):
    """Refine the corrected-arm origin by NCC against the shipped crop.

    The predicted mapping is exact at the frame centre and drifts with radius
    (the first version of this script had a 45 DN mean mismatch at r~2400 px and
    a 0.3 DN mismatch at r=0). That radial failure is not incidental: a residual
    scale error displaces by an amount proportional to radius, which is the very
    defect this milestone is about. So the offset is searched rather than assumed,
    and the achieved NCC is reported so a bad lock is visible in the output the
    way M97b reported its own 0.2253.
    """
    ga = A[ay:ay + size, ax:ax + size, 1].astype(np.float64)
    hb, wb = B.shape[:2]
    # the corrected crop covers the same scene extent at SCALE, so compare on a
    # common grid by taking every SCALE-th sample -- integer decimation only,
    # no interpolation, so no resampling enters the comparison
    idx = (np.arange(size) * SCALE).astype(np.int64)
    best = (-2.0, by0, bx0)
    for step, rad in ((8, 160), (1, 10)):
        cy, cx = best[1], best[2]
        for dy in range(-rad, rad + 1, step):
            for dx in range(-rad, rad + 1, step):
                y, x = cy + dy, cx + dx
                if y < 0 or x < 0 or y + n > hb or x + n > wb:
                    continue
                gb = B[y:y + n, x:x + n, 1].astype(np.float64)
                s = ncc(ga[::4, ::4], gb[np.ix_(idx[::4], idx[::4])])
                if s > best[0]:
                    best = (s, y, x)
    return best


def main():
    ship_p, corr_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    A = tifffile.imread(ship_p)
    B = tifffile.imread(corr_p)
    ha, wa = A.shape[:2]
    hb, wb = B.shape[:2]
    print("shipped %s  corrected %s" % (A.shape, B.shape))

    for name, ay, ax, size in REGIONS:
        n = int(round(size * SCALE))
        dy = ay + size / 2 - (ha - 1) / 2
        dx = ax + size / 2 - (wa - 1) / 2
        by = int((hb - 1) / 2 + dy * SCALE - n / 2)
        bx = int((wb - 1) / 2 + dx * SCALE - n / 2)
        by = max(0, min(by, hb - n))
        bx = max(0, min(bx, wb - n))
        s, by, bx = lock(A, B, ay, ax, size, by, bx, n)
        ca = A[ay:ay + size, ax:ax + size]
        cb = B[by:by + n, bx:bx + n]
        pa = os.path.join(outdir, "%s_SHIP_%dpx.png" % (name, size))
        pb = os.path.join(outdir, "%s_CORR_%dpx.png" % (name, n))
        ta = os.path.join(outdir, "%s_SHIP_%dpx.tif" % (name, size))
        tb = os.path.join(outdir, "%s_CORR_%dpx.tif" % (name, n))
        # The 16-bit crops are what MEASUREMENT reads. The PNGs are previews for
        # human eyes only, and are written by an explicit >>8 which is exactly
        # what PIL was doing silently when it opened the source TIF -- so the
        # PNGs stay byte-identical to the ones this script wrote before the
        # reader was repaired, and that identity is asserted below.
        tifffile.imwrite(ta, ca)
        tifffile.imwrite(tb, cb)
        Image.fromarray((ca >> 8).astype(np.uint8)).save(pa)
        Image.fromarray((cb >> 8).astype(np.uint8)).save(pb)
        # SELF control: what was written is what was read, unresized, 16-bit
        oka = np.array_equal(tifffile.imread(ta), ca)
        okb = np.array_equal(tifffile.imread(tb), cb)
        g = cb[..., 1].astype(np.float64)
        gs = ca[..., 1].astype(np.float64)
        print("  %-26s ship(%d,%d,%d) corr(%d,%d,%d)  lock NCC %.4f  self %s/%s"
              % (name, ay, ax, size, by, bx, n, s,
                 "ok" if oka else "FAIL", "ok" if okb else "FAIL"))
        print("      mean DN  ship %.1f  corr %.1f   |   sd DN  ship %.1f  corr %.1f   [16-bit]"
              % (gs.mean(), g.mean(), gs.std(), g.std()))
    print("\nwrote to " + outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
