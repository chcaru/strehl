"""Does the SHIPPED render carry the patchwork signature?

The M93 A/B compared `gate0` against `gate4`, and merge.rs:3027 calls `gate 0
selector` a **negative control**: DEFAULT_GATE is 4.0. So that A/B measured how
bad the negative control is, which the project already knew by construction.

This script asks the question that actually matters: run the same commissioned
detector over the background of a real render produced by the shipped path.

No single input frames exist at this geometry, so only the kurtosis half of the
patchwork test applies -- the invariant needs matched inputs. Kurtosis alone
cannot say "manufactured"; it can only say "piecewise-constant", which is the
signature under test.

Reads only. Writes PNGs to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

TARGETS = [
    ("shipped render, bee-3", r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"),
    ("M93 gate4 (shipped gate)", r"C:\dev\strehl-out\M93-out\armM4-gate4-binlin.tif"),
    ("M93 gate0 (NEGATIVE CONTROL)", r"C:\dev\strehl-out\M93-out\armM-gate0-binlin.tif"),
    ("M93 single input frame", r"C:\dev\strehl-out\M93-out\armF-f173.tif"),
]
S = 256
BAR = 10.0


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16 -- refusing to measure" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def excess_kurtosis(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    return (((f - mu) ** 4).mean() / v**2 - 3.0) if v > 0 else float("nan")


def commission(sd, rng):
    """Two nulls and a plant, at the sd of the data actually being measured."""
    n1 = excess_kurtosis(rng.normal(0, sd, (S, S)))
    yy, xx = np.mgrid[0:S, 0:S]
    n2 = excess_kurtosis(yy * (sd / 40.0) + xx * (sd / 60.0) + rng.normal(0, sd * 0.05, (S, S)))
    pts = rng.integers(0, S, (60, 2))
    lv = rng.normal(0, sd, 60)
    d2 = (yy[..., None] - pts[:, 0]) ** 2 + (xx[..., None] - pts[:, 1]) ** 2
    plant = lv[np.argmin(d2, axis=2)]
    p = excess_kurtosis(plant)
    ok = abs(n1) < 1.0 and abs(n2) < 1.0 and p > BAR
    print("  commissioning at sd=%.1f: null-iid %+.2f  null-ramp %+.2f  plant-voronoi %+.2f  -> %s"
          % (sd, n1, n2, p, "OK" if ok else "REFUSING TO REPORT"))
    return ok


rng = np.random.default_rng(20260824)
print("Laplacian excess kurtosis over the 12 most background-like interior windows.")
print("A piecewise-constant (patchwork) field reads high; smooth or noisy reads ~0.")
print("Bar = %.1f, set by a planted Voronoi mosaic at the same sd as the data.\n" % BAR)

rows = []
for label, path in TARGETS:
    if not os.path.exists(path):
        print("%-30s MISSING %s" % (label, path))
        continue
    L = lum(path)
    H, W = L.shape
    border = max(200, min(H, W) // 8)
    stride = max(128, min(H, W) // 16)
    cands = []
    for y in range(border, H - S - border, stride):
        for x in range(border, W - S - border, stride):
            w = L[y : y + S, x : x + S]
            cands.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
    if not cands:
        print("%-30s no windows (image too small)" % label)
        continue
    bright = float(np.percentile([c[0] for c in cands], 80))
    pool = sorted([c for c in cands if c[0] >= bright], key=lambda t: t[1])[:12]
    sd = float(np.median([p[1] for p in pool]))
    print("%s  (%dx%d, %d windows scanned)" % (label, W, H, len(cands)))
    if not commission(sd, rng):
        continue
    ks = [excess_kurtosis(L[y : y + S, x : x + S]) for _, _, x, y in pool]
    n_over = sum(1 for k in ks if k > BAR)
    rows.append((label, np.median(ks), max(ks), n_over, len(ks)))
    print("  kurtosis: median %7.2f   worst %7.2f   over bar: %d of %d\n"
          % (np.median(ks), max(ks), n_over, len(ks)))

print("=" * 74)
print("%-30s %10s %10s %12s" % ("arm", "median", "worst", "over bar"))
for label, med, worst, n, tot in rows:
    print("%-30s %10.2f %10.2f %8d / %d" % (label, med, worst, n, tot))
