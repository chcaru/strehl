"""Does arcprofile.py's sensitivity depend on the WIDTH of the defect?

The standing fleet question: what property of the input decides whether this
check can see anything, and have I varied it?

arcprofile.py measures a deviation from a far-field reference at d=750-1400 px.
Its PLANT is fixed at d=50-250 px -- narrow, entirely inside the reference.
So every commissioning run tested the instrument only in the regime where it
works. This sweeps the one property the commissioning holds constant.

Truth is fixed by construction: a multiply by PLANT_GAIN over d in [50, W).
A perfect instrument reports the same depth for every W.
"""
import numpy as np
import arcprofile as ap

PROBE = (50, 250)          # fixed, always inside the plant
GAIN = ap.PLANT_GAIN       # 0.85


def main():
    subj = "flower-bud-alone-cpl"
    mask, thr, _, _ = ap.rp.subject_mask(ap.luma(ap.FLIP.format(subj, "estimator")))
    signed = ap.rp.signed_distance(mask)
    base = ap.luma(ap.FLIP.format(subj, "pyramid"))

    print("=" * 78)
    print("WIDTH SWEEP -- the property arcprofile.py's commissioning never varied")
    print("=" * 78)
    print(f"reference annulus : d={ap.REF_LO}-{ap.REF_HI} px")
    print(f"probe band        : d={PROBE[0]}-{PROBE[1]} px (fixed, always planted)")
    print(f"plant             : multiply by {GAIN} over d in [50, W)")
    print(f"signed distance   : max {signed.max():.0f} px in this frame")
    print()
    print("TRUTH IS THE SAME IN EVERY ROW. A correct instrument prints one column.")
    print()

    inband = lambda a: float(a["dev"][(a["ds"] >= PROBE[0]) &
                                      (a["ds"] < PROBE[1])].mean())
    b0 = ap.analyse(base, signed)
    before = inband(b0)
    truth = 100.0 * ((1 + before / 100.0) * GAIN - 1)

    print(f"    {'W px':>7} {'ref DN':>9} {'ref moved':>10} {'RECOVERED':>11} "
          f"{'TRUTH':>9} {'error pt':>9}  verdict   {'ARM RATIO':>10} {'err':>7}")
    rows = []
    other = ap.luma(ap.FLIP.format(subj, "estimator"))
    pmask = (signed >= PROBE[0]) & (signed < PROBE[1])
    r0 = float(np.median(other[pmask]) / np.median(base[pmask]))
    for W in (250, 500, 750, 900, 1100, 1400, 2100, 4000):
        pl = base.copy()
        pb = (signed >= 50) & (signed < W)
        pl[pb] = pl[pb] * GAIN
        a = ap.analyse(pl, signed)
        got = inband(a)
        moved = 100.0 * (a["ref"] - b0["ref"]) / b0["ref"]
        err = got - truth
        v = "ok" if abs(err) < 1.0 else ("DEGRADED" if abs(err) < abs(truth) / 2
                                         else "BLIND")
        rr = float(np.median(other[pmask]) / np.median(pl[pmask]))
        shift = 100.0 * (rr / r0 - 1)
        rtruth = 100.0 * (1 / GAIN - 1)
        rows.append((W, got, err, v, shift, shift - rtruth))
        print(f"    {W:>7} {a['ref']:>9.0f} {moved:>+9.2f}% {got:>+10.2f}% "
              f"{truth:>+8.2f}% {err:>+8.2f}   {v:<9} {shift:>+9.2f}% "
              f"{shift - rtruth:>+6.2f}")

    print()
    print(f"  The plant is IDENTICAL in depth in every row. Only its outer edge "
          f"moves.")
    worst = max(rows, key=lambda r: abs(r[2]))
    print(f"  Worst case W={worst[0]} px: instrument says {worst[1]:+.2f}%, "
          f"truth {truth:+.2f}%, off by {worst[2]:+.2f} points.")
    blind = [r[0] for r in rows if r[3] == "BLIND"]
    if blind:
        print(f"  BLIND at W = {blind} px -- a real {abs(truth):.1f}% darkening "
              f"reported as nothing.")
        print(f"  Mechanism: the plant reaches the reference annulus, so the "
              f"denominator is\n  scaled by the same factor as the numerator "
              f"and the ratio cancels.")
    else:
        print(f"  No blind regime found; the instrument is width-independent.")

    rerr = max(abs(r[5]) for r in rows)
    print()
    print(f"  ARM RATIO column -- the reference-free statistic, same plant. "
          f"Truth {100*(1/GAIN-1):+.2f}%")
    print(f"  in every row. Worst error across the whole sweep: "
          f"{rerr:.2f} points.")
    if rerr < 1.0:
        print(f"  IMMUNE. It uses no reference, so there is no denominator for "
              f"a broad defect to\n  contaminate. The 24-of-24 arm comparison "
              f"in section 17 is unaffected by this finding;\n  the per-arm "
              f"percentages are the part that is bounded.")
    else:
        print(f"  NOT immune -- it degrades too, by up to {rerr:.2f} points.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
