r"""Independent re-derivation of the rim finding. Shares NO code with rimv6.

rimaxis.py imports V-H2H2-RIMCLIP/rimv6. If that instrument has a systematic
fault, my axis inherits it whole and my 11 green commissioning arms inherit it
too, because they exercise the same code. So this asks the same question with a
method written from scratch and nothing in common but the input file.

Method: find near-vertical step edges by 1-D gradient on rows, require local
dominance so two nearby edges cannot be read as one, take a signed profile
across each edge oriented dark-to-bright, normalise by the measured step, and
report the peak excursion above the bright plateau in t = +2..+7 px.

Controls, both required:
  NULL      the same image smoothed by sigma 2 -- a rim cannot survive blurring,
            so a large reading here indicts the method, not the picture.
  POSITIVE  the same image with a deliberate unsharp mask applied -- if the
            method cannot see a rim that was just PUT there, a null reading on
            the real image means nothing at all.
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter1d, gaussian_filter

SEAL = r"C:\dev\strehl-out\acceptance\SHIP-V4"
NEAR = 7
MINSTEP = 0.10
PLATEAU = (2, 7)
FLATTEN = 0.06


def luma(a):
    a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def select(g, want=6000, seed=0):
    """Edge SITES, chosen once on a rim-free image and reused by every arm.

    The previous version reselected edges on each arm. Blurring removes weak
    edges from the qualifying set, so master and null were measured over
    DIFFERENT POPULATIONS (n=6000 against n=2788) and the difference between
    them carried the change in population, not the change in rim. That is the
    same defect that makes a metric read +14.85% on a rim-free image, and it
    made my null read LARGER than my master. Sites are now frozen.
    """
    rng = np.random.default_rng(seed)
    h, w = g.shape
    rows = rng.choice(np.arange(200, h - 200), size=min(1400, h - 400),
                      replace=False)
    sites = []
    for y in rows:
        line = gaussian_filter1d(g[y], 1.0)
        d = np.diff(line)
        ad = np.abs(d)
        for x in np.where(ad[60:w - 60] > MINSTEP * 0.25)[0] + 60:
            v = ad[x]
            far = max(ad[x - NEAR:x - 2].max(initial=0.0),
                      ad[x + 3:x + NEAR + 1].max(initial=0.0))
            if far > 0.5 * v:
                continue
            sgn = 1 if d[x] > 0 else -1
            sites.append((int(y), int(x), sgn))
            if len(sites) >= want:
                break
        if len(sites) >= want:
            break
    return sites


def profiles(g, sites):
    """Measure the frozen sites on whatever image is supplied."""
    out = []
    for y, x, sgn in sites:
        line = gaussian_filter1d(g[y], 1.0)
        if sgn > 0:
            dark = line[x - NEAR:x - 1].mean()
            seg = line[x + 2:x + NEAR + 2]
        else:
            dark = line[x + 3:x + NEAR + 2].mean()
            seg = line[x - NEAR:x - 1][::-1]
        if seg.size < NEAR - 1:
            continue
        bright = seg[-3:].mean()
        step = bright - dark
        if step < MINSTEP:
            continue
        prof = (seg[:NEAR - 1] - dark) / step
        # ISOLATION. On synthetic edges with a genuinely flat plateau this
        # instrument reads +0.16% clean and +5.28% ringing, so the statistic is
        # sound. On real pictures it read +27% on a subject rimv6 calls clean,
        # because the t=+2..+7 band is full of ordinary texture and a max over
        # a textured band is not an overshoot. Require the far end of the
        # profile to actually SETTLE: the edge must stop moving before it can be
        # asked whether it overshot. This is the same criterion V-HEADTOHEAD2
        # found excludes about 75% of high-contrast features on one subject.
        if prof.size < 4:
            continue
        if np.abs(np.diff(prof[-3:])).max() > FLATTEN:
            continue
        out.append(prof)
    return np.asarray(out) if out else np.zeros((0, NEAR - 1))


def overshoot(p):
    if p.size == 0:
        return float("nan"), 0
    lo, hi = PLATEAU
    band = p[:, max(lo - 2, 0):hi - 1]
    peak = band.max(axis=1)
    return float(np.median(peak) - 1.0), p.shape[0]


def run(name):
    f = os.path.join(SEAL, name + "--SHIP-V4.tiff")
    g = luma(tifffile.imread(f))
    ref = gaussian_filter(g, 2.0)
    sites = select(ref)
    usm = np.clip(g + 1.4 * (g - gaussian_filter(g, 1.2)), 0, 1)
    return {"master": overshoot(profiles(g, sites)),
            "null": overshoot(profiles(ref, sites)),
            "positive": overshoot(profiles(usm, sites))}


def main():
    print("independent rim re-derivation -- no code shared with rimv6\n")
    print("%-26s %14s %14s %14s" % ("subject", "master", "null(blur)",
                                    "positive(USM)"))
    for s in sys.argv[1:]:
        r = run(s)
        m, nl, po = r["master"], r["null"], r["positive"]
        print("%-26s %+7.2f%% %+7.2f%% %+7.2f%%   corrected %+7.2f%%  "
              "USM response %+6.2f pts  n=%d"
              % (s, 100 * m[0], 100 * nl[0], 100 * po[0],
                 100 * (m[0] - nl[0]), 100 * (po[0] - m[0]), m[1]))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
