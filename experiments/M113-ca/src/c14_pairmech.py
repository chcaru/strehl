"""M113-ca C14 -- why C13's commissioning failed, and what the defect is driven by.

C13 part 0a demanded broken/paired > 3.0x on synthetic data and measured 2.03x.
FAIL. The real data showed up to 2.71x (bee-3) and 2.39x (couch-fibers) on the
innermost ring. So the control was WEAKER than the thing it was commissioned to
detect -- it did not exercise the mechanism.

HYPOTHESIS FOR THE MISS. Breaking the pairing replaces median(d_r_i / rad_i) with
median(d_r_i / rad_j). If every window in the bin has nearly the SAME radius,
rad_j ~= rad_i and the damage is small. The damage must therefore scale with the
RELATIVE SPREAD OF RADIUS WITHIN THE BIN. C13's synthetic used
rad ~ U(300,500) -- a max/min of 1.67. The innermost real ring spans r_n 0 to
0.15, i.e. radius from nearly zero to the bin edge: a max/min in the tens.

That also predicts the strong radial gradient already visible in C13: the defect
should be worst at the centre and vanish at the rim, where a ring is a narrow
annulus and all radii are nearly equal.

TWO TESTS.
 T1  sweep the synthetic relative spread and show inflation rises with it,
     recovering >3x once the spread matches the innermost ring. This RE-
     COMMISSIONS the audit at the condition that matters.
 T2  on the real data, measure each ring's relative radius spread and correlate
     it with that ring's broken/paired inflation. If the hypothesis holds the
     relationship is monotone and strong.

FALSIFIER, stated before running: if inflation does NOT rise with relative
spread in T1, or if T2's correlation is weak or wrong-signed, then the pairing
defect is not spread-driven, C13's mechanism story is wrong, and I must find
another explanation for the failed control before trusting C13's numbers.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from c13_bootaudit import boot_broken, boot_paired, EDGES     # noqa: E402
import c4_globalfit as c4g                                    # noqa: E402
from c4_globalfit import cs, measure, fit_eps                  # noqa: E402

LIN = r"C:\dev\strehl-out\M113-ca\lin"
OUT = r"C:\dev\strehl-out\M113-ca"


def main():
    print("=" * 92)
    print("T1 -- does the pairing defect scale with RELATIVE RADIUS SPREAD inside the bin?")
    print("=" * 92)
    rng = np.random.default_rng(0)
    n = 400
    truth = 500e-6
    print("%10s %10s %12s %12s %12s" % ("rad lo", "rad hi", "max/min", "broken ppm", "inflation"))
    t1 = []
    for lo, hi in ((300.0, 500.0), (200.0, 500.0), (100.0, 500.0),
                   (50.0, 500.0), (20.0, 500.0), (5.0, 500.0)):
        rad = rng.uniform(lo, hi, n)
        num = truth * rad + rng.normal(0, 0.02, n)
        sb = boot_broken(num, rad, nboot=600)
        sp = boot_paired(num, rad, nboot=600)
        t1.append(dict(lo=lo, hi=hi, ratio=hi / lo, infl=float(sb / sp)))
        print("%10.1f %10.1f %12.1f %12.1f %12.2fx" % (lo, hi, hi / lo, sb * 1e6, sb / sp))
    rising = all(t1[i]["infl"] <= t1[i + 1]["infl"] * 1.15 for i in range(len(t1) - 1))
    best = max(r["infl"] for r in t1)
    print("\n  monotone rising: %s     max inflation reached: %.2fx" % (rising, best))
    print("  RE-COMMISSION (needs >3.0x at wide spread): %s"
          % ("PASS" if best > 3.0 else "FAIL -- hypothesis wrong"))

    print("\n" + "=" * 92)
    print("T2 -- on the REAL rings: does inflation track each ring's relative radius spread?")
    print("=" * 92)
    c4g.STEP = 100
    res = dict(t1=t1)
    for name in ("bee-3-cpl", "couch-fibers-cpl"):
        path = os.path.join(LIN, "%s-binned-off.tif" % name)
        if not os.path.exists(path):
            continue
        img, W, H = cs.load_tiff_u16(path)
        cx, cy = W / 2.0, H / 2.0
        hd = float(np.hypot(cx, cy))
        ws = c4g.grid(img, W, H)
        m = measure(img, ws, "lk", cx=cx, cy=cy)
        eps_g, tx, ty, n_, rms = fit_eps(m, cx, cy)
        dx = m[:, 2] - tx; dy = m[:, 3] - ty
        px = m[:, 0] - cx; py = m[:, 1] - cy
        rad = np.hypot(px, py); okr = rad > 1e-6
        d_r = dx * (px / np.where(okr, rad, 1)) + dy * (py / np.where(okr, rad, 1))
        rn = rad / hd
        print("\n%s" % name)
        print("%-12s %5s %11s %11s %11s %11s" % ("ring r", "n", "rad max/min", "sd broken", "sd paired", "inflation"))
        sp_l, in_l, rows = [], [], []
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            s = okr & (rn >= lo) & (rn < hi)
            if s.sum() < 6:
                continue
            num = d_r[s]; den = rad[s]
            spread = float(den.max() / den.min())
            sb = boot_broken(num, den); sp = boot_paired(num, den)
            infl = float(sb / sp)
            sp_l.append(spread); in_l.append(infl)
            rows.append(dict(lo=lo, hi=hi, spread=spread, infl=infl))
            print("%-12s %5d %11.2f %11.1f %11.1f %11.2fx"
                  % ("%.2f-%.2f" % (lo, hi), s.sum(), spread, sb * 1e6, sp * 1e6, infl))
        a = np.argsort(np.argsort(sp_l)); b = np.argsort(np.argsort(in_l))
        k = len(sp_l)
        rho = 1 - 6 * np.sum((a - b) ** 2) / (k * (k * k - 1)) if k > 2 else float("nan")
        print("  Spearman rho(relative spread, inflation) = %+.4f over %d rings" % (rho, k))
        res[name] = dict(rows=rows, rho=float(rho))
        del img
    with open(os.path.join(OUT, "c14_pairmech.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c14_pairmech.json")


if __name__ == "__main__":
    main()