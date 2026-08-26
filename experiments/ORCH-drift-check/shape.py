"""What SHAPE is the clamp, and which CHANNEL is it in?

I have made a claim I did not measure. From the fact that the exact-zero count
falls 2.9920% (binned) -> 1.4015% (demosaiced) I inferred the crushed population
must be a THIN RIM, because interpolation would eat a rim's boundary but not a
blob's interior. That is an inference from a ratio between two different renders,
which is exactly the class of reasoning this project keeps catching in others.

ORCH-gallery2/VERDICT.txt measured the opposite, on a different render: the
clamp is BLUE-CHANNEL (723,429 px, 2.192%) and in LARGE CONTIGUOUS REGIONS --
"the brightest neighbour of a zero pixel has a median of 0.0 DN" -- located on
the subject's shadowed crevices, not at the silhouette.

Both cannot be right about the same defect. This settles it on the files that the
gate actually scores, and it also fixes a fourth defect in accept2.py: `.any(axis=2)`
reports THAT a pixel is clipped and never WHICH channel, so a chroma-specific bug
and a luminance clamp produce the identical number.

Reports, per subject:
  1. per-channel zero counts and the joint pattern (which combinations co-occur)
  2. connected-component size distribution of the zero set  -> rim vs region
  3. the brightest-8-neighbour statistic used by the gallery -> interior vs edge
  4. distance from the zero set to the nearest strong luminance edge -> silhouette or not
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

try:
    from scipy import ndimage
except ImportError:
    print("scipy required")
    raise


def describe(name: str, R: np.ndarray, T: np.ndarray) -> None:
    n = T.shape[0] * T.shape[1]
    print(f"\n{'=' * 72}\n{name}   {T.shape[1]}x{T.shape[0]}\n{'=' * 72}")

    # ---- 1. which channel -------------------------------------------------
    z = [(T[:, :, c] == 0) for c in range(3)]
    print("per-channel exact zeros (percent of frame)")
    for c, lab in enumerate("RGB"):
        rz = 100.0 * (R[:, :, c] == 0).mean()
        print(f"  {lab}   ref {rz:8.4f}   test {100.0 * z[c].mean():8.4f}"
              f"   rise {100.0 * z[c].mean() - rz:+8.4f}")

    code = z[0].astype(np.uint8) | (z[1].astype(np.uint8) << 1) | (z[2].astype(np.uint8) << 2)
    print("\njoint pattern of the zero set (which channels together)")
    names = {0: "none", 1: "R", 2: "G", 3: "RG", 4: "B", 5: "RB", 6: "GB", 7: "RGB"}
    for v in range(1, 8):
        cnt = int((code == v).sum())
        if cnt:
            print(f"  {names[v]:>4}  {cnt:10d}  {100.0 * cnt / n:7.4f}%")

    any_z = code > 0
    if not any_z.any():
        print("\n  no clipped pixels -- this subject is a placebo")
        return

    # ---- 2. morphology ----------------------------------------------------
    lab, ncomp = ndimage.label(any_z)
    sizes = np.bincount(lab.ravel())[1:]
    order = np.sort(sizes)[::-1]
    print(f"\nconnected components of the zero set: {ncomp}")
    print(f"  total zero px {int(sizes.sum()):>10d}")
    print(f"  largest       {int(order[0]):>10d} px  ({100.0 * order[0] / sizes.sum():.1f}% of the zero set)")
    print(f"  top 10 sum    {int(order[:10].sum()):>10d} px  ({100.0 * order[:10].sum() / sizes.sum():.1f}%)")
    print(f"  median size   {float(np.median(sizes)):>10.1f} px")
    print(f"  singletons    {int((sizes == 1).sum()):>10d}")

    # A rim is thin: its area is small relative to its bounding box, and eroding
    # by one pixel destroys most of it. A region survives erosion.
    er = ndimage.binary_erosion(any_z, np.ones((3, 3), bool))
    surv = 100.0 * er.sum() / any_z.sum()
    print(f"\nerosion test (3x3): {surv:.1f}% of the zero set survives one erosion")
    print("  a 1-2 px rim is destroyed (survival near 0); a blob is barely touched")
    er2 = ndimage.binary_erosion(any_z, np.ones((5, 5), bool))
    print(f"  5x5: {100.0 * er2.sum() / any_z.sum():.1f}% survives")

    # ---- 3. the gallery's brightest-neighbour statistic --------------------
    g = T.max(axis=2).astype(np.float32)
    mx = ndimage.maximum_filter(g, size=3)
    nb = mx[any_z]
    print(f"\nbrightest 8-neighbour of a zero pixel (max over channels, DN)")
    for q in (50, 75, 90, 99):
        print(f"  p{q:<3d} {np.percentile(nb, q):10.1f}")
    print("  gallery reported median 0.0 -> interiors of large dead regions")

    # ---- 4. is it at the silhouette? --------------------------------------
    ref_l = R.astype(np.float32).mean(axis=2)
    small = ref_l[::4, ::4]
    gy, gx = np.gradient(small)
    gm = np.hypot(gx, gy)
    strong = gm > np.quantile(gm, 0.99)
    dist = ndimage.distance_transform_edt(~strong) * 4.0
    dz = dist[::4, ::4][any_z[::4, ::4][: dist.shape[0], : dist.shape[1]]] \
        if False else dist[any_z[::4, ::4]]
    print(f"\ndistance from a zero pixel to the nearest top-1% reference edge (px)")
    for q in (50, 75, 90):
        print(f"  p{q:<3d} {np.percentile(dz, q):10.1f}")
    alld = dist.ravel()
    print(f"  frame-wide p50 for comparison: {np.percentile(alld, 50):10.1f}")
    print("  clamp AT the silhouette => zero-set p50 much smaller than frame p50")


def main() -> int:
    d = Path(sys.argv[1])
    for subject in sys.argv[2:]:
        rp = d / f"{subject}--ctrl.tiff"
        tp = d / f"{subject}--blend.tiff"
        if not (rp.exists() and tp.exists()):
            print(f"missing pair for {subject}")
            continue
        R = tifffile.imread(rp)
        T = tifffile.imread(tp)
        assert R.dtype == np.uint16 and T.dtype == np.uint16
        assert R.shape == T.shape, f"{subject}: shape mismatch"
        describe(subject, R, T)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
