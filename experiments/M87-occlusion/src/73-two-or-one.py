"""M87 / 73 -- is the veil ONE mechanism or TWO?

THE QUESTION.  In the uncorrected `flower-bud-alone-cpl` and `bee3-full` renders
the orchestrator can see (a) a bright soft veil immediately at the silhouette
and (b) a darker band standing off from it, and has ARGUED they are two things
without measuring it.  If they are two, the shipped correction is aimed at one
of them, which would explain why removing 79.8% of the halo metric still leaves
the render looking veiled.

MY STEP 71 INSTRUMENT ALREADY SHOWS BOTH SIGNS.  E(d) = [image(d) - ens(d)]/far,
where ens is the mean over all 299 single-frame radial profiles, reads a
positive box from d = 3 to 19 (peak +0.14393 at d = 13) and then a NEGATIVE
shelf, crossing zero at d = 32 and troughing at -0.07961 at d = 92.  That is
exactly the orchestrator's (a) and (b), on the judged image, from an instrument
built for something else.  So the question is not whether two features exist.
It is whether they are two MECHANISMS.

WHY E CANNOT ANSWER IT ALONE, WHICH IS THE POINT OF THIS SCRIPT.  E is a
difference against the ensemble of the very frames the election chooses from, so
ANY effect present in every frame cancels out of it.  Formally: let a fixed
per-pixel gain field g be applied to every frame.  Then
  * the focus field at a pixel is scaled by a constant across k, so `argmax_k`
    is EXACTLY unchanged and the election is untouched;
  * image -> image*g and ens -> ens*g, so E -> g*E, a 3% change in E for a 3%
    gain -- i.e. nothing.
So E measures only what the ELECTION does relative to an average frame.  A real
frame-borne darkening -- a genuine two-layer veil that is in every observation,
or a cast shadow -- is INVISIBLE to it.  ORCH's (b) is exactly the hypothesis
"there is something real out there", and the instrument that found (b) is
constitutionally incapable of testing that hypothesis.  Hence a second one.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

INSTRUMENT E, election-created excess (step 71, reused unchanged).

W1 -- THE ROLL.  Roll the ELECTED-INDEX FIELD by (317, 511) and rebuild the
    merge from the rolled field.  This preserves the marginal distribution of
    elected depths exactly -- it is a roll -- and destroys only their
    registration with the boundary.  REGISTERED: if the negative shelf is
    boundary-registered election behaviour, like the positive box, then
    |E_shuf| at the true trough is <= 25% of |E_true| there.  If it is >= 50%,
    the shelf is NOT boundary-registered and is a separate thing.  Between the
    two, indeterminate, and I say so.

C-E-BLIND -- the control that makes W1 mean anything, and it must read ZERO.
    Plant a -3% multiplicative annulus into every frame over d in [30, 70],
    disjoint from the far window [80, 120] so the normaliser is untouched.
    REGISTERED: E must recover <= 5% of the planted amplitude.  This
    demonstrates E's blindness on real pixels through the real profiler instead
    of asserting it from the algebra above.  If E DOES see the plant, my
    blindness argument is wrong and the whole framing of this script fails.

INSTRUMENT V, frame-borne veil, measured on the ENSEMBLE and not on the merge.
    At a fixed distance d, split background pixels by LOCAL OCCLUDER COVERAGE --
    the fraction of subject within radius 48 px -- and compare the ensemble
    level of the high-coverage against the low-coverage half:
        V(d) = [ens_low(d) - ens_high(d)] / ens_low(d)
    A real two-layer veil darkens a pixel in proportion to how much defocused
    occluder surrounds it, in EVERY frame, so V > 0.  Holding d fixed removes
    the radial profile, which is the confound that defeated three earlier
    baselines in this milestone.

C-V-POS -- REGISTERED: plant a darkening proportional to local coverage,
    amplitude 3%, into every frame; V must recover >= 50% of the planted
    contrast.  A V that cannot see a planted veil cannot report the absence of
    a real one.

C-V-NULL -- REGISTERED: with no plant, recompute V against a ROLLED coverage
    map, same marginal distribution, no spatial registration.  V must read
    within +/-0.005.  This guards against coverage correlating with vignetting,
    illumination fall-off or the ROI edge.

VERDICT, registered as a 2x2:
    shelf collapses under W1 AND V ~ 0     -> ONE mechanism, the election, two signs
    shelf collapses under W1 AND V > 0     -> TWO mechanisms: an election artifact
                                              AND a real frame-borne veil
    shelf survives W1                      -> the shelf is not boundary-registered;
                                              report it as a third thing, unexplained

READ-ONLY: D:\\personal\\macro.  Writes only under experiments/M87-occlusion and
the scratch directory C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

FAR = (80, 120)
ROLL = (317, 511)
COV_R = 48
COV_RADII = (48, 128)
PLANT_ANN = (30, 70)
PLANT_AMP = 0.03
DMAX = 200


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
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
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
    print(f"cube {cube.shape}  valid {int(valid.sum())} px  "
          f"subject {100 * fmask.mean():.2f}%", flush=True)

    def prof(img, sub=None):
        v = img[valid][order]
        s = None if sub is None else sub[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            seg = v[a:b] if s is None else v[a:b][s[a:b]]
            if seg.size >= 200:
                out[d] = np.median(seg)
        return out

    # ---- one pass over the cube: ensemble profiles, ensemble image, rolled merge
    arg_shuf = np.roll(argbest, ROLL, axis=(0, 1))
    same = int((arg_shuf == argbest).sum())
    hist_ok = bool(np.array_equal(np.bincount(argbest.ravel(), minlength=n),
                                  np.bincount(arg_shuf.ravel(), minlength=n)))
    print(f"C-ROLL: elected-index marginal preserved = {hist_ok}; "
          f"{100 * same / argbest.size:.3f}% of pixels keep their index", flush=True)

    P = np.empty((n, DMAX + 1))
    ens_img = np.zeros((h, w), np.float64)
    sel_shuf = np.empty((h, w), np.float32)
    for k in range(n):
        fr = np.asarray(cube[k], dtype=np.float32)
        P[k] = prof(fr)
        ens_img += fr
        s = arg_shuf == k
        if s.any():
            sel_shuf[s] = fr[s]
        if k % 60 == 0:
            print(f"  frame {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    ens_img /= n
    ens = np.nanmean(P, axis=0)
    far = float(np.nanmedian(ens[FAR[0]:FAR[1] + 1]))
    print(f"  ensemble far level [{FAR}] = {far:.1f} DN   "
          f"{time.time() - t0:.0f}s", flush=True)

    def E(img):
        return (prof(img) - ens) / far

    Em, Es = E(sel0), E(sel_shuf)
    d = np.arange(DMAX + 1)
    seg = slice(1, 121)
    pk = int(np.nanargmax(np.where(np.isfinite(Em), Em, -np.inf)[seg])) + 1
    tr = int(np.nanargmin(np.where(np.isfinite(Em), Em, np.inf)[seg])) + 1
    print(f"\n--- E on the judged crop ---")
    print(f"  true  peak {Em[pk]:+.5f} at d={pk};  trough {Em[tr]:+.5f} at d={tr}",
          flush=True)
    print(f"  shuf  {Es[pk]:+.5f} at d={pk};  {Es[tr]:+.5f} at d={tr}", flush=True)

    box_ratio = abs(Es[pk] / Em[pk])
    shelf_ratio = abs(Es[tr] / Em[tr])
    print(f"\n--- W1 the roll ---")
    print(f"  positive box  |E_shuf|/|E_true| at d={pk} = {box_ratio:.4f}", flush=True)
    print(f"  negative shelf |E_shuf|/|E_true| at d={tr} = {shelf_ratio:.4f}", flush=True)
    if shelf_ratio <= 0.25:
        w1 = "COLLAPSES: the shelf is boundary-registered election behaviour"
    elif shelf_ratio >= 0.50:
        w1 = "SURVIVES: the shelf is NOT boundary-registered -- a third thing"
    else:
        w1 = "INDETERMINATE between the registered thresholds"
    print(f"  W1 -> {w1}", flush=True)

    # ---- C-E-BLIND.  A fixed per-pixel gain field leaves argmax_k EXACTLY
    # unchanged (it scales every k at that pixel by the same constant), so the
    # election is provably untouched and the plant is a pure photometric one.
    # The first version of this control compared the planted E against a
    # baseline built as prof(ens_img*g) -- the profile OF THE MEAN IMAGE --
    # while the true E uses ens = mean over k of prof(frame_k), the MEAN OF THE
    # PROFILES.  Median and mean do not commute, so it measured the baseline
    # swap and reported that E saw 56.65% of the plant.  Fixed here by planting
    # into every frame and rebuilding the ensemble the same way as the true one.
    g = np.where((dd >= PLANT_ANN[0]) & (dd <= PLANT_ANN[1]),
                 1.0 - PLANT_AMP, 1.0).astype(np.float32)
    Pp = np.empty_like(P)
    for k in range(n):
        Pp[k] = prof((np.asarray(cube[k], dtype=np.float32) * g).astype(np.float32))
    ens_p = np.nanmean(Pp, axis=0)
    far_p = float(np.nanmedian(ens_p[FAR[0]:FAR[1] + 1]))
    Ep = (prof((sel0 * g).astype(np.float32)) - ens_p) / far_p
    mid = (PLANT_ANN[0] + PLANT_ANN[1]) // 2
    seen = abs(Ep[mid] - Em[mid])
    frac = seen / PLANT_AMP
    blind = frac <= 0.05
    ident = float(np.nanmax(np.abs(ens_p[PLANT_ANN[0]:PLANT_ANN[1] + 1]
                                   - (1 - PLANT_AMP) * ens[PLANT_ANN[0]:PLANT_ANN[1] + 1])))
    print(f"\n--- C-E-BLIND (plant {-100 * PLANT_AMP:.0f}% over d{PLANT_ANN}) ---")
    print(f"  far level unplanted {far:.1f} planted {far_p:.1f} "
          f"(the plant is disjoint from the far window, so these must agree)",
          flush=True)
    print(f"  bin-constancy check: max |ens_planted - 0.97*ens| over the annulus "
          f"= {ident:.4f} DN", flush=True)
    print(f"  E at d={mid}: true {Em[mid]:+.5f} planted {Ep[mid]:+.5f}  "
          f"change {seen:.5f} = {100 * frac:.2f}% of the plant", flush=True)
    print(f"  E blind to a frame-borne effect: {blind} "
          f"({'OK, so E cannot test ORCH (b) and a second instrument is required' if blind else 'FAIL, my blindness argument is WRONG'})",
          flush=True)

    # ---- INSTRUMENT V: frame-borne veil, on the ENSEMBLE, at fixed distance.
    # The first version split each distance bin at the MEDIAN coverage.  Median
    # coverage over the valid background is 0.0049, so that split separated
    # near-zero coverage from near-zero coverage, gave an expected planted
    # contrast of 0.00042, and its rolled-coverage null failed at -0.00898.
    # Replaced by a per-bin SLOPE, which the plant calibrates exactly: for a
    # planted gain (1 - A*cov) the level is proportional to (1 - A*cov), so the
    # fractional change per unit coverage is exactly -A and V must move by A.
    cov = uniform_filter(fmask.astype(np.float32), 2 * COV_R + 1)
    print(f"\n--- V, frame-borne veil at fixed distance ---")
    print(f"  local coverage r={COV_R}: min {cov[valid].min():.4f} "
          f"med {np.median(cov[valid]):.4f} p90 {np.quantile(cov[valid], 0.9):.4f} "
          f"max {cov[valid].max():.4f}", flush=True)
    def V(img, covmap):
        """Per distance bin, regress level/median(level) on local coverage.
        Returns the NEGATIVE slope, so positive V = darker where more occluder
        surrounds the pixel = a frame-borne veil."""
        out = np.full(DMAX + 1, np.nan)
        spread = np.full(DMAX + 1, np.nan)
        cv = covmap[valid][order]
        vv = img[valid][order].astype(np.float64)
        for i in range(DMAX + 1):
            a, b_ = edges[i], edges[i + 1]
            if b_ - a < 400:
                continue
            x, y = cv[a:b_].astype(np.float64), vv[a:b_]
            med = np.median(y)
            if med <= 0:
                continue
            sx = float(x.std())
            if sx < 1e-4:
                continue
            sl = float(np.polyfit(x, y / med, 1)[0])
            out[i], spread[i] = -sl, sx
        return out, spread

    ens_f = ens_img.astype(np.float32)
    band = slice(40, 121)
    vres = {}
    for R in COV_RADII:
        cov = uniform_filter(fmask.astype(np.float32), 2 * R + 1)
        Vt_, sp_ = V(ens_f, cov)
        vt = float(np.nanmedian(Vt_[band]))
        spread = float(np.nanmedian(sp_[band]))
        Vn_, _ = V(ens_f, np.roll(cov, ROLL, axis=(0, 1)))
        vn = float(np.nanmedian(Vn_[band]))
        gv = (1.0 - PLANT_AMP * cov).astype(np.float32)
        Vp_, _ = V((ens_f * gv).astype(np.float32), cov)
        vp = float(np.nanmedian(Vp_[band]))
        rec_ = vp - vt
        fv = rec_ / PLANT_AMP
        # the honest magnitude: the slope times the coverage variation that
        # actually EXISTS at these distances, not the slope extrapolated to
        # coverage = 1, which is far outside the data
        amp = vt * spread
        vres[R] = {"V": vt, "null": vn, "plant": vp, "recovered": rec_,
                   "recovered_frac": fv, "cov_sd": spread, "observable_amp": amp,
                   "null_rel": abs(vn) / abs(vt) if abs(vt) > 1e-9 else float("nan"),
                   "Vd": Vt_.tolist(), "Vnull_d": Vn_.tolist()}
        print(f"  r={R:<4} cov sd within a bin {spread:.4f}   V {vt:+.5f}   "
              f"null {vn:+.5f} ({100 * vres[R]['null_rel']:.1f}% of V)   "
              f"C-V-POS recovered {100 * fv:.1f}%   observable amplitude "
              f"{100 * amp:+.3f}% of level", flush=True)

    # primary radius chosen by a RULE stated before the numbers: the radius whose
    # coverage actually varies at the distances being tested, i.e. the larger
    # within-bin spread over d in [40,120].
    PRIM = max(COV_RADII, key=lambda r: vres[r]["cov_sd"])
    pv = vres[PRIM]
    v_true, v_null, v_plant = pv["V"], pv["null"], pv["plant"]
    rec, frac_v = pv["recovered"], pv["recovered_frac"]
    Vt = np.asarray(pv["Vd"])
    Vn = np.asarray(pv["Vnull_d"])
    ok_pos = frac_v >= 0.50
    ok_null_abs = abs(v_null) <= 0.005
    ok_null = pv["null_rel"] <= 0.10
    print(f"  primary radius by within-bin coverage spread: r={PRIM}", flush=True)
    print(f"  C-V-POS: {'OK' if ok_pos else 'FAIL, V is blind'} "
          f"({100 * frac_v:.1f}% of a planted {PLANT_AMP})", flush=True)
    print(f"  C-V-NULL as REGISTERED (|V_null| <= 0.005): {ok_null_abs} "
          f"-- that bar was written for a ratio-scaled V and does not transfer "
          f"to a slope-scaled one", flush=True)
    print(f"  C-V-NULL scale-free (|V_null| <= 10% of |V|): {ok_null} "
          f"at {100 * pv['null_rel']:.1f}%  [AMENDED, post-hoc, marked as such]",
          flush=True)

    print(f"\n{'=' * 74}\n=== VERDICT ===", flush=True)
    amp = pv["observable_amp"]
    shelf = abs(Em[tr])
    ratio_amp = amp / shelf if shelf > 1e-9 else float("nan")
    v_real = ok_pos and ok_null and abs(v_true) > 3 * abs(v_null)
    print(f"  frame-borne veil, observable amplitude {100 * amp:+.3f}% of level; "
          f"election-created shelf {100 * shelf:.3f}%; ratio {ratio_amp:.4f}",
          flush=True)
    if shelf_ratio >= 0.50:
        verdict = ("the shelf SURVIVES the roll: not boundary-registered, "
                   "a third thing, unexplained")
    elif not v_real:
        verdict = ("ONE MECHANISM, TWO SIGNS: the election, boundary-registered; "
                   "no frame-borne veil separable from the null")
    elif ratio_amp >= 0.25:
        verdict = ("TWO MECHANISMS OF COMPARABLE SIZE: an election artifact with "
                   "two signs, AND a real frame-borne veil")
    else:
        verdict = ("TWO MECHANISMS, BUT NOT COMPARABLE: a real frame-borne veil "
                   f"exists at {100 * amp:+.3f}% of level, and the "
                   f"election-created shelf is {1 / max(ratio_amp, 1e-9):.1f}x "
                   "larger; a correction aimed at the election addresses the "
                   "dominant term")
    print(f"  {verdict}", flush=True)

    rep = {"pk": pk, "tr": tr, "E_true_peak": float(Em[pk]),
           "E_true_trough": float(Em[tr]), "E_shuf_at_peak": float(Es[pk]),
           "E_shuf_at_trough": float(Es[tr]), "box_ratio": box_ratio,
           "shelf_ratio": shelf_ratio, "W1": w1, "roll_hist_ok": hist_ok,
           "roll_same_pct": 100 * same / argbest.size,
           "C_E_BLIND_frac": float(frac), "C_E_BLIND_ok": bool(blind),
           "C_E_BLIND_bin_constancy_DN": ident,
           "primary_cov_radius": PRIM, "V_by_radius": vres,
           "V_true": v_true, "V_null": v_null,
           "C_V_NULL_registered_abs_ok": bool(ok_null_abs),
           "C_V_NULL_scalefree_ok": bool(ok_null),
           "V_plant": v_plant, "V_recovered": float(rec),
           "V_expected": float(PLANT_AMP),
           "C_V_POS_frac": float(frac_v), "C_V_POS_ok": bool(ok_pos),
           "V_real": bool(v_real), "observable_amp": float(amp),
           "shelf_amp": float(shelf), "amp_over_shelf": float(ratio_amp),
           "verdict": verdict, "far": far,
           "E_true": Em.tolist(), "E_shuf": Es.tolist(), "ens": ens.tolist()}
    with open(DATA / "73-two-or-one.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    np.save(OUT / "73-ens-img.npy", ens_f)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
        ax[0].axhline(0, color="k", lw=0.6)
        ax[0].plot(d, Em, label="E, shipped election", color="C3")
        ax[0].plot(d, Es, label=f"E, elected field rolled {ROLL}", color="C0")
        ax[0].axvline(pk, color="C3", ls=":", lw=0.8)
        ax[0].axvline(tr, color="C3", ls=":", lw=0.8)
        ax[0].set_ylabel("E(d)")
        ax[0].set_title("election-created excess: both signs collapse, or not")
        ax[0].legend(fontsize=8)
        ax[1].axhline(0, color="k", lw=0.6)
        ax[1].plot(d, Vt, label="V, true coverage", color="C2")
        ax[1].plot(d, Vn, label="V, rolled coverage (null)", color="0.6")
        ax[1].set_xlabel("distance from subject, px")
        ax[1].set_ylabel("V(d)")
        ax[1].set_title("frame-borne veil at fixed distance, on the ensemble")
        ax[1].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "73-two-or-one.png", dpi=130)
        print(f"  wrote {OUT / '73-two-or-one.png'}", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"  (no figure: {exc})", flush=True)

    print(f"\nwrote {DATA / '73-two-or-one.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
