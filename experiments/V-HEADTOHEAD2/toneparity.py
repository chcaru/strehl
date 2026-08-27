"""Does the tone confound that killed the head-to-head also kill the FLIP result?

gradetest.py showed that a tone map fitted on 4x4 BLOCK MEANS -- which contains
no fine-scale information at all -- reproduces Zerene's 0.25-0.30 band from
strehl's own pixels to 0.02%.  That destroys the comparator comparison.

The same test must now be aimed at my own result, because a finding that
survives only because nobody pointed the gun at it is not a finding.

If STREHL_FULLRES_GATHER=1 differed from =0 by a tone change, then the same
procedure would reproduce the post-flip fine bands from the pre-flip pixels.
Three arms, in increasing strength:

  ARM 1  LEVEL PARITY.  Do the two arms even have different tone?  Percentiles
         of the two renders over identical ROIs.  Both are --linear-srgb, no
         auto-tone, identical flags, one binary.  Expect: identical.
  ARM 2  TONE SUFFICIENCY.  Fit g0->g1 on block means, apply to g0, ask whether
         it reproduces g1's fine bands.  Expect: NO (unlike the comparator).
  ARM 3  POTENCY OF ARM 2.  The same procedure run on the pair it is known to
         explain (strehl -> Zerene) must still explain it, when run from this
         script on this ROI set.  Without this, a negative in ARM 2 could just
         mean the code is broken.
"""
import sys

import numpy as np

import h2
import rois
from h2h2b import COMP, Comp, coarse, band_power, load, T, PAD, REF
from gradetest import fit_map, apply_map, norm_mean, NAMES, LO, HI


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    print("=" * 104)
    print(f"IS THE FLIP RESULT A TONE ARTEFACT?  subject {subj}")
    print("=" * 104)

    G1 = load(f"{subj}-full-g1"); G0 = load(f"{subj}-full-g0")
    A1 = load(f"{subj}-A-g1"); B1 = load(f"{subj}-B-g1")
    A0 = load(f"{subj}-A-g0"); B0 = load(f"{subj}-B-g0")
    detail, flat, counts = rois.census(G1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    crops = []
    drop = 0
    for (y, x) in det:
        c1, n1 = G1.crop(y, x, T); c0, n0 = G0.crop(y, x, T)
        ca1, na1 = A1.crop(y, x, T); cb1, nb1 = B1.crop(y, x, T)
        ca0, na0 = A0.crop(y, x, T); cb0, nb0 = B0.crop(y, x, T)
        if n1 or n0 or na1 or nb1 or na0 or nb0:
            drop += 1
            continue
        crops.append((c0, c1, ca0, cb0, ca1, cb1))
    print(f"  {len(det)} ROIs offered = {len(crops)} used + {drop} dropped (clipped)")
    assert len(crops) + drop == len(det)

    # ---------------- ARM 1 -------------------------------------------------
    print("\n--- ARM 1: level parity between the two gather modes ---")
    v0 = np.concatenate([c[0][::8, ::8].ravel() for c in crops])
    v1 = np.concatenate([c[1][::8, ::8].ravel() for c in crops])
    q = [1, 5, 25, 50, 75, 95, 99]
    p0 = np.percentile(v0, q); p1 = np.percentile(v1, q)
    print("     pct     g0(pre)      g1(post)     ratio")
    for qq, a, b in zip(q, p0, p1):
        print(f"    {qq:3d}   {a:11.2f}  {b:11.2f}   {b/a:7.4f}")
    dev = np.abs(p1 / p0 - 1).max()
    print(f"  worst percentile deviation {100*dev:.3f}%  -> "
          f"{'the two arms share a tone curve' if dev < 0.02 else 'TONE DIFFERS'}")

    # ---------------- ARM 2 -------------------------------------------------
    print("\n--- ARM 2: can a block-mean tone map turn g0 into g1's spectrum? ---")
    xs = np.concatenate([coarse(c[0], 4).ravel() for c in crops])
    ys = np.concatenate([coarse(c[1], 4).ravel() for c in crops])
    M = fit_map(xs, ys)
    r0 = norm_mean([band_power(c[0], LO, HI) for c in crops])
    r1 = norm_mean([band_power(c[1], LO, HI) for c in crops])
    rm = norm_mean([band_power(apply_map(M, c[0]), LO, HI) for c in crops])
    hdr = " ".join(nm.center(11) for nm in NAMES)
    print(f"\n  {'':<34} {hdr}")

    def prow(label, v, fmt="{:11.4e}"):
        print(f"  {label:<34} " + " ".join(fmt.format(z) for z in v))

    prow("g0 (pre-flip), normalised", r0)
    prow("g0 UNDER THE FITTED g0->g1 MAP", rm)
    prow("g1 (post-flip), normalised", r1)
    gap = r1 / r0
    tone = rm / r0
    prow("gap to explain  g1/g0", gap, "{:11.4f}")
    prow("tone alone      M(g0)/g0", tone, "{:11.4f}")
    print()
    verdicts = []
    for i, nm in enumerate(NAMES):
        if h2.BANDS[i][0] < 0.20:
            continue
        g, t = gap[i], tone[i]
        frac = (t - 1) / (g - 1) if g > 1.0001 else float("nan")
        ok = (g > 1.0001) and (frac < 0.25)
        verdicts.append(ok)
        print(f"    {nm:>11}  gap {g:6.3f}  tone {t:6.3f}  "
              f"tone explains {100*frac:6.1f}% of it   "
              f"{'-> NOT a tone artefact' if ok else '-> TONE MAY EXPLAIN IT'}")
    print(f"  ARM 2 VERDICT: {'PASS' if all(verdicts) else 'FAIL'} "
          f"({sum(verdicts)}/{len(verdicts)} fine bands under 25%)")

    # ---------------- ARM 3 -------------------------------------------------
    print("\n--- ARM 3: potency. The same code, on the pair it is KNOWN to "
          "explain ---")
    cfg = COMP[subj]
    S = cfg["scale"]
    TC = int(round(T / S))
    X = Comp(cfg)
    pr = []
    for (y, x), c in zip([d for d in det], crops):
        pass
    idx = 0
    pairs = []
    for (y, x) in det:
        c1, n1 = G1.crop(y, x, T)
        if n1:
            continue
        y0, x0 = int(round(y / S)), int(round(x / S))
        cx, ncl = X.crop(y0, x0, TC)
        if cx is None or ncl:
            continue
        a, b = coarse(c1), coarse(cx)
        n = min(a.shape[0], b.shape[0])
        dy, dx, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        if pk < 0.30:
            continue
        cx, ncl = X.crop(y0 + dy * 4, x0 + dx * 4, TC)
        if cx is None or ncl:
            continue
        pairs.append((c1, cx))
    if len(pairs) < 8:
        print(f"  only {len(pairs)} registered pairs -- POTENCY NOT ESTABLISHED, "
              f"so ARM 2's negative is not trustworthy on this subject")
        return 0
    xs = np.concatenate([coarse(a, 4).ravel() for a, b in pairs])
    ys = np.concatenate([coarse(b, 4).ravel() for a, b in pairs])
    MX = fit_map(xs, ys)
    sS = norm_mean([band_power(a, LO, HI) for a, b in pairs])
    sM = norm_mean([band_power(apply_map(MX, a), LO, HI) for a, b in pairs])
    sX = norm_mean([band_power(b, LO * S, HI * S) for a, b in pairs])
    gapx = sX / sS
    tonex = sM / sS
    print(f"  {len(pairs)} registered pairs, strehl vs {cfg['label']}")
    prow("gap to explain  comp/strehl", gapx, "{:11.4f}")
    prow("tone alone      M(strehl)/strehl", tonex, "{:11.4f}")
    pot = []
    for i, nm in enumerate(NAMES):
        if h2.BANDS[i][0] < 0.20 or gapx[i] <= 1.0001:
            continue
        frac = (tonex[i] - 1) / (gapx[i] - 1)
        pot.append(frac > 0.5)
        print(f"    {nm:>11}  tone explains {100*frac:6.1f}% of the "
              f"comparator gap")
    print(f"  ARM 3 VERDICT: {'PASS' if any(pot) else 'FAIL'} -- the procedure "
          f"{'does' if any(pot) else 'does NOT'} still fire where it should, so "
          f"ARM 2's negative {'means something' if any(pot) else 'means nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
