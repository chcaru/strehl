"""The deliverable: blotch and sharpness in every row, and the knee.

Sharpness authority is the COMPLIANT statistic from section 12 -- the disjoint,
selection-immune, band-confined ratio with a bootstrap CI -- not the raw band
energy, which is quoted alongside only as a cross-check. Two independently
constructed sharpness statistics agreeing is worth more than either alone.

"No measurable sharpness cost" means the disj CI does not exclude zero on the
low side: the arm is null or better. "A real blotch reduction" means the
paired-block CI on the blotch ratio excludes 1.0. The knee is the largest real
blotch reduction among the arms that cost nothing.
"""
import sys

import numpy as np

# Section 12, table 12.4: disj sharpness delta % vs the shipped arm, and
# whether its 95% CI excludes zero. Order: G100 G140 G170 G200 G300 G400.
DISJ = {
    "bee-1-cpl":            [(-0.02, 0), (-0.00, 0), (+0.01, 0),
                             (-0.71, 0), (-1.19, 0), (-0.84, 0)],
    "flower-bud-alone-cpl": [(-12.43, 1), (-2.24, 0), (+1.82, 0),
                             (-17.41, 1), (-79.98, 1), (-87.30, 1)],
    "119MSDCF":             [(+9.68, 1), (+16.57, 1), (+0.97, 0),
                             (-26.79, 1), (-55.52, 1), (-69.12, 1)],
    "coffee-bubbles":       [(+7.46, 1), (+11.74, 1), (+6.47, 1),
                             (-9.87, 1), (-46.65, 1), (-59.20, 1)],
    "109MSDCF":             [(+87.27, 1), (+43.80, 1), (-10.52, 1),
                             (-39.93, 1), (-70.13, 1), (-82.02, 1)],
}
ORDER = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF", "coffee-bubbles",
         "109MSDCF"]
# The convicted mid-scale excess: up to 2.43x blotchier than the best input
# frame. Undoing it needs the blotch ratio taken to 1/2.43.
CONVICTED = 2.43


def main():
    sys.path.insert(0, __file__.rsplit("\\", 1)[0])
    import blotch as bl
    import blotch_boot as bb
    import blotch_sweep as bs

    need = (1.0 / CONVICTED - 1.0) * 100.0
    print("TWO-COLUMN ADMISSION SWEEP. Every row carries both columns.")
    print("  blotch    sigma_mid, 20-60 px (box widths 21 and 61), ORCH's "
          "orch_eye_check statistic, imported not reimplemented.")
    print("            Ratio vs the shipped arm, 95%% CI from a paired "
          "%d-block bootstrap. Lower is better." % 108)
    print("  sharp     disj ratio, band 0.20-0.25 cyc/px, selection-immune, "
          "section 12. Delta %%; * = CI excludes 0. Higher is better.")
    print("  grain     sigma_hp, ORCH's fine statistic, same pixels. Context "
          "only.")
    print("  Undoing the convicted %.2fx excess needs blotch %+.1f%%.\n"
          % (CONVICTED, need))

    knees = {}
    for s in ORDER:
        rows, flat, tex, _, _ = bs.run(s)
        bo, nblk = bb.run(s)
        b = rows["WHITE200"]
        print("%s  N=%d  (%d paired blocks)" % (s, bl.NFRAMES[s], nblk))
        print("  %-9s %5s | %-26s | %-16s | %8s"
              % ("arm", "k", "blotch x [95% CI]", "sharp disj", "grain x"))
        cand = []
        for i, a in enumerate(bl.ARMS):
            if a not in rows:
                continue
            m, lo, hi = bo[a]
            if a == "WHITE200":
                d, star = 0.0, 0
            else:
                d, star = DISJ[s][i - 1]
            real = hi < 1.0
            free = (star == 0) or (d > 0)
            print("  %-9s %5s | %8.4f [%.4f, %.4f]%s | %+8.2f%% %-6s | %8.4f"
                  % (a, "2.0*" if a == "WHITE200" else "%.1f" % bl.KS[a],
                     m, lo, hi, " *" if (lo > 1.0 or hi < 1.0) else "  ",
                     d, "*" if star else "", rows[a][1] / b[1]))
            if a != "WHITE200" and real and free:
                cand.append((m, a, lo, hi, d))
        k = min(cand) if cand else None
        knees[s] = k
        if k:
            print("  KNEE %s: blotch %+.2f%% [%+.2f, %+.2f] at sharpness %+.2f%% "
                  "(null or better) -- %.1f%% of the %+.1f%% needed"
                  % (k[1], (k[0] - 1) * 100, (k[2] - 1) * 100,
                     (k[3] - 1) * 100, k[4], 100 * (1 - k[0]) / (1 - 1 / CONVICTED),
                     need))
        else:
            print("  KNEE none: every arm that cuts blotch costs measurable "
                  "sharpness")
        print()

    print("GATE AUTHORITY vs STACK DEPTH")
    print("  authority = span of the disj sharpness column across the seven "
          "arms. A small span means the knob is inert on this subject.")
    print("  %-22s %5s %12s %12s" % ("subject", "N", "sharp span", "blotch span"))
    ns, au = [], []
    for s in ORDER:
        rows, _, _, _, _ = bs.run(s)
        bo, _ = bb.run(s)
        d = [0.0] + [x[0] for x in DISJ[s]]
        sp = max(d) - min(d)
        bl_ = [bo[a][0] for a in bl.ARMS if a in bo]
        print("  %-22s %5d %11.2f%% %11.2f%%"
              % (s, bl.NFRAMES[s], sp, (max(bl_) - min(bl_)) * 100))
        ns.append(bl.NFRAMES[s])
        au.append(sp)
    r = np.corrcoef(np.argsort(np.argsort(ns)),
                    np.argsort(np.argsort(au)))[0, 1]
    print("  Spearman(N, sharpness authority) = %+.4f over %d subjects"
          % (r, len(ns)))

    print("\nKNEE vs N")
    print("  %-22s %5s %s" % ("subject", "N", "knee"))
    for s in ORDER:
        print("  %-22s %5d %s"
              % (s, bl.NFRAMES[s], knees[s][1] if knees[s] else "none"))


if __name__ == "__main__":
    main()
