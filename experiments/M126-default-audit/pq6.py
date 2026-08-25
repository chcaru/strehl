"""M126/PQ6 -- is FOCUS_NOISE_SD's calibration domain the domain it is applied in?

Pre-registered at d3ed787 (experiments/M126-default-audit/PREREG-PQ6.md).

The crate measures FOCUS_NOISE_SD = 0.015214 as the SD of the regularised focus
response on a plane of SYNTHETIC f32 standard normals (merge.rs:2019-2061).
This reads the same statistic off REAL sensor data, using `--limit 1` so the
winner is the only frame and the winner's curse is removed by construction.

Reader discipline: numpy.load for f32 NPY, tifffile for uint16 TIFF, hard
imports, dtype asserted immediately after every load. No PIL anywhere.

ONE-SIDED (registered before measuring): a real flat tile still holds dust,
gradients and faint texture, so every number here is an UPPER BOUND on the true
sensor-noise floor. At-or-below 0.015214 refutes PQ6 cleanly; far-above is
consistent with it but confounded.
"""

import json
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

import score  # reuse the committed, audited selector -- same definitions

ROOT = Path(r"C:\dev\strehl-out\M126\pq6")
SUBJECTS = ["bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl"]

# merge.rs:187
FOCUS_NOISE_SD = 0.015_214
# merge.rs:2065 -- Rayleigh(0.125*sqrt(12)) mean; a box mean does not move it.
RAYLEIGH_MEAN = 0.125 * np.sqrt(12.0) * np.sqrt(np.pi / 2.0)
# focus.rs:117 (SOBEL_RADIUS 1 + WINDOW_RADIUS 13) + merge.rs:93
MARGIN = 14 + 8


def load_focus(subject_dir: Path) -> np.ndarray:
    p = subject_dir / "best_focus.npy"
    a = np.load(p)
    assert a.dtype == np.float32, f"{p} is {a.dtype}, want float32"
    assert a.ndim == 2, f"{p} is {a.shape}, want 2-D"
    return a


def flat_mask_from_render(tif: Path, shape) -> np.ndarray:
    """Flat tiles chosen from the RENDER, never from the response being
    measured -- otherwise the selection is circular."""
    g = score.green(tif)  # asserts uint16 inside
    assert g.shape == shape, f"render {g.shape} != response {shape}"
    st = score.structure(g)
    hh, ww = st.shape[0] // score.TILE, st.shape[1] // score.TILE
    b = st[: hh * score.TILE, : ww * score.TILE].reshape(
        hh, score.TILE, ww, score.TILE
    )
    m = b.mean(axis=(1, 3))
    cut = float(np.quantile(m, score.FLAT_FRAC))
    return m <= cut


def tile_stats(a: np.ndarray, keep: np.ndarray):
    """Per-tile mean and SD of `a`, restricted to tiles flagged in `keep`."""
    hh, ww = keep.shape
    b = a[: hh * score.TILE, : ww * score.TILE].reshape(
        hh, score.TILE, ww, score.TILE
    )
    m1 = b.mean(axis=(1, 3))
    m2 = (b.astype(np.float64) ** 2).mean(axis=(1, 3))
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    return m1[keep], sd[keep]


def main() -> None:
    out = {"FOCUS_NOISE_SD": FOCUS_NOISE_SD, "rayleigh_mean": RAYLEIGH_MEAN,
           "subjects": {}}

    for s in SUBJECTS:
        d = ROOT / f"dump-{s}"
        resp = load_focus(d)
        # Interior only, matching the crate's own margin.
        interior = resp[MARGIN:-MARGIN, MARGIN:-MARGIN]

        keep = flat_mask_from_render(ROOT / f"{s}.tif", resp.shape)
        means, sds = tile_stats(resp, keep)

        out["subjects"][s] = {
            "shape": list(resp.shape),
            "n_flat_tiles": int(keep.sum()),
            "n_tiles_total": int(keep.size),
            # primary, as pre-registered
            "sd_p05": float(np.quantile(sds, 0.05)),
            "sd_p25": float(np.quantile(sds, 0.25)),
            "sd_median": float(np.median(sds)),
            "ratio_p05": float(np.quantile(sds, 0.05) / FOCUS_NOISE_SD),
            "ratio_median": float(np.median(sds) / FOCUS_NOISE_SD),
            # validity check added AFTER pre-registration, labelled as such in
            # the report: if these tiles are truly at the pure-noise floor their
            # MEAN response must sit at the closed-form Rayleigh mean.
            "mean_p05": float(np.quantile(means, 0.05)),
            "mean_median": float(np.median(means)),
            "mean_over_rayleigh": float(np.median(means) / RAYLEIGH_MEAN),
            # global interior SD, the crate test's own form, for reference
            "interior_sd_global": float(interior.astype(np.float64).std()),
            "interior_mean_global": float(interior.astype(np.float64).mean()),
        }
        r = out["subjects"][s]
        print(
            f"{s:>14}  flat tiles {r['n_flat_tiles']:>5}  "
            f"sd p05 {r['sd_p05']:.5f} ({r['ratio_p05']:7.2f}x)  "
            f"med {r['sd_median']:.5f} ({r['ratio_median']:8.2f}x)  "
            f"mean/rayleigh {r['mean_over_rayleigh']:6.2f}"
        )

    # Q3: cross-subject spread of the p05 floor.
    p05s = [out["subjects"][s]["sd_p05"] for s in SUBJECTS]
    out["q3_spread_p05"] = float(max(p05s) / min(p05s))
    meds = [out["subjects"][s]["sd_median"] for s in SUBJECTS]
    out["q3_spread_median"] = float(max(meds) / min(meds))

    # Q5 placebo: a repeat render must be bit-identical and read exactly zero.
    a = load_focus(ROOT / "dump-bee-3-cpl")
    b = load_focus(ROOT / "dump-bee-3-cpl-REPEAT")
    out["q5_bitwise_identical"] = bool(np.array_equal(a, b))
    out["q5_max_abs_diff"] = float(np.abs(a.astype(np.float64)
                                          - b.astype(np.float64)).max())

    print()
    print(f"Q3 cross-subject spread of p05    : {out['q3_spread_p05']:.2f}x")
    print(f"Q3 cross-subject spread of median : {out['q3_spread_median']:.2f}x")
    print(f"Q5 placebo bitwise identical      : {out['q5_bitwise_identical']}")
    print(f"Q5 placebo max abs diff           : {out['q5_max_abs_diff']:.5f}")

    (ROOT / "pq6.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'pq6.json'}")


if __name__ == "__main__":
    main()
