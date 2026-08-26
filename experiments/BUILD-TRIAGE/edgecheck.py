"""Decisive picture-anchored check: is the merge or the frame actually sharper?
Uses 1-D edge profiles and a noise-robust edge-slope statistic, on the SAME
matched tiles the band metric used."""
import numpy as np, tri, os
from scipy import ndimage

for lab in ("DETAIL", "SOURCE-BEST"):
    f = os.path.join(tri.OUT, "tiles", f"119MSDCF.{lab}.npz")
    if not os.path.exists(f): continue
    z = np.load(f); A, B = z["merge"], z["frame"]
    print(f"\n=== 119MSDCF {lab} ===  merge mean {A.mean():.1f} DN, frame mean {B.mean():.1f} DN")
    # Noise floor per arm, measured as the sd of a flat sub-patch difference
    # from its own median-filtered self (structure removed, noise retained).
    for nm, T in (("merge", A), ("frame", B)):
        med = ndimage.median_filter(T, 3)
        print(f"  {nm}: pixel noise sd = {(T-med).std():.2f} DN")
    # Edge slope: median-filter to kill noise, then look at the strongest
    # gradients.  A blur reduces these; noise does not survive the filter.
    for nm, T in (("merge", A), ("frame", B)):
        m = ndimage.median_filter(T, 3).astype(np.float64)
        gy, gx = np.gradient(m)
        g = np.hypot(gy, gx)
        top = np.percentile(g, 99.5)
        print(f"  {nm}: p99.5 edge slope = {top:8.2f} DN/px   "
              f"p99={np.percentile(g,99):8.2f}   p95={np.percentile(g,95):7.2f}")
    # Laplacian energy on the denoised image -- another blur-sensitive,
    # noise-insensitive statistic.
    for nm, T in (("merge", A), ("frame", B)):
        m = ndimage.median_filter(T, 3).astype(np.float64)
        L = ndimage.laplace(m)
        print(f"  {nm}: |laplacian| p99.5 = {np.percentile(np.abs(L),99.5):8.2f} DN")
