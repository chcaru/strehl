"""ORCH interim contact sheet: graded gallery, ordered strongest-first.

PRESENTATION ONLY. Reads the already-graded JPEGs (see grade.py) and lays them
out. The ordering statistic is a crude sharpness proxy computed on tone-curved
8-bit data, which is fine for deciding what to show first and is NOT a
measurement -- nothing here may be cited as a quality number.

The point is narrow: the shipped contact sheet is alphabetical, so the tool's
best work sits between its worst and a viewer judges all 26 by the failures.
Ordering by a sharpness proxy puts the strongest tiles first, which is a fairer
first impression and costs nothing.

Usage:
    python contactsheet.py <graded_dir> <out.jpg> [--cols 5] [--tile 380]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def sharpness_proxy(im: Image.Image) -> float:
    """95th-percentile gradient magnitude on a luminance downsample.

    A proxy, not a metric: computed on tone-curved 8-bit data. Used only to
    decide display order.
    """
    g = np.asarray(im.convert("L").resize((512, 512), Image.LANCZOS), dtype=np.float64) / 255.0
    gy, gx = np.gradient(g)
    return float(np.percentile(np.hypot(gx, gy), 95))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--tile", type=int, default=380)
    args = ap.parse_args()

    files = sorted(Path(args.src).glob("*.jpg"))
    if not files:
        print(f"contactsheet: no JPEGs in {args.src}", file=sys.stderr)
        return 2

    scored = []
    for f in files:
        try:
            im = Image.open(f).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            print(f"contactsheet: SKIP {f.name}: {exc}", file=sys.stderr)
            continue
        scored.append((sharpness_proxy(im), f.stem, im))

    scored.sort(key=lambda t: -t[0])
    print(f"contactsheet: laid out {len(scored)} of {len(files)} file(s) found")
    if len(scored) != len(files):
        print(f"contactsheet: {len(files) - len(scored)} SKIPPED (see lines above)", file=sys.stderr)

    tile, cols = args.tile, args.cols
    cap = 20
    rows = (len(scored) + cols - 1) // cols
    head = 34
    W = cols * tile
    H = head + rows * (tile + cap)
    canvas = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(canvas)
    d.text(
        (10, 11),
        f"strehl -- {len(scored)} subjects, graded for viewing, ordered by a sharpness proxy (strongest first)."
        "  PRESENTATION ONLY: the masters stay linear and faithful.",
        fill=(240, 220, 140),
    )

    for i, (score, name, im) in enumerate(scored):
        r, c = divmod(i, cols)
        im2 = im.copy()
        im2.thumbnail((tile - 6, tile - 6), Image.LANCZOS)
        x = c * tile + (tile - im2.width) // 2
        y = head + r * (tile + cap) + (tile - im2.height) // 2
        canvas.paste(im2, (x, y))
        d.text(
            (c * tile + 5, head + r * (tile + cap) + tile + 4),
            f"{i + 1:2d}. {name}   [{score:.3f}]",
            fill=(190, 190, 195),
        )

    canvas.save(args.dst, quality=90)
    print(f"contactsheet: -> {args.dst}  ({canvas.width}x{canvas.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
