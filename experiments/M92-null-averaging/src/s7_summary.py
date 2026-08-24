"""M92 S7 -- the summary table the report is built from.

Reads out/s2_null_averaging.json and out/s3_dark_corr.json and prints one row
per (stack, arm), plus the pre-registered bars evaluated arm by arm.  It makes
no measurement of its own.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402

E = 0.1754


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    s2 = json.load(open(os.path.join(M92.OUT, "s2_null_averaging.json")))
    p3 = os.path.join(M92.OUT, "s3_dark_corr.json")
    s3 = json.load(open(p3)) if os.path.exists(p3) else {}

    log("=" * 118)
    log("M92 S7 -- master table.  E = 0.1754 px (M82's largest finite price).")
    log("=" * 118)
    log(f"  {'stack':>15} {'arm':>34} {'Null(1)':>8} {'Null(4)':>8} {'Null(24)':>9}"
        f" {'alpha':>7} {'alpha 95% CI':>16} {'rbar':>9} {'floor':>7} {'Nreq':>5}"
        f" {'NaN%':>6}")
    ship = {}
    for stack, sv in s2.items():
        for arm, a in sv["arms"].items():
            if "ladder" not in a or "alpha_ci" not in a:
                continue
            lad = a["ladder"]
            n1 = lad["1"]["rms"]
            n4 = lad.get("4", {}).get("rms", np.nan)
            n24 = lad.get("24", {}).get("rms", np.nan)
            ci = a["alpha_ci"]
            log(f"  {stack:>15} {arm:>34} {n1:8.5f} {n4:8.5f} {n24:9.5f}"
                f" {a['alpha']:7.4f} [{ci[0]:6.3f},{ci[1]:6.3f}]"
                f" {a['corr']['rbar']:+9.5f} {a['implied_floor']:7.5f}"
                f" {str(a['n_required']):>5}"
                f" {100*a['nan_roi'][1]:6.1f}")
            if arm.startswith("A1 ") and "x2" in arm:
                ship[stack] = a

    log("")
    log("=" * 118)
    log("  PRE-REGISTERED BARS, primary estimator, primary level (x2), disjoint grid")
    log("=" * 118)
    ok_a = ok_4 = ok_24 = True
    for stack, a in ship.items():
        lad = a["ladder"]
        n4 = lad["4"]["rms"]
        n24 = lad["24"]["rms"]
        b1 = a["alpha"] >= 0.40
        b2 = n4 < E
        b3 = n24 >= E
        b4 = a["alpha"] < 0.15
        ok_a &= b1
        ok_4 &= b2
        ok_24 &= not (b3 or b4)
        log(f"  {stack:>15}  alpha {a['alpha']:.4f} >= 0.40 ? {str(b1):>5}"
            f" | Null(4) {n4:.5f} < {E} ? {str(b2):>5}"
            f" | Null(24) {n24:.5f} >= {E} (fatal) ? {str(b3):>5}"
            f" | alpha < 0.15 (fatal) ? {str(b4):>5}")
    log(f"\n  SHIP requires all three columns green on every stack:"
        f" alpha {ok_a}, Null(4) {ok_4}, no fatal {ok_24}")

    log("")
    log("  PLACEBO (PL / PLsym) recovery ratios at N = 24, bar [0.85, 1.15]")
    for stack, sv in s2.items():
        for arm, a in sv["arms"].items():
            if not arm.startswith(("PL ", "PLsym ")):
                continue
            r = a["ratio_at_24"]
            det = a["per_N"]["24"]["mean"] / a["per_N"]["24"]["null"]
            f1 = a["per_N"]["1"]["frac_over"]
            f24 = a["per_N"]["24"]["frac_over"]
            log(f"    {stack:>15} {arm:>14}  ratio {r:6.4f}"
                f" {'PASS' if 0.85 <= r <= 1.15 else 'FAIL'}"
                f"   noiseless {str(a['noiseless_ratio'])[:6]:>6}"
                f"   |mean|/Null(24) {abs(det):6.2f}x"
                f"   frac>Null: N=1 {100*f1:5.1f}%  N=24 {100*f24:5.1f}%")

    log("")
    log("  NEGATIVE CONTROLS")
    for stack, sv in s2.items():
        nc2 = sv["arms"].get("NC2")
        if nc2:
            lad = nc2["ladder"]
            log(f"    {stack:>15}  NC2 alpha {nc2['alpha']:+.6f}"
                f"  Null(1) {lad['1']['rms']:.5f} -> Null(24)"
                f" {lad['24']['rms']:.5f}   red = {nc2['red']}")
        nc1 = sv["arms"].get("NC1 COMMON-MODE injection x2")
        a1 = ship.get(stack)
        if nc1 and a1:
            log(f"    {stack:>15}  NC1 alpha {nc1['alpha']:.4f} (A1 "
                f"{a1['alpha']:.4f})   rbar {nc1['corr']['rbar']:+.5f} (A1 "
                f"{a1['corr']['rbar']:+.5f})   floor {nc1['implied_floor']:.5f}"
                f" px   red(alpha<0.40) = {nc1['alpha'] < 0.40}"
                f"  red(rbar>=0.10) = {nc1['corr']['rbar'] >= 0.10}")

    if s3:
        log("")
        log("=" * 118)
        log("  S3 -- REAL SENSOR NOISE and the OVERLAP POSITIVE CONTROL")
        log("=" * 118)
        log(f"  {'stack':>15} {'arm':>22} {'Null(1)':>8} {'alpha':>7}"
            f" {'alpha 95% CI':>16} {'rbar':>9} {'floor':>8} {'NaN%':>6}")
        for stack, sv in s3.items():
            for arm, a in sv["arms"].items():
                if "ladder" not in a:
                    continue
                ci = a["alpha_ci"]
                log(f"  {stack:>15} {arm:>22} {a['ladder']['1']['rms']:8.5f}"
                    f" {a['alpha']:7.4f} [{ci[0]:6.3f},{ci[1]:6.3f}]"
                    f" {a['corr']['rbar']:+9.5f} {a['implied_floor']:8.5f}"
                    f" {100*a['nan_roi'][1]:6.1f}")
        log("")
        for stack, sv in s3.items():
            for arm, a in sv["arms"].items():
                if arm.startswith("OV control"):
                    log(f"    {stack:>15} {arm:>26}: alpha "
                        f"{a['alpha_disjoint']:.4f} -> {a['alpha_overlap']:.4f},"
                        f" rbar {a['rbar_disjoint']:+.4f} ->"
                        f" {a['rbar_overlap']:+.4f}   "
                        f"{'PASS' if a['passed'] else 'FAIL'}")

    with open(os.path.join(M92.OUT, "s7_summary.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\nwrote out/s7_summary.log")


if __name__ == "__main__":
    main()
