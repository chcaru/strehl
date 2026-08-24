"""Does the render carry the spectral signature of an upsample?

merge_cmd.rs:1245 reports that the field of view is "scaled to 0.9315 so that
EVERY frame covers every pixel (6.9% of width dropped, then upsampled to keep
the output dimensions)". If that is what happens, the output is a 6550-px-wide
image stretched to 7032 px, and EVERY pixel of every render is softened before
anyone looks at it -- unconditionally, isotropically, and independently of
alignment quality, gate, or subject.

That is exactly the kind of loss anisotropy.py is built NOT to see: a uniform
scale is isotropic, and the specificity control proved the anisotropy metric
ignores isotropic blur (it moved 0.0113 under a sigma=1.6 Gaussian). So this
needs its own instrument.

THE SIGNATURE. Upsampling by 1/0.9315 = 1.0735 cannot create detail above the
source's Nyquist. In the OUTPUT's frequency units that ceiling sits at

    0.5 * 0.9315 = 0.4657 cyc/px

so the radially-averaged power spectrum should fall off a cliff there and
contain only interpolation leakage above it. A render that was NOT upsampled has
no reason to show a knee at that particular frequency.

CONTROLS. The prediction names one specific frequency, which is what makes it
falsifiable rather than a Rorschach test:
  - a positive control (deliberately downsample-then-upsample by the same
    factor) must produce a knee at 0.4657;
  - a negative control (the same frame left alone) must not;
  - and the knee location is compared against 0.4657 rather than eyeballed.

Central tiles only: at the centre the residual misregistration is nil (measured
-- anisotropy.py reads A = 1.03 at r = 0.05), so this isolates the isotropic
loss from the radial one.
"""
import sys

import numpy as np
import tifffile

TILE = 256
FOV = 0.9315
PREDICTED_KNEE = 0.5 * FOV


def central_tiles(y, n=64):
    h, w = y.shape
    cy, cx = h // 2, w // 2
    half = int(np.sqrt(n)) // 2 + 1
    out = []
    for i in range(-half, half + 1):
        for j in range(-half, half + 1):
            ty, tx = cy + i * TILE, cx + j * TILE
            if 0 <= ty < h - TILE and 0 <= tx < w - TILE:
                out.append(y[ty:ty + TILE, tx:tx + TILE])
    return out[:n]


def radial_spectrum(tiles):
    f = np.fft.fftfreq(TILE)
    fr = np.sqrt((f[:, None] ** 2) + (f[None, :] ** 2))
    win = np.outer(np.hanning(TILE), np.hanning(TILE))
    acc = np.zeros((TILE, TILE))
    for t in tiles:
        t = t.astype(np.float64)
        acc += np.abs(np.fft.fft2((t - t.mean()) * win)) ** 2
    acc /= len(tiles)
    edges = np.linspace(0.02, 0.5, 60)
    mids, vals = [], []
    for i in range(len(edges) - 1):
        m = (fr >= edges[i]) & (fr < edges[i + 1])
        if m.sum() > 4:
            mids.append((edges[i] + edges[i + 1]) / 2)
            vals.append(acc[m].mean())
    return np.array(mids), np.array(vals)


def knee(mids, vals):
    """Frequency of steepest log-power fall-off above 0.30 cyc/px."""
    lv = np.log10(np.maximum(vals, 1e-30))
    sel = mids >= 0.30
    d = np.gradient(lv[sel], mids[sel])
    return float(mids[sel][int(np.argmin(d))])


def resample_roundtrip(y, fov):
    """Downsample by fov then back up, bilinear -- the operation under test."""
    from scipy.ndimage import zoom
    small = zoom(y.astype(np.float32), fov, order=1)
    return zoom(small, np.array(y.shape) / np.array(small.shape), order=1)


if __name__ == "__main__":
    path = sys.argv[1]
    y = tifffile.imread(path)
    y = (0.2126 * y[:, :, 0] + 0.7152 * y[:, :, 1] + 0.0722 * y[:, :, 2])
    print(f"{path}  {y.shape}")
    print(f"predicted upsample knee at {PREDICTED_KNEE:.4f} cyc/px\n")

    tiles = central_tiles(y)
    m, v = radial_spectrum(tiles)
    k_render = knee(m, v)

    # Positive control: plant the very round trip the log claims happens.
    yy = resample_roundtrip(y, FOV)
    m2, v2 = radial_spectrum(central_tiles(yy))
    k_plant = knee(m2, v2)

    print(f"{'freq':>8} {'render':>12} {'planted RT':>12} {'ratio':>8}")
    for a, b, c in zip(m, v, v2):
        if a > 0.24:
            print(f"{a:>8.4f} {b:>12.4e} {c:>12.4e} {c / b:>8.4f}")

    print()
    print(f"knee, render as shipped        : {k_render:.4f} cyc/px")
    print(f"knee, planted 0.9315 round trip: {k_plant:.4f} cyc/px")
    print(f"predicted                      : {PREDICTED_KNEE:.4f} cyc/px")
    print()
    if abs(k_plant - PREDICTED_KNEE) > 0.05:
        print("POSITIVE CONTROL DID NOT LAND: the planted round trip did not put a")
        print("knee where theory says it must. This instrument cannot be trusted.")
        sys.exit(1)
    print("positive control landed.")
    if abs(k_render - PREDICTED_KNEE) < 0.04:
        print("\nRENDER SHOWS THE UPSAMPLE SIGNATURE.")
    else:
        print("\nRender does NOT show a knee at the predicted frequency.")
        print("The coverage upsample is either not happening as logged, or is")
        print("not the dominant band limit -- do not blame softness on it.")
