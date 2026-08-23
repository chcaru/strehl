"""S8 -- rule 39 applied to the gate sweep, and the cost of the fix.

Two jobs, both post-hoc over already-measured artifacts.  No new merges.

(a) The strategic finding of S3 -- "the near-selector is the sharpest
    configuration" -- was reported in an earlier draft with an error bar on
    exactly one of its eight cells, and that one cited the wrong row.  Rule 39
    wants the null and its standard error on every cell.  This recomputes all
    eight against the gate-0.50 reference, correcting the sector jackknife by
    the anti-conservatism factor S7 measured by repetition.

    The correction factor is MEASURED (S7, 24 draws).  Its transfer from a
    re-drawn-noise perturbation to a gate-change perturbation is ARGUED, so the
    raw uncorrected sigma is printed alongside and the verdict is checked to be
    the same under both.

(b) Fact 644 says cost is not a design constraint.  The per-ROI scatter that
    killed K1's noise null is a VARIANCE (S7 PR19 disaggregated), so averaging
    independent ROIs is the obvious fix.  This costs that experiment: how many
    512^2 ROIs would be needed for a given threshold, under the 1/sqrt(N)
    assumption which is itself ARGUED and unmeasured (item 2 of section 11).

Reads only:  out/s3_real.json, out/s7_bias_or_variance.json
Writes only: out/s8_gate_significance.json
"""

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "out"))

SIG_MIN = 2.0
THRESHOLDS = (0.10, 0.05, 0.02, 0.01)


def _isnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def jack_factors(s7):
    """Per-cell measured sd/jack for K1 at 1x noise, plus the global median."""
    per = {}
    for cell, rec in s7.items():
        if cell.startswith("_"):
            continue
        r = rec["K1 dsig_1.0"]
        per[cell] = r["sd"] / r["jack"]
    return per, s7["_pr19"]["ratio_med"]


def gate_significance(s3, per, med):
    rows = []
    for cell, rec in s3.items():
        g = rec.get("gate", {})
        if "0.99" not in g:
            continue
        v, se = g["0.99"]["dsig"], g["0.99"]["se"]
        if _isnan(v) or _isnan(se):
            rows.append(dict(cell=cell, dsig=None, se=None, verdict="NaN -- refuses to report"))
            continue
        f = per.get(cell, med)
        src = "own" if cell in per else "median"
        cse = se * f
        sig_raw, sig_cor = abs(v) / se, abs(v) / cse
        sharper = v < 0
        rows.append(dict(
            cell=cell, dsig=v, se=se, factor=f, factor_src=src, corr_se=cse,
            sigma_raw=sig_raw, sigma_corr=sig_cor, sharper=sharper,
            verdict=("near-selector sharper" if sharper and sig_cor >= SIG_MIN
                     else "significant the OTHER way" if (not sharper) and sig_cor >= SIG_MIN
                     else "not significant"),
        ))
    return rows


def roi_cost(s7):
    """How many independent 512^2 ROIs to reach a threshold, if sd falls as 1/sqrt(N).

    ARGUED premise, not measured -- this is the cost of the experiment that
    would test it, not a result.
    """
    out = {}
    for cell, rec in s7.items():
        if cell.startswith("_"):
            continue
        sd = rec["K1 dsig_1.0"]["sd"]
        out[cell] = dict(sd_per_roi=sd,
                         rois={f"{t:.2f}": int(math.ceil((sd / t) ** 2)) for t in THRESHOLDS})
    return out


def main():
    s3 = json.load(open(os.path.join(OUT, "s3_real.json")))
    s7 = json.load(open(os.path.join(OUT, "s7_bias_or_variance.json")))
    per, med = jack_factors(s7)

    print("=" * 78)
    print("S8 (a) -- RULE 39 ON THE GATE SWEEP: every cell gets an error bar.")
    print("=" * 78)
    print("  Contrast is gate 0.99 vs the gate 0.50 reference (dsig == 0 there).")
    print("  Negative dsig => the near-selector configuration is SHARPER.")
    print()
    print("  measured jackknife anti-conservatism, K1 at 1x noise (S7, 24 draws):")
    for c, v in sorted(per.items()):
        print(f"    {c:22s} sd/jack = {v:.3f}")
    print(f"    median over all 18 (cell,level,variant) = {med:.3f}")
    print()

    rows = gate_significance(s3, per, med)
    hdr = (f'  {"cell":22s} {"dsig":>8s} {"jack se":>8s} {"raw s":>7s} '
           f'{"fac":>5s} {"corr se":>8s} {"corr s":>7s}  verdict')
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in rows:
        if r["dsig"] is None:
            print(f'  {r["cell"]:22s} {"NaN":>8s} {"-":>8s} {"-":>7s} {"-":>5s} {"-":>8s} {"-":>7s}  {r["verdict"]}')
            continue
        print(f'  {r["cell"]:22s} {r["dsig"]:+8.3f} {r["se"]:8.4f} {r["sigma_raw"]:7.2f} '
              f'{r["factor"]:5.2f} {r["corr_se"]:8.4f} {r["sigma_corr"]:7.2f}  {r["verdict"]} [{r["factor_src"]}]')

    ok = [r for r in rows if r["dsig"] is not None and r["sharper"] and r["sigma_corr"] >= SIG_MIN]
    other = [r for r in rows if r["dsig"] is not None and not r["sharper"] and r["sigma_corr"] >= SIG_MIN]
    nan = [r for r in rows if r["dsig"] is None]
    raw_ok = [r for r in rows if r["dsig"] is not None and r["sharper"] and r["sigma_raw"] >= SIG_MIN]

    print()
    print(f"  near-selector sharper at >= {SIG_MIN:.0f} sigma (corrected): {len(ok)} of {len(rows)} cells")
    print(f"  significant in the OPPOSITE direction:                  {len(other)}")
    print(f"  refused to report (NaN):                                {len(nan)}")
    if ok:
        print(f'  corrected sigma range over the surviving cells: '
              f'{min(r["sigma_corr"] for r in ok):.2f} .. {max(r["sigma_corr"] for r in ok):.2f}')
        print(f'  raw (uncorrected) sigma, same cells:           '
              f'{min(r["sigma_raw"] for r in ok):.2f} .. {max(r["sigma_raw"] for r in ok):.2f}')
    same = (len(ok) == len(raw_ok))
    print(f"  verdict identical with and without the correction: {same}")
    print("  => the conclusion does NOT rest on the ARGUED transfer of the factor."
          if same else
          "  => WARNING: the conclusion depends on the ARGUED correction factor.")

    print()
    print("=" * 78)
    print("S8 (b) -- COSTING THE FIX.  Fact 644: cost is not a design constraint.")
    print("=" * 78)
    print("  S7 PR19 disaggregated says K1's noise-null failure is VARIANCE on")
    print("  62-frame stacks.  Variance averages down; bias does not.  So the")
    print("  honest expensive proposal is to average independent ROIs.")
    print()
    print("  PREMISE (ARGUED, UNMEASURED -- this is section 11 item 2): the")
    print("  per-ROI scatter falls as 1/sqrt(N) across disjoint 512^2 ROIs.")
    print("  If ROIs share scene structure or fixed-pattern noise it will not.")
    print("  The table below is the COST OF THE TEST, not a result.")
    print()
    cost = roi_cost(s7)
    print(f'  {"cell":22s} {"sd/ROI":>8s} ' + " ".join(f'{"N@" + f"{t:.2f}":>9s}' for t in THRESHOLDS))
    print("  " + "-" * 62)
    for c, rec in sorted(cost.items()):
        print(f'  {c:22s} {rec["sd_per_roi"]:8.4f} '
              + " ".join(f'{rec["rois"][f"{t:.2f}"]:9d}' for t in THRESHOLDS))
    worst = max(cost.values(), key=lambda r: r["sd_per_roi"])
    print()
    print(f'  Worst measured cell needs {worst["rois"]["0.02"]} disjoint 512^2 ROIs for a 0.02 px')
    print("  threshold.  A 6000x4000 frame holds ~91 disjoint 512^2 tiles, so this")
    print("  is one to two frames' worth of area -- affordable under fact 644, and")
    print("  it is the experiment this milestone did not run.")

    res = dict(jack_factor_per_cell=per, jack_factor_median=med,
               sig_min=SIG_MIN, gate=rows,
               n_sharper=len(ok), n_opposite=len(other), n_nan=len(nan),
               verdict_robust_to_correction=same,
               roi_cost=cost, roi_cost_premise="ARGUED: sd falls as 1/sqrt(N); unmeasured")
    with open(os.path.join(OUT, "s8_gate_significance.json"), "w") as f:
        json.dump(res, f, indent=1)
    print()
    print("wrote out/s8_gate_significance.json")


if __name__ == "__main__":
    main()
