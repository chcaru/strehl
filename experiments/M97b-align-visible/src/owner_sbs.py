"""Owner-facing side-by-side, cropped on MATCHED SCENE CONTENT.

The two renders do not share a field of view -- the gain-corrected one sits in
frame 0's field of view and shows the subject about 1.19x larger. Cropping both
at the same pixel coordinates would compare different parts of the marker, which
is the exact error that made my first radial metric read a meaningless 24.5x.

So: recover the magnification between the two by FFT/NCC, take a larger crop
from the magnified render covering the same scene, and resample it down to the
comparison size. That resampling is a handicap applied to the CORRECTED render
-- it can only make the corrected side look softer than it really is. If it
still looks better, the conclusion is conservative.
"""

import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def green(a: np.ndarray) -> np.ndarray:
    return (a[:, :, 1] if a.ndim == 3 else a).astype(np.float64)


def block(a: np.ndarray, f: int) -> np.ndarray:
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d == 0:
        return 0.0
    return float(np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape).max() / d)


def find_scale(a, b):
    from scipy.ndimage import map_coordinates
    A, B = block(a, 8), block(b, 8)
    h, w = B.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    best = (1.0, -1.0)
    lo, hi = 0.80, 1.40
    for _ in range(4):
        for s in np.linspace(lo, hi, 15):
            z = map_coordinates(B, [(yy - cy) / s + cy, (xx - cx) / s + cx],
                                order=1, mode="nearest")
            v = ncc(A, z)
            if v > best[1]:
                best = (float(s), v)
        d = (hi - lo) / 7.0
        lo, hi = max(0.80, best[0] - d), min(1.40, best[0] + d)
    return best


def refine(ca, Bg, by, bx, n, size, hb, wb):
    """Lock the B crop onto A's scene content by an integer-only local search.

    A single global similarity does not fully register these two renders --
    there is real residual, and the two arms elected different frames in
    places. Without this lock the outer crops showed visibly different scene
    content, which would have made any visual comparison meaningless.

    Two stages, and the first one matters: a single full-resolution NCC search
    was measured to LOSE the lock (self-control 0.9244, treatment 0.22-0.49,
    and it walked away from a centre crop that visually matched). On macro
    texture the full-resolution signal is dominated by the fine detail that
    genuinely differs between the two arms, so the coarse stage matches on
    structure instead. Integer only throughout: a sub-pixel shift would
    resample B a second time and blur the very quantity being judged.
    """
    from scipy.ndimage import zoom
    pad = n // 3
    y0, x0 = max(0, by - pad), max(0, bx - pad)
    y1, x1 = min(hb, by + n + pad), min(wb, bx + n + pad)
    f = size / n
    winr = zoom(Bg[y0:y1, x0:x1], f, order=1)
    hh, ww = winr.shape

    def score(arr, ref, dy, dx, k):
        c = arr[dy:dy + ref.shape[0], dx:dx + ref.shape[1]]
        if c.shape != ref.shape:
            return -2.0
        c = c - c.mean()
        d = np.sqrt((ref * ref).sum() * (c * c).sum())
        return float((ref * c).sum() / d) if d > 0 else -2.0

    K = 4
    aL = block(ca, K)
    aL = aL - aL.mean()
    best, bo = -2.0, (0, 0)
    for dy in range(0, hh - size + 1):
        for dx in range(0, ww - size + 1):
            if dy % K or dx % K:
                continue
            wL = block(winr[dy:dy + size, dx:dx + size], K)
            v = score(wL, aL, 0, 0, K)
            if v > best:
                best, bo = v, (dy, dx)

    a = ca - ca.mean()
    fine, fo = -2.0, bo
    for dy in range(max(0, bo[0] - K), min(hh - size, bo[0] + K) + 1):
        for dx in range(max(0, bo[1] - K), min(ww - size, bo[1] + K) + 1):
            v = score(winr, a, dy, dx, 1)
            if v > fine:
                fine, fo = v, (dy, dx)

    ny = int(round(y0 + fo[0] / f))
    nx = int(round(x0 + fo[1] / f))
    return (max(0, min(hb - n, ny)), max(0, min(wb - n, nx)), fine)


def main(argv):
    out, a_p, b_p = argv[1], argv[2], argv[3]
    A, B = tifffile.imread(a_p), tifffile.imread(b_p)
    s, v = find_scale(green(A), green(B))
    # s is the magnification that must be applied to B to match A, so B's
    # subject is 1/s the size of A's. Getting this backwards makes the crop
    # boxes wrong AND applies the resampling handicap to the wrong side.
    print(f"B must be magnified by {s:.4f} to match A, i.e. B's subject is "
          f"{1/s:.4f}x the size of A's (ncc {v:.4f})")

    size = 420
    ha, wa = A.shape[:2]
    hb, wb = B.shape[:2]
    panels = []
    for name, (fy, fx) in (("upper-left", (0.34, 0.30)),
                           ("centre", (0.50, 0.52)),
                           ("lower-right", (0.66, 0.72))):
        ay, ax = int(ha * fy), int(wa * fx)
        ca = A[ay:ay + size, ax:ax + size]
        # Same scene point in B, measured from each image's own centre.
        dy = ay + size / 2 - (ha - 1) / 2
        dx = ax + size / 2 - (wa - 1) / 2
        n = int(round(size / s))
        by = int((hb - 1) / 2 + dy / s - n / 2)
        bx = int((wb - 1) / 2 + dx / s - n / 2)
        by, bx = max(0, min(hb - n, by)), max(0, min(wb - n, bx))
        # Plant control: displace the starting guess by a known amount. The
        # lock must return the same answer it returns undisplaced, or its
        # search range is a fiction. A 1 px self-control does not test a
        # +/-158 px search.
        plant = os.environ.get("M97_PLANT")
        if plant:
            py, px = (int(t) for t in plant.split(","))
            by = max(0, min(hb - n, by + py))
            bx = max(0, min(wb - n, bx + px))
        by, bx, lock = refine(green(A)[ay:ay + size, ax:ax + size],
                              green(B), by, bx, n, size, hb, wb)
        cb = np.asarray(Image.fromarray((B[by:by + n, bx:bx + n] >> 8).astype(np.uint8))
                        .resize((size, size), Image.LANCZOS))
        ca8 = (ca >> 8).astype(np.uint8)
        strip = np.concatenate([ca8, cb], axis=1)
        im = Image.fromarray(strip)
        d = ImageDraw.Draw(im)
        d.text((6, 4), f"TODAY (shipped alignment)  [{name}]", fill=(255, 255, 0))
        d.text((size + 6, 4), "POSSIBLE (gain-corrected)", fill=(255, 255, 0))
        d.line([(size, 0), (size, size)], fill=(255, 255, 0), width=2)
        panels.append(np.asarray(im))
        print(f"  {name}: A({ay},{ax}) <-> B({by},{bx}) crop {n}px -> {size}px  lock ncc {lock:.4f}")
    Image.fromarray(np.concatenate(panels, axis=0)).save(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
