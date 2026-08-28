"""Cut a 1:1 review of the WHOLE delivered corpus onto a few viewable sheets.

Why this exists, given crop1to1.py already cuts crops from one master:

The contact sheet is a downscale, and a downscale lies in both directions. It
told me `wrapped-text-2` was mush when the master resolves paper fibre, and it
told me nothing at all about four subjects the halo instrument flags. Tonight I
also looked at the two worst-flagged subjects at 1:1 and could not see the
defect either. So both of my instruments -- the statistic and the thumbnail --
have now disagreed with native pixels, and native pixels win.

This is deliberately NOT an A/B. There is no reference, no ratio and no verdict.
It answers one question only, the one the owner actually asked: does this look
print-worthy. That judgement is mine to make and it cannot be delegated to a
number, so the tool's whole job is to put honest pixels in front of my eye.

Design constraints, each of which is a mistake already made in this project:

* Native scale, never resampled. A crop that has been through a resize is a
  statement about the resampler, not about the merge.
* One fixed display transform per subject, taken from that subject's own 99.9th
  percentile, applied identically to every crop of it. Per-crop autoscaling
  makes a flat region and a contrasty region look equally contrasty, which is
  precisely the read that would hide a halo.
* Two sites per subject with different selection rules: one BOUNDARY site,
  where halos and occlusion artifacts live, and one TEXTURE site, where
  sharpness lives. A single rule answers only half the question.
* Sheets are kept narrow enough to be viewed without downscaling, because a
  downscaled sheet of 1:1 crops is just a contact sheet with extra steps.

Usage:
    python orch_corpuseye.py <master-dir> <out-dir> [--size PX] [--per-sheet N]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

SIZE_DEFAULT = 520
GAP = 8
LABEL_H = 22


def to_luma(a: np.ndarray) -> np.ndarray:
    if a.ndim == 2:
        return a.astype(np.float32)
    a = a[:, :, :3].astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def box(a: np.ndarray, r: int) -> np.ndarray:
    """Separable box mean via cumulative sums; O(1) per pixel in the radius."""
    pad = np.pad(a, r + 1, mode="edge")
    c = pad.cumsum(0).cumsum(1)
    w = 2 * r + 1
    s = c[w:, w:] - c[:-w, w:] - c[w:, :-w] + c[:-w, :-w]
    return s[: a.shape[0], : a.shape[1]] / (w * w)


def score_maps(luma: np.ndarray, stride: int = 8):
    """Return (boundary_score, texture_score) on the strided grid.

    The two rules deliberately disagree. Fine texture has enormous gradient and
    no low-frequency step, so it scores high on texture and low on boundary; a
    subject silhouette against a bright ground is the reverse. Ranking both by
    gradient alone would put both crops on the same feature and waste one.
    """
    small = luma[::stride, ::stride]
    gy, gx = np.gradient(small)
    grad = np.hypot(gy, gx)
    lo = box(small, 12)
    hi = box(small, 40)
    step = np.abs(hi - lo)
    return step * grad, box(grad, 6)


def pick(score: np.ndarray, luma_shape, size: int, stride: int, avoid=None):
    """Top-scoring site as a (y, x) top-left corner, kept clear of `avoid`."""
    s = score.copy()
    half = size // (2 * stride)
    s[:half, :] = 0
    s[-half:, :] = 0
    s[:, :half] = 0
    s[:, -half:] = 0
    sep = max(size // stride, 24)
    for idx in np.argsort(s, axis=None)[::-1]:
        sy, sx = np.unravel_index(idx, s.shape)
        y = max(0, min(luma_shape[0] - size, int(sy * stride) - size // 2))
        x = max(0, min(luma_shape[1] - size, int(sx * stride) - size // 2))
        if avoid is not None and abs(sy - avoid[0]) < sep and abs(sx - avoid[1]) < sep:
            continue
        return (y, x, (sy, sx), float(s[sy, sx]))
    return None


def crops_for(path: Path, size: int):
    """Return [(label, uint8 crop), ...] for one master, or None on failure."""
    a = tifffile.imread(str(path))
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[:, :, :3]
    luma = to_luma(a)

    # One transform for the whole subject, from its own highlights. Identical
    # for both crops so their levels stay comparable to each other by eye.
    scale = 1.0 / max(float(np.percentile(luma, 99.9)), 1.0)

    bnd, tex = score_maps(luma)
    out = []
    b = pick(bnd, luma.shape, size, 8)
    t = pick(tex, luma.shape, size, 8, avoid=b[2] if b else None)
    for tag, site in (("boundary", b), ("texture", t)):
        if site is None:
            continue
        y, x, _, _ = site
        c = a[y : y + size, x : x + size].astype(np.float32) * scale
        c = np.clip(c, 0.0, 1.0) ** (1.0 / 2.2)
        out.append((f"{path.stem}  [{tag}]  y={y} x={x}", (c * 255.0 + 0.5).astype(np.uint8)))
    return out, a.shape


def build_sheet(tiles, size: int, cols: int, out_path: Path):
    rows = (len(tiles) + cols - 1) // cols
    cell_h = size + LABEL_H
    sheet = np.full(
        (rows * cell_h + (rows + 1) * GAP, cols * size + (cols + 1) * GAP, 3), 28, np.uint8
    )
    for i, (_, t) in enumerate(tiles):
        r, c = divmod(i, cols)
        yy = GAP + r * (cell_h + GAP) + LABEL_H
        xx = GAP + c * (size + GAP)
        sheet[yy : yy + size, xx : xx + size] = t
    img = Image.fromarray(sheet)
    d = ImageDraw.Draw(img)
    for i, (label, _) in enumerate(tiles):
        r, c = divmod(i, cols)
        yy = GAP + r * (cell_h + GAP)
        xx = GAP + c * (size + GAP)
        d.text((xx + 2, yy + 4), label, fill=(235, 235, 235))
    img.save(str(out_path), quality=95)
    return img.size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=SIZE_DEFAULT)
    ap.add_argument("--per-sheet", type=int, default=6)
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()

    src = Path(args.master_dir)
    dst = Path(args.out_dir)
    dst.mkdir(parents=True, exist_ok=True)

    masters = sorted(p for p in src.iterdir() if p.suffix.lower() in (".tif", ".tiff"))
    if not masters:
        print(f"no masters under {src}", file=sys.stderr)
        return 2
    print(f"masters : {len(masters)}")

    tiles, sheets, failed = [], [], []
    for p in masters:
        try:
            got, shape = crops_for(p, args.size)
        except Exception as exc:  # a subject that cannot be read is not a subject that passed
            failed.append((p.name, repr(exc)))
            print(f"FAILED  : {p.name}  {exc!r}")
            continue
        print(f"ok      : {p.name:42s} {shape}  crops={len(got)}")
        tiles.extend(got)
        while len(tiles) >= args.per_sheet:
            batch, tiles = tiles[: args.per_sheet], tiles[args.per_sheet :]
            out = dst / f"sheet-{len(sheets):02d}.jpg"
            dims = build_sheet(batch, args.size, args.cols, out)
            sheets.append((out, dims, [b[0] for b in batch]))
            print(f"  sheet -> {out}  {dims[0]}x{dims[1]}")
    if tiles:
        out = dst / f"sheet-{len(sheets):02d}.jpg"
        dims = build_sheet(tiles, args.size, args.cols, out)
        sheets.append((out, dims, [b[0] for b in tiles]))
        print(f"  sheet -> {out}  {dims[0]}x{dims[1]}")

    print()
    print(f"SUMMARY : {len(masters)} masters found")
    print(f"          {len(masters) - len(failed)} rendered, {len(failed)} FAILED to read")
    print(f"          {len(sheets)} sheets written to {dst}")
    for name, exc in failed:
        print(f"          FAILED {name}: {exc}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
