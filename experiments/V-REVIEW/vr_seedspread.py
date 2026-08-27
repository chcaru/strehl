"""How many independent degrees of freedom does a 900 px window hold at 50-400 px?

The 800 DN plant LOWERED band from 2064.80 to 2014.82 while contributing 444.20
of its own.  Quadrature would predict 2112.0.  The deficit is a cross-term:
corr = -0.219.  If that is sampling noise, then over seeds the band must move
BOTH ways with a spread ~ 1/sqrt(N_eff) -- and the detection floor of any
single-seed plant ladder is seed-dependent and must be quoted as a spread.
"""
import os, sys
import numpy as np, cv2, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V
import orch_blotch as OB

FY, FX, W = 2254, 5926, OB.WIN


def box(a, r):
    return cv2.blur(a, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


img = tifffile.imread(V.master_path("112MSDCF"))
lum = V.lum_of(img[:, :, :3].astype(np.float32))
blk = lum[FY:FY + W, FX:FX + W].copy()
r0, b0, n0, m0 = OB.blotch_ratio(blk)
print("clean    blotch %.5f  band %8.2f  mean %9.2f" % (r0, b0, m0))
print("")
print("%4s %6s | %9s %9s %9s %9s %8s" %
      ("seed", "amp", "band", "quadpred", "corr", "blotch", "d vs base"))
h, w = lum.shape
for amp in (400.0, 800.0, 1600.0, 3200.0, 6400.0):
    got = []
    for seed in range(1, 9):
        rng = np.random.default_rng(seed)
        n = rng.standard_normal((h, w), dtype=np.float32)
        m = box(n, 100) - box(box(n, 100), 400)
        m *= (amp / m.std())
        mw = m[FY:FY + W, FX:FX + W]
        _, bp, _, _ = OB.blotch_ratio(mw + 10000.0)
        r, b, nn, mm = OB.blotch_ratio(blk + mw)
        quad = float(np.hypot(b0, bp))
        corr = (b * b - b0 * b0 - bp * bp) / (2 * b0 * bp)
        got.append(r)
        print("%4d %6.0f | %9.2f %9.2f %9.3f %9.5f %+7.2f%%"
              % (seed, amp, b, quad, corr, r, 100 * (r - r0) / r0))
    g = np.array(got)
    print("  amp %.0f: blotch over 8 seeds  min %.5f  max %.5f  mean %.5f  sd %.5f"
          % (amp, g.min(), g.max(), g.mean(), g.std()))
    d = 100 * np.abs(g - r0) / r0
    print("  amp %.0f: |delta| vs baseline  min %.2f%%  max %.2f%%   FIRES at tol=2%%: %d of %d seeds"
          % (amp, d.min(), d.max(), int((d > 2.0).sum()), len(d)))
    print("")
neff = (W / 200.0) ** 2
print("effective independent blobs in a %d px window at ~200 px scale: ~%.0f"
      % (W, neff))
print("expected sampling sd of the cross-correlation: ~1/sqrt(%.0f) = %.3f" % (neff, 1 / np.sqrt(neff)))
