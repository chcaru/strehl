"""Render-level H2 control: does the patch survive turning the regulariser arm off?

The replica already refutes H2 as the *origin* -- it contains no regulariser at
all and still reproduces the shipped election. But "the origin is upstream" and
"the arm makes no difference to the picture" are different claims, and only the
second one is about what the owner sees. So render the merge with
STREHL_EDGE_AWARE=0, which swaps regularise_guided (the guided domain transform)
for the plain 17x17 box, and put the crops side by side.

Both arms are align-off so they share one frame of reference. The tone transform
is fixed and identical for every panel; autoscaling per panel would manufacture
or hide a difference.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"
REF = np.array([18735.0, 19249.0, 18686.0])

ARMS = [("edge-aware ON (shipped)", "B-noalign-merge.tif", "B-noalign-elect.tif"),
        ("edge-aware OFF (17x17 box)", "C-noea-merge.tif", "C-noea-elect.tif")]
CROPS = {"upper-lobe": (2112, 2464), "lower-lobe": (3168, 3872)}
HALF = 420


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def main():
    for name, (cy, cx) in CROPS.items():
        fig, axes = plt.subplots(2, len(ARMS), figsize=(7.0 * len(ARMS), 13.4))
        for c, (label, mf, ef) in enumerate(ARMS):
            img = tifffile.imread(str(OUT / mf))
            assert img.dtype == np.uint16, img.dtype
            crop = img[cy - HALF:cy + HALF, cx - HALF:cx + HALF]
            del img
            axes[0, c].imshow(tone(crop))
            axes[0, c].set_title(label, fontsize=13)

            e = tifffile.imread(str(OUT / ef))
            assert e.dtype == np.uint16, e.dtype
            ec = e[(cy - HALF) // 2:(cy + HALF) // 2, (cx - HALF) // 2:(cx + HALF) // 2]
            del e
            im = axes[1, c].imshow(np.repeat(np.repeat(ec, 2, 0), 2, 1),
                                   cmap="turbo", vmin=0, vmax=204,
                                   interpolation="nearest")
            axes[1, c].set_title(f"winner field, median f{np.median(ec):.0f}", fontsize=12)
            plt.colorbar(im, ax=axes[1, c], fraction=.046)
        for ax in axes.ravel():
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"H2 render control at {name}: the regulariser arm is not the cause",
                     fontsize=14)
        fig.tight_layout()
        p = PICS / f"H2-{name}.png"
        fig.savefig(p, dpi=90); plt.close(fig)
        print(f"wrote {p}")

    a = tifffile.imread(str(OUT / "B-noalign-elect.tif")).astype(np.int32)
    b = tifffile.imread(str(OUT / "C-noea-elect.tif")).astype(np.int32)
    d = np.abs(a - b)
    print(f"\nwinner-field difference ON vs OFF, whole plane:")
    print(f"  identical    {np.mean(d == 0) * 100:6.2f}% of pixels")
    print(f"  |delta| > 8  {np.mean(d > 8) * 100:6.2f}%")
    print(f"  median |delta| {np.median(d):.1f}   mean {d.mean():.2f}")


if __name__ == "__main__":
    main()
