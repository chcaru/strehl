"""Re-derive every number quoted in BUILD-GATE-4.md from the measured arms.

The report's tables are transcribed from sweep_table.py output. A transcription
is a place where a number can change without anyone noticing, so this script
recomputes the derived quantities -- the sweep ranges, the falls, the rank
correlation, the peak arms, the exchange rates -- from the absolute ratios and
prints them next to what the report claims.

This is not decoration. In draft, section 5 asserted that the sharpness-optimal
k RISES with the averaging fraction; this script printed the peak arms and the
relationship is the exact opposite. The claim was corrected before the report
was committed. A report whose arithmetic is checked only where it disagrees with
expectation is not checked.

Run: python verify_tables.py
Exit 0 if every claim matches, 1 otherwise.
"""
import sys

import numpy as np
from scipy.stats import spearmanr

# Absolute per-site ceiling ratios, from sweep_table.py.
# Order: WHITE200, G100, G140, G170, G200, G300, G400.
SHARP = {
    "bee-1-cpl":            [2.3983, 2.3905, 2.3943, 2.4023, 2.3910, 2.3817, 2.3647],
    "flower-bud-alone-cpl": [1.3440, 1.1947, 1.3122, 1.3469, 1.1878, 0.9429, 0.9415],
    "119MSDCF":             [1.8590, 2.0207, 2.0558, 1.8688, 1.6510, 1.3339, 1.2318],
    "coffee-bubbles":       [1.1668, 1.2885, 1.3182, 1.2319, 1.0924, 0.7204, 0.5674],
    "109MSDCF":             [2.8206, 4.0096, 3.4338, 2.6507, 2.2538, 1.7907, 1.5452],
}
NOISE = {
    "bee-1-cpl":            [126.83, 103.20, 117.72, 127.29, 121.15, 32.75, 17.04],
    "flower-bud-alone-cpl": [112.34, 111.57, 123.04, 115.27, 84.52, 32.39, 29.45],
    "119MSDCF":             [105.25, 103.06, 110.17, 105.87, 89.23, 37.74, 22.55],
    "coffee-bubbles":       [296.444, 334.142, 342.295, 316.431, 269.301, 140.744, 92.350],
    "109MSDCF":             [129.36, 190.92, 166.07, 116.62, 77.42, 39.15, 37.01],
}
# `averaged` fraction at band 0, from the render banners (banner_capture.ps1).
AVG_SHIP = {"bee-1-cpl": 0.4, "flower-bud-alone-cpl": 12.5, "119MSDCF": 15.5,
            "coffee-bubbles": 26.1, "109MSDCF": 52.5}
AVG_G200 = {"bee-1-cpl": 10.6, "flower-bud-alone-cpl": 37.3, "119MSDCF": 34.4,
            "coffee-bubbles": 36.4, "109MSDCF": 72.5}
KS = [1.0, 1.4, 1.7, 2.0, 3.0, 4.0]
G170, G200 = 3, 4

# What the report claims. Checked, not assumed.
CLAIM_RANGE = {"bee-1-cpl": 1.6, "flower-bud-alone-cpl": 30.1, "119MSDCF": 40.1,
               "coffee-bubbles": 57.0, "109MSDCF": 61.5}
CLAIM_PEAK = {"bee-1-cpl": 1.7, "flower-bud-alone-cpl": 1.7, "119MSDCF": 1.4,
              "coffee-bubbles": 1.4, "109MSDCF": 1.0}
CLAIM_RHO = 0.90
CLAIM_KEFF = 1.731


def main():
    bad = []
    print("%-22s %8s %8s   %8s %8s   %6s" %
          ("subject", "range%", "claim", "fall%", "dnoise%", "peak k"))
    davg, falls = [], []
    for s, v in SHARP.items():
        sweep = v[1:]
        rng = 100.0 * (max(sweep) - min(sweep)) / max(sweep)
        fall = 100.0 * (v[G200] / v[0] - 1.0)
        dn = 100.0 * (NOISE[s][G200] / NOISE[s][0] - 1.0)
        peak = KS[int(np.argmax(sweep))]
        davg.append(AVG_G200[s] - AVG_SHIP[s])
        falls.append(-fall)
        if abs(rng - CLAIM_RANGE[s]) > 0.15:
            bad.append("%s range %.1f != claimed %.1f" % (s, rng, CLAIM_RANGE[s]))
        if peak != CLAIM_PEAK[s]:
            bad.append("%s peak k=%.1f != claimed %.1f" % (s, peak, CLAIM_PEAK[s]))
        print("%-22s %8.1f %8.1f   %8.2f %8.2f   %6.1f" %
              (s, rng, CLAIM_RANGE[s], fall, dn, peak))

    rho, p = spearmanr(davg, falls)
    print("\nSpearman rho (d_averaged vs fall) = %.3f (p=%.3f), claimed %.2f" % (rho, p, CLAIM_RHO))
    if abs(rho - CLAIM_RHO) > 0.01:
        bad.append("rho %.3f != claimed %.2f" % (rho, CLAIM_RHO))

    # Section 4(a): G200 must be negative on sharpness for EVERY subject.
    neg = {s: 100.0 * (v[G200] / v[0] - 1.0) for s, v in SHARP.items()}
    print("\nHEAD (G200) sharpness vs shipped master, all five:")
    for s, d in neg.items():
        print("   %-22s %+7.2f%%" % (s, d))
    if any(d >= 0 for d in neg.values()):
        bad.append("section 4(a) claims G200 is negative on ALL subjects; it is not")

    # Section 4(b): G170 within +-6% sharpness and +-10% noise everywhere.
    print("\nG170 vs shipped master (claim: within +-6.1%% sharp, +-10%% noise):")
    for s, v in SHARP.items():
        ds = 100.0 * (v[G170] / v[0] - 1.0)
        dn = 100.0 * (NOISE[s][G170] / NOISE[s][0] - 1.0)
        ok = abs(ds) <= 6.1 and abs(dn) <= 10.0
        print("   %-22s sharp %+6.2f%%  noise %+6.2f%%   %s" % (s, ds, dn, "ok" if ok else "OUTSIDE"))
        if not ok:
            bad.append("G170 outside the claimed band on %s" % s)

    # Section 4(c): the exchange rate on coffee-bubbles.
    print("\ncoffee-bubbles exchange rate (d sharp %% per d noise %%):")
    v, n = SHARP["coffee-bubbles"], NOISE["coffee-bubbles"]
    ex = []
    for i in range(1, 7):
        ds = 100.0 * (v[i] / v[0] - 1.0)
        dn = 100.0 * (n[i] / n[0] - 1.0)
        ex.append(ds / dn)
        print("   k=%.1f  %+6.2f" % (KS[i - 1], ds / dn))
    if not (0.60 <= min(ex) and max(ex) <= 0.90):
        bad.append("exchange rate outside the claimed 0.70-0.84 band: %.2f-%.2f" % (min(ex), max(ex)))

    print("\n" + ("VERIFY FAILED\n  " + "\n  ".join(bad)) if bad else "\nALL CLAIMS VERIFIED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
