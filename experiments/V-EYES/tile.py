"""Cut 1:1 tiles small enough to survive the viewer.

viewer_target.py established that the path from file to my eye is 1:1 at 400 px
but resampled at 600 px and above: a 1 px horizontal grating survives at 400 and
collapses to a flat wash at 600 and 1000, and 1-2 px checkerboards pick up
large-scale moire at those sizes. Judging the delivered 1000 x 1000 crops by eye
therefore reproduces exactly the defect this audit was called to investigate --
a resampler in front of the observer -- so every tile viewed from here on is cut
at 400 px or less and never resized.

16-bit masters are converted with /257.0 and round-to-nearest, which is what the
delivery README specifies and what the masters' own provenance requires: they
are written with --srgb and are already display-encoded, so any additional tone
map would be a second encoding of an already-encoded signal.

Optionally writes a contrast-stretched twin (percentile clip) for inspecting
shadow structure, clearly named so it is never mistaken for the delivered
rendition.

Usage:
  python tile.py <src> <x> <y> <size> <outpath> [--stretch lo hi]
"""

import sys
import pathlib
import numpy as np
from PIL import Image


def load(src):
    p = pathlib.Path(src)
    if p.suffix.lower() in (".tif", ".tiff"):
        import tifffile

        a = tifffile.imread(str(p))
        return (a / 257.0).round().clip(0, 255).astype(np.uint8)
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    src, x, y, size, out = (
        sys.argv[1],
        int(sys.argv[2]),
        int(sys.argv[3]),
        int(sys.argv[4]),
        sys.argv[5],
    )
    a = load(src)
    h, w = a.shape[:2]
    x = max(0, min(x, w - size))
    y = max(0, min(y, h - size))
    t = a[y : y + size, x : x + size]
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(t).save(out)
    print(f"{pathlib.Path(src).name} {w}x{h} -> tile ({x},{y}) {size}x{size} -> {out}")
    print(f"  min={t.min()} max={t.max()} mean={t.mean():.1f}")

    if "--stretch" in sys.argv:
        i = sys.argv.index("--stretch")
        lo, hi = float(sys.argv[i + 1]), float(sys.argv[i + 2])
        f = t.astype(np.float32)
        a0, a1 = np.percentile(f, lo), np.percentile(f, hi)
        g = np.clip((f - a0) / max(a1 - a0, 1e-6) * 255.0, 0, 255).astype(np.uint8)
        sp = str(pathlib.Path(out).with_name(pathlib.Path(out).stem + "-STRETCHED.png"))
        Image.fromarray(g).save(sp)
        print(f"  stretch p{lo}={a0:.1f} p{hi}={a1:.1f} -> {sp}  (NOT the delivered rendition)")


if __name__ == "__main__":
    main()
