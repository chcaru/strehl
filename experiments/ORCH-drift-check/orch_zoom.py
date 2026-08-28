"""Cut an EXACT rectangle from a master, optionally at integer nearest-neighbour zoom.

crop1to1.py and orch_corpuseye.py both CHOOSE their sites. That is right for a
survey and wrong for an interrogation: once the eye has found something, the
next question is always "what exactly is at y,x", and a picker that re-ranks
will not necessarily go back there.

Integer nearest-neighbour zoom only. No interpolation, ever -- the artifact
under investigation here is suspected to be blocky and grid-aligned, and a
smooth resampler would soften the very evidence that decides what it is.

The optional --chroma pane is the discriminator that matters for this class of
defect: it shows R-G and B-G as a signed map around neutral. Luma structure
belongs to the subject; a defect in the demosaic or the resampler lives in the
colour differences and is often invisible next to real detail.

Usage:
    python orch_zoom.py <master.tiff> <out.jpg> --y Y --x X [--size PX] [--zoom N] [--chroma]
"""

import argparse

import numpy as np
import tifffile
from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("out")
    ap.add_argument("--y", type=int, required=True)
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--zoom", type=int, default=4)
    ap.add_argument("--chroma", action="store_true")
    ap.add_argument("--gain", type=float, default=6.0, help="chroma amplification")
    args = ap.parse_args()

    a = tifffile.imread(args.master)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[:, :, :3]
    h, w = a.shape[:2]
    y = max(0, min(h - args.size, args.y))
    x = max(0, min(w - args.size, args.x))
    crop = a[y : y + args.size, x : x + args.size].astype(np.float32)
    print(f"master : {args.master}")
    print(f"shape  : {a.shape}")
    print(f"rect   : y={y} x={x} size={args.size}  zoom={args.zoom}")

    p999 = float(np.percentile(a[:, :, 1], 99.9))
    rgb = np.clip(crop / max(p999, 1.0), 0.0, 1.0) ** (1.0 / 2.2)
    panes = [(rgb * 255.0 + 0.5).astype(np.uint8)]

    if args.chroma:
        # Signed colour differences about neutral grey. A demosaic or resampler
        # defect shows here as structure that has no counterpart in luma.
        eps = 1.0
        g = crop[:, :, 1] + eps
        rg = np.log2((crop[:, :, 0] + eps) / g)
        bg = np.log2((crop[:, :, 2] + eps) / g)
        print(f"R-G    : mean={rg.mean():+.4f} sd={rg.std():.4f} min={rg.min():+.3f} max={rg.max():+.3f}")
        print(f"B-G    : mean={bg.mean():+.4f} sd={bg.std():.4f} min={bg.min():+.3f} max={bg.max():+.3f}")
        ch = np.zeros(rgb.shape, np.float32)
        ch[:, :, 0] = 0.5 + args.gain * (rg - rg.mean()) * 0.5
        ch[:, :, 2] = 0.5 + args.gain * (bg - bg.mean()) * 0.5
        ch[:, :, 1] = 0.5
        panes.append((np.clip(ch, 0, 1) * 255.0 + 0.5).astype(np.uint8))

    z = args.zoom
    panes = [np.repeat(np.repeat(p, z, axis=0), z, axis=1) for p in panes]
    gap = 8
    ph, pw = panes[0].shape[:2]
    sheet = np.full((ph, len(panes) * pw + (len(panes) - 1) * gap, 3), 28, np.uint8)
    for i, p in enumerate(panes):
        sheet[:, i * (pw + gap) : i * (pw + gap) + pw] = p
    Image.fromarray(sheet).save(args.out, quality=96)
    print(f"wrote  : {args.out}  ({sheet.shape[1]}x{sheet.shape[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
