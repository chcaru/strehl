"""Simulate the proposed fix on the actual defect, per pixel.

The decomposition showed, at four hand-picked ROIs, that strehl's focus measure
peaks on a smooth ramp rather than on texture at the one ROI that is visibly
broken. That is four points. The defect is a *seam*, and a seam is a spatial
object, so the honest test is spatial: elect a winner at every pixel of the crop
that contains the seam, twice --

  ARM A  the shipped operator     : |grad(L)|            -> box r=13 -> argmax
  ARM B  the proposed operator    : |grad(L - blur(L))|  -> box r=13 -> argmax

-- and look at the two winner fields. Arm A must reproduce the seam (that is the
commissioning: an arm that cannot reproduce the defect cannot be used to argue it
is cured). Arm B is the prediction.

This is a *simulation*, not the fix. It runs on 21 of 205 frames, on the
demosaiced green rather than the raw CFA green, with no regulariser, no gate and
no pass two. It can show that the ranking changes; it cannot show what the shipped
merge would output. That distinction is kept in the report.

The control is the dark-patch crop, where the shipped election is already correct:
arm B must leave it alone. A remedy that changes the winner field everywhere is
not a remedy, it is a different defect.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, uniform_filter

from focusdecomp import LOW_SIGMA, WINDOW_RADIUS, sobel_mag

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"
REF = np.array([18735.0, 19249.0, 18686.0])


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def winner_fields(src, roi):
    files = sorted(src.glob("f*.npz"))
    frames = np.array([int(f.stem[1:]) for f in files])
    a_stack, b_stack, crops = [], [], []
    for f in files:
        rgb = np.load(f)[roi]
        g = rgb.astype(np.float64)[:, :, 1]
        L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
        hp = L - gaussian_filter(L, LOW_SIGMA, mode="nearest")
        k = 2 * WINDOW_RADIUS + 1
        a_stack.append(uniform_filter(sobel_mag(L), size=k, mode="nearest"))
        b_stack.append(uniform_filter(sobel_mag(hp), size=k, mode="nearest"))
        crops.append(rgb)
    a, b = np.array(a_stack), np.array(b_stack)
    return frames, frames[a.argmax(0)], frames[b.argmax(0)], crops


def seam_energy(w):
    """Mean |gradient| of the winner field: how much the election jumps around."""
    gy, gx = np.gradient(w.astype(np.float64))
    return float(np.mean(np.hypot(gx, gy)))


def main():
    src = OUT / "ladder-crops"
    for roi, note in (("pale-wash", "THE DEFECT"), ("dark-patch", "CONTROL")):
        frames, wa, wb, crops = winner_fields(src, roi)
        ea, eb = seam_energy(wa), seam_energy(wb)
        # fraction of the crop electing the far (ramp) mode
        far_a = float(np.mean(wa > 90)) * 100
        far_b = float(np.mean(wb > 90)) * 100
        print(f"\n{roi}  [{note}]")
        print(f"  arm A shipped   winner median f{np.median(wa):.0f}  "
              f"far-mode {far_a:5.1f}%  seam energy {ea:6.2f}")
        print(f"  arm B high-pass winner median f{np.median(wb):.0f}  "
              f"far-mode {far_b:5.1f}%  seam energy {eb:6.2f}")

        mid = len(crops) // 2
        fig, axes = plt.subplots(1, 4, figsize=(20, 5.4))
        axes[0].imshow(tone(crops[np.argmin(np.abs(frames - 40))]))
        axes[0].set_title("frame 40 (in focus here)")
        for ax, w, t in ((axes[1], wa, f"ARM A: shipped operator\nmedian f{np.median(wa):.0f}, "
                          f"far-mode {far_a:.1f}%, seam {ea:.2f}"),
                         (axes[2], wb, f"ARM B: high-pass operator\nmedian f{np.median(wb):.0f}, "
                          f"far-mode {far_b:.1f}%, seam {eb:.2f}")):
            im = ax.imshow(w, cmap="turbo", vmin=frames.min(), vmax=frames.max())
            ax.set_title(t)
            plt.colorbar(im, ax=ax, fraction=.046)
        d = axes[3].imshow(np.abs(wa.astype(float) - wb.astype(float)), cmap="inferno")
        axes[3].set_title("|A - B|  frames")
        plt.colorbar(d, ax=axes[3], fraction=.046)
        for ax in axes:
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"{roi} [{note}] -- winner field, shipped vs ramp-free operator "
                     f"(simulation on 21 frames, no regulariser, no gate)", fontsize=13)
        fig.tight_layout()
        p = PICS / f"SIMFIX-{roi}.png"
        fig.savefig(p, dpi=100); plt.close(fig)
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
