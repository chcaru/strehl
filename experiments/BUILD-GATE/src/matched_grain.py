"""Break the sharp/grain degeneracy, and test whether `k` acts with the hard
gate off.

TWO QUESTIONS, one data set.

(A) MATCHED GRAIN. ab_score.py reports r(sharp/tex, grain) = +0.93 to +0.997.
    At that correlation a raw sharpness delta is uninterpretable: "the shipping
    default costs 22% sharpness" and "the shipping default removes 38% of the
    grain" are the same measurement wearing two hats. The fix is to stop
    comparing arms at matched `k` and compare them at MATCHED GRAIN -- find the
    k whose grain equals the pre-fix arm's grain, and read sharpness there.
    Any residual difference is then sharpness that is not grain.

    Grain is NOT monotone in k (it rises to a peak then falls), so the
    interpolation is restricted to the descending branch from the peak. That
    restriction is stated, and the peak is reported, because silently picking a
    branch would hide a second root.

(B) THE SOFT WEIGHT LAW. ORCH concluded that "sweeping `k` cannot fix a gate
    that does not fire." The G090 and G100 arms print 0.0% averaged at EVERY
    level on every subject -- the hard gate is off everywhere -- so if `k` still
    moves the columns between those two arms, it is acting through the weight
    law rather than through admission, and the inference does not hold.

COMMISSIONING. The interpolator is checked three ways in commission(): it must
return an arm's own sharpness when asked for that arm's own grain (null); it
must report a planted sharpness LOSS as a loss; and it must report a planted
sharpness GAIN as a gain. The third is the one this project has been burned by
before -- a statistic bounded below at zero scored a planted improvement as
"no change".
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_score as S                                              # noqa: E402

MEAS = [a for a in S.ARMS if a != "WHITE200"]
KV = {"G090": 0.9, "G100": 1.0, "G129": 1.29, "G140": 1.4,
      "G160": 1.6, "G200": 2.0, "G260": 2.6}


def interp(ks, grain, sharp, target):
    """Sharpness where grain == target, on the descending branch after the peak.

    Returns (k, sharp, peak_k). None if target is off the branch.
    """
    pk = int(np.argmax(grain))
    ks, grain, sharp = ks[pk:], grain[pk:], sharp[pk:]
    for i in range(len(ks) - 1):
        lo, hi = grain[i], grain[i + 1]
        if (lo - target) * (hi - target) <= 0 and hi != lo:
            f = (target - lo) / (hi - lo)
            return (ks[i] + f * (ks[i + 1] - ks[i]),
                    sharp[i] + f * (sharp[i + 1] - sharp[i]), ks[0])
    return None


def commission():
    """Null, planted loss, and planted gain. Fails loudly."""
    ks = np.array([1.0, 1.4, 1.6, 2.0, 2.6])
    grain = np.array([1.20, 1.10, 1.00, 0.80, 0.50])
    sharp = np.array([1.10, 1.05, 1.00, 0.90, 0.70])
    print("COMMISSIONING the matched-grain interpolator")
    r = interp(ks, grain, sharp, 1.10)
    assert r is not None and abs(r[1] - 1.05) < 1e-9, r
    print("  null      : asked for an arm's own grain 1.10 -> sharp %.4f "
          "(its own 1.0500)  PASS" % r[1])
    lost = sharp * np.array([1.0, 0.90, 1.0, 1.0, 1.0])
    r2 = interp(ks, grain, lost, 1.10)
    assert r2 is not None and r2[1] < 0.99 * 1.05, r2
    print("  planted -10%% at the matched arm -> sharp %.4f, reads %+.1f%%  "
          "PASS" % (r2[1], 100 * (r2[1] / 1.05 - 1)))
    gained = sharp * np.array([1.0, 1.15, 1.0, 1.0, 1.0])
    r3 = interp(ks, grain, gained, 1.10)
    assert r3 is not None and r3[1] > 1.01 * 1.05, r3
    print("  planted +15%% at the matched arm -> sharp %.4f, reads %+.1f%%  "
          "PASS  (not bounded below)" % (r3[1], 100 * (r3[1] / 1.05 - 1)))
    print("  interpolator responds to both signs.\n")


def profile(arm, subject):
    """Every level's averaged %, excluding the base band (100% by design)."""
    p = os.path.join(S.AB, arm, subject + ".log")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"^averaged\s*:\s*(.+)$", t, re.M)
    if not m:
        return None
    v = [float(x.rstrip("%")) for x in m.group(1).split()]
    return v[:-1]


def softlaw(rows, subject):
    """Does k move the columns while the hard gate is off at EVERY level?

    'Off' is checked on the whole printed profile, not just level 0. The base
    band is excluded because it is 100% averaged by design, not by gating.
    """
    a, b = rows.get("G090"), rows.get("G100")
    if not a or not b:
        return None
    pa, pb = profile("G090", subject), profile("G100", subject)
    if pa is None or pb is None:
        return None
    off = max(max(pa), max(pb)) < 0.05
    return (b[0] / a[0] - 1, b[1] / a[1] - 1, b[2] / a[2] - 1,
            max(pa), max(pb), off)


def main():
    commission()
    print("(A) MATCHED GRAIN -- sharpness with the grain difference removed.")
    print("    Baseline WHITE200 = white floor, k=2.0 = the PRE-FIX ship.\n")
    print("  %-22s %9s %9s | %8s %9s | %9s"
          % ("subject", "k @grain=1", "peak k", "sharp raw", "@ k=2.0",
             "sharp matched"))
    keep = {}
    for s in S.SUBJECTS:
        rows = S.score(s)
        if not rows or len(rows) < len(S.ARMS):
            print("  %-22s %s" % (s, "incomplete"))
            continue
        keep[s] = rows
        w = rows["WHITE200"]
        ks = np.array([KV[a] for a in MEAS])
        g = np.array([rows[a][1] / w[1] for a in MEAS])
        t = np.array([rows[a][2] / w[2] for a in MEAS])
        r = interp(ks, g, t, 1.0)
        raw = rows["G200"][2] / w[2]
        if r is None:
            print("  %-22s %9s" % (s, "off-branch"))
            continue
        print("  %-22s %9.3f %9.2f | %8s %+8.1f%% | %+8.1f%%"
              % (s, r[0], r[2], "", 100 * (raw - 1), 100 * (r[1] - 1)))
    print("\n  'sharp raw @ k=2.0' is today's shipping default against the")
    print("  pre-fix ship at the SAME k. 'sharp matched' is the same two")
    print("  builds compared at the same GRAIN. The gap between the two")
    print("  columns is how much of the apparent sharpness cost was grain.\n")

    print("(B) SOFT WEIGHT LAW -- G090 vs G100. 'gate off' means the WHOLE")
    print("    printed profile, every level, is under 0.05%, not just L0.\n")
    print("  %-22s %9s %9s %9s | %8s %s"
          % ("subject", "blotch", "grain", "sharp/tex", "worst lvl",
             "gate off?"))
    moved, elig = 0, 0
    for s, rows in keep.items():
        r = softlaw(rows, s)
        if r is None:
            continue
        print("  %-22s %+8.2f%% %+8.2f%% %+8.2f%% | %7.2f%% %s"
              % (s, 100 * r[0], 100 * r[1], 100 * r[2], max(r[3], r[4]),
                 "YES" if r[5] else "no - excluded"))
        if not r[5]:
            continue
        elig += 1
        if max(abs(r[0]), abs(r[1]), abs(r[2])) > 0.01:
            moved += 1
    print("\n  Of the subjects where the hard gate is provably off at every")
    print("  level in BOTH arms, k moved a column by >1%% on %d/%d."
          % (moved, elig))
    print("  Both arms gate under 0.05%% of coefficients, so the gated")
    print("  populations differ by at most 0.05 percentage points. Admission")
    print("  cannot carry a multi-percent move from that; the weight law can,")
    print("  because k is subtracted inside it at every level.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
