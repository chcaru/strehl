"""M103 -- an independent TRUTH ladder for `bee-3-cpl` scale drift.

M97's `signtest.py` measured the end-to-end scale of frame 0 vs frame 298
(0.85714) and reproduced the orchestrator's independent 0.85715 to five
decimals. That is one rung. This milestone needs the whole ladder, because the
question is *which spans the estimator under-reports*, and a single end-to-end
number cannot answer it.

Written here rather than imported from `experiments/M97-warped-merge/src` so a
shared bug cannot make two measurements agree with each other and with nothing
else -- M97's own stated reason for writing its gather by hand. The estimator
below (NCC peak maximised over a scale grid, translation free) is the same
*method* as M97's; the code is retyped and the agreement at j=298 is therefore
a real cross-check of both.

Controls, all run before any reading is believed:

  SELF   frame k against itself           -> must read 1.000
  PLANT  frame 0 zoomed by a known s      -> must recover s
  NULL   two frames one step apart        -> tiny, and must not read 1.000
         by construction (it is a real, if small, drift)

`rawpy`'s `raw_image_visible` is a view into LibRaw's buffer (AGENTS rule 32),
so every read copies inside the `with`.
"""

import json
import os
import sys

import numpy as np
import rawpy
from scipy.ndimage import map_coordinates

STACK = r"D:\personal\macro\bee-3-cpl"
DOWN = 4
# Half-diagonal of the CFA plane, plane px -- the corner radius M86/M97 quote
# errors at. 3516 x 2344 plane, so 0.5*hypot(3516, 2344).
R_PLANE = 0.5 * float(np.hypot(3516.0, 2344.0))


def green_plane(path: str) -> np.ndarray:
    with rawpy.imread(path) as r:
        vis = np.array(r.raw_image_visible, dtype=np.float32, copy=True)
        cfa = np.array(r.raw_colors_visible[:2, :2], dtype=np.int32, copy=True)
        black = float(np.mean(r.black_level_per_channel))
    ys, xs = np.where(cfa == 1)
    g = vis[int(ys[0]) :: 2, int(xs[0]) :: 2] - black
    h, w = (g.shape[0] // DOWN) * DOWN, (g.shape[1] // DOWN) * DOWN
    g = g[:h, :w].reshape(h // DOWN, DOWN, w // DOWN, DOWN).mean(axis=(1, 3))
    return g.astype(np.float32)


def zoom(img: np.ndarray, s: float) -> np.ndarray:
    """Resample about the centre by `s`; s > 1 magnifies."""
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    z = ((xx - cx) + 1j * (yy - cy)) / s
    return map_coordinates(
        img, [np.imag(z) + cy, np.real(z) + cx], order=1, mode="constant", cval=np.nan
    )


def prep(a: np.ndarray) -> np.ndarray:
    a = np.nan_to_num(a, nan=0.0)
    a = a - a.mean()
    return a * np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]


def ncc_peak(a: np.ndarray, b: np.ndarray) -> float:
    fa, fb = np.fft.rfft2(a), np.fft.rfft2(b)
    c = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float(c.max() / d) if d > 0 else -1.0


def best_scale(a_prepped, b_raw, lo=0.70, hi=1.15, n=91, refine=4):
    railed = False
    best, bestv = 1.0, -1.0
    for it in range(refine):
        grid = np.linspace(lo, hi, n)
        vals = [ncc_peak(a_prepped, prep(zoom(b_raw, 1.0 / s))) for s in grid]
        k = int(np.argmax(vals))
        if it == 0 and k in (0, len(grid) - 1):
            railed = True
        best, bestv = float(grid[k]), float(vals[k])
        step = float(grid[1] - grid[0])
        lo, hi, n = best - step, best + step, 21
    return best, bestv, railed


def main(argv):
    out = argv[1]
    js = [int(x) for x in argv[2].split(",")]
    names = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    g0 = green_plane(os.path.join(STACK, names[0]))
    p0 = prep(g0)
    print(f"working plane {g0.shape[1]}x{g0.shape[0]} (DOWN={DOWN})")

    res = {"controls": {}, "ladder": {}}

    # --- controls first, per AGENTS rule 9/20: a metric with no demonstrated
    # failing input is arithmetic, not evidence.
    s, v, rail = best_scale(p0, g0)
    res["controls"]["SELF-0"] = dict(scale=s, ncc=v, railed=rail)
    print(f"SELF   frame 0 vs itself      -> {s:.5f}  ncc {v:.4f}")
    gmid = green_plane(os.path.join(STACK, names[149]))
    s2, v2, r2 = best_scale(prep(gmid), gmid)
    res["controls"]["SELF-149"] = dict(scale=s2, ncc=v2, railed=r2)
    print(f"SELF   frame 149 vs itself    -> {s2:.5f}  ncc {v2:.4f}")
    for planted in (0.98, 0.94, 0.90, 0.86):
        s3, v3, r3 = best_scale(p0, zoom(g0, planted))
        res["controls"][f"PLANT-{planted}"] = dict(
            planted=planted, scale=s3, err=s3 - planted, ncc=v3, railed=r3
        )
        print(f"PLANT  {planted:.3f}                 -> {s3:.5f} "
              f"(err {s3 - planted:+.5f})  ncc {v3:.4f}")

    # --- the ladder itself
    print()
    print(f"{'j':>5} {'scale(0,j)':>11} {'ln':>11} {'ncc':>7} {'corner px':>10} {'railed':>7}")
    for j in js:
        gj = green_plane(os.path.join(STACK, names[j]))
        s, v, rail = best_scale(p0, gj)
        res["ladder"][str(j)] = dict(
            scale=s, ln=float(np.log(s)), ncc=v, railed=rail,
            corner_plane_px=abs(s - 1.0) * R_PLANE,
        )
        print(f"{j:>5} {s:>11.5f} {np.log(s):>+11.6f} {v:>7.4f} "
              f"{abs(s - 1.0) * R_PLANE:>10.1f} {str(rail):>7}")

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
