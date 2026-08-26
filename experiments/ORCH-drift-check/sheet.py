"""Build a viewable A/B sheet: full frames plus 100% crops, one shared tone map.

Discipline: the tone window is computed once from the reference arm and applied
to every arm. An A/B where each side gets its own auto-levels is not an A/B.
Every panel is labelled with its arm, because an unlabelled comparison sheet is
a way to be wrong in public.
"""
import os
import sys
import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image, ImageDraw


def luma(a):
    a = a.astype(np.float64)
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return a


def tone(rgb, lo, hi):
    x = (rgb.astype(np.float64) - lo) / max(hi - lo, 1e-6)
    x = np.clip(x, 0.0, 1.0) ** (1.0 / 2.2)
    out = (x * 255.0 + 0.5).astype(np.uint8)
    if out.ndim == 2:
        out = np.stack([out] * 3, axis=-1)
    return out[:, :, :3]


def label(img, text):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    w = 9 * len(text) + 16
    d.rectangle([0, 0, w, 30], fill=(0, 0, 0))
    d.text((8, 9), text, fill=(255, 255, 0))
    return np.asarray(im)


def main():
    if len(sys.argv) < 5:
        print("usage: sheet.py <ref.tiff> <arm.tiff> <outdir> <name> "
              "[refname] [armname]")
        return 2
    ref_p, arm_p, outdir, name = sys.argv[1:5]
    refname = sys.argv[5] if len(sys.argv) > 5 else "A: estimator (shipped)"
    armname = sys.argv[6] if len(sys.argv) > 6 else "B: pyramid"
    os.makedirs(outdir, exist_ok=True)

    A = tifffile.imread(ref_p)
    B = tifffile.imread(arm_p)
    if A.shape != B.shape:
        print(f"shape mismatch {A.shape} vs {B.shape}")
        return 1

    ya = luma(A)
    lo = float(np.percentile(ya, 0.5))
    hi = float(np.percentile(ya, 99.7))
    print(f"{name}: shared tone window {lo:.0f}..{hi:.0f} DN from REF only")

    # ---- full frames, side by side, downsampled for viewing
    long_edge = 1600
    H, W = ya.shape
    s = long_edge / max(H, W)
    fh, fw = int(H * s), int(W * s)
    panels = []
    for tag, img in ((refname, A), (armname, B)):
        t = tone(img, lo, hi)
        p = np.asarray(Image.fromarray(t).resize((fw, fh), Image.LANCZOS))
        panels.append(label(p, tag))
    gap = np.full((fh, 16, 3), 32, np.uint8)
    Image.fromarray(np.hstack([panels[0], gap, panels[1]])).save(
        f"{outdir}\\{name}--full-AB.jpg", quality=92)

    # ---- 100% crops at the busiest silhouettes
    thr = float(np.quantile(ya, 0.35))
    subj = ndimage.binary_closing(
        ndimage.binary_opening(ya < thr, np.ones((5, 5))), np.ones((5, 5)))
    edge = (ndimage.binary_dilation(subj, np.ones((3, 3)))
            & ~ndimage.binary_erosion(subj, np.ones((3, 3))))
    g, size = 128, 640
    dens = edge[: (H // g) * g, : (W // g) * g].reshape(
        H // g, g, W // g, g).sum(axis=(1, 3))
    m = 3
    dens[:m, :] = 0; dens[-m:, :] = 0; dens[:, :m] = 0; dens[:, -m:] = 0

    order = np.argsort(dens.ravel())[::-1]
    picked = []
    for idx in order:
        gy, gx = divmod(int(idx), dens.shape[1])
        cy, cx = gy * g + g // 2, gx * g + g // 2
        if any(abs(cy - py) < size and abs(cx - px) < size for py, px in picked):
            continue
        picked.append((cy, cx))
        if len(picked) >= 2:
            break

    for i, (cy, cx) in enumerate(picked):
        y0 = max(0, min(H - size, cy - size // 2))
        x0 = max(0, min(W - size, cx - size // 2))
        cps = []
        for tag, img in ((refname, A), (armname, B)):
            cps.append(label(tone(img[y0:y0 + size, x0:x0 + size], lo, hi), tag))
        gap = np.full((size, 16, 3), 32, np.uint8)
        Image.fromarray(np.hstack([cps[0], gap, cps[1]])).save(
            f"{outdir}\\{name}--crop{i}-100pct-AB.jpg", quality=95)
        print(f"  crop{i} at y={y0} x={x0}, {size}px, 100%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
