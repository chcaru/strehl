"""Verify section 23 of docs/research/M95-kernel.md against the JSON artifacts.

Every claim is RECONSTRUCTED from out/*.json and then required to appear in the
section text. Nothing is copied from the report into this file, so the gate fails
if the report drifts from the artifacts in either direction.

Three defects this gate is deliberately built to avoid, all of them measured
failures earlier in this session:

  * NEVER slice the section with split("## 23.") -- that substring also matches
    "### 23.1", which truncates the section to its opening paragraph and made an
    earlier verifier report BAD on 9 of 10 present claims.
  * NEVER match prose across line breaks with a plain string -- the formatter
    wraps, so quotes are checked against whitespace-collapsed text.
  * NEVER discriminate a short numeric token without an anchor -- "0.50" and
    "1.00" occur by chance. Each numeric check carries a neighbouring literal.

Exit codes, distinguishing TOOL failure from SUBJECT failure (discipline 702):
    0  all checks passed
    1  the report disagrees with the artifacts
    2  the gate could not run (missing artifact, section not found)
"""

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-kernel.md")
OUT = os.path.join(ROOT, "experiments", "M95-resample", "out")

fails, checks = [], 0


def jload(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        print(f"TOOL FAILURE: missing artifact {name}")
        sys.exit(2)
    with io.open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def section(body):
    m = re.search(r"^## 23\. ", body, re.M)
    if not m:
        print("TOOL FAILURE: section 23 heading not found")
        sys.exit(2)
    tail = body[m.start():]
    n = re.search(r"^## 24\. ", tail, re.M)
    return tail[: n.start()] if n else tail


def flat(s):
    """Collapse whitespace, strip blockquote markers, normalise U+2212 to ASCII.

    Three normalisations, each for a measured failure:
      * U+2212 -- the corpus uses a typographic minus throughout and Python's
        f-strings emit an ASCII hyphen, so without this every negative number
        reads BAD. The sign survives, so this is not a change of value.
      * line-leading '>' -- the headline sits in a blockquote, and collapsing
        whitespace alone leaves the markers embedded mid-sentence.
      * whitespace -- prose wraps, so a quoted phrase spanning a line break
        will not match as a plain string.
    """
    s = re.sub(r"(?m)^\s*>\s?", "", s.replace("\u2212", "-"))
    return re.sub(r"\s+", " ", s)


def check(label, needle, hay, anchor=None):
    """`needle` must appear; if `anchor` is given it must appear within 400 chars."""
    global checks
    checks += 1
    if anchor is None:
        ok = needle in hay
    else:
        ok = any(anchor in hay[max(0, i - 400): i + 400]
                 for i in (m.start() for m in re.finditer(re.escape(needle), hay)))
    print(f"  {'ok  ' if ok else 'BAD '} {label}: {needle!r}"
          + (f"  [anchor {anchor!r}]" if anchor else ""))
    if not ok:
        fails.append(label)
    return ok


def main():
    if not os.path.exists(REPORT):
        print("TOOL FAILURE: report not found")
        sys.exit(2)
    with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
        body = fh.read().replace("\r\n", "\n")
    S = section(body)
    F = flat(S)
    print(f"section 23: {len(S)} chars, {S.count(chr(10)) + 1} lines\n")

    x11, x12 = jload("x11_bandsignal.json"), jload("x12_bandsnr.json")
    x13, x14 = jload("x13_focusnull.json"), jload("x14_levelsens.json")
    x15, x16 = jload("x15_defocusptc.json"), jload("x16_robust.json")
    x17 = jload("x17_close.json")

    print("[arm 13 -- x11_bandsignal.json]")
    c = x11["partC"]
    check("detail gain", f"+{c['detail']['gain']:.4f}", F, "detail tiles")
    check("flat gain", f"+{c['flat']['gain']:.4f}", F, "flattest tiles")
    check("dark gain", f"+{c['dark']['gain']:.4f}", F, "dark frame")
    check("R1 flat/detail", f"{c['R1_flat_over_detail']:.4f}", F, "R1_flat/detail")
    check("R1 dark/detail", f"{c['R1_dark_over_detail']:.4f}", F, "R1_dark/detail")
    d = x11["partD"]
    check("shot scale", f"{d['shot_scale']:.1f}", F, "photograph to dark")
    check("S_upper", f"{d['S_upper']:.4f}", F, "passed my registered bar")

    print("\n[arm 13b -- x12_bandsnr.json]")
    check("Q3 negative", f"+{abs(x12['Q3_held_flat_S']):.4f}", F, "held-out flat tiles")
    check("Q2 at 0.50", f"+{x12['Q2']['0.50']['S_hat']:.4f}", F, "plant S = 0.50")
    check("Q2 at 0.90", f"+{x12['Q2']['0.90']['S_hat']:.4f}", F, "plant S = 0.90")
    check("void headline", f"+{x12['S_detail_median']:.4f}", F, "VOID by pre-registration")
    check("n tiles 13b", f"**{x12['n_tiles']}** non-clipping tiles", F)
    check("PTC fit a", f"{x12['fit_a']:.4f}", F, "photon transfer curve")
    check("PTC rho", f"**+{x12['rho']:.4f}**", F, "spearman")

    print("\n[arm 13c -- x13_focusnull.json]")
    check("N1 null", f"+{x13['N1_median']:.4f}", F, "two most-defocused frames")
    check("N2 0.50", f"+{x13['N2']['0.50']['S_hat']:.4f}", F, "N2 power, plant 0.50")
    check("N2 0.90", f"+{x13['N2']['0.90']['S_hat']:.4f}", F, "N2 power, plant 0.90")
    check("N3 distinct", f"**{x13['N3_distinct']}** distinct", F)
    check("S_detail 13c", f"+{x13['S_detail_median']:.4f}", F, "mean +")
    check("13c min", f"{x13['S_detail_min']:+.4f}", F, "min ")
    check("13c max", f"{x13['S_detail_max']:+.4f}", F, "max ")

    print("\n[arm 13d -- x14_levelsens.json]")
    check("ratio median", f"{x14['ratio_median']:.4f}", F, "focus/defocus band power ratio")
    check("level defocus", f"{x14['level_defocus_median']:.1f} DN", F, "defocus ")
    check("level focus", f"{x14['level_focus_median']:.1f} DN", F, "focus ")
    for name, key in (("M-none", "M-none"), ("M-shot", "M-shot"), ("M-ptc", "M-ptc")):
        m = x14["models"][key]
        check(f"{name} levelcorr", f"{m['levelcorr_median']:.4f}", F, name)
        check(f"{name} S", f"**{m['S_median']:+.4f}**", F, name)
        check(f"{name} N1", f"{m['N1_median']:+.4f}", F, name)
    check("bracket lo", f"[{x14['bracket_lo']:+.4f}, {x14['bracket_hi']:+.4f}]", F, "bracket")

    print("\n[arm 13e -- x15_defocusptc.json]")
    check("n flat tiles", f"**{x15['n_flat_tiles']} of {x15['n_grid']}**", F)
    check("level span", f"**{x15['level_span']:.3f}×**", F, "E3 level span")
    check("p hat", f"{x15['p_hat']:.4f}", F, "p = ")
    check("fitted law line, reconstructed whole",
          f"log10(P) = \u2212{abs(x15['c_hat']):.4f} + {x15['p_hat']:.4f} \u00b7 log10(L)",
          re.sub(r"\s+", " ", S))
    check("c hat", f"{x15['c_hat']:.4f}", F, "log10(L)")
    check("p CI", f"[{x15['p_ci'][0]:.4f}, {x15['p_ci'][1]:.4f}]", F, "95% CI")
    check("n fit", f"n = {x15['n_fit']}", F)
    check("E1", f"**{x15['E1_value']:.4f}**", F, "held-out null")
    check("E2 0.50", f"+{x15['E2']['0.50']['S_hat']:.4f}", F, "plant 0.50")
    check("E2 0.90", f"+{x15['E2']['0.90']['S_hat']:.4f}", F, "plant 0.90")
    check("S ci", f"[{x15['S_detail_ci'][0]:+.4f},", F, "propagating")

    print("\n[arm 13f -- x16_robust.json]")
    check("p se", f"se **{x16['p_se']:.5f}**", F)
    check("cal range", f"**{x16['cal_L_min']:.1f}–{x16['cal_L_max']:.1f} DN**", F)
    check("det range", f"**{x16['det_L_min']:.1f}–{x16['det_L_max']:.1f} DN**", F)
    check("F1 fail", "FAIL — headline is EXTRAPOLATED", F)
    check("F2 q", f"`q = {x16['F2_q']:+.5f}`", F)
    check("F2 quad", f"**{x16['F2_S_quad']:+.4f}**", F, "quadratic")
    check("F2 delta", f"**{x16['F2_delta']:.4f}**", F, "bar ≤ 0.02")
    check("F3 p20", f"**{x16['F3_p_at_0.20']:+.4f}**", F, "leaves noise-dominated")
    check("F3 p50", f"**{x16['F3_p_at_0.50']:+.4f}**", F, "real signal")
    check("F3 se20", f"**{x16['F3_se_to_0.20']:.1f} se**", F)
    check("F3 se50", f"**{x16['F3_se_to_0.50']:.1f} se**", F)
    check("F4 null", f"**{x16['F4_E1']:.4f}**", F, "own held-out null")

    print("\n[arm 13g -- x17_close.json]")
    check("n interp", f"{x17['n_interpolated']} of {x17['n_detail_tiles']} detail tiles", F)
    check("S interp", f"**{x17['S_interpolated']:+.4f}**", F, "Dropping the 8 extrapolated")
    check("S movement", f"**{x17['S_extrap_movement']:.4f}**", F, "movement of")
    check("read frac", f"**{x17['read_fraction']:.3e} ({100 * x17['read_fraction']:.4f}%)**", F)
    check("p bound", f"**p ≥ {x17['p_lower_bound_from_read']:.6f}**", F)
    check("drag ratio", f"**{x17['drag_over_read_bound']:.0f}×**", F, "read-noise bound")
    check("S at p0", f"{x17['S_at_p0']:+.4f}", F, "M-none, refuted")
    check("S at p1", f"**{x17['S_at_p1']:+.4f}**", F, "pure shot noise")
    check("signal pct", f"{x17['signal_pct']:.1f}% of the power", F,
          "real captured subject detail")
    check("noise pct", f"{x17['noise_pct']:.1f}%", F, "demosaic's response")

    print("\n[structure and retractions]")
    # Each retraction is pinned to its OWN site. Checking a shared phrase across
    # the whole body let one site satisfy the other's check -- caught by
    # negctl_s23.py's D5, which removed the section 7 retraction and still read
    # green because section 14.4 carried the same words.
    for label, needle in (
        ("retraction pinned at \u00a77",
         "the owner is complaining about~~ **\u2014 RETRACTED, see \u00a723.**"),
        ("retraction pinned at \u00a714.4",
         "number on the table~~ **\u2014 the \"sharpness\" framing is RETRACTED, see \u00a723;"),
        ("falsifier updated", "87% sensor noise on those same 40 tiles"),
        ("headline block", "is real captured subject detail. 87.2%"),
        ("linearity argument registered", "registered in commit `c1bd702`"),
        ("orchestrator section", "### 23.12 For the orchestrator"),
        ("prediction scoring", "### 23.11 Scoring my own predictions"),
        ("artifact table", "### 23.13 Artifacts"),
        ("no crates changed", "No source under `crates/` was changed"),
    ):
        check(label, needle, flat(body) if "\u00a7" in label or "falsifier" in label else F)

    print("\n" + "=" * 70)
    if fails:
        print(f"FAIL -- {len(fails)} of {checks} checks disagree with the artifacts")
        for f in fails:
            print(f"    {f}")
        sys.exit(1)
    print(f"GREEN -- {checks}/{checks} claims in section 23 match the JSON artifacts")
    sys.exit(0)


if __name__ == "__main__":
    main()
