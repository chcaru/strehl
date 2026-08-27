"""Reimplement the SHIPPING pyramid merge offline and measure its winner field.

Why this exists
---------------
ORCH commissioned a falsifier for a "response-relative tolerance" fix aimed at
an absolute tolerance of 0.086063 response units. That constant does not occur
in `pyramid.rs` -- the shipping merge -- at all. The shipping selection is

    floor  = gate * beta_k * var          (gate = 2.0)
    excess = max(band_power - floor, 0)
    w      = (excess / max(floor,1) / SNR_REF)^p        SNR_REF = 64

which is a signal-to-noise RATIO raised to a per-band exponent. It is already
relative to the local noise floor. So the knob that exists on the shipping path
is the EXPONENT RAMP, not a tolerance, and `pyramid.rs` says so itself:

    "The rate is driven by the selection exponent, not the gate: 0 violations
     at exponent <= 1, 72 at exponent 8, 511 at 16."

This module measures the plateau structure the mottle story predicts, and runs
the counterfactual on the knob that is actually there.

Fidelity: what is reproduced, and what is guessed
------------------------------------------------
Reproduced from `git show 9b05d0b7:crates/strehl-core/src/pyramid.rs`:
  * KERNEL = [1,4,6,4,1]/16, separable, used for both reduce and expand.
  * Laplacian pyramid of GREEN luma; selection is on green only and the weight
    field is shared across colour planes (`accumulate_level`).
  * `sq = L^2` then `smooth5(sq)` at the same scale (line 1326-1332).
  * Gaussian pyramid of the per-pixel variance (`build_gaussian`, line 1317).
  * `floor / excess / select_weight` exactly as above (lines 1351-1362, 2092).
  * `exponent_at(k, nb) = exponent * sharpen^(nb-1-k)` capped at MAX_EXPONENT
    = 8, k = 0 finest (lines 1050-1057, 1075).
  * base band = plain mean (`BaseBand::Mean`, line 1101).
  * fallback where `den <= 0`: unweighted mean over all frames (line ~1367 doc).
  * `Hull::InputRange` clamp to the per-pixel [min,max] of the inputs (line
    1108), taken from the frames as supplied.

GUESSED, and stated because a structural claim inherits every rule a number
does:
  * `variance` -- the calibrated per-pixel green-luma noise variance in DN^2.
    The calibration is not in the crate, so it is FITTED here by photon
    transfer (var = read2 + g * signal) from the frames themselves. Sensitivity
    to it is measured, not assumed: see `--varscale`.
  * `beta_k` is TAKEN FROM PROVENANCE (the binary's own self-report) rather
    than recomputed, so it is not a guess, but it was measured on the full
    7032 px frame and is applied here to a 900 px tile at native resolution.
    The kernel is scale-free so level k is the same physical scale in both.
"""
import io
import json
import os
import sys

import numpy as np

K = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0
SNR_REF = 64.0
# The Rust clamp bound on `p * ln(r)`. Overridable ONLY so the positive
# control can force it to bind; the shipping value is 80.0.
_CLAMP = 80.0
MAX_EXPONENT = 8.0
BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\plateau"


from scipy.ndimage import convolve1d


def smooth5(a):
    """Separable binomial [1,4,6,4,1]/16 with edge replication.

    `mode="nearest"` replicates the border sample, which is what the crate's
    clamped index does. Verified by `constant_is_preserved` in the self-test:
    a constant image must survive smooth/reduce/expand exactly, and it cannot
    if the border handling differs.
    """
    return convolve1d(convolve1d(a, K, axis=0, mode="nearest"),
                      K, axis=1, mode="nearest")


def reduce_(a):
    return smooth5(a)[::2, ::2]


def _smooth5_zero(a):
    """smooth5 with zero extension, for the zero-inserted expand lattice."""
    return convolve1d(convolve1d(a, K, axis=0, mode="constant", cval=0.0),
                      K, axis=1, mode="constant", cval=0.0)


def expand(a, shape):
    """Upsample by zero insertion, then interpolate, NORMALISED by the lattice.

    MEASURED BUG, and the reason this is not simply `4 * smooth5(up)`. That
    form is exact in the interior and catastrophically wrong at the border:
    expanding a constant 1200 gave interior std 0.0000 but min 300 / max 2700
    and an overall std of 61.87, because `mode="nearest"` replicates the edge
    sample of the ZERO-INSERTED array and so destroys the even/odd tap balance
    that makes the gain uniform. That border ring then dominated the finest
    Laplacian level, which is why a sigma=5 blur moved the sharpness statistic
    by 7% when it should have collapsed it.

    Dividing by the identically-smoothed lattice mask is exact everywhere: in
    the interior the mask smooths to 0.25 and this reduces to the 4x form, and
    at the border it divides out exactly the taps that fell off the edge.
    """
    h, w = shape
    up = np.zeros((h, w), dtype=np.float64)
    msk = np.zeros((h, w), dtype=np.float64)
    up[::2, ::2] = a[:(h + 1) // 2, :(w + 1) // 2]
    msk[::2, ::2] = 1.0
    return _smooth5_zero(up) / np.maximum(_smooth5_zero(msk), 1e-12)


def gauss_pyr(a, nb):
    g = [a]
    for _ in range(nb):
        g.append(reduce_(g[-1]))
    return g


def lap_pyr(a, nb):
    g = gauss_pyr(a, nb)
    lap = [g[k] - expand(g[k + 1], g[k].shape) for k in range(nb)]
    return lap, g[nb]


def exponent_at(k, nb, exponent, sharpen):
    if sharpen == 1.0:
        return exponent
    return min(exponent * (sharpen ** (nb - 1 - k)), MAX_EXPONENT)


def select_weight(excess, floor, p, count=None):
    """Faithful to `9b05d0b7:crates/strehl-core/src/pyramid.rs:2092-2110`.

    The Rust has two UNCLAMPED fast paths that the first version of this
    function did not reproduce:

        if p == 1.0 { r } else if p == 2.0 { r * r }
        else { (p * r.ln()).clamp(-80.0, 80.0).exp() }

    `exponent_at` returns exactly 2.0 at the coarsest band under the shipping
    ramp, so the coarsest band really does take the unclamped path on every
    delivered image. Reproducing it matters for the SNR_REF question, because
    the clamp is the ONLY reason SNR_REF fails to cancel.

    `count`, if given, is a dict that accumulates how often the clamp binds.
    """
    r = excess / np.maximum(floor, 1.0) / SNR_REF
    w = np.zeros_like(r)
    m = excess > 0.0
    if not np.any(m):
        return w
    if p == 1.0:
        w[m] = r[m]
    elif p == 2.0:
        w[m] = r[m] * r[m]
    else:
        t = p * np.log(r[m])
        if count is not None:
            count["binding"] = count.get("binding", 0) + int(
                np.count_nonzero((t < -_CLAMP) | (t > _CLAMP)))
            count["total"] = count.get("total", 0) + int(t.size)
        w[m] = np.exp(np.clip(t, -_CLAMP, _CLAMP))
    return w


def fit_variance(green):
    """Photon transfer: var = read2 + g * signal, fitted from the frame itself.

    MEASURED FAILURE that shaped this function. The first version binned by
    intensity and took the MEDIAN of the robust sigma in each bin. It returned

        var = 10354.9 + -3.6972 * S   DN^2

    a NEGATIVE photon gain, which is physically impossible: shot noise variance
    rises with signal. The cause is that bright bins on this subject are bright
    because they contain sharp detail, so the median |L0| there measures
    structure, not noise. A negative slope then drives `floor` to its clamp at
    bright pixels and makes every weight there extreme -- it would have
    contaminated every number in this report.

    Two changes: a LOW quantile of |L0| per bin (flat patches dominate the low
    tail, detail cannot pull it up), and a non-negativity constraint on the
    gain. The fit is still a guess, so `varscale` exists and the sensitivity is
    reported rather than assumed.
    """
    lap, _ = lap_pyr(green, 1)
    l0 = np.abs(lap[0])
    beta0 = 0.8898
    # half-normal: P(|X| <= q) = 0.2  =>  q = 0.2533 sigma
    Q, QS = 20.0, 0.2533
    lo, hi = np.percentile(green, [1, 99])
    edges = np.linspace(lo, hi, 13)
    xs, ys = [], []
    for i in range(len(edges) - 1):
        m = (green >= edges[i]) & (green < edges[i + 1])
        if m.sum() < 500:
            continue
        xs.append(float(green[m].mean()))
        ys.append(float((np.percentile(l0[m], Q) / QS) ** 2 / beta0))
    if len(xs) < 3:
        v = float((np.percentile(l0, Q) / QS) ** 2 / beta0)
        return np.full_like(green, max(v, 1.0)), v, 0.0
    xs, ys = np.array(xs), np.array(ys)
    A = np.vstack([np.ones(len(xs)), xs]).T
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    read2, g = float(coef[0]), float(coef[1])
    if g < 0.0:
        # Shot noise cannot fall with signal. Refuse the slope, keep a level.
        g = 0.0
        read2 = float(np.median(ys))
    read2 = max(read2, 1.0)
    v = read2 + g * np.maximum(green, 0.0)
    return np.maximum(v, 1.0), read2, g


def merge(frames, cfg, beta, var0, nb=7):
    """Return (reconstruction HxWx3, per-level weight stacks, per-level luma)."""
    exponent = cfg["exponent"]
    sharpen = cfg["sharpen"]
    gate = cfg["gate"]
    mode = cfg.get("mode", "shipping")

    h, w = frames[0].shape[:2]
    laps, bases, plane_laps, plane_bases = [], [], [], []
    for f in frames:
        pl, pb = [], []
        for c in range(3):
            Lc, Bc = lap_pyr(f[:, :, c].astype(np.float64), nb)
            pl.append(Lc)
            pb.append(Bc)
        plane_laps.append(pl)
        plane_bases.append(pb)
        # Channel 1 IS the luma plane, so this aliases rather than recomputing.
        laps.append(pl[1])
        bases.append(pb[1])

    varp = gauss_pyr(var0, nb)
    n = len(frames)
    out_lv, wstack_lv = [], []

    for k in range(nb):
        p = exponent_at(k, nb, exponent, sharpen)
        vv = varp[k]
        ws = []
        for i in range(n):
            sq = smooth5(laps[i][k] ** 2)
            floor = gate * beta[k] * np.maximum(vv, 0.0)
            excess = np.maximum(sq - floor, 0.0)
            ws.append(select_weight(excess, floor, p, count=cfg.get("_clamp")))
        W = np.stack(ws)
        if mode == "mean":
            W = np.zeros_like(W)
        wstack_lv.append(W)
        den = W.sum(axis=0)
        chans = []
        for c in range(3):
            num = sum(W[i] * plane_laps[i][c][k] for i in range(n))
            usum = sum(plane_laps[i][c][k] for i in range(n))
            o = np.where(den > 0.0, num / np.maximum(den, 1e-30), usum / n)
            chans.append(o)
        out_lv.append(chans)

    base = [np.mean([plane_bases[i][c] for i in range(n)], axis=0)
            for c in range(3)]

    rec = np.zeros((h, w, 3), dtype=np.float64)
    for c in range(3):
        R = base[c]
        for k in range(nb - 1, -1, -1):
            R = expand(R, out_lv[k][c].shape) + out_lv[k][c]
        rec[:, :, c] = R

    if cfg.get("hull", True):
        # Running min/max, exactly equal to stacking every frame but without
        # holding n x H x W x 3 float64 at once (1.5 GB at n=79).
        lo = frames[0].astype(np.float64)
        hi = lo.copy()
        for f in frames[1:]:
            ff = f.astype(np.float64)
            np.minimum(lo, ff, out=lo)
            np.maximum(hi, ff, out=hi)
        rec = np.clip(rec, lo, hi)
    return rec, wstack_lv
