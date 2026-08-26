"""Chroma error energy, total and high-frequency, on a linear render.

`chroma_shift.py` asks whether a plane MOVED. This asks whether it got WORSE.
They are different questions and on the demosaiced path only the second one has
a useful answer: Malvar-He-Cutler rebuilds red at three of every four sites out
of the green gradient, so mis-siting the sparse red samples does not translate
the reconstructed plane -- it injects error into it.

The statistic is the standard deviation of the colour-difference planes R-G and
B-G, in linear light, over a central crop. Colour differences are the quantity a
demosaic is built to keep small and they are near-constant across a real edge,
so a rise in their high-frequency energy is exactly the "colour fringe on every
luminance edge" failure mode.

Reported twice: over all frequencies, and restricted to |f| > HF_MIN on each
axis, which is where a quarter-pixel siting error lives.

Usage: python chroma_error.py A.tif B.tif [...]
"""

import sys

import numpy as np
import tifffile

CROP = 2048
HF_MIN = 0.20


def load(path: str) -> np.ndarray:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        desc = page.tags["ImageDescription"].value
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}"
    # ASSERT THE COLOUR SPACE. A colour difference is only meaningful in linear
    # light; through a transfer curve R-G is a function of exposure.
    assert "no transfer curve" in desc.lower(), f"{path}: not a linear render"
    h, w = arr.shape[:2]
    y0, x0 = (h - CROP) // 2, (w - CROP) // 2
    return arr[y0 : y0 + CROP, x0 : x0 + CROP, :].astype(np.float64)


def hf_energy(plane: np.ndarray) -> float:
    win = np.hanning(plane.shape[0])[:, None] * np.hanning(plane.shape[1])[None, :]
    spec = np.abs(np.fft.fft2((plane - plane.mean()) * win)) ** 2
    f = np.fft.fftfreq(plane.shape[0])
    mask = (np.abs(f)[:, None] > HF_MIN) | (np.abs(f)[None, :] > HF_MIN)
    return float(np.sqrt(spec[mask].sum() / mask.sum()))


def main() -> None:
    rows = []
    for path in sys.argv[1:]:
        c = load(path)
        r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
        rows.append((path, np.std(r - g), np.std(b - g),
                     hf_energy(r - g), hf_energy(b - g)))

    print(f"central {CROP}x{CROP}, linear light asserted, HF is |f| > {HF_MIN} cyc/px")
    print()
    print(f"{'render':<52}  {'sd(R-G)':>9} {'sd(B-G)':>9} {'HF(R-G)':>10} {'HF(B-G)':>10}")
    for path, a, bb, c, d in rows:
        print(f"{path.rsplit(chr(92), 1)[-1]:<52}  {a:9.1f} {bb:9.1f} {c:10.1f} {d:10.1f}")
    if len(rows) == 2:
        print()
        print("ratio second/first:")
        for i, name in enumerate(["sd(R-G)", "sd(B-G)", "HF(R-G)", "HF(B-G)"], start=1):
            print(f"   {name:<10} {rows[1][i] / rows[0][i]:.4f}")


if __name__ == "__main__":
    main()
