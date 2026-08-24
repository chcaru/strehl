"""Fine-detail contrast, tile by tile, between two renders of the same geometry.

# Why not Tenengrad, and why not one ROI

M86c measured radial Tenengrad on this stack and read 0.9859 -- very slightly
*worse* aligned. Their reading is that gradient energy cannot see this defect,
because misregistration does not blur a pixel, it fetches it from the wrong
scene point, and seams between winner regions *add* gradient energy.

So this metric is built to be falsifiable in that exact way rather than to
avoid the question:

  * It is **band-limited**. A difference-of-Gaussians keeps the octave where
    resolved hair strands live and rejects both the DC/illumination difference
    and the single-pixel noise floor.
  * It is **normalised by local mean**, so a global exposure or gain difference
    between two renders cannot move it.
  * It is computed on **every tile**, not a chosen ROI, and reported against
    each tile's own detail level. There is no ROI to cherry-pick, and the flat
    tiles are the flat-ROI control that AGENTS rule 9 requires -- they are
    measured in the same pass, by the same code, as the detail tiles.
  * Its **direction can be fooled** (rule 18): seams, sharpening and added
    noise all raise it. That is why the jitter arm exists. Planted
    misregistration is known-worse; if it *raises* this metric, the metric is
    fooled in this regime and no reading of it means anything.

Both inputs must have identical geometry. ALIGNED and ZOOMNULL do, by
construction: same `fit_to_cover` k, same resampler, same field of view.

Usage: detail.py <out.json> <ref.tif> <test.tif> [--tile N]
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

TILE = 256


def bandpass(g: np.ndarray) -> np.ndarray:
    """Difference-of-Gaussians: keeps ~2-8 px structure."""
    return gaussian_filter(g, 1.0) - gaussian_filter(g, 4.0)


def main() -> None:
    dst, ref_p, test_p = sys.argv[1], sys.argv[2], sys.argv[3]
    tile = int(sys.argv[sys.argv.index("--tile") + 1]) if "--tile" in sys.argv else TILE

    a = tifffile.imread(ref_p)
    b = tifffile.imread(test_p)
    if a.shape != b.shape:
        raise SystemExit(f"geometry mismatch: {a.shape} vs {b.shape}")
    ga = a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722]) if a.ndim == 3 else a.astype(np.float64)
    gb = b.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722]) if b.ndim == 3 else b.astype(np.float64)

    ba, bb = bandpass(ga), bandpass(gb)
    h, w = ga.shape
    ny, nx = h // tile, w // tile

    rows = []
    for iy in range(ny):
        for ix in range(nx):
            sl = (slice(iy * tile, (iy + 1) * tile), slice(ix * tile, (ix + 1) * tile))
            ma, mb = ga[sl].mean(), gb[sl].mean()
            if ma < 500 or mb < 500:  # pure black: nothing to normalise against
                continue
            ea = float(np.sqrt((ba[sl] ** 2).mean())) / ma
            eb = float(np.sqrt((bb[sl] ** 2).mean())) / mb
            rows.append((ix, iy, ea, eb))

    ea = np.array([r[2] for r in rows])
    eb = np.array([r[3] for r in rows])
    ratio = eb / np.maximum(ea, 1e-12)

    # Bin tiles by the REFERENCE tile's own detail level. Flat tiles are the
    # control; they are not chosen, they are simply the low bins.
    qs = np.percentile(ea, [0, 20, 40, 60, 80, 90, 100])
    bins = []
    for i in range(len(qs) - 1):
        m = (ea >= qs[i]) & (ea <= qs[i + 1] if i == len(qs) - 2 else ea < qs[i + 1])
        if m.sum() == 0:
            continue
        bins.append(
            {
                "detail_pct": f"{[0,20,40,60,80,90][i]}-{[20,40,60,80,90,100][i]}",
                "n_tiles": int(m.sum()),
                "ref_detail_median": float(np.median(ea[m])),
                "ratio_median": float(np.median(ratio[m])),
                "ratio_mean": float(ratio[m].mean()),
            }
        )

    out = {
        "ref": ref_p,
        "test": test_p,
        "tile": tile,
        "n_tiles": len(rows),
        "ratio_median_all": float(np.median(ratio)),
        "bins": bins,
    }
    print(f"ref  = {ref_p}")
    print(f"test = {test_p}")
    print(f"tiles {len(rows)}  overall median ratio (test/ref) {out['ratio_median_all']:.4f}")
    print(f"{'detail %ile':>12} {'n':>6} {'ref detail':>12} {'ratio med':>10}")
    for bn in bins:
        print(
            f"{bn['detail_pct']:>12} {bn['n_tiles']:>6} {bn['ref_detail_median']:>12.6f} "
            f"{bn['ratio_median']:>10.4f}"
        )
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
