"""Cut the same box out of two arms at 1:1, no magnification, shared stretch.

The owner asked for pixel coordinates so he could open the picture himself. This
writes the crop as well, for one reason: my own naming misled him about the sign
of `d`, and a ready-made crop removes any chance he opens the wrong place
because of it.

Rules this file obeys, each of them earned:

  * **1:1, no resampling.** No np.repeat, no zoom, no interpolation. A magnified
    crop is blocky by construction and cannot be evidence about morphology --
    that is exactly how a sibling lane's crop had to be retracted.
  * **One shared stretch across both panels, quoted in DN.** Per-panel
    normalisation makes a level difference look like a structure difference.
    The two arms' far fields here differ by 0.59% (19163 vs 19050 DN), small
    enough that a shared stretch is honest and necessary.
  * **The stretch bounds are printed**, so a reader can reproduce the picture or
    reject it.

    python crop1to1.py <x> <y> <w> <h> <out.png> <a.tif> <b.tif> [--lo D --hi D]
"""

import pathlib
import sys

import numpy as np
import tifffile


def luma(p):
    a = tifffile.imread(p)
    return a.astype(np.float32).mean(axis=2) if a.ndim == 3 else a.astype(np.float32)


def main():
    argv = sys.argv[1:]
    lo = hi = None
    for flag in ("--lo", "--hi"):
        if flag in argv:
            i = argv.index(flag)
            v = float(argv[i + 1])
            if flag == "--lo":
                lo = v
            else:
                hi = v
            del argv[i:i + 2]
    if len(argv) < 6:
        print(__doc__)
        return 2
    x, y, w, h = (int(v) for v in argv[:4])
    out, paths = argv[4], argv[5:]

    crops = []
    for p in paths:
        a = luma(p)
        c = a[y:y + h, x:x + w]
        crops.append((pathlib.Path(p).name, c, a.shape))
        print(f"  {pathlib.Path(p).name}  full {a.shape}  crop {c.shape}  "
              f"mean {c.mean():.1f} DN  p1 {np.percentile(c, 1):.0f}  "
              f"p99 {np.percentile(c, 99):.0f}")

    allpx = np.concatenate([c.ravel() for _, c, _ in crops])
    if lo is None:
        lo = float(np.percentile(allpx, 0.5))
    if hi is None:
        hi = float(np.percentile(allpx, 99.5))
    print(f"  SHARED stretch {lo:.0f}-{hi:.0f} DN across all panels "
          f"(per-panel stretch would turn a level difference into an "
          f"apparent structure difference)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Exact-pixel panels first. matplotlib's tight_layout shrinks axes to fit
    # titles, so a figure-based panel is NOT 1:1 however the figsize is chosen.
    # These files are, byte for byte: one image pixel, one PNG pixel.
    from PIL import Image
    scaled = []
    for name, c, _ in crops:
        q = np.clip((c - lo) / max(hi - lo, 1e-9), 0, 1)
        q8 = (q * 255.0 + 0.5).astype(np.uint8)
        stem = pathlib.Path(out).with_suffix("")
        p1 = f"{stem}--{pathlib.Path(name).stem}--1to1.png"
        Image.fromarray(q8).save(p1)
        scaled.append(p1)
        print(f"  wrote {p1}   {q8.shape[1]} x {q8.shape[0]} px, EXACT 1:1, "
              f"8-bit of the {lo:.0f}-{hi:.0f} DN window")

    n = len(crops)
    fig, ax = plt.subplots(1, n, figsize=(w / 100.0 * n, h / 100.0 + 0.6),
                           squeeze=False)
    for j, (name, c, _) in enumerate(crops):
        ax[0, j].imshow(c, cmap="gray", vmin=lo, vmax=hi,
                        interpolation="nearest")
        ax[0, j].set_title(f"{name}   crop ({x},{y},{w},{h})", fontsize=9)
        ax[0, j].set_xticks([])
        ax[0, j].set_yticks([])
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    print(f"  wrote {out}  side-by-side for convenience -- NOT 1:1, "
          f"tight_layout resizes the axes. Judge morphology on the files above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
