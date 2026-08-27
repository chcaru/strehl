r"""Commissioning for the sharpness axis, and derivation of its threshold.

The deficit is 1 - master_band / ceiling_band. Arms plant softness and require
it to be seen, plant sharpening and require the score to IMPROVE, and plant
perturbations the axis must ignore. The threshold is DERIVED here from the
instrument's own floor rather than typed, because a threshold set by hand is how
`banding()` came to have a FAIL conjunction that could never fire.
"""
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sharpaxis as sa                                             # noqa: E402
import rimaxis                                                     # noqa: E402

CROP = (1200, 3600, 2048, 2048)
BASE = "109MSDCF"
PASS, FAIL = [], []


def check(name, ok, msg):
    (PASS if ok else FAIL).append(name)
    print("  %-12s %s  %s" % (name, "PASS" if ok else "FAIL", msg))


def main():
    a = tifffile.imread(os.path.join(rimaxis.SEAL_DIR, BASE + "--SHIP-V4.tiff"))
    y, x, h, w = CROP
    g0 = sa.lum(a[y:y + h, x:x + w].astype(np.float32))
    del a
    ref = g0.copy()

    def deficit(arm, ceiling=None):
        c = sa.band(ceiling if ceiling is not None else ref)
        return 1.0 - sa.band(arm) / c

    print("base %s crop %s  band %.6f" % (BASE, CROP, sa.band(g0)))

    print("\n-- arm NULL: an image against itself has no deficit --")
    check("NULL", abs(deficit(g0)) < 1e-12,
          "master against itself reads %.2e" % deficit(g0))

    print("\n-- arm REGTOL: does a %d px misregistration move the statistic? --"
          % sa.REG_TOL)
    devs = []
    for dy in (-sa.REG_TOL, 0, sa.REG_TOL):
        for dx in (-sa.REG_TOL, 0, sa.REG_TOL):
            sub = g0[600 + dy:600 + dy + sa.WIN, 600 + dx:600 + dx + sa.WIN]
            devs.append(sa.band(sub))
    base_w = sa.band(g0[600:600 + sa.WIN, 600:600 + sa.WIN])
    reg_floor = float(max(abs(v - base_w) / base_w for v in devs))
    check("REGTOL", reg_floor < 0.05,
          "worst band shift over +-%d px is %.3f%%; this is the instrument floor "
          "and the source of SHARP_MAX" % (sa.REG_TOL, 100 * reg_floor))

    print("\n-- arm BOUND: is the deficit two-sided, or inert like banding()? --")
    sharper = deficit(ndimage.gaussian_filter(g0, 0.4) * 0 + g0 * 1.0)
    neg = deficit(g0 + 1.5 * (g0 - ndimage.gaussian_filter(g0, 2.0)))
    check("BOUND", neg < 0,
          "a sharpened arm reads %+.3f%% -- below zero, so the statistic is not "
          "bounded below by construction" % (100 * neg))

    print("\n-- arm LADDER: planted defocus of increasing radius --")
    sig = [0.0, 0.3, 0.6, 1.0, 1.6, 2.4]
    ds = [deficit(ndimage.gaussian_filter(g0, s) if s else g0) for s in sig]
    for s_, d_ in zip(sig, ds):
        print("     blur sigma %-4.1f -> deficit %+.3f%%" % (s_, 100 * d_))
    check("LADDER", all(ds[i + 1] > ds[i] for i in range(len(ds) - 1)),
          "monotone increasing across %d rungs" % len(ds))
    # NOT "the faintest rung must be detected". The faintest rung is sigma 0.3,
    # which moves the deficit by 0.129% against a floor of 0.771%: it is BELOW
    # THE INSTRUMENT'S RESOLUTION, and an arm demanding that it be seen is
    # demanding the axis resolve something it has just measured itself unable to
    # resolve. What must be established is where the resolution limit lies, so
    # that the certificate can state what size of softness it is blind to.
    lim = next((s_ for s_, d_ in zip(sig, ds) if d_ > 2 * reg_floor), None)
    check("RESOLUTION", lim is not None and lim <= 0.6,
          "deficit first exceeds twice the %.3f%% floor at blur sigma %s; "
          "softness below that is BELOW THIS AXIS'S RESOLUTION and a PASS is "
          "silence on it" % (100 * reg_floor, lim))

    SHARP_MAX = float(np.ceil(reg_floor * 1000) / 1000.0) * 4
    print("\n   DERIVED SHARP_MAX = 4 x instrument floor = %.3f%%"
          % (100 * SHARP_MAX))

    print("\n-- arm FIRE: can the FAIL conjunction actually fire? --")
    check("FIRE", ds[-1] > SHARP_MAX,
          "strongest blur reads %.3f%% > SHARP_MAX %.3f%%; FAIL is reachable"
          % (100 * ds[-1], 100 * SHARP_MAX))
    check("NOTALWAYS", ds[0] <= SHARP_MAX,
          "the unmodified base reads %.3f%%; FAIL is not automatic" % (100 * ds[0]))

    print("\n-- arms REPAIR/RESTORE: an exact partial repair must score BETTER --")
    d_img = ndimage.gaussian_filter(g0, 1.6)
    lost = g0 - d_img
    sd = deficit(d_img)
    sh = deficit(d_img + 0.75 * lost)
    sf = deficit(d_img + 1.0 * lost)
    print("     defect %+.3f%%  75%%-repaired %+.3f%%  fully repaired %+.3f%%"
          % (100 * sd, 100 * sh, 100 * sf))
    check("REPAIR", sh < sd - 2 * reg_floor,
          "restoring 75%% of the lost detail lowers the deficit by %.3f%%"
          % (100 * (sd - sh)))
    check("RESTORE", abs(sf) < 1e-9,
          "restoring all of it returns to zero deficit (%.2e)" % sf)

    print("\n-- arm BLIND-GAIN: band is mean-normalised, so gain must not move it --")
    check("BLIND-GAIN", abs(deficit(g0 * 1.7)) < 1e-9,
          "x1.7 gain reads %.2e" % deficit(g0 * 1.7))

    print("\n-- arm NOISE: photon noise must not manufacture a ceiling --")
    rng = np.random.default_rng(9)
    noisy = g0 + rng.normal(0, 60.0, g0.shape).astype(np.float32)
    infl = (sa.band(noisy) - sa.band(g0)) / sa.band(g0)
    check("NOISE", infl < 0.05,
          "adding sigma=60 DN noise inflates band by %.2f%%; the sigma %.1f-%.1f "
          "band excludes the octave where photon noise lives, so a noisier frame "
          "cannot win the max-over-frames ceiling"
          % (100 * infl, sa.SIG_LO, sa.SIG_HI))

    print("\n%d PASS  %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED ARMS: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
