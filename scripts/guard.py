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

# Below this, the change is JPEG-grade noise or a one-bit rounding difference
# and calling it a regression would train everyone to ignore the guard. Above
# it, a human should look. Chosen to be a delta that is visible when you flick
# between two images, not one that survives a t-test.
MOVED_MEAN = 0.25  # mean |delta|, 8-bit DN
MOVED_P999 = 6.0  # p99.9 |delta|, 8-bit DN


def load(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16)


def compare(current: Path, reference: Path, out_dir: Path) -> int:
    cur, ref = load(current), load(reference)
    if cur.shape != ref.shape:
        print(f"GUARD  {current.stem}: SHAPE CHANGED {ref.shape} -> {cur.shape}")
        return 1

    d = np.abs(cur - ref)
    lum = d.max(axis=2).astype(np.float32)
    mean, p999, mx = float(lum.mean()), float(np.percentile(lum, 99.9)), float(lum.max())
    moved = mean > MOVED_MEAN or p999 > MOVED_P999

    tag = "MOVED" if moved else "held "
    print(
        f"GUARD  {current.stem}: {tag}  mean {mean:6.3f}  p99.9 {p999:6.2f}  "
        f"max {mx:6.1f} DN8  ({(lum > 2).mean() * 100:5.2f}% of pixels differ by >2)"
    )

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
