"""Sharpness on textured sites, as the counterweight to any halo number.

WHY THIS FILE EXISTS. ORCH's standing warning, reproduced independently by the
falsification lane, is that "on blotch alone the worst arm wins": a plain mean
scores BEST on blotch and destroys 78% of the sharpness. The same trap is open
here. Every knob that reduces selection -- lower exponent, lower sharpen ramp,
more gating, mean base -- moves the merge toward an average, and an average has
no rim because it has no structure. A halo table with no sharpness column will
therefore recommend the blurriest arm with total confidence.

WHAT IT MEASURES. Median |Laplacian| over the most textured decile of the
SUBJECT, in DN. Restricting to textured sites is deliberate: a global high-pass
is dominated by the subject/background edge, which every arm renders and which
moves for reasons that have nothing to do with acuity.

WHAT IT CANNOT DO, stated up front because the commission measures it. A
high-pass statistic cannot tell detail from grain. Adding noise RAISES it. So
this number may only be read as "arm A is sharper than arm B" when the two arms
have comparable grain, and the commission prints the noise sensitivity so the
size of that caveat is a measured number rather than a hand wave.

COMMISSIONING, both directions. A metric commissioned only against a planted
DEFECT is satisfied by any statistic that falls when the image gets worse --
including one that also falls when the image gets better. So there is a planted
IMPROVEMENT (unsharp mask) as well as a planted degradation (Gaussian blur),
and the metric must move the right way on BOTH, plus stay put on identity.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_opening, gaussian_filter,
                           laplace, sobel)

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")
TEXTURED_PCT = 90.0  # keep the top decile of |grad| inside the subject


def luma(a):
    a = a.astype(np.float32)
    if a.ndim == 3:
        a = a[..., :3]
        return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a


def otsu(v):
    v = v[np.isfinite(v)]
    h, e = np.histogram(v, bins=512)
    h = h.astype(float)
    mids = 0.5 * (e[:-1] + e[1:])
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    s0 = np.cumsum(h * mids)
    s1 = s0[-1] - s0
    with np.errstate(invalid="ignore", divide="ignore"):
        m0, m1 = s0 / w0, s1 / w1
        var = w0 * w1 * (m0 - m1) ** 2
    var[~np.isfinite(var)] = -1
    return float(mids[int(np.argmax(var))])


def subject_mask(y):
    s = y < otsu(y.ravel())
    s = binary_opening(s, np.ones((3, 3)))
    s = binary_closing(s, np.ones((5, 5)))
    return s


def textured(y, subj):
    """The most textured decile of the subject.

    Sites are chosen from |grad| rather than from |Laplacian| so that the
    selection is not made by the same operator that is about to be scored --
    otherwise the metric picks the pixels where it is already largest and
    reports a number about its own argmax.
    """
    g = np.hypot(sobel(y, 0), sobel(y, 1))
    if subj.sum() < 1000:
        subj = np.ones_like(subj)
    thr = np.percentile(g[subj], TEXTURED_PCT)
    return subj & (g >= thr)


def sharpness(y, sites):
    return float(np.median(np.abs(laplace(y))[sites]))


def measure(path, sites=None):
    a = tifffile.imread(str(path))
    y = luma(a)
    if sites is None:
        sites = textured(y, subject_mask(y))
    return {"sharp_dn": round(sharpness(y, sites), 3),
            "nsites": int(sites.sum()),
            "shape": list(y.shape)}, sites


def commission():
    """Identity, a planted defect, a planted improvement, and the noise caveat."""
    rng = np.random.default_rng(7)
    n = 900
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    # A textured disc on a smooth ground. The texture MUST contain energy at
    # the scale the planted blur attacks. The first version of this plant used
    # sin(x/5), a 31 px period, and a sigma 1.0 blur moved the metric by 0.9%
    # -- so the commission failed and the metric looked blind when in fact the
    # plant was coarser than the defect. A plant has to be built at the scale
    # of the thing it is testing for. The fine term below has a 6.3 px period,
    # which a sigma 1.0 gaussian attenuates by exp(-0.5) = 0.61.
    fine = 3000.0 * np.sin(xx) * np.sin(yy)
    coarse = 3000.0 * np.sin(xx / 5.0) * np.sin(yy / 5.0)
    base = 12000.0 + fine + coarse
    ground = 52000.0 + 40.0 * (xx / n)
    d = np.hypot(xx - n / 2, yy - n / 2)
    y = np.where(d < 300, base, ground).astype(np.float32)

    subj = subject_mask(y)
    sites = textured(y, subj)
    s0 = sharpness(y, sites)

    ok, fail = 0, []

    def arm(name, img, want, lo, hi):
        nonlocal ok
        # SAME sites for every arm. Re-segmenting per arm would let a blurred
        # image move its own measurement window, so a change in the number
        # could be a change in acuity or a change in where it was read.
        r = sharpness(img, sites) / s0
        good = lo <= r <= hi
        print("  [%s] %-40s ratio=%6.3f  want %s"
              % ("PASS" if good else "FAIL", name, r, want))
        if good:
            ok += 1
        else:
            fail.append(name)
        return r

    print("commissioning sharp.py -- identity, defect, improvement, noise\n")
    arm("identity (must not move)", y.copy(), "1.000 +-0.001", 0.999, 1.001)
    arm("PLANTED DEFECT: gaussian blur sigma 1.0", gaussian_filter(y, 1.0),
        "< 0.80 (must FALL)", -1e9, 0.80)
    sharpened = y + 0.8 * (y - gaussian_filter(y, 1.2))
    arm("PLANTED IMPROVEMENT: unsharp mask", sharpened,
        "> 1.20 (must RISE)", 1.20, 1e9)

    noisy_rows = []
    print("\n  NOISE CAVEAT, measured not assumed:")
    for sg in [5.0, 15.0, 50.0]:
        noisy = y + rng.normal(0.0, sg, y.shape).astype(np.float32)
        rn = sharpness(noisy, sites) / s0
        noisy_rows.append({"sigma_dn": sg, "ratio": round(rn, 4)})
        print("    sigma %5.1f DN of white noise moves this metric by %+7.1f%%"
              % (sg, 100.0 * (rn - 1.0)))
    print("    A high-pass statistic cannot separate detail from grain. Two")
    print("    arms may only be compared on this number when their grain is")
    print("    known to match; a gap smaller than the row above that matches")
    print("    their noise difference is not readable as acuity.")
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "sharp-noise-sensitivity.json").write_text(
        json.dumps(noisy_rows, indent=1))

    print("\nsharp commission: %d/3 %s" % (ok, "PASS" if not fail else "FAIL"))
    if fail:
        print("failed: " + ", ".join(fail))
    return not fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--commission", action="store_true")
    ap.add_argument("--tag", default="sharp")
    a = ap.parse_args()
    if a.commission:
        sys.exit(0 if commission() else 1)
    rows = []
    print("%-34s %12s %10s" % ("file", "sharp_dn", "nsites"))
    for p in a.paths:
        for f in sorted(pathlib.Path().glob(p)) or [pathlib.Path(p)]:
            r, _ = measure(f)
            r["file"] = f.stem
            rows.append(r)
            print("%-34s %12.3f %10d" % (f.stem, r["sharp_dn"], r["nsites"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("sharp-%s.json" % a.tag)).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
