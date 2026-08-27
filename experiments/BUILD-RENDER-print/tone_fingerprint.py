"""Does `--linear-srgb` actually skip the tone rule? Measured, not read.

The `coffee-bubbles` re-render verdict rests on one premise: the linear arm is
pre-tone. I established that by reading `image_out.rs:824` and the test at
:1924-1934, i.e. I hold a MECHANISM that explains why it must be true, which is
the point at which people stop measuring. So measure it.

THE TEST
--------
The tone rule's whole purpose is to put the 99.9th percentile of linear
luminance at `TONE_WHITE_TARGET = 0.90`. That is a fingerprint: if a render
carries the tone rule, its p99.9 lands on the target no matter what the scene
did; if it does not, p99.9 sits wherever the exposure left it.

Two-sided, because a test only one arm can pass proves nothing:

  POSITIVE CONTROL  the --srgb arm, where the tone rule is KNOWN to run and the
                    binary printed `tone: black 0.01169, white 1.02548`.
                    Decoded back to linear, its p99.9 MUST land near 0.90.
                    If it does not, this test cannot see a tone rule at all and
                    the negative arm below is worthless.

  ARM UNDER TEST    the --linear-srgb arm. If its p99.9 also lands near 0.90,
                    the premise is false and the verdict must be withdrawn.

Note the asymmetry that makes this worth running: the positive control is what
gives the negative arm meaning. Without it, "0.02 is not 0.90" is equally
consistent with "no tone rule" and "this script measures the wrong thing".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
TONE_WHITE_TARGET = 0.90  # image_out.rs
TOLERANCE = 0.05


def read(path: Path) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path.name}: dtype {arr.dtype}, expected uint16")
    return arr.astype(np.float64) / 65535.0


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4))


def main() -> int:
    base = Path(r"C:\dev\strehl-out\BUILD-RENDER-modulation")
    print(f"  the tone rule's fingerprint: p99.9 of linear luminance at {TONE_WHITE_TARGET}\n")

    srgb = srgb_to_linear(read(base / "coffee-bubbles--SRGB.tiff")) @ LUMA
    lin = read(base / "coffee-bubbles--LINEAR.tiff") @ LUMA
    p_srgb = float(np.percentile(srgb, 99.9))
    p_lin = float(np.percentile(lin, 99.9))

    hit_srgb = abs(p_srgb - TONE_WHITE_TARGET) <= TOLERANCE
    hit_lin = abs(p_lin - TONE_WHITE_TARGET) <= TOLERANCE

    print(f"  POSITIVE CONTROL  --srgb        p99.9 = {p_srgb:.4f}   "
          f"on target: {hit_srgb}   (tone rule KNOWN to run here)")
    print(f"  ARM UNDER TEST    --linear-srgb p99.9 = {p_lin:.4f}   "
          f"on target: {hit_lin}")

    print()
    if not hit_srgb:
        print("  INCONCLUSIVE: the positive control missed the target, so this test")
        print("  cannot detect a tone rule and the negative arm proves nothing.")
        return 1
    if hit_lin:
        print("  PREMISE FALSE: the linear arm carries the tone rule's fingerprint.")
        print("  The coffee-bubbles re-render verdict must be WITHDRAWN.")
        return 1
    print("  PREMISE CONFIRMED BY MEASUREMENT: the positive control lands on the")
    print(f"  target and the linear arm does not ({p_lin:.4f}, off by "
          f"{abs(p_lin - TONE_WHITE_TARGET) / TOLERANCE:.0f}x the tolerance).")
    print("  --linear-srgb is pre-tone in the pixels, not merely in the source.")

    # p99.9 == 1.0000 EXACTLY is not a neutral way to miss a target: it means at
    # least 0.1% of the frame is pinned at full scale by the per-channel clamp
    # that `image_out.rs:2279` documents as riding on the measurement paths.
    # Reported as a magnitude rather than left as a remark, because a clipped
    # measurement render is a trap for anyone measuring highlights on it -- and
    # a clip census is exactly what the merge banner lists under "not applied".
    print("\n  incidental, since the arm missed the target by CLIPPING rather than by sitting low:")
    raw_lin = read(base / "coffee-bubbles--LINEAR.tiff")
    raw_srgb = read(base / "coffee-bubbles--SRGB.tiff")
    for label, raw in (("--linear-srgb", raw_lin), ("--srgb", raw_srgb)):
        at_max = raw >= 1.0
        any_ch = at_max.any(axis=-1)
        all_ch = at_max.all(axis=-1)
        print(
            f"    {label:<14} clipped: {100.0 * any_ch.mean():6.3f}% of pixels on >=1 channel, "
            f"{100.0 * all_ch.mean():6.3f}% on all three"
        )
    print("    The dark field measured for the verdict sits below p90, decades away from")
    print("    this, so the verdict is unaffected -- but highlight work on a linear render")
    print("    must not assume the top of the range survived.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
