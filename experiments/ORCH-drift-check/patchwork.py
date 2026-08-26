#!/usr/bin/env python3
"""Does the merge invent structure where every input frame is featureless?

This is the README's last named open defect: a "polygonal patchwork in
defocused backgrounds". The halo is fixed and censused; this one I have never
measured, and I will not describe the product as finished while a named defect
sits unchecked.

SELECTION RULE -- the whole point of the file. Tiles are chosen because the
INPUT FRAMES are featureless there, never because the output looks bad and
never because the output looks flat. flatcrop.py ranks by flatness of the
OUTPUT, which would systematically hide this defect: patchwork is precisely
what makes an output tile non-flat, so an output-flatness rule selects against
the thing being looked for. Section 28 is the general form of that error.

THE TEST. A spatially CONSTANT convex weighting w_k (w_k >= 0, sum w_k = 1)
applied to frames x_k cannot manufacture high-frequency amplitude: filtering is
linear and commutes with the weighting, so
    HF(sum_k w_k x_k) = sum_k w_k HF(x_k)
and by the triangle inequality its amplitude is at most max_k ||HF(x_k)||.
Output HF materially ABOVE the single-frame maximum, in a region where every
frame is featureless, therefore cannot come from any constant convex weighting.
It is either invented, or it comes from the weights VARYING in space -- which is
the patchwork hypothesis.

THE CONTROL ARM. The unweighted mean of the sampled frames is a known
spatially-constant convex weighting with a known answer: independent noise
should put it near ||HF|| / sqrt(N), well BELOW the single-frame max. It is
computed by this file on the same tiles with the same statistic. If the control
arm does not land below the max, the statistic is broken and no verdict here
means anything. That is a structural check on the instrument, not on the merge.

SCALE MATCHING. Inputs are decoded half_size -- each output pixel is the mean
of one Bayer quad, so NO demosaic runs and no demosaic-invented detail enters
the input arm. The merged TIFF is box-downsampled 2x to meet it. Both arms are
then free of demosaic high-frequency content and are at the same sampling
pitch. Comparing a demosaiced output against demosaiced inputs would put an
interpolator's invented detail on both sides of a ratio about invented detail.

Registration is irrelevant here by construction: the tiles are featureless in
every frame, so a sub-pixel warp cannot change an HF AMPLITUDE statistic.

Decoding is rawpy, which shares no code with the thing under test.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rawpy
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

TILE = 192


def luma(a: np.ndarray) -> np.ndarray:
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def box2(a: np.ndarray) -> np.ndarray:
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    a = a[:h, :w]
    return a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def hf(a: np.ndarray) -> np.ndarray:
    """High-pass by subtracting a 4x4 box mean, cheaply and separably."""
    k = 4
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    a = a[:h, :w]
    lo = a.reshape(h // k, k, w // k, k).mean(axis=(1, 3))
    lo = np.repeat(np.repeat(lo, k, axis=0), k, axis=1)
    return a - lo


def tile_stat(x: np.ndarray, y: int, xx: int) -> float:
    return float(np.std(hf(x[y:y + TILE, xx:xx + TILE])))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("merged_tiff")
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--tiles", type=int, default=6)
    ap.add_argument("--crop-out", default=None)
    ap.add_argument("--plant", type=float, default=None,
                    help="commissioning plant: add polygonal structure of this "
                         "amplitude (in output DN, 16-bit scale) to the merged arm")
    args = ap.parse_args()

    raws = sorted(Path(args.raw_dir).glob("*.ARW"))
    if not raws:
        print(f"no ARW in {args.raw_dir}", file=sys.stderr)
        return 2
    idx = np.linspace(0, len(raws) - 1, args.frames).round().astype(int)
    picks = [raws[i] for i in sorted(set(idx.tolist()))]

    print(f"{len(raws)} frames present; sampling {len(picks)}")
    stack = []
    for p in picks:
        with rawpy.imread(str(p)) as r:
            rgb = r.postprocess(half_size=True, output_bps=16, no_auto_bright=True,
                                use_camera_wb=True, gamma=(1, 1),
                                output_color=rawpy.ColorSpace.raw,
                                demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR)
        stack.append(luma(rgb.astype(np.float64)))
    X = np.stack(stack)                      # (N, H, W) half-size, no demosaic
    print(f"input arm: {X.shape}, half-size, gamma 1, no auto-bright")

    merged = tifffile.imread(args.merged_tiff)
    if merged.dtype == np.uint16:
        M = luma(merged.astype(np.float64))
    else:
        M = luma(merged.astype(np.float64) * 65535.0)
    M = box2(M)
    print(f"merged arm: {M.shape} after 2x box downsample")

    h = min(X.shape[1], M.shape[0])
    w = min(X.shape[2], M.shape[1])
    X, M = X[:, :h, :w], M[:h, :w]

    if args.plant is not None:
        # Polygonal structure: piecewise-constant cells on an irregular lattice,
        # which is the SHAPE the defect is described as having. A smooth or
        # noise-like plant would not test the same thing.
        rng = np.random.default_rng(7)
        cell = 24
        gy, gx = np.mgrid[0:h, 0:w]
        jitter_y = rng.integers(-6, 7, size=(h // cell + 2,))
        jitter_x = rng.integers(-6, 7, size=(w // cell + 2,))
        cy = (gy + jitter_y[np.clip(gy // cell, 0, len(jitter_y) - 1)]) // cell
        cx = (gx + jitter_x[np.clip(gx // cell, 0, len(jitter_x) - 1)]) // cell
        lut = rng.normal(0.0, 1.0, size=(cy.max() + 2, cx.max() + 2))
        M = M + args.plant * lut[cy, cx]

    # --- selection: flattest tiles in the INPUT arm, by the WORST frame ---
    margin = 64
    cands = []
    for y in range(margin, h - TILE - margin, TILE):
        for x in range(margin, w - TILE - margin, TILE):
            worst = max(tile_stat(X[k], y, x) for k in range(X.shape[0]))
            cands.append((worst, y, x))
    cands.sort()
    chosen = cands[:args.tiles]

    ctrl = X.mean(axis=0)   # known spatially-constant convex weighting

    print()
    print(f"{'tile':>14s} {'in max':>9s} {'in min':>9s} {'MEAN ctrl':>10s} "
          f"{'MERGED':>9s} {'merged/max':>11s} {'ctrl/max':>9s}")
    print("-" * 84)
    ratios, ctrl_ratios = [], []
    for worst, y, x in chosen:
        per = [tile_stat(X[k], y, x) for k in range(X.shape[0])]
        mx, mn = max(per), min(per)
        c = tile_stat(ctrl, y, x)
        m = tile_stat(M, y, x)
        ratios.append(m / mx)
        ctrl_ratios.append(c / mx)
        print(f"  y{y:5d} x{x:5d} {mx:9.2f} {mn:9.2f} {c:10.2f} {m:9.2f} "
              f"{m/mx:11.3f} {c/mx:9.3f}")

    r = float(np.median(ratios))
    cr = float(np.median(ctrl_ratios))
    n = X.shape[0]
    print()
    print(f"median merged/single-frame-max : {r:.3f}")
    print(f"median  MEAN /single-frame-max : {cr:.3f}   (control; 1/sqrt({n}) = {1/np.sqrt(n):.3f})")

    if cr >= 1.0:
        print("\nCONTROL FAILED: a known constant convex weighting did not land "
              "below the single-frame max. The statistic is broken; no verdict.")
        return 3
    print("control OK: the known-convex arm lands below the max, as it must.")

    if r > 1.0:
        print(f"\nVERDICT: merged HF is {r:.2f}x the single-frame maximum in regions "
              "featureless in EVERY frame. No spatially constant convex weighting "
              "can do that. Structure is being invented or the weights vary in space.")
    else:
        print(f"\nVERDICT: merged HF is {r:.2f}x the single-frame maximum -- within "
              "what a convex weighting can produce. No invented structure at this "
              "scale on these tiles.")

    if args.crop_out:
        out = Path(args.crop_out)
        out.mkdir(parents=True, exist_ok=True)
        for worst, y, x in chosen[:3]:
            t = M[y:y + TILE, x:x + TILE]
            lo, hi = np.percentile(t, [0.5, 99.5])
            if hi - lo < 1e-6:
                hi = lo + 1.0
            v = np.clip((t - lo) / (hi - lo), 0, 1)
            big = np.repeat(np.repeat((v * 255).astype(np.uint8), 3, axis=0), 3, axis=1)
            Image.fromarray(big).save(out / f"patch-y{y}-x{x}-stretched.png")
        print(f"\ncontrast-stretched crops -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
