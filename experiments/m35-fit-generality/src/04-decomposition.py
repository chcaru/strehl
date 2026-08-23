"""M35 step 4: is M33's headline confounded? Separate the log domain from the baseline.

Step 3 reproduced M33's published calibration EXACTLY (parabola 0.457, log 0.710)
and then failed to reproduce M35 script 02's 0.549/0.841 from the three factors it
tested.  The residual has a single cause: script 02 fed the parabola
BASELINE-SUBTRACTED samples, while M33 script 04 fed it RAW ones.

That matters more than a harness detail, because M33 script 04's real-data arm ran
exactly three modes:

    ("parabola", base=0.0)   ("log", base=0.0)   ("log_baseline", base=p5)

There is no `parabola_baseline` arm.  So fact 272 compares a RAW parabola against
a BASELINE-SUBTRACTED log fit, and two things changed at once.  The relative
deficit `1 - a0/peak` is not shift-invariant for the parabola either -- subtracting
a floor rescales exactly the quantity being reported -- so some unknown share of
the log fit's measured advantage may be the baseline rather than the log domain.

This script runs the missing 2x2 on M33's own cell (its 40,000 pixels, its 5th
percentile baseline, its median-of-ratios statistic, its random stream), so the
only thing varying is the estimator:

                     raw            baseline-subtracted
    parabola      [M33's 0.457]     [never measured]
    log           [M33 has this]    [M33's 0.710]

If the baseline-subtracted parabola lands near 0.710, fact 272 is measuring the
baseline and not the log domain, and the fact needs rewriting.  If it lands near
0.457, the log domain is doing the work and fact 272 stands as published.

PRE-REGISTERED: I expect the baseline-subtracted parabola to land between the two,
around 0.55, which would mean roughly a third of the published margin is baseline
and two thirds is the log domain -- fact 272 survives but its magnitude is
overstated.  I am registering this because I have already folded fact 272 into
SYNTHESIS, and a prediction made after seeing the answer is worthless.
"""
import numpy as np, os, json

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

V = np.asarray(np.load(M33, mmap_mode="r"), np.float32)
nd = V.shape[0]


def three_point(am_, a0, ap):
    dn = am_ - 2 * a0 + ap
    ok = dn < -1e-12
    sh = np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)
    return ok, np.where(ok, a0 + 0.25 * (ap - am_) * sh, a0)


def deficit(am_, a0, ap, domain, base):
    lo = 1e-9
    xm, x0, xp = (np.maximum(v - base, lo) for v in (am_, a0, ap))
    if domain == "parabola":
        ok, pk = three_point(xm, x0, xp)
        return ok, 1 - x0 / np.maximum(pk, 1e-12)
    ok, pk = three_point(np.log(xm), np.log(x0), np.log(xp))
    return ok, 1 - x0 / np.maximum(np.exp(pk), 1e-12)


out = {}
for STEP, tag in ((2, "x2"), (4, "x4")):
    r2 = np.random.default_rng(20260812)                 # M33's stream
    b = 8
    iy = r2.integers(b, V.shape[1] - b, 40000)
    ix = r2.integers(b, V.shape[2] - b, 40000)
    D = V[:, iy, ix].astype(np.float64)
    dense_max, k_dense = D.max(0), D.argmax(0)
    interior = (k_dense >= 2) & (k_dense <= nd - 3)
    S = D[list(range(0, nd, STEP))]
    m, ar = S.shape[0], np.arange(D.shape[1])
    j = S.argmax(0)
    true_def = 1 - S.max(0) / dense_max
    jj = np.clip(j, 1, m - 2)
    a0, am_, ap = S[jj, ar], S[jj - 1, ar], S[jj + 1, ar]
    p5 = np.percentile(S, 5, axis=0)
    inner = interior & (j >= 1) & (j <= m - 2) & (true_def > 1e-12)

    cell = {}
    for domain in ("parabola", "log"):
        for bname, bv in (("raw", 0.0), ("baseline", p5)):
            ok, pd = deficit(am_, a0, ap, domain, bv)
            g = inner & ok
            r = pd[g] / true_def[g]
            cell[f"{domain}_{bname}"] = dict(
                calib_median=float(np.median(r)),
                within2x=float(((r > 0.5) & (r < 2.0)).mean()),
                n=int(g.sum()))
    out[tag] = cell
    print(f"\n--- {tag} (M33's cell: 40k px, p5 baseline, median of ratios) ---")
    for k, v in cell.items():
        print(f"  {k:18s} calib {v['calib_median']:.3f}   within2x {v['within2x']:.1%}   n={v['n']}")

    pr, pb = cell["parabola_raw"]["calib_median"], cell["parabola_baseline"]["calib_median"]
    lr, lb = cell["log_raw"]["calib_median"], cell["log_baseline"]["calib_median"]
    tot = lb - pr
    print(f"  published margin (log_baseline - parabola_raw) = {tot:+.3f}")
    if abs(tot) > 1e-9:
        print(f"    attributable to the BASELINE  (parabola_baseline - parabola_raw) ="
              f" {pb-pr:+.3f}  = {100*(pb-pr)/tot:.0f}% of the margin")
        print(f"    attributable to the LOG DOMAIN (log_baseline - parabola_baseline) ="
              f" {lb-pb:+.3f}  = {100*(lb-pb)/tot:.0f}% of the margin")
    out[tag]["margin_total"] = float(tot)
    out[tag]["margin_from_baseline"] = float(pb - pr)
    out[tag]["margin_from_log"] = float(lb - pb)

json.dump(out, open(os.path.join(OUT, "04-decomposition.json"), "w"), indent=1)
print("\nwrote 04-decomposition.json")
