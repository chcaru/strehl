"""S5 -- read the election directly out of the merged file.

At `--gate 0` with `STREHL_ALIGN=0` the merge averages exactly one frame per
pixel and applies no resampling, so every merged pixel MUST be the byte-exact
16-bit value that frame's own green sample maps to. That makes the merged file
a readable record of which frame won each pixel, with no access to `merge.rs`
and no instrumentation of the binary.

Two things fall out:

  A. FIDELITY -- what fraction of merged pixels equal SOME frame exactly. If
     this is not ~100%, the merge is doing arithmetic to the winner and the
     "mosaic of elected frames" model is wrong.

  B. THE ELECTION MAP -- which frame won. With that, the merged output can be
     compared against a per-pixel ORACLE built by an independent selector, and
     the loss can be attributed to election rather than to rendering.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
CUBE = os.path.join(L.OUT, "m93_crops_v2.npy")
MERGED = os.path.join(L.OUT, "armM-gate0-binlin.tif")
BLACK, RANGE = 512.0, 14848.0
WIN = 512


def to_tif_u16(green_mean: np.ndarray) -> np.ndarray:
    v = np.clip((green_mean - BLACK) / RANGE, 0.0, 1.0)
    return np.floor(v * 65535.0 + 0.5).astype(np.uint16)


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    names = list(rois.keys())
    cube = np.load(CUBE, mmap_mode="r")
    n = cube.shape[0]
    merged = L.read_tif_green(MERGED)
    print(f"merged TIFF    : {merged.shape[1]} x {merged.shape[0]}   {MERGED}")
    print(f"cube           : {cube.shape}")

    res = {}
    for k, nm in enumerate(names):
        x, y = rois[nm]["x"], rois[nm]["y"]
        m = merged[y : y + WIN, x : x + WIN].astype(np.uint16)
        pred = to_tif_u16(np.asarray(cube[:, k], dtype=np.float64))  # (n, WIN, WIN)
        eq = pred == m[None, :, :]
        nmatch = eq.sum(axis=0)
        frac_any = float((nmatch > 0).mean())
        frac_unique = float((nmatch == 1).mean())
        # Winner: among frames that match exactly, the one whose neighbourhood
        # also matches. Score each candidate by how many of its 5x5 neighbours
        # match, then take the argmax over candidates (rule 4: the tie
        # structure is reported, not hidden).
        from scipy.ndimage import uniform_filter

        support = uniform_filter(eq.astype(np.float32), size=(1, 5, 5))
        support[~eq] = -1.0
        win_idx = np.argmax(support, axis=0)
        best_support = np.max(support, axis=0)
        elected = np.where(nmatch > 0, win_idx, -1)

        vals, counts = np.unique(elected[elected >= 0], return_counts=True)
        order = np.argsort(counts)[::-1]
        top = [(int(vals[i]), int(counts[i]), float(counts[i] / elected.size)) for i in order[:8]]

        res[nm] = dict(
            window=[x, y],
            frac_pixel_matches_some_frame=frac_any,
            frac_unique_match=frac_unique,
            mean_candidates=float(nmatch.mean()),
            median_neighbourhood_support=float(np.median(best_support[elected >= 0])),
            n_distinct_elected=int(vals.size),
            top_elected=top,
            elected_p05=float(np.percentile(elected[elected >= 0], 5)),
            elected_p50=float(np.percentile(elected[elected >= 0], 50)),
            elected_p95=float(np.percentile(elected[elected >= 0], 95)),
        )
        np.save(os.path.join(L.OUT, f"m93_elected_{nm}.npy"), elected.astype(np.int16))
        print()
        print(f"{nm}  window ({x},{y})")
        print(f"  merged pixel equals SOME frame exactly : {100*frac_any:.4f}%")
        print(f"  exactly one candidate frame            : {100*frac_unique:.2f}%")
        print(f"  mean candidate frames per pixel        : {nmatch.mean():.2f}")
        print(f"  distinct frames elected in this ROI    : {vals.size}")
        print(f"  elected frame index  p05 / p50 / p95   : "
              f"{res[nm]['elected_p05']:.0f} / {res[nm]['elected_p50']:.0f} / {res[nm]['elected_p95']:.0f}")
        print(f"  top elected frames (idx, px, share)    : {top[:5]}")

    dst = os.path.join(OUTDIR, "s5_election.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\nwrote          : {dst}")

    worst = min(res[nm]["frac_pixel_matches_some_frame"] for nm in names)
    print(f"\nFIDELITY: worst ROI has {100*worst:.4f}% of merged pixels equal to some frame exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
