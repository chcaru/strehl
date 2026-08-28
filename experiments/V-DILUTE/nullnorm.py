"""V-DILUTE Assignment 2 -- null-normalised acuity.

WHY THIS EXISTS.  contrast_ms.py removes the tone confound with a single median
scalar.  The base band's disagreement is a position-dependent BOWL, not a global
scalar, so a median rescale cannot remove it: what survives shows up as the SAME
multiplicative offset in every band, including the instrument null.

Reading band 1 raw would then credit a tone artifact as an acuity gain.  That is
the identical error class that carried my Experiment B in Assignment 1 (a 4%
geometry artifact).  So report band-1 EDGE DIVIDED BY the coarsest EDGE null.

  raw   = band1_EDGE_B / band1_EDGE_A          (what contrast_ms.py prints)
  null  = coarsest_EDGE_B / coarsest_EDGE_A    (global offset the arms share)
  ACUITY_CORRECTED = raw / null

Noise is reported on the same pixels on every row (rule 3).
"""
import sys
import os
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]
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


def analyse(pa, pb):
    a, b = lum(pa), lum(pb)
    if a.shape != b.shape:
        return None
    b = b * (np.median(a) / np.median(b))
    mid = gaussian_filter(a, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    flat, edge = order[:N_SITES], order[-N_SITES:]
    ba, bb = octaves(a), octaves(b)

    def bs(idx, arr):
        v = []
        for f in idx:
            ty, tx = divmod(int(f), nx)
            v.append(arr[ty * S:ty * S + S, tx * S:tx * S + S].std())
        return float(np.mean(v))

    raw = bs(edge, bb[1]) / bs(edge, ba[1])
    null = bs(edge, bb[-1]) / bs(edge, ba[-1])
    noise = bs(flat, bb[0]) / bs(flat, ba[0])
    noise_n = noise / null
    return dict(raw=raw, null=null, corr=raw / null, noise=noise, noise_c=noise_n)


SUBJECTS = [
    ("coffee-bubbles", 19),
    ("109MSDCF", 22),
    ("119MSDCF", 33),
    ("113MSDCF", 63),
    ("foam", 100),
    ("coffee-bean", 105),
    ("bee-3-cpl", 299),
]

if __name__ == "__main__":
    D = r"D:\strehl-out\V-DILUTE\baseband"
    rows = []
    for subj, n in SUBJECTS:
        for bnd in (7, 2):
            pa = os.path.join(D, f"{subj}.b{bnd}.mean.tiff")
            pb = os.path.join(D, f"{subj}.b{bnd}.weighted.tiff")
            if not (os.path.exists(pa) and os.path.exists(pb)):
                continue
            r = analyse(pa, pb)
            if r:
                rows.append((subj, n, bnd, r))

    hdr = (f"{'subject':<16s} {'N':>4s} {'bands':>5s} | {'raw acuity':>10s} "
           f"{'null':>8s} {'ACUITY CORR':>12s} | {'noise raw':>9s} {'noise corr':>10s}")
    print(hdr)
    print("-" * len(hdr))
    for subj, n, bnd, r in rows:
        role = "default" if bnd == 7 else "POTENCY"
        print(f"{subj:<16s} {n:4d} {bnd:5d} | {r['raw']:10.4f} {r['null']:8.4f} "
              f"{r['corr']:12.4f} | {r['noise']:9.4f} {r['noise_c']:10.4f}   ({role})")
    d7 = [r['corr'] for _, _, b, r in rows if b == 7]
    if d7:
        print()
        print(f"default-band arms: n={len(d7)}  mean ACUITY CORR = {np.mean(d7):.4f}  "
              f"min = {min(d7):.4f}  max = {max(d7):.4f}  spread = {max(d7) - min(d7):.4f}")
    print()
    print("ACUITY CORR = band-1 EDGE ratio divided by the coarsest-EDGE null.")
    print("A value of 1.0000 means base-band treatment changed no acuity at all.")
    print("Arms are --pyramid-base weighted (B) against mean (A), the shipping default.")
