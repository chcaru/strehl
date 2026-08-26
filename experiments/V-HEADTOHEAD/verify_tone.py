"""VERIFY the tone inversion, and with it the claim that the prior arm is linear.

If (a) strehl's tone chain is inverted correctly and (b) the prior file really is
LINEAR Rec.2020, then colocated pixels of the two arms must be related by a
STRAIGHT LINE THROUGH THE ORIGIN (a primaries matrix is linear).  Any curvature
is a failure of (a) or (b).  This is the falsifiable check.
"""
import numpy as np, h2h

P, S = h2h.open_arms()
rng = np.random.default_rng(7)
# smooth interior samples only: avoid edges (where a 2 px misregistration would
# masquerade as tone) and avoid clipping.
xs = rng.integers(1200, 6000, 60000); ys = rng.integers(700, 4200, 60000)
sx, sy = h2h.prior_to_strehl(xs.astype(float), ys.astype(float))
sxi = np.rint(sx).astype(int); syi = np.rint(sy).astype(int)
ok = (sxi > 2) & (sxi < S.shape[1] - 3) & (syi > 2) & (syi < S.shape[0] - 3)
xs, ys, sxi, syi = xs[ok], ys[ok], sxi[ok], syi[ok]

def blk(a, y, x, r=2):
    out = np.empty((len(y), 3), np.float64)
    for i in range(len(y)):
        out[i] = np.asarray(a[y[i]-r:y[i]+r+1, x[i]-r:x[i]+r+1, :], np.float64).mean(axis=(0, 1))
    return out

p = blk(P, ys, xs)
s_raw = blk(S, syi, sxi)
keep = (p.max(axis=1) < 0.95) & (p.min(axis=1) > 0.004)
p = p[keep]; s_raw = s_raw[keep]
print("samples:", len(p))

s_lin = h2h.strehl_to_linear(s_raw)
s_dis = s_raw / 65535.0

for label, sv in (("strehl RAW display (as shipped)", s_dis),
                  ("strehl LINEARISED (tone inverted)", s_lin)):
    # fit prior_G = a * strehl_G  (through origin) and look at the residual shape
    x = sv[:, 1]; y = p[:, 1]
    a = (x * y).sum() / (x * x).sum()
    r = y - a * x
    # curvature test: does a quadratic term buy a big reduction?
    A = np.stack([x, x * x], 1)
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = y - A @ c
    # decile means of residual/target -> shape of the departure
    q = np.quantile(x, np.linspace(0, 1, 11))
    dec = [float(np.mean(r[(x >= q[i]) & (x < q[i+1])]) / a) for i in range(10)]
    print(f"\n{label}")
    print(f"  linear-through-origin  slope {a:.4f}  resid rms {r.std():.5f}  (target rms {y.std():.5f})")
    print(f"  + quadratic term       resid rms {r2.std():.5f}   quad/lin coef {c[1]/c[0]:+.4f}")
    print(f"  residual by decile of strehl G (in strehl units):")
    print("   " + " ".join(f"{d:+.4f}" for d in dec))
    print(f"  max |decile bias| = {max(abs(d) for d in dec):.4f}")
