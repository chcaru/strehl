"""Magenta fraction of a 16-bit render, and the green deficit behind it.

The predicate is ORCH's, from `experiments/ORCH-drift-check/marker_wholeframe.py`,
adopted verbatim so the before-number is comparable to the 2.002 % already in the
corpus: on the render scaled to 0..1, a pixel is magenta when

    (R - G > 0.06) and (B - G > 0.06)

No ROI. Discipline 713: let the predicate find the region.

`f_m` alone is a thresholded statistic and could be moved by a change that merely
nudges pixels to 0.0599, so `d_g = max(R - G)` is reported beside it, and so is
the 99th percentile of green -- the guard registered in PREREGISTRATION.md
against "clearing" magenta by darkening the render.

Usage: python magenta.py <tif> [<tif> ...]
"""

import sys

import numpy as np
import tifffile

THRESH = 0.06


def magenta_mask(f: np.ndarray) -> np.ndarray:
    """ORCH's predicate on a float HxWx3 render scaled to 0..1.

    Exposed so other M109 scripts import it rather than re-typing the
    thresholds (discipline 742): a second copy is a second chance to drift.
    """
    return ((f[..., 0] - f[..., 1]) > THRESH) & ((f[..., 2] - f[..., 1]) > THRESH)


def load(path: str) -> np.ndarray:
    """Read a 16-bit RGB render as float32 in 0..1, with the shape/dtype guards."""
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit(f"{path}: expected HxWx3, got {a.shape}")
    if a.dtype != np.uint16:
        raise SystemExit(f"{path}: expected uint16, got {a.dtype}")
    # float32 is exact for every uint16 value, and halves peak memory on a
    # 33 MP frame against float64.
    return a.astype(np.float32) / 65535.0


def stats(path: str) -> dict:
    f = load(path)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    rg = r - g
    bg = b - g
    mask = magenta_mask(f)
    n = mask.size
    hit = int(mask.sum())
    out = {
        "path": path,
        "pixels": n,
        "magenta_px": hit,
        "magenta_frac": hit / n,
        "max_r_minus_g": float(rg.max()),
        "max_b_minus_g": float(bg.max()),
        "p99_green": float(np.percentile(g, 99.0)),
        "mean_green": float(g.mean()),
    }
    if hit:
        out["magenta_mean_rgb"] = [float(r[mask].mean()), float(g[mask].mean()), float(b[mask].mean())]
    return out


def main() -> None:
    rows = [stats(p) for p in sys.argv[1:]]
    for s in rows:
        print(f"--- {s['path']}")
        print(f"    pixels          {s['pixels']}")
        print(f"    magenta px      {s['magenta_px']}")
        print(f"    magenta frac    {s['magenta_frac'] * 100:.4f} %")
        print(f"    max(R-G)        {s['max_r_minus_g']:.4f}")
        print(f"    max(B-G)        {s['max_b_minus_g']:.4f}")
        print(f"    p99 green       {s['p99_green']:.4f}")
        print(f"    mean green      {s['mean_green']:.4f}")
        if "magenta_mean_rgb" in s:
            m = s["magenta_mean_rgb"]
            print(f"    magenta mean    R={m[0]:.4f} G={m[1]:.4f} B={m[2]:.4f}")
    if len(rows) == 2:
        a, b = rows
        print()
        print(f"    delta magenta   {a['magenta_frac'] * 100:.4f} % -> {b['magenta_frac'] * 100:.4f} %")
        print(f"    delta max(R-G)  {a['max_r_minus_g']:.4f} -> {b['max_r_minus_g']:.4f}")
        print(f"    delta p99 green {a['p99_green']:.4f} -> {b['p99_green']:.4f}"
              f"   (guard: |d| must be < 0.02, is {abs(a['p99_green'] - b['p99_green']):.4f})")


if __name__ == "__main__":
    main()
