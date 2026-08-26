"""REFUTED -- DO NOT CITE THE NUMBERS THIS PRINTS.

ca_look_control.py killed this. Planting a known integer roll of 3 px in the R
channel and asking this code to measure it returns 0.007 px. It reads near-zero
regardless of the truth, so its "corner CA is under 0.08 px" table said nothing
about CA and everything about the statistic.

The defect is in radial_disp(): it builds the radial profile by AVERAGING along
the perpendicular direction across the whole 700 px patch. That average destroys
the edge structure the displacement lives in, so the profile is nearly
featureless and the cross-correlation peak sits at lag 0 by default. A dead
statistic and a genuinely well-corrected image produce the same output.

Use ca_radial.py + ca_control.py instead. That instrument measures R/B
correlation, was validated against a planted radial shear of known magnitude,
and passed all three of its pre-registered conditions.

Kept, marked, and not deleted, because the negative result is the useful part:
this is the ninth instrument failure of this run, and the second in which the
intended control could not fail (here the frame centre, where the radial
direction is undefined, so the control returned None and never ran).

Original docstring follows.
--------------------------------------------------------------------------
Look for the lateral-CA fringing that the disabled STREHL_FIX_CA would leave.

check-defaults.py says STREHL_FIX_CA is OFF in every shipped render, and credits
it with removing 61-67% of corner colour fringing and 0.363 px -> 0.059 px of
blue displacement. If that is real and it is off, corner fringing should be
VISIBLE at 1:1 in the shipped masters. If it is not visible, the claim is about
a regime that does not show in print and the promotion is not urgent.

Two outputs:
  1. corner crops as 8-bit PNG, to actually look at
  2. a radial R-G and B-G displacement measured per corner, sub-pixel

Lateral CA is radial and grows with field height, so the CENTRE is the built-in
control: whatever the corners show, the centre must show far less, or I am
measuring something that is not CA.
"""
import os
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\SHIP-V1"
OUT = r"C:\dev\strehl-out\ORCH-CA"
CROP = 700


def to8(a):
    """16-bit -> 8-bit for viewing, with a mild percentile stretch."""
    a = a.astype(np.float32)
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.5)
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((a - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def shift_1d(ref, mov, max_lag=6):
    """Sub-pixel shift of `mov` relative to `ref` by parabola-fitted xcorr peak.

    Both are 1-D gradient profiles, already mean-removed.
    """
    best, best_lag = -np.inf, 0
    scores = {}
    for lag in range(-max_lag, max_lag + 1):
        m = np.roll(mov, lag)
        s = float(np.dot(ref, m))
        scores[lag] = s
        if s > best:
            best, best_lag = s, lag
    # parabola on the three points around the peak
    l = best_lag
    if l - 1 in scores and l + 1 in scores:
        y0, y1, y2 = scores[l - 1], scores[l], scores[l + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-12:
            return l - 0.5 * (y2 - y0) / den
    return float(l)


def radial_disp(patch, cy, cx, py, px):
    """Measure R-G and B-G displacement along the radial direction in `patch`.

    (py, px) is the patch's top-left in full-frame coords; (cy, cx) the frame
    centre. Projects gradient energy onto the radial axis and correlates.
    """
    h, w, _ = patch.shape
    my, mx = py + h / 2.0, px + w / 2.0
    vy, vx = my - cy, mx - cx
    n = np.hypot(vy, vx)
    if n < 1e-6:
        return None
    vy, vx = vy / n, vx / n

    f = patch.astype(np.float32)
    # Project each channel onto ~64 radial bins by summing along the
    # perpendicular direction. Simple and resampling-free: bin by rounded
    # radial coordinate, which is an integer operation.
    yy, xx = np.mgrid[0:h, 0:w]
    r = (yy - h / 2.0) * vy + (xx - w / 2.0) * vx
    rb = np.round(r).astype(np.int32)
    rb -= rb.min()
    nb = rb.max() + 1
    if nb < 32:
        return None

    prof = np.zeros((nb, 3), np.float64)
    cnt = np.zeros(nb, np.float64)
    np.add.at(cnt, rb.ravel(), 1.0)
    for c in range(3):
        np.add.at(prof[:, c], rb.ravel(), f[:, :, c].ravel())
    ok = cnt > 0
    prof[ok] /= cnt[ok, None]

    # gradient of each radial profile, mean-removed, normalised
    g = np.diff(prof, axis=0)
    keep = np.isfinite(g).all(axis=1)
    g = g[keep]
    if g.shape[0] < 24:
        return None
    g -= g.mean(axis=0, keepdims=True)
    nrm = np.linalg.norm(g, axis=0)
    nrm[nrm < 1e-9] = 1.0
    g /= nrm

    rg = shift_1d(g[:, 1], g[:, 0])
    bg = shift_1d(g[:, 1], g[:, 2])
    energy = float(np.abs(np.diff(prof[:, 1])).mean())
    return rg, bg, energy


def main():
    subjects = sys.argv[1:] or ["tweezers-cpl", "coffee-bean", "bee-3-cpl"]
    os.makedirs(OUT, exist_ok=True)

    print("%-22s %-10s %8s %8s %10s" % ("subject", "site", "R-G px", "B-G px", "edge"))
    print("-" * 64)

    for name in subjects:
        p = os.path.join(SRC, name + ".tiff")
        if not os.path.exists(p):
            print("MISSING %s" % p)
            continue
        img = tifffile.imread(p)
        if img.ndim != 3 or img.shape[2] < 3:
            print("UNEXPECTED SHAPE %s %s" % (name, img.shape))
            continue
        H, W, _ = img.shape
        cy, cx = H / 2.0, W / 2.0
        m = 40  # keep off the very edge, where warp coverage can be ragged

        sites = {
            "TL": (m, m),
            "TR": (m, W - CROP - m),
            "BL": (H - CROP - m, m),
            "BR": (H - CROP - m, W - CROP - m),
            "CENTRE": (int(cy - CROP / 2), int(cx - CROP / 2)),
        }
        for site, (py, px) in sites.items():
            py, px = max(0, py), max(0, px)
            patch = img[py:py + CROP, px:px + CROP, :3]
            if patch.shape[0] < CROP // 2 or patch.shape[1] < CROP // 2:
                continue
            tifffile.imwrite(
                os.path.join(OUT, "%s--%s.png" % (name, site)),
                to8(patch),
            )
            r = radial_disp(patch, cy, cx, py, px)
            if r is None:
                print("%-22s %-10s %8s %8s %10s" % (name, site, "-", "-", "-"))
            else:
                rg, bg, e = r
                print("%-22s %-10s %8.3f %8.3f %10.1f"
                      % (name, site, rg, bg, e))
        print()


if __name__ == "__main__":
    main()
