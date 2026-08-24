"""Measure the band-limited detail metric on one named ROI, and build a
side-by-side so the number and the picture are checked against each other.

The whole-image tile median can wash out a strong local effect, and an eye can
invent one. Neither is trusted here without the other.

Usage: roi_check.py <ref.tif> <test.tif> <x> <y> <w> <h> <out_prefix>
"""

import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter


def gray(a: np.ndarray) -> np.ndarray:
    if a.ndim == 3:
        return a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def band(g: np.ndarray) -> np.ndarray:
    return gaussian_filter(g, 1.0) - gaussian_filter(g, 4.0)


def main() -> None:
    ref_p, test_p = sys.argv[1], sys.argv[2]
    x, y, w, h = (int(v) for v in sys.argv[3:7])
    prefix = sys.argv[7]

    ra = tifffile.imread(ref_p)[y : y + h, x : x + w]
    ta = tifffile.imread(test_p)[y : y + h, x : x + w]
    gr, gt = gray(ra), gray(ta)

    for name, g in (("ref ", gr), ("test", gt)):
        b = band(g)
        print(
            f"{name}: mean {g.mean():9.1f}  band-rms {np.sqrt((b**2).mean()):9.3f}  "
            f"norm {np.sqrt((b**2).mean())/g.mean():.6f}  "
            f"p99|band| {np.percentile(np.abs(b),99):8.2f}"
        )
    br, bt = band(gr), band(gt)
    nr = np.sqrt((br**2).mean()) / gr.mean()
    nt = np.sqrt((bt**2).mean()) / gt.mean()
    print(f"ratio test/ref = {nt/nr:.4f}")

    # Multi-scale: which spatial octave, if any, moved.
    print(f"\n{'sigma pair':>14} {'ref':>10} {'test':>10} {'ratio':>8}")
    for s1, s2 in ((0.6, 1.2), (1.0, 2.0), (1.5, 3.0), (2.5, 5.0), (4.0, 8.0), (6.0, 12.0)):
        b1 = gaussian_filter(gr, s1) - gaussian_filter(gr, s2)
        b2 = gaussian_filter(gt, s1) - gaussian_filter(gt, s2)
        e1 = np.sqrt((b1**2).mean()) / gr.mean()
        e2 = np.sqrt((b2**2).mean()) / gt.mean()
        print(f"{s1:5.1f}-{s2:<8.1f} {e1:10.6f} {e2:10.6f} {e2/e1:8.4f}")

    def to8(a: np.ndarray) -> np.ndarray:
        return (a.astype(np.float32) / 65535.0 * 255.0).clip(0, 255).astype(np.uint8)

    pair = np.concatenate([to8(ra), to8(ta)], axis=1)
    Image.fromarray(pair).save(f"{prefix}-sidebyside.png")
    d = np.abs(gr - gt)
    dn = (d / max(d.max(), 1e-9) * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(dn).save(f"{prefix}-absdiff.png")
    print(f"\nabs diff: mean {d.mean():.1f} max {d.max():.1f} (of 65535)")
    print(f"wrote {prefix}-sidebyside.png and {prefix}-absdiff.png")


if __name__ == "__main__":
    main()
