"""V-DILUTE Assignment 2 -- band-count sweep scorer.

Every row pairs an acuity number with a noise number on the same pixels
(rule 3), shows the instrument null, and prints the ABSOLUTE FLAT column so
that "energy falling with scale = noise, rising = structure" can be read
directly instead of assumed.

Band placement follows ORCH's contrast_ms.py exactly: a Gaussian of width sigma
cuts at 1/(2*pi*sigma) cyc/px.
"""
import sys
import os
import glob
import re
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]
S = 256
N_SITES = 12


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def rails(p):
    a = tifffile.imread(p)
    return (100.0 * np.mean(a >= 65535), 100.0 * np.mean(a <= 0), float(np.median(a)))


def octaves(x):
    out, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        out.append(prev - cur)
        prev = cur
    return out


def sites_from(ref):
    """Sites chosen on the REFERENCE only, so selection is common to all arms."""
    mid = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = ref.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    return nx, order[:N_SITES], order[-N_SITES:]


def band_std(idx, arr, nx):
    v = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        v.append(arr[ty * S:ty * S + S, tx * S:tx * S + S].std())
    return float(np.mean(v))


def main(subj, refbands=7):
    D = r"C:\dev\strehl-out\V-DILUTE\bandsweep"
    paths = {}
    for p in glob.glob(os.path.join(D, f"{subj}.nb*.tiff")):
        m = re.search(r"\.nb(\d+)\.tiff$", p)
        if m:
            paths[int(m.group(1))] = p
    if refbands not in paths:
        print(f"no reference arm nb{refbands}")
        return

    ref = lum(paths[refbands])
    nx, flat, edge = sites_from(ref)
    rb = octaves(ref)
    # reference tone
    med_ref = np.median(ref)

    ref_ac = band_std(edge, rb[1], nx)
    ref_no = band_std(flat, rb[0], nx)
    ref_nl = band_std(edge, rb[-1], nx)

    print(f"SUBJECT {subj}   reference = --pyramid-bands {refbands} (SHIPPING DEFAULT)")
    print(f"sites: {N_SITES} FLAT + {N_SITES} EDGE tiles of {S}px, chosen on the reference only")
    print()
    hdr = (f"{'bands':>5s} {'clip%':>7s} {'black%':>7s} {'median':>8s} | "
           f"{'ACUITY':>8s} {'NULL':>7s} {'ACUITY/NULL':>11s} {'NOISE':>8s} {'NOISE/NULL':>10s} | "
           f"{'absFLAT b0':>10s} {'absFLAT b1':>10s} {'absFLAT b3':>10s} {'absFLAT b5':>10s}")
    print(hdr)
    print("-" * len(hdr))
    for b in sorted(paths):
        a = lum(paths[b])
        if a.shape != ref.shape:
            print(f"{b:5d}   shape {a.shape} != ref {ref.shape} -- SKIP (geometry differs)")
            continue
        # remove tone placement the same way contrast_ms.py does
        a = a * (med_ref / np.median(a))
        ba = octaves(a)
        ac = band_std(edge, ba[1], nx) / ref_ac
        no = band_std(flat, ba[0], nx) / ref_no
        nl = band_std(edge, ba[-1], nx) / ref_nl
        cl, bl, md = rails(paths[b])
        mark = "  <-- default" if b == refbands else ""
        if abs(nl - 1.0) > 0.005 and b != refbands:
            mark += "  [NULL VOID]"
        print(f"{b:5d} {cl:7.3f} {bl:7.3f} {md:8.0f} | "
              f"{ac:8.4f} {nl:7.4f} {ac / nl:11.4f} {no:8.4f} {no / nl:10.4f} | "
              f"{band_std(flat, ba[0], nx):10.2f} {band_std(flat, ba[1], nx):10.2f} "
              f"{band_std(flat, ba[3], nx):10.2f} {band_std(flat, ba[5], nx):10.2f}{mark}")

    print()
    print("ACUITY = band-1 (0.17-0.25 cyc/px, QUALIFIED SIGNAL) EDGE std, ratio to default.")
    print("NOISE  = band-0 (0.25-0.50 cyc/px, qualified NOISE)  FLAT std, ratio to default.")
    print("NULL   = coarsest EDGE ratio; |NULL-1| > 0.005 means the arms differ globally,")
    print("         so ACUITY/NULL is the only defensible acuity column on those rows.")
    print("absFLAT: energy FALLING with coarser scale = noise; RISING = structure.")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 7)
