"""Is D = max/min sufficient, or does composition depth qualify it?

ORCH's unified rule says exposure is governed by what the statistic reads
(value vs position) and by D = max/min of its terms. M111 has four cross-arm
statistics from the same pixels whose D ordering does NOT match their measured
exposure ordering:

    blobA interior flatness  D = 1.006  ->  -0.04%
    blobA boundary hardness  D = 3.111  ->  -7.60%
    blobB boundary hardness  D = 6.105  ->  -8.72%
    blobB interior flatness  D = 8.050  ->  +2.99%   <- highest D, near-immune

Four points is not a result. This tests it at n ~ 1500.

THE PROPOSED MECHANISM. The two statistics differ in COMPOSITION DEPTH, not in
D. Boundary hardness divides two RAW gradient energies, one per arm. Interior
flatness divides two RATIOS, each of which is already an inside/outside ratio
computed WITHIN one arm. Quantisation inflates both of an inner ratio's terms
in the same direction, so each inner ratio has already cancelled once before
the outer division happens. If that is right, D governs the family whose terms
are raw energies and under-predicts protection for the family whose terms are
themselves ratios -- and D alone would then send a fleet to re-run work on the
composed family that is in fact fine.

PRE-REGISTERED, before these numbers exist:

  E1 within family R (raw energies, the boundary-hardness shape), |shift| rises
     with D: Spearman rho > +0.30. This must reproduce ORCH's own result, and
     if it fails the instrument is wrong and nothing else here is readable.
  E2 within family Q (ratio of within-arm ratios, the interior-flatness shape),
     D does not govern: |rho| < 0.30.
  E3 THE DECISIVE ONE. Restricted to tiles where BOTH families are in the
     high-D regime (D >= 4 in each), family Q's median |shift| is below family
     R's by at least a factor of 2. Same D, different exposure => D is not
     sufficient and composition depth is the missing variable.
  E4 NULL / SELF-REFUTATION. If E3 fails -- Q within 2x of R at matched D --
     then D IS sufficient, my four-statistic ordering was small-sample noise,
     and I report that against myself rather than qualifying ORCH's rule.

Reads only from C:\\dev\\strehl-out\\. Writes only
C:\\dev\\strehl-out\\M111-pil-audit\\composition_depth.json.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
TILE = 256
STRIDE = int(os.environ.get("M111_STRIDE", "128"))
INNER = 96
BINS = [1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 8.0, np.inf]


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float64)
            + 0.7152 * a[..., 1].astype(np.float64)
            + 0.0722 * a[..., 2].astype(np.float64))


def gmag(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else 0.0


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    assert mt.dtype == np.uint16 and ct.dtype == np.uint16
    mp = np.asarray(Image.open(MERGED))
    cp = np.asarray(Image.open(CTRL))
    assert mp.dtype == np.uint8, "PIL arm did not narrow; test is void"
    print("tifffile %s %s   PIL %s %s" % (mt.dtype, mt.shape, mp.dtype, mp.shape))

    h = min(mt.shape[0], ct.shape[0], mp.shape[0], cp.shape[0])
    w = min(mt.shape[1], ct.shape[1], mp.shape[1], cp.shape[1])
    lo, hi = (TILE - INNER) // 2, (TILE - INNER) // 2 + INNER

    R, Q = [], []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            sl = (slice(y0, y0 + TILE), slice(x0, x0 + TILE))
            gm_t, gc_t = gmag(luma(mt[sl])), gmag(luma(ct[sl]))
            gm_p, gc_p = gmag(luma(mp[sl])), gmag(luma(cp[sl]))
            if gm_t.mean() < 1.0 or gc_t.mean() < 1.0:
                continue

            # Family R: two RAW energies, one per arm.
            a_t, b_t = float(np.percentile(gm_t, 90)), float(np.percentile(gc_t, 90))
            a_p, b_p = float(np.percentile(gm_p, 90)), float(np.percentile(gc_p, 90))
            if min(a_t, b_t) > 1e-9 and min(a_p, b_p) > 1e-9:
                s_t, s_p = a_t / b_t, a_p / b_p
                R.append((max(a_t, b_t) / min(a_t, b_t),
                          abs(100.0 * (s_p - s_t) / s_t)))

            # Family Q: two WITHIN-ARM ratios, then divided.
            def inner(g):
                i = float(g[lo:hi, lo:hi].mean())
                o = float(g.mean() * g.size - g[lo:hi, lo:hi].sum()) / (g.size - INNER ** 2)
                return i / o if o > 1e-9 else np.nan

            qm_t, qc_t = inner(gm_t), inner(gc_t)
            qm_p, qc_p = inner(gm_p), inner(gc_p)
            if all(np.isfinite(v) and v > 1e-9 for v in (qm_t, qc_t, qm_p, qc_p)):
                s_t, s_p = qm_t / qc_t, qm_p / qc_p
                Q.append((max(qm_t, qc_t) / min(qm_t, qc_t),
                          abs(100.0 * (s_p - s_t) / s_t)))

    R, Q = np.asarray(R), np.asarray(Q)
    print("family R (raw energies)      n = %d" % len(R))
    print("family Q (ratio of ratios)   n = %d" % len(Q))

    def table(name, arr):
        print("\n%s  median |shift| by D" % name)
        rows = []
        for i in range(len(BINS) - 1):
            m = (arr[:, 0] >= BINS[i]) & (arr[:, 0] < BINS[i + 1])
            med = float(np.median(arr[m, 1])) if m.sum() else float("nan")
            rows.append({"lo": BINS[i], "hi": None if np.isinf(BINS[i + 1]) else BINS[i + 1],
                         "n": int(m.sum()), "median_shift_pct": med})
            print("   D [%.2f,%s)  n=%5d   %8.2f %%"
                  % (BINS[i], "inf" if np.isinf(BINS[i + 1]) else "%.2f" % BINS[i + 1],
                     m.sum(), med))
        return rows

    rowsR, rowsQ = table("R", R), table("Q", Q)
    rhoR, rhoQ = spearman(R[:, 0], R[:, 1]), spearman(Q[:, 0], Q[:, 1])

    hiR = R[R[:, 0] >= 4.0, 1]
    hiQ = Q[Q[:, 0] >= 4.0, 1]
    medR = float(np.median(hiR)) if len(hiR) else float("nan")
    medQ = float(np.median(hiQ)) if len(hiQ) else float("nan")
    factor = medR / medQ if medQ > 1e-9 else float("inf")

    e1 = rhoR > 0.30
    e2 = abs(rhoQ) < 0.30
    e3 = (len(hiR) >= 30 and len(hiQ) >= 30 and factor >= 2.0)

    print("\n[pre-registered gates]")
    print("  E1 D governs family R (rho > +0.30) : %s  (rho %+.3f)"
          % ("PASS" if e1 else "FAIL", rhoR))
    print("  E2 D does not govern family Q       : %s  (rho %+.3f)"
          % ("PASS" if e2 else "FAIL", rhoQ))
    print("  E3 at matched D>=4, Q >=2x milder   : %s  (R %.2f%% n=%d vs Q %.2f%% n=%d, %.2fx)"
          % ("PASS" if e3 else "FAIL", medR, len(hiR), medQ, len(hiQ), factor))
    verdict = ("D IS NOT SUFFICIENT: composition depth qualifies it" if e3 else
               "E4 SELF-REFUTATION: D is sufficient; M111's four-statistic ordering was noise")
    print("\nVERDICT: %s" % verdict)

    doc = {"tile": TILE, "stride": STRIDE, "inner": INNER,
           "n_R": len(R), "n_Q": len(Q), "bins_R": rowsR, "bins_Q": rowsQ,
           "spearman_R": rhoR, "spearman_Q": rhoQ,
           "matched_highD": {"threshold": 4.0, "median_R_pct": medR, "n_R": len(hiR),
                             "median_Q_pct": medQ, "n_Q": len(hiQ), "factor": factor},
           "gates": {"E1": bool(e1), "E2": bool(e2), "E3": bool(e3)},
           "verdict": verdict}
    dst = os.path.join(OUT, "composition_depth.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
