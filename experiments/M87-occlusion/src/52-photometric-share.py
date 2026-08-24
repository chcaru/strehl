"""M87 / 52 -- decomposing the halo into a PHOTOMETRIC share and an OPTICAL share.

Asked by the orchestrator (facts 1262-1266): part of what reads as halo may be a
per-frame brightness bias landing on a pixel whose runner-up is many frames away,
sending it to the wrong depth outright.

My own `05-photometry.py` renormalised the ESTIMATE only and left the selection
untouched, so this question was never asked. Here the normalisation is applied
BEFORE the focus field is computed, so it can change WHO WINS.

Why the test can express the effect (DERIVED, not assumed):
    field = box(sobel(L), 13) / max(sigma(L), eps),  sigma ~ sqrt(0.5*(g*L + rn^2))
Under a per-frame gain a, the numerator scales by `a` and, in the shot-noise
dominated regime, sigma scales by sqrt(a), so the field scales by ~sqrt(a).
A 5.31% level bias moves the response ~2.6%, which is large against the
admission tolerance t*sqrt(2)*FOCUS_NOISE_SD. A scale-invariant focus measure
would have made this test vacuous; this one is not.

M96's competitive-set definition is used verbatim and cited, not re-derived:
    admit(k) = best - field_k <= t*sqrt(2)*FOCUS_NOISE_SD
    gap      = (hi - lo + 1) - n      DISCONNECTED if > 0
(docs/research/M96-election-margin.md). Per the orchestrator, M96's 25.247%
whole-frame figure is NOT inherited -- the fraction is re-measured here on this
ROI and reported as its own number.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

CACHE = pathlib.Path("cache")
DATA = pathlib.Path("data")
ISO = 100.0
GATE_T = 2.0  # the shipped gate
MARGIN = 22   # src/04: WINDOW_RADIUS + REGULARISER_RADIUS + 1; the cube is ROI+22


def per_frame_gain(luma, probe):
    """Illumination probe = far-background pixels only.

    A whole-crop median is NOT a valid probe here: the subject sweeps through
    focus, so the crop median tracks real scene content and 'correcting' it
    would normalise away signal. Measured, the naive probe gives a 20.75%
    spread -- 3.9x the orchestrator's 5.31% -- which is the tell. The mean of a
    DEFOCUSED BACKGROUND region is preserved under blur, so far-background
    pixels probe illumination alone.
    """
    lev = np.array([float(np.asarray(luma[k], np.float32)[probe].mean())
                    for k in range(luma.shape[0])], np.float64)
    ref = float(np.median(lev))
    return (ref / lev).astype(np.float32), lev, ref


def elect(luma, gain=None):
    """Recompute the focus field frame by frame and return (argbest, selected G)."""
    n, h, w = luma.shape
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int32)
    for k in range(n):
        lk = np.asarray(luma[k], np.float32)
        if gain is not None:
            lk = lk * gain[k]
        f = L.regularised_field(lk, ISO)
        m = f > best
        best[m] = f[m]
        arg[m] = k
        if k % 60 == 0:
            print(f"    frame {k:3d}/{n}", flush=True)
    sel = np.zeros((h, w), np.float32)
    for k in range(n):
        m = arg == k
        if m.any():
            lk = np.asarray(luma[k], np.float32)
            sel[m] = (lk * gain[k])[m] if gain is not None else lk[m]
    return arg, sel, best


def m96_stats(field, best, t=GATE_T):
    """M96's disconnected-competitive-set statistic. Definition cited, not re-derived."""
    tol = np.float32(t) * np.float32(L.SQRT2) * np.float32(L.FOCUS_NOISE_SD)
    n, h, w = field.shape
    cnt = np.zeros((h, w), np.int32)
    lo = np.full((h, w), n, np.int32)
    hi = np.full((h, w), -1, np.int32)
    for k in range(n):
        adm = (best - np.asarray(field[k], np.float32)) <= tol
        cnt += adm
        lo[adm & (lo == n)] = k
        hi[adm] = k
    gap = (hi - lo + 1) - cnt
    return gap > 0, gap, cnt


def main():
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    print(f"cube {luma.shape}")

    from scipy.ndimage import distance_transform_edt
    probe = distance_transform_edt(~mask) > 60.0
    print(f"illumination probe: {100*probe.mean():.2f}% of pixels, "
          f"far background (>60 px from subject)")
    assert probe.sum() > 10000, "probe too small to be a level estimate"
    gain, lev, ref = per_frame_gain(luma, probe)
    rng = float(lev.max() - lev.min())
    print(f"per-frame level: ref {ref:.1f} DN, spread {rng:.1f} DN "
          f"= {100 * rng / ref:.2f}% of reference; gain in "
          f"[{gain.min():.4f}, {gain.max():.4f}]")

    print("  electing on RAW frames...")
    arg_raw, sel_raw, best_raw = elect(luma)
    print("  electing on GAIN-NORMALISED frames...")
    arg_nrm, sel_nrm, _ = elect(luma, gain)

    moved = arg_raw != arg_nrm
    dk = np.abs(arg_raw.astype(np.int32) - arg_nrm.astype(np.int32))
    print(f"re-elected: {100 * moved.mean():.3f}% of pixels")

    disc, gap, cnt = m96_stats(field, best_raw)
    print(f"M96 disconnected on THIS ROI (re-measured, not inherited): "
          f"{100 * disc.mean():.3f}%  mean gap {gap[disc].mean():.2f} frames")

    conn = ~disc
    e_disc = float(moved[disc].mean()) if disc.any() else float("nan")
    e_conn = float(moved[conn].mean()) if conn.any() else float("nan")
    enrich = e_disc / e_conn if e_conn > 0 else float("inf")
    md_disc = float(np.median(dk[moved & disc])) if (moved & disc).any() else float("nan")
    md_conn = float(np.median(dk[moved & conn])) if (moved & conn).any() else float("nan")
    print(f"re-election rate: disconnected {100*e_disc:.3f}%  connected {100*e_conn:.3f}%"
          f"   ENRICHMENT {enrich:.2f}x")
    print(f"median |dk| among movers: disconnected {md_disc:.0f}  connected {md_conn:.0f}")

    # label-shuffle control, exactly as the orchestrator ran it
    rng_ = np.random.default_rng(0x4D3837)
    sh = disc.ravel().copy()
    rng_.shuffle(sh)
    sh = sh.reshape(disc.shape)
    # the enrichment must be recomputed ENTIRELY under the shuffled labels --
    # comparing shuffled-positive against the TRUE connected rate is
    # mis-specified and reads 2.724x on data where the null is 1.00.
    e_sh = float(moved[sh].mean()) / float(moved[~sh].mean())
    print(f"label-shuffle control: {e_sh:.3f}x  (must be ~1.00)")

    # ---- the decomposition: halo metric under each election ---------------
    R = L.ROIS["ROI_LEG"]
    INNER = (MARGIN, MARGIN + (R[1] - R[0]), MARGIN, MARGIN + (R[3] - R[2]))
    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    r_raw = M2.score_iso(sel_raw, p, nv, boot=500)
    r_nrm = M2.score_iso(sel_nrm, p, nv, boot=500)
    share = 100 * (1 - r_nrm["ISO"] / r_raw["ISO"])
    print(f"\nHALO METRIC, {int(val.sum())} profiles")
    print(f"  election on RAW frames        ISO {r_raw['ISO']:.5f} "
          f"CI[{r_raw['ISO_ci'][0]:.5f},{r_raw['ISO_ci'][1]:.5f}]")
    print(f"  election on NORMALISED frames ISO {r_nrm['ISO']:.5f} "
          f"CI[{r_nrm['ISO_ci'][0]:.5f},{r_nrm['ISO_ci'][1]:.5f}]")
    print(f"  PHOTOMETRIC SHARE of the halo = {share:+.1f}%")

    json.dump({
        "level_spread_pct": 100 * rng / ref,
        "reelected_pct": 100 * float(moved.mean()),
        "disconnected_pct_this_roi": 100 * float(disc.mean()),
        "mean_gap": float(gap[disc].mean()),
        "reelect_disc_pct": 100 * e_disc, "reelect_conn_pct": 100 * e_conn,
        "enrichment": enrich, "shuffle_control": e_sh,
        "median_dk_disc": md_disc, "median_dk_conn": md_conn,
        "ISO_raw": r_raw["ISO"], "ci_raw": r_raw["ISO_ci"],
        "ISO_norm": r_nrm["ISO"], "ci_norm": r_nrm["ISO_ci"],
        "photometric_share_pct": share, "n_profiles": int(val.sum()),
    }, open(DATA / "52-photometric-share.json", "w"), indent=1)
    np.save(CACHE / "52-sel-elect-norm.npy", sel_nrm)
    np.save(CACHE / "52-disc.npy", disc)


if __name__ == "__main__":
    main()
