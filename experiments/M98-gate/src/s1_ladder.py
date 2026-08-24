"""M98 S1 -- the gate ladder, both contested metrics, from the same half-merges.

Runs the RULE 9 FLAT-ROI CONTROL FIRST, before any headline, because a metric
that credits a defocused background with gaining detail invalidates every number
already computed with it (rule 9's own text: run it first, not as a closing
check).

Usage:  python s1_ladder.py <stack>
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402
import m57lib as K    # noqa: E402

STACK = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else list(M98.ARMS)


def main():
    t0 = time.time()
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log(f"M98 S1 -- gate ladder on {STACK}")
    log("  Both metrics from the SAME two half-merges (parity frame split):")
    log("    A_hf  band cross-power over f in [0.15, 0.2762] cyc/px  -- M85's")
    log("          quantity, made noise-free.  Ratio A_hf(T)/A_hf(0).")
    log("    dsig  m57lib equivalent-Gaussian-blur difference, px, over")
    log("          f in [0.05, 0.2762].  M92's quantity.  POSITIVE = gate T is")
    log("          BLURRIER than gate 0.")
    log("=" * 78)

    # ---- geometry and the stratification map, fixed on the gate-0 ALN render
    ref = M98.render_path(STACK, "ALN", 0.0, "A")
    g0a = M98.green(ref)
    h, w = g0a.shape
    grid = M98.roi_grid(h, w)
    hp = [M98.hp_sd(M98.crop(g0a, xy)) for xy in grid]
    ter = M98.terciles(hp)
    log(f"\nrender geometry : {w} x {h}   ROIs: {len(grid)} of {M98.ROI}^2")
    log(f"stratifier      : m41lib.hp_sd (9x9 high-pass sd) on {os.path.basename(ref)}")
    log(f"terciles        : low {[f'{hp[i]:.2f}' for i in ter['low']]}")
    log(f"                  mid {[f'{hp[i]:.2f}' for i in ter['mid']]}")
    log(f"                  high {[f'{hp[i]:.2f}' for i in ter['high']]}")

    result = dict(stack=STACK, w=w, h=h, grid=grid, hp_sd=hp,
                  terciles={k: [int(i) for i in v] for k, v in ter.items()},
                  arms={})

    for arm in ARMS:
        log("\n" + "=" * 78)
        log(f"ARM {arm}")
        log("=" * 78)
        planes = {}
        for g in M98.GATES:
            pa, pb = (M98.render_path(STACK, arm, g, hf) for hf in ("A", "B"))
            if not (os.path.exists(pa) and os.path.exists(pb)):
                log(f"  MISSING renders for gate {g:g}; arm skipped")
                planes = None
                break
            planes[g] = (M98.green(pa), M98.green(pb))
        if planes is None:
            continue

        # ---------------- PAIR REGISTRATION (instrument repair, S9) ----------
        # Each half solved its own alignment and got its own fit_to_cover
        # scale, so the two renders are at different magnifications.  Fitted
        # ONCE here on the gate-0 pair and applied unchanged at every gate.
        cen, sh, pk = [], [], []
        for xy in grid:
            dy, dx, q = M98.shift_of(M98.crop(planes[0.0][0], xy),
                                     M98.crop(planes[0.0][1], xy))
            cen.append(xy)
            sh.append((dy, dx))
            pk.append(q)
        fit = M98.fit_similarity(cen, sh, h, w)
        log(f"\n--- PAIR REGISTRATION (frozen on gate 0, applied at all gates) ---")
        log(f"  per-ROI phase-correlation peak / median |cc| : "
            f"min {min(pk):.1f}  med {np.median(pk):.1f}")
        log(f"  fitted scale s = {fit['s']:+.6f}  (half B is {1+fit['s']:.6f}x "
            f"half A about the plane centre)")
        log(f"  fitted shift   = ({fit['ty']:+.3f}, {fit['tx']:+.3f}) px")
        log(f"  residual after the similarity: rms {fit['resid_rms']:.3f} px, "
            f"max {fit['resid_max']:.3f} px")
        kk = M98.cover_scales(STACK, arm)
        if kk:
            pred = kk["A"] / kk["B"] - 1.0
            log(f"  INDEPENDENT CHECK -- the render logs' fit_to_cover scales are")
            log(f"    k_A = {kk['A']:.4f}, k_B = {kk['B']:.4f}, so half B should be")
            log(f"    k_A/k_B - 1 = {pred:+.6f}.  Fitted {fit['s']:+.6f}.  "
                f"Difference {fit['s']-pred:+.6f}.")
            log(f"    The fit never sees this number.")
        result.setdefault("pairfit", {})[arm] = dict(fit=fit, peak_med=float(np.median(pk)),
                                                     cover=kk)
        for g in M98.GATES:
            a, b = planes[g]
            planes[g] = (a, M98.apply_similarity(b, fit, h, w))
        # per-ROI residual, also frozen on gate 0
        res = []
        for xy in grid:
            dy, dx, _ = M98.shift_of(M98.crop(planes[0.0][0], xy),
                                     M98.crop(planes[0.0][1], xy))
            res.append((dy, dx))
        log(f"  per-ROI residual after resampling: rms "
            f"{np.sqrt(np.mean([d[0]**2+d[1]**2 for d in res])):.3f} px "
            f"-- removed per ROI by an exact Fourier shift, frozen on gate 0")
        crops = {g: [(M98.crop(planes[g][0], xy),
                      M98.fourier_shift(M98.crop(planes[g][1], xy), *res[k]))
                     for k, xy in enumerate(grid)] for g in M98.GATES}

        # ---------------- RULE 9: FLAT-ROI CONTROL, RUN FIRST ----------------
        kflat = int(np.argmin(hp))
        log(f"\n--- RULE 9 FLAT-ROI CONTROL (run FIRST) --- ROI {kflat} at "
            f"{grid[kflat]}, hp_sd {hp[kflat]:.3f}")
        log(f"  {'gate':>5} {'sigma_flat(DN)':>15} {'ratio':>8} {'N_incoh':>13}"
            f" {'N ratio':>9} {'n_eff_loc':>10} {'A_hf':>14} {'A_hf ratio':>11}")
        flat = {}
        a0 = None
        rs_flat = {g: K.RingStats(*crops[g][kflat]) for g in M98.GATES}
        for g in M98.GATES:
            ca, cb = crops[g][kflat]
            sf = M98.sigma_flat(ca, cb)
            ah = M98.a_hf(rs_flat[g])
            ni = M98.n_incoh(rs_flat[g])
            ne = M98.n_eff_local(rs_flat[0.0], rs_flat[g])
            if a0 is None:
                sf0, a0, n0 = sf, ah, ni
            flat[g] = dict(sigma_flat=sf, a_hf=ah, n_incoh=ni, n_eff_loc=ne)
            log(f"  {g:>5g} {sf:>15.5f} {sf/sf0:>8.4f} {ni:>13.5g} "
                f"{ni/n0:>9.4f} {ne:>10.3f} {ah:>14.5g} {ah/a0:>11.4f}")
        r_sig = flat[4.0]["sigma_flat"] / flat[0.0]["sigma_flat"]
        r_n = flat[4.0]["n_incoh"] / flat[0.0]["n_incoh"]
        r_ahf = flat[4.0]["a_hf"] / flat[0.0]["a_hf"]
        ok_flat = (r_n <= 0.25) and (r_ahf <= 1.05)
        log(f"  PRE-REGISTERED BAR: sigma_flat(4)/sigma_flat(0) <= 0.5  -> {r_sig:.4f}  "
            f"{'PASS' if r_sig <= 0.5 else 'FAIL'}")
        log(f"  REFINED BAR (declared as a departure, see report S9):")
        log(f"    N_incoh(4)/N_incoh(0) <= 0.25 (= sigma 0.5) -> {r_n:.4f}  "
            f"{'PASS' if r_n <= 0.25 else 'FAIL'}   [sigma ratio {np.sqrt(r_n):.4f}]")
        log(f"  BAR: A_hf(4)/A_hf(0) <= 1.05 on this ROI -> {r_ahf:.4f}  "
            f"{'PASS' if r_ahf <= 1.05 else 'FAIL'}")
        log(f"  FLAT control (refined): {'GREEN' if ok_flat else 'RED'}")

        # ---------------- the ladder, per ROI ----------------
        rs = {g: [K.RingStats(*crops[g][k]) for k in range(len(grid))]
              for g in M98.GATES}
        per_gate = {}
        for g in M98.GATES:
            rows = []
            for k, xy in enumerate(grid):
                ah = M98.a_hf(rs[g][k])
                ah0 = M98.a_hf(rs[0.0][k])
                d = K.dsig(rs[0.0][k], rs[g][k])
                ca, cb = crops[g][k]
                rows.append(dict(k=k, x=xy[0], y=xy[1], hp_sd=hp[k],
                                 a_hf=ah, a_hf_ratio=ah / ah0 if ah0 else np.nan,
                                 dsig=d["px"], dsig_se=d["se_px"], gof=d["gof"],
                                 n_incoh=M98.n_incoh(rs[g][k]),
                                 n_eff_loc=M98.n_eff_local(rs[0.0][k], rs[g][k]),
                                 sigma_flat=M98.sigma_flat(ca, cb)))
            per_gate[f"{g:g}"] = rows

        log(f"\n--- LADDER, pooled over all {len(grid)} ROIs ---")
        log(f"  {'gate':>5} {'A_hf(T)/A_hf(0)':>16} {'dsig(0->T) px':>15} "
            f"{'SE':>8} {'sigma':>7} {'n+':>4} {'n-':>4} {'n_eff_loc med':>14}")
        for g in M98.GATES:
            rows = per_gate[f"{g:g}"]
            sa = M98.stats_across([r["a_hf_ratio"] for r in rows])
            sd_ = M98.stats_across([r["dsig"] for r in rows])
            ne = np.nanmedian([r["n_eff_loc"] for r in rows])
            log(f"  {g:>5g} {sa['mean']:>16.5f} {sd_['mean']:>+15.5f} "
                f"{sd_['se']:>8.5f} {sd_['sigma']:>7.2f} {sd_['npos']:>4} "
                f"{sd_['nneg']:>4} {ne:>14.3f}")

        log(f"\n--- STRATIFIED by detail tercile (discipline 603) ---")
        strat = {}
        for name in ("low", "mid", "high"):
            idx = ter[name]
            log(f"\n  tercile {name.upper()}  (hp_sd "
                f"{min(hp[i] for i in idx):.2f} - {max(hp[i] for i in idx):.2f}, "
                f"{len(idx)} ROIs)")
            log(f"    {'gate':>5} {'A_hf ratio':>12} {'SE':>8} "
                f"{'dsig px':>10} {'SE':>8} {'sigma':>7} {'n<0':>5} "
                f"{'n_eff_loc':>10} {'gof med':>8}")
            strat[name] = {}
            for g in M98.GATES:
                rows = [per_gate[f"{g:g}"][i] for i in idx]
                sa = M98.stats_across([r["a_hf_ratio"] for r in rows])
                sd_ = M98.stats_across([r["dsig"] for r in rows])
                gg = [r["gof"] for r in rows if np.isfinite(r["gof"])]
                gof = float(np.median(gg)) if gg else float("nan")
                ne = M98.stats_across([r["n_eff_loc"] for r in rows])
                strat[name][f"{g:g}"] = dict(a_hf=sa, dsig=sd_, gof=gof, n_eff=ne)
                log(f"    {g:>5g} {sa['mean']:>12.5f} {sa['se']:>8.5f} "
                    f"{sd_['mean']:>+10.5f} {sd_['se']:>8.5f} {sd_['sigma']:>7.2f} "
                    f"{sd_['nneg']:>5} {ne['mean']:>10.3f} {gof:>8.4f}")

        result["arms"][arm] = dict(per_gate=per_gate, strat=strat, flat=flat,
                                   flat_roi=kflat, flat_ok=bool(ok_flat))

    log(f"\n({time.time()-t0:.0f}s)")
    tag = "" if ARMS == list(M98.ARMS) else "-" + "_".join(ARMS)
    with open(os.path.join(M98.OUT, f"s1_{STACK}{tag}.json"), "w") as fh:
        json.dump(result, fh, indent=1, default=float)
    with open(os.path.join(M98.OUT, f"s1_{STACK}{tag}.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
