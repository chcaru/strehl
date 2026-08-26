#!/usr/bin/env python3
"""BUILD-GHOST core library: residual non-rigid motion, measured in the same
coordinate system and the same model class the shipped aligner uses.

WHY THIS SHAPE
==============
`crates/strehl-core/src/align.rs` states the shipped model exactly:

  * it works in **plane pixels** -- the half-resolution CFA plane, one plane px
    spans two sensor px;
  * it fits **a similarity, and only a similarity**: `p' = a*p + b` on
    coordinates relative to the plane centre, `a` complex (uniform scale +
    rotation), `b` complex (translation); four real parameters;
  * it measures a pair by **tiled zero-mean normalised cross correlation with
    parabolic sub-pixel refinement**, least-squares similarity fit to the tile
    displacement field, **one MAD outlier pass**.

So this module measures on the plane grid, correlates tiles with ZNCC +
parabolic refinement, and fits the same complex-linear similarity with one MAD
pass.  What is left over is, by construction, motion the shipped aligner cannot
absorb.

THE DEFOCUS CONFOUNDER, AND HOW IT IS SEPARATED
===============================================
Two frames at different focus positions differ enormously with nothing moving.
Any metric built on "how different are these pixels" reports that difference as
motion.  Three things separate them here, and each is checked by a control in
`controls.py` rather than asserted:

  1. **The primary metric is a DISPLACEMENT, not a difference.**  Defocus is a
     symmetric low-pass: it changes the amplitude of structure, not its
     position.  A correlation peak therefore does not move when a tile goes
     soft -- it gets shorter.  Motion moves the peak.  These are different
     axes of the same correlation surface and the metric only reads one.
  2. **A focus-match gate.**  A tile is admitted only if its high-frequency
     modulation is comparable in BOTH frames (`FOCUS_MATCH_MAX_LN`).  Tiles
     that are sharp in one frame and soft in the other -- where a
     displacement estimate would be least trustworthy -- are excluded and
     COUNTED, never silently dropped.
  3. **A correlation-confidence gate** on the ZNCC peak height, so a tile of
     pure noise cannot contribute a displacement.

UNITS
=====
Everything internal is **plane px**.  Everything reported is converted to
**sensor px** (x2), because the delivered masters in SHIP-V1 are on the sensor
grid and that is the grid a print is judged on.  Both are labelled at every
exit point.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

PLANE_TO_SENSOR = 2.0

# --- gates.  Numbers here are defaults; controls.py calibrates and reports them.
TILE_COARSE = 256          # plane px, for the global similarity fit
STRIDE_COARSE = 128
TILE_FINE = 64             # plane px, for localised residual motion
STRIDE_FINE = 32
MAX_SHIFT_COARSE = 40      # plane px search half-width, coarse (absorbs breathing)
MAX_RESID = 8              # plane px search half-width, fine, AROUND the global prediction
RHO_FLOOR = 0.30           # ZNCC peak height a tile must reach to vote
UNIQ_FLOOR = 0.10          # fine-stage peak-to-rival margin (see zncc_shift)
UNIQ_EXCL = 3              # plane px; rivals nearer than this are the same peak
# UNIQ_FLOOR was measured, not chosen.  experiments/BUILD-GHOST/tune_uniq.py
# sweeps it over four nulls and the positive control at once
# (C:\dev\strehl-out\BUILD-GHOST\tune_uniq3.log).  Residual p99, sensor px:
#
#            gate off   u>=0.05   u>=0.10   u>=0.15
#   C4 defocus-only        2.10      1.61      1.03      0.86
#   C6 wrapped-text-1     11.09      1.68      1.67      1.67
#   C6 angled-ruler       12.65      2.16      1.78      1.80
#   C6 flat-on-ruler       1.44      1.22      1.13      0.94
#   C7 two greens          7.05      1.80      1.58      1.53
#   C3 REAL 2.0 px motion  1.93      1.94      1.96      1.99   <-- untouched
#
# The gate removes ~10 sensor px of spurious residual from four independent
# nulls while the planted 2.0 sensor px motion does not move at all.  0.10 is
# where the nulls have flattened and 60% of tiles still survive; 0.15 buys
# almost nothing more and costs another third of the coverage.
FOCUS_MATCH_MAX_LN = 0.70  # |ln(hf_a / hf_b)| admitted (a 2.01x modulation ratio)
HF_SIG_MIN_REL = 0.50      # NOISE-CORRECTED tile hf must exceed this x the tile's own sigma
USFAC = 16                 # sub-pixel refinement grid, 1/16 plane px = 1/8 sensor px


# ----------------------------------------------------------------- decoding

def decode_plane(path: str) -> dict:
    """Decode one RAW to the half-resolution CFA plane, CAMERA-LINEAR.

    No demosaic, no white balance, no colour matrix, NO TONE CURVE.  Black is
    subtracted and the result is in raw DN above black, so every number derived
    from it is a linear flux.  (Project rule 1: never measure across a tone
    curve.)

    Returns the two greens averaged (the plane luminance the aligner uses) plus
    per-CFA-channel linear flux for the exposure-drift arm.
    """
    import rawpy

    with rawpy.imread(path) as r:
        v = r.raw_image_visible.astype(np.float32)
        pat = np.asarray(r.raw_pattern)
        black = np.asarray(r.black_level_per_channel, dtype=np.float32)
        white = float(r.white_level)
        desc = r.color_desc.decode() if isinstance(r.color_desc, bytes) else str(r.color_desc)

    h, w = v.shape
    h2, w2 = h // 2, w // 2
    q = v[: h2 * 2, : w2 * 2].reshape(h2, 2, w2, 2)

    planes, sat = {}, {}
    for oy in range(2):
        for ox in range(2):
            ci = int(pat[oy, ox])
            name = desc[ci] if ci < len(desc) else str(ci)
            sub = q[:, oy, :, ox]
            key = name if name not in planes else name + "2"
            planes[key] = sub.astype(np.float32) - black[ci]
            sat[key] = float((sub >= white - 1).mean())

    gkeys = [k for k in planes if k.startswith("G")]
    assert len(gkeys) == 2, f"expected two greens, got {sorted(planes)}"
    g = 0.5 * (planes[gkeys[0]] + planes[gkeys[1]])

    return {
        "path": path,
        "g": g,                                   # (H/2, W/2) float32, DN above black
        "flux": {k: float(p.mean()) for k, p in planes.items()},
        "sat": sat,                               # fraction at/above white level
        "black": float(black[0]),
        "white": white,
        "shape": (h, w),
    }


# ----------------------------------------------------------------- tiling

def tile_origins(shape: tuple[int, int], tile: int, stride: int, margin: int) -> np.ndarray:
    """Top-left origins of a tile grid, inset by `margin` so a search window fits."""
    h, w = shape
    ys = np.arange(margin, h - tile - margin + 1, stride)
    xs = np.arange(margin, w - tile - margin + 1, stride)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    return np.stack([yy.ravel(), xx.ravel()], axis=1)


def gather_tiles(img: np.ndarray, origins: np.ndarray, tile: int) -> np.ndarray:
    """(N, tile, tile) view-copy of tiles at the given origins."""
    idx_y = origins[:, 0, None] + np.arange(tile)[None, :]
    idx_x = origins[:, 1, None] + np.arange(tile)[None, :]
    return img[idx_y[:, :, None], idx_x[:, None, :]]


_HANN: dict[int, np.ndarray] = {}
_WAUTO: dict[int, tuple[np.ndarray, np.ndarray, float]] = {}


def hann2d(n: int) -> np.ndarray:
    if n not in _HANN:
        w = np.hanning(n + 2)[1:-1].astype(np.float32)
        _HANN[n] = np.outer(w, w).astype(np.float32)
    return _HANN[n]


def window_autocorr(n: int) -> tuple[np.ndarray, np.ndarray, float]:
    """The Hann window's own autocorrelation, and its spectrum.

    THIS CORRECTION IS LOAD-BEARING, and it was found by a control rather than
    by inspection.  Correlating w(x)a(x) against w(x)a(x-delta) gives a surface
    whose envelope is the window autocorrelation A_w(tau), which peaks at tau=0
    while the signal correlation peaks at tau=delta.  Their product peaks
    BETWEEN the two, so every sub-pixel answer is dragged toward zero in
    proportion to itself.  Measured before this correction: a planted 0.50
    sensor px read 0.30 (a 40% under-read), and control C7 -- whose true answer
    is exactly (-0.5, +0.5) plane px and is known from the CFA geometry rather
    than planted -- read (-0.442, +0.425), short by 12% and 15%.  Two
    independent controls, one synthetic and one from the sensor's own lattice,
    agreeing on the same bias.

    Dividing the correlation surface by A_w(tau)/A_w(0) removes the envelope.
    """
    if n not in _WAUTO:
        w = hann2d(n)
        Wf = np.fft.fft2(w)
        Pw = (Wf * np.conj(Wf)).astype(np.complex64)          # |W|^2
        A = np.real(np.fft.ifft2(Pw))
        _WAUTO[n] = (np.fft.fftshift(A / A[0, 0]).astype(np.float32),
                     Pw, float(np.real(Pw.sum())))
    return _WAUTO[n]


def hf_modulation(t: np.ndarray, k: float = 0.0, r2: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Per-tile high-frequency signal modulation, NOISE-CORRECTED.

    (N,T,T) -> (hf_sig, sigma_rel), both (N,).

    This is the FOCUS measure: a low-pass (defocus) lowers it, a translation does
    not.  It must be noise-corrected or it is not a focus measure at all -- these
    captures run 1-3 stops under and the plane's top octave is genuinely
    noise-dominated (measured: sigma 31 DN against a 1872 DN mean on
    couch-fibers-cpl/DSC00150), so a RAW first-difference statistic mostly
    reports the sensor, not the focus.

    For white noise of variance s2 the mean square of a one-pixel difference is
    2*s2, so subtracting that leaves the signal's own high-frequency power.  s2
    comes from the frame's measured photon-transfer curve, var = k*mean + r2, so
    the correction tracks brightness across the frame rather than assuming one
    number.  Normalising by the tile mean makes the result a modulation depth,
    hence invariant to the photometric gain drift measured separately in the
    exposure arm -- the two arms cannot contaminate each other.
    """
    d1 = np.diff(t, axis=1)[:, :, :-1]
    d2 = np.diff(t, axis=2)[:, :-1, :]
    hf2_raw = 0.5 * (np.mean(d1 * d1, axis=(1, 2)) + np.mean(d2 * d2, axis=(1, 2)))
    m = np.mean(t, axis=(1, 2))
    s2 = np.maximum(k * np.maximum(m, 0.0) + r2, 1e-6)
    hf2_sig = np.maximum(hf2_raw - 2.0 * s2, 0.0)
    md = np.maximum(m, 1.0)
    return np.sqrt(hf2_sig) / md, np.sqrt(s2) / md


def photon_transfer(g: np.ndarray) -> tuple[float, float]:
    """Estimate (k, r2) in var = k*mean + r2 from the plane's own top octave.

    A 2x2 checkerboard difference of a smooth scene is noise-dominated, so
    binning its ROBUST spread against local mean is a photon-transfer curve
    taken from the data rather than assumed.  MAD, not RMS, so scene structure
    that survives the checkerboard does not inflate it.
    """
    s = g[::2, ::2][:1200, :1200]
    d = (s[:-1:2, :-1:2] - s[:-1:2, 1::2] - s[1::2, :-1:2] + s[1::2, 1::2]) / 2.0
    m = (s[:-1:2, :-1:2] + s[:-1:2, 1::2] + s[1::2, :-1:2] + s[1::2, 1::2]) / 4.0
    m, d = m.ravel(), d.ravel()
    lo, hi = np.percentile(m, [2, 98])
    if not np.isfinite(lo) or hi <= lo:
        return 1.0, 4.0
    edges = np.linspace(lo, hi, 24)
    idx = np.clip(np.digitize(m, edges) - 1, 0, len(edges) - 2)
    mm, vv = [], []
    for b in range(len(edges) - 1):
        sel = idx == b
        if sel.sum() < 400:
            continue
        mm.append(m[sel].mean())
        vv.append((np.median(np.abs(d[sel] - np.median(d[sel]))) * 1.4826) ** 2)
    if len(mm) < 4:
        return 1.0, 4.0
    A = np.stack([np.asarray(mm), np.ones(len(mm))], 1)
    k, r2 = np.linalg.lstsq(A, np.asarray(vv), rcond=None)[0]
    return float(max(k, 1e-3)), float(max(r2, 0.0))


def _prep(A: np.ndarray, win: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = A.astype(np.float32)
    a = a - a.mean(axis=(1, 2), keepdims=True)
    a = a * win
    return a, np.sqrt((a * a).sum(axis=(1, 2)))


def zncc_shift(A: np.ndarray, B: np.ndarray, max_shift: int,
               chunk: int = 512, excl: int = UNIQ_EXCL
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Tiled ZNCC, integer peak with a parabolic guess, window-bias corrected.

    A, B : (N, T, T) float32.  Returns (d, rho, edge, uniq).

    d      (N,2) as (dy, dx) in plane px -- **the displacement that carries
           content from A to B**.
    rho    the ZNCC peak height.
    edge   peak sat on the search-window boundary: a bound, not a measurement.
    uniq   PEAK UNIQUENESS, (peak - best_rival) / peak, where best_rival is the
           highest point of the surface more than `excl` plane px away.

    Why uniqueness is returned and gated on.  A high peak is not the same as an
    unambiguous one, and three separate control failures turned out to be the
    same thing:

      * repetitive content (text, a ruler's mm ticks) offers the correlator
        several equally good answers one period apart, and it takes whichever
        noise favours -- a whole period of spurious "motion";
      * a heavily blurred tile has a broad, flat correlation plateau, so the
        argmax wanders across the plateau under noise;
      * the two green sub-lattices of one exposure alias differently near
        Nyquist, which likewise produces rival peaks.

    In all three the peak is TALL and the answer is WORTHLESS.  rho cannot see
    it; the margin to the best rival can.

    The sign convention above is not asserted, it is pinned by two independent
    controls: C2 recovers a planted similarity with the sign as written, and C7
    recovers the (-0.5, +0.5) plane px offset between the two green sub-lattices
    of one exposure, which is fixed by the CFA geometry and not by this code.

    Call `refine_shift` on the tiles you intend to keep: the parabolic peak here
    is good enough to gate on, and not good enough to publish.
    """
    n, t, _ = A.shape
    win = hann2d(t)
    Awn, _, _ = window_autocorr(t)
    d = np.full((n, 2), np.nan, np.float64)
    rho = np.zeros(n, np.float64)
    uniq = np.zeros(n, np.float64)
    edge = np.zeros(n, bool)
    c0 = t // 2
    lo, hi = c0 - max_shift, c0 + max_shift + 1
    env = np.maximum(Awn[lo:hi, lo:hi], 0.2)[None, :, :]
    ww = 2 * max_shift + 1
    gy, gx = np.mgrid[0:ww, 0:ww]

    for s in range(0, n, chunk):
        a, na = _prep(A[s:s + chunk], win)
        b, nb = _prep(B[s:s + chunk], win)
        ok = (na > 0) & (nb > 0)
        na = np.where(ok, na, 1.0)
        nb = np.where(ok, nb, 1.0)

        C = np.fft.irfft2(np.fft.rfft2(b) * np.conj(np.fft.rfft2(a)), s=(t, t))
        C = np.fft.fftshift(C, axes=(1, 2)) / (na * nb)[:, None, None]
        W = C[:, lo:hi, lo:hi] / env

        m = W.shape[0]
        flat = W.reshape(m, -1).argmax(axis=1)
        py, px = np.unravel_index(flat, W.shape[1:])
        peak = W.reshape(m, -1)[np.arange(m), flat]
        on_edge = (py == 0) | (px == 0) | (py == W.shape[1] - 1) | (px == W.shape[2] - 1)
        sy, sx = _parabolic_peak(W, py, px, peak, on_edge)

        far = (np.abs(gy[None] - py[:, None, None]) > excl) | \
              (np.abs(gx[None] - px[:, None, None]) > excl)
        rival = np.where(far, W, -np.inf).reshape(m, -1).max(axis=1)
        rival = np.where(np.isfinite(rival), rival, 0.0)
        u = (peak - rival) / np.maximum(peak, 1e-9)
        u[peak <= 0] = 0.0

        d[s:s + chunk, 0] = (py - max_shift) + sy
        d[s:s + chunk, 1] = (px - max_shift) + sx
        r = peak.copy()
        r[on_edge] = 0.0            # a peak on the search edge is not a measurement
        r[~ok[:m]] = 0.0
        rho[s:s + chunk] = r
        uniq[s:s + chunk] = np.where(ok[:m] & ~on_edge, u, 0.0)
        edge[s:s + chunk] = on_edge
    return d, rho, edge, uniq


def _parabolic_peak(W, py, px, peak, on_edge):
    m = W.shape[0]
    ar = np.arange(m)
    sy = np.zeros(m)
    sx = np.zeros(m)
    if (~on_edge).any():
        i = ar[~on_edge]
        for axis, out in ((0, sy), (1, sx)):
            if axis == 0:
                cm, cp = W[i, py[i] - 1, px[i]], W[i, py[i] + 1, px[i]]
            else:
                cm, cp = W[i, py[i], px[i] - 1], W[i, py[i], px[i] + 1]
            den = cm - 2 * peak[i] + cp
            good = np.abs(den) > 1e-12
            v = np.zeros(i.size)
            v[good] = 0.5 * (cm[good] - cp[good]) / den[good]
            out[i] = v
    return np.clip(sy, -1, 1), np.clip(sx, -1, 1)


def refine_shift(A: np.ndarray, B: np.ndarray, d0: np.ndarray,
                 usfac: int = 16, half: float = 1.0,
                 chunk: int = 192) -> np.ndarray:
    """Sub-pixel refinement by upsampled inverse DFT, window-bias corrected.

    d0 : (N,2) integer-ish starting shifts, (dy, dx) plane px.  Returns refined
    (N,2).  Run only on the tiles that survived the gates -- it is the expensive
    step and a rejected tile's displacement is never used.

    cc(y,x) = sum_{u,v} P[u,v] exp(2i*pi*(f_u*y + f_v*x)) is the ordinary inverse
    DFT evaluated off the integer grid.  SIGNED frequencies are mandatory:
    exp(2i*pi*u*y/T) and exp(2i*pi*(u-T)*y/T) agree only when y is an integer,
    which is exactly the case this routine exists to leave.  The same evaluation
    is applied to the window's own spectrum and divided out, so the fine grid
    carries no more window bias than the integer grid does.
    """
    n, t, _ = A.shape
    out = np.array(d0, dtype=np.float64, copy=True)
    if n == 0:
        return out
    win = hann2d(t)
    _, Pw, Pw_sum = window_autocorr(t)
    fs = np.fft.fftfreq(t).astype(np.float32)
    k = int(round(2 * half * usfac)) + 1
    off = ((np.arange(k) - (k - 1) / 2.0) / usfac).astype(np.float32)
    iy = np.rint(d0[:, 0]).astype(np.float64)
    ix = np.rint(d0[:, 1]).astype(np.float64)

    for s in range(0, n, chunk):
        sl = slice(s, min(s + chunk, n))
        a, na = _prep(A[sl], win)
        b, nb = _prep(B[sl], win)
        P = (np.fft.fft2(b) * np.conj(np.fft.fft2(a))).astype(np.complex64)
        ys = (iy[sl][:, None] + off[None, :]).astype(np.float32)
        xs = (ix[sl][:, None] + off[None, :]).astype(np.float32)
        kr = np.exp(2j * np.pi * (ys[:, :, None] * fs[None, None, :])).astype(np.complex64)
        kc = np.exp(2j * np.pi * (fs[None, :, None] * xs[:, None, :])).astype(np.complex64)
        cc = np.abs(np.matmul(kr, np.matmul(P, kc)))
        aw = np.abs(np.matmul(kr, np.matmul(Pw[None], kc))) / Pw_sum
        surf = cc / np.maximum(aw, 0.2)
        m = surf.shape[0]
        fl = surf.reshape(m, -1).argmax(axis=1)
        ky, kx = np.unravel_index(fl, (k, k))
        out[sl, 0] = iy[sl] + off[ky]
        out[sl, 1] = ix[sl] + off[kx]
    return out


# ------------------------------------------------- the shipped model class

@dataclass
class SimilarityFit:
    u: complex          # a - 1 : scale-minus-one and rotation, together
    b: complex          # translation, plane px
    inliers: np.ndarray
    n_used: int
    mad: float

    def predict(self, pc: np.ndarray) -> np.ndarray:
        """pc: (N,) complex, tile centres relative to the plane centre.
        Returns predicted displacement as (N,) complex, plane px."""
        return self.u * pc + self.b

    @property
    def scale_minus_one(self) -> float:
        return float(np.real(self.u))

    @property
    def rotation_rad(self) -> float:
        return float(np.imag(self.u))


def fit_similarity(pc: np.ndarray, d: np.ndarray, w: np.ndarray,
                   mad_k: float = 3.0) -> SimilarityFit:
    """Weighted complex linear least squares for `d = u*pc + b`, one MAD pass.

    This is the shipped aligner's estimator: four real parameters carried as two
    complex ones, fitted to the tile displacement field, with a single MAD
    outlier rejection pass (align.rs, "least-squares fit of the similarity to
    the tile displacement field, one MAD outlier pass").
    """
    def solve(mask):
        p, dd, ww = pc[mask], d[mask], w[mask]
        if p.size < 6:
            return None
        M = np.stack([p, np.ones_like(p)], axis=1)
        Mw = M * ww[:, None]
        A = Mw.conj().T @ M
        rhs = Mw.conj().T @ dd
        try:
            sol = np.linalg.solve(A, rhs)
        except np.linalg.LinAlgError:
            return None
        return complex(sol[0]), complex(sol[1])

    mask = np.ones(pc.shape, bool)
    sol = solve(mask)
    if sol is None:
        return SimilarityFit(0j, 0j, mask, 0, np.nan)
    u, b = sol
    res = np.abs(d - (u * pc + b))
    med = float(np.median(res))
    mad = float(np.median(np.abs(res - med))) * 1.4826
    keep = res <= med + mad_k * max(mad, 1e-6)
    sol2 = solve(keep)
    if sol2 is not None:
        u, b = sol2
        mask = keep
    return SimilarityFit(u, b, mask, int(mask.sum()), mad)


def fit_affine(pc: np.ndarray, d: np.ndarray, w: np.ndarray, mad_k: float = 3.0):
    """Six-parameter real affine fit -- a STRICTLY MORE PERMISSIVE model than the
    one that ships.  Used only as a conservative cross-check: residual against
    affine is a lower bound on residual against the shipped similarity, so if
    affine still leaves motion, the shipped path certainly does."""
    x, y = np.real(pc), np.imag(pc)
    dx, dy = np.real(d), np.imag(d)
    M = np.stack([x, y, np.ones_like(x)], axis=1)

    def solve(mask):
        if mask.sum() < 8:
            return None
        Mw = M[mask] * w[mask, None]
        A = Mw.T @ M[mask]
        try:
            cx = np.linalg.solve(A, Mw.T @ dx[mask])
            cy = np.linalg.solve(A, Mw.T @ dy[mask])
        except np.linalg.LinAlgError:
            return None
        return cx, cy

    mask = np.ones(pc.shape, bool)
    s = solve(mask)
    if s is None:
        return None, mask
    cx, cy = s
    res = np.hypot(M @ cx - dx, M @ cy - dy)
    med = float(np.median(res))
    mad = float(np.median(np.abs(res - med))) * 1.4826
    keep = res <= med + mad_k * max(mad, 1e-6)
    s2 = solve(keep)
    if s2 is not None:
        cx, cy = s2
        mask = keep
    return (cx, cy), mask


def affine_predict(coef, pc: np.ndarray) -> np.ndarray:
    cx, cy = coef
    x, y = np.real(pc), np.imag(pc)
    M = np.stack([x, y, np.ones_like(x)], axis=1)
    return (M @ cx) + 1j * (M @ cy)


# ----------------------------------------------------------------- the pass

@dataclass
class PairResult:
    ok: bool
    reason: str = ""
    n_coarse: int = 0
    n_coarse_used: int = 0
    n_fine_total: int = 0
    n_fine_gated_focus: int = 0
    n_fine_gated_rho: int = 0
    n_fine_gated_both: int = 0
    n_fine_saturated: int = 0     # residual larger than the search window: a BOUND
    n_fine_kept: int = 0
    sim: SimilarityFit | None = None
    origins: np.ndarray | None = None      # (K,2) plane px, kept fine tiles
    resid: np.ndarray | None = None        # (K,) complex, plane px
    resid_affine: np.ndarray | None = None
    stats: dict = field(default_factory=dict)

    def census(self) -> dict:
        """Every fine tile in exactly one bucket; the buckets sum to the total."""
        d = {"kept": self.n_fine_kept, "gated_focus": self.n_fine_gated_focus,
             "gated_confidence": self.n_fine_gated_rho, "gated_both": self.n_fine_gated_both,
             "saturated": self.n_fine_saturated}
        d["total"] = self.n_fine_total
        assert sum(v for k, v in d.items() if k != "total") == self.n_fine_total, \
            f"bucket partition {d} does not sum to total"
        return d


def measure_pair(ga: np.ndarray, gb: np.ndarray,
                 noise: tuple[float, float] | None = None,
                 tile_coarse: int = TILE_COARSE, stride_coarse: int = STRIDE_COARSE,
                 tile_fine: int = TILE_FINE, stride_fine: int = STRIDE_FINE,
                 max_shift_coarse: int = MAX_SHIFT_COARSE,
                 max_resid: int = MAX_RESID,
                 rho_floor: float = RHO_FLOOR,
                 uniq_floor: float = UNIQ_FLOOR,
                 focus_match_max_ln: float = FOCUS_MATCH_MAX_LN,
                 hf_sig_min_rel: float = HF_SIG_MIN_REL,
                 usfac: int = USFAC) -> PairResult:
    """Residual local displacement between two plane images.

    Stage 1 -- coarse tiles establish the global similarity.  That is the
               aligner's whole job, and it is fitted here in the aligner's own
               model class so the leftover is genuinely the leftover.
    Stage 2 -- fine tiles are correlated in a window centred ON THE GLOBAL
               PREDICTION, so the number that comes out is the residual itself
               rather than a large displacement minus a large prediction.  A
               narrow window also denies a low-texture tile the chance to find a
               spurious peak 10 px away and call it motion.

    Every fine tile lands in exactly one of five buckets -- kept, gated on
    focus, gated on confidence, gated on both, or saturated against the search
    window -- and `PairResult.census()` asserts they sum to the total.
    """
    h, w = ga.shape
    cy0, cx0 = (h - 1) / 2.0, (w - 1) / 2.0
    if noise is None:
        ka, ra = photon_transfer(ga)
        kb, rb = photon_transfer(gb)
        k, r2 = 0.5 * (ka + kb), 0.5 * (ra + rb)
    else:
        k, r2 = noise

    def focus_gate(A, B):
        hfa, sa = hf_modulation(A, k, r2)
        hfb, sb = hf_modulation(B, k, r2)
        struct = (hfa >= hf_sig_min_rel * sa) & (hfb >= hf_sig_min_rel * sb)
        lnr = np.abs(np.log(np.maximum(hfa, 1e-12) / np.maximum(hfb, 1e-12)))
        return struct & (lnr <= focus_match_max_ln), lnr

    # ---- Stage 1: the global similarity
    oc = tile_origins((h, w), tile_coarse, stride_coarse, max_shift_coarse)
    if oc.shape[0] < 8:
        return PairResult(False, "plane too small for the coarse grid")
    A = gather_tiles(ga, oc, tile_coarse)
    B = gather_tiles(gb, oc, tile_coarse)
    fokC, _ = focus_gate(A, B)
    dC, rhoC, edgeC, uniqC = zncc_shift(A, B, max_shift_coarse)

    # No uniqueness gate here, deliberately.  A 256 px coarse tile of natural
    # texture has a BROAD correlation peak -- natural images are close to 1/f,
    # so the surface three plane px from the peak is still ~0.9 of it -- and a
    # margin test reads that as ambiguity.  Measured: gating the coarse stage at
    # uniq>=0.15 passed 3 of 400 tiles, collapsing the similarity fit to the
    # identity and turning every fine "residual" into the whole 7.4 plane px
    # warp.  The coarse stage keeps rho plus fit_similarity's MAD pass, which is
    # exactly what align.rs itself uses.  Uniqueness belongs to the fine stage,
    # where the tile is 64 px, the search is +/-8, and ambiguity is real.
    okC = fokC & (rhoC >= rho_floor) & ~edgeC & np.isfinite(dC).all(axis=1)
    if okC.sum() < 8:
        del A, B
        return PairResult(False, f"only {int(okC.sum())} of {oc.shape[0]} coarse tiles "
                                 f"passed the gates", n_coarse=int(oc.shape[0]))
    dC[okC] = refine_shift(A[okC], B[okC], dC[okC], usfac=usfac)
    del A, B

    pcC = ((oc[:, 1] + tile_coarse / 2 - cx0) + 1j * (oc[:, 0] + tile_coarse / 2 - cy0))[okC]
    dcx = (dC[okC, 1] + 1j * dC[okC, 0])
    sim = fit_similarity(pcC, dcx, rhoC[okC])
    aff, _ = fit_affine(pcC, dcx, rhoC[okC])

    # ---- Stage 2: local residual, searched about the global prediction
    of = tile_origins((h, w), tile_fine, stride_fine, max_shift_coarse + max_resid)
    n_tot = int(of.shape[0])
    pc_all = (of[:, 1] + tile_fine / 2 - cx0) + 1j * (of[:, 0] + tile_fine / 2 - cy0)
    dpred = sim.predict(pc_all)
    shift_i = np.stack([np.rint(np.imag(dpred)).astype(int),
                        np.rint(np.real(dpred)).astype(int)], axis=1)
    ob = of + shift_i
    inb = ((ob[:, 0] >= 0) & (ob[:, 0] <= h - tile_fine)
           & (ob[:, 1] >= 0) & (ob[:, 1] <= w - tile_fine))
    ob = np.clip(ob, [0, 0], [h - tile_fine, w - tile_fine])

    A = gather_tiles(ga, of, tile_fine)
    B = gather_tiles(gb, ob, tile_fine)
    fok, lnr = focus_gate(A, B)
    focus_ok = fok & inb
    dF, rhoF, edgeF, uniqF = zncc_shift(A, B, max_resid)

    # "Confidence" is two things, and a tile must clear both: the peak must be
    # TALL (rho) and it must be UNAMBIGUOUS (uniq).  Height alone passed the
    # periodic-content and blur-plateau tiles that broke C4, C6 and C7.
    rho_ok = (rhoF >= rho_floor) & (uniqF >= uniq_floor) & np.isfinite(dF).all(axis=1)
    n_amb = int((focus_ok & (rhoF >= rho_floor) & (uniqF < uniq_floor) & ~edgeF).sum())
    sat = focus_ok & edgeF                     # structure present, residual off the end
    keep = focus_ok & rho_ok & ~edgeF
    if keep.any():
        dF[keep] = refine_shift(A[keep], B[keep], dF[keep], usfac=usfac)
    del A, B

    res = PairResult(
        True,
        n_coarse=int(oc.shape[0]), n_coarse_used=sim.n_used,
        n_fine_total=n_tot,
        n_fine_gated_focus=int((~focus_ok & rho_ok).sum()),
        n_fine_gated_rho=int((focus_ok & ~rho_ok & ~edgeF).sum()),
        n_fine_gated_both=int((~focus_ok & ~rho_ok).sum()),
        n_fine_saturated=int(sat.sum()),
        n_fine_kept=int(keep.sum()),
        sim=sim,
    )
    res.census()   # asserts the partition

    if keep.sum() == 0:
        res.ok = False
        res.reason = "no fine tile passed the gates"
        return res

    # residual = locally measured shift, plus the rounding we took out of the
    # prediction when we gathered B on the integer grid.
    remainder = (shift_i[keep, 1] - np.real(dpred[keep])) \
        + 1j * (shift_i[keep, 0] - np.imag(dpred[keep]))
    res.origins = of[keep]
    res.resid = (dF[keep, 1] + 1j * dF[keep, 0]) + remainder
    if aff is not None:
        res.resid_affine = res.resid + (sim.predict(pc_all[keep]) - affine_predict(aff, pc_all[keep]))
    res.stats.update({
        "rho_kept_median": float(np.median(rhoF[keep])),
        "uniq_kept_median": float(np.median(uniqF[keep])),
        # of the tiles gated on confidence, how many were rejected for AMBIGUITY
        # rather than for a low peak.  A sub-count, not a bucket: the five-bucket
        # partition above is what has to sum, and this must not disturb it.
        "n_gated_ambiguous": n_amb,
        # THE OPERATING POINT: how much the focus actually differs between these
        # two frames, over the tiles that were used.  This is the number that
        # says where a real corpus pair sits on the C4 defocus-null ladder, and
        # therefore what the detector's floor is FOR THIS PAIR.
        "focus_diff_ln_p50": float(np.median(lnr[keep])),
        "focus_diff_ln_p90": float(np.percentile(lnr[keep], 90)),
        "photon_k": k, "photon_r2": r2,
        "sim_scale_minus_one": sim.scale_minus_one,
        "sim_rotation_rad": sim.rotation_rad,
        "sim_tx_plane": float(np.real(sim.b)),
        "sim_ty_plane": float(np.imag(sim.b)),
        "sim_mad_plane": sim.mad,
    })
    return res


def resid_summary(r: PairResult, prefix: str = "") -> dict:
    """Residual magnitude distribution, reported in SENSOR px."""
    if not r.ok or r.resid is None:
        return {}
    m = np.abs(r.resid) * PLANE_TO_SENSOR
    out = {
        f"{prefix}n": int(m.size),
        f"{prefix}p50": float(np.percentile(m, 50)),
        f"{prefix}p90": float(np.percentile(m, 90)),
        f"{prefix}p99": float(np.percentile(m, 99)),
        f"{prefix}max": float(m.max()),
    }
    if r.resid_affine is not None:
        ma = np.abs(r.resid_affine) * PLANE_TO_SENSOR
        out[f"{prefix}p99_affine"] = float(np.percentile(ma, 99))
    return out


def clusters(origins: np.ndarray, resid: np.ndarray, thresh_sensor: float,
             stride: int = STRIDE_FINE) -> list[dict]:
    """Connected groups of over-threshold tiles, with the coherence of their
    residual vectors.  Detector noise is spatially white and directionally
    random; real motion is contiguous and points one way.  This is what
    separates a scatter of unlucky tiles from a thing that moved."""
    m = np.abs(resid) * PLANE_TO_SENSOR
    hot = np.nonzero(m >= thresh_sensor)[0]
    if hot.size == 0:
        return []
    pts = origins[hot]
    key = {(int(p[0]) // stride, int(p[1]) // stride): i for i, p in enumerate(pts)}
    seen, out = set(), []
    for start in range(len(pts)):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            i = stack.pop()
            comp.append(i)
            gy, gx = int(pts[i][0]) // stride, int(pts[i][1]) // stride
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    j = key.get((gy + dy, gx + dx))
                    if j is not None and j not in seen:
                        seen.add(j)
                        stack.append(j)
        comp = np.asarray(comp)
        v = resid[hot[comp]]
        coh = float(np.abs(v.mean()) / max(np.abs(v).mean(), 1e-9))
        half = TILE_FINE / 2.0     # origins are tile corners; a crop wants centres
        pk = pts[comp][np.argmax(m[hot[comp]])]
        out.append({
            "n_tiles": int(comp.size),
            "peak_sensor_px": float(m[hot[comp]].max()),
            "mean_sensor_px": float(m[hot[comp]].mean()),
            "coherence": coh,
            "mean_dir_plane_yx": [float(v.mean().imag), float(v.mean().real)],
            "centre_plane_yx": [float(pts[comp][:, 0].mean() + half),
                                float(pts[comp][:, 1].mean() + half)],
            "peak_plane_yx": [float(pk[0] + half), float(pk[1] + half)],
        })
    out.sort(key=lambda c: (-c["n_tiles"], -c["peak_sensor_px"]))
    return out


def frames_of(subject_dir: str) -> list[str]:
    fs = sorted(f for f in os.listdir(subject_dir) if f.lower().endswith(".arw"))
    return [os.path.join(subject_dir, f) for f in fs]
