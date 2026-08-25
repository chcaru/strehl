"""E0b -- look at the images, and measure inter-frame drift.

Discipline 824 ("look at the output") and discipline 832 ("state what is held
constant"): before any statistic, produce previews of the exact arrays the
statistics will run on, and check that the single frames really do sit at the
same pixels as the merged arm (M93 rendered with alignment OFF, so they should,
but M86 measured 232.7 px of drift across the 299-frame stack and that has to
be quantified over the frames actually used).

PIL is used for WRITING PNG previews only.  Every read is `tifffile` +
`assert dtype == uint16` (discipline 828).

Run:  python experiments/M121-halo-polarity/e0b_look.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from m121_io import FRAMES, M93, OUT, arm_path, load_u16, luma  # noqa: E402


def to_png(a: np.ndarray, path: pathlib.Path, lo=None, hi=None):
    if lo is None:
        lo, hi = np.percentile(a, [0.5, 99.5])
    b = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    b = np.sqrt(b)  # gamma, for looking at only
    Image.fromarray((b * 255).astype(np.uint8)).save(path)
    return float(lo), float(hi)


def drift(a: np.ndarray, b: np.ndarray, cy: int, cx: int, half: int = 256) -> tuple[float, float, float]:
    """Integer-pixel phase correlation peak of two crops."""
    A = a[cy - half:cy + half, cx - half:cx + half].astype(np.float64)
    B = b[cy - half:cy + half, cx - half:cx + half].astype(np.float64)
    A -= A.mean()
    B -= B.mean()
    w = np.outer(np.hanning(2 * half), np.hanning(2 * half))
    F = np.fft.rfft2(A * w) * np.conj(np.fft.rfft2(B * w))
    F /= np.abs(F) + 1e-12
    c = np.fft.irfft2(F, s=A.shape)
    k = np.unravel_index(np.argmax(c), c.shape)
    dy = k[0] - (2 * half if k[0] > half else 0)
    dx = k[1] - (2 * half if k[1] > half else 0)
    return float(dy), float(dx), float(c.max())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    look = OUT / "look"
    look.mkdir(exist_ok=True)

    m = luma(load_u16(arm_path("armM4-gate4-binlin")))
    print("armM4 luma", m.shape, m.min(), m.max())

    lo, hi = to_png(m[::4, ::4], look / "overview-armM4.png")
    print("overview stretch", lo, hi)

    # A coarse tile map so ROIs can be picked from something, not guessed.
    h, w = m.shape
    ty, tx = 8, 12
    print("\ntile map: mean / sd / p99-p1 of luma, 1:1 plane px")
    for j in range(ty):
        row = []
        for i in range(tx):
            t = m[j * h // ty:(j + 1) * h // ty, i * w // tx:(i + 1) * w // tx]
            row.append(f"{t.mean():7.0f}/{t.std():6.0f}")
        print(f" y{j}: " + " ".join(row))

    # Drift between the single frames actually used, measured on four widely
    # separated 512 px windows.
    f0 = luma(load_u16(M93 / f"{FRAMES[0]}.tif"))
    print("\ninter-frame drift, integer px, phase correlation vs", FRAMES[0])
    for name in FRAMES[1:]:
        fk = luma(load_u16(M93 / f"{name}.tif"))
        for (cy, cx) in [(600, 900), (600, 2600), (1700, 900), (1700, 2600), (1172, 1758)]:
            dy, dx, pk = drift(f0, fk, cy, cx)
            print(f"  {name} at (y={cy},x={cx}): dy={dy:+.0f} dx={dx:+.0f} peak={pk:.4f}")

    # And merged vs single frame -- the pair every matched-pixel claim rests on.
    print("\nmerged armM4 vs single frames, same windows")
    for name in FRAMES:
        fk = luma(load_u16(M93 / f"{name}.tif"))
        for (cy, cx) in [(600, 2600), (1172, 1758)]:
            dy, dx, pk = drift(m, fk, cy, cx)
            print(f"  {name} at (y={cy},x={cx}): dy={dy:+.0f} dx={dx:+.0f} peak={pk:.4f}")


if __name__ == "__main__":
    main()
