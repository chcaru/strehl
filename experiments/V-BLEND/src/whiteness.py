"""Is the energy WHITE? Tested against the honest counterfactual.

ORCH compared each arm's correlation against a SYNTHETIC white field pushed
through the same high-pass (rho = -0.0035) and concluded that rho >> 0 means
the energy is optical detail rather than noise.

That counterfactual is only right if real sensor noise ARRIVES white at the
output. It does not: every render here goes through a Malvar-He-Cutler demosaic
and a CatmullRom resample, and both are low-pass filters that correlate
neighbouring pixels. So the correct "if it were noise" reference is REAL SENSOR
NOISE THAT HAS BEEN THROUGH THE SAME CHAIN -- i.e. a single-frame render.

This measures rho for: synthetic white, a single frame, both arms, and the
literal difference between the arms.
"""
import sys
import numpy as np
import tifffile
from noisefloor import tiles, sigma_std, immerkaer, BOX

def green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)

def resid(t):
    """tile minus a fitted quadratic -- removes scene gradient, keeps texture."""
    from noisefloor import _basis, _Q
    box = t.shape[1]
    if box not in _Q: _Q[box] = _basis(box)
    Q = _Q[box]
    f = t.reshape(t.shape[0], -1)
    return (f - (f @ Q) @ Q.T).reshape(t.shape)

def rho_lag1(t):
    """Normalised lag-1 autocorrelation, mean of horizontal and vertical.
    White noise -> 0. Any low-pass -> positive."""
    r = resid(t)
    r = r - r.mean(axis=(1, 2), keepdims=True)
    v = (r*r).mean(axis=(1, 2))
    h = (r[:, :, :-1]*r[:, :, 1:]).mean(axis=(1, 2))
    w = (r[:, :-1, :]*r[:, 1:, :]).mean(axis=(1, 2))
    return 0.5*(h+w)/np.maximum(v, 1e-12)

def hf_fraction(t):
    """Fraction of residual power above half-Nyquist. White ~ 0.75 in 2D."""
    r = resid(t)
    F = np.abs(np.fft.fft2(r, axes=(1, 2)))**2
    n = r.shape[1]
    fy = np.fft.fftfreq(n)[:, None]; fx = np.fft.fftfreq(n)[None, :]
    rad = np.sqrt(fy**2+fx**2)
    hi = rad > 0.25            # 0.25 cyc/px = half of Nyquist (0.5)
    dc = (rad == 0)
    tot = F.sum(axis=(1, 2))-F[:, dc[0] if False else 0, 0]
    return (F*hi).sum(axis=(1, 2))/np.maximum(tot, 1e-12)

def coarse(t, ds=8):
    n = t.shape[0]; b = t.shape[1]//ds
    return sigma_std(t.reshape(n, b, ds, b, ds).mean(axis=(2, 4)).astype(np.float32))

if __name__ == "__main__":
    K = 10.0
    names, paths = [], []
    for a in sys.argv[1:]:
        n, p = a.split("=", 1); names.append(n); paths.append(p)
    G = [green(p) for p in paths]
    T = [tiles(g) for g in G]
    msig = np.mean([t.mean(axis=(1, 2)) for t in T], axis=0)
    sel = np.mean([coarse(t) for t in T], axis=0)

    # restrict to the BRIGHT BACKDROP: defocused in every frame of the bracket,
    # so there is no scene detail there for any merge to recover.
    m = (msig >= 16000) & (msig < 32000)
    idx = np.where(m)[0]
    keep = idx[sel[idx] <= np.percentile(sel[idx], K)]
    print(f"bright-backdrop tiles 16000-32000 DN, flattest {K:.0f}%: {keep.size} of {int(m.sum())}")
    print("(defocused in every frame -- no recoverable detail lives here)\n")

    rng = np.random.default_rng(7)
    white = np.asarray(rng.normal(0, 50.0, (keep.size, BOX, BOX)), dtype=np.float32)
    rows = [("synthetic white (ORCH's reference)", white)]
    for n, t in zip(names, T):
        rows.append((n, t[keep].astype(np.float32)))
    if len(T) >= 3:
        rows.append((f"{names[-1]} MINUS {names[-2]} (the change)",
                     (T[-1][keep].astype(np.float32)-T[-2][keep].astype(np.float32))))

    print(f"  {'signal':<40} {'sigma':>9} {'rho_lag1':>10} {'HF frac':>9} {'std/hf':>8}")
    for n, t in rows:
        s = float(np.median(sigma_std(t))); h = float(np.median(immerkaer(t)))
        print(f"  {n:<40} {s:9.3f} {float(np.median(rho_lag1(t))):10.4f} "
              f"{float(np.median(hf_fraction(t))):9.4f} {s/max(h,1e-9):8.3f}")
    print("\n  white noise gives rho ~ 0.00 and HF frac ~ 0.75 by construction.")
