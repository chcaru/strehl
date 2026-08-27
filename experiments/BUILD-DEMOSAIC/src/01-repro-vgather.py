"""Reproduce V-GATHER's master-level chroma statistic on two freshly rendered
arms, using V-GATHER's own code, so that the number my ground-truth harness
contradicts is a number I have measured myself rather than one I have read.

Statistic D (chroma_real.py): rms of the 7x7-box high-pass of (R-B), pooled
over the flattest quantile of 128 px tiles, on --linear-srgb --demosaic
masters rendered with STREHL_FULLRES_GATHER=0 (plane) and =1 (fullres).
"""
from __future__ import annotations
import os, sys
import numpy as np, tifffile

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import boxblur, hp  # noqa: E402  -- V-GATHER's own definitions

OUT = r"C:\dev\strehl-out\BUILD-DEMOSAIC"
T = 128
QS = [0.02, 0.05, 0.10, 0.25, 0.50, 1.00]


def load(p):
    return tifffile.imread(p)[:, :, :3].astype(np.float64)


def planes(im):
    return (0.2126 * im[:, :, 0] + 0.7152 * im[:, :, 1] + 0.0722 * im[:, :, 2],
            im[:, :, 0] - im[:, :, 2])


def tiled(y, t=T):
    h = (y.shape[0] // t) * t
    w = (y.shape[1] // t) * t
    return y[:h, :w].reshape(h // t, t, w // t, t)


def measure(im0, im1, q):
    l0, c0 = planes(im0)
    l1, c1 = planes(im1)
    h = (min(l0.shape[0], l1.shape[0]) // T) * T
    w = (min(l0.shape[1], l1.shape[1]) // T) * T
    l0, c0, l1, c1 = l0[:h, :w], c0[:h, :w], l1[:h, :w], c1[:h, :w]
    st = tiled((l0 + l1) / 2).std(axis=(1, 3))
    sel = st <= np.quantile(st, q)
    out = []
    for y in (l0, l1, c0, c1):
        e = tiled(hp(y))
        v = (e ** 2).mean(axis=(1, 3))
        out.append(float(np.sqrt(v[sel].mean())))
    return out + [int(sel.sum()), float(np.quantile(st, q))]


def report(subj):
    p0 = os.path.join(OUT, f"{subj}-g0.tiff")
    p1 = os.path.join(OUT, f"{subj}-g1.tiff")
    i0, i1 = load(p0), load(p1)
    print(f"{subj}: g0 {i0.shape} {i0.dtype}  g1 {i1.shape}")
    print(f"  max |g1-g0| = {np.abs(i1 - i0).max():.3f} DN   "
          f"mean |g1-g0| = {np.abs(i1 - i0).mean():.4f} DN")
    print(f"  {'q':>6} {'nt':>6} | {'luma g0':>10} {'luma g1':>10} {'ratio':>8} "
          f"| {'chr g0':>10} {'chr g1':>10} {'ratio':>8}")
    for q in QS:
        L0, L1, C0, C1, nt, _ = measure(i0, i1, q)
        print(f"  {q:6.2f} {nt:6d} | {L0:10.4f} {L1:10.4f} {L1/L0:8.4f} "
              f"| {C0:10.4f} {C1:10.4f} {C1/C0:8.4f}")
    print(flush=True)


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["wt1"]):
        report(s)
