"""M87 / 75 -- ORCH's photometric-step hypothesis for the veil: measure it, do
not argue about it.

THE HYPOTHESIS, as ORCH put it.  On `flowers-cpl` a `--gate 0` render shows
hard-edged polygonal patchwork: in a low-signal region adjacent pixels elect
frames that disagree PHOTOMETRICALLY, so every winner-field boundary is a
visible step.  Applied to a silhouette: the winner field must transition between
two frame indices far apart on the focus axis, and if those frames differ in
gain or offset the transition is a SIGNED STEP.  A bright band on one side and a
darker stand-off band on the other is what a signed step looks like when the
winner field overshoots and returns -- which would make my "one mechanism or
two" answer a single mechanism with a sign change.

MY JUDGEMENT BEFORE MEASURING, AND IT GOES AGAINST MY OWN PRIOR SECTION.  ORCH
is right that my three kills do not exclude this, and one of my published
conclusions is weaker than I wrote it:

  * §26.4's roll (W1) does NOT discriminate.  A roll is a RIGID TRANSLATION of
    the elected-index field, so it preserves every local index gradient exactly
    -- the steps still exist afterwards, in the same number and magnitude, just
    relocated off the silhouette.  A photometric-step artifact is therefore
    *also* boundary-registered and *also* collapses under the roll.  When I
    concluded "both features are boundary-registered election behaviour", that
    conclusion INCLUDES ORCH's mechanism rather than excluding it.
  * What IS already excluded is the frame-borne component V (+2.852% of level),
    because it is measured on the ENSEMBLE MEAN, which elects nothing.  No
    property of the election can appear there.  So the hypothesis is live for
    the box and the shelf, and dead for V.
  * §65's `|dk|` gate measured a THRESHOLD and not a gradient (`|dk|` < 3 gives
    dR -0.0268, `|dk|` >= 60 gives +0.3926, everything between ~0 +/- 0.07), and
    the registered monotone clause failed.  That is evidence against a
    photometric step, whose magnitude should grow with the index gap, but it is
    not a kill: it was measured with a RANK statistic, and a per-frame gain
    changes ranks, so dR is not neutral to the mechanism under test.

So: three measurements, all on the cached cube.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

D1 -- IS THERE ENOUGH PHOTOMETRIC DRIFT TO DO THE JOB?  Fit a per-frame gain and
    offset against the ensemble reference on the far background (d >= 140, so no
    subject lies within 140 px), then look up the gain of the frame ACTUALLY
    ELECTED at each band pixel.  The most a photometric step can deliver is the
    brightness spread across the elected frames.
    REGISTERED: if the band's elected-gain excess over the far field's is below
    25% of E's box amplitude (0.14393), photometric drift cannot account for the
    box, and I report the shortfall as a factor.

C-D1-POS -- plant a known per-frame gain ramp of +/-4% into the frames and
    require the fit to recover it to within 10% relative.  A drift estimator
    that cannot see a planted drift cannot report a small one.

D2 -- DOES THE ARTIFACT SCALE WITH THE INDEX GAP?  ORCH's prediction is monotone
    growth: the step is set by how far apart the elected frames are.  For band
    pixels compute the local index gap (max - min of the winner field in a 5x5
    neighbourhood) and correlate it with the per-pixel excess over the ensemble.
    REGISTERED: report Spearman rho with a rolled-gap null.  A photometric-step
    mechanism predicts rho clearly positive; a veiling mechanism does not
    require it.

D3 -- THE DIRECT KILL, and it is the one worth having.  Normalise every frame to
    a common gain and offset BEFORE the merge, re-run the election on the
    normalised frames, re-merge, recompute E against the normalised ensemble.
    REGISTERED: if the box amplitude survives at >= 75% of its unnormalised
    value the mechanism is REFUTED as the dominant cause; at <= 25% it is
    CONFIRMED as dominant; between the two, partial, and I say so.

C-D3-POS -- THE CONTROL WITHOUT WHICH D3 MEANS NOTHING, and this milestone has
    already been burned once by a negative control with no positive control of
    its own.  Plant a per-frame gain ramp of +/-10% -- several times any
    plausible real drift -- into the frames, re-elect, re-merge, and measure E.
    REGISTERED: the plant must (a) move E's box by a detectable amount, and
    (b) photometric normalisation must remove at least 50% of that planted
    movement.  If (b) fails, my normalisation does not work and D3's result is
    uninterpretable regardless of which way it comes out.

READ-ONLY: D:\\personal\\macro.  Writes only under experiments/M87-occlusion and
the scratch directory C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter, minimum_filter
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

ISO = 100.0
FAR = (80, 120)
REF_D = 140          # "guaranteed constant depth": no subject within 140 px
BOX = (2, 22)
DMAX = 200
ROLL = (317, 511)
PLANT_D1 = 0.04
PLANT_D3 = 0.10


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros((h, w), bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, DMAX + 2))
    ref_px = valid & (dd >= REF_D)
    band_px = valid & (dd >= BOX[0]) & (dd <= BOX[1])
    print(f"cube {cube.shape}   reference region d>={REF_D}: "
          f"{int(ref_px.sum())} px   band d{BOX}: {int(band_px.sum())} px",
          flush=True)

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    def getf(k, gain=None):
        f = np.asarray(cube[k], dtype=np.float32)
        return f if gain is None else (f * np.float32(gain[k]))

    # ---------------- D1: per-frame gain and offset on the far background
    print(f"\n--- D1 per-frame photometric fit on d >= {REF_D} ---", flush=True)
    ref_stack = np.empty((n, int(ref_px.sum())), np.float32)
    for k in range(n):
        ref_stack[k] = getf(k)[ref_px]
    reference = ref_stack.mean(0).astype(np.float64)
    rc = reference - reference.mean()
    den = float((rc * rc).sum())

    def fit(stack):
        g = np.empty(n)
        o = np.empty(n)
        for k in range(n):
            y = stack[k].astype(np.float64)
            g[k] = float((rc * (y - y.mean())).sum() / den)
            o[k] = float(y.mean() - g[k] * reference.mean())
        return g, o

    gain, off = fit(ref_stack)
    gp2p = float(gain.max() - gain.min())
    print(f"  gain  min {gain.min():.5f}  max {gain.max():.5f}  p-p {gp2p:.5f} "
          f"({100 * gp2p:.3f}%)   sd {gain.std():.5f}", flush=True)
    print(f"  offset p-p {off.max() - off.min():.2f} DN "
          f"(far level ~{reference.mean():.0f} DN, "
          f"{100 * (off.max() - off.min()) / reference.mean():.3f}%)", flush=True)

    planted = np.linspace(1 - PLANT_D1, 1 + PLANT_D1, n)
    gpl, _ = fit(ref_stack * planted[:, None].astype(np.float32))
    recov = (gpl / gain)
    err = float(np.max(np.abs(recov / planted - 1.0)))
    ok_d1c = err <= 0.10
    print(f"  C-D1-POS planted +/-{100 * PLANT_D1:.0f}% ramp: max relative "
          f"recovery error {100 * err:.3f}%  ({'OK' if ok_d1c else 'FAIL'})",
          flush=True)

    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    g_band = gain[argbest[band_px]]
    g_far = gain[argbest[valid & (dd >= FAR[0]) & (dd <= FAR[1])]]
    excess = float(np.median(g_band) / np.median(g_far) - 1.0)
    box_amp = 0.14393
    ratio = abs(excess) / box_amp
    ok_d1 = ratio < 0.25
    print(f"  elected-frame gain: band median {np.median(g_band):.5f}, "
          f"far median {np.median(g_far):.5f}, excess {100 * excess:+.4f}%",
          flush=True)
    print(f"  E box amplitude {100 * box_amp:.3f}% of level -> photometric drift "
          f"supplies {100 * ratio:.2f}% of it, a shortfall of "
          f"{1 / max(ratio, 1e-9):.1f}x  "
          f"({'CANNOT account for the box' if ok_d1 else 'is large enough to matter'})",
          flush=True)

    # ---------------- D2: does the excess scale with the local index gap?
    print(f"\n--- D2 excess against local winner-field gap ---", flush=True)
    P = np.empty((n, DMAX + 1))
    for k in range(n):
        P[k] = prof(getf(k))
    ens = np.nanmean(P, axis=0)
    far_lvl = float(np.nanmedian(ens[FAR[0]:FAR[1] + 1]))
    ensmap = np.interp(dd, np.arange(DMAX + 1), np.nan_to_num(ens, nan=far_lvl))
    exc = (sel0 - ensmap) / far_lvl
    gap = (maximum_filter(argbest, 5) - minimum_filter(argbest, 5)).astype(np.float32)
    gb, eb = gap[band_px], exc[band_px]
    rho = float(spearmanr(gb, eb).statistic)
    gap_roll = np.roll(gap, ROLL, axis=(0, 1))
    rho0 = float(spearmanr(gap_roll[band_px], eb).statistic)
    print(f"  band gap: median {np.median(gb):.1f} frames, p90 "
          f"{np.quantile(gb, 0.9):.1f}", flush=True)
    print(f"  Spearman rho(excess, gap) = {rho:+.4f}   rolled-gap null "
          f"{rho0:+.4f}", flush=True)
    for lo, hi in ((0, 2), (2, 10), (10, 40), (40, 120), (120, 300)):
        s = (gb >= lo) & (gb < hi)
        if s.sum() > 500:
            print(f"    gap [{lo:>3},{hi:>3}): {int(s.sum()):>7} px  "
                  f"median excess {np.median(eb[s]):+.5f}", flush=True)

    # ---------------- D3: normalise, re-elect, re-merge
    def elect(gain_mul, norm):
        """Run the shipped election over frames optionally gain-planted and
        optionally photometrically normalised, and return the merged image."""
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        gg, oo = (gain, off)
        if gain_mul is not None:
            st = ref_stack * gain_mul[:, None].astype(np.float32)
            gg, oo = fit(st)

        def frame(k):
            f = getf(k, gain_mul)
            if norm:
                f = ((f - np.float32(oo[k])) / np.float32(gg[k])).astype(np.float32)
            return f

        for k in range(n):
            fl = L.regularised_field(frame(k), ISO)
            b = fl > best
            best[b] = fl[b]
            arg[b] = k
        sel = np.empty((h, w), np.float32)
        Pk = np.empty((n, DMAX + 1))
        for k in range(n):
            f = frame(k)
            Pk[k] = prof(f)
            s = arg == k
            if s.any():
                sel[s] = f[s]
        e = np.nanmean(Pk, axis=0)
        fl_ = float(np.nanmedian(e[FAR[0]:FAR[1] + 1]))
        return (prof(sel) - e) / fl_, arg

    print(f"\n--- D3 photometric normalisation before the merge ---", flush=True)
    E_base, arg_base = elect(None, False)
    E_norm, arg_norm = elect(None, True)
    d = np.arange(DMAX + 1)
    pk = int(np.nanargmax(np.where(np.isfinite(E_base), E_base, -np.inf)[1:121])) + 1
    tr = int(np.nanargmin(np.where(np.isfinite(E_base), E_base, np.inf)[1:121])) + 1
    surv = E_norm[pk] / E_base[pk]
    surv_t = E_norm[tr] / E_base[tr]
    agree = float((arg_base == arg_norm).mean())
    print(f"  re-elected baseline reproduces the cached merge: box "
          f"{E_base[pk]:+.5f} at d={pk} (cached +0.14393 at d=13), trough "
          f"{E_base[tr]:+.5f} at d={tr}", flush=True)
    print(f"  after normalisation: box {E_norm[pk]:+.5f} ({100 * surv:.2f}% "
          f"survives), trough {E_norm[tr]:+.5f} ({100 * surv_t:.2f}% survives)",
          flush=True)
    print(f"  election unchanged at {100 * agree:.3f}% of pixels", flush=True)
    if surv >= 0.75:
        d3 = "REFUTED as the dominant cause of the box"
    elif surv <= 0.25:
        d3 = "CONFIRMED as the dominant cause of the box"
    else:
        d3 = "PARTIAL, between the registered thresholds"
    print(f"  D3 -> photometric-step mechanism {d3}", flush=True)

    print(f"\n--- C-D3-POS planted +/-{100 * PLANT_D3:.0f}% per-frame ramp ---",
          flush=True)
    ramp = np.linspace(1 - PLANT_D3, 1 + PLANT_D3, n)
    E_pl, _ = elect(ramp, False)
    E_pln, _ = elect(ramp, True)
    moved = E_pl[pk] - E_base[pk]
    removed = E_pl[pk] - E_pln[pk]
    frac_rm = removed / moved if abs(moved) > 1e-9 else float("nan")
    ok_a = abs(moved) > 0.005
    ok_b = frac_rm >= 0.50
    print(f"  planted box {E_pl[pk]:+.5f} against baseline {E_base[pk]:+.5f}: "
          f"the plant moved E by {moved:+.5f}  "
          f"({'detectable' if ok_a else 'NOT DETECTABLE, control (a) FAILS'})",
          flush=True)
    print(f"  normalised planted box {E_pln[pk]:+.5f}: normalisation removed "
          f"{removed:+.5f} = {100 * frac_rm:.1f}% of the planted movement  "
          f"({'OK' if ok_b else 'FAIL, D3 is uninterpretable'})", flush=True)

    print(f"\n{'=' * 74}\n=== VERDICT ===", flush=True)
    if not (ok_a and ok_b):
        verdict = ("UNINTERPRETABLE: C-D3-POS failed, so D3's result cannot be "
                   "read either way")
    elif surv >= 0.75:
        verdict = (f"ORCH's photometric-step mechanism is REFUTED for the box: "
                   f"{100 * surv:.1f}% of it survives explicit per-frame gain "
                   f"and offset normalisation, while a planted "
                   f"{100 * PLANT_D3:.0f}% drift is removed at "
                   f"{100 * frac_rm:.0f}%")
    else:
        verdict = f"photometric-step mechanism {d3}"
    print(f"  {verdict}", flush=True)

    rep = {"gain_p2p": gp2p, "gain_sd": float(gain.std()),
           "offset_p2p_DN": float(off.max() - off.min()),
           "far_level_DN": float(reference.mean()),
           "C_D1_POS_err": err, "C_D1_POS_ok": bool(ok_d1c),
           "elected_gain_band": float(np.median(g_band)),
           "elected_gain_far": float(np.median(g_far)),
           "elected_excess": excess, "box_amp": box_amp,
           "drift_share_of_box": ratio, "D1_cannot_account": bool(ok_d1),
           "D2_rho": rho, "D2_rho_null": rho0,
           "pk": pk, "tr": tr, "E_base_box": float(E_base[pk]),
           "E_base_trough": float(E_base[tr]), "E_norm_box": float(E_norm[pk]),
           "E_norm_trough": float(E_norm[tr]), "box_survival": float(surv),
           "trough_survival": float(surv_t), "election_agreement": agree,
           "D3": d3, "planted_move": float(moved),
           "planted_removed": float(removed), "planted_removed_frac": float(frac_rm),
           "C_D3_POS_detectable": bool(ok_a), "C_D3_POS_removed": bool(ok_b),
           "verdict": verdict, "gain": gain.tolist(), "offset": off.tolist(),
           "E_base": E_base.tolist(), "E_norm": E_norm.tolist(),
           "E_planted": E_pl.tolist(), "E_planted_norm": E_pln.tolist()}
    with open(DATA / "75-photometric.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
        ax[0].plot(np.arange(n), gain, lw=1)
        ax[0].set_xlabel("frame k")
        ax[0].set_ylabel("fitted gain")
        ax[0].set_title(f"per-frame gain on d>={REF_D}: p-p {100 * gp2p:.2f}%")
        ax[1].axhline(0, color="k", lw=0.6)
        ax[1].plot(d, E_base, label="shipped merge", color="C3")
        ax[1].plot(d, E_norm, label="gain+offset normalised", color="C0")
        ax[1].plot(d, E_pl, label=f"planted +/-{100 * PLANT_D3:.0f}% drift",
                   color="C1", ls="--")
        ax[1].plot(d, E_pln, label="planted, then normalised", color="C2", ls=":")
        ax[1].set_xlim(0, 130)
        ax[1].set_xlabel("distance from subject, px")
        ax[1].set_ylabel("E(d)")
        ax[1].set_title("does normalising the frames remove the veil?")
        ax[1].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "75-photometric.png", dpi=130)
        print(f"  wrote {OUT / '75-photometric.png'}", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"  (no figure: {exc})", flush=True)

    print(f"\nwrote {DATA / '75-photometric.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
