"""V-CA v5 -- the two things the CA headline still lacks.

(A) RE-MEASURE 61.0 % IN THE MEASUREMENT SPACE.  Fact 1665 / new discipline 65
    ("never diagnose a mechanism on a viewing render").  Every published CA
    number is from a --srgb render, which applies the camera colour matrix AND
    the sRGB transfer curve.  `lind-*.tif` is linear + demosaic at full
    resolution -- same geometry, matrix and gamma removed.  Same statistic,
    clean space.

(B) THE INTERPOLATION-NULL CONTROL -- a within-arm substitute for the missing
    `anti` arm.  The shipped correction is a pure radial magnification (the
    _RADIAL variant zeroes translation), so the resample displacement is
      d(r) = |eps_r| * r  pixels,  eps_r = -704.5e-6.
    Catmull-Rom interpolation blur depends on frac(d): it is MAXIMUM at
    frac(d)=0.5 and EXACTLY ZERO at frac(d)=0, where the gather is an integer
    pixel shift and no interpolation happens at all.

    So an interpolation-driven "improvement" MUST oscillate with radius, with
    nulls at d = 1, 2 px and peaks at d = 0.5, 1.5, 2.5 px.  A correction-driven
    improvement must not.  This is a control the corpus does not have, and
    unlike the anti arm it needs no source change -- the signal is already in
    the render on disk.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
EPS = 704.5e-6


def chroma(f):
    return np.abs(f[..., 0] - (0.2126*f[..., 0] + 0.7152*f[..., 1] + 0.0722*f[..., 2]))


def edge_bands(off):
    y = 0.2126*off[..., 0] + 0.7152*off[..., 1] + 0.0722*off[..., 2]
    gy = np.zeros_like(y); gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :])
    gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    g = gy + gx
    thr = float(np.percentile(g[::7, ::7], 98.0))
    seed = g >= thr
    # distance-from-edge bands by iterated dilation (4-neighbour), bands 0..10
    band = np.full(seed.shape, 255, np.uint8)
    cur = seed.copy(); band[cur] = 0
    for k in range(1, 11):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]; nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]; nxt[:, :-1] |= cur[:, 1:]
        new = nxt & ~cur
        band[new] = k
        cur = nxt
    return band


def part_a(subject, off_name, on_name, label):
    off = tifffile.imread(str(ROOT / subject / off_name)).astype(np.float32)
    on = tifffile.imread(str(ROOT / subject / on_name)).astype(np.float32)
    print(f"\n--- (A) {subject}  {label}  [{off_name} vs {on_name}]  shape={off.shape}")
    band = edge_bands(off)
    co, cn = chroma(off), chroma(on)
    prof = []
    for k in range(11):
        m = band == k
        prof.append((int(m.sum()), float(co[m].mean()), float(cn[m].mean())))
    print(f"    whole frame mean|R-Y|  {co.mean():9.2f} -> {cn.mean():9.2f}"
          f"   {100*(cn.mean()/co.mean()-1):+7.2f}%")
    print(f"    band 0 raw             {prof[0][1]:9.2f} -> {prof[0][2]:9.2f}"
          f"   {100*(prof[0][2]/prof[0][1]-1):+7.2f}%")
    for K in (3, 5, 7):
        eo = prof[0][1] - prof[K][1]; en = prof[0][2] - prof[K][2]
        print(f"    edge-localised EXCESS, baseline band K={K}: "
              f"{eo:8.2f} -> {en:8.2f}   FALL {100*(1-en/eo):6.2f}%")
    # per-plane footprint, the fact-1663 claim
    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        d = np.abs(on[..., ci] - off[..., ci])
        print(f"    plane {nm}: changed {100*float((d>0).mean()):6.2f}% of px   "
              f">4 display lv on {100*float((d>4*257).mean()):5.2f}%   max {d.max():8.0f} DN")


def part_b(subject, off_name, on_name, label):
    off = tifffile.imread(str(ROOT / subject / off_name)).astype(np.float32)
    on = tifffile.imread(str(ROOT / subject / on_name)).astype(np.float32)
    h, w, _ = off.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0)
    d = EPS * r                      # resample displacement, pixels
    band = edge_bands(off)
    edge = band <= 1                 # fringe sites only: where the effect lives
    co, cn = chroma(off), chroma(on)
    print(f"\n--- (B) {subject}  {label}  interpolation-null control")
    print(f"    displacement d(r) spans {d.min():.3f} .. {d.max():.3f} px")
    print(f"    {'d range':>14} {'frac(d)':>9} {'n':>10} {'off':>9} {'on':>9} {'fall%':>8}  expect")
    step = 0.125
    edges = np.arange(0.0, d.max() + step, step)
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        m = edge & (d >= lo) & (d < hi)
        n = int(m.sum())
        if n < 20000:
            continue
        fc = (lo + hi) / 2.0 % 1.0
        a, b = float(co[m].mean()), float(cn[m].mean())
        near0 = min(fc, 1 - fc) < 0.13
        near5 = abs(fc - 0.5) < 0.13
        tag = "NULL (no blur)" if near0 else ("PEAK (max blur)" if near5 else "")
        print(f"    {lo:6.3f}-{hi:5.3f} {fc:9.3f} {n:10d} {a:9.1f} {b:9.1f}"
              f" {100*(1-b/a):7.2f}%  {tag}")


if __name__ == "__main__":
    s = "bee-3-cpl"
    part_a(s, "default.tif", "ca.tif", "sRGB (what every published number used)")
    part_a(s, "lind-default.tif", "lind-ca.tif", "LINEAR + demosaic (measurement space)")
    part_b(s, "default.tif", "ca.tif", "sRGB")
    part_b(s, "lind-default.tif", "lind-ca.tif", "LINEAR")
