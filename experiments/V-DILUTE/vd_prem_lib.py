# -*- coding: utf-8 -*-
"""V-DILUTE: candidate-set control against the SELECTION PREMIUM.

Assignment: find the control over the CANDIDATE SET that removes the premium
(V-NEVERWORSE facts 1843-1845, `f1f40150`) while preserving sharpness on the
same pixels. Offline in NumPy; no Rust is touched.

Predictions are pre-registered in `PREREG-PREMIUM.md`, committed at `81ee69fa`
BEFORE this file produced a number.

GAUGE IS INHERITED, NOT RE-INVENTED. `smooth5`, `lap_pyr`, `expand`,
`exponent_at`, `select_weight` and `fit_variance` are imported from
V-NEVERWORSE's `vn_pyr`; the twin is their `synth`; the statistic is their
`raw_band` of the twin-merge residual against the known base; the premium is
their `arm_noise_pow / mean_noise_pow`. The commissioning gate for this whole
file is that `argmax` at N=79 on 112MSDCF reproduces **240.70x within 5%**. If
it does not, I am measuring something else and no other number here counts.

GREEN-PLANE ONLY, and it is exact rather than an approximation: every statistic
in the inherited gauge (`spectrum`, `raw_band`, `blotch`, `level`) reads
`img[:, :, 1]`. The red and blue planes cannot influence any reported number,
and the hull clamp is per-channel, so green's clamp needs only green's own
running min/max. This cuts memory 3x and time ~3x with no loss of fidelity.

THE MECHANISM UNDER TEST. In `vn_pyr.merge` the score is `smooth5(lap_i**2)`
and the value copied is `lap_i` -- the score CONTAINS the coefficient it
selects, so selection prefers whichever frame's noise inflated its own score
and then copies that noise. That is a winner's curse, and it is attacked by
DECORRELATING the score from the copied sample, not by shrinking N.
"""
import io
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage

# NOTE: this is a library and must NOT touch sys.stdout. An earlier version
# re-wrapped it at import time, which closed the runner's own wrapper and
# killed the process with "I/O operation on closed file" before any arm ran.
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl"
                   r"\experiments\V-NEVERWORSE")

import vn_pyr as VP                                    # noqa: E402
from vn_plateau import BETA, SHIP                      # noqa: E402

BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
OUT = r"D:\strehl-out\V-DILUTE\premium"
NB = 7
PREM_BAND = (0.30, 0.35)    # inherited: where the premium is scored
SHARP_BAND = (0.20, 0.25)   # qualified SIGNAL on 112MSDCF (S/y = 2.43)


# ----------------------------------------------------------------- loading
def load_green(subj):
    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    return np.stack([z[k][:, :, 1].astype(np.float64) for k in keys])


def pick(n, k):
    """Matched-range decimation, endpoints pinned (vn_ninv.pick)."""
    return sorted(set(np.linspace(0, n - 1, k).round().astype(int).tolist()))


# -------------------------------------------------------------- statistics
def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


_HANN = {}


def raw_band(g, band):
    h, w = g.shape
    if (h, w) not in _HANN:
        _HANN[(h, w)] = _hann2(h, w)
    x = g - g.mean()
    F = np.fft.rfft2(x * _HANN[(h, w)])
    p = F.real ** 2 + F.imag ** 2
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    m = (rad >= band[0]) & (rad < band[1])
    return float(p[m].mean())


# ------------------------------------------------------------ cached stack
class Stack(object):
    """Laplacian pyramids built once; every arm reuses them."""

    def __init__(self, g, nb=NB):
        self.n = len(g)
        self.h, self.w = g[0].shape
        self.nb = nb
        self.laps = []
        self.bases = []
        for i in range(self.n):
            L, B = VP.lap_pyr(g[i], nb)
            self.laps.append(L)
            self.bases.append(B)
        self.lo = g.min(axis=0)
        self.hi = g.max(axis=0)

    def level(self, k):
        return np.stack([self.laps[i][k] for i in range(self.n)])

    def reconstruct(self, out_lv, hull=True):
        R = np.mean([self.bases[i] for i in range(self.n)], axis=0)
        for k in range(self.nb - 1, -1, -1):
            R = VP.expand(R, out_lv[k].shape) + out_lv[k]
        if hull:
            R = np.clip(R, self.lo, self.hi)
        return R


# ------------------------------------------------------------------- arms
C0 = (6.0 / 16.0) ** 2      # smooth5 centre-tap weight in 2D


def base_scores(L):
    return np.stack([VP.smooth5(L[i] ** 2) for i in range(len(L))])


def loo_scores(sq, order=1):
    """Score frame i from its NEIGHBOURS in focus order, never from itself.

    Frame noise is independent across captures, so excluding i removes the
    winner's curse EXACTLY -- unlike a spatial puncture, which leaves the
    band's own spatial correlation behind. Defocus is smooth in frame index,
    so the focus signal survives.

    order=1 : mean of i-1, i+1. Biased low at a peak (a chord under a convex
              maximum), which costs a little selectivity.
    order=2 : (4*m1 - m2)/3, the leave-one-out quadratic prediction at i from
              i+-1 and i+-2. Unbiased for a quadratic peak.
    """
    n = len(sq)
    out = np.empty_like(sq)
    for i in range(n):
        j1 = [j for j in (i - 1, i + 1) if 0 <= j < n]
        if order == 1 or n < 5:
            out[i] = np.mean([sq[j] for j in j1], axis=0)
        else:
            j2 = [j for j in (i - 2, i + 2) if 0 <= j < n]
            if not j2:
                out[i] = np.mean([sq[j] for j in j1], axis=0)
            else:
                m1 = np.mean([sq[j] for j in j1], axis=0)
                m2 = np.mean([sq[j] for j in j2], axis=0)
                out[i] = np.maximum((4.0 * m1 - m2) / 3.0, 0.0)
    return out


def weights_from(scores, floor, p):
    ws = []
    for i in range(len(scores)):
        excess = np.maximum(scores[i] - floor, 0.0)
        ws.append(VP.select_weight(excess, floor, p))
    return np.stack(ws)


def onehot(W, idx):
    hot = np.zeros_like(W)
    np.put_along_axis(hot, idx[None], 1.0, axis=0)
    return hot


def arm_weights(name, L, floor, p, ctx):
    """Return W, an (n,H,W) weight stack for one pyramid level.

    Names are parsed, not enumerated, so a sweep needs no new code:
      pool<S>        spatial pool of the score by gaussian sigma S, then argmax
      axis<W>        pool the score along the FOCUS AXIS W times, then argmax
      pwin<S>_<H>    pooled peak, then AVERAGE frames within +-H of it
      lvl0mean       plain mean at level 0 only, shipping elsewhere
      lvl0pool<S>    heavy spatial pool at level 0 only, shipping elsewhere
    """
    n = len(L)
    k = ctx["level"]
    if name == "mean":
        return np.zeros((n,) + L[0].shape)

    sq = ctx["sq"]
    W = ctx["W_ship"]
    den0 = W.sum(axis=0)
    live = den0 > 0.0

    if name == "shipping":
        return W
    if name == "lvl0mean":
        # The candidate set collapses to ALL frames in the band with no scene
        # content, and is untouched everywhere else.
        return np.zeros((n,) + L[0].shape) if k == 0 else W
    if name.startswith("lvl0pool"):
        if k != 0:
            return W
        s = float(name[8:])
        sq2 = np.stack([ndimage.gaussian_filter(sq[i], s) for i in range(n)])
        return weights_from(sq2, floor, p)
    if name == "argmax":
        return np.where(live[None], onehot(W, W.argmax(axis=0)), 0.0)
    if name == "random":
        r = ctx["rng"].integers(0, n, size=L[0].shape)
        return np.where(live[None], onehot(W, r), 0.0)
    if name == "oracle":
        W2 = weights_from(ctx["sq_alt"], floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name in ("loo1", "loo2"):
        sq2 = loo_scores(sq, order=1 if name == "loo1" else 2)
        W2 = weights_from(sq2, floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name == "punctured":
        sq2 = np.stack([(sq[i] - C0 * L[i] ** 2) / (1.0 - C0)
                        for i in range(n)])
        W2 = weights_from(np.maximum(sq2, 0.0), floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name.startswith("pool"):
        s = float(name[4:])
        sq2 = np.stack([ndimage.gaussian_filter(sq[i], s) for i in range(n)])
        W2 = weights_from(sq2, floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name.startswith("axis"):
        reps = int(name[4:])
        sq2 = sq.copy()
        for _ in range(reps):
            t = sq2.copy()
            sq2[1:-1] = 0.25 * t[:-2] + 0.5 * t[1:-1] + 0.25 * t[2:]
        W2 = weights_from(sq2, floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name.startswith("pwin"):
        s, half = name[4:].split("_")
        sq2 = np.stack([ndimage.gaussian_filter(sq[i], float(s))
                        for i in range(n)])
        kstar = weights_from(sq2, floor, p).argmax(axis=0)
        idx = np.arange(n)[:, None, None]
        win = (np.abs(idx - kstar[None]) <= int(half)).astype(np.float64)
        return np.where(live[None], win, 0.0)
    if name.startswith("capK"):
        K = int(name[4:])
        if K >= n:
            return W
        thr = np.sort(W, axis=0)[-K][None]
        return np.where(W >= thr, W, 0.0)
    if name == "peakfit":
        sq2 = sq.copy()
        sq2[1:-1] = 0.25 * sq[:-2] + 0.5 * sq[1:-1] + 0.25 * sq[2:]
        W2 = weights_from(sq2, floor, p)
        return np.where(live[None], onehot(W, W2.argmax(axis=0)), 0.0)
    if name.startswith("winavg"):
        half = int(name[6:])
        sq2 = loo_scores(sq, order=1)
        sq2 = np.stack([ndimage.gaussian_filter(sq2[i], 2.0)
                        for i in range(n)])
        kstar = weights_from(sq2, floor, p).argmax(axis=0)
        idx = np.arange(n)[:, None, None]
        win = (np.abs(idx - kstar[None]) <= half).astype(np.float64)
        return np.where(live[None], win, 0.0)
    raise SystemExit("unknown arm %r" % (name,))


def run_arm(name, stack, varp, rng, alt=None):
    out_lv = []
    for k in range(stack.nb):
        L = stack.level(k)
        p = VP.exponent_at(k, stack.nb, SHIP["exponent"], SHIP["sharpen"])
        floor = SHIP["gate"] * BETA[k] * np.maximum(varp[k], 0.0)
        sq = base_scores(L)
        ctx = {"sq": sq, "rng": rng, "level": k,
               "W_ship": weights_from(sq, floor, p),
               "sq_alt": base_scores(alt.level(k)) if alt is not None else None}
        W = arm_weights(name, L, floor, p, ctx)
        den = W.sum(axis=0)
        num = (W * L).sum(axis=0)
        usum = L.sum(axis=0) / len(L)
        out_lv.append(np.where(den > 0.0, num / np.maximum(den, 1e-30), usum))
        del L, sq, ctx, W
    return stack.reconstruct(out_lv)
