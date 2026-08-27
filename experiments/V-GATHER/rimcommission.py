r"""Commissioning for the halo/rim axis.

An axis nobody has tried to fool is not an instrument, it is a number. This
plants a rim and requires RED, plants an exact partial REPAIR and requires the
score to FALL, and plants perturbations the axis must ignore.

THE IMPROVEMENT ARMS ARE THE POINT. A statistic whose error sign is bounded
below -- one that can overlook a defect but can never charge for a repair --
passes defect-only commissioning trivially. This project has already shipped
exactly that: `banding()` returns the median of gaps between change indices,
which is >= 1 by construction, so its FAIL conjunction could never fire on any
image. Arm BOUND tests for that failure mode directly and arms REPAIR/RESTORE
test that a real improvement is scored as one.

SELECTION IS HELD FIXED ACROSS ARMS. Edges are chosen once, on the smoothed
base, and every arm is measured on that identical edge list. Reselecting per arm
would let the planted rim change which edges are examined, and the comparison
would then be between populations rather than between images.
"""
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
import rimv6                                                       # noqa: E402
import rimaxis                                                     # noqa: E402

SEAL_DIR = rimaxis.SEAL_DIR
BASE = "109MSDCF"
CROP = (1200, 3600, 2048, 2048)
RIM_MAX = rimaxis.RIM_MAX

PASS, FAIL = [], []


def check(name, ok, msg):
    (PASS if ok else FAIL).append(name)
    print("  %-13s %s  %s" % (name, "PASS" if ok else "FAIL", msg))


def usm(g, amt, r=2.0):
    return g + amt * (g - ndimage.gaussian_filter(g, r))


def main():
    p = os.path.join(SEAL_DIR, BASE + "--SHIP-V4.tiff")
    a = tifffile.imread(p)
    y, x, h, w = CROP
    a = a[y:y + h, x:x + w]
    g0 = rimaxis.lum_of(a)
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a

    rois = rimaxis.pick_rois(g0, clip, n=64)
    ref, sel, n_all, cut, fl = rimaxis.select_for(g0, clip, rois)
    if fl is None:
        raise SystemExit("COMMISSIONING CANNOT RUN: no cut yields a floor on " + BASE)
    base_floor = fl["resid_bright"]
    print("base %s crop %s: %d/%d isolated edges, cut %.2f, floor %+.4f%%"
          % (BASE, CROP, len(sel), n_all, cut, 100 * base_floor))

    def score(g):
        r = rimaxis.measure_arm(g.astype(np.float32), sel)
        if r is None:
            raise SystemExit("MEASUREMENT RETURNED None ON A COMMISSIONING ARM")
        return r["resid_bright"] - base_floor, r

    s0, r0 = score(g0)
    print("\n-- arm FLOOR: a rim-free image must read its own null --")
    # NOT score(ref). score() subtracts base_floor, which was measured ON ref,
    # so score(ref) is 0.0000 by construction and the arm would be a tautology
    # -- a PASS that cannot fail proves nothing about the instrument. The raw
    # residual is the quantity with content.
    check("FLOOR", abs(base_floor) <= rimaxis.FLOOR_MAX,
          "smoothed base reads RAW %+.4f%% against its own structural null, "
          "tolerance %.1f%% (self-subtracted value %+.4f%% is tautological and "
          "is not what is tested)"
          % (100 * base_floor, 100 * rimaxis.FLOOR_MAX, 100 * score(ref)[0]))

    print("\n-- arm BOUND: is the statistic two-sided, or inert like banding()? --")
    blurred, _ = score(ndimage.gaussian_filter(g0, 1.6))
    check("BOUND", blurred < 0 or s0 < 0,
          "a reading below zero exists (base %+.4f%%, blurred %+.4f%%); the "
          "statistic is not bounded below by construction"
          % (100 * s0, 100 * blurred))

    print("\n-- arm LADDER: planted rim of increasing amount --")
    amts = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
    ss = [score(usm(g0, a_))[0] for a_ in amts]
    for a_, s in zip(amts, ss):
        print("     usm amt %-5.2f -> %+.4f%%" % (a_, 100 * s))
    mono = all(ss[i + 1] > ss[i] for i in range(len(ss) - 1))
    check("LADDER", mono, "monotone increasing across %d rungs" % len(ss))
    check("SENSITIVE", ss[1] - ss[0] > 0.002,
          "the faintest rung (amt 0.25) moves the reading by %+.4f%%"
          % (100 * (ss[1] - ss[0])))

    print("\n-- arm FIRE: can the FAIL conjunction actually fire? --")
    check("FIRE", ss[-1] > RIM_MAX,
          "strongest rung reads %+.4f%% > RIM_MAX %.1f%%; FAIL is reachable"
          % (100 * ss[-1], 100 * RIM_MAX))
    check("NOTALWAYS", s0 <= RIM_MAX,
          "the unmodified base reads %+.4f%% <= RIM_MAX; FAIL is not automatic"
          % (100 * s0))

    print("\n-- arms REPAIR/RESTORE: an exact partial repair must score BETTER --")
    d = usm(g0, 4.0)
    planted = d - g0
    sd, _ = score(d)
    shalf, _ = score(g0 + 0.25 * planted)
    sfull, _ = score(g0 + 0.0 * planted)
    print("     defect %+.4f%%  quarter-repaired %+.4f%%  fully repaired %+.4f%%"
          % (100 * sd, 100 * shalf, 100 * sfull))
    check("REPAIR", shalf < sd - 0.002,
          "removing 75%% of the planted rim lowers the score by %+.4f%%"
          % (100 * (shalf - sd)))
    check("RESTORE", abs(sfull - s0) < 1e-9,
          "removing all of it returns to the base reading exactly")

    print("\n-- arms BLIND: perturbations a step-normalised rim must ignore --")
    sg, _ = score(g0 * 1.3)
    so, _ = score(g0 + 4000.0)
    check("BLIND-GAIN", abs(sg - s0) < 1e-6,
          "x1.3 gain moves the reading by %+.2e%%" % (100 * (sg - s0)))
    check("BLIND-OFF", abs(so - s0) < 1e-6,
          "+4000 DN offset moves the reading by %+.2e%%" % (100 * (so - s0)))

    print("\n-- arm ISOLATION: is the MIN_REACH criterion load-bearing? --")
    sel_all = rimv6.select(ref, clip, rois, rimaxis.T, cut, min_reach=-1e9)
    r_all = rimaxis.measure_arm(g0, sel_all)
    check("ISOLATION", r_all is not None
          and abs(r_all["resid_bright"] - (s0 + base_floor)) > 0.002,
          "dropping isolation moves the raw reading from %+.4f%% to %+.4f%% "
          "over %d edges instead of %d -- the criterion changes the answer"
          % (100 * (s0 + base_floor),
             100 * (r_all["resid_bright"] if r_all else float("nan")),
             len(sel_all), len(sel)))

    print("\n%d PASS  %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED ARMS: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
