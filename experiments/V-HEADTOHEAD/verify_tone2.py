"""Second, stronger check of the tone inversion: scan an exponent.

Fit prior_RGB = M @ (strehl_RGB ** gamma) for a free 3x3 M at each gamma.
If strehl is correctly linearised AND prior is linear, the best gamma is 1.0
(the two are then related by a pure primaries matrix).  A wrong linearisation
shows up as gamma != 1.  This has power to fail: the SAME code run on the
un-inverted display values must return gamma far from 1.
"""
import numpy as np, h2h
P, S = h2h.open_arms()
rng = np.random.default_rng(11)
xs = rng.integers(1200, 6000, 40000); ys = rng.integers(700, 4200, 40000)
sx, sy = h2h.prior_to_strehl(xs.astype(float), ys.astype(float))
sxi = np.rint(sx).astype(int); syi = np.rint(sy).astype(int)
def blk(a, y, x, r=2):
    o = np.empty((len(y), 3))
    for i in range(len(y)):
        o[i] = np.asarray(a[y[i]-r:y[i]+r+1, x[i]-r:x[i]+r+1, :], np.float64).mean(axis=(0,1))
    return o
p = blk(P, ys, xs); s = blk(S, syi, sxi)
k = (p.max(1) < 0.95) & (p.min(1) > 0.004)
p, s = p[k], s[k]
lin = h2h.strehl_to_linear(s); dis = s / 65535.0
print("samples", len(p))
for label, sv in (("as-shipped display", dis), ("tone-inverted linear", lin)):
    best = None
    for g in np.arange(0.40, 3.01, 0.02):
        X = np.clip(sv, 1e-9, None) ** g
        M, *_ = np.linalg.lstsq(X, p, rcond=None)
        r = p - X @ M
        e = float(np.sqrt((r ** 2).mean()))
        if best is None or e < best[1]:
            best = (g, e, M)
    g, e, M = best
    X = np.clip(sv, 1e-9, None)
    M1, *_ = np.linalg.lstsq(X, p, rcond=None)
    e1 = float(np.sqrt(((p - X @ M1) ** 2).mean()))
    print(f"\n{label}: best gamma = {g:.2f} (rms {e:.5f});  gamma=1 rms {e1:.5f}  ratio {e1/e:.3f}")
    print("  matrix at gamma=1 (strehl->prior), rows = strehl RGB:")
    for row in M1:
        print("    " + " ".join(f"{v:+.4f}" for v in row))
