"""Band-limited, selection-immune per-site ceiling.

ORCH added three requirements to the gate sweep. Two of them are NOT met by
`orch_sharp1to1.patch_gain`, which is the numerator every number in
BUILD-GATE-4 was computed with:

  * REQ 3, report only <=0.25 cyc/px. `patch_gain` reports `detail(...)[0]`,
    the full-resolution first-difference gradient. Its power response is
    4 sin^2(pi f), which RISES monotonically to Nyquist -- it is weighted
    towards exactly the band three independent instruments have withdrawn.
    Section `bandsplit` measures what fraction of it actually lives there on
    real data rather than assuming the white-noise figure.

  * REQ 2, do not take a max over the reported quantity. `patch_gain` does
    exactly that: `sf = max(detail(c[sl])[0] for c in reg)`. A max over n draws
    of a noisy quantity exceeds its true value, so the reference is inflated and
    the ratio is depressed -- which biases AGAINST the merge, but by an unknown
    amount that varies with n, and n varies across subjects here from 19 to 299.

This module answers both without editing ORCH's file.

THE DISJOINT CONSTRUCTION

Select the reference frame per tile on band A (0.05-0.20 cyc/px); report the
ratio on band B (0.20-0.25). The two bands share no Fourier bins, so noise that
wins the selection in A is independent of the quantity reported in B, and no max
is ever taken over B. This is immune BY CONSTRUCTION rather than by correction,
which matters because a correction needs a model of the inflation and the model
is the thing in doubt.

Immunity by construction is still a claim, so it is COMMISSIONED: `null` builds
n statistically identical noised copies of the master and runs the same
machinery. The true ratio is then 1.000 by construction, and any deviation is
leak. Following ORCH's instruction, a subject whose leak exceeds LEAK_REFUSE is
REFUSED and its absolute number is not reported at all.

WHAT REMAINS TRUE REGARDLESS, AND WHY THE SWEEP'S CONCLUSION DOES NOT DEPEND ON
ANY OF THIS: the ceiling is built ONCE per subject and held fixed across all
seven gate arms. Selection inflation is therefore a constant common denominator
and cancels EXACTLY in every arm-to-arm delta. It biases the ABSOLUTE level and
cannot touch the COMPARISON. That was argued in BUILD-GATE-3 sec 3 against my
own interest, before any of these numbers existed, and it is tested directly in
`compare`.

Windowing: every tile is Hann-windowed before the FFT. Without it the tile edge
is a discontinuity whose spectrum spreads across all frequencies, which would
put wideband energy into band B and destroy the very band separation the
construction depends on.
"""
import glob
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "ORCH-drift-check"))

from orch_sharp1to1 import (                                      # noqa: E402
    CORR_MIN, CROP, PATCH, SEARCH, detail, luma, register,
)
from ceiling import NTILE, SRC_ROOT, pick_sites                   # noqa: E402

# Cycles per pixel. Nyquist is 0.5.
BAND_A = (0.05, 0.20)     # selection only, never reported
BAND_B = (0.20, 0.25)     # reported, never selected on
BAND_W = (0.05, 0.25)     # the whole supportable band, for the max-based arm
LEAK_REFUSE = 0.02        # refuse the absolute number above 2% leak
NULL_N = 24


def _hann(n):
    w = np.hanning(n + 2)[1:-1]
    return np.outer(w, w)


def _masks(n):
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fy ** 2 + fx ** 2)
    out = {}
    for name, (lo, hi) in (("A", BAND_A), ("B", BAND_B), ("W", BAND_W)):
        out[name] = ((f >= lo) & (f < hi))
    out["HI"] = (f >= 0.25)
    out["ALL"] = (f > 0)
    return out


_W = _hann(PATCH)
_M = _masks(PATCH)


def tile_bands(crop):
    """Per-tile band energies on the PATCH grid. Returns (ntile,ntile,3): A,B,W."""
    out = np.zeros((NTILE, NTILE, 3))
    for py in range(NTILE):
        for px in range(NTILE):
            t = crop[py * PATCH:(py + 1) * PATCH, px * PATCH:(px + 1) * PATCH]
            F = np.abs(np.fft.fft2((t - t.mean()) * _W)) ** 2
            out[py, px, 0] = F[_M["A"]].sum()
            out[py, px, 1] = F[_M["B"]].sum()
            out[py, px, 2] = F[_M["W"]].sum()
    return out


def bandsplit(crop):
    """Fraction of the FINE gradient statistic's energy above 0.25 cyc/px.

    Answers ORCH's REQ 3 question -- 'say what fraction of its energy sits in
    withdrawn territory before you quote it' -- for the statistic BUILD-GATE-4
    actually used. Measured on the real image, not on the white-noise ideal:
    real spectra fall with frequency, so the white figure (81.8% for a first
    difference) is an upper bound and the honest number must be measured.
    """
    hi_num = hi_den = 0.0
    for py in range(NTILE):
        for px in range(NTILE):
            t = crop[py * PATCH:(py + 1) * PATCH, px * PATCH:(px + 1) * PATCH]
            # The gradient operator applied in the Fourier domain, so the
            # measured split is of the STATISTIC's energy, not the image's.
            fy = np.fft.fftfreq(PATCH)[:, None]
            fx = np.fft.fftfreq(PATCH)[None, :]
            g = 4 * (np.sin(np.pi * fy) ** 2 + np.sin(np.pi * fx) ** 2)
            F = np.abs(np.fft.fft2((t - t.mean()) * _W)) ** 2 * g
            hi_num += F[_M["HI"]].sum()
            hi_den += F[_M["ALL"]].sum()
    return hi_num / hi_den if hi_den > 0 else float("nan")


def build(subject, ref_master, verbose=True):
    """One pass over the COMPLETE bracket, caching per-frame per-tile bands.

    The existing ceiling npz stores only the running max, which is why this is a
    second pass and not a re-read: a disjoint construction needs each frame's
    band B kept alongside its band A, and a max has already thrown that away.
    """
    import rawpy
    from regcheck import register_fft
    m = tifffile.imread(ref_master)[..., :3].astype(np.float64)
    sites, _ = pick_sites(m)
    if not sites:
        raise SystemExit("no site on %s survived selection" % subject)
    my = luma(m)
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if verbose:
        print("%s: %d sites, %d frames (COMPLETE)" % (subject, len(sites), len(arw)),
              flush=True)

    mb = [tile_bands(my[y:y + CROP, x:x + CROP]) for y, x in sites]
    split = float(np.mean([bandsplit(my[y:y + CROP, x:x + CROP]) for y, x in sites]))
    cache = [np.full((len(arw), NTILE, NTILE, 3), np.nan) for _ in sites]
    for n, p in enumerate(arw):
        with rawpy.imread(p) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        sy = luma(s.astype(np.float64))
        for si, (y, x) in enumerate(sites):
            if y - SEARCH < 0 or x - SEARCH < 0:
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape != (CROP + 2 * SEARCH, CROP + 2 * SEARCH):
                continue
            (dy, dx), c = register_fft(my[y:y + CROP, x:x + CROP], pad)
            if c < CORR_MIN:
                continue
            cache[si][n] = tile_bands(sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP])
        if verbose and (n + 1) % 10 == 0:
            print("    %d/%d" % (n + 1, len(arw)), flush=True)
    return {"sites": np.array(sites), "master": np.array(mb),
            "cache": np.array(cache), "subject": subject,
            "nframes": len(arw), "hi_fraction": split}


def ratios(master_b, cache):
    """Both constructions, from one cache.

    max : max over band W, the inflated construction patch_gain uses
    disj: select on band A, report band B, never a max over B
    """
    out = {}
    valid = ~np.isnan(cache[..., 0])
    # max over frames of band W
    w = np.where(valid, cache[..., 2], -np.inf)
    mx = w.max(axis=0)
    ok = np.isfinite(mx) & (mx > 0)
    out["max"] = float(np.median((master_b[..., 2][ok]) / mx[ok])) if ok.any() else float("nan")
    # disjoint: argmax on A, read B
    a = np.where(valid, cache[..., 0], -np.inf)
    pick = a.argmax(axis=0)
    b_sel = np.take_along_axis(cache[..., 1], pick[None], axis=0)[0]
    ok2 = np.isfinite(b_sel) & (b_sel > 0)
    out["disj"] = float(np.median((master_b[..., 1][ok2]) / b_sel[ok2])) if ok2.any() else float("nan")
    # Gain-invariant. A pure exposure gain g scales EVERY band by g^2, so the
    # within-image share B/W cancels it exactly. Needed because the masters are
    # rendered --auto-exposure while the ceiling frames are no_auto_bright, and
    # that gain was measured to span 0.59x-3.31x ACROSS subjects, i.e. 0.35x-
    # 10.96x in energy -- enough to dominate any absolute level.
    w_sel = np.take_along_axis(cache[..., 2], pick[None], axis=0)[0]
    ok3 = ok2 & np.isfinite(w_sel) & (w_sel > 0) & (master_b[..., 2] > 0)
    if ok3.any():
        ms = master_b[..., 1][ok3] / master_b[..., 2][ok3]
        fs = b_sel[ok3] / w_sel[ok3]
        out["share"] = float(np.median(ms / fs))
    else:
        out["share"] = float("nan")
    return out


def _sigma(y):
    """Immerkaer robust noise sigma. Standard, and cited rather than invented."""
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], float)
    from numpy.lib.stride_tricks import sliding_window_view
    v = sliding_window_view(y, (3, 3))
    r = (v * k).sum(axis=(2, 3))
    return float(np.abs(r).mean() * np.sqrt(np.pi / 2) / 6.0)


def null(ref_master, subject, n=NULL_N, scale=1.0, seed=0):
    """Forced null: n statistically identical noised copies. True ratio 1.000.

    Both arms are draws from the SAME distribution, so any departure from 1.000
    is the construction's own selection inflation and nothing else.
    """
    rng = np.random.default_rng(seed)
    m = tifffile.imread(ref_master)[..., :3].astype(np.float64)
    sites, _ = pick_sites(m)
    my = luma(m)
    res = []
    for y, x in sites:
        base = my[y:y + CROP, x:x + CROP]
        sd = _sigma(base) * scale
        mb = tile_bands(base + rng.normal(0, sd, base.shape))
        cache = np.array([tile_bands(base + rng.normal(0, sd, base.shape))
                          for _ in range(n)])
        res.append(ratios(mb, cache))
    return ({k: float(np.mean([r[k] for r in res])) for k in res[0]}, sd)
