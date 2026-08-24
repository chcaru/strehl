"""M77 addendum B -- apply PREREGISTRATION-B.md section B.6 verbatim.

X1  cross-check      dD(T*) > 0.98
X2  blind replication  any T > 4 with dN_ben >= 1.10 and dD > 0.98
X3  the null, which GATES X1:  |1-dD_null(T*)| / |1-dD(T*)| >= 0.5  ->  UNREADABLE
X4  the sigma limb (M71), priced

B.7 hazards 1-3 are evaluated and reported whatever the criteria say.

The post-hoc section at the end is labelled post hoc and does NOT overturn the
registered ruling. It is what the null makes computable, not a second bite.
"""

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m77  # noqa: E402

# M71 section 8.3, "shipped model" column: err = predicted sigma / true sigma - 1,
# per green photosite. Positive is conservative, negative is over-confident.
M71_S = [50.0, 200.0, 504.0, 1000.0, 2000.0, 8000.0, 15000.0]
M71_ERR = [0.0089, 0.0063, 0.0000, -0.0102, -0.0299, -0.1275, -0.2111]


def m71_err(s):
    """Log-linear interpolation of M71 section 8.3, clamped at the ends."""
    s = max(M71_S[0], min(M71_S[-1], float(s)))
    return float(np.interp(math.log(s), [math.log(v) for v in M71_S], M71_ERR))


def interp_gate(rows, ladder, target):
    """Gate at which n_eff == target, log-log between bracketing rungs."""
    ne = [rows[f"{g:g}"]["n_eff"] for g in ladder]
    for i in range(len(ladder) - 1):
        if ne[i] <= target <= ne[i + 1]:
            if ne[i + 1] <= ne[i]:
                return ladder[i], i, 0.0
            f = math.log(target / ne[i]) / math.log(ne[i + 1] / ne[i])
            g0, g1 = ladder[i], ladder[i + 1]
            if g0 <= 0:
                return g1 * f, i, f
            return g0 * (g1 / g0) ** f, i, f
    return None, None, None


def at(rows, ladder, key, i, f):
    a = rows[f"{ladder[i]:g}"][key]
    b = rows[f"{ladder[i + 1]:g}"][key]
    return a + f * (b - a)


def roi_mean_dn(stack, roi, n=5):
    """Mean green-luma level (DN above black) of the ROI, over n spread frames."""
    files = m77.stack_files(stack)
    idx = [round(k * (len(files) - 1) / (n - 1)) for k in range(n)]
    vals = []
    for i in idx:
        p = m77.green_luma_plane(files[i])
        vals.append(float(p[roi["y"]:roi["y"] + roi["h"],
                            roi["x"]:roi["x"] + roi["w"]].mean()))
    return float(np.mean(vals)), min(vals), max(vals)


def main():
    m77.banner("M77 addendum B -- section B.6 applied verbatim")
    data = json.loads((m77.OUT / "07-sweepB.json").read_text(encoding="utf-8"))
    res = {}
    for stack, d in data.items():
        ladder = d["ladder"]
        rows = d["rows"]
        tgt = d["m70_spectral_n_eff"]
        print(f"\n{'=' * 76}\n  {stack}   N={d['N']}  ISO {d['iso']:g}  "
              f"{'BLIND' if d['blind'] else 'NOT blind (declared B.2)'}")
        print(f"  M70 spectral n_eff = {tgt}   "
              f"(section 21.3, out/s07_unclipped.log:60-61)")

        tstar, i, f = interp_gate(rows, ladder, tgt)
        lo, ilo, flo = interp_gate(rows, ladder, 0.5 * tgt)
        hi, ihi, fhi = interp_gate(rows, ladder, 2.0 * tgt)
        print(f"  T*  = {tstar:.3f}   (n_eff {rows[f'{ladder[i]:g}']['n_eff']:.3f} "
              f"@ gate {ladder[i]:g}  ..  "
              f"{rows[f'{ladder[i + 1]:g}']['n_eff']:.3f} @ gate {ladder[i + 1]:g})")
        print(f"  band  T_lo = {lo:.3f} (n_eff {0.5 * tgt:.3f})   "
              f"T_hi = {hi:.3f} (n_eff {2.0 * tgt:.3f})   [B.5 factor-2 reading "
              f"of M70 section 21.5]")
        print(f"  shipped DEFAULT_GATE = {m77.DEFAULT_GATE:g}   "
              f"-> T*/default = {tstar / m77.DEFAULT_GATE:.2f}x")

        dD = at(rows, ladder, "dD", i, f)
        dDn = at(rows, ladder, "dD_null", i, f)
        dN = at(rows, ladder, "dN_ben", i, f)
        dD_lo = at(rows, ladder, "dD", ilo, flo)
        dD_hi = at(rows, ladder, "dD", ihi, fhi)

        x1 = dD > 0.98
        contam = abs(1.0 - dDn) / abs(1.0 - dD) if abs(1.0 - dD) > 1e-12 else math.inf
        x3_fires = contam >= 0.5
        print(f"\n  X1  dD(T*)      = {dD:.4f}   [bar > 0.98 -> "
              f"{'MET' if x1 else 'NOT MET'}]")
        print(f"      dN_ben(T*)  = {dN:.4f}")
        print(f"      dD across the factor-2 band: {dD_lo:.4f} .. {dD_hi:.4f}")
        print(f"  X3  dD_null(T*) = {dDn:.4f}   contam_D = "
              f"|1-{dDn:.4f}|/|1-{dD:.4f}| = {contam:.3f}   "
              f"[bar >= 0.50 -> {'FIRES' if x3_fires else 'clear'}]")
        verdict = "UNREADABLE" if x3_fires else ("MET" if x1 else "NOT MET")
        print(f"  ==> X1 VERDICT: {verdict}"
              + ("   (registered consequence B.6: decline to rule)"
                 if x3_fires else ""))

        free = [g for g in ladder
                if g > m77.DEFAULT_GATE
                and rows[f"{g:g}"]["dN_ben"] >= 1.10
                and rows[f"{g:g}"]["dD"] > 0.98]
        x2 = len(free) > 0
        print(f"\n  X2  rungs with T>4, dN_ben>=1.10, dD>0.98: "
              f"{[f'{g:g}' for g in free] if free else 'NONE'}   "
              f"[{'MET' if x2 else 'NOT MET'}]")
        if not x2:
            best = max((g for g in ladder if g > m77.DEFAULT_GATE
                        and rows[f'{g:g}']['dN_ben'] >= 1.10),
                       key=lambda g: rows[f"{g:g}"]["dD"], default=None)
            if best is not None:
                print(f"      closest: gate {best:g}  dN_ben "
                      f"{rows[f'{best:g}']['dN_ben']:.4f}  dD "
                      f"{rows[f'{best:g}']['dD']:.4f}  (misses the dD bar by "
                      f"{0.98 - rows[f'{best:g}']['dD']:.4f})")

        # --- X4: the sigma limb, priced.
        sbar, smin, smax = roi_mean_dn(stack, d["detail_roi"])
        e = m71_err(sbar)
        print(f"\n  X4  detail ROI mean green luma = {sbar:.1f} DN above black "
              f"({smin:.1f}..{smax:.1f} over 5 frames)")
        print(f"      M71 section 8.3 interpolated error at that level: "
              f"{e * 100:+.2f}%  ({'over-confident' if e < 0 else 'conservative'})")
        corr = {}
        for g in ladder:
            r = rows[f"{g:g}"]
            nt = r["model_noise"] / (1.0 + e)
            corr[f"{g:g}"] = math.sqrt(max(0.0, r["raw_rms"] ** 2 - nt * nt))
        ref = corr[f"{m77.DEFAULT_GATE:g}"]
        dD4_a = corr[f"{ladder[i]:g}"] / ref
        dD4_b = corr[f"{ladder[i + 1]:g}"] / ref
        dD4 = dD4_a + f * (dD4_b - dD4_a)
        crossed = (dD4 > 0.98) != x1
        print(f"      corrected_rms at gate 4: {rows[f'{m77.DEFAULT_GATE:g}']['corrected']:.3f}"
              f"  ->  {ref:.3f} under M71   "
              f"(model_noise {rows[f'{m77.DEFAULT_GATE:g}']['model_noise']:.3f} -> "
              f"{rows[f'{m77.DEFAULT_GATE:g}']['model_noise'] / (1 + e):.3f})")
        print(f"      dD(T*) under M71 = {dD4:.4f}  vs {dD:.4f} shipped   "
              f"-> bar {'CROSSED' if crossed else 'not crossed'}")

        # --- B.7 hazard 2: does the detail statistic track the null?
        a = np.array([rows[f"{g:g}"]["dD"] for g in ladder])
        b = np.array([rows[f"{g:g}"]["dD_null"] for g in ladder])
        r_p = float(np.corrcoef(a, b)[0, 1])
        print(f"\n  B.7-2  Pearson r(dD, dD_null) over {len(ladder)} rungs = "
              f"{r_p:.4f}   [bar > 0.95 -> {'FIRES' if r_p > 0.95 else 'clear'}]")

        # --- POST HOC, labelled: what the null makes computable.
        print("\n  POST HOC (not a registered criterion, does not overturn X1):")
        print(f"      {'gate':>6} {'corrected':>10} {'null':>9} {'signal':>9} "
              f"{'dD_sig':>8}")
        sig = {}
        for g in ladder:
            r = rows[f"{g:g}"]
            s = math.sqrt(max(0.0, r["corrected"] ** 2 - r["corrected_null"] ** 2))
            sig[f"{g:g}"] = s
        sref = sig[f"{m77.DEFAULT_GATE:g}"]
        for g in ladder:
            r = rows[f"{g:g}"]
            print(f"      {g:6g} {r['corrected']:10.3f} {r['corrected_null']:9.3f} "
                  f"{sig[f'{g:g}']:9.3f} "
                  f"{sig[f'{g:g}'] / sref if sref > 0 else float('nan'):8.4f}")
        sa, sb = sig[f"{ladder[i]:g}"] / sref, sig[f"{ladder[i + 1]:g}"] / sref
        dD_sig = sa + f * (sb - sa)
        print(f"      dD_sig(T*) = {dD_sig:.4f}   (structure-only, null subtracted "
              "in quadrature)")

        res[stack] = {
            "N": d["N"], "iso": d["iso"], "blind": d["blind"],
            "m70_spectral_n_eff": tgt, "T_star": tstar, "T_lo": lo, "T_hi": hi,
            "T_star_over_default": tstar / m77.DEFAULT_GATE,
            "dD_at_Tstar": dD, "dN_ben_at_Tstar": dN, "dD_null_at_Tstar": dDn,
            "dD_band": [dD_lo, dD_hi],
            "X1_bar_met": bool(x1), "X3_contam_D": contam,
            "X3_fires": bool(x3_fires), "X1_verdict": verdict,
            "X2_free_rungs": [f"{g:g}" for g in free], "X2_met": bool(x2),
            "X4_roi_mean_dn": sbar, "X4_m71_err": e,
            "X4_dD_at_Tstar_corrected": dD4, "X4_bar_crossed": bool(crossed),
            "hazard2_pearson_r": r_p,
            "posthoc_dD_signal_at_Tstar": dD_sig,
            "posthoc_signal": sig,
        }

    (m77.OUT / "08-decideB.json").write_text(json.dumps(res, indent=2),
                                             encoding="utf-8")
    print("\n  wrote out/08-decideB.json")


if __name__ == "__main__":
    main()
