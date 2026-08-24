"""M87 / 80 -- repair of 79's sign test, and the 2x2 that settles a sign flip
between 79 and section 27.7.

TWO THINGS WENT WRONG IN 79 AND BOTH ARE INSTRUMENT DEFECTS, NOT FINDINGS.

DEFECT 1 -- THE POSITIVE CONTROL PLANTED A GAIN THAT CANCELS THE REAL ONE.
    S0 measured this cube's natural drift at Spearman rho = -0.9289 against
    frame index -- strongly ordered and DECREASING.  My ramp plant was
    `linspace(0.9, 1.1)`, rho = +1.0000, INCREASING.  Composing them multiplies
    a decreasing gain by an increasing one, so `g_real * ramp` has a smaller
    spread than `g_real` alone: I planted a control that made the effect
    smaller.  It returned slope -1.7375 and I am treating the whole S2 verdict
    as void.  The hump plant (rho = -0.5962, same direction as the drift)
    reinforced instead and returned +0.8123, which is the tell.
    THE FIX: build a DRIFT-FREE base first, `luma[k] / g_real[k]` with the
    election frozen, and plant onto that.  Cancellation is then impossible
    because there is nothing left to cancel against.

DEFECT 2 -- THE REGRESSION IS DOMINATED BY SCENE STRUCTURE.  R2 was 0.0014 on
    real data because the observed step between two adjacent pixels is mostly
    the scene changing, not the gain.  A slope fitted through that is fitting
    noise.
    THE FIX: a PAIRED DIFFERENCE.  Two composites that differ only in per-frame
    gain, with the election frozen bit-for-bit, have identical scene content, so
        Dpair(p,q) = [with(p) - with(q)] - [without(p) - without(q)]
    isolates the photometric contribution to the step EXACTLY.  The scene, the
    veil and the election all cancel.  This is the per-pair form of section
    27.5's cell 10, which M99 fact 22 makes the physically realisable arm.

AND A SIGN FLIP TO EXPLAIN.  Section 27.7 measured rho(excess, gap) = -0.0800
on all band pixels using a 5x5 winner-field range.  79 measured **+0.1662** on
M96's disconnected competitive set using M96's own gap.  Same cube, opposite
sign.  Two things differ -- the POPULATION and the STATISTIC -- and I ran them
confounded.  T1 separates them.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

T1 -- THE 2x2.  {all band pixels, M96-disconnected} x {M96 competitive-set gap,
    5x5 winner-field range}, pooled within distance bins, each against its own
    rolled null.
    REGISTERED: name which factor carries the sign.  If it is the POPULATION,
    section 27.7's negative reading is a dilution effect and the orchestrator's
    choice of M96's population is the correct one.  If it is the STATISTIC, one
    of the two gap definitions is measuring something else and I must say which.
    The connected cell is undefined by construction (M96's gap is identically 0
    there) and is reported as undefined, not as a number.

T2 -- THE REPAIRED SIGN TEST, on the paired difference.
C-EXACT -- the paired-difference estimator must recover the known photometric
    step with slope 1 and R2 near 1.  This is an algebraic identity, so anything
    else means my pairing is wrong and every number below it is void.
C-POS-RAMP / C-POS-HUMP -- plant each shape ONTO THE DRIFT-FREE BASE and require
    recovery.  Both must pass; if one shape passes and the other fails the
    instrument is keyed to plant shape.
C-NULL -- shuffle the frame->gain map; slope must collapse.

T3 -- THE NUMBER THAT ACTUALLY ANSWERS THE QUESTION, and it is an amplitude, not
    a correlation.  What FRACTION of the observed step at the silhouette is
    photometric?  median |Dpair| / median |observed step|, reported band-wide
    and at the veil peak d in [8,18].
    REGISTERED: a mechanism supplying under 25% of the step is not the cause of
    the veil; over 75% and it is; between, partial.

T4 -- THE HEAD-TO-HEAD THE ORCHESTRATOR ASKED FOR.  A veiling mechanism has a
    FIXED sign set by which side occludes: the pixel nearer the subject is
    veiled brighter.  A photometric step's sign is set by g.  Score both
    predictors on the SAME pairs by sign agreement.
    REGISTERED: report both agreements and their difference.  This is the
    cleanest single discriminator available and it needs no model fit at all.

READ-ONLY: D:\\personal\\macro.
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

REF_D = 140
BAND = (2, 40)
PEAK = (8, 18)
DMAX = 200
ROLL = (317, 511)
SEED = 8803
PLANT = 0.10
HUMP_PEAK = 110
HUMP_RATIO = 1.18


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def ols(x, y):
    xc = x - x.mean()
    yc = y - y.mean()
    den = float((xc * xc).sum())
    if den <= 0:
        return float("nan"), float("nan")
    b = float((xc * yc).sum() / den)
    sy = float((yc * yc).sum())
    return b, (b * b * den / sy if sy > 0 else float("nan"))


def main():
    t0 = time.time()
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    best = np.load(CACHE / "bee3-leg-best.npy")
    n, h, w = luma.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros((h, w), bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    band = valid & (dd >= BAND[0]) & (dd <= BAND[1])
    ref_px = valid & (dd >= REF_D)

    lvl = np.empty(n)
    for k in range(n):
        lvl[k] = float(np.asarray(luma[k], np.float32)[ref_px].mean())
    g_real = (lvl / lvl.mean()).astype(np.float64)
    kk = np.arange(n)
    print(f"real drift: rho vs k {spearmanr(lvl, kk).statistic:+.4f}   max/min "
          f"{lvl.max() / lvl.min():.4f}", flush=True)

    # ---------------- T1
    print("\n--- T1 population or statistic: which carries the sign? ---",
          flush=True)
    import importlib.util
    _s = importlib.util.spec_from_file_location(
        "m52", pathlib.Path(__file__).resolve().parent / "52-photometric-share.py")
    m52 = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(m52)
    disc, gap96, _cnt = m52.m96_stats(field, best)
    gap5 = (maximum_filter(argbest, 5) - minimum_filter(argbest, 5)).astype(np.float32)

    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, DMAX + 2))

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    P = np.empty((n, DMAX + 1))
    for k in range(n):
        P[k] = prof(np.asarray(luma[k], np.float32))
    with np.errstate(invalid="ignore"):
        ens = np.nanmean(P, axis=0)
    farlvl = float(np.nanmedian(ens[80:121]))
    ensmap = np.interp(dd, np.arange(DMAX + 1), np.nan_to_num(ens, nan=farlvl))
    exc = (sel0 - ensmap) / farlvl

    def pooled(gmap, sub):
        num = wsum = 0.0
        for d in range(BAND[0], BAND[1] + 1):
            s = sub & (dd == d)
            if int(s.sum()) < 500 or float(gmap[s].std()) < 1e-6:
                continue
            r = spearmanr(gmap[s], exc[s]).statistic
            if np.isfinite(r):
                num += r * int(s.sum())
                wsum += int(s.sum())
        return (num / wsum, int(wsum)) if wsum else (float("nan"), 0)

    t1 = {}
    for pn, sub in (("all band", band), ("M96 disconnected", band & disc)):
        for sn, gm in (("M96 gap", gap96), ("5x5 range", gap5)):
            r, nn = pooled(gm, sub)
            r0, _ = pooled(np.roll(gm, ROLL, axis=(0, 1)), sub)
            t1[f"{pn} / {sn}"] = {"rho": r, "null": r0, "n": nn}
            note = "" if np.isfinite(r) else "  (undefined: gap is identically 0)"
            print(f"  {pn:<17} x {sn:<10} n={nn:>7}  rho {r:+.4f}  null "
                  f"{r0:+.4f}{note}", flush=True)
    r_ab5 = t1["all band / 5x5 range"]["rho"]
    r_dc96 = t1["M96 disconnected / M96 gap"]["rho"]
    r_ab96 = t1["all band / M96 gap"]["rho"]
    r_dc5 = t1["M96 disconnected / 5x5 range"]["rho"]
    pop_swing = abs(r_dc5 - r_ab5)
    sta_swing = abs(r_ab96 - r_ab5)
    print(f"  holding the statistic at 5x5, changing population: "
          f"{r_ab5:+.4f} -> {r_dc5:+.4f}  (swing {pop_swing:.4f})", flush=True)
    print(f"  holding the population at all-band, changing statistic: "
          f"{r_ab5:+.4f} -> {r_ab96:+.4f}  (swing {sta_swing:.4f})", flush=True)
    driver = "POPULATION" if pop_swing > sta_swing else "STATISTIC"
    print(f"  -> the sign is carried by the {driver}", flush=True)

    # ---------------- pairs
    ay, ax = np.where(band[:-1, :] & band[1:, :])
    by, bx = np.where(band[:, :-1] & band[:, 1:])
    pi = np.concatenate([np.ravel_multi_index((ay, ax), (h, w)),
                         np.ravel_multi_index((by, bx), (h, w))])
    qi = np.concatenate([np.ravel_multi_index((ay + 1, ax), (h, w)),
                         np.ravel_multi_index((by, bx + 1), (h, w))])
    kp, kq = argbest.ravel()[pi], argbest.ravel()[qi]
    keep = kp != kq
    pi, qi, kp, kq = pi[keep], qi[keep], kp[keep], kq[keep]
    dp, dq = dd.ravel()[pi], dd.ravel()[qi]
    at_peak = (dp >= PEAK[0]) & (dp <= PEAK[1])
    print(f"\n{len(pi)} adjacent background pairs in d{BAND} elected different "
          f"frames; {int(at_peak.sum())} at the veil peak d{PEAK}", flush=True)

    def compose(g):
        out = np.empty((h, w), np.float32)
        for k in range(n):
            s = argbest == k
            if s.any():
                out[s] = (np.asarray(luma[k], np.float32) * np.float32(g[k]))[s]
        return out

    free = compose(1.0 / g_real)          # drift removed, election frozen
    obs_real = sel0.ravel()[pi] - sel0.ravel()[qi]
    fr_p, fr_q = free.ravel()[pi], free.ravel()[qi]

    def arm(comp, g, tag, bar=None):
        cp, cq = comp.ravel()[pi], comp.ravel()[qi]
        dpair = (cp - cq) - (fr_p - fr_q)
        pred = 0.5 * (fr_p + fr_q) * (g[kp] - g[kq])
        b, r2 = ols(pred, dpair)
        thr = np.quantile(np.abs(pred), 0.5)
        big = np.abs(pred) >= thr
        agree = float((np.sign(dpair[big]) == np.sign(pred[big])).mean())
        ok = "" if bar is None else ("  PASS" if bar[0] <= b <= bar[1] else "  FAIL")
        print(f"  {tag:<28} slope {b:+8.4f}   R2 {r2:7.4f}   sign "
              f"{100 * agree:6.2f}%{ok}", flush=True)
        return {"slope": b, "r2": float(r2), "sign": agree,
                "pass": None if bar is None else bool(bar[0] <= b <= bar[1])}

    print("\n--- T2 the repaired sign test, on the paired difference ---",
          flush=True)
    rng = np.random.default_rng(SEED)
    shuf = rng.permutation(n)
    ramp = np.linspace(1 - PLANT, 1 + PLANT, n)
    hump = 1.0 + (HUMP_RATIO - 1.0) * np.exp(-0.5 * ((kk - HUMP_PEAK) / (n / 4.0)) ** 2)
    hump = hump / hump.mean()
    t2 = {}
    t2["C-EXACT"] = arm(sel0, g_real, "C-EXACT real drift", (0.90, 1.10))
    t2["C-POS-RAMP"] = arm(compose(ramp / g_real), ramp, "C-POS-RAMP on drift-free",
                           (0.90, 1.10))
    t2["C-POS-HUMP"] = arm(compose(hump / g_real), hump, "C-POS-HUMP on drift-free",
                           (0.90, 1.10))
    t2["C-NULL"] = arm(sel0, g_real[shuf], "C-NULL shuffled g", (-0.25, 0.25))
    ctrl_ok = all(t2[k]["pass"] for k in t2)
    print(f"  all four controls {'PASS' if ctrl_ok else 'FAIL'}", flush=True)

    # ---------------- T3
    print("\n--- T3 what fraction of the observed step is photometric? ---",
          flush=True)
    dpair_real = (sel0.ravel()[pi] - sel0.ravel()[qi]) - (fr_p - fr_q)
    t3 = {}
    for tag, sub in (("whole band d(2,40)", np.ones(len(pi), bool)),
                     (f"veil peak d{PEAK}", at_peak)):
        frac = float(np.median(np.abs(dpair_real[sub])) /
                     np.median(np.abs(obs_real[sub])))
        t3[tag] = {"fraction": frac, "n": int(sub.sum()),
                   "median_abs_photometric": float(np.median(np.abs(dpair_real[sub]))),
                   "median_abs_observed": float(np.median(np.abs(obs_real[sub])))}
        print(f"  {tag:<22} photometric {np.median(np.abs(dpair_real[sub])):8.2f} DN "
              f"of an observed {np.median(np.abs(obs_real[sub])):8.2f} DN step "
              f"= {100 * frac:5.2f}%", flush=True)
    fpk = t3[f"veil peak d{PEAK}"]["fraction"]
    t3_v = ("NOT the cause" if fpk < 0.25 else
            "the cause" if fpk > 0.75 else "a PARTIAL contributor")
    print(f"  -> at the veil peak the photometric step is {t3_v} "
          f"({100 * fpk:.2f}%)", flush=True)

    # ---------------- T4
    print("\n--- T4 head to head: veil geometry against photometry ---",
          flush=True)
    pred_ph = np.sign(g_real[kp] - g_real[kq])
    pred_veil = np.sign(dq.astype(np.int64) - dp.astype(np.int64))
    so = np.sign(obs_real)
    use = (so != 0) & (pred_ph != 0) & (pred_veil != 0)
    a_ph = float((so[use] == pred_ph[use]).mean())
    a_ve = float((so[use] == pred_veil[use]).mean())
    usep = use & at_peak
    a_php = float((so[usep] == pred_ph[usep]).mean())
    a_vep = float((so[usep] == pred_veil[usep]).mean())
    print(f"  whole band  n={int(use.sum()):>7}   photometry "
          f"{100 * a_ph:6.2f}%   veil geometry {100 * a_ve:6.2f}%", flush=True)
    print(f"  veil peak   n={int(usep.sum()):>7}   photometry "
          f"{100 * a_php:6.2f}%   veil geometry {100 * a_vep:6.2f}%", flush=True)
    win = "VEIL GEOMETRY" if a_vep > a_php else "PHOTOMETRY"
    print(f"  -> at the veil peak the step's sign is better predicted by "
          f"{win} ({100 * max(a_vep, a_php):.2f}% against "
          f"{100 * min(a_vep, a_php):.2f}%)", flush=True)

    print("\n" + "=" * 74 + "\n=== VERDICT ===", flush=True)
    if not ctrl_ok:
        print("  VOID: a registered control failed; no reading is available",
              flush=True)
    else:
        print(f"  the photometric step is REAL and MEASURED, and it supplies "
              f"{100 * fpk:.2f}% of the rendered step at the veil peak", flush=True)
        print(f"  the step's sign is predicted by veil geometry at "
              f"{100 * a_vep:.2f}% and by photometry at {100 * a_php:.2f}%",
              flush=True)
        print(f"  T1: the section 27.7 / 79 sign flip is carried by the {driver}",
              flush=True)

    rep = {"rho_drift": float(spearmanr(lvl, kk).statistic), "T1": t1,
           "T1_driver": driver, "T1_pop_swing": float(pop_swing),
           "T1_stat_swing": float(sta_swing), "T2": t2, "controls_ok": bool(ctrl_ok),
           "T3": t3, "T3_verdict": t3_v,
           "T4": {"band_photometry": a_ph, "band_veil": a_ve,
                  "peak_photometry": a_php, "peak_veil": a_vep,
                  "n_band": int(use.sum()), "n_peak": int(usep.sum())},
           "n_pairs": int(len(pi)), "n_peak_pairs": int(at_peak.sum())}
    with open(DATA / "80-sign-repaired.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '80-sign-repaired.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
