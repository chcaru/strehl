"""S9 — the non-vacuous form of N2, in the space where the claim lives.

N2' in S8 was vacuous: only 1357 of 8.24 M pixels had both red and blue
unchanged, because the correction touches nearly every pixel. The claim it was
trying to make is still the right one, but it has to be made in CAMERA-LINEAR
space, before the matrix mixes the channels, because that is where "green is
untouched" is a statement about my code rather than about the matrix.

The pipeline is invertible on unclipped pixels:

    camera RGB --[matrix M]--> linear sRGB --[sRGB curve]--> 16-bit

so undoing the curve and multiplying by inv(M) recovers camera-linear RGB from
each render, and the green planes of the two must agree. M is reconstructed here
from the XYZ->cam matrix the binary PRINTED during this session's render, by
re-implementing `color::camera_to_srgb` from `color.rs` -- not copied from a
note, and not read back out of the Rust.

Clipped pixels are excluded because clipping is not invertible, and near-black
pixels are excluded because the sRGB curve's slope there is ~12.9, so 16-bit
quantisation alone lands as a large camera-linear swing. Both exclusions are
reported, and both are properties of the instrument rather than of the result.

THE POWER CONTROL IS THE POINT
------------------------------
An inversion this lossy could read "no difference" simply because it is blunt.
So the SAME procedure is run on the red plane, where a large difference is known
to exist. If green reads ~0 and red reads large on identical machinery, the
green null is a measurement. If both read ~0, the instrument is blind and the
null means nothing. This is discipline 594 applied to the inverse pipeline.
"""

import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M95-chroma-cositing"

# PRINTED by this session's render; see after-srgb.tif.log line 85.
XYZ_TO_CAM = np.array([
    [0.7460, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
])
SRGB_TO_XYZ_D65 = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])


def camera_to_srgb(xyz_to_cam):
    """Re-implementation of `color::camera_to_srgb` from color.rs lines 175-212."""
    cam_from_srgb = xyz_to_cam @ SRGB_TO_XYZ_D65
    cam_from_srgb = cam_from_srgb / cam_from_srgb.sum(axis=1, keepdims=True)
    return np.linalg.inv(cam_from_srgb)


def srgb_decode(x):
    """Inverse of `color::srgb_encode`, IEC 61966-2-1."""
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def to_camera_linear(tif, minv):
    v = tif.astype(np.float64) / 65535.0
    lin = srgb_decode(v)
    return lin @ minv.T


def main():
    m = camera_to_srgb(XYZ_TO_CAM)
    minv = np.linalg.inv(m)
    print("camera_to_srgb, reconstructed from the printed characterisation:")
    for r in m:
        print("   [%8.4f %8.4f %8.4f]" % tuple(r))
    print("   condition number %.2f (well inside invertible)" % np.linalg.cond(m))

    z = tifffile.imread(os.path.join(OUT, "ship-before-Z.tif"))
    y = tifffile.imread(os.path.join(OUT, "ship-after.tif"))

    # Sub-sample: 8.2 M px x 3 x float64 twice is more memory than this needs.
    z, y = z[::3, ::3, :], y[::3, ::3, :]

    clipped = (z.min(axis=2) == 0) | (z.max(axis=2) == 65535) \
        | (y.min(axis=2) == 0) | (y.max(axis=2) == 65535)
    dark = (z[:, :, 1] < 3000) | (y[:, :, 1] < 3000)
    good = ~clipped & ~dark
    n = good.size
    print("\nexclusions on %d sampled pixels:" % n)
    print("   clipped in either render : %d (%.2f%%)" % (int(clipped.sum()), 100 * clipped.mean()))
    print("   below 3000 DN green      : %d (%.2f%%)" % (int(dark.sum()), 100 * dark.mean()))
    print("   usable                   : %d (%.2f%%)" % (int(good.sum()), 100 * good.mean()))
    if good.sum() < 100000:
        print("   TOO FEW USABLE PIXELS -- this test would be vacuous")
        return 1

    cz = to_camera_linear(z, minv)
    cy = to_camera_linear(y, minv)
    d = np.abs(cz - cy)

    print("\n== camera-linear differences, on usable pixels ==")
    stats = {}
    for c, nm in enumerate("RGB"):
        v = d[:, :, c][good]
        stats[nm] = (float(np.sqrt(np.mean(v**2))), float(np.percentile(v, 99.9)))
        print("   %s  RMS %.6f   p99.9 %.6f   (camera-linear, full scale = 1.0)"
              % (nm, stats[nm][0], stats[nm][1]))

    gr = stats["G"][0]
    rr = max(stats["R"][0], stats["B"][0])
    ratio = rr / gr if gr > 0 else float("inf")
    print("\n== N2'' and its power control ==")
    print("   green RMS change            : %.6f" % gr)
    print("   largest chroma RMS change   : %.6f  (the power control)" % rr)
    print("   separation                  : %.1fx" % ratio)
    power = rr > 1e-3
    null = ratio > 20.0
    print("   power   (chroma change is detectable) : %s" % ("PASS" if power else "FAIL"))
    print("   N2''    (green is >20x quieter)       : %s" % ("PASS" if null else "FAIL"))

    print("\n   Residual green is NOT expected to be exactly zero here: it is the")
    print("   round trip through a 16-bit sRGB quantisation and a matrix inverse,")
    print("   not the green plane itself. The bit-exact claim is the Rust unit")
    print("   test, which runs with no matrix and is certified by mutation R2.")

    ok = power and null
    print("\nS9: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
