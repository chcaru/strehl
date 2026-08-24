"""M92 S2 -- does the independent-noise null average down across disjoint ROIs?

This is the milestone's primary measurement.  Every bar it is read against was
frozen in PREREGISTRATION.md and committed at 55ecc26 before this file ran.

ARMS (PREREGISTRATION section 7)
  A1    N1 null, synthetic i.i.d. Gaussian, independent per ROI per draw,
        at the stack's CORRECT EXIF ISO.  Levels 1x, 2x, 3x the merged sigma.
        DECLARED LIMITATION: the injection is independent across ROIs BY
        CONSTRUCTION, so A1's cross-ROI correlation is a control on the
        correlation estimator, not a measurement of sensor common mode.  The
        between-ROI structure it does carry is real: it is the fixed content of
        each ROI's own half-merges.
  A1f   A1 on 109MSDCF at M57's hard-coded ISO 500, to price section 0's defect.
  NC1   the SAME noise realisation added at every ROI -- must go red.
  NC2   the SAME ROI repeated N times instead of N distinct ones -- must go red.
  PL    placebo: a planted Gaussian of exactly 0.1754 px (M82's largest finite
        price) and of 0.10 px (M57's PR4 signal) on configuration 2, WITH the
        same independent noise, so the placebo shares the null's noise
        structure exactly.
  PL2   fraction of (draw, subset) pairs at each N where the planted signal
        exceeds that N's measured null.

RULE 20.  What would make this fail: a floor.  If the per-ROI estimates share a
common-mode component, Null(N) plateaus at Null(1)*sqrt(rbar) and no number of
ROIs reaches M82's 0.1754 px.  NC1 and NC2 are the proof that the harness can
report that outcome.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as K    # noqa: E402

R = int(os.environ.get("M92_R", "128"))
E_M82 = 0.1754          # M82's largest finite central sharpness price, fact 1140
B_M57 = 0.343           # M57's per-ROI null bound, fact 1140's frozen bound
LEVELS = tuple(float(x) for x in os.environ.get("M92_LEVELS", "1,2,3").split(","))
PRIMARY_LEVEL = 2.0
PLANTS = tuple(float(x) for x in os.environ.get("M92_PLANTS", "0.1754,0.10").split(","))
ONLY = [s for s in os.environ.get("M92_STACKS", "").split(",") if s]
NBOOT = int(os.environ.get("M92_NBOOT", "1500"))
TAG = os.environ.get("M92_TAG", "")


def load_cells(stack, kind):
    z = np.load(os.path.join(M92.CACHE, f"cells_{stack}_{kind}.npz"))
    g = f"{M92.GATE_SHIPPED:.2f}"
    n = sum(1 for k in z.files if k.endswith(f"_{g}_a"))
    return [(z[f"{k:02d}_{g}_a"], z[f"{k:02d}_{g}_b"]) for k in range(n)]


def draw_block(ma, mb, sm, mult, seed, blur_sb=0.0, common=None, sym=False):
    """R draws of the N1 null (optionally with a planted blur) on one ROI.

    `sym` adds an independent noise realisation to configuration 1 as well, so
    both configurations carry the same noise.  That is closer to the real
    comparison (gate 0.50 vs gate 0.99 on the same frames, both noisy) than
    M57's one-sided N1, and is reported as a sensitivity variant, not a
    replacement.  Returns (px, slope, jack_se) each of length R.
    """
    base_a = K.M.blur(ma, blur_sb) if blur_sb > 0 else ma
    base_b = K.M.blur(mb, blur_sb) if blur_sb > 0 else mb
    rs1 = None if sym else K.RingStats(ma, mb)
    rng = np.random.default_rng(seed)
    px = np.empty(R); sl = np.empty(R); js = np.empty(R)
    add = sm * mult
    for r in range(R):
        if common is None:
            na = rng.standard_normal(ma.shape).astype(np.float32) * add
            nb = rng.standard_normal(mb.shape).astype(np.float32) * add
        else:
            na = common[0][r] * add
            nb = common[1][r] * add
        if sym:
            ca = rng.standard_normal(ma.shape).astype(np.float32) * add
            cb = rng.standard_normal(mb.shape).astype(np.float32) * add
            rs1 = K.RingStats(ma + ca, mb + cb)
        d = K.dsig(rs1, K.RingStats(base_a + na, base_b + nb))
        px[r], sl[r], js[r] = d["px"], d["slope"], d["se_px"]
    return px, sl, js


def slope_variant(sl):
    """Sensitivity variant: average the SLOPES, then transform to px.
    Reported whether or not it agrees with the primary (PREREGISTRATION s4)."""
    return sl


def report_ladder(tag, res, log):
    log(f"    {'N':>4}  {'Null(N) px':>11}  {'[95% CI]':>21}  {'mean px':>10}"
        f"  {'drop':>6}")
    for N in sorted(res):
        r = res[N]
        log(f"    {N:>4}  {r['rms']:11.5f}  [{r.get('ci_lo', np.nan):8.5f},"
            f"{r.get('ci_hi', np.nan):8.5f}]  {r['mean']:+10.5f}"
            f"  {100*r['drop_frac']:5.1f}%")


def analyse(d, sl, js, index, log, label, seed=92):
    """Ladder, exponent, correlation and jackknife honesty for one d matrix."""
    res = M92.null_rms_boot(d, index, seed=seed, nboot=NBOOT)
    a, r2 = M92.exponent(res)
    lo, hi, sda = M92.exponent_ci(d, index, seed=seed, nboot=max(NBOOT // 3, 40))
    resn = M92.null_rms(d, index, strict=False)
    an, _ = M92.exponent(resn)
    pc = M92.pair_corr(d)
    # slope-domain sensitivity variant, transformed back to px at each N
    resv = {}
    for N, idx in index.items():
        sub = sl[idx]
        ok = np.isfinite(sub).all(1)
        if not ok.any():
            resv[N] = dict(rms=np.nan, mean=np.nan, sd=np.nan, n=0, drop_frac=1.0)
            continue
        bbar = sub.mean(1)[ok]
        v = np.sign(bbar) * np.sqrt(np.abs(bbar))
        resv[N] = dict(rms=float(np.sqrt((v ** 2).mean())), mean=float(v.mean()),
                       sd=float(v.std(ddof=1)) if v.size > 1 else np.nan,
                       n=int(v.size), drop_frac=float(1 - ok.mean()))
    av, _ = M92.exponent(resv)
    with np.errstate(invalid="ignore"):
        sdj = np.nanstd(d, axis=1, ddof=1)
        mj = np.nanmedian(js, axis=1)
        ratio = sdj / mj
    nan_roi = 1.0 - np.isfinite(d).mean(axis=1)
    log(f"  [{label}]")
    report_ladder(label, res, log)
    log(f"    exponent alpha = {a:.4f}  (95% CI {lo:.4f}..{hi:.4f}, boot sd "
        f"{sda:.4f}, R^2 {r2:.4f})")
    log(f"    SENSITIVITY  slope-domain alpha = {av:.4f}   |   NaN-tolerant "
        f"(nanmean) alpha = {an:.4f}, Null(1) {resn[1]['rms']:.5f}, "
        f"Null({max(resn)}) {resn[max(resn)]['rms']:.5f}")
    log(f"    Null(1) {res[1]['rms']:.5f} px   Null(4) {res.get(4,{}).get('rms',np.nan):.5f} px"
        f"   Null(24) {res.get(24,{}).get('rms',np.nan):.5f} px")
    log(f"    per-ROI NaN rate: min {100*nan_roi.min():.1f}%  median "
        f"{100*np.median(nan_roi):.1f}%  max {100*nan_roi.max():.1f}%")
    log(f"    cross-ROI correlation rbar = {pc['rbar']:+.5f} +- {pc['se_rbar']:.5f}"
        f"  (median {pc['rmed']:+.4f}, range {pc['rmin']:+.4f}..{pc['rmax']:+.4f},"
        f" {pc['n_pair']} pairs)")
    log(f"    implied floor Null(1)*sqrt(rbar) = "
        f"{M92.implied_floor(res[1]['rms'], pc['rbar']):.5f} px"
        f"   N_eff at 24 ROIs = {M92.n_eff_rois(24, pc['rbar']):.2f}")
    log(f"    jackknife honesty sd(draws)/median(jack se): min {np.nanmin(ratio):.2f}"
        f"  median {np.nanmedian(ratio):.2f}  max {np.nanmax(ratio):.2f}"
        f"   (M57 S7 measured 1.29/1.90/3.09)")
    nreq = next((N for N in sorted(res)
                 if np.isfinite(res[N]["rms"]) and res[N]["rms"] < E_M82), None)
    log(f"    N required for Null(N) < {E_M82} px: "
        f"{nreq if nreq else '> 24 (not reached)'}")
    return dict(ladder={str(k): v for k, v in res.items()},
                ladder_slope_variant={str(k): v for k, v in resv.items()},
                ladder_nanmean={str(k): v for k, v in resn.items()},
                alpha=a, alpha_ci=[lo, hi], alpha_boot_sd=sda, alpha_r2=r2,
                alpha_slope_variant=av, alpha_nanmean=an, corr=pc,
                null1=res[1]["rms"], null4=res.get(4, {}).get("rms", np.nan),
                null24=res.get(24, {}).get("rms", np.nan),
                nan_roi=[float(nan_roi.min()), float(np.median(nan_roi)),
                         float(nan_roi.max())],
                implied_floor=M92.implied_floor(res[1]["rms"], pc["rbar"]),
                jack_ratio=[float(np.nanmin(ratio)), float(np.nanmedian(ratio)),
                            float(np.nanmax(ratio))],
                n_required=nreq)


def main():
    t0 = time.time()
    meta = json.load(open(os.path.join(M92.OUT, "s1_cells.json")))
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    out = {}
    log("=" * 78)
    log("M92 S2 -- does the null average down?  R = %d draws, 24 disjoint ROIs."
        % R)
    log(f"  bars frozen at 55ecc26: alpha >= 0.40, Null(4) < {E_M82} px,"
        f" Null(24) >= {E_M82} px is fatal, rbar >= 0.10 is material")
    log("=" * 78)

    for stack in (ONLY or list(M92.STACKS)):
        cells = load_cells(stack, "disjoint")
        rows = meta[stack]["disjoint"]
        iso = meta[stack]["iso"]
        log("\n" + "=" * 78)
        log(f"{stack}  ({meta[stack]['n_frames']} frames, EXIF ISO {iso})")
        log("=" * 78)

        # ---- rule 9: texture table, LOW-TEXTURE HALF FIRST -----------------
        order = np.argsort([r["hp_sd"] for r in rows])
        med = float(np.median([r["hp_sd"] for r in rows]))
        log(f"  ROI table, sorted by hp_sd (rule 9 -- low texture first). "
            f"median hp_sd {med:.3f}")
        log(f"    {'k':>3} {'x':>5} {'y':>5} {'hp_sd':>8} {'level DN':>9}"
            f" {'n_eff':>7} {'sigma_m DN':>11}")
        for k in order:
            r = rows[k]
            log(f"    {r['k']:>3} {r['x']:>5} {r['y']:>5} {r['hp_sd']:>8.3f}"
                f" {r['level']:>9.1f} {r['n_eff']:>7.3f} {r['sigma_merged']:>11.4f}")

        # ---- pre-noise screen, uses no null data --------------------------
        keep, screened = [], []
        for k, (ma, mb) in enumerate(cells):
            rs1 = K.RingStats(ma, mb)
            d = K.dsig(rs1, K.RingStats(K.M.blur(ma, 0.10), K.M.blur(mb, 0.10)))
            (keep if np.isfinite(d["px"]) else screened).append(k)
        log(f"  screen (noiseless, finite dsig at a planted 0.10 px): "
            f"{len(keep)}/{len(cells)} retained")
        if screened:
            log(f"    screened out: " + ", ".join(
                f"k={k} ({rows[k]['x']},{rows[k]['y']})" for k in screened))
        idxmap = M92.subset_index(len(keep), seed=92)

        sres = {"iso": iso, "n_frames": meta[stack]["n_frames"],
                "kept": keep, "screened": screened, "arms": {}}

        # ---- A1 (and A1f on the ISO-160 stack) ---------------------------
        isos = [("A1", iso)] + ([("A1f", 500)] if iso != 500 else [])
        for arm, use_iso in isos:
            for mult in (LEVELS if arm == "A1" else (PRIMARY_LEVEL,)):
                px = np.empty((len(keep), R)); sl = np.empty((len(keep), R))
                js = np.empty((len(keep), R))
                for j, k in enumerate(keep):
                    ma, mb = cells[k]
                    sm, _ = M92.merged_sigma(rows[k]["level"], use_iso,
                                             rows[k]["n_eff"])
                    px[j], sl[j], js[j] = draw_block(
                        ma, mb, sm, mult, seed=92_000 + 1000 * k + int(mult * 10))
                lbl = f"{arm} indep noise x{mult:.0f} (ISO {use_iso})"
                sres["arms"][lbl] = analyse(px, sl, js, idxmap, log, lbl)
                np.savez_compressed(os.path.join(
                    M92.CACHE, f"d_{stack}_{arm}_{mult:.0f}.npz"),
                    px=px, slope=sl, jack=js, keep=np.array(keep))
                log(f"    ({time.time()-t0:.0f}s)")

                # NC2 -- broken averaging, on the primary level only
                if arm == "A1" and mult == PRIMARY_LEVEL:
                    one = M92.subset_index(len(keep), seed=92, repeat_one=0)
                    r2 = M92.null_rms(px, one)
                    a2, _ = M92.exponent(r2)
                    log(f"  [NC2 broken averaging -- SAME ROI repeated N times]")
                    log(f"    Null(1) {r2[1]['rms']:.5f}  Null(4) {r2[4]['rms']:.5f}"
                        f"  Null(24) {r2[24]['rms']:.5f}  alpha {a2:.5f}")
                    red = (a2 < 0.15)
                    log(f"    max |Null(N) - Null(1)| = "
                        f"{max(abs(r2[N]['rms']-r2[1]['rms']) for N in r2):.3e}"
                        f"   SHIP criterion red = {red}")
                    sres["arms"]["NC2"] = dict(
                        ladder={str(k): v for k, v in r2.items()}, alpha=a2,
                        red=bool(red))

        # ---- NC1 common-mode injection (primary level) -------------------
        rngc = np.random.default_rng(4242)
        common_pool = (rngc.standard_normal((R, M92.ROI_N, M92.ROI_N)).astype(np.float32),
                       rngc.standard_normal((R, M92.ROI_N, M92.ROI_N)).astype(np.float32))
        px = np.empty((len(keep), R)); sl = np.empty((len(keep), R))
        js = np.empty((len(keep), R))
        for j, k in enumerate(keep):
            ma, mb = cells[k]
            sm, _ = M92.merged_sigma(rows[k]["level"], iso, rows[k]["n_eff"])
            px[j], sl[j], js[j] = draw_block(ma, mb, sm, PRIMARY_LEVEL, seed=0,
                                             common=common_pool)
        lbl = f"NC1 COMMON-MODE injection x{PRIMARY_LEVEL:.0f}"
        sres["arms"][lbl] = analyse(px, sl, js, idxmap, log, lbl)
        del common_pool
        log(f"    ({time.time()-t0:.0f}s)")

        # ---- PL placebo ---------------------------------------------------
        # PLsym's null baseline: the SAME symmetric noise construction with no
        # plant, so the placebo is read against its own matched null, never
        # against the one-sided one.
        pxs = np.empty((len(keep), R)); sls = np.empty((len(keep), R))
        jss = np.empty((len(keep), R))
        for j, k in enumerate(keep):
            ma, mb = cells[k]
            sm, _ = M92.merged_sigma(rows[k]["level"], iso, rows[k]["n_eff"])
            pxs[j], sls[j], jss[j] = draw_block(
                ma, mb, sm, PRIMARY_LEVEL, seed=94_000 + 1000 * k, sym=True)
        lbl = f"A1sym two-sided null x{PRIMARY_LEVEL:.0f} (ISO {iso})"
        sres["arms"][lbl] = analyse(pxs, sls, jss, idxmap, log, lbl)
        symbase = sres["arms"][lbl]
        log(f"    ({time.time()-t0:.0f}s)")

        for sb in PLANTS:
            for sym in ((False, True) if sb == PLANTS[0] else (False,)):
                tagp = "PLsym" if sym else "PL"
                pxp = np.empty((len(keep), R)); slp = np.empty((len(keep), R))
                jsp = np.empty((len(keep), R))
                noiseless = []
                for j, k in enumerate(keep):
                    ma, mb = cells[k]
                    sm, _ = M92.merged_sigma(rows[k]["level"], iso,
                                             rows[k]["n_eff"])
                    pxp[j], slp[j], jsp[j] = draw_block(
                        ma, mb, sm, PRIMARY_LEVEL,
                        seed=93_000 + 1000 * k + int(sb * 1e4) + (7 if sym else 0),
                        blur_sb=sb, sym=sym)
                    if not sym:
                        d0 = K.dsig(K.RingStats(ma, mb),
                                    K.RingStats(K.M.blur(ma, sb), K.M.blur(mb, sb)))
                        noiseless.append(d0["px"])
                log(f"  [{tagp} placebo: planted {sb} px, truth = +{sb} px "
                    f"exactly, with x{PRIMARY_LEVEL:.0f} "
                    f"{'two-sided' if sym else 'one-sided'} noise]")
                if noiseless:
                    nl = np.array(noiseless)
                    log(f"    noiseless recovery per ROI: mean {nl.mean():+.6f} px"
                        f" (ratio {nl.mean()/sb:.5f}), range "
                        f"{nl.min():+.6f}..{nl.max():+.6f}")
                base = (symbase if sym else
                        sres["arms"][f"A1 indep noise x{PRIMARY_LEVEL:.0f} (ISO {iso})"])
                log(f"    {'N':>4} {'mean px':>10} {'ratio':>8} {'sd px':>9}"
                    f" {'Null(N)':>9} {'frac > Null':>12}")
                pl = {}
                for N, idx in idxmap.items():
                    sub = pxp[idx]
                    ok = np.isfinite(sub).all(1)
                    if not ok.any():
                        continue
                    v = sub.mean(1)[ok]
                    nn = base["ladder"][str(N)]["rms"]
                    frac = float((np.abs(v) > nn).mean())
                    log(f"    {N:>4} {v.mean():+10.5f} {v.mean()/sb:8.4f}"
                        f" {v.std(ddof=1):9.5f} {nn:9.5f} {100*frac:11.1f}%")
                    pl[str(N)] = dict(mean=float(v.mean()),
                                      ratio=float(v.mean() / sb),
                                      sd=float(v.std(ddof=1)), null=nn,
                                      frac_over=frac)
                r24 = pl.get("24", {}).get("ratio", np.nan)
                log(f"    PL bar [0.85, 1.15] at N = 24: ratio {r24:.4f} -> "
                    f"{'PASS' if 0.85 <= r24 <= 1.15 else 'FAIL'}")
                sres["arms"][f"{tagp} {sb}"] = dict(
                    per_N=pl,
                    noiseless_mean=float(nl.mean()) if noiseless else None,
                    noiseless_ratio=float(nl.mean() / sb) if noiseless else None,
                    ratio_at_24=r24, pass_bar=bool(0.85 <= r24 <= 1.15))
                log(f"    ({time.time()-t0:.0f}s)")

        out[stack] = sres
        with open(os.path.join(M92.OUT, f"s2_null_averaging{TAG}.json"), "w") as fh:
            json.dump(out, fh, indent=2, default=float)

    with open(os.path.join(M92.OUT, f"s2_null_averaging{TAG}.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s2_null_averaging.{{json,log}}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
