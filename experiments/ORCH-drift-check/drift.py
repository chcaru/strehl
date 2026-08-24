"""ORCH independent re-derivation of M86's breathing-drift claim.

M86 measured 232.7 px of inter-frame drift on bee-3-cpl and built alignment on
that basis.  Nobody has checked it.  This is a deliberately different method in
a different language: no strehl code is imported, the estimator is FFT
cross-correlation over a scale ladder rather than a tile solve, and it carries
its own null and its own plant.

Claim under test: frame 0 and the last frame of bee-3-cpl differ by a
similarity whose scale term displaces a corner pixel by ~230 px.
"""

import io
import json
import os
import sys

import numpy as np
import rawpy

STACK = r"D:\personal\macro\bee-3-cpl"
OUT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
DOWN = 4  # block-mean factor applied to the half-res green plane


def green_plane(path):
    """One CFA green sub-lattice, block-mean downsampled.  No demosaic."""
    with rawpy.imread(path) as r:
        # rawpy returns views into libraw's buffer, freed on __exit__.
        vis = np.array(r.raw_image_visible, dtype=np.float32, copy=True)
        col = np.array(r.raw_colors_visible[:2, :2], dtype=np.int32, copy=True)
        black = float(np.mean(r.black_level_per_channel))
    # locate a green site in the 2x2 CFA cell (green is colour index 1)
    ys, xs = np.where(col == 1)
    oy, ox = int(ys[0]), int(xs[0])
    g = vis[oy::2, ox::2] - black
    h = (g.shape[0] // DOWN) * DOWN
    w = (g.shape[1] // DOWN) * DOWN
    g = g[:h, :w].reshape(h // DOWN, DOWN, w // DOWN, DOWN).mean(axis=(1, 3))
    return g.astype(np.float32)


def prep(a):
    """Window and remove DC so correlation is driven by structure."""
    a = a - a.mean()
    hy = np.hanning(a.shape[0]).astype(np.float32)
    hx = np.hanning(a.shape[1]).astype(np.float32)
    return a * hy[:, None] * hx[None, :]


def resample_scale(img, s):
    """Bilinear resample of img about its centre by factor s (s>1 magnifies)."""
    h, w = img.shape
    cy, cx = (h - 1) * 0.5, (w - 1) * 0.5
    yy = (np.arange(h, dtype=np.float32) - cy) / s + cy
    xx = (np.arange(w, dtype=np.float32) - cx) / s + cx
    y0 = np.clip(np.floor(yy), 0, h - 2).astype(np.int32)
    x0 = np.clip(np.floor(xx), 0, w - 2).astype(np.int32)
    fy = (yy - y0)[:, None].astype(np.float32)
    fx = (xx - x0)[None, :].astype(np.float32)
    a = img[np.ix_(y0, x0)]
    b = img[np.ix_(y0, x0 + 1)]
    c = img[np.ix_(y0 + 1, x0)]
    d = img[np.ix_(y0 + 1, x0 + 1)]
    return (a * (1 - fy) * (1 - fx) + b * (1 - fy) * fx
            + c * fy * (1 - fx) + d * fy * fx)


def ncc_peak(a, b):
    """Peak of the normalised cross-correlation, over all translations."""
    fa = np.fft.rfft2(a)
    fb = np.fft.rfft2(b)
    x = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    denom = np.sqrt(float((a * a).sum()) * float((b * b).sum()))
    if denom <= 0:
        return -1.0
    return float(x.max()) / denom


def best_scale(a, b, lo, hi, n=41, refine=3):
    """Scale of b relative to a, by maximising the NCC peak over a ladder."""
    best, bestv = 1.0, -1.0
    for _ in range(refine):
        grid = np.linspace(lo, hi, n)
        vals = [ncc_peak(a, prep(resample_scale(b, 1.0 / s))) for s in grid]
        k = int(np.argmax(vals))
        best, bestv = float(grid[k]), float(vals[k])
        step = float(grid[1] - grid[0])
        lo, hi = best - step, best + step
        n = 21
    return best, bestv


def main():
    os.makedirs(OUT, exist_ok=True)
    names = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    print("frames: %d" % len(names))

    ref_raw = green_plane(os.path.join(STACK, names[0]))
    print("green plane (downsampled): %s" % (ref_raw.shape,))
    ref = prep(ref_raw)

    full_h = ref_raw.shape[0] * 2 * DOWN
    full_w = ref_raw.shape[1] * 2 * DOWN
    r_corner = 0.5 * float(np.hypot(full_w, full_h))
    print("full-res ~%dx%d, corner radius %.1f px" % (full_w, full_h, r_corner))

    rows = []

    # --- NULL: a frame against itself must return scale exactly 1.0 -------
    s, v = best_scale(ref, ref_raw, 0.96, 1.04)
    print("NULL   self-vs-self          scale %.6f  ncc %.4f" % (s, v))
    rows.append(dict(kind="null", k=0, scale=s, ncc=v))

    # --- PLANT: a known scale on the same wiring must be recovered --------
    # discipline 598: an exact-zero null is also what a disconnected probe
    # looks like, so the null above is worthless without this.
    for planted in (1.010, 0.985):
        s, v = best_scale(ref, resample_scale(ref_raw, planted), 0.96, 1.04)
        print("PLANT  s=%.4f -> recovered %.6f  (err %+.6f)  ncc %.4f"
              % (planted, s, s - planted, v))
        rows.append(dict(kind="plant", planted=planted, scale=s, ncc=v))

    sys.stdout.flush()

    # --- TREATMENT: the real ladder --------------------------------------
    ks = list(range(20, len(names), 20)) + [len(names) - 1]
    for k in ks:
        b = green_plane(os.path.join(STACK, names[k]))
        s, v = best_scale(ref, b, 0.94, 1.06)
        drift = abs(s - 1.0) * r_corner
        print("FRAME %3d  scale %.6f  ncc %.4f  corner drift %8.2f px"
              % (k, s, v, drift))
        rows.append(dict(kind="frame", k=k, scale=s, ncc=v, corner_px=drift))
        sys.stdout.flush()

    io.open(os.path.join(OUT, "drift.json"), "w", encoding="utf-8").write(
        json.dumps(dict(stack=STACK, down=DOWN, r_corner=r_corner, rows=rows),
                   indent=1))
    print("\nwrote %s" % os.path.join(OUT, "drift.json"))


if __name__ == "__main__":
    main()
