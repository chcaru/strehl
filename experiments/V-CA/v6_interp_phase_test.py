"""V-CA v6 -- statistical test of the interpolation-null control.

The blur hypothesis for the CA headline says: on-vs-off partly measures
interpolation, because OFF short-circuits and never resamples (fact 1517).

The shipped correction is a pure radial magnification, so resample displacement
is d(r) = |eps_r| * r px.  Catmull-Rom blur is a function of frac(d) ONLY:
maximum at frac = 0.5, EXACTLY ZERO at frac = 0 (integer shift = pure copy).

  BLUR HYPOTHESIS predicts: apparent chroma reduction is LARGEST at frac=0.5.
  CORRECTION HYPOTHESIS  predicts: no dependence on frac, or -- if interpolation
     degrades the correction -- reduction LARGEST at frac=0.

The CA effect also grows with radius, and d is monotone in radius, so the radial
trend must be removed before reading the oscillation.  Detrend fall% against a
cubic in d, then regress the residual on cos(2*pi*d), which is +1 at every
integer (no blur) and -1 at every half-integer (max blur).

  coefficient < 0  =>  blur hypothesis supported
  coefficient > 0  =>  blur hypothesis REFUTED; interpolation is a COST to the
                       correction, not the source of its apparent benefit

Significance by permutation on the residuals (the bins are not independent
enough for a t-test to be honest).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
EPS = 704.5e-6
RNG = np.random.default_rng(20260824)


def chroma(f):
    return np.abs(f[..., 0] - (0.2126*f[..., 0] + 0.7152*f[..., 1] + 0.0722*f[..., 2]))


def edge_mask(off):
    y = 0.2126*off[..., 0] + 0.7152*off[..., 1] + 0.0722*off[..., 2]
    gy = np.zeros_like(y); gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :])
    gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    g = gy + gx
    seed = g >= float(np.percentile(g[::7, ::7], 98.0))
    m = seed.copy()
    m[1:, :] |= seed[:-1, :]; m[:-1, :] |= seed[1:, :]
    m[:, 1:] |= seed[:, :-1]; m[:, :-1] |= seed[:, 1:]
    return m


def run(subject, off_name, on_name, label, nbin=48):
    off = tifffile.imread(str(ROOT / subject / off_name)).astype(np.float32)
    on = tifffile.imread(str(ROOT / subject / on_name)).astype(np.float32)
    h, w, _ = off.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = EPS * np.hypot(xx - (w-1)/2.0, yy - (h-1)/2.0)
    m = edge_mask(off)
    co, cn, dd = chroma(off)[m], chroma(on)[m], d[m]

    lo, hi = 0.60, dd.max()          # skip the near-centre zone where CA ~ 0
    edges = np.linspace(lo, hi, nbin + 1)
    mid, fall, wt = [], [], []
    for i in range(nbin):
        s = (dd >= edges[i]) & (dd < edges[i+1])
        n = int(s.sum())
        if n < 5000:
            continue
        a, b = float(co[s].mean()), float(cn[s].mean())
        mid.append((edges[i]+edges[i+1])/2.0); fall.append(100*(1-b/a)); wt.append(n)
    mid = np.array(mid); fall = np.array(fall); wt = np.array(wt, float)

    X = np.vstack([np.ones_like(mid), mid, mid**2, mid**3]).T
    W = np.diag(wt/wt.sum())
    beta = np.linalg.lstsq(W @ X, W @ fall, rcond=None)[0]
    resid = fall - X @ beta
    phase = np.cos(2*np.pi*mid)      # +1 at integer d (NO blur), -1 at half-integer

    c = float((resid*phase*wt).sum() / (phase*phase*wt).sum())
    null = np.array([float((RNG.permutation(resid)*phase*wt).sum()
                           / (phase*phase*wt).sum()) for _ in range(20000)])
    p = float((np.abs(null) >= abs(c)).mean())

    nb = np.abs(phase) > 0.75
    print(f"\n=== {subject}  {label} ===")
    print(f"  usable bins {len(mid)}   d range {mid.min():.2f}..{mid.max():.2f} px")
    print(f"  mean fall%  at frac(d)~0   (NO interpolation blur) : "
          f"{np.average(fall[nb & (phase>0)], weights=wt[nb & (phase>0)]):7.2f}%")
    print(f"  mean fall%  at frac(d)~0.5 (MAX interpolation blur): "
          f"{np.average(fall[nb & (phase<0)], weights=wt[nb & (phase<0)]):7.2f}%")
    print(f"  detrended cos(2*pi*d) coefficient = {c:+.3f} pp   permutation p = {p:.5f}")
    print("  blur hypothesis predicts a NEGATIVE coefficient. Observed sign: "
          f"{'POSITIVE -> REFUTED' if c > 0 else 'negative -> supported'}")


if __name__ == "__main__":
    run("bee-3-cpl", "lind-default.tif", "lind-ca.tif", "LINEAR + demosaic (measurement space)")
    run("bee-3-cpl", "default.tif", "ca.tif", "sRGB (the published space)")
