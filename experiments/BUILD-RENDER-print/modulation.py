"""Does a subject's dark field carry real modulation, or only noise?

ORCH asked the discriminating question for `coffee-bubbles`: the master shows
1.89 L* of modulation across 94.67% of the frame, and that number was measured
AFTER the tone rule. Two hypotheses with opposite consequences:

    RESHOOT   the scene never had modulation, and no code change recovers it.
    RE-RENDER the scene has modulation and the tone rule flattened it.

Telling the owner to re-shoot something a code change would fix costs him a
shoot and returns the same picture, so the two must be separated by measurement
and not by argument.

THE MEASUREMENT
---------------
Measure the *linear* merge output, before the tone rule. `--linear-srgb` is that
tap: `image_out.rs` sets `wants_tone: self.applies_curve()` and a test asserts
`LinearSrgb -> false`, so the render is the colour matrix and nothing else. The
binary says so itself in its banner:

    Order: black, as-shot WB, 2x2 bin, matrix, clamp -- NO transfer curve,
    safe to measure on.

THE DISCRIMINATOR, AND WHY A PLAIN STANDARD DEVIATION WILL NOT DO
-----------------------------------------------------------------
A flat region and a noisy region both have a small spread, and a noisy region
can have a LARGE one. `sigma` alone therefore cannot tell "the scene has
structure" from "the sensor has grain", and reporting it would produce a
confident number that answers neither hypothesis.

So the statistic is a RATIO ACROSS SCALE. Box-average the region by `BLOCK`
and re-measure:

  * uncorrelated noise averages down by `BLOCK` (sqrt of BLOCK**2 samples), so
    sigma_coarse / sigma_fine -> 1 / BLOCK.
  * real structure larger than `BLOCK` px survives averaging untouched, so the
    ratio -> 1.

`structure_ratio` is that quotient expressed against the noise expectation:
1.0 means "indistinguishable from noise", and >> 1.0 means "spatially
correlated signal is present". It is dimensionless and invariant to any linear
gain, which matters because the linear arm carries no exposure -- `--exposure`
and `--auto-exposure` both refuse to run without `--srgb`. A statistic that
moved with exposure could not be compared across arms at all.

COMMISSIONING
-------------
Two arms that must disagree, per the standing rule that a statistic is worth
nothing until something has been planted that it must catch and a null has been
shown not to move it:

  NULL      pure Gaussian noise, no structure -> structure_ratio ~ 1
  PLANT     smooth gradient + the same noise  -> structure_ratio >> 1

If the null scores high the statistic is reading noise as signal; if the plant
scores low it is blind. Either way the subject numbers below mean nothing and
the script refuses to print them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile

# BT.709 luminance weights -- the ones linear sRGB is defined with.
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)

# Side of the box average used to separate correlated structure from grain.
# 16 gives a 256-sample average, so noise falls by 16x and the two hypotheses
# are separated by more than an order of magnitude.
BLOCK = 16

# The "dark field" is everything below this percentile of luminance. The
# question is about the flat majority of the frame, not the few specular
# highlights that set the tone rule's white point.
DARK_PCT = 90.0

# structure_ratio at or below this is consistent with noise alone.
NOISE_LIKE = 2.0


def read_linear(path: Path) -> np.ndarray:
    """Linear-sRGB luminance in [0,1] from a 16-bit RGB TIFF.

    `tifffile`, never `PIL.Image.open`, which silently downconverts a 16-bit
    RGB TIFF to 8 bits and has corrupted results in this project before. The
    dtype and channel count are asserted rather than coerced: a fallback to a
    lossier reader is strictly worse than a hard failure, because it produces a
    number instead of a stack trace.
    """
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path.name}: dtype {arr.dtype}, expected uint16")
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise SystemExit(f"{path.name}: shape {arr.shape}, expected HxWx3")
    return (arr.astype(np.float64) / 65535.0) @ LUMA


def box_down(y: np.ndarray, block: int) -> np.ndarray:
    """Non-overlapping box average, cropping the ragged edge."""
    h, w = (y.shape[0] // block) * block, (y.shape[1] // block) * block
    return y[:h, :w].reshape(h // block, block, w // block, block).mean(axis=(1, 3))


def structure(y: np.ndarray, block: int = BLOCK) -> dict:
    """Separate spatially correlated signal from uncorrelated grain."""
    s_fine = float(y.std())
    s_coarse = float(box_down(y, block).std())
    # Noise alone would fall by exactly `block`; anything above that is
    # structure that survived the average.
    expected_if_noise = s_fine / block
    ratio = s_coarse / expected_if_noise if expected_if_noise > 0 else 0.0
    return {
        "mean": float(y.mean()),
        "sigma_fine": s_fine,
        "sigma_coarse": s_coarse,
        "structure_ratio": ratio,
    }


def dark_field(y: np.ndarray, pct: float = DARK_PCT) -> np.ndarray:
    """The flat majority of the frame, as a masked copy keeping geometry.

    The block average needs the 2-D layout, so the bright tail is replaced by
    the region mean rather than removed -- that is neutral for the mean and can
    only ever REDUCE the measured structure, so it cannot manufacture a
    positive result.
    """
    cut = np.percentile(y, pct)
    mask = y <= cut
    out = y.copy()
    out[~mask] = float(y[mask].mean())
    return out


def contrast_ratio(y: np.ndarray) -> float:
    """p99/p1 of the region: how many times brighter its top is than its floor."""
    lo, hi = np.percentile(y, [1.0, 99.0])
    return float(hi / lo) if lo > 0 else float("inf")


def detrend(y: np.ndarray, scale: int = 128) -> np.ndarray:
    """Remove illumination falloff so only subject-scale detail is left.

    A smooth vignette is spatially correlated and would score as "structure"
    just as a bubble does, so the unqualified ratio cannot distinguish "the
    subject has detail" from "the lens has falloff". Subtracting a box average
    far larger than any subject feature removes the falloff and keeps the
    detail, which turns the statistic into a claim about the SUBJECT.
    """
    coarse = box_down(y, scale)
    # Nearest-neighbour re-expansion is enough: the trend is smooth by
    # construction, and interpolating it would only blur a surface that is
    # already far smoother than the block grid.
    big = np.repeat(np.repeat(coarse, scale, axis=0), scale, axis=1)
    h, w = big.shape
    return y[:h, :w] - big


def stretch_crop(y: np.ndarray, out: Path, size: int = 900) -> dict:
    """Write the dark field stretched to its own range, so it can be judged.

    This project has a documented history of green metrics over bad images, so
    a structure ratio is not allowed to be the last word. Stretching the dark
    field to its OWN p1..p99 shows exactly what a grade could recover: if
    bubbles appear, the modulation is real and was thrown away downstream; if
    mush appears, the number was counting something that is not a picture.
    """
    from PIL import Image  # 8-bit display artifact only, never a measurement

    # Centre the crop on the darkest large region -- the flat majority the
    # 1.89 L* figure was measured over, not the specular highlights.
    coarse = box_down(y, 64)
    yy, xx = np.unravel_index(int(np.argmin(coarse)), coarse.shape)
    cy, cx = yy * 64 + 32, xx * 64 + 32
    half = size // 2
    cy = int(np.clip(cy, half, y.shape[0] - half))
    cx = int(np.clip(cx, half, y.shape[1] - half))
    crop = y[cy - half : cy + half, cx - half : cx + half]

    lo, hi = np.percentile(crop, [1.0, 99.0])
    stretched = np.clip((crop - lo) / (hi - lo), 0.0, 1.0) if hi > lo else np.zeros_like(crop)
    # sRGB encode for viewing only. The measurement above was linear; this is
    # display, and the distinction is the one this project keeps retracting for.
    disp = np.where(
        stretched <= 0.0031308,
        stretched * 12.92,
        1.055 * np.power(np.maximum(stretched, 1e-12), 1 / 2.4) - 0.055,
    )
    Image.fromarray((disp * 255).round().astype(np.uint8), mode="L").save(out)
    return {"centre": (cx, cy), "lo": float(lo), "hi": float(hi)}


def commission(seed: int = 20260826) -> bool:
    """Two arms required to disagree. Returns True if the statistic works."""
    rng = np.random.default_rng(seed)
    h = w = 1024
    noise = rng.normal(0.0, 0.01, size=(h, w))

    # NULL: grain only. Must look like noise.
    null = structure(0.05 + noise)

    # PLANT: a smooth ramp far larger than BLOCK, plus the SAME grain, so the
    # only difference between the arms is the presence of structure.
    ramp = np.linspace(0.0, 0.04, w)[None, :] * np.ones((h, 1))
    plant = structure(0.05 + ramp + noise)

    print("  commissioning the structure statistic (two arms, must disagree)")
    print(f"    NULL   grain only          structure_ratio = {null['structure_ratio']:8.2f}")
    print(f"    PLANT  ramp + same grain   structure_ratio = {plant['structure_ratio']:8.2f}")

    ok_null = null["structure_ratio"] < NOISE_LIKE
    ok_plant = plant["structure_ratio"] > 10.0 * null["structure_ratio"]
    if not ok_null:
        print(f"    FAILED: the null scored {null['structure_ratio']:.2f}, it reads grain as signal")
    if not ok_plant:
        print("    FAILED: the plant did not separate from the null, the statistic is blind")
    if ok_null and ok_plant:
        print(f"    COMMISSIONED: separation {plant['structure_ratio'] / null['structure_ratio']:.0f}x\n")
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tiffs", nargs="+", type=Path, help="linear-sRGB renders to measure")
    ap.add_argument("--block", type=int, default=BLOCK)
    ap.add_argument("--crops", type=Path, default=None, help="write stretched dark-field crops here")
    args = ap.parse_args()

    if not commission():
        print("REFUSING to report subject numbers: the instrument is not commissioned.")
        return 1

    print(f"  linear-sRGB modulation, dark field = below p{DARK_PCT:g}, block {args.block}\n")
    hdr = (
        f"  {'subject':<24} {'mean':>9} {'sig/mean':>9} {'p99/p1':>7} {'stops':>6} "
        f"{'struct':>7} {'detrend':>8}  verdict"
    )
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    if args.crops:
        args.crops.mkdir(parents=True, exist_ok=True)

    for path in args.tiffs:
        y = read_linear(path)
        dk = dark_field(y)
        st = structure(dk, args.block)
        # The same statistic with illumination falloff removed. If this
        # collapses while `struct` stays high, the frame has a vignette and no
        # subject detail, and the unqualified number was measuring the lens.
        dt = structure(detrend(dk), args.block)
        rel = st["sigma_fine"] / st["mean"] if st["mean"] > 0 else 0.0
        cr = contrast_ratio(y[y <= np.percentile(y, DARK_PCT)])
        stops = float(np.log2(cr)) if np.isfinite(cr) and cr > 0 else float("nan")
        verdict = "NOISE ONLY" if dt["structure_ratio"] < NOISE_LIKE else "has detail"
        name = path.stem.replace("--LINEAR", "")
        print(
            f"  {name:<24} {st['mean']:9.5f} {rel:8.1%} {cr:7.2f} {stops:6.2f} "
            f"{st['structure_ratio']:7.2f} {dt['structure_ratio']:8.2f}  {verdict}"
        )
        if args.crops:
            info = stretch_crop(y, args.crops / f"{name}--darkfield-stretched.png")
            print(
                f"    {'':<22} crop at {info['centre']}, "
                f"stretched from linear [{info['lo']:.5f}, {info['hi']:.5f}]"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
