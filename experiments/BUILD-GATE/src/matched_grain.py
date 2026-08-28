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


def interp(ks, grain, sharp, target, branch="upper"):
    """Sharpness where grain == target. Kept for callers wanting one root."""
    r = roots(ks, grain, sharp, target)
    if not r:
        return None
    pk = float(ks[int(np.argmax(grain))])
    lo = [x for x in r if x[0] < pk]
    hi = [x for x in r if x[0] >= pk]
    pick = (hi or r)[0] if branch == "upper" else (lo or r)[0]
    return pick[0], pick[1], pk


def roots(ks, grain, sharp, target):
    """EVERY k where grain crosses target, with sharpness at each.

    Grain is not monotone in k: it rises to a peak then falls, so grain=1.0
    generally has TWO solutions, one either side of the peak. They are not
    interchangeable -- they deliver the same grain from different amounts of
    selection, and the sharpness at each is a measurement, not a symmetry.
    Returning only one root is how a better operating point gets hidden.
    """
    out = []
    for i in range(len(ks) - 1):
        lo, hi = grain[i], grain[i + 1]
        if (lo - target) * (hi - target) <= 0 and hi != lo:
            f = (target - lo) / (hi - lo)
            out.append((float(ks[i] + f * (ks[i + 1] - ks[i])),
                        float(sharp[i] + f * (sharp[i + 1] - sharp[i]))))
    return out


def commission():
    """Null, planted loss, planted gain, and a known two-root curve."""
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

    # A curve with a KNOWN pair of roots, and deliberately different sharpness
    # at each, so a one-root implementation is caught rather than trusted.
    k2 = np.array([0.9, 1.0, 1.3, 1.4, 1.6, 2.0])
    g2 = np.array([0.90, 0.95, 1.05, 1.10, 1.05, 0.90])
    s2 = np.array([1.00, 1.04, 1.12, 1.14, 1.05, 0.90])
    rr = roots(k2, g2, s2, 1.00)
    assert len(rr) == 2, rr
    assert rr[0][0] < 1.4 < rr[1][0], rr        # 1.4 is the peak k, not 1.10
    assert abs(rr[0][1] - rr[1][1]) > 0.05, rr
    print("  two-root  : found %d roots at k=%.3f (sharp %.4f) and k=%.3f "
          "(sharp %.4f)" % (len(rr), rr[0][0], rr[0][1], rr[1][0], rr[1][1]))
    print("              a one-root version would have reported only the "
          "second and\n              hidden a %+.1f%% better operating point."
          "  PASS" % (100 * (rr[0][1] / rr[1][1] - 1)))
    print("  interpolator responds to both signs and finds both roots.\n")


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
    print("  %-22s %8s | %-24s | %-24s"
          % ("subject", "raw@k=2", "lower root (less selection)",
             "upper root (more selection)"))
    keep, twin = {}, 0
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
        rr = roots(ks, g, t, 1.0)
        raw = rows["G200"][2] / w[2]
        pk = float(ks[int(np.argmax(g))])
        lo = [x for x in rr if x[0] < pk]
        hi = [x for x in rr if x[0] >= pk]
        f = lambda x: ("k=%.3f  sharp %+.1f%%" % (x[0], 100 * (x[1] - 1))
                       ) if x else "none on this branch"
        if lo and hi:
            twin += 1
        print("  %-22s %+7.1f%% | %-24s | %-24s"
              % (s, 100 * (raw - 1), f(lo[0] if lo else None),
                 f(hi[0] if hi else None)))
    print("\n  %d/%d subjects have TWO k values delivering the pre-fix grain."
          % (twin, len(keep)))
    print("  'raw@k=2' is today's default against the pre-fix ship at the same")
    print("  k. The root columns are the same two builds compared at the same")
    print("  GRAIN; the gap is how much of the raw number was grain.\n")

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
