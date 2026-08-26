"""Do-no-harm regression guard for gallery subjects.

Compares one gallery image against a stored reference and says, loudly, whether
it moved -- and shows you WHERE, because a scalar delta cannot tell an
improvement from a degradation and this project has a long history of green
numbers over bad images.

The subject this exists for is couch-fibers-cpl. It was audited and found
genuinely good: sharp to individual filaments, no artefacts. That makes it the
control proving the core machinery is sound and that the remaining defects are
localised to depth boundaries -- and it makes it the subject most likely to be
silently degraded by work aimed at something else. An adaptive window that
shrinks too far, or a deconvolution that rings, will damage high-frequency
texture first, and it will do it while the subject it was tuned on improves.

Why compare the JPEGs rather than the 16-bit TIFFs: the gallery JPEG is what a
human judges, the encoder is deterministic, and identical pixels in produce
identical bytes out. Comparing at viewing scale also weights the comparison the
way a viewer does, instead of reporting a per-pixel delta nobody could see.
That does mean this cannot resolve sub-DN changes; it is not trying to. It is
trying to answer "did the picture get worse", which is the question that
matters.

8-bit JPEG through PIL is fine. The rule that bans PIL is specifically about
16-bit RGB TIFFs, which it silently downconverts to 8 bits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

# A pixel delta answers "did anything change". The question the guard is FOR is
# "did this subject lose detail", and those are different questions: raising
# contrast scales every edge amplitude, so a tone change and a defocus produce
# the same edge-weighted difference map. Deciding on the raw delta means the
# guard fires on a change its own author intended, forever, and a guard that
# always fires is worse than no guard -- it launders a real regression through
# an alarm everyone has learned to ignore.
#
# So the VERDICT comes from a contrast-normalised gradient statistic, which is
# invariant to any monotonic global rescale of the image, and the raw delta is
# kept only as context for the human who looks at the picture afterwards. This
# is the same correction already made to trend.py (see BUILD-RENDER.md section
# 14), where the un-normalised form reported a library-wide regression that was
# nothing but the tone curve landing.
SOFTER = 0.98   # normalised sharpness ratio below this: detail was lost
SHARPER = 1.06  # and above this: ringing or over-sharpening, also a regression
# Raw delta thresholds. NOT a verdict any more -- printed so a real change is
# still visible, and used only to suppress the diff images when nothing at all
# happened.
MOVED_MEAN = 0.25  # mean |delta|, 8-bit DN
MOVED_P999 = 6.0  # p99.9 |delta|, 8-bit DN


def load(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16)


def sharpness_normalised(a: np.ndarray) -> float:
    """Gradient RMS after standardising the image to zero mean, unit variance.

    The standardisation is what makes this blind to tone. Multiplying an image
    by 0.95 multiplies its gradient RMS by 0.95 and its standard deviation by
    0.95, so the ratio is unchanged -- while a blur lowers the gradient without
    lowering the variance nearly as much, and still registers.
    """
    y = a.astype(np.float32).mean(axis=2)
    s = float(y.std())
    if s < 1e-6:
        return 0.0
    y = (y - y.mean()) / s
    gx = np.diff(y, axis=1)
    gy = np.diff(y, axis=0)
    return float(np.sqrt((gx * gx).mean() + (gy * gy).mean()))


def compare(current: Path, reference: Path, out_dir: Path) -> int:
    cur, ref = load(current), load(reference)
    if cur.shape != ref.shape:
        print(f"GUARD  {current.stem}: SHAPE CHANGED {ref.shape} -> {cur.shape}")
        return 1

    d = np.abs(cur - ref)
    lum = d.max(axis=2).astype(np.float32)
    mean, p999, mx = float(lum.mean()), float(np.percentile(lum, 99.9)), float(lum.max())
    differs = mean > MOVED_MEAN or p999 > MOVED_P999

    s_cur = sharpness_normalised(cur)
    s_ref = sharpness_normalised(ref)
    ratio = s_cur / s_ref if s_ref > 0 else 0.0
    moved = ratio < SOFTER or ratio > SHARPER

    if moved:
        tag = "MOVED"
    elif differs:
        # The honest middle case, and the one that used to be a false alarm:
        # the picture changed but its detail did not. A tone change lands here.
        tag = "held*"
    else:
        tag = "held "
    print(
        f"GUARD  {current.stem}: {tag}  sharp x{ratio:5.3f}  "
        f"mean {mean:6.3f}  p99.9 {p999:6.2f}  max {mx:6.1f} DN8  "
        f"({(lum > 2).mean() * 100:5.2f}% of pixels differ by >2)"
    )
    if tag == "held*":
        print("       pixels moved but detail did not -- a tone or colour change, not a regression")

    if not moved:
        return 0

    # Amplified difference map plus the two frames it came from, so the first
    # thing anyone does about a MOVED is look at the picture rather than argue
    # about the number.
    out_dir.mkdir(parents=True, exist_ok=True)
    amp = np.clip(lum * 8.0, 0, 255).astype(np.uint8)
    Image.fromarray(amp).save(out_dir / f"{current.stem}-diff8x.png")
    strip = np.concatenate([ref.astype(np.uint8), cur.astype(np.uint8)], axis=1)
    Image.fromarray(strip).save(out_dir / f"{current.stem}-before-after.png")
    print(f"       look at {out_dir / (current.stem + '-before-after.png')}")
    return 1


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: guard.py <current.jpg> <reference.jpg> <out_dir>", file=sys.stderr)
        return 2
    current, reference, out_dir = (Path(a) for a in sys.argv[1:4])
    if not current.exists():
        print(f"GUARD  {current.stem}: MISSING -- the subject did not render")
        return 1
    if not reference.exists():
        # First run establishes the reference. Deliberately not silent: a guard
        # that quietly creates its own baseline from a broken render is worse
        # than no guard.
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(current.read_bytes())
        print(f"GUARD  {current.stem}: reference ESTABLISHED at {reference}")
        print("       check this image is actually good before trusting it.")
        return 0
    return compare(current, reference, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
