"""Downsampled green previews of the reference frame of each stack, with a plane
coordinate grid, so ROIs are chosen by looking rather than by guessing.
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from common import decode, frames, OUT
from edges import green_of

STACKS = [("tweezers-cpl", 50), ("bee-3-cpl", 149), ("leaf-2-cpl", 91),
          ("wrapped-text-1", None)]

fig, axes = plt.subplots(1, len(STACKS), figsize=(4.2 * len(STACKS), 4.0))
for ax, (s, ref) in zip(axes, STACKS):
    fs = frames(s)
    k = ref if ref is not None else len(fs) // 2
    cfa, _, _ = decode(fs[k])
    g = green_of(cfa)                       # plane grid
    d = g[::8, ::8]
    lo, hi = np.percentile(d, 2), np.percentile(d, 99.5)
    ax.imshow(d, cmap="gray", vmin=lo, vmax=hi,
              extent=[0, g.shape[1], g.shape[0], 0])
    ax.set_title(f"{s}  frame {k} of {len(fs)}\ngreen plane {g.shape[1]}x{g.shape[0]}",
                 fontsize=8)
    ax.set_xlabel("plane x (1 plane px = 2 sensel)", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.grid(color="y", alpha=0.4, lw=0.4)
    ax.set_xticks(np.arange(0, g.shape[1], 400))
    ax.set_yticks(np.arange(0, g.shape[0], 400))
fig.suptitle("M107 -- reference-frame previews, PLANE coordinates. "
             "Stretch: green plane, linear, p2-p99.5, 8x decimated (nearest).",
             fontsize=9)
fig.tight_layout(rect=[0, 0, 1, 0.93])
p = os.path.join(OUT, "fig", "M107-preview.png")
fig.savefig(p, dpi=110)
print("wrote", p)
