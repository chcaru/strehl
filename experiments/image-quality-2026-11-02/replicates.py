"""Texture kept versus noise removed, from pixel-aligned half-stack replicates.

usage: replicates.py A_even.tif A_odd.tif B_even.tif B_odd.tif [tile]

Each arm is rendered twice from disjoint frame halves (STREHL_FRAME_PARITY) under
the SAME warp map, so the two renders are pixel-aligned. In linear luma, after a
band-pass, a tile's
  texture power T = mean(e * o)              (cross-covariance: independent
                                              noise cancels, common scene stays)
  noise power   N = mean((e - o)^2) / 2      (one half-stack's noise variance)
Two bands: fine = x - box3(x), mid = box3(x) - box9(x). Tiles darker than
0.01 linear luma (black backgrounds) are reported separately as `dark`.

Per band, tiles are binned by arm A's texture SNR T_A/N_A and the median of
T_B/T_A and N_B/N_A is reported per bin. An arm that only removes noise shows
T_B/T_A ~ 1 in every bin with N_B/N_A < 1. Lost detail shows as T_B/T_A < 1 in
the bins where texture is real (SNR >= 1). T is noisy where SNR << 1, so the
lowest bin's T ratio is not interpretable; its N ratio is.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter


def luma(p):
    a = tifffile.imread(p).astype(np.float32) / 65535
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def bands(y):
    b3 = uniform_filter(y, 3)
    return {"fine": y - b3, "mid": b3 - uniform_filter(y, 9)}


def tiles(x, t):
    h, w = x.shape[0] // t * t, x.shape[1] // t * t
    return x[:h, :w].reshape(h // t, t, w // t, t).mean(axis=(1, 3))


def main():
    ae, ao, be, bo = (luma(p) for p in sys.argv[1:5])
    t = int(sys.argv[5]) if len(sys.argv) > 5 else 64
    mean = tiles(ae, t)
    lit = mean > 0.01
    dark = (mean > 0.0002) & (mean <= 0.01)
    for name in ("fine", "mid"):
        A = bands(ae)[name], bands(ao)[name]
        B = bands(be)[name], bands(bo)[name]
        TA, NA = tiles(A[0] * A[1], t), tiles((A[0] - A[1]) ** 2, t) / 2
        TB, NB = tiles(B[0] * B[1], t), tiles((B[0] - B[1]) ** 2, t) / 2
        snr = TA / np.maximum(NA, 1e-20)
        print(f"[{name}] total noise B/A {NB[lit].sum() / NA[lit].sum():.3f}  "
              f"total texture B/A {TB[lit].sum() / TA[lit].sum():.4f}")
        if dark.sum() >= 5:
            print(f"   dark tiles {dark.sum():5d}  noise B/A {np.median(NB[dark] / NA[dark]):.3f}  "
                  f"texture B/A {TB[dark].sum() / max(TA[dark].sum(), 1e-30):.4f}")
        edges = [-np.inf, 0.3, 1, 3, 10, 30, 100, np.inf]
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = lit & (snr >= lo) & (snr < hi)
            if m.sum() < 5:
                continue
            print(f"   SNR [{lo:>5},{hi:>5})  tiles {m.sum():5d}  texture B/A "
                  f"{np.median(TB[m] / np.maximum(TA[m], 1e-20)):.4f}  noise B/A "
                  f"{np.median(NB[m] / NA[m]):.3f}")


if __name__ == "__main__":
    main()
