"""Shared helpers for M95 (merge-vs-frame sharpness).

Everything here is written for this milestone; nothing is imported from another
milestone's scratch, because a number recalled from an earlier note is not a
measurement.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass

import numpy as np

PIN = r"C:\dev\strehl-out\M95-pin\target\release\strehl.exe"
OUT = r"C:\dev\strehl-out\M93-out"
FRAMES = r"C:\dev\strehl-out\M93-frames"
STACK = r"D:\personal\macro\bee-3-cpl"

# Sensor pitch. Derived in `s0_optics.py` from the active-area geometry and the
# 35 mm frame width; not taken on report from anywhere.
PITCH_UM = None  # filled by callers that need cy/mm; see s0_optics.py


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_strehl(args: list[str], align: str | None) -> str:
    """Run the pinned binary. `align` is the STREHL_ALIGN value, or None for default."""
    env = dict(os.environ)
    if align is None:
        env.pop("STREHL_ALIGN", None)
    else:
        env["STREHL_ALIGN"] = align
    p = subprocess.run([PIN] + args, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"strehl failed rc={p.returncode}\n{p.stderr[-4000:]}")
    return p.stdout + p.stderr


def read_tif_green(path: str) -> np.ndarray:
    """Green channel of a 16-bit RGB TIFF, as float64 in [0, 65535]."""
    import tifffile

    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    assert a.dtype == np.uint16, a.dtype
    return a[:, :, 1].astype(np.float64)


def read_tif_rgb(path: str) -> np.ndarray:
    import tifffile

    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    return a


@dataclass
class RawFrame:
    cfa: np.ndarray  # visible-area CFA, uint16
    black: float
    white: float
    pattern: str


def decode_raw(path: str) -> RawFrame:
    """Independent decode, for the loader control and the through-focus curve.

    Rule 32: `raw_image_visible` is a view into LibRaw's buffer. Copy inside the
    `with`.
    """
    import rawpy

    with rawpy.imread(path) as r:
        cfa = np.array(r.raw_image_visible, dtype=np.uint16, copy=True)
        black = float(np.mean(r.black_level_per_channel))
        white = float(r.white_level)
        desc = r.color_desc.decode() if isinstance(r.color_desc, bytes) else r.color_desc
        pat = "".join(desc[i] for i in r.raw_pattern.flatten())
    return RawFrame(cfa=cfa, black=black, white=white, pattern=pat)


def green_mean_plane(cfa: np.ndarray) -> np.ndarray:
    """(G1 + G2) / 2 per 2x2 RGGB quad, as float64 raw DN (no black subtraction)."""
    g1 = cfa[0::2, 1::2].astype(np.float64)
    g2 = cfa[1::2, 0::2].astype(np.float64)
    h = min(g1.shape[0], g2.shape[0])
    w = min(g1.shape[1], g2.shape[1])
    return 0.5 * (g1[:h, :w] + g2[:h, :w])


def hann2(n: int) -> np.ndarray:
    w = np.hanning(n + 2)[1:-1]
    return np.outer(w, w)


def radial_psd(tile: np.ndarray, nbins: int = 256):
    """Radially averaged power spectrum of a square tile.

    Returns (f_cyc_per_px, power). `f` runs 0 .. 0.5 cycles per sample of the
    grid the tile lives on. The tile is mean-removed and Hann-windowed; the
    window's power loss is divided out so that levels are comparable between
    tiles of the same size.
    """
    t = tile.astype(np.float64)
    n = t.shape[0]
    assert t.shape == (n, n), t.shape
    w = hann2(n)
    t = (t - t.mean()) * w
    # Window power normalisation: E[|FFT|^2] scales with sum(w^2).
    norm = (w**2).sum()
    F = np.fft.fftshift(np.fft.fft2(t))
    P = (np.abs(F) ** 2) / norm
    fy = np.fft.fftshift(np.fft.fftfreq(n))
    fx = np.fft.fftshift(np.fft.fftfreq(n))
    R = np.hypot(*np.meshgrid(fy, fx, indexing="ij"))
    edges = np.linspace(0.0, 0.5, nbins + 1)
    idx = np.digitize(R.ravel(), edges) - 1
    ok = (idx >= 0) & (idx < nbins)
    tot = np.bincount(idx[ok], weights=P.ravel()[ok], minlength=nbins)
    cnt = np.bincount(idx[ok], minlength=nbins)
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    centres = 0.5 * (edges[:-1] + edges[1:])
    return centres, prof, cnt


def band_power(f: np.ndarray, p: np.ndarray, lo: float, hi: float) -> float:
    """Mean power over a radial band, in cycles/sample."""
    m = (f >= lo) & (f < hi) & np.isfinite(p)
    assert m.sum() > 0, (lo, hi)
    return float(np.nanmean(p[m]))


def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    # Explicit 2-D input only: rule 23's general form. This is a plane, not a cube.
    assert img.ndim == 2, img.shape
    return gaussian_filter(img.astype(np.float64), sigma=sigma, mode="reflect")
