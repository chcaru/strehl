r"""RIM / occlusion-halo A/B, reusing rimv6.py UNMODIFIED.

WHAT IS REUSED AND WHY. rimv6 is this project's sixth rim instrument; five
predecessors are on record as failures in its own docstring, and it is the one
that separates SELECTION of edges (done on a rim-free reference, where no rim
exists to select for or against) from MEASUREMENT of the rim. rimaxis.py drives
it for the print certificate. Nothing in rimv6 is changed here.

WHAT IS DIFFERENT FROM rimaxis.py. rimaxis scores ONE master against its own
structural null. This is a two-arm comparison of the SAME scene, so:

  * the edge list is chosen ONCE, on the smoothed MEAN of the two arms, and
    both arms are measured at those identical pixel locations. The selection
    therefore cannot favour either arm.
  * the interval is a PAIRED bootstrap over edges, valid here (and not in
    rimv6.boot_diff, which is unpaired) precisely because the two arms share
    every edge location. Unpaired would be needlessly wide.
  * the structural null and the instrument floor are COMMON to both arms and
    cancel in the difference, so the differential number does not depend on
    them. They are still printed, because the ABSOLUTE level does.

STATISTIC. Per edge, q is the profile normalised to its own step; the bright
reading is max(q[+2..+7]) - 1. It is NOT bounded below by zero -- an edge still
climbing at +7 reads negative -- so the column can register an improvement, not
only a defect. That is checked, not asserted: see --commission.
"""
import argparse
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "V-H2H2-RIMCLIP"))
sys.path.insert(0, R)
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "V-GATHER")))
import rimv6                                                       # noqa: E402
import rimaxis                                                     # noqa: E402

T = 256
NTILE = 80
SMOOTH = 3.0
NMIN = 30


def lum(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def load(p):
    a = tifffile.imread(p)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[:, :, :3]
    cm = (a.max(axis=2) >= 65535) | (a.max(axis=2) <= 0)
    clipf = float((a.max(axis=2) >= 65535).mean())
    return lum(a), cm, clipf


def choose(ref, clip, rois):
    """Sweep the flatness cut to drive the rim-free reference to its own
    structural null. Same rule as rimaxis.select_for: no tolerance is chosen,
    so there is no tolerance to choose favourably."""
    best = None
    for cut in rimv6.FLAT_CANDIDATES:
        sel = rimv6.select(ref, clip, rois, T, cut)
        if len(sel) < NMIN:
            continue
        e = rimv6.measure(ref, sel, T)
        r = rimv6.stats(e, nmin=NMIN)
        if r is None:
            continue
        w = rimv6.edge_width(e)
        nn = rimv6.try_null(w) if w else None
        if nn is None:
            continue
        resid = r["bright"] - nn[0]
        if best is None or abs(resid) < abs(best[0]):
            best = (resid, cut, sel, w, nn[0])
    return best


def paired(oa, ob, nboot=4000, seed=41):
    d = ob - oa
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(nboot, len(d)))
    m = np.median(d[idx], axis=1)
    return (float(np.median(d)), float(np.percentile(m, 2.5)),
            float(np.percentile(m, 97.5)))


def run(gA, gB, cm, tag="", sel=None, floor=None, rois=None):
    if sel is None:
        gm = 0.5 * (gA + gB)
        rois = rimaxis.pick_rois(gm, cm, n=NTILE)
        ref = ndimage.gaussian_filter(gm, SMOOTH).astype(np.float32)
        best = choose(ref, cm, rois)
        if best is None:
            return {"refused": "no flatness cut leaves %d edges" % NMIN}
        floor = {"resid": best[0], "cut": best[1], "width": best[3],
                 "null": best[4], "n": len(best[2])}
        sel = best[2]
    ea = rimv6.measure(gA, sel, T)
    eb = rimv6.measure(gB, sel, T)
    if ea is None or eb is None or len(ea["ov"]) != len(eb["ov"]):
        return {"refused": "edge populations differ between arms"}
    m, lo, hi = paired(ea["ov"], eb["ov"])
    out = {"tag": tag, "n_edges": int(len(ea["ov"])),
           "floor": floor,
           "A_bright": float(np.median(ea["ov"])),
           "B_bright": float(np.median(eb["ov"])),
           "A_dark": float(np.median(ea["un"])),
           "B_dark": float(np.median(eb["un"])),
           "d_bright": m, "d_lo": lo, "d_hi": hi,
           "_sel": sel, "_floor": floor, "_rois": rois}
    dm, dlo, dhi = paired(ea["un"], eb["un"], seed=57)
    out["d_dark"], out["d_dark_lo"], out["d_dark_hi"] = dm, dlo, dhi
    return out


def show(r):
    if "refused" in r:
        print("  REFUSED %s" % r["refused"])
        return
    f = r["floor"]
    print("  edges %d   flatness cut %.2f   edge width %.2f px   structural "
          "null %+.3f%%   instrument floor %+.3f%%"
          % (r["n_edges"], f["cut"], f["width"], 100 * f["null"],
             100 * f["resid"]))
    print("  BRIGHT rim   A %+.3f%%   B %+.3f%%   B-A %+.3f%% "
          "[%+.3f%%, %+.3f%%]   (DOWN = less halo)"
          % (100 * r["A_bright"], 100 * r["B_bright"], 100 * r["d_bright"],
             100 * r["d_lo"], 100 * r["d_hi"]))
    print("  DARK  rim    A %+.3f%%   B %+.3f%%   B-A %+.3f%% "
          "[%+.3f%%, %+.3f%%]   (DOWN = less undershoot)"
          % (100 * r["A_dark"], 100 * r["B_dark"], 100 * r["d_dark"],
             100 * r["d_dark_lo"], 100 * r["d_dark_hi"]))


def clamp(g, blur=2.0, size=7):
    """Local overshoot clamp: bound every pixel to the range its own smoothed
    neighbourhood spans. Removes over- and undershoot at an edge while leaving
    the edge step itself intact -- a genuine halo-removal operator, which is
    what the IMPROVE direction of this axis needs."""
    b = ndimage.gaussian_filter(g, blur)
    lo = ndimage.minimum_filter(b, size)
    hi = ndimage.maximum_filter(b, size)
    return np.clip(g, lo, hi).astype(np.float32)


def usm(g, amount, radius):
    return (g + amount * (g - ndimage.gaussian_filter(g, radius))).astype(np.float32)


def commission(path):
    print("COMMISSIONING the rim axis on real pixels: %s" % path)
    g, cm, clipf = load(path)
    print("  whole-image clip fraction %.4f%%" % (100 * clipf))
    base = run(g, g, cm, tag="NULL")
    if "refused" in base:
        print("  REFUSED at selection: %s" % base["refused"])
        return 1
    sel, floor, rois = base["_sel"], base["_floor"], base["_rois"]
    rows = []

    def arm(name, b, sgn, a=None):
        r = run(g if a is None else a, b, cm, tag=name, sel=sel, floor=floor)
        print("\n  %s" % name)
        show(r)
        ok = ((sgn > 0 and r["d_bright"] > 0 and r["d_lo"] > 0) or
              (sgn < 0 and r["d_bright"] < 0 and r["d_hi"] < 0) or
              (sgn == 0 and r["d_bright"] == 0.0))
        print("  ---> %s" % ("PASS" if ok else "FAIL"))
        rows.append((name, ok))

    print("\n  NULL   identical image")
    show(base)
    rows.append(("NULL identical image", base["d_bright"] == 0.0))
    print("  ---> %s" % ("PASS" if base["d_bright"] == 0.0 else "FAIL"))

    arm("DEFECT  planted halo, USM amount 0.5 r=2.0 -> must RISE",
        usm(g, 0.5, 2.0), +1)
    arm("DEFECT  planted halo, USM amount 0.2 r=2.0 -> must RISE",
        usm(g, 0.2, 2.0), +1)
    arm("IMPROVE local overshoot clamp -> must FALL", clamp(g), -1)
    arm("IMPROVE remove a planted halo (A=USM0.5, B=original) -> must FALL",
        g, -1, a=usm(g, 0.5, 2.0))

    bad = [r for r in rows if not r[1]]
    print("\n  COMMISSIONED %d/%d arms" % (len(rows) - len(bad), len(rows)))
    for n, _ in bad:
        print("    NOT COMMISSIONED: %s" % n)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", metavar="TIFF")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--tag", default="")
    ap.add_argument("--json")
    args = ap.parse_args()
    if args.commission:
        return commission(args.commission)
    gA, cmA, clipA = load(args.a)
    gB, cmB, clipB = load(args.b)
    print("%s\n  A clip %.4f%%   B clip %.4f%%" % (args.tag, 100 * clipA, 100 * clipB))
    r = run(gA, gB, cmA | cmB, tag=args.tag)
    show(r)
    if args.json:
        r.pop("_sel", None), r.pop("_floor", None), r.pop("_rois", None)
        r["clipA"], r["clipB"] = clipA, clipB
        json.dump(r, open(args.json, "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
