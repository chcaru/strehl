"""M70 - through-focus spectral response library.

Reuses `experiments/m5-diffraction/m5_lib.py` verbatim for everything that was
already validated there (active-area load, green-quincunx crop, Welch
periodogram normalisation, radial averaging into *sensor* cyc/px). M5's
self-test proves the sublattice-to-sensor frequency conversion and asserts the
periodogram's absolute normalisation against a known white-noise variance to
+-0.7%; re-deriving either here would be a second chance to get them wrong.

What is NEW here:

* the noise model is taken from the SHIPPED profile
  (`crates/strehl-core/src/profile.rs`), not from `m5_lib.noise_model_var`.
  m5_lib predates M25's ISO-50 fix and M48's read-noise fix and is wrong by 2x
  at ISO 50 and by +18% in read noise above ISO 400. Constants are parsed out
  of the crate at import time and asserted, never retyped (M62's convention).
* band aggregation and the through-focus statistics.

Nothing in `crates/` is written. `profile.rs` is read as text only.
"""

from __future__ import annotations

import os
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(os.path.dirname(_HERE))  # experiments/
_REPO = os.path.dirname(_EXP)
sys.path.insert(0, os.path.join(_EXP, "m5-diffraction"))

import m5_lib as L  # noqa: E402  (path set above)

BLACK_LEVEL = L.BLACK_LEVEL
WHITE_LEVEL = L.WHITE_LEVEL
PITCH_UM = L.PITCH_UM
LAMBDA_UM = L.LAMBDA_UM


# ---------------------------------------------------------------------------
# Sensor noise model - parsed from the shipped crate, never retyped.
# ---------------------------------------------------------------------------
def _parse_profile() -> dict:
    path = os.path.join(_REPO, "crates", "strehl-core", "src", "profile.rs")
    src = open(path, encoding="utf-8").read()
    blk = src[src.index("const A7C2: CameraProfile = CameraProfile {") :]
    blk = blk[: blk.index("};")]
    out = {}
    for key in (
        "gain_divisor",
        "base_iso",
        "read_noise_e_low",
        "read_noise_e_high",
        "second_base_iso",
    ):
        m = re.search(key + r":\s*([0-9.]+)", blk)
        assert m, key
        out[key] = float(m.group(1))
    return out


PROFILE = _parse_profile()
# Guard: these are the values the corpus records. If the crate moves under us
# (M69 is live) the run must stop rather than silently re-denominate.
assert PROFILE["gain_divisor"] == 436.8, PROFILE
assert PROFILE["base_iso"] == 100.0, PROFILE
assert PROFILE["read_noise_e_low"] == 4.20, PROFILE
assert PROFILE["read_noise_e_high"] == 1.2392, PROFILE
assert PROFILE["second_base_iso"] == 400.0, PROFILE


def gain_dn_per_e(iso: float) -> float:
    """`profile.rs::gain_dn_per_e` - note the max() with base ISO, which is
    M25's ISO-50 fix (SYNTHESIS fact 550): Sony ISO 50 is an extended pull that
    reads out at base-ISO gain."""
    return max(iso, PROFILE["base_iso"]) / PROFILE["gain_divisor"]


def read_noise_e(iso: float) -> float:
    return (
        PROFILE["read_noise_e_high"]
        if iso >= PROFILE["second_base_iso"]
        else PROFILE["read_noise_e_low"]
    )


def noise_var_dn2(signal_dn: float | np.ndarray, iso: float):
    """sigma^2(S, ISO) in DN^2, S in DN above black."""
    g = gain_dn_per_e(iso)
    return g * np.asarray(signal_dn, dtype=np.float64) + (read_noise_e(iso) * g) ** 2


# ---------------------------------------------------------------------------
# Optics reference points (DERIVED, formula from M5 / fact 27-28).
# ---------------------------------------------------------------------------
def n_eff(marked_f: float, bellows_b: float = 3.0) -> float:
    return marked_f * bellows_b


def f_cutoff_sensor(marked_f: float, bellows_b: float = 3.0) -> float:
    """Diffraction cutoff in sensor cyc/px. B = 1 + m/p = 3.000 from pure
    geometry (rule 21) predicts M5's measured f/11 knee to 2.1%."""
    return PITCH_UM / (LAMBDA_UM * n_eff(marked_f, bellows_b))


# ---------------------------------------------------------------------------
# Windowed statistics of a patch, matching the periodogram's own weighting.
# ---------------------------------------------------------------------------
def w2_weighted_mean(patch: np.ndarray, tile: int, window: str = "hann") -> float:
    """Mean of `patch` under the same w^2 weighting the Welch periodogram uses.

    E[P(f)] for independent noise of per-pixel variance s_i^2 is
    sum_i w_i^2 s_i^2 / sum_i w_i^2, so the *right* signal level to feed the
    photon-transfer model is this weighted mean, not the plain mean.
    """
    n = patch.shape[0]
    step = tile // 2
    starts = list(range(0, n - tile + 1, step))
    w = L.window_2d(tile, window)
    w2 = w * w
    wsum = float(w2.sum())
    acc, cnt = 0.0, 0
    for i in starts:
        for j in starts:
            acc += float((patch[i : i + tile, j : j + tile] * w2).sum()) / wsum
            cnt += 1
    return acc / cnt


# ---------------------------------------------------------------------------
# Band machinery
# ---------------------------------------------------------------------------
# Sensor cyc/px. Fixed before any real spectrum was computed. `hi` is the band
# above the f/11 diffraction cutoff and is the built-in negative control on the
# f/11 stacks: fact 27 measures no optical signal there.
BANDS = (
    ("b1_low", 0.025, 0.050),
    ("b2", 0.050, 0.100),
    ("b3_mid", 0.100, 0.150),
    ("b4_mid", 0.150, 0.200),
    ("b5_mid", 0.200, 0.2762),
    ("b6_above_f11_cut", 0.2762, 0.3400),
)
MID_BANDS = ("b3_mid", "b4_mid", "b5_mid")


def band_index(f: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (f >= lo) & (f < hi)


def band_average(f, p, counts):
    """Return dict band -> (power, n_radial_bins, n_fft_bins)."""
    out = {}
    for name, lo, hi in BANDS:
        m = band_index(f, lo, hi)
        if not m.any():
            out[name] = (np.nan, 0, 0.0)
            continue
        # weight radial bins by their fft-bin population: this is the same as
        # averaging the underlying 2-D periodogram over the annulus.
        wgt = counts[m]
        out[name] = (
            float((p[m] * wgt).sum() / wgt.sum()),
            int(m.sum()),
            float(wgt.sum()),
        )
    return out


# ---------------------------------------------------------------------------
# Through-focus statistics. `s` is the noise-subtracted band signal power per
# frame, shape (K,).
# ---------------------------------------------------------------------------
def smooth3(x: np.ndarray) -> np.ndarray:
    """Explicit [1,2,1]/4 along the FRAME axis only, edge-replicated.

    Rule 23: a separable filter applied to an array with a non-spatial axis
    will touch that axis unless you stop it. Here the frame axis is the ONLY
    axis and the array is 1-D by construction, so nothing spatial is touched.
    """
    assert x.ndim == 1
    if x.size < 3:
        return x.copy()
    xp = np.concatenate([x[:1], x, x[-1:]])
    return 0.25 * xp[:-2] + 0.5 * xp[1:-1] + 0.25 * xp[2:]


def through_focus_stats(s: np.ndarray, half_window: int | None = None) -> dict:
    """Effective frame counts for a matched filter along the focus axis.

    Let A_k = |H_k(f)|.|L(f)| be the measured band amplitude of frame k. The
    latent |L(f)| is common to every frame, so A_k / max_j A_j = |H_k| /
    max_j |H_j| *without knowing the latent*: the scene cancels in the ratio.

    n_eff_MF = sum_k A_k^2 / max_k A_k^2 = sum_k S_k / max_k S_k
    is exactly the quantity in M20 fact 4.2's corrected gain shorthand:
    the matched filter's SNR gain over inverse-filtering the single best frame
    is sqrt(sum|H|^2)/max|H| = sqrt(n_eff_MF).

    `pr` is the participation ratio (sum S)^2 / sum S^2, an argmax-free
    effective count reported because `n_eff_MF`'s denominator is a max over a
    noisy response (rule 4). `n_eff_MF_smoothed` uses a [1,2,1]/4-smoothed
    denominator for the same reason; the raw and smoothed pair bracket the
    winner's-curse bias, which is measured on the plant in s03.
    """
    s = np.asarray(s, dtype=np.float64)
    k = s.size
    pos = np.clip(s, 0.0, None)
    ssm = smooth3(s)
    i_pk_raw = int(np.argmax(s))
    i_pk_sm = int(np.argmax(ssm))
    out = {
        "k": k,
        "peak_idx_raw": i_pk_raw,
        "peak_idx_smoothed": i_pk_sm,
        "peak_power_raw": float(s[i_pk_raw]),
        "peak_power_smoothed": float(ssm[i_pk_sm]),
        "sum_power": float(pos.sum()),
    }
    den_raw = max(s[i_pk_raw], 1e-30)
    den_sm = max(ssm[i_pk_sm], 1e-30)
    out["n_eff_mf_raw"] = float(pos.sum() / den_raw)
    out["n_eff_mf_smoothed"] = float(pos.sum() / den_sm)
    ss = float((pos**2).sum())
    out["pr"] = float(pos.sum() ** 2 / ss) if ss > 0 else 0.0

    # Windowed variant: only frames within +-half_window of the smoothed peak.
    # Drift moves scene content through a fixed patch on deep stacks, which can
    # only ADD apparent off-peak power; the window bounds that.
    if half_window is not None:
        lo = max(0, i_pk_sm - half_window)
        hi = min(k, i_pk_sm + half_window + 1)
        pw = pos[lo:hi]
        out["n_eff_mf_window"] = float(pw.sum() / den_sm)
        out["window_lo"], out["window_hi"] = lo, hi

    # Relative amplitude at +-1 and +-2 steps from the smoothed peak - the
    # external reviewer's own claim ("MTF 0.3-0.8 one or two steps off peak").
    amp = np.sqrt(pos)
    a_pk = float(np.sqrt(max(ssm[i_pk_sm], 0.0)))
    for d in (1, 2, 3, 5):
        vals = []
        if i_pk_sm - d >= 0:
            vals.append(amp[i_pk_sm - d])
        if i_pk_sm + d < k:
            vals.append(amp[i_pk_sm + d])
        out[f"rel_amp_{d}"] = float(np.mean(vals) / a_pk) if (vals and a_pk > 0) else np.nan
    return out


def mf_gain_over_top_m(s: np.ndarray, m: int) -> float:
    """SNR gain of the matched filter over averaging the best `m` frames and
    inverse-filtering the result.

    Averaging m frames gives L.(1/m).sum H_k + noise sigma/sqrt(m); dividing by
    the effective transfer (1/m)|sum H_k| leaves SNR = |L|.|sum H_k|/(sigma
    sqrt m). The matched filter's is |L|.sqrt(sum|H|^2)/sigma. Only |H_k| is
    measurable here (phase is not), and |sum H_k| <= sum|H_k|, so using
    sum|H_k| in the denominator makes this a LOWER bound on the gain -
    i.e. conservative against the deconvolution proposal.
    """
    s = np.clip(np.asarray(s, dtype=np.float64), 0.0, None)
    amp = np.sqrt(s)
    top = np.sort(amp)[::-1][:m]
    den = top.sum()
    if den <= 0:
        return np.nan
    return float(np.sqrt((amp**2).sum()) * np.sqrt(m) / den)
