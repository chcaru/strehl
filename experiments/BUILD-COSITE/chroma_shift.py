"""Chroma misregistration between planes, by phase correlation.

Answers one question: after a change, are red and blue still sitting on top of
green, or has something moved them? Sub-pixel, on real pixels, no target.

Phase correlation gives the rigid displacement that best aligns two planes. The
peak is refined to sub-pixel by a parabolic fit on the three samples straddling
it in each axis, which is the standard estimator and is good to ~0.05 px on
textured data.

Sign convention: a POSITIVE dx means the second plane's content sits at larger
x than the first's, i.e. it must move by -dx to land on it.

Usage: python chroma_shift.py IMAGE.tif [IMAGE2.tif ...]
"""

import sys

import numpy as np
import tifffile

CROP = 1024


def load(path: str):
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        tag = page.tags.get("ImageDescription")
        desc = tag.value if tag is not None else ""
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}, expected uint16"
    # ASSERT THE COLOUR SPACE. A transfer curve is a per-pixel nonlinearity and
    # would bias a correlation between channels of different mean level.
    assert "no transfer curve" in desc.lower(), (
        f"{path}: needs a LINEAR render; got {desc[:90]!r}"
    )
    return arr, desc.split(":")[0]


def parabolic(y0: float, y1: float, y2: float) -> float:
    """Sub-sample offset of the peak of the parabola through three samples."""
    denom = y0 - 2.0 * y1 + y2
    return 0.0 if denom == 0 else 0.5 * (y0 - y2) / denom


def shift_between(a: np.ndarray, b: np.ndarray) -> tuple:
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    fa = np.fft.fft2((a - a.mean()) * win)
    fb = np.fft.fft2((b - b.mean()) * win)
    cross = fa * np.conj(fb)
    mag = np.abs(cross)
    mag[mag == 0] = 1.0
    corr = np.real(np.fft.ifft2(cross / mag))
    peak = np.unravel_index(np.argmax(corr), corr.shape)
    n0, n1 = corr.shape
    py, px = peak
    dy = parabolic(corr[(py - 1) % n0, px], corr[py, px], corr[(py + 1) % n0, px])
    dx = parabolic(corr[py, (px - 1) % n1], corr[py, px], corr[py, (px + 1) % n1])
    wy = py - n0 if py > n0 // 2 else py
    wx = px - n1 if px > n1 // 2 else px
    return (wy + dy, wx + dx)


def main() -> None:
    for path in sys.argv[1:]:
        arr, space = load(path)
        h, w = arr.shape[:2]
        y0, x0 = (h - CROP) // 2, (w - CROP) // 2
        crop = arr[y0 : y0 + CROP, x0 : x0 + CROP, :].astype(np.float64)
        r, g, b = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
        rg = shift_between(g, r)
        bg = shift_between(g, b)
        print(f"{path}   ({w}x{h}, {space})")
        print(f"   R relative to G : dy {rg[0]:+.3f}  dx {rg[1]:+.3f}  px")
        print(f"   B relative to G : dy {bg[0]:+.3f}  dx {bg[1]:+.3f}  px")
        sep = np.hypot(rg[0] - bg[0], rg[1] - bg[1])
        print(f"   R-to-B separation: {sep:.3f} px")


if __name__ == "__main__":
    main()
