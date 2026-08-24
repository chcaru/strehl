"""M69 arm B4 -- pricing the fine field's dispersion where it is actually spent.

Pre-registered in PREREGISTRATION-2.md (c545588) as: "what the measured
dispersion does to bimodality_sigma (through_focus.rs:614) and to the shipped
placebo cut (merge_cmd.rs:1737-1746)."

Reads out/97-b-fine-field.json. Runs no new field measurement -- everything here
is arithmetic on B1-B3's committed numbers plus source reading, so it is DERIVED
and labelled so.

B4.0  read the consumption sites from source rather than from a description.
B4.1  what a per-pixel sigma does to the z-score bimodality_sigma reports.
B4.2  the placebo cut: does calibrating it per stack absorb the dispersion?
B4.3  the N term -- does bimodality_sigma carry the defect M66 proved in
      Gate::tolerance() and M62 confessed in guard G?
"""

import json
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

CORE = m69.ROOT / "crates" / "strehl-core" / "src"
CLI = m69.ROOT / "crates" / "strehl-cli" / "src"


def b40():
    m69.banner("B4.0 -- the consumption sites, read from source")
    tf = (CORE / "through_focus.rs").read_text(encoding="utf-8").splitlines()
    mc = (CLI / "merge_cmd.rs").read_text(encoding="utf-8").splitlines()
    print("  Every line in crates/ that spends FINE_FOCUS_NOISE_SD arithmetically:\n")
    spend = []
    for name, lines in (("through_focus.rs", tf), ("merge_cmd.rs", mc)):
        for i, ln in enumerate(lines, 1):
            if "FINE_FOCUS_NOISE_SD" not in ln:
                continue
            s = ln.strip()
            doc = s.startswith("//") or s.startswith("///") or s.startswith("//!")
            decl = "pub const FINE_FOCUS_NOISE_SD" in s
            arith = (not doc) and (not decl) and ("/" in s or "*" in s)
            kind = "DOC" if doc else ("DECL" if decl else ("ARITH" if arith else "other"))
            if kind in ("ARITH", "DECL"):
                print(f"    {name}:{i:<5} [{kind:>5}] {s[:88]}")
            if kind == "ARITH":
                spend.append(f"{name}:{i}")
    print(f"\n  arithmetic sites: {len(spend)} -> {spend}")
    print("\n  And the cut that is compared against it:")
    for i, ln in enumerate(tf, 1):
        if "bimodality_sigma_cut" in ln and "///" not in ln:
            print(f"    through_focus.rs:{i:<5} {ln.strip()[:88]}")
    return spend


def b41(d):
    m69.banner("B4.1 -- what the dispersion does to the z-score bimodality_sigma reports")
    print("  bimodality_sigma(i) = (far_val[i] - floor[i]) / (sqrt(2) * FINE_FOCUS_NOISE_SD).")
    print("  The numerator is a per-pixel difference of fine responses; the denominator")
    print("  is a global constant. If the true per-pixel SD is rho(p) * the constant,")
    print("  the reported z is inflated by exactly 1/rho(p).\n")
    b3 = d["b3"]
    print(f"  {'stack':<16} {'rho_obs':>8} {'p05':>7} {'p95':>7} | "
          f"{'z inflation at p05':>19} {'at p95':>9} {'ratio':>7}")
    print("  " + "-" * 78)
    rows = {}
    for st, v in b3.items():
        f = v["fine"]
        lo, hi = 1.0 / f["p95"], 1.0 / f["p05"]
        print(f"  {st:<16} {f['rho_obs']:>8.4f} {f['p05']:>7.4f} {f['p95']:>7.4f} | "
              f"{hi:>19.3f} {lo:>9.3f} {hi / lo:>7.3f}x")
        rows[st] = {"z_inflation_p05": hi, "z_inflation_p95": lo,
                    "spread": hi / lo}
    worst = max(rows.values(), key=lambda r: r["spread"])
    best = min(rows.values(), key=lambda r: r["spread"])
    print(f"\n  Within a single stack the same reported z means between {1 / max(v['fine']['p95'] for v in b3.values()):.3f}")
    print(f"  and {1 / min(v['fine']['p05'] for v in b3.values()):.3f} true sigma depending only on where the pixel is.")
    print(f"  Worst within-stack spread {worst['spread']:.3f}x, best {best['spread']:.3f}x.")
    return rows


def b42(d):
    m69.banner("B4.2 -- does the per-stack placebo cut absorb it?")
    print("  merge_cmd.rs sets bimodal_cut = p99 of the PLACEBO population, one scalar")
    print("  for the whole image, and flags pixels with b >= cut. The placebo is a")
    print("  frame-permutation of the SAME pixels, so it carries the same per-pixel")
    print("  rho(p). Two questions, and they have different answers.\n")
    b3 = d["b3"]
    print("  (a) Does it absorb the STACK-level dispersion?  YES, by construction:")
    v = [x["fine"]["rho_obs"] for x in b3.values()]
    print(f"      corpus rho_obs spans {max(v) / min(v):.3f}x across stacks, and a cut")
    print("      re-derived per stack from that stack's own placebo sees the stack's")
    print("      own scale. The stack-level limb of this defect is already handled.\n")
    print("  (b) Does it absorb the WITHIN-image dispersion?  NO. The cut is a single")
    print("      scalar over pixels. Under a global p99 cut the per-pixel false-positive")
    print("      rate is not 1% everywhere; it is concentrated in the high-rho tail.\n")
    print(f"  {'stack':<16} {'p95/p05':>8}  {'implied FPR ratio, p95 pixel vs p05 pixel':>44}")
    print("  " + "-" * 72)
    rows = {}
    for st, x in b3.items():
        f = x["fine"]
        w = f["within_stack"]
        # Gaussian-tail illustration only: a cut placed at q sigma of the median
        # pixel sits at q*(rho_med/rho_p) sigma of a pixel with scale rho_p.
        q = 2.326  # the 99th percentile of a standard normal
        med = 0.5 * (f["p05"] + f["p95"])
        from math import erfc, sqrt
        tail = lambda t: 0.5 * erfc(t / sqrt(2.0))
        r_hi = tail(q * med / f["p95"]) / tail(q)
        r_lo = tail(q * med / f["p05"]) / tail(q)
        print(f"  {st:<16} {w:>8.3f}  {r_hi:>20.1f}x  vs {r_lo:>15.3f}x")
        rows[st] = {"within_stack": w, "fpr_ratio_hi": r_hi, "fpr_ratio_lo": r_lo}
    print("\n  ILLUSTRATION ONLY, and labelled so: bimodality_sigma's null is a")
    print("  multiplicity tail over n-3 frames, not a Gaussian tail (through_focus.rs:731")
    print("  says so, and M63 section 2.3 registered the same point and refused to quote")
    print("  a sigma-count for exactly this reason). The Gaussian numbers above are a")
    print("  scale illustration of a real effect, NOT a false-positive rate.")
    return rows


def b43():
    m69.banner("B4.3 -- the N term: does this site carry M66's defect?")
    tf = (CORE / "through_focus.rs").read_text(encoding="utf-8")
    m = re.search(
        r"/// `bimodality_sigma_cut` is in units.*?Calibrate it against the permutation placebo\n"
        r"\s*/// \(\[`new_permuted`\]\(Self::new_permuted\)\) on the stack in hand\.",
        tf, re.S)
    print("  through_focus.rs, the doc comment on `confidence`, quoted verbatim:\n")
    if m:
        for ln in m.group(0).splitlines():
            print("    " + ln.strip())
    else:
        print("    !! pattern not found -- report this rather than paraphrasing")
    print("\n  Read against M66's finding and M62's confession:")
    print("    M66  : Gate::tolerance() = T * sqrt(2) * FOCUS_NOISE_SD  -- NO N term,")
    print("           against max_j X_j whose expectation grows with N.")
    print("    M62  : guard G is a fixed 0.95 line against a statistic whose null")
    print("           drifts with N, with nothing in its statement mentioning N.")
    print("    HERE : the constant is equally N-free, but the THRESHOLD is not a")
    print("           constant at all. The crate refuses to ship a default, names the")
    print("           order statistic explicitly, and mandates per-stack calibration")
    print("           against a permutation placebo.")
    return bool(m)


def main():
    m69.banner("M69 arm B4 -- pricing the fine field's dispersion  (DERIVED throughout)")
    d = json.loads((m69.OUT / "97-b-fine-field.json").read_text(encoding="utf-8"))
    print(f"  E1 verdict carried in from B2: {d['e1_verdict']}"
          f"   D_fine+bare = {d['dispersion']['fine+bare']['D']:.3f}x")
    spend = b40()
    r41 = b41(d)
    r42 = b42(d)
    ok = b43()
    (m69.OUT / "98-b4.json").write_text(
        json.dumps({"arith_sites": spend, "z_inflation": r41, "fpr": r42,
                    "n_doc_found": ok}, indent=2),
        encoding="utf-8",
    )
    print("\n  wrote out/98-b4.json")


if __name__ == "__main__":
    main()
