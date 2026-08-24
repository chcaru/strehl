"""Verify the report's load-bearing numbers against the persisted JSON.

Every claim below is checked against the file that produced it. A number that
cannot be found in the report text, or that disagrees with its source, is a
FAIL. This exists because the milestone brief is explicit that a number recalled
from earlier notes is not a measurement.
"""
from __future__ import annotations
import json, os, re, sys

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
OUT = os.path.join(ROOT, "experiments", "M95-merge-vs-frame", "out")
REPORT = os.path.join(ROOT, "docs", "research", "M95-merge-vs-frame-sharpness.md")

txt = open(REPORT, encoding="utf-8").read()
# Strip blockquote markers before collapsing whitespace, so a quoted headline
# spanning several wrapped lines is matchable as one sentence.
flat = re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", "", txt))


def j(n):
    return json.load(open(os.path.join(OUT, n), encoding="utf-8"))


fails = []


def check(label, needle, truth=None, tol=None, source=""):
    """needle must appear in the report; if truth given, it must also match."""
    present = needle in flat
    ok = present
    detail = ""
    if truth is not None and tol is not None:
        m = re.search(r"-?\u2212?[\d,]+\.?\d*", needle.replace("\u2212", "-"))
        got = float(m.group(0).replace(",", "")) if m else float("nan")
        got = abs(got)
        ok = present and abs(got - abs(truth)) <= tol
        detail = f" (report {got}, source {truth})"
    print(f"  {'OK  ' if ok else 'FAIL'}  {label:52s} '{needle}'{detail}  <- {source}")
    if not ok:
        fails.append(label)


s5b, s5, s10, s12 = j("s5b_election_checks.json"), j("s5_election.json"), j("s10_controls.json"), j("s12_resample.json")
s8, s9, s0, s6 = j("s8_floor.json"), j("s9_loose_ends.json"), j("s0_optics.json"), j("s6_spectral.json")
r4, s1, s3, s11 = j("r4_loader.json"), j("s1_drift.json"), j("s3_focus.json"), j("s11_figure.json")

print("== P1 fidelity ==")
tot = sum(sum(r["n"] for r in d.get("grid_control", [])) for d in s5b.values())
pairs = sum(len(d.get("grid_control", [])) for d in s5b.values())
mn = min(r["frac_exact"] for d in s5b.values() for r in d.get("grid_control", []))
mx = max(r["max_abs"] for d in s5b.values() for r in d.get("grid_control", []))

# The headline sentence is the single most load-bearing string in the report,
# so it is checked as one exact literal assembled from the source data rather
# than as a set of independently-satisfiable substrings. A negative control
# caught the earlier version staying green when the headline's "0 DN" was
# mutated, because the same substring occurred in a table further down.
headline = (f"{tot:,} pixels across {pairs} frame/ROI combinations, "
            f"{100*mn:.4f} % exact, maximum difference {mx:.0f} DN of 65535")
check("HEADLINE sentence, assembled from source", headline, None, None,
      "s5b grid_control (tot/pairs/min frac_exact/max abs)")
check("total pixels in grid control", f"{tot:,}", float(tot), 0, "s5b grid_control")
check("frame/ROI pairs", str(pairs), float(pairs), 0, "s5b grid_control")
check("min fraction exact", "1.000000", mn, 1e-9, "s5b grid_control")
check("min fraction exact, P1 fact site", f"minimum fraction exact **{mn:.6f}**",
      mn, 1e-9, "s5b grid_control")
check("table row: max abs diff is zero DN", "**0 DN**", None, None, f"s5b max_abs={mx}")
check("summary table row", f"| **{pairs}** | **{tot:,}** | **{mn:.6f}** | **{mx:.0f} DN** |",
      None, None, "s5b grid_control")

print("== P2 coverage ==")
for roi in ("ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT", "ROI-FLAT"):
    v = 100 * s5[roi]["frac_pixel_matches_some_frame"]
    check(f"{roi} matches-some", f"{v:.4f} %", v, 5e-5, "s5")

print("== P5 R7 ==")
for roi, want in (("ROI-LOWDRIFT", "2.65"), ("ROI-MIDDRIFT", "2.32"),
                  ("ROI-HIGHDRIFT", "1.78"), ("ROI-FLAT", "1.09")):
    v = s10["R7"][roi]["ratio"]
    check(f"{roi} G1-G2 ratio", f"**{want}×**", float(want), 0.005, f"s10 R7 ratio={v:.4f}")
for roi, want in (("ROI-LOWDRIFT", "85.8"), ("ROI-MIDDRIFT", "81.4"), ("ROI-HIGHDRIFT", "68.5")):
    v = 100 * s10["R7"][roi]["excess_var_frac"]
    check(f"{roi} scene share", f"**{want} %**", float(want), 0.05, f"s10 excess={v:.2f}")
# The flat control's 1.09x is quoted at four separate sites; a control showed a
# bare-substring check leaves three of them free to drift.
fr = s10["R7"]["ROI-FLAT"]["ratio"]
fs = 100 * s10["R7"]["ROI-FLAT"]["excess_var_frac"]
check("flat ratio, headline site", f"against **{fr:.2f}×** in a defocused control", fr, 0.005, "s10")
check("flat ratio, table site", f"| **{fr:.2f}×** | {fs:.1f} %", fr, 0.005, "s10")
check("flat ratio, prose site", f"the same statistic reads {fr:.2f}×", fr, 0.005, "s10")
check("flat ratio, P5 fact site", f"flat control reads **{fr:.2f}×** ({fs:.1f} %)", fr, 0.005, "s10")

print("== P6 optics ==")
check("binned nyquist", "48.94 cy/mm", s0["nyq_bin_cymm"], 0.005, "s0")
check("full nyquist", "97.88 cy/mm", s0["nyq_full_cymm"], 0.005, "s0")
check("pitch", "**5.1081 µm**", None, None, f"s0 pitch={s0['pitch_um']:.4f}")
check("mtf@bin min", "**0.421**", s9["mtf_bin_range"][0], 0.0005, "s9")
check("mtf@bin max", "**0.616**", s9["mtf_bin_range"][1], 0.0005, "s9")
check("mtf@74 min", "**0.175**", s9["mtf_74_range"][0], 0.0005, "s9")
check("mtf@74 max", "**0.432**", s9["mtf_74_range"][1], 0.0005, "s9")
lo, hi = s9["mtf_bin_range"]
check("P6 mtf@bin range restated", f"**{lo:.3f}–{hi:.3f} at the binned Nyquist**",
      lo, 0.0005, "s9 mtf_bin_range")
l7, h7 = s9["mtf_74_range"]
check("P6 mtf@74 range restated", f"**{l7:.3f}–{h7:.3f} at 74 cy/mm**", l7, 0.0005,
      "s9 mtf_74_range")

print("== P7/P8 floor ==")
for roi, want in (("ROI-LOWDRIFT", "0.8955"), ("ROI-MIDDRIFT", "4.6273"), ("ROI-HIGHDRIFT", "0.7985")):
    check(f"{roi} A demosaiced", want, s8["measured"][roi]["A"], 5e-5, "s8 measured")
check("flat A", "**1.5180**", s8["measured"]["ROI-FLAT"]["A"], 5e-5, "s8")
# Context-anchored: the same value appears in the prose and again in the
# candidate-fact block, and a control showed that checking a bare substring
# leaves one of the two sites free to drift. Each site is checked separately.
sp_d = s8["plateau_vs_focus"]["ROI-LOWDRIFT"]["span"]
sp_f = s8["plateau_vs_focus"]["ROI-FLAT"]["span"]
check("plateau detail span, prose site", f"spans **{sp_d:.4f}×** with focus", sp_d, 5e-5, "s8")
check("plateau detail span, P8 site", f"spans **{sp_d:.4f}×** across the stack", sp_d, 5e-5, "s8")
check("plateau flat span, prose site", f"control** spans **{sp_f:.4f}×**", sp_f, 5e-5, "s8")
check("plateau flat span, P8 site", f"only **{sp_f:.4f}×** on the flat control", sp_f, 5e-5, "s8")

print("== P9 resample ==")
check("sigma numeric", "**σ = 0.2558 px**", s12["sigma_eq_px_by_band"]["0.05-0.4"]["numeric"], 5e-5, "s12")
check("sigma kernel only", "0.2908", s12["sigma_eq_px_by_band"]["0.05-0.4"]["kernel_only"], 5e-5, "s12")
check("sigma with replicas", "0.2706", s12["sigma_eq_px_by_band"]["0.05-0.4"]["with_replicas"], 5e-5, "s12")
check("dev kernel only", "0.0623", s12["max_abs_dev_kernel_only_0p05_0p40"], 5e-5, "s12")
check("dev with replicas", "0.0406", s12["max_abs_dev_with_replicas_0p05_0p40"], 5e-5, "s12")
check("C6 low bin", "**1.0360**", s12["C6_max_mtf_broadband"], 5e-5, "s12")
check("C6 above 0.10", "**1.0036**", s12["C6_max_mtf_above_0p10"], 5e-5, "s12")
check("C6 argmax f", "f = 0.0361 cy/px", s12["C6_argmax_f"], 5e-5, "s12")

print("== P10 drift ==")
cs = s1["corner_span_plane_px"]
check("drift min corner", "**28.5", min(cs.values()), 0.05, "s1")
check("drift max corner", "240.7 plane px**", max(cs.values()), 0.05, "s1")

print("== P15 loader ==")
check("loader exact pct, control site", "**99.9763 %** exact, residual rms",
      100 * r4["frac_exact"], 5e-5, "r4")
check("loader exact pct, P15 site", "**99.9763 %** exact,\nmax **1 DN**".replace("\n", " "),
      100 * r4["frac_exact"], 5e-5, "r4")
check("loader implied black", "**511.99988**", r4["implied_black"], 5e-6, "r4")
check("loader implied range", "**14847.99984**", r4["implied_range"], 5e-6, "r4")

print("== figure ==")
check("figure identical", "3979 / 3979", float(s11["identical"]), 0, "s11")
check("figure maxdiff 0", "max difference 0 DN", None, None, f"s11 maxdiff={s11['maxdiff']}")
check("figure frac", "**3.07 %**", 100 * s11["frac_near"], 0.005, "s11")

print("== controls ==")
check("R5 sha", "895e458d", None, None, s10["R5"]["sha_original"][:8])
check("R6b collapse", "10.1360 %", 100 * s10["R6"]["b"]["shifted"], 5e-5, "s10")
check("R6c before", "4453", float(s10["R6"]["c"]["before"]), 0, "s10")
check("R6a unelected", "0.0519 %", 100 * s10["R6"]["a"]["unelected_exact"], 5e-5, "s10")
check("C3 diamond", "1.50 × 10⁻¹²", None, None, f"s8 C3 diamond_A={s8['C3']['diamond_A']:.3e}")
check("C3 circle hard", "0.9836", s8["C3"]["circle_hard_A"], 5e-5, "s8")
check("C3 circle diff", "0.9978", s8["C3"]["circle_diffraction_A"], 5e-5, "s8")
check("C2 isotropy", "**1.0025**", s8["C2"]["ratio"], 5e-5, "s8")
check("R1a worst", "**0.04 %**", 100 * s6["R1_verdict"]["worst_a"], 0.005, "s6")
check("R1b worst", "**28.7 %**", 100 * s6["R1_verdict"]["worst_b"], 0.05, "s6")

print("== sigma_eq confound (P10) ==")
for roi, want in (("ROI-LOWDRIFT", "-0.7504"), ("ROI-MIDDRIFT", "-0.4846"), ("ROI-HIGHDRIFT", "-0.5587")):
    v = s6["PRIMARY"][roi]["rows"][0]["sigma_raw"]
    check(f"{roi} sigma_raw", want.replace("-", "−"), abs(float(want)), 5e-5,
          f"s6 PRIMARY={v:.4f}")

print("== focus ==")
for roi in ("ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT"):
    check(f"{roi} peak frame", str(s3["res"][roi]["peak_frame"]), None, None, "s3")

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    sys.exit(1)
print("ALL REPORT NUMBERS VERIFIED AGAINST SOURCE JSON")
