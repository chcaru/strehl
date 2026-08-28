"""V-DILUTE -- ORCH guard: raw band power counts noise as sharpness.

ORCH (V-NEVERWORSE broadcast): "One arm read +0.142 sharper raw and -0.134
softer once noise-corrected -- a sign flip. If your statistic can be inflated by
noise, correct it or say plainly it cannot be trusted."

My band-count sweep ACUITY column is a RAW band-1 EDGE std.  It is exactly the
shape ORCH warns about.  The claim at risk is my Assignment 2 section 4:
"deeper than the default is worse, -0.12% at N=22 and -1.38% at N=299".  At
bands=9/N=299 the raw acuity fell 1.38% and the noise fell 1.29% -- nearly
together, which is the signature of a noise change being read as an acuity
change.

NOISE-CORRECTED STATISTIC.  At a given band, EDGE-site variance is structure
plus noise; FLAT-site variance is noise alone (flat tiles are the 12 lowest
mid-scale-gradient tiles, chosen on the reference so the choice is common to
all arms).  So

    structure_amplitude = sqrt( max(edge_std^2 - flat_std^2, 0) )

and the reported ratio is that quantity for arm B over arm A, then divided by
the coarsest-EDGE null exactly as before.  If the raw and corrected columns
disagree in SIGN, the raw claim must be withdrawn.
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


def sites(ref):
    mid = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = ref.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    o = np.argsort(tg.ravel())
    return nx, o[:N_SITES], o[-N_SITES:]


def bstd(idx, arr, nx):
    v = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        v.append(arr[ty * S:ty * S + S, tx * S:tx * S + S].std())
    return float(np.mean(v))


def corrected(idx_e, idx_f, bands, nx, j):
    """sqrt(max(edge^2 - flat^2, 0)) -- structure with the noise floor removed."""
    e = bstd(idx_e, bands[j], nx)
    f = bstd(idx_f, bands[j], nx)
    return float(np.sqrt(max(e * e - f * f, 0.0)))


def run(subj, ref_b, band_j):
    D = r"D:\strehl-out\V-DILUTE\bandsweep"
    paths = {}
    for p in glob.glob(os.path.join(D, f"{subj}.nb*.tiff")):
        m = re.search(r"\.nb(\d+)\.tiff$", p)
        if m:
            paths[int(m.group(1))] = p
    ref = lum(paths[ref_b])
    nx, flat, edge = sites(ref)
    med = np.median(ref)
    rb = octaves(ref)
    r_raw = bstd(edge, rb[band_j], nx)
    r_cor = corrected(edge, flat, rb, nx, band_j)
    r_nul = bstd(edge, rb[-1], nx)
    r_noi = bstd(flat, rb[0], nx)

    lo = EDGES[band_j]
    hi = 0.5 if band_j == 0 else EDGES[band_j - 1]
    print(f"SUBJECT {subj}   band {band_j} = {lo:.3f}-{hi:.3f} cyc/px   "
          f"reference bands={ref_b}")
    hdr = (f"{'bands':>5s} | {'RAW acuity':>10s} {'CORRECTED':>10s} "
           f"{'noise':>8s} {'null':>7s} | {'raw dev':>8s} {'corr dev':>9s}  sign")
    print(hdr)
    print("-" * len(hdr))
    for b in sorted(paths):
        a = lum(paths[b])
        if a.shape != ref.shape:
            continue
        a = a * (med / np.median(a))
        ba = octaves(a)
        nul = bstd(edge, ba[-1], nx) / r_nul
        raw = bstd(edge, ba[band_j], nx) / r_raw / nul
        cor = corrected(edge, flat, ba, nx, band_j) / r_cor / nul
        noi = bstd(flat, ba[0], nx) / r_noi / nul
        dr, dc = raw - 1.0, cor - 1.0
        flip = ""
        if b != ref_b and abs(dr) > 1e-4 and abs(dc) > 1e-4 and np.sign(dr) != np.sign(dc):
            flip = "  <== SIGN FLIP"
        mark = "  <-- default" if b == ref_b else flip
        print(f"{b:5d} | {raw:10.4f} {cor:10.4f} {noi:8.4f} {nul:7.4f} | "
              f"{dr:+8.4f} {dc:+9.4f}{mark}")
    print()


if __name__ == "__main__":
    for subj, n in (("109MSDCF", 22), ("bee-3-cpl", 299)):
        for j in (1, 0):
            run(subj, 7, j)
