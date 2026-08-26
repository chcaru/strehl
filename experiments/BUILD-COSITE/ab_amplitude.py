"""Amplitude ratio between two renders of the same scene, per channel, per band.

The two arms differ by exactly one operation, so the ratio of their amplitude
spectra IS the ratio of the transfer functions applied -- the scene, the merge
decisions, the exposure and the colour matrix all cancel. Nothing here needs an
edge, a slant or a target.

Both arms MUST be linear-light renders. The colour space is read out of the
TIFF's own ImageDescription and asserted, because an sRGB transfer curve moves
every ratio a metric computes and this project has already burned an agent on
that assumption.

The co-site is a shift on BOTH axes, so the quantity BUILD-SHARP tabulates as
"2-D" is m(f) on x times m(f) on y -- i.e. the transfer at the 2-D frequency
(fx, fy) = (f, f), not at radius f. This measures exactly there, averaging the
four sign-symmetric copies (+/-f, +/-f) since |m| is even on each axis.

Usage: python ab_amplitude.py BEFORE.tif AFTER.tif
"""

import sys

import numpy as np
import tifffile

BANDS = [0.25, 0.35, 0.50]
# Half-width of the averaging box around each (+/-f, +/-f), in cycles/px.
HALF = 0.008
# Central crop side, in pixels. A power of two keeps the FFT honest and cheap.
CROP = 2048


def load_linear(path: str) -> np.ndarray:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        tag = page.tags.get("ImageDescription")
        desc = tag.value if tag is not None else ""
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}, expected uint16"
    assert arr.ndim == 3 and arr.shape[2] == 3, f"{path}: shape {arr.shape}"
    # ASSERT THE COLOUR SPACE BEFORE COMPUTING ANY DN.
    #
    # Two linear spaces are acceptable and they are NOT interchangeable for
    # this measurement. "Linear sRGB" has had the camera matrix applied, and
    # that matrix MIXES CHANNELS -- output green is a weighted sum of all three
    # camera planes, with negative off-diagonal terms. Measuring a per-plane
    # transfer function through it reports green moving when green was never
    # touched. Camera-native is the space in which the three planes are still
    # independent, so it is the only one in which the green placebo means
    # anything. Both are accepted; which one was read is printed.
    if desc.startswith("Linear camera-native RGB"):
        space = "camera-native (planes independent -- green placebo is valid)"
    elif desc.startswith("Linear sRGB:"):
        space = "linear sRGB (MATRIXED -- green is a mix; placebo is NOT valid)"
    else:
        raise AssertionError(
            f"{path}: refusing to measure amplitude in a non-linear space.\n"
            f"  ImageDescription began: {desc[:90]!r}"
        )
    assert "transfer curve" in desc and "NO transfer curve" in desc.upper(), (
        f"{path}: transfer curve present"
    )
    print(f"  space  {path}: {space}")
    return arr


def central(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    y0, x0 = (h - CROP) // 2, (w - CROP) // 2
    assert y0 >= 0 and x0 >= 0, f"image {w}x{h} is smaller than the {CROP} crop"
    return arr[y0 : y0 + CROP, x0 : x0 + CROP, :].astype(np.float64)


def spectrum(plane: np.ndarray) -> np.ndarray:
    """Amplitude spectrum of one plane, Hann-windowed on both axes."""
    win = np.hanning(plane.shape[0])[:, None] * np.hanning(plane.shape[1])[None, :]
    return np.abs(np.fft.fft2((plane - plane.mean()) * win))


def band_power(spec: np.ndarray, f: float) -> float:
    """Mean power in boxes around the four (+/-f, +/-f) corners."""
    n = spec.shape[0]
    freqs = np.fft.fftfreq(n)
    total, count = 0.0, 0
    for sy in (+1, -1):
        for sx in (+1, -1):
            my = np.abs(freqs - sy * f) <= HALF
            mx = np.abs(freqs - sx * f) <= HALF
            box = spec[np.ix_(my, mx)]
            total += float(np.sum(box.astype(np.float64) ** 2))
            count += box.size
    assert count > 0, f"no bins within {HALF} of f={f}"
    return total / count


def main() -> None:
    before_path, after_path = sys.argv[1], sys.argv[2]
    before = central(load_linear(before_path))
    after = central(load_linear(after_path))
    assert before.shape == after.shape

    print(f"BEFORE {before_path}")
    print(f"AFTER  {after_path}")
    print(f"crop   {CROP}x{CROP} centred, Hann windowed, linear light asserted")
    print()

    names = ["R", "G", "B"]
    ident = []
    for c, name in enumerate(names):
        same = np.array_equal(
            before[:, :, c].astype(np.uint64), after[:, :, c].astype(np.uint64)
        )
        ident.append(same)
        print(f"  plane {name}: identical over the crop = {same}")
    print()

    print("  amplitude ratio AFTER/BEFORE at the 2-D frequency (f, f)")
    print("  chan     f=0.25    f=0.35    f=0.50")
    out = {}
    for c, name in enumerate(names):
        sb = spectrum(before[:, :, c])
        sa = spectrum(after[:, :, c])
        row = []
        for f in BANDS:
            pb, pa = band_power(sb, f), band_power(sa, f)
            row.append(np.sqrt(pa / pb))
        out[name] = row
        print(f"  {name:>4}   " + "  ".join(f"{v:8.4f}" for v in row))
    return out


if __name__ == "__main__":
    main()
