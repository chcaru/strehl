"""BUILD-SHARP shared harness.

Everything here reads 16-bit linear TIFFs written by the pinned binary and
NEVER re-encodes them for measurement. Display encoding is imported from
`scripts/crop_set.py` so that a BUILD-SHARP crop and a baseline crop of the
same pixels are byte-comparable.

Rule 7: 16-bit RGB TIFFs are read with `tifffile` and the dtype is asserted.
Rule 6: any registration performed for measurement uses INTEGER shifts only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))

import crop_set as CS  # noqa: E402

OUT = Path(r"C:\dev\strehl-out\BUILD-SHARP")
RENDERS = OUT / "renders"


def read_linear(path) -> np.ndarray:
    """16-bit linear RGB TIFF -> float32 [0,1]; dtype asserted (rule 7)."""
    return CS.read_linear(Path(path))


def read_green(path) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path}: dtype {arr.dtype}, expected uint16")
    return arr[..., 1].astype(np.float32) / 65535.0


def arm(subject: str, name: str) -> Path:
    return RENDERS / subject / name / "linear.tif"


# ---------------------------------------------------------------------------
# integer-only registration
# ---------------------------------------------------------------------------


def _norm(a: np.ndarray) -> np.ndarray:
    a = a - a.mean()
    n = np.sqrt((a * a).sum())
    return a / n if n > 0 else a


def subpixel_peak(ref: np.ndarray, mov: np.ndarray, search: int = 8):
    """Best offset aligning `mov` onto `ref`: integer peak + parabola refine.

    The parabola is fitted to CORRELATION VALUES, not to resampled pixels, so
    this estimates a sub-pixel offset without ever interpolating an image
    (rule 6 -- a sub-pixel resample would inject blur into the very quantity
    being measured).

    Returns (dy, dx, ncc, integer_dy, integer_dx).
    """
    h, w = ref.shape
    rn = _norm(ref[search : h - search, search : w - search])

    grid = np.full((2 * search + 1, 2 * search + 1), -2.0, dtype=np.float64)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            mc = mov[search + dy : h - search + dy, search + dx : w - search + dx]
            grid[dy + search, dx + search] = float((rn * _norm(mc)).sum())

    k = int(np.argmax(grid))
    iy, ix = np.unravel_index(k, grid.shape)
    peak = float(grid[iy, ix])
    iy, ix = int(iy) - search, int(ix) - search
    if abs(iy) >= search or abs(ix) >= search:
        return (float(iy), float(ix), peak, iy, ix)

    def parab(a, b, c):
        d = a - 2 * b + c
        return 0.0 if abs(d) < 1e-12 else 0.5 * (a - c) / d

    sy = float(np.clip(parab(grid[iy + search - 1, ix + search], peak,
                             grid[iy + search + 1, ix + search]), -1, 1))
    sx = float(np.clip(parab(grid[iy + search, ix + search - 1], peak,
                             grid[iy + search, ix + search + 1]), -1, 1))
    return (iy + sy, ix + sx, peak, iy, ix)


# ---------------------------------------------------------------------------
# spectral instrument
# ---------------------------------------------------------------------------


def hann2(n: int) -> np.ndarray:
    w = np.hanning(n + 2)[1:-1]
    return np.outer(w, w).astype(np.float32)


def radial_power(tile: np.ndarray, nbins: int = 64):
    """Radially averaged power spectrum of one square tile, in cyc/px."""
    n = tile.shape[0]
    t = (tile - tile.mean()) * hann2(n)
    F = np.fft.rfft2(t)
    P = F.real**2 + F.imag**2
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    edges = np.linspace(0, 0.5, nbins + 1)
    idx = np.clip(np.digitize(r.ravel(), edges) - 1, 0, nbins - 1)
    s = np.bincount(idx, weights=P.ravel(), minlength=nbins)
    c = np.bincount(idx, minlength=nbins)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / np.maximum(c, 1)
    f = 0.5 * (edges[:-1] + edges[1:])
    return f, m, c


def band_power(tile: np.ndarray, lo: float, hi: float) -> float:
    f, p, c = radial_power(tile)
    m = (f >= lo) & (f < hi) & (c > 0)
    if not m.any():
        return 0.0
    return float((p[m] * c[m]).sum() / c[m].sum())


# ---------------------------------------------------------------------------
# display
# ---------------------------------------------------------------------------


def display_gain(lin: np.ndarray, pct: float = 99.5, target: float = 0.90) -> float:
    p = float(np.percentile(lin[..., 1], pct))
    return target / p if p > 1e-6 else 1.0


def to_png8(patch: np.ndarray, gain: float, colour: bool = True) -> np.ndarray:
    m = CS.A7C2_CAM_TO_SRGB if colour else None
    return CS.to_display(patch, gain, m)
