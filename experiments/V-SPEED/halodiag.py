"""Is `overshoot` measuring a rim, or is it measuring the background's own
illumination gradient?

WHY THIS EXISTS
---------------
ORCH's run of `experiments/ORCH-drift-check/halo_profile.py` on the 26 faithful
masters returns 7 clean, 4 HALO, 15 skipped, and I reproduce that partition
exactly. Before diagnosing a mechanism for the four, the four have to be real.
Three things in the instrument's own output argue they are not:

  1. ITS OWN HEADER already convicts two of them as confounds and says they
     were inspected at 1:1 and found clean:
       "tweezers-cpl  bump 1573.7 ... the two arms are separate components ...
        Inspected at 1:1: the boundary is clean."
       "flat-on-ruler  overshoot +4477 ... illumination falloff across a flat
        card, measured as a rim."
     Today's numbers are 1542.3 and +4481.8 -- the same two confounds, still
     being scored. The regime guards that were added to catch them (largest
     component >=70% of mass, far annuli within 3000 DN) do not fire on these
     two masters.

  2. ITS TWO STATISTICS CONTRADICT EACH OTHER on three of the four. The header
     states the criterion plainly: "A halo is a local maximum in the profile,
     so it raises both." dry-erase (over +236.7, bump 0.0), lavendar (over
     +527.3, bump 0.0) and tweezers (over -15502.0, bump 1542.3) each raise
     exactly one. A bump of 0.0 means the profile is strictly monotone --
     no local maximum anywhere -- which is the header's own definition of
     no rim.

  3. EVERY MEASURED SUBJECT, clean and HALO alike, has its maximum in the
     OUTERMOST near band, 80-120 px. A stacking halo lives against the
     silhouette, at a few px. If the argmax is always the band furthest from
     the subject, then `overshoot` is not reading a rim at any distance; it is
     reading median(d=80-120) - median(d=400-900), which is a property of the
     BACKGROUND between 120 px and 900 px and has nothing to do with the edge.

WHAT THIS SCRIPT TESTS
----------------------
Claim 3 is falsifiable and cheap, so test it rather than assert it.

  A. ARGMAX. Report which band carries the maximum, for every subject. If a
     real rim were present anywhere the argmax would be an inner band on at
     least one subject.

  B. INTERIOR LOCAL MAXIMUM. A rim is a bump that comes back down. Test for a
     band strictly greater than both of its neighbours. This is the header's
     own criterion, applied per-subject rather than as a global bump.

  C. FAR-FIELD SENSITIVITY, the decisive one. `overshoot` is a difference
     against a reference annulus at 400-900 px. Recompute it against nearer
     references. If the HALO verdicts are a property of the near field they
     will survive; if they are a property of how far away the reference sits,
     they will move with it. A rim 4 px from the silhouette cannot know where
     the reference annulus is.

The expensive part -- decode, segment, distance transform -- is cached to npz,
because every later experiment in this lane re-reads the same profiles.
"""
import argparse
import glob
import json
import os
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt, label)

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")
CACHE = OUT / "cache"

# Deliberately the same NEAR bands and sub-sampling as halo_profile.py. This
# script exists to interrogate that instrument's numbers, so it must reproduce
# them before it is allowed to disagree with them.
NEAR = [(2, 6), (6, 12), (12, 20), (20, 32), (32, 50), (50, 80), (80, 120)]
SUB = 4

# The alternative far-field references for test C. The shipping one is first.
FARS = [(400, 900), (200, 400), (150, 300), (120, 250)]


def luma(a):
    if a.ndim == 3:
        return (0.2126 * a[..., 0] + 0.7152 * a[..., 1]
                + 0.0722 * a[..., 2]).astype(np.float32)
    return a.astype(np.float32)


def otsu(v):
    h, edges = np.histogram(v, bins=256)
    h = h.astype(np.float64)
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    mids = (edges[:-1] + edges[1:]) / 2.0
    s0 = np.cumsum(h * mids)
    s1 = s0[-1] - s0
    with np.errstate(invalid="ignore", divide="ignore"):
        m0 = s0 / w0
        m1 = s1 / w1
        var = w0 * w1 * (m0 - m1) ** 2
    var[~np.isfinite(var)] = -1
    return float(mids[int(np.argmax(var))])


def prepare(path):
    """Decode, segment, distance-transform. Cached: this is the slow part."""
    stem = os.path.basename(path).split(".")[0]
    cf = CACHE / (stem + ".npz")
    if cf.exists():
        z = np.load(cf)
        return z["y"], z["d"], stem
    y = luma(tifffile.imread(path))[::SUB, ::SUB]
    t = otsu(y.ravel())
    subj = y < t
    subj = binary_opening(subj, np.ones((3, 3)))
    subj = binary_closing(subj, np.ones((5, 5)))
    d = (distance_transform_edt(~subj) * SUB).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cf, y=y.astype(np.float32), d=d)
    return y, d, stem


def bandmeds(y, d):
    out = []
    for lo, hi in NEAR:
        m = (d >= lo) & (d < hi)
        n = int(m.sum())
        out.append(float(np.median(y[m])) if n > 200 else None)
    return out


def farmed(y, d, far):
    m = (d >= far[0]) & (d < far[1])
    n = int(m.sum())
    return (float(np.median(y[m])), n) if n > 200 else (None, n)


def interior_local_max(vals):
    """A rim is a band strictly greater than BOTH neighbours.

    Endpoints are excluded on purpose. The outermost band being highest is a
    ramp that has not finished climbing, not a bump; the innermost being
    highest is impossible against a dark subject. Only an interior peak is a
    rim, and this is the header's own criterion made per-subject.
    """
    v = [x for x in vals if x is not None]
    peaks = []
    for i in range(1, len(v) - 1):
        if v[i] > v[i - 1] and v[i] > v[i + 1]:
            peaks.append((i, v[i] - max(v[i - 1], v[i + 1])))
    return peaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?",
                    default=r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.tif"))
                   + glob.glob(os.path.join(args.src, "*.tiff")))
    if args.only:
        files = [f for f in files if args.only in os.path.basename(f)]

    rows = []
    print("A/B: where is the maximum, and is there an interior peak?\n")
    print("%-34s %9s %-9s %6s  %s"
          % ("subject", "argmax", "band", "peaks", "interior peak height"))
    print("-" * 88)
    for f in files:
        y, d, stem = prepare(f)
        vals = bandmeds(y, d)
        fl, fn = farmed(y, d, FARS[0])
        if fl is None or all(v is None for v in vals):
            print("%-34s %9s %-9s %6s  (not scorable: far n=%d)"
                  % (stem, "-", "-", "-", fn))
            continue
        rel = [None if v is None else v - fl for v in vals]
        vv = [v for v in rel if v is not None]
        ai = int(np.argmax(vv))
        peaks = interior_local_max(rel)
        rows.append({"subject": stem, "argmax_idx": ai,
                     "argmax_band": list(NEAR[ai]), "rel": rel,
                     "peaks": [[int(i), round(h, 1)] for i, h in peaks]})
        print("%-34s %9d %-9s %6d  %s"
              % (stem, ai, "%d-%d" % NEAR[ai], len(peaks),
                 ", ".join("band %d by %.1f DN" % (i, h) for i, h in peaks)
                 or "none"))

    n = len(rows)
    outer = sum(1 for r in rows if r["argmax_idx"] == len(NEAR) - 1)
    withpk = sum(1 for r in rows if r["peaks"])
    print("-" * 88)
    print("%d scorable subjects: %d have argmax in the OUTERMOST band (%d-%d),"
          % (n, outer, NEAR[-1][0], NEAR[-1][1]))
    print("%d have any interior local maximum." % withpk)

    print("\n\nC: does the verdict depend on where the reference annulus sits?\n")
    hdr = "%-34s" % "subject"
    for far in FARS:
        hdr += " %14s" % ("%d-%d" % far)
    print(hdr + "   verdict flips?")
    print("-" * 108)
    flips = 0
    for r in rows:
        y, d, _ = prepare(os.path.join(args.src, r["subject"] + ".tiff")
                          if os.path.exists(os.path.join(
                              args.src, r["subject"] + ".tiff"))
                          else os.path.join(args.src, r["subject"] + ".tif"))
        vals = bandmeds(y, d)
        line = "%-34s" % r["subject"]
        verds = []
        for far in FARS:
            fl, fn = farmed(y, d, far)
            if fl is None:
                line += " %14s" % "-"
                verds.append(None)
                continue
            rel = [v - fl for v in vals if v is not None]
            ov = max(rel)
            verds.append(ov > 200.0)
            line += " %14.1f" % ov
        real = [v for v in verds if v is not None]
        flip = len(set(real)) > 1
        flips += 1 if flip else 0
        r["overshoot_by_far"] = [None if v is None else round(
            float(v), 1) for v in
            [max([x - farmed(y, d, far)[0] for x in vals if x is not None])
             if farmed(y, d, far)[0] is not None else None for far in FARS]]
        r["verdict_flips_with_reference"] = bool(flip)
        print(line + "   %s" % ("YES" if flip else "no"))
    print("-" * 108)
    print("%d of %d subjects change verdict purely by moving the reference"
          % (flips, len(rows)))
    print("annulus. A rim a few px from the silhouette cannot know where the")
    print("reference sits, so any subject that flips was never reading a rim.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "halodiag.json").write_text(json.dumps(rows, indent=1))
    print("\nwrote %s" % (OUT / "halodiag.json"))


if __name__ == "__main__":
    sys.exit(main())
