r"""Halo / occlusion-rim axis of the print certificate.

WHY THIS AXIS EXISTS. The blotch certification measures mid-scale mottling and
is blind to edge overshoot, which is the owner's oldest and loudest complaint
about this tool. A gate that certifies 17 subjects while unable to see a halo
will certify a haloed print.

WHAT IS REUSED AND WHAT IS REFUSED. The measurement core is
experiments/V-H2H2-RIMCLIP/rimv6.py, imported UNMODIFIED. Its predecessor v3 is
inadmissible and is not used at any point: v3 reads +14.85% on a smoothed image
that has no rim by construction, so it cannot distinguish a halo from geometry.
v6 separates SELECTION from MEASUREMENT -- edges are chosen on a rim-free
reference where no rim exists to select for or against -- which is the property
v5 broke by gating on shoulder flatness, a criterion correlated with the
measurand because a rim IS shoulder structure.

THE THREE THINGS SUBTRACTED BEFORE ANYTHING IS CALLED A HALO.

  STRUCTURAL NULL. A monotone edge of finite width reads non-zero by
  construction, because q reaches its plateau later on a wide edge so
  max(q[+2..+7]) falls short of 1 with nothing overshooting. Comparing against
  zero would condemn a correct image on the dark axis and flatter it by ~3
  points on the bright axis. The null is interpolated in measured edge width and
  RAISES outside its covered range rather than clamping.

  INSTRUMENT FLOOR. The same subject, smoothed, has no rim by construction. Its
  residual against its own null is this subject's floor and is subtracted.

  ISOLATION. The bright reading is max(q) over t=+2..+7 and is only a rim
  measurement if the profile has a plateau inside that zone. Edges still
  climbing at t=+7 read negative by construction. Those are excluded, and the
  EXCLUDED FRACTION IS REPORTED PER SUBJECT, because an axis that can see only
  a quarter of a subject's edges must say so rather than report a clean number
  over the quarter it liked. On 119MSDCF only 24.65% of edges plateau by t=+7.

REPORTED, NOT ASSUMED: `isolated_frac`. A subject whose isolated fraction is too
low is REFUSED on this axis, never passed.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
import rimv6                                                       # noqa: E402

SEAL_DIR = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = os.path.join(HERE, "rim.json")
T = 256
NTILE = 40
SMOOTH = 3.0
MIN_ISOLATED = 0.20
NMIN = 30

# DERIVED, NOT TYPED. RIM_MAX is set EQUAL to the instrument floor tolerance,
# because an axis may not claim to resolve an excursion smaller than the largest
# floor it is willing to tolerate on a rim-free image. Any other value is a
# number chosen to produce a verdict. The previous draft typed 3.0% and its
# commissioning immediately refuted it: no planted rim at unsharp-mask amount
# 2.0 could reach it, so FAIL was unreachable -- the same inert-threshold defect
# as `banding()`, whose median-of-gaps statistic is >= 1 by construction and
# whose FAIL conjunction therefore could never fire on any of the 26 masters.
RIM_MAX = FLOOR_MAX_FWD = 0.02


def lum_of(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def pick_rois(g, clip, n=NTILE, seed=5):
    """Tiles with the most edge energy. Chosen on the image under test, which is
    legitimate here because the criterion is EDGE PRESENCE -- a property of the
    scene -- and every arm for a subject then reuses the identical tile list."""
    h, w = g.shape
    cand = []
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            if clip[y:y + T, x:x + T].any():
                continue
            t = g[y:y + T, x:x + T]
            gy, gx = np.gradient(ndimage.uniform_filter(t, 3))
            cand.append((float(np.percentile(np.hypot(gx, gy), 99.5)), y, x))
    cand.sort(reverse=True)
    return [(y, x) for _, y, x in cand[:n]]


def measure_arm(g, sel):
    e = rimv6.measure(g, sel, T)
    r = rimv6.stats(e, nmin=NMIN)
    if r is None:
        return None
    w = rimv6.edge_width(e)
    nn = rimv6.try_null(w) if w else None
    if nn is None:
        return None
    r["width"] = w
    r["null_bright"], r["null_dark"] = nn[0], nn[1]
    r["resid_bright"] = r["bright"] - nn[0]
    r["resid_dark"] = r["dark"] - nn[1]
    ci = rimv6.boot_ci(e, nmin=NMIN)
    r["ci_bright"] = [ci[0], ci[1]] if ci else None
    return r


FLOOR_MAX = FLOOR_MAX_FWD


def select_for(g, clip, rois):
    """Sweep the flatness cut to MINIMISE the instrument's own floor.

    The floor is what the smoothed, rim-free version of this same subject reads
    against its own structural null. It should be zero and it is not: at a
    hardcoded cut of 0.10, `foam` read +5.014% on an image that cannot contain a
    rim. Subtracting a floor that large would be subtracting most of the answer,
    and it is exactly the defect that made v3 inadmissible at +14.85%.

    No tolerance is chosen here, so there is no tolerance to choose favourably:
    the cut is whichever candidate drives the floor closest to zero while
    leaving enough isolated edges to measure. If the best available cut still
    leaves the floor above FLOOR_MAX, the subject is REFUSED on this axis --
    the instrument has not reached its null and has no business reporting.

    `n_all` reruns the winning cut with the isolation test disabled, so the
    excluded fraction is measured on the identical candidate population rather
    than inferred from a different one -- the population-mismatch defect that
    condemned v5.
    """
    ref = ndimage.gaussian_filter(g, SMOOTH).astype(np.float32)
    best = None
    for cut in rimv6.FLAT_CANDIDATES:
        sel = rimv6.select(ref, clip, rois, T, cut)
        if len(sel) < NMIN:
            continue
        fl = measure_arm(ref, sel)
        if fl is None:
            continue
        score = abs(fl["resid_bright"])
        if best is None or score < best[0]:
            best = (score, cut, sel, fl)
    if best is None:
        return ref, [], 0, None, None
    _, cut, sel, fl = best
    n_all = len(rimv6.select(ref, clip, rois, T, cut, min_reach=-1e9))
    return ref, sel, n_all, cut, fl


def run_subject(path):
    a = tifffile.imread(path)
    g = lum_of(a)
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a
    rois = pick_rois(g, clip)
    ref, sel, n_all, cut, fl = select_for(g, clip, rois)
    rec = {"n_sel": len(sel), "n_candidates": n_all,
           "isolated_frac": (len(sel) / n_all) if n_all else 0.0,
           "n_rois": len(rois), "cut": cut}
    if len(sel) < NMIN or fl is None:
        rec["refused"] = ("no flatness cut leaves %d isolated edges inside the "
                          "null table's covered width range" % NMIN)
        return rec
    if abs(fl["resid_bright"]) > FLOOR_MAX:
        rec["floor"] = fl
        rec["refused"] = ("instrument floor %+.3f%% exceeds %.1f%% at the best "
                          "available cut -- a rim-free image does not read its "
                          "null on this subject" % (100 * fl["resid_bright"],
                                                    100 * FLOOR_MAX))
        return rec
    rec["master"] = measure_arm(g, sel)
    rec["floor"] = fl
    if rec["master"] is None:
        rec["refused"] = "edge width outside the null table's covered range"
        return rec
    rec["corrected_bright"] = rec["master"]["resid_bright"] - rec["floor"]["resid_bright"]
    rec["corrected_dark"] = rec["master"]["resid_dark"] - rec["floor"]["resid_dark"]
    return rec


def main():
    subs = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(SEAL_DIR)
                  if f.endswith("--SHIP-V4.tiff"))
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    only = sys.argv[1:] or subs
    for i, s in enumerate(subs, 1):
        if s in doc or s not in only:
            continue
        rec = run_subject(os.path.join(SEAL_DIR, s + "--SHIP-V4.tiff"))
        doc[s] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        if "refused" in rec:
            print("[%2d/%d] %-36s REFUSED %s" % (i, len(subs), s, rec["refused"]))
        else:
            print("[%2d/%d] %-36s iso %5.1f%% (%d/%d)  bright %+.3f%%  floor %+.3f%%"
                  "  CORRECTED %+.3f%%"
                  % (i, len(subs), s, 100 * rec["isolated_frac"], rec["n_sel"],
                     rec["n_candidates"], 100 * rec["master"]["resid_bright"],
                     100 * rec["floor"]["resid_bright"],
                     100 * rec["corrected_bright"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
