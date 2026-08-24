"""M95 arm 6 shared library: ground-truth demosaic metrology.

The one idea here is that a demosaic can be scored against a KNOWN answer.
Every other instrument in this investigation has compared two renders and asked
which has more top-octave power. That question cannot distinguish detail that
was recovered from artifact that was injected, and an interpolator can do both.

Given truth `T` and a demosaic output `D`, band-limited, the emitted power
splits exactly:

    alpha(f) = sum_t D_t(f) conj(T_t(f)) / sum_t |T_t(f)|^2
    P_sig(f) = |alpha(f)|^2 * P_T(f)
    P_eps(f) = P_D(f) - P_sig(f)        >= 0, the least-squares residual

`alpha` is estimated per frequency bin and pooled over tiles, so a demosaic is
allowed to be any linear shift-invariant filter without being charged for it.
What it is charged for is everything that is NOT such a filter: aliasing,
zipper, maze, false colour. Those fold energy from other frequencies and cannot
be absorbed by any alpha, so they land in P_eps. That is the whole design.

MHC is ported here from `crates/strehl-core/src/demosaic.rs`, which was itself
written from the Malvar-He-Cutler paper's stencils. The port is certified
against the shipped Rust by `d1_certify.py` (control K6) and is not admissible
evidence about strehl until that passes.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

# ---------------------------------------------------------------- CFA geometry
# RGGB, matching CfaPlane::rggb_at. Row 0 is R G R G, row 1 is G B G B.
#   (x even, y even) -> R      (x odd,  y even) -> G1
#   (x even, y odd)  -> G2     (x odd,  y odd)  -> B


def rggb_masks(h: int, w: int):
    """Boolean masks for the four CFA sites of an `h` x `w` RGGB mosaic."""
    y = np.arange(h)[:, None]
    x = np.arange(w)[None, :]
    xe, ye = (x % 2 == 0), (y % 2 == 0)
    return {
        "R": ye & xe,
        "G1": ye & ~xe,
        "G2": ~ye & xe,
        "B": ~ye & ~xe,
    }


def mosaic_rggb(T: np.ndarray) -> np.ndarray:
    """Sample a full-colour `(h, w, 3)` image at RGGB sites -> `(h, w)`."""
    h, w, _ = T.shape
    m = rggb_masks(h, w)
    out = np.empty((h, w), dtype=np.float32)
    out[m["R"]] = T[..., 0][m["R"]]
    out[m["G1"]] = T[..., 1][m["G1"]]
    out[m["G2"]] = T[..., 1][m["G2"]]
    out[m["B"]] = T[..., 2][m["B"]]
    return out


# --------------------------------------------------------- Malvar-He-Cutler
# Kernels indexed [dy + 2][dx + 2] so that correlate() computes
#     sum_k kernel[dy+2][dx+2] * input[y+dy][x+dx]
# which is exactly `conv()` in demosaic.rs. Weights are in eighths there and the
# 0.125 is folded in here.


def _k(taps):
    a = np.zeros((5, 5), dtype=np.float64)
    for dx, dy, wt in taps:
        a[dy + 2, dx + 2] = wt
    return (a * 0.125).astype(np.float32)


F_G = _k([(0, 0, 4), (-1, 0, 2), (1, 0, 2), (0, -1, 2), (0, 1, 2),
          (-2, 0, -1), (2, 0, -1), (0, -2, -1), (0, 2, -1)])

F_H = _k([(0, 0, 5), (-1, 0, 4), (1, 0, 4), (-2, 0, -1), (2, 0, -1),
          (-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1),
          (0, -2, 0.5), (0, 2, 0.5)])

F_V = _k([(0, 0, 5), (0, -1, 4), (0, 1, 4), (0, -2, -1), (0, 2, -1),
          (-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1),
          (-2, 0, 0.5), (2, 0, 0.5)])

F_X = _k([(0, 0, 6), (-1, -1, 2), (1, -1, 2), (-1, 1, 2), (1, 1, 2),
          (-2, 0, -1.5), (2, 0, -1.5), (0, -2, -1.5), (0, 2, -1.5)])


def _corr(M, k):
    # 'mirror' reflects without repeating the edge sample, which is exactly
    # reflect() in demosaic.rs: -i for i<0 and 2(n-1)-i for i>=n. That parity is
    # load-bearing -- clamping would put a red sample where the stencil expects
    # green.
    return ndimage.correlate(M, k, mode="mirror").astype(np.float32)


def demosaic_mhc(M: np.ndarray) -> np.ndarray:
    """Port of `strehl_core::demosaic::demosaic`. Certified by K6."""
    M = np.ascontiguousarray(M, dtype=np.float32)
    h, w = M.shape
    m = rggb_masks(h, w)
    g, fh, fv, fx = _corr(M, F_G), _corr(M, F_H), _corr(M, F_V), _corr(M, F_X)
    out = np.empty((h, w, 3), dtype=np.float32)

    R, B, G1, G2 = m["R"], m["B"], m["G1"], m["G2"]
    out[..., 0] = np.where(R, M, np.where(B, fx, np.where(G1, fh, fv)))
    out[..., 1] = np.where(R | B, g, M)
    out[..., 2] = np.where(B, M, np.where(R, fx, np.where(G1, fv, fh)))
    return out


def demosaic_bilinear(M: np.ndarray) -> np.ndarray:
    """Port of `demosaic_bilinear_row`. The reference arm, not a shipping path."""
    M = np.ascontiguousarray(M, dtype=np.float32)
    h, w = M.shape
    m = rggb_masks(h, w)
    kc = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32) * 0.25
    kd = np.array([[1, 0, 1], [0, 0, 0], [1, 0, 1]], np.float32) * 0.25
    kh = np.array([[0, 0, 0], [1, 0, 1], [0, 0, 0]], np.float32) * 0.5
    kv = np.array([[0, 1, 0], [0, 0, 0], [0, 1, 0]], np.float32) * 0.5
    cross, diag = _corr(M, kc), _corr(M, kd)
    horiz, vert = _corr(M, kh), _corr(M, kv)

    R, B, G1, G2 = m["R"], m["B"], m["G1"], m["G2"]
    out = np.empty((h, w, 3), dtype=np.float32)
    out[..., 0] = np.where(R, M, np.where(B, diag, np.where(G1, horiz, vert)))
    out[..., 1] = np.where(R | B, cross, M)
    out[..., 2] = np.where(B, M, np.where(R, diag, np.where(G1, vert, horiz)))
    return out


def demosaic_nearest(M: np.ndarray) -> np.ndarray:
    """Replicate each CFA sample across its quad.

    Deliberately artifact-heavy. This is the same operation that broke the
    orchestrator's three successive `np.kron` binned anchors: block replication
    puts a step at every quad boundary and therefore INJECTS top-octave energy
    that is not in the scene. It is in the ladder so that B1 has something that
    is unambiguously worse yet unambiguously louder.
    """
    M = np.ascontiguousarray(M, dtype=np.float32)
    h, w = M.shape
    out = np.empty((h, w, 3), dtype=np.float32)
    # quad-corner values broadcast over the 2x2 block
    r = np.repeat(np.repeat(M[0::2, 0::2], 2, 0), 2, 1)[:h, :w]
    b = np.repeat(np.repeat(M[1::2, 1::2], 2, 0), 2, 1)[:h, :w]
    g1 = np.repeat(np.repeat(M[0::2, 1::2], 2, 0), 2, 1)[:h, :w]
    g2 = np.repeat(np.repeat(M[1::2, 0::2], 2, 0), 2, 1)[:h, :w]
    y = np.arange(h)[:, None]
    out[..., 0] = r
    out[..., 1] = np.where(y % 2 == 0, g1, g2)
    out[..., 2] = b
    return out


DEMOSAICS = {
    "MHC": demosaic_mhc,
    "BILINEAR": demosaic_bilinear,
    "NEAREST": demosaic_nearest,
}

# ------------------------------------------------------------------ photometry

BT709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def luma(rgb: np.ndarray) -> np.ndarray:
    return (rgb * BT709).sum(-1).astype(np.float32)


# ------------------------------------------------------------------- band work


def hann2(n: int) -> np.ndarray:
    w = np.hanning(n + 2)[1:-1].astype(np.float32)
    return np.outer(w, w)


def band_mask(n: int, lo: float, hi: float) -> np.ndarray:
    """Radial frequency mask in cycles/pixel for an `n` x `n` rfft2 grid."""
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    return (r >= lo) & (r <= hi)


def pick_tiles(T: np.ndarray, n: int, count: int, lo: float, hi: float,
               margin: int = 16, seed: int = 0):
    """Top-`count` non-overlapping `n` x `n` tiles by in-band energy of T.

    Ranking by the TRUTH's own band energy, never by any arm's, so the tile set
    cannot favour one demosaic. Flat tiles are excluded because every demosaic
    is perfect on them and including them would dilute every effect toward zero.
    """
    L = luma(T) if T.ndim == 3 else T
    h, w = L.shape
    win, msk = hann2(n), band_mask(n, lo, hi)
    ys = range(margin, h - n - margin, n)
    xs = range(margin, w - n - margin, n)
    scored = []
    for y in ys:
        for x in xs:
            t = L[y:y + n, x:x + n]
            F = np.fft.rfft2(t * win)
            scored.append((float((np.abs(F[msk]) ** 2).sum()), y, x))
    scored.sort(reverse=True)
    return [(y, x) for _, y, x in scored[:count]]


def decompose(D: np.ndarray, T: np.ndarray, tiles, n: int,
              lo: float, hi: float) -> dict:
    """Split D's in-band power into detail correlated with T and residual.

    Returns log10 powers relative to truth. `alpha` is per frequency bin, pooled
    over tiles, so any linear shift-invariant response is free; only what no
    such filter can explain is charged as artifact.
    """
    win, msk = hann2(n), band_mask(n, lo, hi)
    nb = int(msk.sum())
    num = np.zeros(nb, dtype=np.complex128)
    den = np.zeros(nb, dtype=np.float64)
    pd = np.zeros(nb, dtype=np.float64)
    for (y, x) in tiles:
        FT = np.fft.rfft2(T[y:y + n, x:x + n] * win)[msk]
        FD = np.fft.rfft2(D[y:y + n, x:x + n] * win)[msk]
        num += FD * np.conj(FT)
        den += np.abs(FT) ** 2
        pd += np.abs(FD) ** 2
    alpha = num / den
    p_t = den.sum()
    p_sig = (np.abs(alpha) ** 2 * den).sum()
    p_d = pd.sum()
    p_eps = max(p_d - p_sig, 0.0)
    return {
        "n_tiles": len(tiles),
        "n_bins": nb,
        "power": float(np.log10(p_d / p_t)),
        "signal": float(np.log10(p_sig / p_t)),
        "artifact": float(np.log10(p_eps / p_t)) if p_eps > 0 else float("-inf"),
        "artifact_share": float(p_eps / p_d),
        "alpha_mean_abs": float(np.abs(alpha).mean()),
        "p_eps_over_p_t": float(p_eps / p_t),
    }


def blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur, per channel, reflecting at the border."""
    if sigma <= 0:
        return img.copy()
    if img.ndim == 2:
        return ndimage.gaussian_filter(img, sigma, mode="mirror").astype(np.float32)
    out = np.empty_like(img)
    for c in range(img.shape[-1]):
        out[..., c] = ndimage.gaussian_filter(img[..., c], sigma, mode="mirror")
    return out


def box2(img: np.ndarray) -> np.ndarray:
    """2x box-downsample. Even dimensions only."""
    h, w = img.shape[0] // 2 * 2, img.shape[1] // 2 * 2
    a = img[:h, :w]
    if a.ndim == 2:
        return (a.reshape(h // 2, 2, w // 2, 2).mean((1, 3))).astype(np.float32)
    return (a.reshape(h // 2, 2, w // 2, 2, a.shape[2]).mean((1, 3))).astype(np.float32)
