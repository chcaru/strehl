"""V-M116 probe 7: spatial dispersion of the headline effect.

A single scalar over 1.65 million pixels has no error bar. This splits the plane
into 64x64 tiles, keeps the tiles that are >=50% inside each mask, and reports
the per-tile dD distribution -- so the effect size can be judged against a
spread rather than against nothing.
"""
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
T = 64


def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a[:, :, 1].astype(np.float64)


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def tile_sd(h, m, ny, nx):
    """per-tile sd of h over the pixels of mask m; NaN where <50% covered."""
    out = np.full((ny, nx), np.nan)
    for i in range(ny):
        for j in range(nx):
            sub = m[i*T:(i+1)*T, j*T:(j+1)*T]
            if sub.mean() < 0.5:
                continue
            v = h[i*T:(i+1)*T, j*T:(j+1)*T][sub]
            if v.size >= 64:
                out[i, j] = v.std()
    return out


for s in SUBJECTS:
    st = structure(load_green(M / f"{s}__M0u.tif"))
    mflat = st <= np.quantile(st, 0.20)
    mdet = st >= np.quantile(st, 0.80)
    g0, g1 = load_green(M / f"{s}__B0.tif"), load_green(M / f"{s}__B1u.tif")
    h0, h1 = g0 - box(g0, 5), g1 - box(g1, 5)
    ny, nx = g0.shape[0] // T, g0.shape[1] // T
    print(f"\n=== {s} ===  ({ny}x{nx} tiles of {T}x{T} plane px)")
    for name, m in (("DETAIL", mdet), ("FLAT", mflat)):
        a = tile_sd(h0, m, ny, nx)
        b = tile_sd(h1, m, ny, nx)
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        d = np.log10(b[ok]) - np.log10(a[ok])
        q = np.percentile(d, [5, 25, 50, 75, 95])
        print(f"  {name:6s} n={ok.sum():5d} tiles   "
              f"mean {d.mean():+.4f}  sd {d.std():.4f}   "
              f"p5 {q[0]:+.4f} p25 {q[1]:+.4f} med {q[2]:+.4f} p75 {q[3]:+.4f} p95 {q[4]:+.4f}   "
              f"merge wins {100.0*(d>0).mean():5.1f}% of tiles")
