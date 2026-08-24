"""Find and characterise the rectangular seams visible in the merged render.

The 100% crop of `bee-3-cpl` shows a rectangular patch whose hair strands do not
continue across its boundary -- a discontinuity, not a softness. That is a much
more damaging defect than the 0.3693 dex high-frequency deficit I have spent the
night on, because it is visible at normal viewing distance and reads as an
obvious error rather than as a soft photograph.

Two questions, in order:
  1. Is it real, or an artefact of my own downscaled strip? Answered by cropping
     at native resolution with no resampling anywhere in the path.
  2. Is it on a REGULAR GRID? A one-off is a bad election at one spot; a grid is
     a structural tiling defect in the merge, and those have very different
     fixes. Answered by projecting horizontal and vertical gradient energy and
     looking for periodic spikes.

The grid search deliberately looks for periodicity rather than for "a big edge",
because a subject full of hair strands is full of big edges. A seam betrays
itself by being STRAIGHT, FULL-LENGTH and EVENLY SPACED, which the subject's own
structure is not.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\ORCH-gallery"


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def seam_profile(y, axis):
    """Mean |second difference| along `axis`, profiled across the other axis.

    A seam is a step that runs the full length of the image, so it survives
    averaging along its own direction while subject detail averages away.
    Second difference rather than first, because a step's second difference is
    a sharp spike while a smooth shading gradient's is zero.
    """
    d = np.abs(np.diff(y, n=2, axis=axis))
    return d.mean(axis=1 - axis)


def top_peaks(prof, n=12, guard=6):
    """Strongest isolated peaks, measured against a local median baseline."""
    from scipy.ndimage import median_filter
    base = median_filter(prof, size=51)
    ex = prof - base
    sd = float(np.median(np.abs(ex - np.median(ex)))) * 1.4826
    out = []
    work = ex.copy()
    for _ in range(n):
        i = int(np.argmax(work))
        if work[i] <= 0:
            break
        out.append((i, float(ex[i] / sd) if sd > 0 else 0.0))
        work[max(0, i - guard):i + guard + 1] = -np.inf
    return out, sd


def main(stem="bee-3-cpl"):
    src = os.path.join(OUT, f"{stem}-exposed.tif")
    if not os.path.exists(src):
        src = os.path.join(OUT, f"{stem}-srgb.tif")
    print(f"reading {os.path.basename(src)}")
    a = tifffile.imread(src)
    y = luma(a)
    h, w = y.shape
    print(f"shape {a.shape}\n")

    for axis, name in ((0, "horizontal seams (rows)"), (1, "vertical seams (cols)")):
        prof = seam_profile(y, axis)
        peaks, sd = top_peaks(prof)
        print(f"--- {name} ---")
        if not peaks:
            print("  none\n")
            continue
        idx = sorted(p[0] for p in peaks)
        print("  strongest positions: " + ", ".join(str(i) for i in idx))
        print("  strengths (MAD sigma): " +
              ", ".join(f"{s:.1f}" for _, s in sorted(peaks)))
        gaps = np.diff(idx)
        if len(gaps) >= 2:
            print(f"  gaps: {list(gaps)}")
            g = gaps[gaps > 8]
            if len(g) >= 2:
                med = int(np.median(g))
                frac = float(np.mean(np.abs(g - med) <= max(2, 0.05 * med)))
                print(f"  median gap {med} px; {100 * frac:.0f}% of gaps within 5% of it")
                if frac >= 0.6:
                    print(f"  >>> REGULAR GRID at about {med} px <<<")
                else:
                    print("  >>> not periodic: these are isolated, not a tiling <<<")
        print()

    # Native-resolution crop around the centre seam, no resampling at all.
    cy, cx = h // 2, w // 2
    ch, cw = 900, 1400
    c = a[cy - ch // 2:cy + ch // 2, cx - cw // 2:cx + cw // 2]
    p = os.path.join(OUT, f"{stem}-SEAM-100PCT.png")
    Image.fromarray((c >> 8).astype(np.uint8)).save(p)
    print(f"wrote {p}  ({cw}x{ch}, native resolution, no resampling)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"))
