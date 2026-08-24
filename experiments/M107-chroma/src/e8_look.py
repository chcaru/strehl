"""Render WHERE e8 measured, before any e8 number is quoted.

The auto ROI selector maximises fringe score, which is exactly what a
large-radius corner does under lateral CA. It landed at y0=8 -- the top edge
of the frame. The orchestrator's claim is about BEE HAIRS. If the ROI is not
on bee hair, K2 scores the wrong thing with full apparent precision.

This file renders the frame with the ROI box drawn and 1:1 crops of all three
arms, so the question is settled by looking rather than by argument.
"""
import os
import sys

import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT  # noqa: E402
from e8_kernel import KDIR, ARMS, REF, S, hp  # noqa: E402

FIG = os.path.join(OUT, "fig")


def main(x0, y0, tag):
    img = tifffile.imread(os.path.join(KDIR, f"bee-3-cpl-{REF}.tif"))
    H, W = img.shape[:2]
    small = img[::8, ::8].astype(np.float64) / 65535.0

    fig = plt.figure(figsize=(15, 7.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[2.4, 1, 1, 1])

    ax = fig.add_subplot(gs[:, 0])
    ax.imshow(np.clip(small, 0, 1))
    ax.add_patch(Rectangle((x0 / 8, y0 / 8), S / 8, S / 8,
                           ec="#00ff00", fc="none", lw=2))
    ax.plot([W / 16], [H / 16], "+", color="#00ffff", ms=14, mew=2)
    r = np.hypot(x0 + S / 2 - W / 2, y0 + S / 2 - H / 2)
    ax.set_title(f"bee-3-cpl catmull-rom, 1:8 decimated, sRGB as-rendered (no stretch)\n"
                 f"green = E8 ROI {S}x{S} at ({x0},{y0}); cyan + = frame centre; "
                 f"ROI centre r = {r:.0f} px", fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])

    C = 220
    cy, cx = y0 + S // 2, x0 + S // 2
    for j, a in enumerate(ARMS):
        im = tifffile.imread(os.path.join(KDIR, f"bee-3-cpl-{a}.tif"))
        c = im[cy - C // 2:cy + C // 2, cx - C // 2:cx + C // 2]
        c = c.astype(np.float64) / 65535.0
        del im
        a1 = fig.add_subplot(gs[0, j + 1])
        a1.imshow(np.clip(c, 0, 1), interpolation="nearest")
        a1.set_title(f"{a}\n1:1, {C}x{C} px, NO stretch", fontsize=8)
        a1.set_xticks([]); a1.set_yticks([])

        # chroma view: HIGH-PASSED (sigma 6 px, the same operator E8's statistic
        # uses) then 25x gain about neutral. The high-pass is essential: the
        # first version of this panel showed raw (R-G, ., B-G) and rendered the
        # wing's overall warm cast as a saturated orange field, i.e. it showed
        # SUBJECT CHROMATICITY, not fringing. DIAGNOSTIC STRETCH.
        g = c[..., 1]
        d = np.stack([hp(c[..., 0] - g), np.zeros_like(g), hp(c[..., 2] - g)], -1)
        a2 = fig.add_subplot(gs[1, j + 1])
        a2.imshow(np.clip(0.5 + 25.0 * d, 0, 1), interpolation="nearest")
        a2.set_title(f"{a}: HP(R-G) / HP(B-G), sigma=6 px\n"
                     f"DIAGNOSTIC STRETCH 25x about 0.5 grey", fontsize=8)
        a2.set_xticks([]); a2.set_yticks([])

    fig.suptitle("M107 fig6 -- WHERE E8 measured. Top: as rendered, no stretch. "
                 "Bottom: high-passed chroma at 25x diagnostic gain "
                 "(magenta = R>G, green = G>R, yellow = G>B, blue = B>G).",
                 fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(FIG, f"M107-fig6-kernel-roi-{tag}.png")
    fig.savefig(p, dpi=125)
    print("wrote", p)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
