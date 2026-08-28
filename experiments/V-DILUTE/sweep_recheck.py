"""V-DILUTE -- ORCH correction #4 re-check of the BAND-COUNT SWEEP.

The sweep conclusion ("acuity saturates at the shipping default, deeper is
worse") was read off band 1 (0.17-0.25).  Under correction #4 that band is not
universally signal.  bee's boundary is ~0.48 (bee-1-cpl, V-LINEAR 31eda43a), so
on bee the band that matters most is band 0 (0.25-0.50), which I had labelled
NOISE.  That is the dangerous direction ORCH named: it would license shipping a
softer image.

So re-read the sweep in EVERY band, null-normalised, and check whether the
conclusion depends on which band is chosen.
"""
import sys
import os
import glob
import re
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]
EDGES = [1.0 / (2.0 * np.pi * s) for s in SIGMAS]
S, N_SITES = 256, 12


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def octaves(x):
    out, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        out.append(prev - cur)
        prev = cur
    return out


def main(subj, ref_b=7):
    D = r"D:\strehl-out\V-DILUTE\bandsweep"
    paths = {}
    for p in glob.glob(os.path.join(D, f"{subj}.nb*.tiff")):
        m = re.search(r"\.nb(\d+)\.tiff$", p)
        if m:
            paths[int(m.group(1))] = p
    ref = lum(paths[ref_b])
    mid = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = ref.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    flat, edge = order[:N_SITES], order[-N_SITES:]
    med_ref = np.median(ref)
    rb = octaves(ref)

    def bs(idx, arr):
        v = []
        for f in idx:
            ty, tx = divmod(int(f), nx)
            v.append(arr[ty * S:ty * S + S, tx * S:tx * S + S].std())
        return float(np.mean(v))

    ref_e = [bs(edge, rb[j]) for j in range(len(SIGMAS))]

    print(f"SUBJECT {subj}   reference --pyramid-bands {ref_b}   "
          f"EDGE sites, null-normalised, ALL BANDS")
    hdr = (f"{'bands':>5s} | " +
           " ".join(f"{f'{(0.5 if j == 0 else EDGES[j-1]):.2f}':>8s}" for j in range(len(SIGMAS) - 1)) +
           f" | {'null':>7s}")
    print(hdr)
    print("-" * len(hdr))
    for b in sorted(paths):
        a = lum(paths[b])
        if a.shape != ref.shape:
            continue
        a = a * (med_ref / np.median(a))
        ba = octaves(a)
        null = bs(edge, ba[-1]) / ref_e[-1]
        vals = [bs(edge, ba[j]) / ref_e[j] / null for j in range(len(SIGMAS) - 1)]
        mark = "  <-- default" if b == ref_b else ""
        print(f"{b:5d} | " + " ".join(f"{v:8.4f}" for v in vals) +
              f" | {null:7.4f}{mark}")
    print()
    print("If the ordering of arms is the same in every column, the sweep")
    print("conclusion does not depend on which band a subject qualifies.")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 7)
