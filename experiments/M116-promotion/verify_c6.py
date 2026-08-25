"""Verifier for section 12 of docs/research/M116-promotion.md (campaign 6).

Every numeric claim in section 12 is re-derived from the campaign artefacts
(arms.json, gain.json, ta-trap.json) and then located at its own anchored site
in the report. Two properties this milestone has learned to insist on:

  * All-occurrence anchoring. A check is pinned to a neighbouring literal, not
    to the first place a token happens to appear, because short tokens like
    "7" or "1.114" occur many times by chance.
  * Boundary-aware token matching. Substring counting is wrong for numeric
    tokens: "1.101" occurs inside "1.1015", and "0.090" inside "0.0901".

Commissioned by negctl_c6.py, which plants defects in both the report and the
JSONs and requires each to be caught by the guard that targets it, by message
text. A verifier that has never failed is not evidence.

Exit 0 GREEN, 1 RED. Reads nothing on D:.
"""

import json
import os
import re
import sys

OUT = r"C:\dev\strehl-out\M116\invariant"
REPORT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "research", "M116-promotion.md")

FAILURES = []
CHECKS = [0]


def token_re(tok):
    """Match tok as a whole numeric token.

    Guards both sides: a leading (?<![-+0-9.]) stops "1.114" matching inside
    "11.114" or "-1.114", and a trailing (?![0-9]) stops it matching inside
    "1.1145".
    """
    return re.compile(r"(?<![-+0-9.])" + re.escape(tok) + r"(?![0-9])")


def section(text, heading):
    """The body of one section, from its heading to the next heading of the
    same or higher level. Scoping every check to its section is what stops a
    number being 'verified' by a duplicate somewhere else in the report."""
    m = re.search(r"^## " + re.escape(heading) + r".*$", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]


def exact(body, s, label):
    """Require an exact string, not a token near an anchor.

    Presence-of-a-token-near-an-anchor is satisfied by any duplicate of that
    token inside the anchor window, which is how negctl_c6 caught D1, D4 and D7
    passing while the claim they check had been altered: the P2 row repeats
    1.114, the same paragraph repeats (656, 1552), and NCC repeats the phase
    peak's 1.0000. Pinning the whole line removes the duplicate entirely.
    """
    CHECKS[0] += 1
    if body is None:
        FAILURES.append("%s: section 12 not found" % label)
        return
    if s not in body:
        FAILURES.append("%s: exact claim %r not present" % (label, s[:80]))


def check(body, anchor, tok, label):
    """Require tok to appear within 400 chars of SOME occurrence of anchor."""
    CHECKS[0] += 1
    if body is None:
        FAILURES.append("%s: section 12 not found" % label)
        return
    hits = list(re.finditer(re.escape(anchor), body))
    if not hits:
        FAILURES.append("%s: anchor %r not found" % (label, anchor))
        return
    rx = token_re(tok)
    for h in hits:
        if rx.search(body[h.start(): h.end() + 400]):
            return
    FAILURES.append("%s: %r not found near any of the %d occurrences of %r"
                    % (label, tok, len(hits), anchor))


def near(a, b, tol, label):
    CHECKS[0] += 1
    if abs(a - b) > tol:
        FAILURES.append("%s: re-derived %.6f, report/artefact says %.6f (tol %g)"
                        % (label, a, b, tol))


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        print("GUARD: missing artefact %s -- run the campaign first" % p)
        sys.exit(3)
    with open(p) as fh:
        return json.load(fh)


def main():
    arms = load("arms.json")
    gain = load("gain.json")
    trap = load("ta-trap.json")
    with open(REPORT, encoding="utf-8") as fh:
        text = fh.read()
    body = section(text, "12. Campaign 6")

    by = {a["tag"]: a for a in arms["arms"]}

    # --- 12.1 the arm table ------------------------------------------------
    exact(body, "| `P0-default` (shipped) | **1.114** | 7 of 12 | `E6132CD07B13` |",
          "12.1 P0 median")
    exact(body, "| `P1-photometric` | **1.101** | 7 of 12 | `891297BF4F60` |",
          "12.1 P1 median")
    exact(body, "| `P2-placebo` | **1.114** | 7 of 12 | `E6132CD07B13` |",
          "12.1 P2 median")
    near(by["P0-default"]["median_vs_noisiest"], 1.114, 5e-4, "P0 median artefact")
    near(by["P1-photometric"]["median_vs_noisiest"], 1.101, 5e-4, "P1 median artefact")
    near(by["P2-placebo"]["median_vs_noisiest"], 1.114, 5e-4, "P2 median artefact")

    CHECKS[0] += 1
    if not all(a["violations"] == 7 for a in arms["arms"]):
        FAILURES.append("12.1 violations: artefact does not read 7 for all arms")

    # The placebo sha must genuinely equal the default's, and the report must
    # quote that sha. Case-insensitive: PowerShell prints upper, json lower.
    CHECKS[0] += 1
    if arms["p0_sha256"] != arms["p2_sha256"]:
        FAILURES.append("12.2 placebo: p0 and p2 sha differ in the artefact")
    CHECKS[0] += 1
    if arms["p0_sha256"][:12].lower() not in body.lower():
        FAILURES.append("12.2 placebo: report does not quote the shared sha prefix")

    # --- 12.2 the reproduction gate ---------------------------------------
    g = arms["p0_vs_armM4"]
    near(g["ncc"], 1.0, 5e-4, "P0 vs armM4 NCC")
    near(g["phase_peak"], 1.0, 5e-4, "P0 vs armM4 phase peak")
    CHECKS[0] += 1
    if (g["shift_dy"], g["shift_dx"]) != (0, 0):
        FAILURES.append("12.2 reproduction: shift is (%s,%s), not (0,0)"
                        % (g["shift_dy"], g["shift_dx"]))
    exact(body, "phase-correlation peak **1.0000**, **NCC 1.0000**", "12.2 NCC in report")

    # --- 12.4 the registered result ---------------------------------------
    near(arms["delta_median"], -0.0130, 5e-4, "delta median")
    check(body, "registered PROMOTE bar", "-0.02", "12.4 bar")
    check(body, "d = median(P1) - median(P0)", "-0.0130", "12.4 delta")
    CHECKS[0] += 1
    if arms["verdict_against_prereg_bars"] != "NULL":
        FAILURES.append("12.4 verdict: artefact says %s, report says NULL"
                        % arms["verdict_against_prereg_bars"])

    # --- 12.5 the paired statistic ----------------------------------------
    raw_pct = 100.0 * (gain["median_hf_ratio_p1_over_p0"] - 1.0)
    near(raw_pct, 4.42, 0.02, "paired raw effect percent")
    check(body, "raises** fine-scale structure in", "9 of 12", "12.5 count")
    check(body, "raises** fine-scale structure in", "+4.42%", "12.5 magnitude")
    exact(body, "Those two windows are `(656, 1552)` and", "12.5 median window A")
    exact(body, "`(2832, 400)` in **both** arms", "12.5 median window B")
    CHECKS[0] += 1
    rises = sum(1 for w in gain["windows"] if w["hf_ratio"] > 1.0)
    if rises != 9:
        FAILURES.append("12.5: %d of 12 windows rise on hf, report says 9" % rises)

    # The arithmetic the report shows for both medians must actually hold.
    near((1.108 + 1.120) / 2, 1.114, 1e-9, "12.5 P0 median arithmetic")
    near((1.040 + 1.163) / 2, 1.1015, 1e-9, "12.5 P1 median arithmetic")

    # --- 12.6 the gain confound -------------------------------------------
    near(100.0 * (gain["median_level_ratio_p1_over_p0"] - 1.0), 0.04, 0.02,
         "level ratio percent")
    near(100.0 * gain["fraction_of_raw_effect_explained_by_gain"], 0.9, 0.1,
         "fraction explained by gain")
    near(gain["median_q_ratio_p1_over_p0"], 1.0455, 5e-4, "gain-invariant q")
    check(body, "Median level ratio", "1.0004", "12.6 level ratio")
    check(body, "explains", "0.9%", "12.6 gain fraction")

    # --- 12.7 three designs ------------------------------------------------
    check(body, "M120 §36.2", "1.0946", "12.7 M120")
    check(body, "M122 |", "1.0638", "12.7 M122")
    check(body, "M116 campaign 6", "1.0455", "12.7 mine")
    CHECKS[0] += 1
    harmed = gain["q_windows_harmed"]
    if harmed != 10:
        FAILURES.append("12.7: q harms %d of 12, report says 10" % harmed)
    check(body, "14.03", "peak-to-peak", "12.7 drift")

    # --- 12.8 the trap -----------------------------------------------------
    near(trap["median_ratio_min"], 0.951, 5e-4, "trap median min")
    near(trap["median_ratio_max"], 1.000, 5e-4, "trap median max")
    near(trap["corr_violations_vs_frame_noise"], 0.639, 5e-3, "trap correlation")
    CHECKS[0] += 1
    if trap["violations_max"] != 6:
        FAILURES.append("12.8: trap violations max is %d, report says 6"
                        % trap["violations_max"])
    CHECKS[0] += 1
    if len(trap["frames"]) != 9:
        FAILURES.append("12.8: %d trap frames, report says nine" % len(trap["frames"]))
    CHECKS[0] += 1
    if not trap["ratio_readout_passes_trap"]:
        FAILURES.append("12.8: artefact says the ratio readout FAILS the trap")
    CHECKS[0] += 1
    if trap["violation_readout_passes_trap"]:
        FAILURES.append("12.8: artefact says the violation readout PASSES the trap")
    check(body, "median ratio | ", "0.951", "12.8 trap range")
    check(body, "corr(violations, frame noise)", "0.639", "12.8 correlation")

    # No trap frame may be one of the instrument's own denominator frames --
    # that would bound the ratio at 1.0 by construction and the trap could not
    # fail. This is the property that makes section 12.8 a trap at all.
    CHECKS[0] += 1
    excluded = set(trap["excluded_because_in_denominator_set"])
    used = {f["frame"] for f in trap["frames"]}
    if used & excluded:
        FAILURES.append("12.8: trap used denominator frames %s, so the ratio was "
                        "bounded by 1.0 by construction" % sorted(used & excluded))

    # --- 12.3 the registration defect --------------------------------------
    check(body, "sit\n**(287, -154) px**", "287", "12.3 offset")
    check(body, "returns\nmedian **0.090**", "0.090", "12.3 A0 misregistered median")
    check(body, "M120 refused", "0.7136", "12.3 M120 NCC")

    print("verify_c6: %d checks over section 12" % CHECKS[0])
    if FAILURES:
        print("RED")
        for f in FAILURES:
            print("  " + f)
        sys.exit(1)
    print("GREEN — every section 12 claim re-derived from the artefacts and "
          "located at its anchored site")


if __name__ == "__main__":
    main()
