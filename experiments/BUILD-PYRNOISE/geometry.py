"""Measure the geometry the alignment applies, instead of trusting the banner.

The merge ALIGNS BY DEFAULT and its banner says the field of view was "scaled to
0.9870 ... then upsampled to keep the output dimensions". `argmax-baseline` does
not align at all, and neither does a single frame. So the aligned arms and the
unaligned arms are NOT at matched pixel sites, and a ROI transferred between
them without correction measures registration error rather than noise.

This fits the mapping empirically -- patch cross-correlation on a grid, then a
least-squares similarity (uniform scale + translation) -- and checks the fitted
scale against the number the banner printed. Two independent routes to the same
quantity; if they disagree the banner is not describing the pixels.

Written to be able to fail: if the true mapping were not a scale about the
centre, the residuals would not collapse and the printout says so.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter


def green(p):
    return tifffile.imread(str(p))[:, :, 1].astype(np.float64)


def hp(a, w=9):
    return a - uniform_filter(a, size=w, mode="reflect")


def shift_of(ref, mov, cy, cx, half=96, search=24):
    """Integer-pixel displacement of `mov` relative to `ref` at (cy, cx),
    by normalised cross-correlation over a +/-`search` window."""
    r = hp(ref[cy - half:cy + half, cx - half:cx + half])
    r = r - r.mean()
    rn = np.sqrt((r * r).sum())
    if rn == 0:
        return None
    best, bdy, bdx = -2.0, 0, 0
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            m = mov[cy + dy - half:cy + dy + half, cx + dx - half:cx + dx + half]
            if m.shape != r.shape:
                continue
            m = hp(m)
            m = m - m.mean()
            mn = np.sqrt((m * m).sum())
            if mn == 0:
                continue
            c = float((r * m).sum() / (rn * mn))
            if c > best:
                best, bdy, bdx = c, dy, dx
    return bdy, bdx, best


def fit(ref_path, mov_path, label):
    ref, mov = green(ref_path), green(mov_path)
    H, W = ref.shape
    cy0, cx0 = (H - 1) / 2.0, (W - 1) / 2.0
    ys = np.linspace(0.18, 0.82, 5) * H
    xs = np.linspace(0.18, 0.82, 5) * W
    P, D, C = [], [], []
    for y in ys:
        for x in xs:
            r = shift_of(ref, mov, int(y), int(x))
            if r is None:
                continue
            dy, dx, c = r
            if c < 0.30:
                continue
            P.append((y - cy0, x - cx0))
            D.append((dy, dx))
            C.append(c)
    P, D, C = np.array(P), np.array(D), np.array(C)
    if len(P) < 6:
        print(f"{label}: only {len(P)} usable patches -- NO FIT")
        return None
    # d = (s-1)*p + t, one uniform scale, separate translations
    A = np.zeros((2 * len(P), 3))
    b = np.zeros(2 * len(P))
    A[0::2, 0] = P[:, 0]; A[0::2, 1] = 1.0
    A[1::2, 0] = P[:, 1]; A[1::2, 2] = 1.0
    b[0::2] = D[:, 0]; b[1::2] = D[:, 1]
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    k, ty, tx = sol
    resid = b - A @ sol
    print(f"{label}")
    print(f"  patches used     : {len(P)}  (mean NCC {C.mean():.3f}, min {C.min():.3f})")
    print(f"  fitted scale     : {1.0 + k:.6f}   (magnification of mov w.r.t. ref)")
    print(f"  fitted translate : dy {ty:+.2f} px, dx {tx:+.2f} px")
    print(f"  residual rms     : {np.sqrt((resid ** 2).mean()):.3f} px   max |resid| {np.abs(resid).max():.2f} px")
    print(f"  raw displacement : |d| min {np.abs(D).min():.1f}  max {np.abs(D).max():.1f} px")
    return 1.0 + k, ty, tx, cy0, cx0


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\BUILD-PYRNOISE\renders\109MSDCF"
    print(f"=== {d} ===\n")
    # 1. Does STREHL_ALIGN=0 really put the merge on the raw grid? Compare it
    #    with argmax-baseline, which is documented not to align.
    fit(d + r"\argmax.tif", d + r"\pyr_default_noalign.tif",
        "argmax (unaligned)  ->  pyr_default_noalign : expect scale 1.000000")
    print()
    # 2. What does the alignment actually do to the pixels?
    r = fit(d + r"\pyr_default_noalign.tif", d + r"\pyr_default.tif",
            "pyr_default_noalign  ->  pyr_default (aligned)")
    print()
    if r:
        s = r[0]
        print(f"  banner said the field of view was scaled to 0.9870, i.e. the")
        print(f"  output is magnified by 1/0.9870 = {1/0.9870:.6f}.")
        print(f"  fitted magnification = {s:.6f}   ratio to banner = {s/(1/0.9870):.4f}")
