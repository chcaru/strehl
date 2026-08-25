"""M126-default-audit — the derived quantities the predictions are judged on.

Spearman correlations, additivity residuals and the alignment contrast, computed
from scores.json so that no number in the report is arrived at by hand.

    python experiments\\M126-default-audit\\derived.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(r"C:\dev\strehl-out\M126")
SUBJECTS = ["bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl"]
DRIFT = {
    "bee-3-cpl": 1.629, "lead-1-cpl": 2.026, "leaf-2-cpl": 5.315,
    "coffee-bean": 12.065, "tweezers-cpl": 13.765,
}
# (dropped-gate arm, the same gate's alone arm)
DROPS = [("D1-noca", "G1-ca"), ("D2-norobust", "G2-robust"),
         ("D3-nosmooth", "G3-smooth"), ("D4-nosoftgate", "G4-softgate"),
         ("D5-nophotometric", "G5-photometric")]


def main() -> int:
    d = json.loads((ROOT / "scores.json").read_text())
    ms = json.loads((ROOT / "masksource.json").read_text())
    A = lambda s, a: d[s]["aligned"]["arms"][a]  # noqa: E731

    drift = [DRIFT[s] for s in SUBJECTS]

    print("## X8 -- does SMOOTH's effect rank-order with drift?\n")
    dq = [A(s, "G3-smooth")["Q"] - A(s, "A0-default")["Q"] for s in SUBJECTS]
    r = spearmanr(drift, dq)
    print(f"dQ(G3) by drift: " + ", ".join(f"{s}={v:+.5f}" for s, v in zip(SUBJECTS, dq)))
    print(f"\nSpearman rho = {r.statistic:+.4f}, p = {r.pvalue:.4f}, n = 5\n")

    print("## X13 -- additivity: is (ALL - drop_i) the same as (gate_i alone - A0)?\n")
    print("| gate | subject | in company (dQ) | alone (dQ) | residual | "
          "in company (dD) | alone (dD) | residual |")
    print("|---|---|---|---|---|---|---|---|")
    worst = 0.0
    for drop, alone in DROPS:
        for s in SUBJECTS:
            ref, all_on = A(s, "A0-default"), A(s, "ALL-on")
            dq_c = all_on["Q"] - A(s, drop)["Q"]
            dq_a = A(s, alone)["Q"] - ref["Q"]
            dd_c = all_on["D"] - A(s, drop)["D"]
            dd_a = A(s, alone)["D"] - ref["D"]
            worst = max(worst, abs(dq_c - dq_a), abs(dd_c - dd_a))
            print(f"| `{alone}` | `{s}` | {dq_c:+.5f} | {dq_a:+.5f} | "
                  f"{dq_c - dq_a:+.5f} | {dd_c:+.5f} | {dd_a:+.5f} | {dd_c - dd_a:+.5f} |")
    print(f"\nWorst absolute additivity residual across all gates and subjects: "
          f"**{worst:.5f} dex** (X13 registered `< 0.005`).\n")

    print("## X15 / X16 -- the alignment contrast, and why it is not clean\n")
    print("| subject | drift | Q(A0), masks M0 | Q(B1u), masks M0u | difference |")
    print("|---|---|---|---|---|")
    ali = []
    for s in SUBJECTS:
        qa = A(s, "A0-default")["Q"]
        qb = d[s]["unaligned"]["arms"]["B1u-noalign"]["Q"]
        ali.append(qa - qb)
        print(f"| `{s}` | {DRIFT[s]:.3f} | {qa:.5f} | {qb:.5f} | {qa - qb:+.5f} |")
    r2 = spearmanr(drift, [-x for x in ali])
    print(f"\nSpearman rho(drift, cost of turning ALIGN off) = {r2.statistic:+.4f}, "
          f"p = {r2.pvalue:.4f}, n = 5")
    print("\nThe two columns are scored against DIFFERENT mask arms, because no "
          "mask arm is registered to both the aligned and the unaligned grid. "
          "masksource.py measures that this single choice swings the same "
          "contrast by up to 0.666 dex -- larger than every difference in this "
          "table. The table is therefore reported and NOT used to issue a verdict.\n")

    print("## X18 -- does the merge-vs-single contrast fall as drift rises?\n")
    for tag in ("M0u", "B0"):
        vals = [ms[s][tag]["dQ"] for s in SUBJECTS]
        r3 = spearmanr(drift, vals)
        print(f"- masks from `{tag}`: rho = {r3.statistic:+.4f}, p = {r3.pvalue:.4f}, "
              f"values " + ", ".join(f"{v:+.4f}" for v in vals))

    print("\n## X19 -- pooled dQ positive while a minority of detail tiles improve\n")
    print("| arm | subject | pooled dQ | detail tiles improved |")
    print("|---|---|---|---|")
    n = 0
    for arm in ["G4-softgate", "G5-photometric", "ALL-on", "D5-nophotometric",
                "D3-nosmooth", "D2-norobust", "D1-noca"]:
        for s in SUBJECTS:
            a, ref = A(s, arm), A(s, "A0-default")
            dq_ = a["Q"] - ref["Q"]
            imp = a["tiles_detail"]["improved_frac"]
            if dq_ > 0 and imp < 0.5:
                n += 1
                print(f"| `{arm}` | `{s}` | {dq_:+.5f} | {100.0 * imp:.1f}% |")
    print(f"\n{n} arm-subject cells show a positive pooled dQ carried by a "
          f"minority of detail tiles.\n")

    print("## Per-tile dispersion, so the pooled numbers are not read as uniform\n")
    print("| arm | subject | dD_tile median | dD_tile sd | p10 | p90 | improved |")
    print("|---|---|---|---|---|---|---|")
    for arm in ["G3-smooth", "G4-softgate", "G5-photometric", "G6-halo",
                "ALL-on", "PC2-nearest-solved"]:
        for s in SUBJECTS:
            t = A(s, arm)["tiles_detail"]
            print(f"| `{arm}` | `{s}` | {t['median']:+.5f} | {t['sd']:.5f} | "
                  f"{t['p10']:+.5f} | {t['p90']:+.5f} | {100.0 * t['improved_frac']:.1f}% |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
