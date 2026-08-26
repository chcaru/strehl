"""The owner's sharp test: is the jagged boundary present in the winner field itself?

His prediction, verbatim: dumping the election field on bee-1-cpl should show the
same jagged boundary, spatially coincident with the outline in the image.
Coincidence is strong evidence; a smooth field under a jagged outline refutes it
outright and sends the search downstream of the election.

So: the toned merge, the winner index, the magnitude of the winner index's
gradient, and n_eff, all at 1:1 over the same crop. The election map is on the
plane grid, exactly half the output in each axis, so it is upsampled by
NEAREST-NEIGHBOUR replication only. Any interpolation here would invent or
destroy exactly the jaggedness in question.

A second panel set paints the winner-field seams straight onto the toned merge, so
coincidence can be judged by eye rather than by flipping between two images.
"""
import argparse
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
REF = np.array([19093.0, 20163.0, 21361.0])     # paper white, measured in bee1.py

CROPS = {
    "left-foreleg": (2124, 1025),      # (cy, cx) on the 4688 x 7032 output grid
    "upper-left-body": (1582, 1391),
    "antenna": (700, 3000),
    "wing-tip": (1400, 5600),
}
HALF = 380


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jump", type=int, default=20)
    ap.add_argument("--tag", default="D", help="render prefix: D (aligned) or E-noalign")
    args = ap.parse_args()
    PICS.mkdir(parents=True, exist_ok=True)

    stem = {"D": ("D-merge.tif", "D-elect.tif", "D-neff.tif"),
            "E-noalign": ("E-noalign-merge.tif", "E-noalign-elect.tif",
                          "E-noalign-neff.tif")}[args.tag]
    img = tifffile.imread(str(OUT / stem[0]))
    assert img.dtype == np.uint16, img.dtype
    e = tifffile.imread(str(OUT / stem[1]))
    assert e.dtype == np.uint16, e.dtype
    n = tifffile.imread(str(OUT / stem[2]))
    assert n.dtype == np.uint16, n.dtype
    print(f"[{args.tag}] merge {img.shape}, elect {e.shape}, neff {n.shape}")

    for name, (cy, cx) in CROPS.items():
        crop = tone(img[cy - HALF:cy + HALF, cx - HALF:cx + HALF])
        py0, py1 = (cy - HALF) // 2, (cy + HALF) // 2
        px0, px1 = (cx - HALF) // 2, (cx + HALF) // 2
        ec = e[py0:py1, px0:px1].astype(np.int32)
        nc = n[py0:py1, px0:px1].astype(np.float64)

        gy, gx = np.gradient(ec.astype(np.float64))
        grad = np.hypot(gx, gy)
        seam = grad > args.jump

        up = lambda a: np.repeat(np.repeat(a, 2, 0), 2, 1)
        painted = crop.copy()
        m = up(seam)[:crop.shape[0], :crop.shape[1]]
        painted[m] = [1.0, 0.25, 0.0]

        fig, axes = plt.subplots(1, 5, figsize=(27, 5.9))
        axes[0].imshow(crop, interpolation="nearest")
        axes[0].set_title("merge, 1:1, linear->tone", fontsize=11)
        im = axes[1].imshow(up(ec), cmap="turbo", interpolation="nearest")
        axes[1].set_title(f"winner index (nearest x2)\nmedian f{np.median(ec):.0f}",
                          fontsize=11)
        plt.colorbar(im, ax=axes[1], fraction=.046)
        axes[2].imshow(up(np.minimum(grad, 60)), cmap="inferno", interpolation="nearest")
        axes[2].set_title("|grad winner index|", fontsize=11)
        im = axes[3].imshow(up(nc), cmap="viridis", interpolation="nearest")
        axes[3].set_title(f"n_eff, median {np.median(nc):.0f}", fontsize=11)
        plt.colorbar(im, ax=axes[3], fraction=.046)
        axes[4].imshow(painted, interpolation="nearest")
        axes[4].set_title(f"seams (|d idx| > {args.jump}) painted on the merge", fontsize=11)
        for ax in axes:
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"bee-1-cpl {name}: does the winner field carry the visible boundary?",
                     fontsize=14)
        fig.tight_layout()
        p = PICS / f"BEE2-{args.tag}-{name}.png"
        fig.savefig(p, dpi=95); plt.close(fig)
        print(f"wrote {p}   seam pixels {100 * seam.mean():.2f}%  "
              f"n_eff median {np.median(nc):.0f}  winner p5-p95 "
              f"{np.percentile(ec, 5):.0f}-{np.percentile(ec, 95):.0f}")


if __name__ == "__main__":
    main()
