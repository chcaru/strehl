"""
b7_magenta.py -- why does a RED rim look PINK-MAGENTA?

b3b established, in the byte-frozen camera-native linear output, that the
coffee-bean rim is red-only: R/G +1.43%, B/G +0.00%. Axial CA cannot make that
(it would need blue at roughly 45% of red on this stack, since dB/dR = 0.60),
and the same rim is present in a SINGLE unstacked frame, which axial CA also
cannot do. So in the space where the physics lives, the defect is not magenta
and not axial.

But rule 7 says: if the pictures and the number disagree, the pictures are
right. The picture is magenta. So the number and the picture must be reconciled,
not one of them discarded. The reconciliation has to happen somewhere between
the measurement output and the gallery JPEG, and there are exactly three
candidate stages:

    camera-native linear, binned      <- b3b measured here, red-only
      + camera colour matrix          -> --linear-srgb --binned
      + Malvar-He-Cutler demosaic     -> --linear-srgb (full res)
      + sRGB transfer curve           -> --srgb, i.e. the gallery

This walks that ladder one stage at a time and measures the same rim statistic
at every rung, so the magenta can be attributed to a named stage rather than to
"the pipeline". The gallery JPEG is measured after linearising it back through
the inverse sRGB EOTF, so that the ratios compared across rungs are ratios of
linear light in every case and the curve's non-linearity is not silently
folded into the comparison.

The expected mechanism, stated in advance so it can fail: the camera-to-sRGB
matrix has a strongly negative green coefficient in its red row and a negative
green coefficient in its blue row. A local green DEFICIT at the rim therefore
lifts BOTH output red and output blue, converting a camera-space red-only
excess into an output-space red-and-blue excess, which is magenta. If that is
what is happening, the blue excess should appear at the matrix rung and not
before it.
"""
import os
import sys

import numpy as np

from common import OUT, dump
import b3_defects as b3

REND = os.path.join(OUT, "render")
GALLERY = r"C:\dev\strehl-out\gallery"


def srgb_to_linear(x):
    """Inverse sRGB EOTF. x in [0,1]."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def read_jpeg_linear(path):
    """Gallery JPEG -> linear light, float64 HxWx3.

    Rule 1 is about 16-bit TIFFs and PIL; a JPEG is 8-bit by definition so
    there is no silent truncation to guard against here. The dtype is asserted
    anyway, because the cost of asserting is zero and the cost of being wrong
    about it is a retracted result.
    """
    import imageio.v3 as iio
    a = iio.imread(path)
    assert a.dtype == np.uint8, f"expected uint8 JPEG, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] >= 3, f"unexpected shape {a.shape}"
    return srgb_to_linear(a[:, :, :3] / 255.0)


def rim(img, label, nsample=6000):
    h, w = img.shape[:2]
    return b3.rim_report(img, label, w / 2.0, h / 2.0, nsample=nsample)


def run():
    rungs = []

    p = os.path.join(REND, "coffee-bean-merge.tif")
    if os.path.exists(p):
        rungs.append(("1_camera_native_linear_binned", b3.read16(p).astype(np.float64)))

    p = os.path.join(REND, "coffee-bean-linsrgb.tif")
    if os.path.exists(p):
        rungs.append(("2_plus_colour_matrix_binned", b3.read16(p).astype(np.float64)))

    p = os.path.join(REND, "coffee-bean-linsrgb-demosaic.tif")
    if os.path.exists(p):
        rungs.append(("3_plus_demosaic", b3.read16(p).astype(np.float64)))

    p = os.path.join(GALLERY, "coffee-bean.jpg")
    if os.path.exists(p):
        rungs.append(("4_gallery_srgb_relinearised", read_jpeg_linear(p)))

    out = {"rungs": {}}
    for name, img in rungs:
        print(f"-- {name}: {img.shape}")
        r = rim(img, name)
        out["rungs"][name] = r
        print(f"   peak R/G {r['peak_rg_excess']*100:+.2f}%   "
              f"B/G {r['peak_bg_excess']*100:+.2f}%")
    return out


def show(o):
    print("\n===== where does the magenta come from? =====")
    print("Excess of each channel ratio at the rim, in LINEAR light at every rung.")
    print(f"{'rung':<34}{'R/G':>10}{'B/G':>10}{'magenta?':>10}")
    for name, r in o["rungs"].items():
        rg = r["peak_rg_excess"] * 100
        bg = r["peak_bg_excess"] * 100
        mag = "yes" if (rg > 0.5 and bg > 0.5) else "no"
        print(f"{name:<34}{rg:>+9.2f}%{bg:>+9.2f}%{mag:>10}")


if __name__ == "__main__":
    o = run()
    show(o)
    dump("b7_magenta", o)
