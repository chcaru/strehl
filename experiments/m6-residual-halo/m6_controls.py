"""M6 planted-cause controls: do the discriminators actually discriminate?

The whole of deliverable 1 rests on one claim — that `S1 gamma` fires under
blur-induced correlation bias and not under depth-dependent magnification. That
claim is a *prediction about an estimator*, so it is testable, and this file
tests it on four stacks built from real sensor frames with a known cause planted
in each:

  N1-null        global similarity only, no depth blur   -> gamma ~ 0, no monotone dg
  P0-depth-only  depth-dependent magnification only      -> gamma ~ 0, monotone dg
  P2-blur-only   depth-dependent blur only               -> gamma > 0, no monotone dg
  P1-both        both                                    -> gamma > 0, monotone dg

N1 is a **real-data null** in the sense SYNTHESIS §5 item 9 demands: the texture,
the photon noise and the read noise are those of an actual ARW frame, warped by a
known similarity. It is not white noise.

Two labels are run for every case. `truth-depth` is the planted depth field,
which exists only in the controls. `measured-w` is the registered per-tile focus
argmax, which is the only label the real stacks can offer. Running both is the
point: N1 and P0 have **no depth-dependent blur**, so they have no focus peak,
so their measured label is noise and `|c - w|` collapses onto the frame-pair
fixed effect. The `ident` column reports how much of the regressor survives the
two-way demeaning and is what tells that failure apart from a false alarm.

If the sign pattern above does not come out, the discriminator is not fit for
purpose and the real-stack result must not be quoted. Run:

    python m6_controls.py
"""

from __future__ import annotations

import sys

import numpy as np

import m6_lib as L

PREFIX = "data/control"
CASES = ["N0-integer", "N1-null", "P0-depth-only", "P2-blur-only", "P1-both", "P3-asym-psf"]

#: What was **pre-registered** before the controls were run: does the case
#: contain blur, and does it contain depth-dependent magnification?
PREDICTED = {
    "N0-integer": (False, False),
    "N1-null": (False, False),
    "P0-depth-only": (False, True),
    "P2-blur-only": (True, False),
    "P1-both": (True, True),
    "P3-asym-psf": (True, False),
}

#: Does the case contain a **field-dependent asymmetric PSF** — a defocus blur
#: whose centroid walks radially with the amount of blur?
ASYM = {c: (c == "P3-asym-psf") for c in CASES}

#: What S6 actually detects, as opposed to what it was designed to detect.
#:
#: S6 was written to isolate an asymmetric PSF: regress the *radial* residual on
#: the signed blur asymmetry `|mov-w| - |ref-w|`, with tile and pair fixed
#: effects. The control disagreed. It fires on `P1-both`, which has a strictly
#: symmetric Gaussian PSF and no asymmetry whatsoever.
#:
#: The reason is structural and was missed at design time. Depth-dependent
#: magnification displaces tile `i` in pair `(j, j+D)` by
#: `gstep*D*kappa*dz_i*r_i` — a pair scalar times a tile scalar times radius.
#: That is a depth x pair *interaction*, which additive fixed effects cannot
#: absorb, and it is correlated with `|mov-w| - |ref-w|` because both are driven
#: by `w_i`. So S6 responds to cause (a) as well.
#:
#: What survives is still worth having, but it is a weaker claim than intended:
#:
#:   S6 fires  <=>  the data contain a radially organised depth x pair
#:                  interaction, from EITHER an asymmetric PSF OR
#:                  depth-dependent magnification.
#:
#: The decisive negative control is `P2-blur-only`: heavy symmetric defocus, S1
#: fires at gamma=+0.063, and S6 stays flat at +0.003 +/- 0.013. So a **null**
#: S6 does rule out both mechanisms at the planted amplitude, which is the
#: direction the real-stack result needs. A **positive** S6 would not have told
#: (a) from an asymmetric PSF on its own, and that limitation is reported in
#: M6-residual-halo-measured.md rather than papered over.
S6_EXPECT = {c: (ASYM[c] or PREDICTED[c][1]) for c in CASES}

#: Same story in the other direction: S2 was designed for cause (a) and fires on
#: `P3-asym-psf` too, because a PSF centroid that walks radially is a radial
#: displacement and that is exactly what S2 measures. Amplitude and sign still
#: separate them in practice — planted depth-magnification gives rho = -0.83 /
#: -0.71, the asymmetric PSF gives rho = +0.20 — but S2 is not clean either.
S2_EXPECT = {c: (PREDICTED[c][1] or ASYM[c]) for c in CASES}

#: What the cases turned out to contain. One entry differs from the prediction
#: and the difference is reported rather than quietly absorbed:
#:
#: `N1-null` was written as a null and is not one. Bilinear resampling
#: attenuates high spatial frequencies by an amount that depends on the
#: sub-pixel phase, so a scaled synthetic frame carries a per-tile per-frame
#: sharpness modulation that nobody planted — median profile peakiness 0.082
#: against 0.024 for the same stack shifted by whole pixels. S1 fires on it
#: because there really is blur varying with frame index; the statistic is
#: right and the null was wrong. `N0-integer` was added afterwards as the null
#: that actually holds, and it is the one quoted as the estimator floor.
#:
#: This matters beyond bookkeeping: any synthetic alignment benchmark built by
#: resampling one frame has this bias baked in.
EXPECT = dict(PREDICTED, **{"N1-null": (True, False)})


def run_case(case: str, n_perm: int = L.N_PERM):
    t = L.load_tiles(PREFIX, case)
    focus = L.load_focus(PREFIX, case)
    fits = L.load_fits(PREFIX, case, grid="m6")
    truth = L.load_truth(PREFIX, case)

    w, pk, prof = L.winner_index(focus)
    wt = np.full_like(w, np.nan)
    for tid, d in truth.items():
        if tid < len(wt):
            wt[tid] = d

    ox, oy = L.scale_centre(fits)
    out = {
        "case": case,
        "peakiness_median": float(np.nanmedian(pk)),
        "frac_peaky": float(np.nanmean(pk > L.PEAKINESS_MIN)),
        "w_sd": float(np.nanstd(w)),
        "scale_centre": (ox, oy),
    }

    for label, ww in (("measured-w", w), ("truth-depth", wt)):
        if not np.isfinite(ww).any():
            continue
        g = L.s1_gamma(t, ww, n_perm=n_perm)
        gc = L.s1_gamma(t, ww, controls=("logcontrast", "peak"), n_perm=199)
        s2 = L.s2_scale_anomaly(t, ww, ox, oy)
        out[label] = {
            "gamma": g,
            "gamma_controlled": gc,
            "s2": s2,
            "s6": L.s6_signed_bias(t, ww, ox, oy),
        }
    out["s4"] = L.s4_rejection(t, w)
    out["res_by_delta"] = {
        int(d): float(np.nanmean(t.select(t.ok & (t.delta == d)).res)) for d in np.unique(t.delta)
    }
    return out


def main():
    print("M6 planted-cause controls")
    print("=" * 100)
    results = {case: run_case(case) for case in CASES}

    print("\n0. Does the case even HAVE a depth label? (registered focus profile)")
    print(f"  {'case':<16}{'pk median':>11}{'frac>gate':>11}{'w sd (frames)':>16}")
    for c in CASES:
        r = results[c]
        print(f"  {c:<16}{r['peakiness_median']:>11.3f}{r['frac_peaky']:>11.3f}{r['w_sd']:>16.2f}")

    print("\n1. S1 gamma, px of residual per frame of defocus mismatch")
    print("   ident = fraction of the regressor's variance surviving the two-way demeaning;")
    print("   below 0.02 gamma is not identified and the value is meaningless, not a false alarm.")
    print(
        f"  {'case':<16}{'label':<13}{'gamma':>11}{'+/-SE':>9}{'ident':>8}"
        f"{'p_perm':>9}{'p_torus':>9}{'n':>7}  verdict"
    )
    for c in CASES:
        for label in ("measured-w", "truth-depth"):
            r = results[c].get(label)
            if r is None:
                continue
            g = r["gamma"]
            v = "FIRES" if g.fires else ("unidentified" if not g.identified else "quiet")
            print(
                f"  {c:<16}{label:<13}{g.gamma:>+11.5f}{g.se_cluster:>9.5f}{g.ident:>8.4f}"
                f"{g.p_perm:>9.4f}{g.p_torus:>9.4f}{g.n:>7d}  {v}"
            )

    print("\n2. S1 gamma with contrast and peak controls (is it a bias or a variance effect?)")
    print(f"  {'case':<16}{'label':<13}{'gamma':>11}{'+/-SE':>9}{'p_torus':>9}")
    for c in CASES:
        for label in ("measured-w", "truth-depth"):
            r = results[c].get(label)
            if r is None:
                continue
            g = r["gamma_controlled"]
            print(f"  {c:<16}{label:<13}{g.gamma:>+11.5f}{g.se_cluster:>9.5f}{g.p_torus:>9.4f}")

    print("\n3. S2 depth organisation of the per-tile radial scale anomaly")
    print(
        f"  {'case':<16}{'label':<13}{'rho(dg,w)':>11}{'p_tor':>8}"
        f"{'rho(res,|w-mid|)':>18}{'p_tor':>8}{'aniso':>8}"
    )
    for c in CASES:
        for label in ("measured-w", "truth-depth"):
            r = results[c].get(label)
            if r is None:
                continue
            s = r["s2"]
            print(
                f"  {c:<16}{label:<13}{s['rho_dg_w']:>+11.3f}{s['p_torus_dg']:>8.4f}"
                f"{s['rho_res_absw']:>+18.3f}{s['p_torus_v']:>8.4f}{s['aniso']:>8.3f}"
            )

    print("\n4. S4 censoring: does the aligner drop tiles as a function of defocus?")
    for c in CASES:
        s4 = results[c]["s4"]
        print(
            f"  {c:<16} reject rate {s4['overall']:.3f}   "
            f"slope {s4['slope_per_frame']:+.5f} +/- {s4['se']:.5f} per frame of mismatch"
        )

    print("\n5. Mean per-tile residual by baseline (px)")
    for c in CASES:
        row = "  ".join(f"d={d}:{v:.3f}" for d, v in sorted(results[c]["res_by_delta"].items()))
        print(f"  {c:<16} {row}")

    # ---- verdicts -------------------------------------------------------
    print("\n" + "=" * 100)
    print("VERDICT: S1 must fire when and only when blur was planted, using the")
    print("label a real stack could actually supply where that label is identified.")
    ok = True
    for c in CASES:
        blur, depth = EXPECT[c]
        pred_blur, _ = PREDICTED[c]
        gm = results[c]["measured-w"]["gamma"]
        gt = results[c]["truth-depth"]["gamma"]
        use, tag = (gm, "measured-w") if gm.identified else (gt, "truth-depth")
        agree = use.fires == blur
        ok &= agree
        note = "" if blur == pred_blur else "   [pre-registered prediction was 'no blur'; see EXPECT]"
        print(
            f"  {c:<16} blur={str(blur):<5} via {tag:<12} fires={str(use.fires):<5} "
            f"{'OK' if agree else 'MISMATCH'}   gamma={use.gamma:+.5f} "
            f"ident={use.ident:.4f} p_torus={use.p_torus:.4f}{note}"
        )

    n0 = results["N0-integer"]["measured-w"]["gamma"]
    print(
        f"\n  ESTIMATOR FLOOR (real texture, real sensor noise, no interpolator):"
        f"  gamma = {n0.gamma:+.6f} +/- {n0.se_cluster:.6f} px per frame, ident {n0.ident:.3f}"
    )

    print("\nVERDICT: S2 - a depth-organised radial scale anomaly. Designed for cause (a),")
    print("but it also fires on a radially walking asymmetric PSF, because that IS a")
    print("radial displacement organised by depth. Amplitude and sign still separate the")
    print("two: planted depth-magnification gives rho = -0.7 to -0.8, the asymmetric PSF")
    print("gives rho = +0.20. See S2_EXPECT.")
    s2ok = True
    for c in CASES:
        use, tag = (
            (results[c]["measured-w"]["s2"], "measured-w")
            if results[c]["measured-w"]["gamma"].identified
            else (results[c]["truth-depth"]["s2"], "truth-depth")
        )
        fired = use["p_torus_dg"] <= 0.05
        agree = fired == S2_EXPECT[c]
        s2ok &= agree
        print(
            f"  {c:<16} expect={str(S2_EXPECT[c]):<5} via {tag:<12} fires={str(fired):<5} "
            f"{'OK' if agree else 'MISMATCH'}   rho={use['rho_dg_w']:+.3f} p={use['p_torus_dg']:.4f}"
        )

    print()
    print("VERDICT: S6 - what it actually detects is a radially organised depth x pair")
    print("interaction, which an asymmetric PSF and depth-dependent magnification BOTH")
    print("produce (see S6_EXPECT). The load-bearing control is P2-blur-only: heavy")
    print("SYMMETRIC defocus, S1 fires hard, S6 must stay flat. That is what licenses")
    print("reading a null S6 on real data as 'neither mechanism at this amplitude'.")
    s6ok = True
    for c in CASES:
        use, tag = (
            (results[c]["measured-w"]["s6"], "measured-w")
            if results[c]["measured-w"]["gamma"].identified
            else (results[c]["truth-depth"]["s6"], "truth-depth")
        )
        fired = use["p_torus_rad"] <= 0.05 and abs(use["b_rad"]) > 2 * use["se_rad"]
        agree = fired == S6_EXPECT[c]
        s6ok &= agree
        note = "   [asym-PSF planted]" if ASYM[c] else ""
        print(
            f"  {c:<16} expect={str(S6_EXPECT[c]):<5} via {tag:<12} fires={str(fired):<5} "
            f"{'OK' if agree else 'MISMATCH'}   b_rad={use['b_rad']:+.5f} +/- {use['se_rad']:.5f} "
            f"p={use['p_torus_rad']:.4f}  b_tan={use['b_tan']:+.5f} (placebo){note}"
        )
    p2 = results["P2-blur-only"]["measured-w"]
    print(
        f"\n  SYMMETRIC-BLUR REFERENCE (P2): S1 gamma={p2['gamma'].gamma:+.5f} FIRES while"
        f" S6 b_rad={p2['s6']['b_rad']:+.5f} +/- {p2['s6']['se_rad']:.5f} stays flat."
    )
    n0s6 = results["N0-integer"]["measured-w"]["s6"]
    print(
        f"  S6 REAL-DATA FLOOR (N0, no interpolator): b_rad = {n0s6['b_rad']:+.6f}"
        f" +/- {n0s6['se_rad']:.6f} px per frame of asymmetry."
    )

    print()
    if not ok:
        print("S1 FAILED ITS PLANTED-CAUSE CONTROLS - do not quote the real-stack result.")
        sys.exit(1)
    print("S1 PASSES ITS PLANTED-CAUSE CONTROLS")
    print("S2 " + ("PASSES" if s2ok else "FAILS") + " ITS PLANTED-CAUSE CONTROLS")
    print("S6 " + ("PASSES" if s6ok else "FAILS") + " ITS PLANTED-CAUSE CONTROLS")
    if not (s2ok and s6ok):
        sys.exit(1)


if __name__ == "__main__":
    main()

