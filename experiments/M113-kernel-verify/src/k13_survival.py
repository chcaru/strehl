"""M113 K13 - HOW MUCH OF THE SINGLE-FRAME RINGING SURVIVES, AS A FUNCTION OF n_eff?

K12 stage A failed its pre-registered power bar (>2.0x) at 1.793x. That bar was
WRONGLY SET, and the reason matters more than the failure: I calibrated it
against fact 1374's 9.902x, and M95-kernel.md section 22.4 has ALREADY RETIRED
that figure -- P95 re-derives 1.78x on a clean 1000 DN step and records that
"the 9.9x figure reproduces at 9.06x only on an ungated population that is
99.87% noise". My positive control reads 1.793x against the author's corrected
1.78x. The instrument recovers essentially all of the real signal; the bar was
built from a number that no longer exists.

So the question is no longer "is there 9.9x ringing at n_eff = 1". The honest
question is: of the ~1.79x single-frame overshoot that genuinely exists, HOW
MUCH SURVIVES THE MERGE, and does the survival fraction rise as n_eff falls?

Statistic is M95's own: excursion beyond a local 3x3 [min,max] envelope, as a
fraction of local range, p99.9. Envelope comes from the NEAREST arm -- a
sample-and-hold kernel, which by construction cannot overshoot, and a third arm
independent of both arms under comparison (discipline 752).

CEILING. Within each n_eff stratum I also resample the nearest arm ONCE at a
half-pixel phase and measure the same statistic. That is what the same content
would look like with no averaging at all, so the ratio
   (merged excess) / (single-resample excess)
is the fraction of ringing the merge failed to remove, per stratum. If the
orchestrator's mechanism is right this should approach 1.0 as n_eff -> 1.
"""
import json
import os

import numpy as np
import tifffile
from scipy import ndimage

from k12_neff_ringing import NB, cr_w, l3_w, luma, shift

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render3"
STRATA = [("n_eff == 1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8),
          ("9-16", 9, 16), ("17-32", 17, 32), ("33-64", 33, 64),
          ("65-128", 65, 128), ("129+", 129, 10**9)]


def over_field(out, emin, emax, rng):
    return np.maximum(np.maximum(out - emax, emin - out), 0.0) / rng


def main():
    nn = luma(os.path.join(R, "lin-nn.tif"))
    cr = luma(os.path.join(R, "lin-cr.tif"))
    l3 = luma(os.path.join(R, "lin-l3.tif"))
    ne = tifffile.imread(os.path.join(R, "neff-cr.tif")).astype(np.int32)

    emax = ndimage.maximum_filter(nn, footprint=NB)
    emin = ndimage.minimum_filter(nn, footprint=NB)
    rng = np.maximum(emax - emin, 1e-9)
    g = np.hypot(*np.gradient(nn))
    gthr = float(np.percentile(g, 90.0))

    o_cr = over_field(cr, emin, emax, rng)
    o_l3 = over_field(l3, emin, emax, rng)
    # ceiling: the same content resampled ONCE, no averaging
    s_cr = over_field(shift(nn, 0.5, cr_w), emin, emax, rng)
    s_l3 = over_field(shift(nn, 0.5, l3_w), emin, emax, rng)

    print("Statistic: p99.9 excursion beyond the nearest arm's 3x3 envelope,")
    print("as a % of local range. Restricted to top-decile-gradient pixels")
    print(f"(|grad| >= {gthr:.1f} DN) -- ringing only happens at edges.\n")
    print(f"{'stratum':12s} {'edge n':>9s} | {'MERGED cr':>10s} {'MERGED l3':>10s} "
          f"{'ratio':>7s} | {'1-SHOT cr':>10s} {'1-SHOT l3':>10s} {'ratio':>7s} | "
          f"{'survival':>9s}")
    rows = {}
    for nm, lo, hi in STRATA:
        m = (ne >= lo) & (ne <= hi) & (g >= gthr)
        if m.sum() < 2000:
            continue
        mc, ml = np.percentile(o_cr[m], 99.9), np.percentile(o_l3[m], 99.9)
        sc, sl = np.percentile(s_cr[m], 99.9), np.percentile(s_l3[m], 99.9)
        # excess of l3 over cr, merged vs single-shot
        ex_m, ex_s = ml - mc, sl - sc
        surv = ex_m / ex_s if ex_s > 1e-12 else float("nan")
        rows[nm] = dict(n=int(m.sum()), merged_cr=mc, merged_l3=ml, merged_ratio=ml/mc,
                        shot_cr=sc, shot_l3=sl, shot_ratio=sl/sc, survival=surv)
        print(f"{nm:12s} {int(m.sum()):9d} | {100*mc:9.2f}% {100*ml:9.2f}% "
              f"{ml/mc:7.3f} | {100*sc:9.2f}% {100*sl:9.2f}% {sl/sc:7.3f} | "
              f"{100*surv:8.1f}%")

    print("\n'survival' = (l3-cr excess in the MERGED arms) / (same excess when the")
    print("content is resampled ONCE). 100% would mean the merge removed nothing;")
    print("0% would mean it removed all of it.")

    allm = g >= gthr
    print(f"\nAll edge pixels, no stratification ({int(allm.sum())} px):")
    mc, ml = np.percentile(o_cr[allm], 99.9), np.percentile(o_l3[allm], 99.9)
    sc, sl = np.percentile(s_cr[allm], 99.9), np.percentile(s_l3[allm], 99.9)
    print(f"  merged      cr {100*mc:6.2f}%  l3 {100*ml:6.2f}%  ratio {ml/mc:.3f}")
    print(f"  single-shot cr {100*sc:6.2f}%  l3 {100*sl:6.2f}%  ratio {sl/sc:.3f}")
    print(f"  survival of the excess: {100*(ml-mc)/(sl-sc):.1f}%")

    res = dict(strata=rows, gthr=gthr,
               overall=dict(merged_cr=mc, merged_l3=ml, shot_cr=sc, shot_l3=sl,
                            survival=float((ml-mc)/(sl-sc))))
    json.dump(res, open(os.path.join(OUT, "k13_survival.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k13_survival.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())