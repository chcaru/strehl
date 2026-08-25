"""Is M116's arm geometry the same frame of reference as M93's single frames?

ORCH's patchwork_invariant.py compares a merged arm against M93's single frames
window-for-window at identical (x, y). That is only a comparison if the two
images are registered to each other. M116's arms share a frozen warp map solved
by `strehl align`; M93's single frames were rendered by a different milestone
and there is no reason to assume the same warp.

So: measure the integer pixel shift by phase correlation. Integer only -- a
sub-pixel resample would add blur to the very quantity (fine structure) the
invariant scores. Discipline: registration is established before comparison,
not assumed from a matching array shape.

Read-only. Prints only.
"""
from pathlib import Path

import numpy as np
import tifffile

M93 = Path(r"C:\dev\strehl-out\M93-out")
M116 = Path(r"C:\dev\strehl-out\M116\measure")


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit(f"{p} read as {a.dtype}, expected uint16")
    return (a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3
            else a.astype(np.float64))


def shift_of(a, b):
    """Integer (dy, dx) that best aligns b onto a, by phase correlation."""
    a = a - a.mean()
    b = b - b.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    FA = np.fft.rfft2(a * win)
    FB = np.fft.rfft2(b * win)
    R = FA * np.conj(FB)
    m = np.abs(R)
    R = np.divide(R, m, out=np.zeros_like(R), where=m > 0)
    c = np.fft.irfft2(R, s=a.shape)
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    if dy > a.shape[0] // 2:
        dy -= a.shape[0]
    if dx > a.shape[1] // 2:
        dx -= a.shape[1]
    return int(dy), int(dx), float(c.max())


REF = M93 / "armF-f173.tif"
TARGETS = [
    ("M93 armF-f143 (another single)", M93 / "armF-f143.tif"),
    ("M93 armM-gate0-binlin", M93 / "armM-gate0-binlin.tif"),
    ("M93 armM4-gate4-binlin  <- ORCH baseline", M93 / "armM4-gate4-binlin.tif"),
    ("M93 armC-aligned-gate0", M93 / "armC-aligned-gate0.tif"),
    ("M116 bee-3-cpl__A0 (shipped)", M116 / "bee-3-cpl__A0.tif"),
    ("M116 bee-3-cpl__A1 (photometric)", M116 / "bee-3-cpl__A1.tif"),
]

# A central crop: cheap, and away from the border where warping is worst.
Y, X, S = 900, 1400, 1024
R = lum(REF)[Y:Y + S, X:X + S]
print(f"reference: {REF.name}, crop y={Y} x={X} {S}x{S}")
print(f"{'image':<44} {'dy':>5} {'dx':>5} {'peak':>8}  verdict")
for name, p in TARGETS:
    if not p.exists():
        print(f"{name:<44} MISSING")
        continue
    a = lum(p)
    if a.shape != lum(REF).shape:
        print(f"{name:<44} GEOMETRY DIFFERS")
        continue
    dy, dx, pk = shift_of(R, a[Y:Y + S, X:X + S])
    v = ("registered" if (dy, dx) == (0, 0)
         else f"SHIFTED by ({dy},{dx}) px")
    print(f"{name:<44} {dy:>5} {dx:>5} {pk:>8.4f}  {v}")
