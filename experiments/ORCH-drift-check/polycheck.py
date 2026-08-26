#!/usr/bin/env python3
"""Does the estimator's polygonal patchwork appear on subjects other than bee-3-cpl?

Section 45 proved the patchwork is the estimator backend rather than the noise
gate, but it proved it by eye on ONE subject.  The record carries that as an
explicit uncertainty.  This closes it, or fails to.

The measurement.  Polygons are *structure in a region that should be smooth*.  A
defocused background is smooth by construction: every input frame is out of focus
there, so any fine structure in the output was manufactured by the merge.  So:

  1.  Restrict to background -- the pixels whose gradient on the ARM MEAN is in
      the bottom `--bg-pct`.  Selecting on the mean means neither arm chooses its
      own ground.
  2.  Inside that region, score each block by high-pass energy: the standard
      deviation of the block after subtracting a box-blurred copy of itself.
      Smooth background scores near the noise floor.  Polygons score above it,
      because a hard-edged facet boundary is exactly high-frequency content.
  3.  Report both arms' scores on the SAME blocks, and crop the worst
      disagreement at 1:1 with no resampling.

The control that makes it a measurement rather than an assertion: the same
statistic is reported on `--n-ctrl` blocks drawn at random from the same
background mask.  If the two arms differ on the worst block but agree on the
random blocks, the difference is localised structure.  If they differ everywhere
by the same amount, the statistic is reading a global property -- exposure,
noise, sharpening -- and says nothing about polygons.

Usage:
    python polycheck.py <estimator.tiff> <pyramid.tiff> <out.jpg> --label-a est
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return a.astype(np.float32) / 65535.0


def boxblur(a: np.ndarray, r: int) -> np.ndarray:
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), axis=0)
    a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def grad(y: np.ndarray) -> np.ndarray:
    gy = np.abs(np.diff(y, axis=0, prepend=y[:1]))
    gx = np.abs(np.diff(y, axis=1, prepend=y[:, :1]))
    return gy + gx


def font(sz: int):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("out")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--crop", type=int, default=520)
    ap.add_argument("--bg-pct", type=float, default=30.0)
    ap.add_argument("--hp-radius", type=int, default=6)
    ap.add_argument("--n-ctrl", type=int, default=24)
    ap.add_argument("--bg-frac", type=float, default=0.90)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    A, B = load(args.a), load(args.b)
    assert A.shape == B.shape, f"shape mismatch {A.shape} vs {B.shape}"
    h, w = A.shape[:2]
    ya, yb = A.mean(axis=2), B.mean(axis=2)
    ym = 0.5 * (ya + yb)

    # Background mask from the ARM MEAN, so neither arm chooses its own ground.
    g = grad(ym)
    thr = np.percentile(g, args.bg_pct)

    c = args.crop
    step = c // 2
    ys = list(range(0, h - c, step))
    xs = list(range(0, w - c, step))

    hp_a = np.abs(ya - boxblur(ya, args.hp_radius))
    hp_b = np.abs(yb - boxblur(yb, args.hp_radius))

    def coarse(y: np.ndarray, f: int) -> np.ndarray:
        """Box-average by f, then measure gradient.

        This is the discriminator between noise and structure.  Averaging fxf
        independent samples divides white noise by f, but leaves a hard-edged
        facet boundary of size >> f essentially intact.  So if the two arms'
        ratio SHRINKS toward 1 as f grows, the excess was noise; if it HOLDS or
        GROWS, the excess is structure that survives averaging -- which is what
        a polygonal facet is.
        """
        hh, ww = (y.shape[0] // f) * f, (y.shape[1] // f) * f
        d = y[:hh, :ww].reshape(hh // f, f, ww // f, f).mean(axis=(1, 3))
        return grad(d)

    cand = []
    for y in ys:
        for x in xs:
            gb = g[y:y + c, x:x + c]
            if (gb < thr).mean() < args.bg_frac:      # block must be almost all background
                continue
            sa = float(hp_a[y:y + c, x:x + c].std())
            sb = float(hp_b[y:y + c, x:x + c].std())
            cand.append((y, x, sa, sb))

    if not cand:
        print("no block is >=90% background at this bg-pct; nothing to measure")
        return 1

    rng = np.random.default_rng(args.seed)
    idx = rng.choice(len(cand), size=min(args.n_ctrl, len(cand)), replace=False)
    ctrl = np.array([[cand[i][2], cand[i][3]] for i in idx])

    worst = max(cand, key=lambda t: t[2] - t[3])
    wy, wx, wsa, wsb = worst

    print(f"{os.path.basename(args.a)}  vs  {os.path.basename(args.b)}")
    print(f"  background blocks considered : {len(cand)}  "
          f"({args.crop}px, >=90% below the {args.bg_pct:g}th gradient pct)")
    print(f"  high-pass sd, WORST block @({wx},{wy}):")
    print(f"      {args.label_a:<10s} {wsa:.6f}")
    print(f"      {args.label_b:<10s} {wsb:.6f}")
    print(f"      ratio {args.label_a}/{args.label_b} = {wsa / wsb:.3f}"
          if wsb else "      ratio undefined")
    print(f"  CONTROL -- {ctrl.shape[0]} random background blocks:")
    print(f"      {args.label_a:<10s} median {np.median(ctrl[:, 0]):.6f}")
    print(f"      {args.label_b:<10s} median {np.median(ctrl[:, 1]):.6f}")
    cr = float(np.median(ctrl[:, 0]) / np.median(ctrl[:, 1]))
    print(f"      ratio median = {cr:.3f}")
    print(f"  worst/control ratio separation = {(wsa / wsb) / cr:.3f}"
          if wsb and cr else "")
    print("      (a separation near 1.0 means the arms differ uniformly and this"
          " says nothing\n       about polygons; a separation well above 1.0"
          " means localised structure)")

    # THE DISCRIMINATOR.  The uniform excess above could be noise rather than
    # polygons: this estimator arm averages fewer frames than the pyramid arm,
    # and noise is high-pass energy too.  Averaging fxf samples divides white
    # noise by f but leaves a facet boundary intact, so the scale dependence of
    # the ratio separates the two explanations.
    print("\n  scale ladder over ALL background blocks -- noise dies under "
          "averaging, facets do not:")
    print(f"      {'factor':>7s} {'est':>10s} {'pyr':>10s} {'ratio':>8s} "
          f"{'noise pred':>11s}")
    base = None
    for f_ in (1, 2, 4, 8, 16):
        ra, rb = [], []
        for (y, x, _, _) in cand:
            ba = ya[y:y + c, x:x + c]
            bb = yb[y:y + c, x:x + c]
            if f_ == 1:
                ra.append(float(grad(ba).mean()))
                rb.append(float(grad(bb).mean()))
            else:
                ra.append(float(coarse(ba, f_).mean()))
                rb.append(float(coarse(bb, f_).mean()))
        ma, mb = float(np.median(ra)), float(np.median(rb))
        r = ma / mb if mb else float("nan")
        if base is None:
            base = r
        print(f"      {f_:7d} {ma:10.6f} {mb:10.6f} {r:8.3f} "
              f"{'-' if f_ == 1 else f'{base:.3f} if noise':>11s}")
    print("      If the excess were noise the ratio would stay flat while both")
    print("      columns fell as 1/f.  A ratio that GROWS with f is structure")
    print("      that survives averaging, i.e. facets.")

    ca = (A[wy:wy + c, wx:wx + c] * 255).clip(0, 255).astype(np.uint8)
    cb = (B[wy:wy + c, wx:wx + c] * 255).clip(0, 255).astype(np.uint8)
    lab = 26
    sheet = Image.new("RGB", (2 * c + 12, c + lab + 20), (16, 16, 18))
    sheet.paste(Image.fromarray(ca, "RGB"), (0, lab))
    sheet.paste(Image.fromarray(cb, "RGB"), (c + 12, lab))
    d = ImageDraw.Draw(sheet)
    f = font(15)
    d.text((2, 5), f"{args.label_a}  hp sd={wsa:.5f}  @({wx},{wy}) 1:1",
           font=f, fill=(255, 210, 90))
    d.text((c + 14, 5), f"{args.label_b}  hp sd={wsb:.5f}  same rect",
           font=f, fill=(140, 230, 140))
    d.text((2, c + lab + 2),
           f"background block, >=90% below p{args.bg_pct:g} gradient on the arm "
           f"mean; control separation {(wsa / wsb) / cr:.2f}x",
           font=font(13), fill=(190, 190, 198))
    sheet.save(args.out, "JPEG", quality=95, subsampling=0)
    print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
