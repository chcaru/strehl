"""Price STREHL_COVER, and say by what MECHANISM.

The two masters differ in exactly one switch: COVER=on reproduces the SHIP-V4
master bit-for-bit (coveridentity.py), COVER=0 is the same binary, same solve,
same pinned exposure. So anything measured between them is COVER's.

COVER crops the field of view to 0.9475 and upsamples back to the same output
dimensions. That is a magnification, and a magnification alone must LOWER mean
gradient per pixel: the same edge is spread over more pixels. If the measured
gradient goes UP instead, the resample kernel is adding overshoot, and that is
ringing rather than sharpening.

Two statistics are read side by side on the SAME matched patches:
  orig_detail  mean|grad|, orch_sharp1to1's statistic. Not amplitude-invariant.
  acutance     E(HI)/E(LO), amplitude-invariant. Immune to any tone difference.

COMMISSIONING. The ratio is exercised against a null and BOTH signs of plant --
a defect AND an improvement -- because a suite that plants only degradations
cannot tell a blind statistic from a perverse one. That is the failure that
produced statistic B in this project and it is not repeated here.
"""
import os, sys
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, acutance, orig_detail, register, blur, usm

OFF = r"C:\dev\strehl-out\V-GATHER\sharp\wrapped-text-1\MASTER.tiff"
ON = r"C:\dev\strehl-out\V-GATHER\cover\wrapped-text-1\MASTER_COVERON.tiff"
P = 96
FIT_SEARCH = 288       # corner displacement at 1.055x on this frame is ~234 px
REFINE = 12
CORR_MIN = 0.55
STD_FLOOR = 250.0


def sites(y0, stride, h, w, margin):
    return [(y, x) for y in range(margin, h - margin - P, stride)
            for x in range(margin, w - margin - P, stride)]


def fit_scale(a, b):
    """Empirically measure the magnification. Not read from the render log."""
    h, w = a.shape
    pts = []
    for (y, x) in sites(0, 512, h, w, FIT_SEARCH + 32):
        ref = a[y:y + P, x:x + P]
        if float(ref.std()) < STD_FLOOR:
            continue
        win = b[y - FIT_SEARCH:y + P + FIT_SEARCH, x - FIT_SEARCH:x + P + FIT_SEARCH]
        dy, dx, c = register(ref, win, FIT_SEARCH)
        if c < CORR_MIN:
            continue
        pts.append((y + P / 2, x + P / 2, dy, dx, c))
    pts = np.array([(py, px, dy, dx) for py, px, dy, dx, _ in pts], float)
    corrs = np.array([c for *_, c in [(0, 0, 0, 0, p[4]) for p in []]]) if False else None
    ay, by = np.polyfit(pts[:, 0], pts[:, 2], 1)
    ax, bx = np.polyfit(pts[:, 1], pts[:, 3], 1)
    sy, sx = 1 + ay, 1 + ax
    oy, ox = -by / ay, -bx / ax
    ry = pts[:, 2] - (ay * pts[:, 0] + by)
    rx = pts[:, 3] - (ax * pts[:, 1] + bx)
    return sy, sx, oy, ox, len(pts), float(np.abs(ry).max()), float(np.abs(rx).max())


def matched(a, b, sy, sx, oy, ox, stride=384, margin=420):
    """Patch pairs registered by INTEGER shift only, predicted then refined."""
    h, w = a.shape
    out = []
    for (y, x) in sites(0, stride, h, w, margin):
        ref = a[y:y + P, x:x + P]
        if float(ref.std()) < STD_FLOOR:
            continue
        py = int(round((sy - 1) * (y + P / 2 - oy)))
        px = int(round((sx - 1) * (x + P / 2 - ox)))
        yy, xx = y + py, x + px
        if yy < REFINE or xx < REFINE or yy + P + REFINE > h or xx + P + REFINE > w:
            continue
        win = b[yy - REFINE:yy + P + REFINE, xx - REFINE:xx + P + REFINE]
        dy, dx, c = register(ref, win, REFINE)
        if c < CORR_MIN:
            continue
        out.append((ref, b[yy + dy:yy + dy + P, xx + dx:xx + dx + P], c))
    return out


def ratios(pairs, plant=None):
    od, ac = [], []
    for ref, mov, _ in pairs:
        m = mov
        if plant == "blur":
            m = blur(m, 0.8)
        elif plant == "usm":
            m = usm(m, 0.8, 1.0)
        do, dm = orig_detail(ref), orig_detail(m)
        ao, am = acutance(ref), acutance(m)
        if do > 0:
            od.append(dm / do)
        if np.isfinite(ao) and ao > 0 and np.isfinite(am):
            ac.append(am / ao)
    return np.array(od), np.array(ac)


if __name__ == "__main__":
    a = luma(tifffile.imread(OFF)[..., :3].astype(np.float32))
    b = luma(tifffile.imread(ON)[..., :3].astype(np.float32))
    print("COVER=0 %s   COVER=on %s" % (a.shape, b.shape))
    sy, sx, oy, ox, n, ry, rx = fit_scale(a, b)
    print("\nMEASURED magnification  (fitted, not read from the log)")
    print("  scale y %.5f   scale x %.5f   from %d registered patches" % (sy, sx, n))
    print("  centre (%.0f, %.0f)   max fit residual %.1f px (y) %.1f px (x)"
          % (oy, ox, ry, rx))
    print("  render log claimed FOV scaled to 0.9475 -> magnification %.5f"
          % (1 / 0.9475))

    pairs = matched(a, b, sy, sx, oy, ox)
    print("\n%d matched patch pairs (integer shift only, corr >= %.2f)"
          % (len(pairs), CORR_MIN))

    print("\nCOMMISSIONING the ratio  (COVER=on patch / COVER=0 patch)")
    print("%-40s %14s %14s" % ("arm", "orig_detail", "acutance"))
    print("-" * 70)
    nullpairs = [(r, r.copy(), 1.0) for r, _, _ in pairs]
    for label, prs, plant in (
            ("NULL      same patch, zero shift", nullpairs, None),
            ("DEFECT    numerator blurred 0.8px", nullpairs, "blur"),
            ("IMPROVE   numerator sharpened (usm)", nullpairs, "usm")):
        o, c = ratios(prs, plant)
        print("%-40s %14.6f %14.6f" % (label, np.median(o), np.median(c)))

    o, c = ratios(pairs)
    print("\nMEASURED  COVER=on vs COVER=0, matched patches")
    print("  orig_detail  median %.4f   p10 %.4f   p90 %.4f" % (np.median(o), np.percentile(o, 10), np.percentile(o, 90)))
    print("  acutance     median %.4f   p10 %.4f   p90 %.4f" % (np.median(c), np.percentile(c, 10), np.percentile(c, 90)))
    print("\n  a pure %.4fx magnification with NO kernel overshoot would put" % sy)
    print("  orig_detail near %.4f (gradient spread over more pixels)." % (1 / sy))
