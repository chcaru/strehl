"""Potency check for `chroma_shift.py`, and the demosaic-path question it asks.

An instrument that reports "nothing moved" is indistinguishable from one that
cannot see movement. This plants a KNOWN sub-pixel shift in the red plane of a
real render and checks that the phase-correlation estimator recovers it.

Then it asks the question that matters: on the DEMOSAICED render, does shifting
the underlying R *samples* by half a full-resolution pixel move the *output* R
plane by half a pixel? It does not have to. Malvar-He-Cutler reconstructs R at
the three non-R sites of every quad from a green-gradient correction, so most of
the output R plane is built out of green -- which the fold never touches. A
diluted response is a real property of the demosaic, not a blind instrument, and
these two measurements together are what tell the difference.

Usage: python potency_chroma_shift.py IMAGE.tif
"""

import sys

import numpy as np
import tifffile

sys.path.insert(0, str(__file__.rsplit("\\", 1)[0]))
from chroma_shift import CROP, shift_between  # noqa: E402

PLANTS = [0.0, 0.25, 0.5, 1.0]


def keys_weights(t: float) -> np.ndarray:
    a = -0.5
    t2, t3 = t * t, t * t * t
    return np.array([
        a * (t3 - 2.0 * t2 + t),
        (a + 2.0) * t3 - (a + 3.0) * t2 + 1.0,
        -(a + 2.0) * t3 + (2.0 * a + 3.0) * t2 - a * t,
        -a * (t3 - t2),
    ])


def shift_plane(plane: np.ndarray, d: float) -> np.ndarray:
    """Shift on BOTH axes by d, separable Keys, border-clamped."""
    w = keys_weights(d - np.floor(d))
    base = int(np.floor(d))
    h, wd = plane.shape
    tmp = np.zeros_like(plane)
    xs = np.arange(wd)
    for k in range(4):
        tmp += w[k] * plane[:, np.clip(xs + base + k - 1, 0, wd - 1)]
    out = np.zeros_like(plane)
    ys = np.arange(h)
    for k in range(4):
        out += w[k] * tmp[np.clip(ys + base + k - 1, 0, h - 1), :]
    return out


def main() -> None:
    path = sys.argv[1]
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        desc = page.tags["ImageDescription"].value
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}"
    assert "no transfer curve" in desc.lower(), f"{path}: not linear"

    h, w = arr.shape[:2]
    y0, x0 = (h - CROP) // 2, (w - CROP) // 2
    crop = arr[y0 : y0 + CROP, x0 : x0 + CROP, :].astype(np.float64)
    g = crop[:, :, 1]

    print(f"{path}  ({w}x{h})")
    print("  planted shift of the OUTPUT red plane, both axes -> recovered")
    for d in PLANTS:
        r = shift_plane(crop[:, :, 0], d)
        dy, dx = shift_between(g, r)
        base_dy, base_dx = shift_between(g, crop[:, :, 0])
        print(
            f"    plant {d:+.2f}  ->  dy {dy - base_dy:+.3f}  dx {dx - base_dx:+.3f}"
            f"   (recovered / planted = {((dy - base_dy) / d) if d else float('nan'):.3f})"
        )


if __name__ == "__main__":
    main()
