"""Cut matched 100% crops from two arms at a silhouette, tone-mapped identically.

The tone map is computed ONCE from the reference arm and applied to both, so a
visible difference is a difference in the pixels and not in two independent
auto-levels. That is the whole discipline here: an A/B where each side gets its
own normalisation can manufacture or hide any difference you like.
"""
import sys
import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image


def luma(a):
    a = a.astype(np.float64)
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return a


def tone(rgb, lo, hi):
    x = (rgb.astype(np.float64) - lo) / max(hi - lo, 1e-6)
    x = np.clip(x, 0.0, 1.0)
    x = x ** (1.0 / 2.2)
    return (x * 255.0 + 0.5).astype(np.uint8)


def main():
    if len(sys.argv) < 4:
        print("usage: crops.py <ref.tiff> <arm.tiff> <outdir> [n_crops] [size]")
        return 2
    ref_p, arm_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    ncrop = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    size = int(sys.argv[5]) if len(sys.argv) > 5 else 700

    import os
    os.makedirs(outdir, exist_ok=True)

    A = tifffile.imread(ref_p)
    B = tifffile.imread(arm_p)
    if A.shape != B.shape:
        print(f"shape mismatch {A.shape} vs {B.shape}")
        return 1

    y = luma(A)
    thr = float(np.quantile(y, 0.35))
    subj = y < thr
    subj = ndimage.binary_opening(subj, np.ones((5, 5)))
    subj = ndimage.binary_closing(subj, np.ones((5, 5)))
    # silhouette density on a coarse grid -> pick the busiest boundaries
    edge = ndimage.binary_dilation(subj, np.ones((3, 3))) & ~ndimage.binary_erosion(subj, np.ones((3, 3)))
    g = 128
    H, W = edge.shape
    dens = edge[: (H // g) * g, : (W // g) * g].reshape(H // g, g, W // g, g).sum(axis=(1, 3))
    # exclude the outer ring: frame-edge artifacts are a different question
    m = 3
    dens[:m, :] = 0; dens[-m:, :] = 0; dens[:, :m] = 0; dens[:, -m:] = 0

    lo = float(np.percentile(luma(A), 0.5))
    hi = float(np.percentile(luma(A), 99.7))
    print(f"tone window from REF only: {lo:.0f} .. {hi:.0f} DN (applied to both)")

    flat = dens.ravel()
    order = np.argsort(flat)[::-1]
    picked = []
    for idx in order:
        gy, gx = divmod(int(idx), dens.shape[1])
        cy, cx = gy * g + g // 2, gx * g + g // 2
        if any(abs(cy - py) < size and abs(cx - px) < size for py, px in picked):
            continue
        picked.append((cy, cx))
        if len(picked) >= ncrop:
            break

    for i, (cy, cx) in enumerate(picked):
        y0 = max(0, min(H - size, cy - size // 2))
        x0 = max(0, min(W - size, cx - size // 2))
        for tag, img in (("A-estimator", A), ("B-pyramid", B)):
            c = img[y0:y0 + size, x0:x0 + size]
            out = tone(c, lo, hi)
            if out.ndim == 2:
                out = np.stack([out] * 3, axis=-1)
            Image.fromarray(out[:, :, :3]).save(
                f"{outdir}\\crop{i}_y{y0}_x{x0}_{tag}.png")
        print(f"crop {i}: y={y0} x={x0} size={size}  edgepx={int(flat[order[i]])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
