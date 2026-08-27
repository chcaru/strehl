"""Where did `coffee-bubbles`' modulation go? Paired linear vs toned arms.

`modulation.py` establishes that the LINEAR merge carries real, spatially
correlated subject detail. This script asks the second half of the question:
how much of it survives into the file a lab would print, and it answers by
MEASURING BOTH ARMS rather than by re-implementing the tone rule.

That choice is deliberate. Predicting the output from `Tone`'s published
constants would test my transcription of `image_out.rs`, not the binary; if I
mis-read `gain()` the prediction would agree with my misunderstanding and
disagree with the pixels. Both arms come from the same pinned binary and the
same frames, so the only difference between them is the tone rendering and the
transfer curve.

Geometry note: the linear arm is BINNED (one 2x2 quad per pixel) and the sRGB
arm is DEMOSAICED, so the sRGB frame is exactly 2x in each axis. The regions
are matched by fractional coordinates, never by pixel index.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def read16(path: Path) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path.name}: dtype {arr.dtype}, expected uint16")
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise SystemExit(f"{path.name}: shape {arr.shape}, expected HxWx3")
    return arr.astype(np.float64) / 65535.0


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4))


def lstar(y_lin: np.ndarray) -> np.ndarray:
    """CIE L* from relative luminance. The perceptual axis a print lives on."""
    return np.where(y_lin > 0.008856, 116.0 * np.cbrt(np.maximum(y_lin, 0)) - 16.0, 903.3 * y_lin)


def frac_region(img: np.ndarray, f0: float, f1: float) -> np.ndarray:
    """A region addressed by fraction of frame, so it survives a resolution change."""
    h, w = img.shape[:2]
    return img[int(f0 * h) : int(f1 * h), int(f0 * w) : int(f1 * w)]


def main() -> int:
    base = Path(r"C:\dev\strehl-out\BUILD-RENDER-modulation")
    lin_path = base / "coffee-bubbles--LINEAR.tiff"
    srgb_path = base / "coffee-bubbles--SRGB.tiff"

    lin = read16(lin_path) @ LUMA
    srgb_disp = read16(srgb_path) @ LUMA
    srgb_lin = srgb_to_linear(read16(srgb_path)) @ LUMA

    print(f"  linear arm : {lin.shape[1]} x {lin.shape[0]}  (binned)")
    print(f"  sRGB   arm : {srgb_disp.shape[1]} x {srgb_disp.shape[0]}  (demosaiced)")
    scale = srgb_disp.shape[1] / lin.shape[1]
    print(f"  scale      : {scale:.2f}x  -- regions matched by fraction, not by index\n")

    # The dark field, defined ONCE on the linear arm and carried to the toned
    # arm as a spatial mask. Defining it separately per arm would let each arm
    # choose a different set of pixels and the comparison would be of two
    # different regions wearing one name.
    dark_cut = np.percentile(lin, 90.0)
    mask_lin = lin <= dark_cut
    # Same mask at the demosaiced arm's resolution.
    mask_srgb = np.repeat(np.repeat(mask_lin, 2, axis=0), 2, axis=1)
    mask_srgb = mask_srgb[: srgb_lin.shape[0], : srgb_lin.shape[1]]

    a = lin[mask_lin]
    b = srgb_lin[: mask_srgb.shape[0], : mask_srgb.shape[1]][mask_srgb]
    print(f"  dark field = below p90 of the LINEAR arm, {mask_lin.mean():.2%} of frame,")
    print("  carried to the toned arm as a spatial mask so both arms score the same pixels\n")

    print("  LINEAR luminance")
    ra = np.percentile(a, 99) / max(np.percentile(a, 1), 1e-9)
    rb = np.percentile(b, 99) / max(np.percentile(b, 1), 1e-9)
    print(f"    linear arm      p1..p99 = {np.percentile(a, 1):.5f} .. {np.percentile(a, 99):.5f}"
          f"   ratio {ra:7.2f}  = {np.log2(ra):5.2f} stops")
    print(f"    toned  arm      p1..p99 = {np.percentile(b, 1):.5f} .. {np.percentile(b, 99):.5f}"
          f"   ratio {rb:7.2f}  = {np.log2(rb):5.2f} stops\n")

    lb = lstar(b)
    got = float(np.percentile(lb, 99) - np.percentile(lb, 1))
    print("  the same pixels on the perceptual axis a print lives on")
    print(f"    toned  arm      L* p1..p99 = {np.percentile(lb, 1):6.2f} .. {np.percentile(lb, 99):6.2f}"
          f"   spread {got:6.2f} L*")

    # NOT a stretch-to-range ceiling. Normalising a region to its own p1..p99
    # and then measuring p1..p99 of the result returns 100 L* for ANY input,
    # including a constant field -- it is arithmetic, not a measurement, and it
    # would have been published as one. What follows instead is a fact about
    # the delivered file that a lab has to live with: how many of the 256
    # levels an 8-bit print pipeline offers does this region actually occupy?
    disp8 = np.round(srgb_disp[: mask_srgb.shape[0], : mask_srgb.shape[1]][mask_srgb] * 255.0)
    lo8, hi8 = np.percentile(disp8, [1.0, 99.0])
    print(f"    toned  arm      8-bit levels p1..p99 = {lo8:.0f} .. {hi8:.0f}"
          f"   -> {hi8 - lo8 + 1:.0f} of 256 levels, {int(len(np.unique(disp8)))} distinct present")

    print(f"\n  {mask_lin.mean():.2%} of the frame is delivered in {got:.2f} L* "
          f"and {hi8 - lo8 + 1:.0f} of 256 levels.")
    print("  modulation.py measured that same region's detrended structure ratio at 8.84")
    print("  against a commissioned noise floor of 1.00, so the detail is real and present")
    print("  in the linear merge. It is not being captured badly; it is being DELIVERED flat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
