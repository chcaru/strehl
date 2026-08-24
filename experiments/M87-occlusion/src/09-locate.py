"""M87 step 9 -- stop designing instruments and LOOK at where the halo is.

Draws the merged crop with the foreground-mask boundary overlaid in red, and
prints raw horizontal cuts through the visibly haloed edge, so the geometry of
the artifact is established from the image rather than assumed.
"""

import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

SUB = (300, 800, 100, 800)


def stretch(a, lo, hi, gamma=2.2):
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)


def main():
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")

    c = sel[SUB[0]:SUB[1], SUB[2]:SUB[3]]
    m = mask[SUB[0]:SUB[1], SUB[2]:SUB[3]]
    lo, hi = np.percentile(c, (0.5, 99.7))
    v = stretch(c, lo, hi)
    rgb = np.repeat((v * 255).astype(np.uint8)[..., None], 3, axis=2)
    edge = m ^ ndi.binary_erosion(m)
    rgb[edge] = [255, 0, 0]
    Image.fromarray(rgb).save(OUT / "09-overlay.png")

    # amplify the local structure: merge minus a wide median of itself
    med = ndi.median_filter(c, size=61)
    r = c - med
    s = np.clip(r / (0.06 * float(np.median(c))) * 0.5 + 0.5, 0, 1)
    Image.fromarray((s * 255).astype(np.uint8)).save(OUT / "09-residual.png")

    kf = int(np.bincount(argbest[mask]).argmax())
    f = np.asarray(lumas[kf], np.float32)[SUB[0]:SUB[1], SUB[2]:SUB[3]]
    Image.fromarray((stretch(f, lo, hi) * 255).astype(np.uint8)).save(
        OUT / "09-frame-kF.png")
    fmed = ndi.median_filter(f, size=61)
    sf = np.clip((f - fmed) / (0.06 * float(np.median(f))) * 0.5 + 0.5, 0, 1)
    Image.fromarray((sf * 255).astype(np.uint8)).save(OUT / "09-residual-kF.png")

    print(f"k_F = {kf}   stretch lo {lo:.0f} hi {hi:.0f}")
    print("\nraw horizontal cuts through the crop (merge | frame k_F), "
          "crop col -> value")
    for row in (60, 120, 180, 240, 300):
        line_m = c[row]
        line_f = f[row]
        mr = m[row]
        first_bg = int(np.argmax(~mr[np.argmax(mr):]) + np.argmax(mr)) if mr.any() else 0
        print(f"\n  row {row} (box row {SUB[0] + row}), mask ends at crop col {first_bg}")
        cols = range(max(first_bg - 6, 0), min(first_bg + 90, c.shape[1]), 3)
        print("    col : merge   frameKF   ratio")
        for x in cols:
            print(f"    {x:4d}: {line_m[x]:7.1f}  {line_f[x]:7.1f}  "
                  f"{line_m[x] / max(line_f[x], 1):6.3f}")


if __name__ == "__main__":
    main()
