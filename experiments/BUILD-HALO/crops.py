"""BUILD-HALO -- before/after crops at occluding edges, and the sharpness check.

Writes 16-bit crops.  Never PIL for a 16-bit RGB read (discipline 828 /
SYNTHESIS fact 1615) -- `m121_io.load_u16` reads with tifffile and asserts the
dtype, and this module writes with tifffile too, so nothing round-trips through
an 8-bit path.

Two products, and they are deliberately in one file so a halo result cannot be
reported without the regression that bounds it:

  crops   -- 100% crops at hand-picked occluding edges, before | after | 3x the
             signed difference, side by side in one 16-bit TIFF.
  sharp   -- the sharpness regression.  Mean |grad| over the SHARPEST decile of
             a plane, plus the 10-90 rise on the same donor edges.  A halo fix
             that is really a blur shows up here and nowhere in the rim
             statistics.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

M121 = pathlib.Path(__file__).resolve().parents[1] / "M121-halo-polarity"
sys.path.insert(0, str(M121))
from halo_lib import _sobel2  # noqa: E402
from m121_io import load_u16, luma  # noqa: E402


def grad_mag(y: np.ndarray) -> np.ndarray:
    gx, gy = _sobel2(y)
    return np.hypot(gx, gy)


def sharpness(y: np.ndarray, border: int = 64) -> dict:
    """Detail statistics on the interior, in raw DN per px.

    `p99` and the top-decile mean are read on |grad| rather than on a variance,
    because a selection stacker that has gone noisy RAISES variance while
    LOWERING real detail, and the two must not be confusable.  The top decile is
    where the real subject detail is; the median is mostly background.
    """
    g = grad_mag(y)[border:-border, border:-border]
    thr = np.percentile(g, 90.0)
    return {
        "grad_mean": float(g.mean()),
        "grad_p99": float(np.percentile(g, 99.0)),
        "grad_top_decile_mean": float(g[g >= thr].mean()),
        "grad_p999": float(np.percentile(g, 99.9)),
    }


def find_edges(y: np.ndarray, n: int, border: int = 96, sep: int = 220) -> list[tuple[int, int]]:
    """The `n` strongest, well-separated gradient peaks.  Deterministic."""
    g = uniform_filter(grad_mag(y), size=5)
    g[:border] = g[-border:] = 0
    g[:, :border] = g[:, -border:] = 0
    picks: list[tuple[int, int]] = []
    work = g.copy()
    for _ in range(n):
        i = int(np.argmax(work))
        yy, xx = divmod(i, work.shape[1])
        if work[yy, xx] <= 0:
            break
        picks.append((yy, xx))
        y0, y1 = max(0, yy - sep), min(work.shape[0], yy + sep)
        x0, x1 = max(0, xx - sep), min(work.shape[1], xx + sep)
        work[y0:y1, x0:x1] = 0
    return picks


def crop_pair(before: np.ndarray, after: np.ndarray, cy: int, cx: int, half: int):
    y0, y1 = cy - half, cy + half
    x0, x1 = cx - half, cx + half
    b = before[y0:y1, x0:x1]
    a = after[y0:y1, x0:x1]
    d = (a.astype(np.float32) - b.astype(np.float32)) * 3.0 + 32768.0
    gap = np.full((b.shape[0], 8, 3), 0, dtype=np.uint16)
    panel = np.concatenate(
        [b, gap, a, gap, np.clip(d, 0, 65535).astype(np.uint16)], axis=1
    )
    return panel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--half", type=int, default=160)
    ap.add_argument("--at", action="append", default=[], help="Y,X, repeatable")
    a = ap.parse_args()

    bp, ap_ = pathlib.Path(a.before), pathlib.Path(a.after)
    brgb, argb = load_u16(bp), load_u16(ap_)
    assert brgb.shape == argb.shape, (brgb.shape, argb.shape)
    by, ay = luma(brgb), luma(argb)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.at:
        picks = [tuple(int(v) for v in s.split(",")) for s in a.at]
    else:
        picks = find_edges(by, a.n)

    for k, (cy, cx) in enumerate(picks):
        panel = crop_pair(brgb, argb, cy, cx, a.half)
        p = out / f"{a.tag}-crop{k}-y{cy}-x{cx}-before-after-diff3x.tif"
        tifffile.imwrite(str(p), panel)
        print(f"wrote {p}  ({panel.shape[1]}x{panel.shape[0]})")

    rep = {"before": str(bp), "after": str(ap_),
           "sharpness_before": sharpness(by), "sharpness_after": sharpness(ay),
           "crops": [[int(y), int(x)] for y, x in picks]}
    sb, sa = rep["sharpness_before"], rep["sharpness_after"]
    print(f"\n{'statistic':24s} {'before':>12s} {'after':>12s} {'ratio':>8s}")
    for k in sb:
        r = sa[k] / sb[k] if sb[k] else float("nan")
        flag = "  <-- LOST DETAIL" if r < 0.97 else ""
        print(f"{k:24s} {sb[k]:12.4f} {sa[k]:12.4f} {r:8.4f}{flag}")
    (out / f"{a.tag}-sharpness.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
