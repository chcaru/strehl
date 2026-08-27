"""Paired spatial bootstrap for the blotch column, plus a degeneracy test.

Two things this settles that the point estimates cannot.

1. RESOLUTION. The blotch column spans 3.4% on the shallow subjects while the
   grain column spans 4-5x over the same arms. Before that is reported as
   "the gate does not move mottle" it has to be shown that 3.4% is inside the
   statistic's noise floor rather than a real small effect. The design is
   paired: the SAME spatial blocks are resampled for every arm, so subject
   structure -- which is identical across arms by construction -- cancels
   inside each resample instead of being averaged over.

2. DEGENERACY OF sharp/flat. ORCH required a sharpness column on the same
   pixels as the blotch. On a site chosen FOR being flat, band energy at
   0.20-0.25 cyc/px is mostly noise, so that column may be a second noise
   column wearing a sharpness label. Measured here as its correlation with
   grain across the arms, rather than asserted.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
from orch_eye_check import boxblur                                # noqa: E402

BLK = 80
MARGIN = 32
NBOOT = 2000


def band_image(c):
    """ORCH's sigma_mid integrand, kept as an image so it can be resampled."""
    return np.mean([boxblur(c[..., k], 10) - boxblur(c[..., k], 30)
                    for k in range(3)], axis=0)


def blocks(d):
    """Per-block sufficient statistics, interior only.

    The box filters are invalid within 30px of an edge, so those pixels are
    dropped. Only (sum, sum of squares, count) are kept: the pooled sigma over
    any subset of blocks is an exact function of those three, so a resample
    never has to materialise the pixels. Doing it the obvious way -- gathering
    (NBOOT, nblocks, BLK, BLK) -- asks for 11 GB and was measured to hang.
    """
    h, w = d.shape
    out = []
    for y in range(MARGIN, h - MARGIN - BLK + 1, BLK):
        for x in range(MARGIN, w - MARGIN - BLK + 1, BLK):
            b = d[y:y + BLK, x:x + BLK]
            out.append((b.sum(), (b ** 2).sum(), b.size))
    return np.array(out, dtype=np.float64)


def run(subject, seed=20260824):
    ref = os.path.join(bl.SWEEP, "WHITE200", subject + ".tiff")
    flat, _, _ = bl.pick_flat_sites(ref)
    per = {}
    for arm in bl.ARMS:
        p = os.path.join(bl.SWEEP, arm, subject + ".tiff")
        if not os.path.exists(p):
            continue
        acc = [blocks(band_image(bl.codes(p, y, x))) for (y, x) in flat]
        per[arm] = np.concatenate(acc)
    arms = list(per)
    n = per[arms[0]].shape[0]
    for a in arms:
        assert per[a].shape[0] == n, (a, per[a].shape, n)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(NBOOT, n))

    def sig(st):
        # Pooled sigma over the resampled blocks, from sufficient statistics.
        # Identical to sigma over the pooled pixels, which is what sigma_mid
        # computes -- evaluated on a resample of its own support.
        s1, s2, n = st[..., 0].sum(-1), st[..., 1].sum(-1), st[..., 2].sum(-1)
        return np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0.0))

    bs = sig(per["WHITE200"][idx])
    out = {}
    for a in arms:
        r = sig(per[a][idx]) / bs
        out[a] = (float(np.mean(r)), float(np.percentile(r, 2.5)),
                  float(np.percentile(r, 97.5)))
    return out, n


def main():
    # Commission the shortcut before quoting any interval from it. The pooled
    # sigma is computed from per-block (sum, sumsq, n); if that identity is
    # wrong every CI below is decoration. Checked against a direct sigma over
    # the same pixels, on real data, not a synthetic array.
    ref = os.path.join(bl.SWEEP, "WHITE200", sys.argv[1] + ".tiff")
    fl, _, _ = bl.pick_flat_sites(ref)
    di = band_image(bl.codes(ref, *fl[0]))
    st = blocks(di)
    direct = np.concatenate([di[y:y + BLK, x:x + BLK].ravel()
                             for y in range(MARGIN, di.shape[0] - MARGIN - BLK + 1, BLK)
                             for x in range(MARGIN, di.shape[1] - MARGIN - BLK + 1, BLK)])
    a = float(np.sqrt(st[:, 1].sum() / st[:, 2].sum()
                      - (st[:, 0].sum() / st[:, 2].sum()) ** 2))
    b = float(direct.std())
    rel = abs(a - b) / b
    print("COMMISSION the sufficient-statistic shortcut: pooled sigma %.10f vs "
          "direct sigma %.10f, rel %.2e  %s"
          % (a, b, rel, "ok" if rel < 1e-9 else "FAIL"))
    if rel >= 1e-9:
        sys.exit(1)

    print("\nPaired spatial bootstrap of the blotch column, %dpx blocks, "
          "%d resamples." % (BLK, NBOOT))
    print("Ratio vs WHITE200 with a 95%% CI. A CI containing 1.0 means the arm "
          "did not move blotch.\n")
    res = {}
    for s in sys.argv[1:]:
        out, n = run(s)
        res[s] = out
        print("%s  N=%d frames, %d paired blocks" % (s, bl.NFRAMES[s], n))
        for a in bl.ARMS:
            if a not in out:
                continue
            m, lo, hi = out[a]
            flag = "" if (lo <= 1.0 <= hi) else "  *moved"
            print("  %-9s %8.4f  [%.4f, %.4f]%s" % (a, m, lo, hi, flag))
        print()

    print("DEGENERACY TEST: is sharp/flat a sharpness column or a second noise "
          "column?")
    print("Pearson r between sharp/flat and grain across the 7 arms, per "
          "subject. r near 1 means the column carries no independent "
          "information about detail on those pixels.")
    for s in sys.argv[1:]:
        rows, _, _, _, _ = __import__("blotch_sweep").run(s)
        g = np.array([rows[a][1] for a in bl.ARMS if a in rows])
        f = np.array([rows[a][2] for a in bl.ARMS if a in rows])
        t = np.array([rows[a][3] for a in bl.ARMS if a in rows])
        print("  %-22s r(sharp/flat, grain) = %.4f   r(sharp/tex, grain) = %.4f"
              % (s, np.corrcoef(g, f)[0, 1], np.corrcoef(g, t)[0, 1]))


if __name__ == "__main__":
    main()
