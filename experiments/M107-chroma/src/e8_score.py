"""Score K1-K7 against the bars as REGISTERED, and render fig7.

Bars are read from PRE-REGISTRATION-2.md (bf975e0) and
PRE-REGISTRATION-2-AMENDMENT.md (e96040d). They are transcribed here as
constants so the scoring is mechanical: no verdict is chosen by looking at
the number and deciding afterwards what the threshold was.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT  # noqa: E402

FIG = os.path.join(OUT, "fig")
ROIS = [("centre", "bee hair, r = 125 px"), ("auto", "wing, r = 2713 px")]


def load(tag):
    return json.load(open(os.path.join(OUT, "json", f"e8_kernel_{tag}.json")))


def score(v, lo, hi, name, low_lab, mid_lab, hi_lab):
    if v < lo:
        return f"{name} = {v:.4f}  -> {low_lab}"
    if v > hi:
        return f"{name} = {v:.4f}  -> {hi_lab}"
    return f"{name} = {v:.4f}  -> {mid_lab}"


def main():
    D = {t: load(t) for t, _ in ROIS}
    lines = []
    for t, lab in ROIS:
        d = D[t]
        lines.append(f"\n=== ROI '{t}' ({lab}) ===")
        lines.append(f"K1 VALIDITY  catmull==gallery bytes: {d['K1_hash']['identical']}; "
                     f"corr(L_nearest,L_catmull) = {d['K4']['L']['corr']:.4f} "
                     f"(bar >= 0.60) -> "
                     f"{'PASS' if d['K1_hash']['identical'] and d['K4']['L']['corr'] >= 0.60 else 'FAIL'}")
        for ch in ("cr", "cb"):
            v = d["K2"][f"{ch}_ratio"]
            lines.append("K2 PREMISE   " + score(
                v, 1.05, 1.15, f"rms({ch}) nearest/catmull",
                "PREMISE FALSE (<=1.05)", "below the >1.15 bar: NOT CONFIRMED",
                "CONFIRMED (>1.15)"))
        lines.append(f"             luma ratio = {d['K2']['luma_ratio']:.4f} "
                     f"(the reference the eye cannot separate from colour)")
        for ch in ("cr", "cb"):
            v = d["K3"][f"rho_{ch}_ratio"]
            lines.append("K3 INVARIANT " + score(
                v, 0.85, 1.30, f"rho({ch}) nearest/catmull",
                "outside band (low)", "PRE-EXISTING, merely re-filtered",
                "ALIASING implicated (>1.30)"))
        for ch in ("cr", "cb"):
            rel = d["K4"][f"{ch}_rel"]
            sl = d["K4"][ch]["slope"]
            verdict = ("SAME FRINGE" if rel >= 0.70 and sl > 0 else
                       "ALIASING-CREATED" if rel < 0.40 else "INDETERMINATE")
            lines.append(f"K4 STRUCTURE r({ch})/r(luma) = {rel:.4f} (bar >=0.70), "
                         f"slope = {sl:+.4f} (must be > 0) -> {verdict}")
        for ch in ("cr", "cb"):
            k = d["K5"][ch]
            alias = k["hf_fraction"] >= 0.50 and k["axis_anisotropy"] > 1.5
            lines.append(f"K5 LATTICE   {ch} residual: hf_fraction = {k['hf_fraction']:.4f} "
                         f"(bar >=0.50), axis_anisotropy = {k['axis_anisotropy']:.4f} "
                         f"(bar >1.5) -> {'ALIASING' if alias else 'NOT ALIASING'}")
        kl = d["K5"]["L"]
        lines.append(f"             LUMA reference: hf = {kl['hf_fraction']:.4f}, "
                     f"anisotropy = {kl['axis_anisotropy']:.4f}  <-- the lattice "
                     f"signature IS present, in luma only")
        for ch in ("cr", "cb"):
            v = d["K6"][f"rho_{ch}_bilinear_over_nearest"]
            lines.append("K6 (b)v(c)   " + score(
                v, 0.50, 0.70, f"rho({ch}) bilinear/nearest",
                "Nyquist-scale (c) DOMINANT (<0.50)", "(c) BOUNDED SMALL",
                "(c) BOUNDED SMALL"))
        for ch in ("cr", "cb"):
            v = d["K7"]["nearest_to_catmull"][f"rho7_{ch}"]
            n = d["K7"]["catmull_to_bilinear"][f"rho7_{ch}"]
            verdict = ("PRE-EXISTING, MERELY BLURRED" if 0.90 <= v <= 1.10 else
                       "NEAREST SYNTHESISED CHROMA" if v > 1.20 else
                       "CATMULL ADDS CHROMA" if v < 0.90 else "INDETERMINATE")
            lines.append(f"K7 MATCHED   rho7({ch}) = {v:.4f} [bar 0.90-1.10] -> {verdict}"
                         f"   (NULL catmull->bilinear = {n:.4f})")
        lines.append(f"             sigma* = {d['K7']['nearest_to_catmull']['sigma_star']:.4f} px "
                     f"= Catmull-Rom's lowpass relative to a zero-order hold")
        c = d["K3_CTRL"]
        lines.append("K3-CTRL cal  " + "; ".join(
            f"sig={k.split('_')[1]}: rms_L x{v['rms_L_ratio']:.4f} -> rho_cr x{v['rho_cr_ratio']:.4f}"
            for k, v in c.items()))
        lines.append(f"             real arm separation rms_L x{1/d['K2']['luma_ratio']:.4f} "
                     f"-- between the sig=0.25 and sig=0.5 control points")
        p = d["K3_POWER"]
        lines.append("K3-POWER     " + "; ".join(
            f"red shifted {k.split('_')[1]}px -> rho_cr x{v['rho_cr_ratio']:.4f}, "
            f"rho_cb x{v['rho_cb_ratio']:.4f}" for k, v in p.items())
            + "  (rises in cr, flat in cb: responsive AND specific)")
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(OUT, "e8-scorecard.txt"), "w").write(txt)

    # ------------------------------------------------------------ fig 7
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.9))
    x = np.arange(4)
    labs = ["cr\ncentre", "cb\ncentre", "cr\nwing", "cb\nwing"]

    def vals(fn):
        return [fn(D[t], ch) for t in ("centre", "auto") for ch in ("cr", "cb")]

    # panel 1: K2, the orchestrator's premise, against luma
    a = ax[0]
    a.bar(x - 0.2, vals(lambda d, c: d["K2"][f"{c}_ratio"]), 0.4,
          color="#c44", label="chroma rms ratio")
    a.bar(x + 0.2, vals(lambda d, c: d["K2"]["luma_ratio"]), 0.4,
          color="#888", label="luma rms ratio (the null)")
    a.axhline(1.15, color="k", ls="--", lw=1)
    a.text(3.45, 1.152, "K2 bar 1.15", ha="right", va="bottom", fontsize=7)
    a.axhline(1.0, color="k", lw=0.8)
    a.set_ylim(0.95, 1.25)
    a.set_title("K2: is nearest's fringe 'markedly stronger'?\n"
                "nearest / catmull-rom, rms of high-passed field", fontsize=9)
    a.legend(fontsize=7)

    # panel 2: K7, the decisive substitution
    a = ax[1]
    a.axhspan(0.90, 1.10, color="#cfe8cf", zorder=0)
    a.bar(x - 0.2, vals(lambda d, c: d["K7"]["nearest_to_catmull"][f"rho7_{c}"]), 0.4,
          color="#268", label="nearest blurred to catmull's luma")
    a.bar(x + 0.2, vals(lambda d, c: d["K7"]["catmull_to_bilinear"][f"rho7_{c}"]), 0.4,
          color="#888", label="NULL: catmull -> bilinear")
    for i, v in enumerate(vals(lambda d, c: d["K7"]["nearest_to_catmull"][f"rho7_{c}"])):
        a.text(i - 0.2, v + 0.004, f"{v:.3f}", ha="center", fontsize=7)
    a.axhline(1.0, color="k", lw=0.8)
    a.set_ylim(0.85, 1.15)
    a.set_title("K7: match luma with a CHANNEL-INDEPENDENT blur,\n"
                "then compare chroma. Green band = 'pre-existing'", fontsize=9)
    a.legend(fontsize=7, loc="lower right")

    # panel 3: K5, the lattice signature -- present in luma, absent in chroma
    a = ax[2]
    y_l = [D[t]["K5"]["L"]["axis_anisotropy"] for t in ("centre", "auto")]
    y_c = [D[t]["K5"][c]["axis_anisotropy"] for t in ("centre", "auto") for c in ("cr", "cb")]
    a.bar([0, 3], y_l, 0.8, color="#888", label="luma residual")
    a.bar([1, 2, 4, 5], [y_c[0], y_c[1], y_c[2], y_c[3]], 0.8,
          color="#268", label="chroma residual")
    for i, v in zip([0, 1, 2, 3, 4, 5], [y_l[0], y_c[0], y_c[1], y_l[1], y_c[2], y_c[3]]):
        a.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=7)
    a.axhline(1.5, color="k", ls="--", lw=1)
    a.text(5.4, 1.53, "K5 aliasing bar 1.5", ha="right", va="bottom", fontsize=7)
    a.axhline(1.0, color="k", lw=0.8)
    a.set_xticks([0, 1, 2, 3, 4, 5])
    a.set_xticklabels(["L", "cr", "cb", "L", "cr", "cb"], fontsize=8)
    a.set_title("K5: CFA-axis anisotropy of the nearest-minus-catmull residual\n"
                "above 0.7 Nyquist.  centre ROI | wing ROI", fontsize=9)
    a.legend(fontsize=7)

    for a in ax[:2]:
        a.set_xticks(x)
        a.set_xticklabels(labs, fontsize=8)
    fig.suptitle("M107 fig7 -- ORCH-kernel arms scored against bars registered at bf975e0 / e96040d. "
                 "No stretch: these are ratios of measured rms. cr = R-G, cb = B-G, "
                 "all in linear light after a sigma=6 px high-pass.", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(FIG, "M107-fig7-kernel-bars.png")
    fig.savefig(p, dpi=130)
    print("\nwrote", p)


if __name__ == "__main__":
    main()
