"""Where does the pyramid merge lose its ~10% acuity?

`accept.py` reports ONE number per frame: mean |Laplacian| of green over pixels
above the 20th luminance percentile. That cannot distinguish "10% softer
everywhere" from "one region annihilated". This resolves it spatially.

Uniform softness is repayable by restore.rs (which attributes 18.6% of merge
blur variance to the resampling kernel). A structured loss is not.

The lit mask and the tile ordering are taken from the REFERENCE arm only, so
the partition cannot be shaped by the arm under test.

Commissioning: a ctrl-vs-ctrl null must return ratio 1.0000 in every tile.
If it does not, the instrument is broken and the real result is not read.

Usage:
  python acuitymap.py <dir> <subject> --ref ctrl --test blend [--tile 128]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path.name}: expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] >= 3, f"{path.name}: unexpected shape {a.shape}"
    return a[:, :, 1].astype(np.float32)


def abs_lap(g: np.ndarray) -> np.ndarray:
    """|Laplacian|, 4-neighbour, same convention as accept.py."""
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = (
        4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return np.abs(lap)


def tile_stats(al: np.ndarray, lit: np.ndarray, t: int):
    h, w = al.shape
    ny, nx = h // t, w // t
    out = np.full((ny, nx), np.nan, dtype=np.float64)
    cnt = np.zeros((ny, nx), dtype=np.int64)
    for iy in range(ny):
        for ix in range(nx):
            sl = (slice(iy * t, (iy + 1) * t), slice(ix * t, (ix + 1) * t))
            m = lit[sl]
            n = int(m.sum())
            cnt[iy, ix] = n
            if n >= 64:
                out[iy, ix] = float(al[sl][m].mean())
    return out, cnt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("subject")
    ap.add_argument("--ref", default="ctrl")
    ap.add_argument("--test", default="blend")
    ap.add_argument("--tile", type=int, default=128)
    a = ap.parse_args()

    d = Path(a.dir)
    pref = d / f"{a.subject}--{a.ref}.tiff"
    ptest = d / f"{a.subject}--{a.test}.tiff"
    for p in (pref, ptest):
        if not p.exists():
            print(f"missing: {p}")
            return 2

    gr = green(pref)
    gt = green(ptest)
    assert gr.shape == gt.shape, f"shape mismatch {gr.shape} vs {gt.shape}"

    # lit population defined by the REFERENCE only
    thr = np.percentile(gr, 20.0)
    lit = gr > thr

    ar, at = abs_lap(gr), abs_lap(gt)
    tr, cnt = tile_stats(ar, lit, a.tile)
    tt, _ = tile_stats(at, lit, a.tile)

    print(f"subject   : {a.subject}")
    print(f"arms      : ref={a.ref}  test={a.test}")
    print(f"shape     : {gr.shape}   tile={a.tile}  grid={tr.shape[0]}x{tr.shape[1]}")
    print(f"lit thresh: {thr:.1f} DN   lit fraction {lit.mean():.3f}")

    # --- commissioning: the null must be exactly 1.0 everywhere ---
    tn, _ = tile_stats(ar, lit, a.tile)
    with np.errstate(invalid="ignore", divide="ignore"):
        null = tn / tr
    ok = np.nanmax(np.abs(null - 1.0))
    print(f"\nNULL CONTROL ref-vs-ref  max |ratio-1| = {ok:.2e}", end="  ")
    if ok > 1e-9:
        print("** INSTRUMENT BROKEN -- not reading the real result **")
        return 3
    print("OK")

    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = tt / tr
    v = ratio[np.isfinite(ratio)]
    if v.size == 0:
        print("no judgeable tiles")
        return 2

    glob = float(at[lit].mean() / ar[lit].mean())
    print(f"\nGLOBAL acuity ratio (accept.py's number) : {glob:.4f}")
    print(f"tiles judged                             : {v.size} of {ratio.size}")

    print("\n--- distribution of per-tile ratio ---")
    for q in (0, 1, 5, 25, 50, 75, 95, 99, 100):
        print(f"  p{q:<3d} {np.percentile(v, q):.4f}")
    print(f"  mean {v.mean():.4f}   sd {v.std():.4f}")

    # Structured or uniform? If uniform, every tile sits near the global ratio.
    frac_worse = float((v < glob - 0.05).mean())
    frac_better = float((v > glob + 0.05).mean())
    print(f"\n  tiles >5pp WORSE than global : {frac_worse:6.1%}")
    print(f"  tiles >5pp BETTER than global: {frac_better:6.1%}")
    print(f"  tiles that GAIN acuity (>1.0): {float((v > 1.0).mean()):6.1%}")

    # Does the loss track how sharp the reference tile is?
    rr = tr[np.isfinite(ratio)]
    order = np.argsort(rr)
    print("\n--- ratio by reference-tile sharpness quintile (flat -> sharp) ---")
    print(f"  {'quintile':<10}{'refAcuity':>12}{'ratio':>10}{'nTiles':>9}")
    for i in range(5):
        sel = order[i * len(order) // 5 : (i + 1) * len(order) // 5]
        print(f"  q{i:<9d}{rr[sel].mean():12.1f}{v[sel].mean():10.4f}{len(sel):9d}")

    # write a heatmap
    try:
        from PIL import Image

        lo, hi = 0.70, 1.10
        n = np.clip((ratio - lo) / (hi - lo), 0, 1)
        rgb = np.zeros((*ratio.shape, 3), dtype=np.uint8)
        bad = ~np.isfinite(ratio)
        rgb[..., 0] = np.where(bad, 40, (255 * (1 - n)).astype(np.uint8))
        rgb[..., 1] = np.where(bad, 40, (255 * n).astype(np.uint8))
        rgb[..., 2] = np.where(bad, 40, 40)
        out = d / f"{a.subject}-ACUITYMAP.png"
        Image.fromarray(rgb).resize(
            (ratio.shape[1] * 6, ratio.shape[0] * 6), Image.NEAREST
        ).save(out)
        print(f"\nheatmap (red=lost acuity, green=kept): {out}")
    except Exception as e:  # noqa: BLE001
        print(f"\nheatmap skipped: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
