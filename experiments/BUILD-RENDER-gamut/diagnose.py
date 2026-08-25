"""Where does the negative blue come from?

12% of the pixels of `flower-inner-edge-cpl` land at B < 0 after the colour
matrix and are hard-clamped to zero. A million pixels with a destroyed channel
is a print defect on its own, and the tone fix raised saturation, which pushes
colours further out, not less.

Three candidate causes were named and they demand different fixes:

  * **genuinely out-of-gamut colour** -- the scene contains saturated hues sRGB
    cannot represent. The fix is gamut MAPPING; the colour is real and should be
    brought inside the gamut in a way that preserves hue and relative lightness.
  * **the near-black floor** -- a matrix with negative off-diagonal terms turns
    small, noisy, near-zero camera values into small negative sRGB values. Then
    "12% of pixels are out of gamut" is not a colour statement at all, it is a
    statement about the dark end of the frame, and the fix belongs with the
    black point.
  * **an ordering error** -- white balance, matrix or normalisation applied in
    the wrong place, in which case the number is a bug and not a property of the
    scene.

They are trivially separable, because they live in different places in the
image. This script partitions the negative-blue pixels by how bright they are
and how deep the excursion is, and reports where they actually sit. Run it
before choosing a fix; the choice is not obvious from the 12% alone.

Reads camera-native linear renders (`stack --demosaic`, no `--srgb`), which is
the only honest input: measuring this on an `--srgb` render would be measuring
after the clamp that is under investigation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from crop_set import A7C2_CAM_TO_SRGB  # noqa: E402  (validated port of the Rust)


def read_camera_linear(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}; PIL would have hidden this"
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    return a.astype(np.float32) / 65535.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tiffs", nargs="+", type=Path)
    ap.add_argument("--stride", type=int, default=3, help="subsample for speed")
    a = ap.parse_args()

    m = A7C2_CAM_TO_SRGB.astype(np.float32)
    print("cam -> linear sRGB matrix (rows sum to 1 by construction):")
    for row in m:
        print("   [{:+.4f} {:+.4f} {:+.4f}]  sum {:+.4f}".format(*row, row.sum()))
    print()

    for t in a.tiffs:
        cam = read_camera_linear(t)[:: a.stride, :: a.stride]
        srgb = cam @ m.T
        n = srgb[..., 0].size

        for ci, cname in enumerate("RGB"):
            neg = srgb[..., ci] < 0.0
            if not neg.any():
                print(f"{t.stem:28s} {cname}: none negative")
                continue
            v = srgb[..., ci][neg]
            # How bright is a pixel that goes negative? Use the two channels
            # that did NOT go negative, so the answer is not circular.
            others = [c for c in range(3) if c != ci]
            bright = srgb[..., others][neg].max(axis=-1)
            print(
                f"{t.stem:28s} {cname}: {neg.mean()*100:6.2f}% negative | "
                f"depth p50 {np.percentile(v,50):+.4f} p1 {np.percentile(v,1):+.4f} "
                f"min {v.min():+.4f}"
            )
            # The partition that decides the fix.
            dark = bright < 0.05
            mid = (bright >= 0.05) & (bright < 0.25)
            lit = bright >= 0.25
            print(
                f"{'':28s}    of those, by brightness of the surviving channels: "
                f"dark(<0.05) {dark.mean()*100:5.1f}%  "
                f"mid {mid.mean()*100:5.1f}%  lit(>=0.25) {lit.mean()*100:5.1f}%"
            )
            # Depth relative to the pixel's own magnitude. A genuinely saturated
            # colour goes DEEPLY negative relative to its brightness; a noisy
            # near-black pixel goes negative by a hair.
            rel = -v / np.maximum(bright, 1e-6)
            print(
                f"{'':28s}    |negative| as a fraction of the pixel's brightness: "
                f"p50 {np.percentile(rel,50):.3f}  p90 {np.percentile(rel,90):.3f}  "
                f"p99 {np.percentile(rel,99):.3f}"
            )
            # How much of the frame is out of gamut by an amount that could
            # possibly matter visually?
            for thr in (0.002, 0.01, 0.05):
                frac = (srgb[..., ci] < -thr).mean() * 100
                print(f"{'':28s}    below -{thr:<6}: {frac:6.3f}% of frame")
        # Camera-side sanity: is the input itself sane, or is something upstream
        # producing values that no matrix could rescue?
        print(
            f"{'':28s} camera-native: "
            + "  ".join(
                f"{c} p50 {np.percentile(cam[...,i],50):.4f} p99.9 {np.percentile(cam[...,i],99.9):.4f}"
                for i, c in enumerate("RGB")
            )
        )
        print(f"{'':28s} n sampled: {n}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
