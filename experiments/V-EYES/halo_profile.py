"""Was the halo the owner saw in the file, or made by the 5x downscale?

The owner's complaint was a bright rim following the subject silhouette -- the
"cut-out sticker" look. The gallery he judged had been resampled to 1400 px,
19.9% of master width. Lanczos and bicubic kernels have negative lobes, so they
overshoot at a step edge by construction: reducing 5x with such a kernel PUTS a
bright rim on a dark-to-light boundary that has none in the source. That makes
"halo" and "downscaled" confounded in the only evidence anyone has judged, and
separating them decides whether an implementer should touch the merge at all.

So the same edges are measured twice: in the full-resolution master, and in a
5x Lanczos reduction of it. If the rim appears only in the reduction, the defect
was in the delivery and the merge is exonerated on this point.

Overshoot is measured on edge-normal profiles. For each strong edge point the
profile is sampled along the luma gradient; the bright plateau is taken as the
median of samples 12-20 px on the bright side, and the overshoot is the maximum
in the 1-6 px band minus that plateau, in DN. A real halo is a positive
excursion adjacent to the edge that decays back to the plateau. Reported as the
mean over all sampled edges and as the 95th percentile, because a halo on a
minority of edges is still a halo.

Commissioning, per AGENTS.md, three arms on the identical tile so that a blind
metric and a perverse one are both caught:
  CLEAN    the master tile as delivered.
  DEFECT   the same tile with an unsharp mask, which is literally an edge
           overshoot generator. Must read HIGHER than clean.
  IMPROVE  the same tile Gaussian-blurred, which cannot have overshoot.
           Must read LOWER than clean.

Usage: python halo_profile.py <outdir> <fulljpeg> [more...]
"""

import sys
import pathlib
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(
        np.float32
    )


def overshoot(lum, n_edges=400, rng=None):
    """Mean and p95 overshoot in DN on the bright side of strong edges."""
    rng = rng or np.random.default_rng(7)
    b = cv2.GaussianBlur(lum, (0, 0), 1.0)
    gx = cv2.Sobel(b, cv2.CV_32F, 1, 0, 3)
    gy = cv2.Sobel(b, cv2.CV_32F, 0, 1, 3)
    gm = np.sqrt(gx * gx + gy * gy)
    thr = np.percentile(gm, 99.0)
    ys, xs = np.nonzero(gm > thr)
    keep = (xs > 30) & (xs < lum.shape[1] - 30) & (ys > 30) & (ys < lum.shape[0] - 30)
    ys, xs = ys[keep], xs[keep]
    if ys.size == 0:
        return float("nan"), float("nan"), 0
    idx = rng.choice(ys.size, size=min(n_edges, ys.size), replace=False)
    outs = []
    for i in idx:
        y, x = int(ys[i]), int(xs[i])
        n = np.array([gx[y, x], gy[y, x]], np.float32)
        nn = np.linalg.norm(n)
        if nn < 1e-6:
            continue
        n /= nn  # points toward increasing luma == the bright side
        prof = []
        for t in range(0, 22):
            px, py = x + n[0] * t, y + n[1] * t
            ix, iy = int(round(px)), int(round(py))
            if ix < 0 or iy < 0 or ix >= lum.shape[1] or iy >= lum.shape[0]:
                prof = []
                break
            prof.append(lum[iy, ix])
        if len(prof) < 21:
            continue
        prof = np.array(prof)
        plateau = float(np.median(prof[12:21]))
        near = float(prof[1:7].max())
        if plateau - prof[0] < 25:  # not actually a strong step
            continue
        outs.append(near - plateau)
    if not outs:
        return float("nan"), float("nan"), 0
    o = np.array(outs)
    return float(o.mean()), float(np.percentile(o, 95)), len(o)


def main():
    outdir = pathlib.Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    files = sys.argv[2:]

    a = np.asarray(Image.open(files[0]).convert("RGB"))
    L = luma(a)
    t = L[1500:3500, 2500:4500]
    print(f"COMMISSIONING on {pathlib.Path(files[0]).name} tile (2500,1500) 2000x2000")
    c_m, c_p, c_n = overshoot(t)
    d = cv2.GaussianBlur(t, (0, 0), 1.5)
    d_m, d_p, _ = overshoot(np.clip(t + 1.2 * (t - d), 0, 255))
    i_m, i_p, _ = overshoot(cv2.GaussianBlur(t, (0, 0), 1.5))
    print(f"  CLEAN   mean overshoot {c_m:+7.2f} DN  p95 {c_p:+7.2f}  ({c_n} edges)")
    print(f"  DEFECT  unsharp        {d_m:+7.2f} DN  p95 {d_p:+7.2f}   "
          f"{'PASS' if d_m > c_m else 'FAIL'} (must exceed clean)")
    print(f"  IMPROVE blur           {i_m:+7.2f} DN  p95 {i_p:+7.2f}   "
          f"{'PASS' if i_m < c_m else 'FAIL'} (must fall below clean)")
    print()

    print(f"{'subject':<40} {'full mean':>10} {'full p95':>9} {'5x mean':>9} {'5x p95':>8} {'verdict':>10}")
    print("-" * 92)
    for f in files:
        p = pathlib.Path(f)
        a = np.asarray(Image.open(p).convert("RGB"))
        L = luma(a)
        fm, fp, _ = overshoot(L, 600)
        small = cv2.resize(
            L, (L.shape[1] // 5, L.shape[0] // 5), interpolation=cv2.INTER_LANCZOS4
        )
        sm, sp, _ = overshoot(small, 600)
        verdict = "DELIVERY" if (sm - fm) > 1.0 else "same"
        print(f"{p.stem:<40} {fm:>10.2f} {fp:>9.2f} {sm:>9.2f} {sp:>8.2f} {verdict:>10}")

        if p.stem in ("bee-1-cpl", "dry-erase-marker-head-cpl"):
            u8 = np.clip(small, 0, 255).astype(np.uint8)
            Image.fromarray(u8[150:550, 150:550]).save(outdir / f"{p.stem}-5xLANCZOS.png")


if __name__ == "__main__":
    main()
