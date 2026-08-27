"""Is the strehl-vs-comparator fine-scale gap explicable by TONE ALONE?

h2h2b.py's GRADE arm failed: a mild S-curve moved the coarse-normalised fine
band by up to 2.90x, which is LARGER than the entire strehl-vs-Zerene gap it
was supposed to measure.  So "normalise by the coarse band" does not make the
statistic grade-invariant, and the Lightroom-vs-RAW confound named in the
README is not a caveat -- it may be the whole result.

This decides that, using the ACTUAL tone difference rather than a hypothetical
one.  Procedure:

  1. Fit a monotone map M: strehl luma -> comparator luma, from CO-LOCATED,
     REGISTERED samples.  M is the empirical tone difference between the two
     renders.  It is fitted on COARSE (4x4 block-averaged) values so that it
     is driven by tone, not by either render's fine detail or noise.
  2. Apply M to strehl's own crop.  This is "strehl, graded the way the
     comparator is graded" -- same pixels, same resolution, same noise, only
     the tone changed.
  3. Compare the coarse-normalised fine-band power of:
        strehl raw          strehl-under-M          comparator
     If strehl-under-M lands at or above the comparator, then the comparator's
     apparent fine-scale advantage is FULLY ACCOUNTED FOR BY TONE and the
     comparison cannot decide resolution.

  4. A ladder of synthetic pure-gamma curves gives the sensitivity: how much
     fine-band movement per unit of tone difference.  Gamma is the mildest
     monotone curve there is, so it bounds the effect from below.

CONTROL: M is fitted from block-averaged data, so it has no access to the fine
bands at all.  If applying it nevertheless moves the fine bands, that movement
is harmonic generation by the curve -- which is precisely the confound.
"""
import sys

import numpy as np
import tifffile

import h2
import rois
from h2h2b import COMP, Comp, coarse, band_power, load, T, PAD, REF

NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])


def fit_map(xs, ys, nq=256):
    q = np.linspace(0.5, 99.5, nq)
    a = np.percentile(xs, q)
    b = np.percentile(ys, q)
    keep = np.concatenate([[True], np.diff(a) > 1e-9])
    return a[keep], b[keep]


def apply_map(m, v):
    return np.interp(v, m[0], m[1])


def norm_mean(rows):
    r = np.array(rows)
    ref = r[:, REF]
    ok = ref > 0
    return (r[ok] / ref[ok, None]).mean(0)


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    cfg = COMP[subj]
    S = cfg["scale"]
    TC = int(round(T / S))
    print("=" * 104)
    print(f"TONE-SUFFICIENCY TEST : {subj}  strehl vs {cfg['label']}")
    print("=" * 104)

    F = load(f"{subj}-full-g1")
    X = Comp(cfg)
    detail, flat, counts = rois.census(F, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    pairs = []
    drop = 0
    for (y, x) in det:
        cs, ns = F.crop(y, x, T)
        if ns:
            drop += 1
            continue
        y0, x0 = int(round(y / S)), int(round(x / S))
        cx, ncl = X.crop(y0, x0, TC)
        if cx is None or ncl:
            drop += 1
            continue
        a, b = coarse(cs), coarse(cx)
        n = min(a.shape[0], b.shape[0])
        dy, dx, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        if pk < 0.30:
            drop += 1
            continue
        cx, ncl = X.crop(y0 + dy * 4, x0 + dx * 4, TC)
        if cx is None or ncl:
            drop += 1
            continue
        pairs.append((cs, cx))
    print(f"  {len(det)} ROIs offered = {len(pairs)} registered + {drop} dropped")
    assert len(pairs) + drop == len(det)
    if len(pairs) < 8:
        print("  too few; abandoned")
        return 0

    # ---- fit the empirical tone map on COARSE data only ---------------------
    xs = np.concatenate([coarse(a, 4).ravel() for a, b in pairs])
    ys = np.concatenate([coarse(b, 4).ravel() for a, b in pairs])
    M = fit_map(xs, ys)
    lx, ly = np.log(np.maximum(M[0], 1e-9)), np.log(np.maximum(M[1], 1e-9))
    sl = np.diff(ly) / np.maximum(np.diff(lx), 1e-9)
    sl = sl[np.isfinite(sl)]
    print(f"\n  empirical tone map strehl->comparator, fitted on 4x4 BLOCK "
          f"MEANS (no access to any fine band):")
    print(f"    d(log comp)/d(log strehl): median {np.median(sl):.3f}  "
          f"10-90% [{np.percentile(sl,10):.3f},{np.percentile(sl,90):.3f}]"
          f"   (1.000 == identical tone)")

    rowsS, rowsM, rowsX = [], [], []
    for cs, cx in pairs:
        rowsS.append(band_power(cs, LO, HI))
        rowsM.append(band_power(apply_map(M, cs), LO, HI))
        rowsX.append(band_power(cx, LO * S, HI * S))
    nS, nM, nX = norm_mean(rowsS), norm_mean(rowsM), norm_mean(rowsX)

    hdr = " ".join(nm.center(11) for nm in NAMES)
    print(f"\n  {'':<34} {hdr}")

    def prow(label, v, fmt="{:11.4e}"):
        print(f"  {label:<34} " + " ".join(fmt.format(z) for z in v))

    print(f"\n=== coarse-normalised spectra (each / its own {NAMES[REF]} band) ===")
    prow("strehl, as rendered", nS)
    prow("strehl, UNDER THE FITTED MAP", nM)
    prow(f"{cfg['label'][:26]}, as rendered", nX)

    print("\n=== does tone alone account for the gap? ===")
    gap = nX / nS
    tone = nM / nS
    prow("gap to explain   comp/strehl", gap, "{:11.4f}")
    prow("tone alone       M(strehl)/strehl", tone, "{:11.4f}")
    prow("fraction of gap explained", np.where(gap > 1, (tone - 1) / np.maximum(gap - 1, 1e-9), np.nan), "{:11.4f}")
    fine = [i for i, nm in enumerate(NAMES) if h2.BANDS[i][0] >= 0.20]
    for i in fine:
        g, t = gap[i], tone[i]
        if g <= 1:
            verd = "no gap to explain"
        elif t >= g:
            verd = "TONE ALONE OVER-EXPLAINS THE GAP -> undecidable"
        elif t > 1 + 0.5 * (g - 1):
            verd = "tone explains most of the gap -> undecidable"
        else:
            verd = "tone does NOT explain the gap"
        print(f"    {NAMES[i]:>11}  gap {g:6.3f}  tone {t:6.3f}   {verd}")

    print("\n=== sensitivity ladder: pure gamma, the mildest monotone curve ===")
    print(f"  {'gamma':<34} {hdr}")
    for gm in (1.10, 1.25, 1.50, 2.00):
        rows = []
        for cs, cx in pairs:
            m = cs.mean()
            rows.append(band_power(m * (cs / m) ** gm, LO, HI))
        v = norm_mean(rows) / nS
        print(f"  {('  x^%.2f  ratio to ungraded' % gm):<34} "
              + " ".join(f"{z:11.4f}" for z in v))
    print("  A pure gamma changes NO resolution whatsoever.  Whatever these")
    print("  rows are not equal to 1.0000 by is pure confound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
