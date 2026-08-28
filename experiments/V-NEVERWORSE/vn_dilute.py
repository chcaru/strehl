"""V-NEVERWORSE: attack the N-dilution mechanism.

ORCH's claim, from `orch_dilution.py`:

    share_winner = 1 / (1 + SUM_{k != winner} (e_k / e_winner)^p)

with N-1 terms in the sum, so a fixed absolute exponent produces less
selection the deeper the stack gets.

THREE THINGS ARE WRONG WITH THAT EXPRESSION AS A MODEL OF THE SHIPPING LAW,
and this file measures how much each one matters. Verified at the pin
(`git show 9b05d0b7:crates/strehl-core/src/pyramid.rs`, 1351-1362 and
2092-2110):

  1. THE RATIO IS OF EXCESS, NOT ENERGY. `excess = (e - floor).max(0)` and
     `r = excess / floor.max(1) / SNR_REF`. So the term is
     `((e_k - floor)/(e_win - floor))^p`, not `(e_k/e_win)^p`. Writing
     `u = e/floor`, the true loser ratio is

         rho = (u_k - 1) / (u_win - 1)      not      r = u_k / u_win

     and rho < r ALWAYS, for u_k < u_win and u > 1. Floor subtraction makes
     the merge MORE selective than ORCH's model, not less. The gap widens as
     the winner approaches the floor, which is exactly the flat-region case.

  2. THE GATE IS HARD. Any frame with `e_k <= floor` contributes EXACTLY
     zero, so the sum does not have N-1 terms; it has (admitted - 1) terms.
     Whether the mechanism can bite at all therefore depends on whether the
     ADMITTED COUNT grows with N, which is a measurement on real stacks and
     is the single thing that decides this. It is Part C.

  3. `floor = gate * beta_k * var` AND BETA COLLAPSES AT COARSE BANDS.
     BETA = [0.8898, 0.0529, 0.0101, 0.0024, 0.0006, 0.0001, 0.0, 0.0]. At
     k >= 5 the floor is at or below the `max(floor, 1.0)` clamp, so the gate
     admits every frame and `r` reverts to an ABSOLUTE scale. Meanwhile the
     exponent ladder is LOWEST at those same bands (p = 2 at k = 6, p = 8 at
     k <= 2). Dilution is therefore predicted to be a COARSE-band effect.

     That prediction is falsifiable and it is the attack: V-SOFTCHECK's
     softening is at 0.30-0.35 cyc/px, which is the FINEST band. If dilution
     lives at the coarse end and the softening lives at the fine end, the
     mechanism cannot be the explanation however good the arithmetic looks.

A FOURTH FIDELITY GAP, stated because a structural claim inherits every rule
a number does: in the Rust, `variance` is a PER-FRAME argument
(`add_frame(planes, luma, variance, ws)`, line 1303-1308), so `floor` differs
between frames at a pixel and ORCH's share expression -- which cancels a
common floor -- is not exactly the shipping law even after correction 1. This
model shares one `var0` across frames, as `vn_pyr.py` does, so it reproduces
the CANCELLING case. The residual is measured in Part A5 rather than assumed.

Everything here is on green luma, which `pyramid.rs:1300` states is the plane
the selection is made on.

COMMISSIONING is in `commission()` and plants in BOTH directions: a flattened
through-focus curve (must dilute: share down, n_eff up) and a sharpened one
(must concentrate: share up, n_eff down), plus a tie control whose exact
1/m is verified to be a prediction rather than a short-circuit by perturbing
it off the tie and requiring it to move.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_pyr as VP  # noqa: E402
from vn_plateau import BETA, SHIP  # noqa: E402

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
NB = 7
GATE = SHIP["gate"]

# ORCH's proposed N-invariant fix measures each frame against the winner
# rather than against an absolute reference: w_k = max(0, r_k - THETA*r_max)^p.
# THETA is not specified in his message, so it is a guess and is declared as
# one. 0.5 is the midpoint of the only interval it can occupy: at 0 the fix is
# a no-op and at 1 only the winner ever survives, which is winner-take-all by
# construction and would be a different defect.
THETA = 0.5

# A band with too few coefficients is not evidence. At 64 px and 7 bands the
# coarsest band is a SINGLE pixel, whose merged/mean displacement is dominated
# by whether that one pixel happened to clear the gate. Bands below this are
# excluded by rule and reported by name wherever they are excluded.
MIN_BAND_PX = 64

# Band k of a [1,4,6,4,1]/16 Laplacian pyramid has its peak response near
# 0.25 / 2^k cyc/px. That is the NOMINAL map; `band_frequency_response()`
# measures the real one, because the whole refutation turns on which band a
# 0.30-0.35 cyc/px measurement lands in and a nominal number is an assertion.
BAND_CYC = [0.25 / (2.0 ** k) for k in range(NB)]


def band_frequency_response(nb=NB, size=256):
    """Which band actually carries a given spatial frequency.

    Measured, not asserted. For each probe frequency a pure sinusoid is
    decomposed, every band but one is zeroed, the survivor is expanded back to
    full resolution, and the variance of that reconstruction is the band's
    contribution AT FULL RES -- which is the quantity that decides whether a
    defect at some cyc/px can be attributed to some band. The Laplacian
    pyramid is not orthogonal, so contributions are normalised across bands
    rather than assumed to sum to the input.

    This exists because the refutation of ORCH's mechanism rests on the fine
    bands and the coarse bands being different places, and on V-SOFTCHECK's
    0.30-0.35 cyc/px landing in the fine ones.
    """
    xs = np.arange(size)
    out = []
    for f in (0.005, 0.01, 0.02, 0.04, 0.0625, 0.08, 0.125, 0.16, 0.20,
              0.25, 0.30, 0.325, 0.35, 0.40, 0.45):
        img = 1000.0 + 500.0 * np.sin(2.0 * np.pi * f * xs)[None, :] \
            * np.ones((size, 1))
        lap, base = VP.lap_pyr(img, nb)
        contrib = []
        for k in range(nb):
            R = np.zeros_like(base)
            for j in range(nb - 1, -1, -1):
                R = VP.expand(R, lap[j].shape) + (lap[j] if j == k
                                                  else np.zeros_like(lap[j]))
            contrib.append(float(np.var(R)))
        tot = sum(contrib) or 1.0
        frac = [c / tot for c in contrib]
        out.append(dict(cyc=f, frac=frac, peak_band=int(np.argmax(frac))))
    peak_cyc = []
    for k in range(nb):
        col = [(r["frac"][k], r["cyc"]) for r in out]
        peak_cyc.append(max(col)[1])
    return dict(rows=out, peak_cyc_per_band=peak_cyc,
                nominal=BAND_CYC)



def exponent_ladder(nb=NB):
    return [VP.exponent_at(k, nb, SHIP["exponent"], SHIP["sharpen"])
            for k in range(nb)]


# ---------------------------------------------------------------- Part A
def orch_share(n, r, p):
    """ORCH's expression, reproduced exactly from orch_dilution.py."""
    return 1.0 / (1.0 + (n - 1) * (r ** p))


def true_share(n, r, p, s):
    """The same configuration under the SHIPPING law.

    `s = u_win = e_win / floor` is the winner's energy in units of its own
    noise floor -- the quantity ORCH's model has no slot for. Losers sit at
    `u_k = r * s`. A loser at or below the floor is gated to exactly zero and
    leaves the sum entirely.
    """
    if s <= 1.0:
        return float("nan")
    uk = r * s
    if uk <= 1.0:
        return 1.0
    rho = (uk - 1.0) / (s - 1.0)
    return 1.0 / (1.0 + (n - 1) * (rho ** p))


def part_a():
    """How much of ORCH's dilution survives the excess ratio and the gate."""
    out = {"ladder": exponent_ladder(), "band_cyc": BAND_CYC, "rows": []}
    for p in (8.0, 4.0, 2.0):
        for r in (0.3, 0.5, 0.7, 0.9):
            for s in (1.05, 1.5, 3.0, 10.0, 100.0, 1e4):
                for n in (22, 63, 299):
                    o = orch_share(n, r, p)
                    t = true_share(n, r, p, s)
                    out["rows"].append(dict(p=p, r=r, s=s, n=n,
                                            orch=o, true=t,
                                            gated=bool(r * s <= 1.0)))
    return out


# ---------------------------------------------------------------- Part B/C
def band_accumulate(frames, var0, rungs, nb=NB, mode="ship", theta=0.0,
                    rmax=None):
    """One streaming pass over `frames`, updating every rung's accumulators.

    Returns per-rung, per-band statistics. Memory is O(rungs * bands), not
    O(N), which is what makes N = 299 at 900 px possible on a shared box.

    `mode`:
      "ship"  -- the shipping law, w = (excess/max(floor,1)/SNR_REF)^p
      "rmax"  -- the proposed N-invariant fix, w = max(0, r - theta*r_max)^p.
                 Needs the per-pixel r_max, so it is a SECOND pass over the
                 frames using `rmax` from a first "ship" pass.

    `swl` and `sl` accumulate the weighted and unweighted sums of the SIGNED
    band coefficient, so the merged band can be reconstructed exactly as
    `vn_pyr.merge` does -- weighted where anything was admitted, unweighted
    mean where nothing was -- and its amplitude measured. Share is a proxy for
    softness; the merged band amplitude is the thing itself, and carrying it
    on the same pixels is the anti-blur requirement, not boilerplate.
    """
    varp = VP.gauss_pyr(var0, nb)
    ps = exponent_ladder(nb)
    acc = {}
    for name, idx in rungs.items():
        acc[name] = [dict(n=len(idx),
                          sw=np.zeros(varp[k].shape),
                          sw2=np.zeros(varp[k].shape),
                          wmax=np.zeros(varp[k].shape),
                          adm=np.zeros(varp[k].shape),
                          emax=np.zeros(varp[k].shape),
                          swl=np.zeros(varp[k].shape),
                          sl=np.zeros(varp[k].shape))
                     for k in range(nb)]
    member = {name: set(idx) for name, idx in rungs.items()}

    for i, f in enumerate(frames):
        lap, _ = VP.lap_pyr(f, nb)
        for k in range(nb):
            Lk = lap[k]
            sq = VP.smooth5(Lk ** 2)
            floor = GATE * BETA[k] * np.maximum(varp[k], 0.0)
            excess = np.maximum(sq - floor, 0.0)
            if mode == "rmax":
                r = excess / np.maximum(floor, 1.0) / VP.SNR_REF
            else:
                w = VP.select_weight(excess, floor, ps[k])
                adm = (w > 0.0).astype(np.float64)
            for name in rungs:
                if i not in member[name]:
                    continue
                a = acc[name][k]
                if mode == "rmax":
                    eff = np.maximum(r - theta * rmax[name][k], 0.0)
                    w = np.where(eff > 0.0, eff ** ps[k], 0.0)
                    adm = (w > 0.0).astype(np.float64)
                a["sw"] += w
                a["sw2"] += w * w
                np.maximum(a["wmax"], w, out=a["wmax"])
                a["adm"] += adm
                np.maximum(a["emax"], excess / np.maximum(floor, 1.0)
                           / VP.SNR_REF, out=a["emax"])
                a["swl"] += w * Lk
                a["sl"] += Lk
    return acc, None, varp



def summarise(acc, varp, flat=None, nb=NB):
    """Per-rung, per-band scalars.

    `share` and `n_eff` are averaged ONLY over pixels where at least one
    frame was admitted. A pixel with nothing admitted falls through to the
    unweighted mean in the merge; folding it in as share = 0 would report
    dilution that is really abstention, and folding it in as share = 1 would
    report selection that is really a mean. It is counted separately so the
    partition sums.
    """
    out = {}
    for name, bands in acc.items():
        rows = []
        for k in range(nb):
            a = bands[k]
            live = a["sw"] > 0.0
            npix = a["sw"].size
            nlive = int(live.sum())
            sh = np.full(a["sw"].shape, np.nan)
            ne = np.full(a["sw"].shape, np.nan)
            sh[live] = a["wmax"][live] / a["sw"][live]
            ne[live] = (a["sw"][live] ** 2) / np.maximum(a["sw2"][live], 1e-300)
            m = flat[k] if flat is not None else None
            sel = live if m is None else (live & m)
            # The merged band, exactly as vn_pyr.merge forms it: weighted
            # where anything was admitted, unweighted mean where nothing was.
            merged = np.where(live, a["swl"] / np.maximum(a["sw"], 1e-300),
                              a["sl"] / a["n"])
            msel = m if m is not None else np.ones(merged.shape, bool)
            rows.append(dict(
                band=k, cyc=BAND_CYC[k], p=exponent_ladder(nb)[k],
                n=a["n"],
                px_total=npix, px_live=nlive, px_dead=npix - nlive,
                dead_frac=float((npix - nlive) / npix),
                adm_mean=float(a["adm"][sel].mean()) if sel.any() else float("nan"),
                adm_frac=float(a["adm"][sel].mean() / a["n"]) if sel.any() else float("nan"),
                share=float(np.nanmean(sh[sel])) if sel.any() else float("nan"),
                n_eff=float(np.nanmean(ne[sel])) if sel.any() else float("nan"),
                # n_eff counting the unweighted-mean fallback as full
                # participation, which is what section 9.4 reported. Both are
                # published because they answer different questions and the
                # difference between them IS the dead fraction.
                n_eff_incl_dead=float(np.nanmean(
                    np.where(live, ne, float(a["n"]))[msel])),
                band_amp=float(np.sqrt(np.mean(merged[msel] ** 2))),
                mean_amp=float(np.sqrt(np.mean(
                    (a["sl"][msel] / a["n"]) ** 2))),
                floor_med=float(np.median(GATE * BETA[k] * varp[k])),
                floor_below1=float(np.mean(GATE * BETA[k] * varp[k] < 1.0)),
            ))
        out[name] = rows
    return out


def flat_masks(frames, varp, nb=NB, q=25):
    """Flattest-quartile mask per band, from the MEAN frame's band energy.

    Taken from the mean rather than from any single frame so the mask does
    not select for the frame that happens to be in focus there -- the same
    trap that made an earlier arm of this lane measure focus instead of
    flatness.
    """
    mean = np.mean(frames, axis=0)
    lap, _ = VP.lap_pyr(mean, nb)
    ms = []
    for k in range(nb):
        sq = VP.smooth5(lap[k] ** 2)
        ms.append(sq <= np.percentile(sq, q))
    return ms


# ---------------------------------------------------------------- rungs
def make_rungs(n, want=(1, 2, 4, 8, 16)):
    """Nested subsets at MATCHED FOCUS RANGE: every s-th frame, always
    including the first and last, so every rung spans the same depth and only
    the sampling density changes. That is V-SOFTCHECK's 63-vs-32 design."""
    rungs = {}
    for s in want:
        idx = list(range(0, n, s))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        if len(idx) >= 3:
            rungs["N%d" % len(idx)] = idx
    return rungs


# ---------------------------------------------------------------- commission
def _share_neff(W):
    """share and n_eff from a weight stack, the same way summarise does."""
    sw = W.sum(axis=0)
    live = sw > 0
    sh = W.max(axis=0)[live] / sw[live]
    ne = (sw[live] ** 2) / (W ** 2).sum(axis=0)[live]
    return float(sh.mean()), float(ne.mean()), int(live.sum())


def commission_arith():
    """The share/n_eff arithmetic, against configurations with known answers.

    ORCH's warning about controls that return suspiciously round numbers is
    taken literally here: C1 and C2 DO return exact 1/m and m, so C3 proves
    they are predictions by perturbing off the tie and requiring movement.
    A short-circuit would not move.
    """
    rng = np.random.default_rng(20260827)
    res, ok = {}, True
    m, npx = 24, 4000

    # C1 TIE: every admitted frame equal -> share exactly 1/m, n_eff exactly m
    W = np.ones((m, npx))
    sh, ne, live = _share_neff(W)
    res["C1"] = dict(share=sh, n_eff=ne, want_share=1.0 / m, want_neff=m)
    if abs(sh - 1.0 / m) > 1e-12 or abs(ne - m) > 1e-9:
        ok = False

    # C2 SPIKE: one frame astronomically ahead -> share 1, n_eff 1
    W = np.full((m, npx), 1e-12)
    W[3] = 1.0
    sh2, ne2, _ = _share_neff(W)
    res["C2"] = dict(share=sh2, n_eff=ne2)
    if not (sh2 > 1.0 - 1e-9 and abs(ne2 - 1.0) < 1e-6):
        ok = False

    # C3 the tie is a PREDICTION, not a short-circuit: perturb and it moves.
    # SWEPT, not a single arbitrary magnitude. The first version perturbed by
    # 1%, measured 1.95% displacement and failed a 2% bar -- a bar chosen
    # before the effect was known. What the control has to establish is that
    # the exact 1/m is computed rather than returned, so the deliverable is
    # the point at which displacement becomes unambiguous, and monotonicity
    # across the sweep. A short-circuit reads exactly 0.0 at every rung.
    sweep = []
    for eps in (0.0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3):
        Wp = np.abs(np.ones((m, npx))
                    * (1.0 + eps * rng.standard_normal((m, npx))))
        s_, n_, _ = _share_neff(Wp)
        sweep.append(dict(eps=eps, share=s_,
                          d_rel=abs(s_ - 1.0 / m) / (1.0 / m)))
    mono = all(sweep[i]["d_rel"] <= sweep[i + 1]["d_rel"] + 1e-12
               for i in range(len(sweep) - 1))
    first = next((x["eps"] for x in sweep if x["d_rel"] > 0.01), None)
    res["C3"] = dict(sweep=sweep, monotone=mono, first_eps_over_1pct=first,
                     zero_eps_d_rel=sweep[0]["d_rel"])
    if not mono or first is None or sweep[0]["d_rel"] > 1e-12:
        ok = False

    # C4 GATE: a frame at or below the floor must contribute exactly zero,
    # and removing it must not change any other frame's share. This is the
    # claim ORCH's whole mechanism rests on, so it is measured not assumed.
    W = np.zeros((m, npx))
    W[:6] = rng.random((6, npx)) + 0.5
    sh4, ne4, _ = _share_neff(W)
    sh4b, ne4b, _ = _share_neff(W[:6])
    res["C4"] = dict(share_with_dead=sh4, share_without=sh4b,
                     n_eff_with_dead=ne4, n_eff_without=ne4b)
    if abs(sh4 - sh4b) > 1e-12 or abs(ne4 - ne4b) > 1e-9:
        ok = False

    # C5 DIRECTION: adding tied competitors must LOWER share and RAISE n_eff.
    # A statistic that fails this cannot measure dilution at all.
    a = _share_neff(np.ones((6, npx)))
    b = _share_neff(np.ones((60, npx)))
    res["C5"] = dict(share6=a[0], share60=b[0], neff6=a[1], neff60=b[1])
    if not (b[0] < a[0] and b[1] > a[1]):
        ok = False

    # C6 EXACT IDENTITY OF THE MERGED-AMPLITUDE WIRING. Feed the real
    # accumulator N byte-identical frames. Then every weight at a pixel is
    # equal, so the weighted merge IS the plain mean, and band_amp must equal
    # mean_amp to floating-point precision -- while share must be exactly 1/n.
    # This lives here rather than in commission_real because the synthetic
    # "tie" arm equalises FOCUS, not pixels: its per-frame noise still elects
    # a winner, and the 0.11% residual that leaves is the mottle mechanism
    # showing up in a commissioning arm rather than an error.
    base = synth_stack("graded", 2, size=64)[0]
    nid = 7
    accid, _, varid = band_accumulate([base.copy() for _ in range(nid)],
                                      VP.fit_variance(base)[0],
                                      {"id": list(range(nid))})
    sid = summarise(accid, varid)["id"]
    amp_err = max(abs(r["band_amp"] - r["mean_amp"]) /
                  max(r["mean_amp"], 1e-12) for r in sid)
    sh_err = max(abs(r["share"] - 1.0 / nid) for r in sid
                 if r["share"] == r["share"])
    res["C6"] = dict(n=nid, amp_rel_err=amp_err, share_abs_err=sh_err,
                     expect_share=1.0 / nid)
    if not (amp_err < 1e-12 and sh_err < 1e-12):
        ok = False

    # C7 that identity must be a PREDICTION, not a short-circuit. Perturb one
    # frame by a sweep of amplitudes and require the displacement to be zero
    # at zero perturbation and to grow monotonically -- ORCH's warning about
    # `resamp.py` returning exactly 1.0000 from an `if s == 1` branch.
    #
    # MEASURED FAILURE THAT SHAPED THIS. The first version scored the sweep on
    # the MAX over bands at size = 64, where band 6 is a SINGLE pixel. That
    # pixel read dead (merged = mean, displacement exactly 0.0000) at four of
    # the five sweep points and live at the fifth, so the max was 0.7796 at
    # eps = 0.1 and 0.0000 at eps = 1.0 and the control failed as
    # non-monotone. Every band with more than one pixel was strictly monotone.
    # A degenerate band is not evidence either way, so bands below
    # MIN_BAND_PX are EXCLUDED BY A STATED RULE and reported by name, rather
    # than absorbed into a summary statistic where a skipped band and a passed
    # band print the same glyph.
    sizec = 256
    basec = synth_stack("graded", 2, size=sizec)[0]
    v0c = VP.fit_variance(basec)[0]
    sweep, scored, skipped = [], None, None
    for eps in (0.0, 0.001, 0.01, 0.1, 1.0):
        fr = [basec.copy() for _ in range(nid)]
        fr[0] = fr[0] * (1.0 + eps)
        acce, _, vare = band_accumulate(fr, v0c, {"id": list(range(nid))})
        se = summarise(acce, vare)["id"]
        if scored is None:
            scored = [r["band"] for r in se if r["px_total"] >= MIN_BAND_PX]
            skipped = [dict(band=r["band"], px=r["px_total"]) for r in se
                       if r["px_total"] < MIN_BAND_PX]
        sweep.append(dict(eps=eps, per_band={
            r["band"]: abs(r["band_amp"] - r["mean_amp"]) /
            max(r["mean_amp"], 1e-12) for r in se if r["band"] in scored}))
    bad = []
    for k in scored:
        d = [s["per_band"][k] for s in sweep]
        if d[0] >= 1e-12:
            bad.append(dict(band=k, why="nonzero at eps=0", v=d[0]))
        if not all(d[i] <= d[i + 1] for i in range(len(d) - 1)):
            bad.append(dict(band=k, why="non-monotone", v=d))
        if d[-1] <= 1e-6:
            bad.append(dict(band=k, why="never responds", v=d[-1]))
    res["C7"] = dict(size=sizec, min_band_px=MIN_BAND_PX,
                     bands_scored=scored, bands_skipped=skipped,
                     n_scored=len(scored), n_skipped=len(skipped),
                     n_bands_total=len(scored) + len(skipped),
                     sweep=sweep, violations=bad)
    if bad or not scored:
        ok = False

    res["ok"] = ok
    return res


def synth_stack(kind, n, size=256, seed=7):
    """Synthetic frames with a KNOWN through-focus structure.

    All three arms come from ONE knob -- the focus selectivity `scale` -- over
    an IDENTICAL base texture, depth map and noise realisation, so the arms
    differ only in the variable under test. ORCH's softness lane found its own
    arms rendered at mismatched exposure before it reached a number; sharing
    the seed and the base is how this one avoids the same class of error, and
    `synth_arms_differ_only_in_scale` checks it rather than asserting it.

    Pixel depth is a ramp `D(y)` in [-1, 1]; frame i is focused at
    `d_i = -1 + 2i/(n-1)`; the defocus blur at a pixel is `|D - d_i| * scale`.
    So the band-energy curve across frames is a genuine graded response with a
    single peak, which is exactly the structure ORCH's two-point model omits.

        scale = 0    every frame identical up to noise      -> maximal tie
        scale = 3    a graded response, several frames near  -> realistic
        scale = 40   only the nearest frame is unblurred     -> maximal spike

    MEASURED FAILURE THAT SHAPED THIS. The first version made each frame sharp
    only inside a stripe of half-width 0.02 while the depth step was 0.087, so
    the stripes did not tile the frame and most pixels had NO sharp frame at
    all. The "spike" arm came back with n_eff RISING 5.67% -- more diluted
    than the graded arm -- and commissioning refused. A plant that does not
    plant is indistinguishable from a statistic that cannot see it.
    """
    from scipy.ndimage import gaussian_filter
    scale = {"tie": 0.0, "graded": 3.0, "spike": 40.0}[kind]
    rng = np.random.default_rng(seed)
    base = rng.standard_normal((size, size))
    base = VP.smooth5(base)
    base = 2000.0 + 4000.0 * (base - base.min()) / np.ptp(base)
    sigmas = np.concatenate([[0.0], np.geomspace(0.25, 8.0, 15)])
    blurs = np.stack([base if s == 0.0 else gaussian_filter(base, s)
                      for s in sigmas])
    D = np.linspace(-1.0, 1.0, size)[:, None] * np.ones((1, size))
    noise = rng.standard_normal((n, size, size)) * 25.0
    frames = []
    for i in range(n):
        d = -1.0 + 2.0 * i / max(n - 1, 1)
        defocus = np.abs(D - d) * scale
        idx = np.abs(sigmas[:, None, None] - defocus[None]).argmin(axis=0)
        frames.append(np.take_along_axis(blurs, idx[None], axis=0)[0]
                      + noise[i])
    return frames


def synth_arms_differ_only_in_scale(n=8, size=64):
    """At scale 0 the arm must be byte-identical to a second build of itself,
    and the graded and spike arms must share their noise exactly. Verified,
    not asserted: this is the check the softness lane wished it had run."""
    a = synth_stack("tie", n, size)
    b = synth_stack("tie", n, size)
    same = all(np.array_equal(x, y) for x, y in zip(a, b))
    g = synth_stack("graded", n, size)
    s = synth_stack("spike", n, size)
    # Identical noise => the difference between arms is pure focus structure.
    # At the in-focus pixel row of frame 0 both arms are unblurred, so they
    # must agree there to the last bit.
    agree0 = np.allclose(g[0][0], s[0][0], rtol=0, atol=1e-9)
    return dict(reproducible=bool(same), shared_noise_at_focus=bool(agree0))



def commission_real():
    """The full path -- band_accumulate + summarise -- under both plants.

    Both directions, per the project rule. A plant that only ever makes the
    reading worse cannot distinguish a blind statistic from a working one.
    Margins are recorded, not reduced to a boolean.
    """
    n, band = 24, 3
    out = {}
    for kind in ("graded", "tie", "spike"):
        fr = synth_stack(kind, n)
        var0, _, _ = VP.fit_variance(fr[0])
        acc, _, varp = band_accumulate(fr, var0, {"all": list(range(n))})
        s = summarise(acc, varp)["all"][band]
        out[kind] = dict(share=s["share"], n_eff=s["n_eff"],
                         adm_mean=s["adm_mean"], px_live=s["px_live"],
                         px_dead=s["px_dead"], px_total=s["px_total"],
                         band_amp=s["band_amp"], mean_amp=s["mean_amp"],
                         amp_gain=s["band_amp"] / s["mean_amp"])
    g, t, p = out["graded"], out["tie"], out["spike"]
    out["margins"] = dict(
        tie_share_rel=(t["share"] - g["share"]) / g["share"],
        tie_neff_rel=(t["n_eff"] - g["n_eff"]) / g["n_eff"],
        spike_share_rel=(p["share"] - g["share"]) / g["share"],
        spike_neff_rel=(p["n_eff"] - g["n_eff"]) / g["n_eff"],
        # `band_amp` is an ABSOLUTE amplitude and the three arms do not share
        # scene content, so comparing it across arms is a mismatched gauge --
        # the spike arm has less in-focus energy per frame by construction.
        # The matched comparison is each arm's merge against its OWN plain
        # mean, on the same pixels, which is what amp_gain is.
        spike_amp_gain_rel=(p["amp_gain"] - g["amp_gain"]) / g["amp_gain"],
        tie_amp_gain_rel=(t["amp_gain"] - g["amp_gain"]) / g["amp_gain"],
        tie_amp_vs_mean=abs(t["amp_gain"] - 1.0),
        graded_amp_vs_mean=g["amp_gain"] - 1.0)
    mg = out["margins"]
    out["ok"] = bool(mg["tie_share_rel"] < -0.01 and mg["tie_neff_rel"] > 0.01
                     and mg["spike_share_rel"] > 0.01
                     and mg["spike_neff_rel"] < -0.01
                     # C6 planted improvement: a merge that selects a real
                     # feature must beat its own plain mean by MORE than one
                     # merging a stack where selection buys little. A
                     # statistic that only ever falls under a plant is blind
                     # to the trade the fix can take.
                     and mg["spike_amp_gain_rel"] > 0.01
                     # C7 planted degradation: with focus variation removed,
                     # the merge must lose its advantage over the plain mean
                     # and collapse toward it.
                     and mg["tie_amp_gain_rel"] < -0.01
                     and mg["tie_amp_vs_mean"] < 0.02
                     # C8: that collapse must be a reading and not a
                     # short-circuit -- the same code separates merge from
                     # mean by 100x more on a graded stack.
                     and mg["graded_amp_vs_mean"] >
                     50.0 * mg["tie_amp_vs_mean"])
    for k in ("graded", "tie", "spike"):
        if out[k]["px_live"] + out[k]["px_dead"] != out[k]["px_total"]:
            out["ok"] = False
    return out


# ---------------------------------------------------------------- main
def measure(subj, frames, nb=NB, theta=THETA):
    n = len(frames)
    var0, read2, gph = VP.fit_variance(frames[0])
    rungs = make_rungs(n)
    flat = flat_masks(frames, None, nb)
    acc, _, varp = band_accumulate(frames, var0, rungs, nb=nb)
    # Second pass: ORCH's proposed N-invariant fix, measured on the same
    # pixels with the same frames. r_max is the per-rung, per-pixel maximum
    # of r taken from the first pass, so the two arms differ only in the
    # weighting law.
    rmax = {name: [acc[name][k]["emax"] for k in range(nb)] for name in rungs}
    accf, _, _ = band_accumulate(frames, var0, rungs, nb=nb, mode="rmax",
                                 theta=theta, rmax=rmax)
    return dict(subject=subj, n=n,
                var_read2=read2, var_gain=gph, theta=theta,
                rungs={k: len(v) for k, v in rungs.items()},
                ladder=exponent_ladder(nb), band_cyc=BAND_CYC,
                all_px=summarise(acc, varp, nb=nb),
                flat_px=summarise(acc, varp, flat=flat, nb=nb),
                fix_all_px=summarise(accf, varp, nb=nb),
                fix_flat_px=summarise(accf, varp, flat=flat, nb=nb))


def main():
    os.makedirs(OUT, exist_ok=True)
    import vn_gbundle as GB
    subs = sys.argv[1:] or ["coffee-bubbles"]

    print("COMMISSIONING (arithmetic)")
    ca = commission_arith()
    for k in ("C1", "C2", "C4", "C5"):
        print("  %s %s" % (k, json.dumps(ca[k], default=float)))
    c3 = ca["C3"]
    print("  C3 monotone=%s  zero-perturbation displacement=%.3g  "
          "first eps over 1%%=%s" % (c3["monotone"], c3["zero_eps_d_rel"],
                                     c3["first_eps_over_1pct"]))
    for x in c3["sweep"]:
        print("     eps %-6.3f share %.6f  displacement %+.3f%%"
              % (x["eps"], x["share"], 100 * x["d_rel"]))
    print("  arithmetic ok: %s" % ca["ok"])
    print("\nARM HYGIENE (arms must differ only in the knob)")
    print("  %s" % json.dumps(synth_arms_differ_only_in_scale()))
    print("\nCOMMISSIONING (full path, both directions)")
    cr = commission_real()
    for k in ("graded", "tie", "spike"):
        print("  %-7s share %.4f  n_eff %6.2f  adm %5.2f"
              % (k, cr[k]["share"], cr[k]["n_eff"], cr[k]["adm_mean"]))
    for k, v in cr["margins"].items():
        print("    %-18s %+8.2f%%" % (k, 100 * v))
    print("  full-path ok: %s" % cr["ok"])
    if not (ca["ok"] and cr["ok"]):
        print("\nREFUSED: commissioning failed; no measurement reported")
        return 1

    a = part_a()
    print("\nPART A: how much of ORCH's dilution survives the excess ratio")
    print("  ladder (finest->coarsest): %s"
          % ", ".join("%.2f" % x for x in a["ladder"]))

    fr = band_frequency_response()
    print("\nBAND <-> FREQUENCY, MEASURED (fraction of full-res variance)")
    print("  cyc/px   " + "".join("L%-7d" % k for k in range(NB)) + " peak")
    for r in fr["rows"]:
        print("  %-8.4f " % r["cyc"]
              + "".join("%-8.3f" % x for x in r["frac"])
              + " L%d" % r["peak_band"])
    print("  band peak cyc/px measured: %s"
          % ", ".join("L%d=%.3f" % (k, v)
                      for k, v in enumerate(fr["peak_cyc_per_band"])))
    res_fr = fr

    res = dict(part_a=a, bandfreq=res_fr,
               commission=dict(arith=ca, real=cr,
                               arms=synth_arms_differ_only_in_scale()),
               subjects={})
    for s in subs:
        # "<subject>@registered" widens admission to every frame that got a
        # warp. On a deep stack `ok_b`'s ncc >= 0.75 threshold removes frames
        # that are merely far from the master's focus plane, and measuring the
        # 172-frame subrange that survives would answer a question about depth
        # with a stack that has had its depth removed.
        rule = None
        if "@" in s:
            s, rule = s.split("@", 1)
        try:
            frames, kept, meta = GB.load(s, rule=rule)
        except (IOError, OSError) as e:
            print("  %s NOT EXAMINED: %s" % (s, e))
            res["subjects"][s] = {"state": "NOT EXAMINED", "why": str(e)}
            continue
        key = s if rule is None else "%s@%s" % (s, rule)
        print("\nPART B/C: %s, %d frames admitted (%s, rule %s), source "
              "index span %d..%d"
              % (key, len(frames), meta.get("source"), meta.get("admit_rule"),
                 kept[0], kept[-1]))
        r = measure(s, list(frames))
        r["state"] = "MEASURED"
        r["source"] = meta.get("source")
        r["admit_rule"] = meta.get("admit_rule")
        r["index_span"] = [int(kept[0]), int(kept[-1])]
        r["n_in_stack"] = len(meta.get("rows", [])) or None
        res["subjects"][key] = r
        names = sorted(r["all_px"], key=lambda x: int(x[1:]))
        small = [k for k in range(NB)
                 if r["all_px"][names[0]][k]["px_total"] < MIN_BAND_PX]
        print("    bands scored %d, skipped %d (below %d px: %s), total %d"
              % (NB - len(small), len(small), MIN_BAND_PX,
                 small or "none", NB))
        stats = [("dead_frac", "%7.4f",
                  "fraction of coefficients with NOTHING admitted "
                  "-> plain mean of all N"),
                 ("share", "%7.4f", "winner's share of the weight, "
                  "live coefficients only"),
                 ("n_eff", "%7.2f", "effective frames, live only"),
                 ("n_eff_incl_dead", "%7.2f",
                  "effective frames counting the mean fallback as full "
                  "participation (section 9.4's convention)"),
                 ("amp_gain", "%7.4f",
                  "merged band RMS / plain-mean band RMS, SAME pixels "
                  "-- >1 means the merge is sharper than averaging")]
        for scope, arm in (("all_px", "SHIPPING"), ("flat_px", "SHIPPING"),
                           ("fix_all_px", "FIX r_max theta=%.2f" % THETA)):
            print("  == %s | %s ==" % (scope, arm))
            for key, fmt, why in stats:
                print("   -- %s: %s" % (key, why))
                print("      band  cyc/px    p    "
                      + "".join("%-9s" % n for n in names))
                for k in range(NB):
                    x0 = r[scope][names[0]][k]
                    line = "      L%-4d %-8.4f %-5.2f" % (k, BAND_CYC[k],
                                                          x0["p"])
                    for n in names:
                        x = r[scope][n][k]
                        v = (x["band_amp"] / x["mean_amp"]
                             if key == "amp_gain" else x[key])
                        line += (fmt + "  ") % v
                    print(line + ("   [SKIPPED px<%d]" % MIN_BAND_PX
                                  if k in small else ""))
        del frames
    p = os.path.join(OUT, "dilute.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
