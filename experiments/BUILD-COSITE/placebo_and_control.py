"""The green placebo, and the fold's own cost, on camera-native planes.

Runs on the pair of BYTE-FROZEN renders (`stack ... -o x.tif`, no colour flag),
which are linear camera-native: three independent planes, no matrix, so a
per-plane statement means what it says. The binned `--linear-srgb` render cannot
serve here because its matrix mixes all three planes into every output channel.

Two things are measured.

1. THE PLACEBO. Green must be bit-identical between the two arms. Only the R and
   B gather transforms were touched, so any green difference at all means
   something moved that was not meant to. Asserted by SHA-256 of the plane
   bytes, not by eye and not by a tolerance.

2. THE FOLD'S OWN COST. Neither arm co-sites (the byte-frozen path never calls
   `write_binned`), so AFTER/BEFORE on R and B here isolates exactly one thing:
   what adding a constant 0.25 px to an already-large-phase gather costs. This
   is BUILD-SHARP's "folding is free" control, which it computed from a phase
   histogram and predicted at 0.9942 / 0.9800 / 0.9471.

3. THE SERIAL STAGE, on the same real pixels: the co-site kernel from
   `image_out.rs` applied here in numpy, so the amplitude it removes is measured
   rather than assumed.

Usage: python placebo_and_control.py SERIAL.tif FOLD.tif
"""

import hashlib
import sys

import numpy as np
import tifffile

BANDS = [0.25, 0.35, 0.50]
HALF = 0.008
CROP = 2048
SHARP_CONTROL = {0.25: 0.9942, 0.35: 0.9800, 0.50: 0.9471}


def keys_weights(t: float) -> np.ndarray:
    """`image_out.rs::keys_weights`, transcribed."""
    a = -0.5
    t2, t3 = t * t, t * t * t
    return np.array(
        [
            a * (t3 - 2.0 * t2 + t),
            (a + 2.0) * t3 - (a + 3.0) * t2 + 1.0,
            -(a + 2.0) * t3 + (2.0 * a + 3.0) * t2 - a * t,
            -a * (t3 - t2),
        ]
    )


def resample_shift(plane: np.ndarray, d: float) -> np.ndarray:
    """`image_out.rs::resample_shift` with dy = dx = d, border-clamped."""
    w = keys_weights(d - np.floor(d))
    base = int(np.floor(d))
    h, wd = plane.shape
    tmp = np.zeros_like(plane)
    xs = np.arange(wd)
    for k in range(4):
        j = np.clip(xs + base + k - 1, 0, wd - 1)
        tmp += w[k] * plane[:, j]
    out = np.zeros_like(plane)
    ys = np.arange(h)
    for k in range(4):
        i = np.clip(ys + base + k - 1, 0, h - 1)
        out += w[k] * tmp[i, :]
    return out


def load(path: str) -> np.ndarray:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        tag = page.tags.get("ImageDescription")
        desc = tag.value if tag is not None else ""
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}, expected uint16"
    # ASSERT THE COLOUR SPACE BEFORE COMPUTING ANY DN. This measurement is only
    # valid where the three planes are independent, i.e. before the matrix.
    assert desc.startswith("Linear camera-native RGB"), (
        f"{path}: needs the byte-frozen camera-native render; got {desc[:90]!r}"
    )
    return arr


def central(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    y0, x0 = (h - CROP) // 2, (w - CROP) // 2
    return arr[y0 : y0 + CROP, x0 : x0 + CROP, :].astype(np.float64)


def spectrum(plane: np.ndarray) -> np.ndarray:
    win = np.hanning(plane.shape[0])[:, None] * np.hanning(plane.shape[1])[None, :]
    return np.abs(np.fft.fft2((plane - plane.mean()) * win))


def band_power(spec: np.ndarray, f: float) -> float:
    n = spec.shape[0]
    freqs = np.fft.fftfreq(n)
    total, count = 0.0, 0
    for sy in (+1, -1):
        for sx in (+1, -1):
            box = spec[np.ix_(np.abs(freqs - sy * f) <= HALF,
                              np.abs(freqs - sx * f) <= HALF)]
            total += float(np.sum(box.astype(np.float64) ** 2))
            count += box.size
    return total / count


def ratio(before: np.ndarray, after: np.ndarray) -> list:
    sb, sa = spectrum(before), spectrum(after)
    return [np.sqrt(band_power(sa, f) / band_power(sb, f)) for f in BANDS]


def main() -> None:
    a_path, b_path = sys.argv[1], sys.argv[2]
    a, b = load(a_path), load(b_path)
    assert a.shape == b.shape

    print(f"SERIAL {a_path}   {a.shape}")
    print(f"FOLD   {b_path}   {b.shape}")
    print("space  linear camera-native (no matrix -- planes are independent)")
    print()

    print("1. THE PLACEBO -- SHA-256 of each full plane's bytes")
    names = ["R", "G", "B"]
    for c, name in enumerate(names):
        ha = hashlib.sha256(np.ascontiguousarray(a[:, :, c]).tobytes()).hexdigest()
        hb = hashlib.sha256(np.ascontiguousarray(b[:, :, c]).tobytes()).hexdigest()
        verdict = "IDENTICAL" if ha == hb else "MOVED"
        print(f"   {name}  serial {ha[:16]}  fold {hb[:16]}   {verdict}")
    g_same = np.array_equal(a[:, :, 1], b[:, :, 1])
    print(f"   green bit-identical over the whole plane: {g_same}")
    print()

    ca, cb = central(a), central(b)
    print("2. THE FOLD'S OWN COST -- amplitude ratio FOLD/SERIAL at (f, f)")
    print("   (neither arm co-sites; this is the added-0.25-phase control)")
    print("   chan     f=0.25    f=0.35    f=0.50")
    for c, name in enumerate(names):
        r = ratio(ca[:, :, c], cb[:, :, c])
        print(f"   {name:>4}   " + "  ".join(f"{v:8.4f}" for v in r))
    print("   pred     " + "  ".join(f"{SHARP_CONTROL[f]:8.4f}" for f in BANDS)
          + "   <- BUILD-SHARP's predicted control")
    print()

    print("3. THE SERIAL CO-SITE STAGE, measured on these same real pixels")
    print("   (image_out.rs's own Keys kernel, applied here; ratio shifted/plain)")
    print("   chan     f=0.25    f=0.35    f=0.50")
    for c, name, d in ((0, "R", +0.25), (2, "B", -0.25)):
        plain = ca[:, :, c]
        r = ratio(plain, resample_shift(plain, d))
        print(f"   {name:>4}   " + "  ".join(f"{v:8.4f}" for v in r))
    print("   exact  " + "  ".join(
        f"{abs(np.sum(keys_weights(0.25) * np.exp(-2j * np.pi * f * (np.arange(4) - 1)))) ** 2:8.4f}"
        for f in BANDS) + "   <- closed form m(f)^2")
    print()

    print("4. THE COMPOSED ANSWER -- what the fold buys on the binned path")
    print("   fold/serial = (fold's own cost) / (co-site's cost)")
    print("   chan     f=0.25    f=0.35    f=0.50")
    for c, name, d in ((0, "R", +0.25), (2, "B", -0.25)):
        own = ratio(ca[:, :, c], cb[:, :, c])
        cos = ratio(ca[:, :, c], resample_shift(ca[:, :, c], d))
        print(f"   {name:>4}   " + "  ".join(f"{own[i] / cos[i]:8.4f}" for i in range(3)))
    print("   pred     1.1280    1.4384    2.0038   <- BUILD-SHARP's prediction")


if __name__ == "__main__":
    main()
