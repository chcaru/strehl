"""S10 — the deliverable figure, rebuilt.

S6's figure was honest but hard to read: it showed a 0.25 px effect at 1:1, and
the two rows collided. This rebuilds it with three changes, none of which touch
what is measured:

  * a tighter crop shown at 4x nearest-neighbour, because a quarter-pixel
    effect is not legible at 1:1 and nearest-neighbour magnification adds no
    interpolation of its own;
  * a third column carrying the DEMOSAICED reference, box-averaged to the same
    grid. It is the independent standard both renders are being scored against
    in `s6_shipped.py`, so putting it on the page lets the eye check the same
    thing the number checks -- which render is closer to correct;
  * the crop is still chosen by GREEN gradient energy alone, blind to the
    effect, and the search now also requires the region to be in focus, since a
    defocused edge has no fringe to show either way.

No sharpness number appears on any panel. Sharpness was not measured on this
axis and this figure makes no claim about it.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402
from s4_benefit import box2  # noqa: E402

OUT = r"C:\dev\strehl-out\M95-chroma-cositing"
CROP = 96
ZOOM = 5


def main():
    before = tifffile.imread(os.path.join(OUT, "ship-before-Z.tif")).astype(np.float64)
    after = tifffile.imread(os.path.join(OUT, "ship-after.tif")).astype(np.float64)
    demo = tifffile.imread(os.path.join(OUT, "ship-demosaic.tif")).astype(np.float64)
    ref = np.stack([box2(demo[:, :, c]) for c in range(3)], axis=2)
    del demo
    h, w = before.shape[0], before.shape[1]

    # -------- crop selection: GREEN only, so it cannot see the effect --------
    g = before[:, :, 1]
    best, bxy = -1.0, (0, 0)
    for y in range(300, h - CROP - 300, 48):
        for x in range(300, w - CROP - 300, 48):
            t = g[y:y + CROP, x:x + CROP]
            gy, gx = np.gradient(t)
            # Gradient energy AND local contrast: a defocused region can have a
            # high mean gradient from noise alone and has no fringe to show.
            score = float(np.mean(np.hypot(gy, gx))) * float(t.std())
            if score > best:
                best, bxy = score, (y, x)
    y, x = bxy
    print("crop (%d, %d) size %d, green score %.3g  [selection used green only]"
          % (y, x, CROP, best))

    cb = before[y:y + CROP, x:x + CROP, :]
    ca = after[y:y + CROP, x:x + CROP, :]
    cr = ref[y:y + CROP, x:x + CROP, :]

    lo = float(np.percentile(cb / 65535.0, 1.0))
    hi = float(np.percentile(cb / 65535.0, 99.0))

    def zoom(a):
        return np.repeat(np.repeat(a, ZOOM, axis=0), ZOOM, axis=1)

    def show(t):
        return zoom(np.clip((t / 65535.0 - lo) / max(hi - lo, 1e-9), 0, 1))

    def chroma(t, gain=5.0):
        v = t / 65535.0
        o = np.full_like(v, 0.5)
        o[:, :, 0] = 0.5 + gain * (v[:, :, 0] - v[:, :, 1])
        o[:, :, 2] = 0.5 + gain * (v[:, :, 2] - v[:, :, 1])
        return zoom(np.clip(o, 0, 1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 3, figsize=(15.0, 11.0))
    fig.patch.set_facecolor("white")
    cols = [
        (cb, "A   BEFORE", "binned render as shipped"),
        (ca, "B   AFTER", "binned render, chroma co-sited"),
        (cr, "C   REFERENCE", "demosaiced render, box-averaged"),
    ]
    fig.subplots_adjust(hspace=0.22)
    for i, (img, t1, t2) in enumerate(cols):
        a = ax[0][i]
        a.imshow(show(img), interpolation="nearest")
        a.set_title("%s\n%s" % (t1, t2), fontsize=12, loc="left", fontweight="bold")
        a.set_xticks([])
        a.set_yticks([])
        a = ax[1][i]
        a.imshow(chroma(img), interpolation="nearest")
        a.set_title("%s   chroma only, 5x\nluminance removed, 5x gain"
                    % "DEF"[i], fontsize=12, loc="left", fontweight="bold")
        a.set_xticks([])
        a.set_yticks([])

    fig.suptitle(
        "M95  -  chroma co-siting on strehl's binned sRGB render\n"
        "strehl stack bee-3-cpl --gate 2.0 --srgb   |   %d x %d px crop at %dx nearest neighbour   |   "
        "crop chosen by GREEN gradient alone, blind to the effect"
        % (CROP, CROP, ZOOM),
        fontsize=13, y=0.985,
    )
    fig.text(
        0.5, 0.028,
        "In a 2x2 RGGB quad the two greens straddle the centre, but red sits at one corner and blue at the "
        "opposite one. Writing all three\n"
        "into a single binned pixel as if they were co-sited leaves red and blue half a binned pixel apart on "
        "the diagonal. B resamples red by\n"
        "+0.25 px and blue by -0.25 px onto green's grid. Measured over the whole frame against C: red "
        "misregistration 0.582 -> 0.049 binned px,\n"
        "blue 0.456 -> 0.031, chroma RMS at edges 1286 -> 420 DN. No sharpness number is claimed here; "
        "sharpness was not measured on this axis.",
        ha="center", fontsize=9.5, color="0.2", family="monospace",
    )
    fig.tight_layout(rect=[0, 0.085, 1, 0.925], h_pad=3.0)
    path = os.path.join(OUT, "M95-chroma-cositing-before-after.png")
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote %s" % path)
    C.jdump("s10_figure.json", {"crop": [int(y), int(x)], "size": CROP,
                                "zoom": ZOOM, "green_score": best, "path": path})
    return 0


if __name__ == "__main__":
    sys.exit(main())
