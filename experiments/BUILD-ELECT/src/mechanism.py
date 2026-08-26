"""The money picture: render the decomposition table as an image.

focusdecomp.py measured that at the pale-wash ROI strehl's focus measure peaks at
f136 while its high-frequency part peaks at f40. That is a table of numbers, and
this project has shipped two defects that were invisible in tables and obvious in
three seconds of looking. So: draw it.

Each row is one frame. Columns are the toned crop, the full-luma |grad| that the
focus measure actually aggregates, and that gradient split into its low-pass
(ramp) and high-pass (texture) parts. Column scales are shared across rows so the
two frames are directly comparable -- per-panel autoscaling would erase exactly
the difference being shown.

The control ROI is drawn with the identical treatment. If the low-pass column
lights up at the elected frame everywhere, the split is an artifact of the split;
it must light up only where the defect is.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, uniform_filter

from focusdecomp import (LOW_SIGMA, MEASURE_HALF, WINDOW_RADIUS, centre, sobel_mag)

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"
REF = np.array([18735.0, 19249.0, 18686.0])   # fixed tone, never autoscaled

ROI_FRAMES = {
    "pale-wash":    [40, 136],   # true texture peak vs the frame the binary elected
    "dark-patch":   [24, 136],   # control: elected at its own texture peak
}


def tone(rgb):
    x = np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1)
    return x ** (1 / 2.2)


def planes(rgb):
    g = rgb.astype(np.float64)[:, :, 1]
    L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
    low = gaussian_filter(L, LOW_SIGMA, mode="nearest")
    return L, low, L - low


def boxed(a):
    return uniform_filter(sobel_mag(a), size=2 * WINDOW_RADIUS + 1, mode="nearest")


def main():
    src = OUT / "ladder-crops"
    for roi, fr in ROI_FRAMES.items():
        data = {}
        for k in fr:
            z = np.load(src / f"f{k:03d}.npz")
            rgb = z[roi]
            L, low, high = planes(rgb)
            data[k] = {"crop": tone(rgb), "full": boxed(L), "low": boxed(low),
                       "high": boxed(high), "lowluma": low}

        cols = ["crop", "full", "high", "low", "lowluma"]
        titles = {"crop": "the frame", "full": "|grad| boxed r=13\n(what strehl ranks)",
                  "high": "high-pass part\n(real texture)",
                  "low": "low-pass part\n(smooth ramp)",
                  "lowluma": "the low-pass luma\n(where the ramp is)"}
        vmax = {c: max(np.percentile(centre(data[k][c]), 99.5) for k in fr)
                for c in ("full", "high", "low")}
        vmax["lowluma"] = max(centre(data[k]["lowluma"]).max() for k in fr)

        fig, axes = plt.subplots(len(fr), len(cols), figsize=(4.0 * len(cols), 4.3 * len(fr)))
        for r, k in enumerate(fr):
            for c, col in enumerate(cols):
                ax = axes[r, c]
                if col == "crop":
                    ax.imshow(np.clip(centre(data[k][col].transpose(2, 0, 1)).transpose(1, 2, 0)
                                      if False else data[k][col][
                        data[k][col].shape[0] // 2 - 2 * MEASURE_HALF:
                        data[k][col].shape[0] // 2 + 2 * MEASURE_HALF,
                        data[k][col].shape[1] // 2 - 2 * MEASURE_HALF:
                        data[k][col].shape[1] // 2 + 2 * MEASURE_HALF], 0, 1))
                else:
                    m = centre(data[k][col])
                    ax.imshow(m, cmap="inferno", vmin=0, vmax=vmax[col])
                    ax.set_xlabel(f"median {np.median(m):.4g}", fontsize=9)
                ax.set_xticks([]); ax.set_yticks([])
                if r == 0:
                    ax.set_title(titles[col], fontsize=11)
                if c == 0:
                    ax.set_ylabel(f"frame {k}", fontsize=13)
        fig.suptitle(
            f"{roi}: what strehl's focus measure is actually responding to\n"
            f"columns share a scale across rows; nothing is autoscaled per panel",
            fontsize=13)
        fig.tight_layout()
        p = PICS / f"MECH-{roi}.png"
        fig.savefig(p, dpi=100); plt.close(fig)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
