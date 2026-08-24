"""How much resolution is at stake, in the band the eye judges sharpness by.

Two renders of the same merge, same gate, same alignment, same colour: one
binned to 3516 x 2344, one demosaiced to 7032 x 4688. Compare them at the same
displayed size -- the binned one upsampled 2x, which is what a viewer does when
they open it and zoom to match.

The statistic is radially-averaged power of luminance, reported in bands of
full-res cycles/px. The binned grid cannot represent anything above 0.25
cyc/full-res px, so that is the line that matters.

Controls:
  * P1 a defocused background crop: both renders must be near the floor there,
    and any advantage must shrink.
  * P2 the binned render upsampled and then re-downsampled: a round trip that
    provably adds no information, to show the comparison is not just rewarding
    the presence of more pixels.
"""

import json
import os
import sys

import numpy as np
import tifffile

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
REN = r"C:\dev\strehl-out\M95-resolution"


def luma(rgb):
    a = rgb.astype(np.float64) / 65535.0
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def radial_power(img):
    """Radially-averaged power spectrum, x-axis in cycles/px of THIS grid."""
    h, w = img.shape
    n = min(h, w)
    a = img[:n, :n]
    a = a - a.mean()
    win = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    P = np.abs(np.fft.fftshift(np.fft.fft2(a * win))) ** 2
    fy = np.fft.fftshift(np.fft.fftfreq(n))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(n))[None, :]
    r = np.hypot(fy, fx)
    nb = 128
    idx = np.clip((r / 0.5 * nb).astype(int), 0, nb - 1)
    tot = np.bincount(idx.ravel(), P.ravel(), minlength=nb)
    cnt = np.bincount(idx.ravel(), minlength=nb)
    freq = (np.arange(nb) + 0.5) / nb * 0.5
    return freq, tot / np.maximum(cnt, 1)


def upsample2(a):
    """Bilinear 2x upsample. Adds pixels, cannot add information."""
    h, w = a.shape
    y = np.linspace(0, h - 1, h * 2)
    x = np.linspace(0, w - 1, w * 2)
    yi = np.clip(y.astype(int), 0, h - 2)
    xi = np.clip(x.astype(int), 0, w - 2)
    fy = (y - yi)[:, None]
    fx = (x - xi)[None, :]
    a00 = a[np.ix_(yi, xi)]
    a01 = a[np.ix_(yi, xi + 1)]
    a10 = a[np.ix_(yi + 1, xi)]
    a11 = a[np.ix_(yi + 1, xi + 1)]
    return (a00 * (1 - fy) * (1 - fx) + a01 * (1 - fy) * fx
            + a10 * fy * (1 - fx) + a11 * fy * fx)


def band_energy(freq, p, lo, hi):
    m = (freq >= lo) & (freq < hi)
    return float(p[m].sum())


def compare(binned, demo, y, x, n, label):
    """y,x,n in FULL-RES pixel coordinates."""
    d = luma(demo[y:y + n, x:x + n])
    b = luma(binned[y // 2:y // 2 + n // 2, x // 2:x // 2 + n // 2])
    bu = upsample2(b)
    # P2: a round trip through the binned grid, applied to the DEMOSAIC crop.
    # It provably destroys everything above 0.25 cyc/px, so it bounds what the
    # comparison should show if the demosaic advantage were an artifact.
    rt = upsample2(d.reshape(n // 2, 2, n // 2, 2).mean(axis=(1, 3)))

    rows = {}
    for tag, img in (("demosaic", d), ("binned_up", bu), ("P2_roundtrip", rt)):
        f, p = radial_power(img)
        rows[tag] = {
            "low": band_energy(f, p, 0.0, 0.25),
            "high": band_energy(f, p, 0.25, 0.5),
        }
    out = {"label": label, "y": y, "x": x, "n": n, "bands": rows}
    hi_ratio = rows["demosaic"]["high"] / rows["binned_up"]["high"]
    rt_ratio = rows["demosaic"]["high"] / rows["P2_roundtrip"]["high"]
    lo_ratio = rows["demosaic"]["low"] / rows["binned_up"]["low"]
    out.update({"high_ratio": hi_ratio, "roundtrip_ratio": rt_ratio, "low_ratio": lo_ratio})
    print("   %-14s  above 0.25 cyc/px: demosaic/binned %7.2fx   demosaic/roundtrip %7.2fx"
          % (label, hi_ratio, rt_ratio))
    print("                   below 0.25 cyc/px: demosaic/binned %7.3fx  (must be ~1: same picture)"
          % lo_ratio)
    return out


def main():
    binned = tifffile.imread(os.path.join(REN, "ship-binned.tif"))
    demo = tifffile.imread(os.path.join(REN, "ship-demosaic.tif"))
    print("binned  %s\ndemosaic %s\n" % (binned.shape, demo.shape))
    assert demo.shape[0] == binned.shape[0] * 2

    # Crops in full-res coordinates. Subject crops chosen from r0_recon's
    # gradient ranking on the RAW frame -- i.e. before any render existed and
    # blind to this comparison. Background crop is a low-gradient tile.
    crops = [
        ("subject T1", 1024 + 400, 5120 + 400),
        ("subject T3", 2560 + 400, 1024 + 400),
        ("subject T4", 2048 + 400, 1536 + 400),
        ("background", 300, 300),
    ]
    res = []
    print("== spectral comparison, 1024 px full-res crops ==")
    for label, y, x in crops:
        res.append(compare(binned, demo, y, x, 1024, label))

    with open(os.path.join(OUT, "s4_spectral.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
