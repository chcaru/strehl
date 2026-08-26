"""Is the visible blob a gate contour?

A veil correction is a smooth function of distance from the silhouette, so the
difference image (on - off) should be smooth. A GATE contour is a step: pixels
on one side are corrected and pixels on the other are not, with nothing in
between beyond the blend band.

The test: compare the gradient magnitude of the difference image against the
gradient magnitude of the OFF image, both restricted to backdrop far from the
subject. On the backdrop the off image is nearly flat, so if the difference has
structure the correction put it there. Reported as a ratio so it cannot be read
as an absolute scale.
"""

import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_closing, binary_opening, distance_transform_edt


def luma(p: pathlib.Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def gradmag(a: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(a)
    return np.hypot(gy, gx)


out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\VEILZ2")
for stem in sys.argv[2:] or ["cb", "fb"]:
    off, on = luma(out / f"{stem}-off.tif"), luma(out / f"{stem}-on.tif")
    subj = off < 0.5 * float(np.median(off))
    subj = binary_opening(binary_closing(subj, np.ones((9, 9))), np.ones((9, 9)))
    far = (distance_transform_edt(~subj) >= 300) & ~subj

    d = on - off
    g_off, g_d = gradmag(off)[far], gradmag(d)[far]
    lo, hi = np.percentile(d[far], [1, 99])

    print(f"\n=== {stem}: backdrop at d >= 300 px, {far.sum():,} px ===")
    print(f"  correction applied here : mean {d[far].mean():+.0f} DN, p1..p99 {lo:+.0f}..{hi:+.0f}")
    print(f"  gradient of OFF backdrop: median {np.median(g_off):8.1f} DN/px")
    print(f"  gradient of DIFFERENCE  : median {np.median(g_d):8.1f} DN/px  p99 {np.percentile(g_d, 99):8.1f}")

    # A contour is a CURVE in a 2-D image, so it occupies a vanishing fraction
    # of the pixels and cannot move the median. Read the tail against the
    # backdrop's own typical gradient, and read it together with how much
    # correction is being applied out here at all: a large, spatially structured
    # correction at a distance where the veil has already decayed is the defect.
    step = float(np.percentile(g_d, 99) / max(np.median(g_off), 1e-6))
    print(f"  p99 step vs backdrop    : {step:8.2f}x")
    if hi < 400.0:
        print("  -> negligible correction this far out: confined to the rim, as intended.")
    elif step > 5.0:
        print("  -> LARGE correction far from the silhouette WITH a steep tail: this is a")
        print("     GATE CONTOUR, a visible hard-edged region, not a smooth veil removal.")
    else:
        print("  -> large but smooth correction far out: over-broad, but not a contour.")
