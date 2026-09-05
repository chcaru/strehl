#!/usr/bin/env python3
"""Verify STATUS sections 2.9.54 and 2.9.55 against lane sources.

Every claim written into STATUS by the orchestrator must appear in the lane
artifact it cites. This checks that direction: STATUS -> source. A claim
present in STATUS but absent from source is a fabrication or a transcription
error and reads RED.

Numbers are matched in both comma-grouped and plain form, and prose is matched
whitespace-collapsed so a phrase spanning a line break still resolves.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "STATUS.md"
SECTIONS = ["HEADER",
            "2.9.54", "2.9.55", "2.9.56", "2.9.57", "2.9.58", "2.9.59",
            "2.9.60", "2.9.61", "2.9.62", "2.9.63", "2.9.64", "2.9.65",
            "2.9.66", "2.9.67", "2.9.68", "2.9.69", "2.9.70", "2.9.71",
            "2.9.72", "2.9.73", "2.9.74", "2.9.75"]


def collapse(s):
    return re.sub(r"\s+", " ", s)


def unquote(block):
    """Strip leading markdown blockquote markers, one level, per line.

    The STATUS HEADER is entirely a '>' blockquote, so any needle that wraps
    across a line inside it would otherwise collapse to '...paid > arms...' and
    never match. Only a LEADING marker is removed, so mid-line '>' characters
    in needles such as '>=2.00x' or 'Q05 > 1.10' are untouched.
    """
    return "\n".join(re.sub(r"^\s*>\s?", "", ln) for ln in block.splitlines())


def load(p):
    return collapse(Path(p).read_text(encoding="utf-8", errors="replace"))


def section_text(status_raw, sec):
    lines = status_raw.splitlines()
    # "HEADER" is the standing summary above section 1 -- the most owner-facing
    # prose in the file, and until now the only part of STATUS no pin could
    # reach. It is delimited by the top of the file and the first "## 1." rule.
    if sec == "HEADER":
        for j, ln in enumerate(lines):
            if ln.startswith("## 1."):
                if j == 0:
                    raise SystemExit("FATAL: HEADER is empty")
                return "\n".join(lines[:j])
        raise SystemExit("FATAL: '## 1.' not found; HEADER bound is undefined")
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("### " + sec + " "):
            start = i
            break
    if start is None:
        raise SystemExit("FATAL: section %s not found in STATUS" % sec)
    for j in range(start + 1, len(lines)):
        s = lines[j]
        # next same-or-higher-level header ends the section
        if s.startswith("### ") or s.startswith("## "):
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


def variants(needle):
    """Comma-grouped and plain forms of any numeric needle."""
    out = {needle}
    out.add(needle.replace(",", ""))
    m = re.fullmatch(r"(\d+)", needle.replace(",", ""))
    if m:
        d = m.group(1)
        grouped = ""
        while len(d) > 3:
            grouped = "," + d[-3:] + grouped
            d = d[:-3]
        out.add(d + grouped)
    return out


# (label, needle, source path relative to strehl root)
R = "docs/research/"
E = "experiments/"
CLAIMS = [
    # --- M164 transfer veto ---
    ("veto blur sigma", "0.27", R + "M164-transfer-veto.md"),
    ("veto usm amount", "0.0035", R + "M164-transfer-veto.md", None,
     "**amount `0.0035`**"),
    ("veto gain delta", "0.00018", R + "M164-transfer-veto.md"),
    ("veto resample px", "0.001", R + "M164-transfer-veto.md"),
    ("veto blur+gain arms", "72/72", R + "M164-transfer-veto.md"),
    ("veto identity token", "IDENTITY_EQUIVALENT", R + "M164-transfer-veto.md"),
    ("veto legit-diff bound", "2.058879", R + "M164-transfer-veto.md"),
    ("veto movable null LSB", "2.552833", R + "M164-transfer-veto.md"),
    # --- M164 M1 admissibility and staged capture ---
    ("M1 capture exposures", "1,661", R + "M164-m1-staged-capture.md", None, None),
    ("M1 inventory RAWs", "10,509", R + "M164-m1-staged-capture.md", None, None),
    ("M1 rehearsal frames", "896", R + "M164-m1-staged-capture.md", None,
     "`896`-frame rehearsal"),
    ("M1 sealed frames", "704", R + "M164-m1-staged-capture.md", None, None),
    ("M1-first total", "1,602", R + "M164-m1-staged-capture.md", None, None),
    ("M1 combined total", "1,917", R + "M164-m1-staged-capture.md", None, None),
    ("M1 per-class frames", "96", R + "M164-m1-staged-capture.md", None,
     "Every additional focus class adds `96` flat frames"),
    # --- M136 M8-O ---
    ("m8o impossible count", "977,684", R + "M136-m8o-bar.md"),
    ("m8o denominator", "74,173,536", R + "M136-m8o-bar.md"),
    ("m8o denominator json", "74173536", E + "M136-m8o-bar/analysis.json"),
    # --- M163 M10 ---
    ("m10 baseline coverage", "0.94925", E + "M163-m10-uncertainty/commission.json"),
    ("m10 baseline crps", "0.101205", E + "M163-m10-uncertainty/commission.json"),
    ("m10 degraded crps", "0.156590", E + "M163-m10-uncertainty/commission.json"),
    ("m10 degraded coverage", "0.8113", E + "M163-m10-uncertainty/commission.json"),
    ("m10 improved-from crps", "0.109187", E + "M163-m10-uncertainty/commission.json"),
    ("m10 improved-from cov", "0.6764", E + "M163-m10-uncertainty/commission.json"),
    # --- M166 bar audit ---
    # --- M136 recommission and the refused promotion ---
    ("recommission sha256", "5FEC854466CC31C215458C16C9868EBFDE6A46E05D1839EE85FB3BD15EDA9865",
     E + "M136-m8o-bar/verifier-recommission-e5489d64-result.json", None, None),
    ("recommission status", "PASS",
     E + "M136-m8o-bar/verifier-recommission-e5489d64-result.json", None, None),
    ("catmull v1.5 diagnostic", "31148", E + "M136-m8o-bar/analysis.json", None,
     "\"projected_plus_internal_quant_violations\": 31148"),
    ("improvement plant present", "planted improvement",
     E + "M136-m8o-bar/verifier-commission-e5489d64.json", None, "improvement_plant"),
    # --- host load quarantine (2.9.55) ---
    ("host cpu mean", "mean **`93.2%`**", E + "ORCH-verify/host-load-2026-09-06.json", None,
     "\"mean_pct\": 93.2"),
    ("host cpu samples", "`97.0%`", E + "ORCH-verify/host-load-2026-09-06.json", None,
     "\"samples_pct\": [88.6, 97.0, 94.1]"),
    ("m153 zero turns", "`2,782` tool calls", E + "ORCH-verify/host-load-2026-09-06.json", None,
     "\"tool_calls\": 2782"),
    ("m153 elapsed hours", "for `5.07`", E + "ORCH-verify/host-load-2026-09-06.json", None,
     "\"elapsed_hours\": 5.07"),
    # --- coordination policy (2.9.56) ---
    ("policy broadcast count", "broadcast to `9` active lanes",
     E + "ORCH-verify/host-policy-broadcast-2026-09-06.json", None,
     "\"recipients_active_lanes\": 9"),
    # --- M2 loose-direction defect ---
    ("m2 blur-improves ratio", "0.571215", R + "M166-bar-achievability.md", None, None),
    # --- M162 fork + gate ---
    ("fork lightroom tiffs", "105", R + "M162-noise-regression.md", None,
     "used 105 Lightroom-developed TIFFs"),
    # --- M165 common input ---
    ("rawpy version", "0.27.0", R + "M165-common-input.md"),
    ("libraw version", "0.22.1", R + "M165-common-input.md"),
    ("tiff native dims", "7028", R + "M165-common-input.md"),
    ("manifest v3", "v3 common-input manifest", R + "M165-common-input.md", None,
     "The v3 common-input manifest requires the v2 map"),
    ("m165 stage0m battery", "Stage 0M manifest/refusal battery", R + "M165-common-input.md", None,
     "Stage 0M manifest/refusal battery: **PASS**"),
    # --- scorecard ---
    ("m8r score", "1.030569", "docs/proposals/2026-09-sota-scorecard.md"),
    ("m1 withdrawn", "NO ADMISSIBLE BAR", "docs/proposals/2026-09-sota-scorecard.md"),
    # --- M167 detail battery ---
    ("m137 flat beats detail", "1.0249391472947889", R + "M167-detail-battery.md", None,
     "exceeded detail"),
    ("m2 battery replay", "0.5712148772282098", R + "M167-detail-battery.md", None,
     "Independent replay returned"),
    ("m167 results sha",
     "210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B0",
     R + "M167-detail-battery.md"),
    # --- M170 / M8-R closure assessment ---
    ("m8r first run numerator", "1,977,960,960", R + "M8-overshoot.md"),
    ("clamped flat null structure", "13.314850036584688",
     "experiments/M134-kernel-frontier/M137-clamped-detail.md"),
    # --- M147 preflight: the terminal blocker ---
    ("preflight design ratio", "2.0312", R + "M147-preflight.md"),
    ("aperture usm score gain", "1.409469446", R + "M164-aperture-identifiability.md"),
    ("aperture airy calibration error", "1.11e-15", R + "M164-aperture-identifiability.md"),
    ("m3 improvement arm median", "0.0104133574", R + "M169-m3-veil.md"),
    ("m3 census eligible sites", "1,233", R + "M169-m3-veil.md"),
    # --- M164 reference identifiability: AMBIGUITY SURVIVES ---
    ("ref info dominance ratio", "0.698970",
     R + "M164-reference-identifiability.md", "a ratio of"),
    ("ref bits inferior", "1.160964",
     R + "M164-reference-identifiability.md", "reference information"),
    ("scored bits superior", "1.660964",
     R + "M164-reference-identifiability.md", "scored state"),
    ("ref bits movable", "2.350220",
     R + "M164-reference-identifiability.md", "stronger reference transfer"),
    ("ref dominance movable ratio", "1.414973",
     R + "M164-reference-identifiability.md", "dominance gate can move"),
    ("margin over bar", "1.560%",
     R + "M164-reference-identifiability.md", "relative to the bar"),
    ("margin over achieved", "1.536%",
     R + "M164-reference-identifiability.md", "achieved ratio"),
    # --- M174 M3 assertion adjudication: (B) ---
    ("m3 clean null full precision", "0.0029430516302103543",
     R + "M174-m3-improvement-assertion.md"),
    ("m3 gate crossing per component", "0.477804796",
     R + "M174-m3-improvement-assertion.md"),
    # --- M139: M12 peak memory, the column the FAIL actually rests on ---
    ("m12 mem w1 n33", "2.246288", R + "M139-m12-campaign.md"),
    ("m12 mem w2 n33", "4.474667", R + "M139-m12-campaign.md"),
    ("m12 mem w4 n33", "8.931210", R + "M139-m12-campaign.md"),
    ("m12 mem w8 n33", "15.611515", R + "M139-m12-campaign.md"),
    ("m12 mem w16 n33", "24.396667", R + "M139-m12-campaign.md"),
    ("m12 mem w1 n105", "2.246090", R + "M139-m12-campaign.md"),
    ("m12 mem w2 n105", "4.475765", R + "M139-m12-campaign.md"),
    ("m12 mem w4 n105", "8.932907", R + "M139-m12-campaign.md"),
    ("m12 mem w8 n105", "17.837166", R + "M139-m12-campaign.md"),
    ("m12 mem w16 n105", "33.428261", R + "M139-m12-campaign.md"),
    # --- M175: the free comparator arm, rebuilt and passed ---
    ("m175 sentinel intercept", "-6.6597626500634704e-18",
     R + "M175-fork-arm.md"),
    ("m175 sentinel residual", "2.220446049250313e-16",
     R + "M175-fork-arm.md"),
    # --- M164: the GX claim and what it does not buy ---
    ("m164 gx removes nothing", "gx_removed=0", R + "M164-gx-sota-claim.md"),
    # --- M166: the corrected witness and session totals ---
    # STATUS-side needles are full phrases, not bare numerals. A bare "164" is
    # satisfied by every occurrence of "M164" and a bare "1,215" by the second
    # site in the same section, which makes the check unfalsifiable. The 5th
    # element carries the source-side literal.
    ("m166 witness block", "| **total** | **`164`** |",
     R + "M166-reference-dominance-rehearsal.md", None, "164"),
    ("m166 corrected session", "**`1,215`, not `1,147`**",
     R + "M166-reference-dominance-rehearsal.md", None, "1,215"),
    ("m166 rehearsal frames", "The rehearsal is `1,092` registered frames",
     R + "M166-reference-dominance-rehearsal.md", None, "1,092"),
    # --- M151: the cap that masqueraded as a population ---
    # STATUS-side needles are phrases: a bare "275" or "1,944" recurs in the
    # same table and in the re-derivation, so a single-site mutation of a bare
    # numeral cannot falsify the claim.
    ("m151 tile population", "54 * 36 = 1,944",
     R + "M151-m5-checker.md", None, "1,944"),
    ("m151 eligible at population", "it reads `275`",
     R + "M151-m5-checker.md", None, "275"),
    ("m151 wilson lcb", "0.990258", R + "M151-m5-checker.md"),
    # --- 2.9.72: the scorecard outran the plan ---
    # The plan is the authority; these needles pin MY summary of it against the
    # plan's own words, so a drifting paraphrase in STATUS fails loudly.
    ("m169 lead verdict", "SCORECARD EXCEEDS PLAN",
     R + "M169-comparator-requirement-audit.md"),
    # --- header (STATUS:26-40): what the licence is actually worth ---
    # These four are the numbers the OWNER acts on, so each is pinned to the
    # exact cell of M169 section 4.1 that produced it. The STATUS needle and the
    # source literal deliberately differ in wording ("7 more" vs "7 of 12"): the
    # needle proves MY prose still says it, srclit proves the SOURCE still does.
    # If M169 revises its table, these go RED rather than drifting silently.
    ("m169 plan licence axes", "prerequisite for **1 of 12** axes",
     R + "M169-ratification-stakes.md", None, "**1 of 12**"),
    ("m169 propagated axes", "propagates the absent paid arms to **7** more",
     R + "M169-ratification-stakes.md", None, "**7 of 12**"),
    ("m169 axes shedding d", "**6** axes shed blocker `(d)`",
     R + "M169-ratification-stakes.md", None, "**6 of 12**"),
    ("m169 newly scoreable", "**0 of 12** newly scoreable",
     R + "M169-ratification-stakes.md", None, "**0 of 12**"),
    # The headline. Pinned to the scorecard clause that establishes there are
    # twelve axes and that a verdict needs all of them; the "0 passed" half is
    # the orchestrator's own adjudication and is proved instead by the planted
    # control in commission_header.py, which mutates it and requires a RED.
    ("header scored axis count",
     "**Current position against that bar: 0 of 12 axes passed.**",
     "docs/proposals/2026-09-sota-scorecard.md", None,
     "A verdict requires measurements for all twelve axes"),
    ("plan noise quotable now", "Nothing — quotable now",
     "docs/proposals/2026-08-sota-path.md"),
    ("plan speed hold the line",
     "Hold the line (D5; D9 buys back the worker-cap tax first)",
     "docs/proposals/2026-08-sota-path.md"),
    ("plan detail names licence", "Only fine detail names",
     "docs/proposals/2026-08-sota-path.md", None, "a licensed comparator"),
    ("plan free arm clears nothing",
     "is a useful foreign arm and repairs a real provenance defect",
     "docs/proposals/2026-08-sota-path.md"),
    ("m164 manifest refusals", "with `17` persistent refusals",
     R + "M164-dominance-manifest.md", None, "17 persistent refusal records"),
    ("m166 disjoint arithmetic", "891 - 96 + 128 + 164 + 128 = 1,215",
     R + "M166-rehearsal-cost.md", None, "891 - 96 + 128 + 164 + 128"),
    ("m166 not interchangeable",
     "Equal budgets do not make the files interchangeable",
     R + "M166-rehearsal-cost.md"),
    # --- 2.9.73: M12 scored FAIL; M11 quarantined; M164 answered both asks ---
    # M139's two independent bars. The memory numbers share a sentence, so each
    # is pinned on its own labelled phrase rather than the bare numeral.
    ("m139 memory peak", "Job Object peak `35.65745162963867 GiB`",
     R + "M139-m12-campaign.md", None, "35.65745162963867 GiB"),
    ("m139 sampled commit", "sampled private commit `35.65724182128906 GiB`",
     R + "M139-m12-campaign.md", None, "35.65724182128906 GiB"),
    ("m139 sampled bytes", "`38,286,671,872` bytes",
     R + "M139-m12-campaign.md", None, "38,286,671,872"),
    ("m139 external busy",
     "external-busy fraction among all accepted runs was `0.0991197`",
     R + "M139-m12-campaign.md", None, "0.0991197"),
    ("m139 coverage shortfall", "coverage was `0.7957678743186919`",
     R + "M139-m12-campaign.md", None, "0.7957678743186919"),
    ("m139 sample gap", "`60.85830001393333 ms`",
     R + "M139-m12-campaign.md", None, "60.85830001393333"),
    ("m139 null plant bytes", "peaked at `80,920,576` bytes",
     R + "M139-m12-campaign.md", None, "80,920,576"),
    # The byte property. STATUS states it in prose; M139 now states it as a
    # table, so the pin quotes STATUS's sentence but proves it against the
    # table ROW, which is the thing that would actually change if the result
    # changed.
    ("m139 five hashes",
     "five distinct TIFF hashes and five distinct pixel hashes",
     R + "M139-m12-campaign.md", None, "| 33 | 5 | 5 | **FAIL** |"),
    ("m139 five hashes n299", "at three independent `N`",
     R + "M139-m12-campaign.md", None, "| 299 | 5 | 5 | **FAIL** |"),
    # M139's guard on the memory reading. This is the sentence that stops an
    # under-sampled peak from being read as an over-claim: sampling error can
    # only hide a failure here, never invent one.
    ("m139 understate guard",
     "It cannot manufacture the observed above-6-GiB failure",
     R + "M139-m12-campaign.md"),
    # The two terms the completed campaign added. The modulo spread is a
    # measured FAIL; the ratio is the one registered term that stayed unread.
    ("m139 modulo spread", "`0.07618677189815302` (`7.618677%`)",
     R + "M139-m12-campaign.md", None, "0.07618677189815302"),
    ("m139 ratio sampled", "`1.4615654159027742` sampled",
     R + "M139-m12-campaign.md", None, "1.4615654159027742"),
    ("m139 ratio kernel", "`1.461570587793803` kernel",
     R + "M139-m12-campaign.md", None, "1.461570587793803"),
    # N=299 finally scored, which is what turns M12-D from UNMEASURED to PASS.
    ("m12 mem w1 n299", "2.246307", R + "M139-m12-campaign.md"),
    ("m12 mem w2 n299", "4.476284", R + "M139-m12-campaign.md"),
    ("m12 mem w4 n299", "8.935242", R + "M139-m12-campaign.md"),
    ("m12 mem w8 n299", "17.836559", R + "M139-m12-campaign.md"),
    ("m12 mem w16 n299", "35.657452", R + "M139-m12-campaign.md"),
    # M153: the instrument is real, the number is refused. Only the host-load
    # quarantine is pinnable here -- UNMEASURED_COMPARATOR_QUALIFICATION occurs
    # 5x in STATUS and 3x in its source, so no mutation can flip it and a
    # presence check on it would read as coverage while testing nothing.
    ("m153 host quarantine", "QUARANTINED_HOST_LOAD",
     R + "M153-m11-harness.md"),
    ("m153 null timing", "null `0.003762750 s`",
     R + "M153-m11-harness.md", None, "0.003762750"),
    ("m153 plant timing", "plant recovered as `0.081845017 s`",
     R + "M153-m11-harness.md", None, "0.081845017"),
    ("m153 async tail", "async tail `0.1182856 s`",
     R + "M153-m11-harness.md", None, "0.1182856"),
    # M164's two rulings. Both are INFERRED BY READING and STATUS says so; the
    # pins here prove the ruling text itself has not drifted.
    ("m164 licence critical path", "LICENCE ON CRITICAL PATH",
     R + "M164-dominance-manifest.md"),
    ("m164 ask2a manifest input", "ASK 2A IS A MANIFEST INPUT",
     R + "M164-dominance-manifest.md"),
    ("m164 not side errand",
     "a direct critical-path input, not a side errand",
     R + "M164-dominance-manifest.md"),
    # NOT pinned here, deliberately: M160's "reduction order changes with worker
    # count" and M166's "Worker-independent arithmetic ..." are already asserted
    # by earlier sections. Adding them as 2.9.73 claims would have been
    # satisfied by those pre-existing quotes, so they would have proved nothing
    # about this section while inflating the GREEN count.
    #
    # 2.9.75: M176's reproduction of the M12-S mechanism. These are the lane's
    # own measured figures; the derived memory numbers are re-computed in the
    # xdoc block instead, because they are mine and exist in no source.
    ("m176 mechanism", "REDUCTION_ORDER", R + "M176-worker-invariance.md",
     None, None),
    ("m176 pixels moved", "3,430", R + "M176-worker-invariance.md",
     "8,241,504", None),
    ("m176 pixel total", "8,241,504", R + "M176-worker-invariance.md",
     "3,430", None),
    ("m176 pixel pct", "0.041619", R + "M176-worker-invariance.md",
     None, None),
    ("m176 lattice", "[5,5,5,4]", R + "M176-worker-invariance.md",
     None, None),
]

status_raw = STATUS.read_text(encoding="utf-8", errors="replace")
sec = collapse(unquote("\n".join(section_text(status_raw, s) for s in SECTIONS)))

# Claims may carry a 4th element: a context literal that must occur within
# WINDOW characters of the value in the source. Presence alone is not enough
# when a neighbouring real value differs only in its last digit.
WINDOW = 160
CLAIMS = [(c + (None, None))[:5] for c in CLAIMS]


def rounds_to(full, short):
    """True if the longer decimal `full` rounds exactly to `short`."""
    if "." not in short:
        return False
    try:
        dec = len(short.split(".")[1])
        return format(float(full), ".%df" % dec) == short
    except ValueError:
        return False


def positions(hay, needle, extend=False):
    """Boundary-aware matches of a numeric needle.

    A bare substring search makes a check unfalsifiable as soon as any other
    site carries a longer number with the same prefix: `2.0312` is satisfied by
    `2.031203`, so mutating the canonical site still reads GREEN. Commissioning
    caught exactly that.

    STATUS is searched strictly (`extend=False`): a quoted value must have its
    own canonical site, not ride on a longer neighbour. Sources are searched
    with `extend=True`, because STATUS legitimately quotes a rounded form of a
    full-precision artifact value -- but only when the longer value actually
    rounds to the quoted one.
    """
    out = []
    for v in variants(needle):
        for m in re.finditer(re.escape(v), hay):
            if m.start() > 0 and hay[m.start() - 1].isdigit():
                continue
            after = hay[m.end()] if m.end() < len(hay) else ""
            if after.isdigit():
                if not extend:
                    continue
                tail = re.match(r"\d+", hay[m.end():]).group(0)
                if not rounds_to(v + tail, v):
                    continue
            out.append(m)
    return out


def found(src, needle, ctx):
    """True if needle occurs in src, and (if ctx given) ctx occurs near it."""
    for m in positions(src, needle, extend=True):
        if ctx is None:
            return True
        w = src[max(0, m.start() - WINDOW):m.end() + WINDOW]
        if ctx in w:
            return True
    return False


cache = {}
green = red = 0
missing_in_status = []

# ---- header-scoped claims ----------------------------------------------------
# `sec` above concatenates EVERY section, so a value that also appears in
# 2.9.66 or 2.9.74 satisfies a whole-file presence check even when the header
# itself has been corrupted. The header is the most owner-facing prose in the
# file and must not inherit its correctness from a section further down. These
# claims are therefore matched against the HEADER TEXT ALONE, and separately
# against the lane source, so neither a header edit nor lane drift passes.
HDR = collapse(unquote(section_text(status_raw, "HEADER")))
HEADER_ONLY = [
    ("hdr m8r score", "1.030569",
     "docs/proposals/2026-09-sota-scorecard.md"),
    ("hdr m12 peak", "35.65745162963867", R + "M139-m12-campaign.md"),
    ("hdr m12 modulo", "0.07618677189815302", R + "M139-m12-campaign.md"),
    ("hdr m12 coverage", "0.7957678743186919", R + "M139-m12-campaign.md"),
    ("hdr plan m12 bar", "bytes invariant to worker count (D9a)",
     "docs/proposals/2026-08-sota-path.md"),
    ("hdr plan measurable", "Two axes -- M8 and M12 -- are measurable today",
     "docs/proposals/2026-08-sota-path.md"),
    ("hdr m178 verdict", "UNRATIFIED_ADDITION", R + "M178-m12s-adjudication.md"),
    ("hdr m178 origin", "986c46535fc082395831724f1d45c33a1d974390",
     R + "M178-m12s-adjudication.md"),
    ("hdr m178 reword", "dd957dd5f8ef36af99065db5aa52065171556adf",
     R + "M178-m12s-adjudication.md"),
    ("hdr m169 r9 lines", "295-311", R + "M178-m12s-adjudication.md"),
    ("hdr scorecard rev", "Revision 1.11",
     "docs/proposals/2026-09-sota-scorecard.md"),
]
for label, needle, rel in HEADER_ONLY:
    p = ROOT / rel
    if not p.exists():
        print("RED   %-24s SOURCE MISSING %s" % (label, rel))
        red += 1
        continue
    if rel not in cache:
        cache[rel] = load(p)
    if not positions(HDR, needle):
        print("RED   %-24s %s NOT IN STATUS HEADER" % (label, needle))
        red += 1
    elif not positions(cache[rel], needle):
        print("RED   %-24s %s NOT IN %s" % (label, needle, rel))
        red += 1
    else:
        print("GREEN %-24s %s  [header-scoped]" % (label, needle))
        green += 1

for label, needle, rel, ctx, srclit in CLAIMS:
    p = ROOT / rel
    if not p.exists():
        print("RED   %-24s SOURCE MISSING %s" % (label, rel))
        red += 1
        continue
    if rel not in cache:
        cache[rel] = load(p)
    src = cache[rel]
    in_status = bool(positions(sec, needle))
    if not in_status:
        # Every entry in CLAIMS is something this section asserts. Absence means
        # the assertion was removed or mistyped -- both are defects. Treating it
        # as "skipped" made the whole verifier a no-op: a wrong digit in STATUS
        # silently left the claim unchecked and the run still read GREEN.
        print("RED   %-24s %s NOT ASSERTED IN STATUS %s" % (label, needle, "/".join(SECTIONS)))
        missing_in_status.append(label)
        red += 1
        continue
    probe = srclit if srclit is not None else needle
    if found(src, probe, ctx):
        note = ""
        if srclit is not None:
            note = "  [pinned]"
        elif ctx is not None:
            note = "  [anchor %s]" % ctx
        print("GREEN %-24s %s%s" % (label, needle, note))
        green += 1
    else:
        print("RED   %-24s %s NOT IN %s" % (label, needle, rel))
        red += 1

# ---- negative controls: mutate each needle, require the check to stop finding it ----
# A global decoy search collides on short tokens ("100" vs "105") and on values
# that legitimately appear elsewhere in the same document (M164's non-firing
# 0.0030 sits in the same table row as its firing 0.0035). Where that happens the
# check is pinned to a distinguishing source literal, and the control mutates
# that same literal, so the control measures the check that actually runs.
ctl_pass = ctl_fail = ctl_skip = 0
ctl_skip_reasons = []
for label, needle, rel, ctx, srclit in CLAIMS:
    src = cache.get(rel)
    probe = srclit if srclit is not None else needle
    if src is None or not re.search(r"\d", probe):
        ctl_skip += 1
        ctl_skip_reasons.append((label, "non-numeric or source unread"))
        continue
    idx = max(i for i, ch in enumerate(probe) if ch.isdigit())
    mutated = probe[:idx] + str((int(probe[idx]) + 5) % 10) + probe[idx + 1:]
    if mutated == probe:
        ctl_skip += 1
        ctl_skip_reasons.append((label, "mutation is a no-op"))
        continue
    if found(src, mutated, ctx):
        print("CTLFAIL %-22s decoy %s still satisfies the check" % (label, mutated))
        ctl_fail += 1
    else:
        ctl_pass += 1

# ---- cross-document derived claims -------------------------------------------
# STATUS 2.9.65 asserts a COUNT derived from a table that another lane owns and
# actively edits. A quoted count goes stale silently: the sentence still reads
# well after the table beneath it changes. Recompute it from the source instead
# of pinning the digit.
xdoc_pass = xdoc_fail = 0
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"


def check(label, ok, detail):
    global xdoc_pass, xdoc_fail
    if ok:
        print("XDOC  %-24s %s" % (label, detail))
        xdoc_pass += 1
    else:
        print("XFAIL %-24s %s" % (label, detail))
        xdoc_fail += 1


if not SCORECARD.exists():
    check("scorecard present", False, "MISSING %s" % SCORECARD)
else:
    sc_lines = SCORECARD.read_text(encoding="utf-8", errors="replace").splitlines()
    # The §3.1 readiness table: rows "| M<n> | **<class codes>** | ..."
    d_axes = []
    for ln in sc_lines:
        m = re.match(r"^\| (M\d+) \| \*\*(.+?)\*\* \|", ln)
        if m and "(d)" in m.group(2):
            d_axes.append(m.group(1))
    expected = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    check("blocker (d) axis set", d_axes == expected,
          "recomputed %s (STATUS 2.9.65 asserts exactly these seven)" % (d_axes,))
    check("m3 carries (a)(b)(d)",
          any(re.match(r"^\| M3 \| \*\*.*\(a\)\(b\)\(d\)\*\* \|", ln) for ln in sc_lines),
          "STATUS 2.9.61 correction depends on M3 carrying (a) and (d)")
    joined = collapse("\n".join(sc_lines))
    check("all-arms-required rule",
          "the named-comparator requirement is unmet and the dependent comparative axes remain"
          in joined,
          "STATUS 2.9.65 quotes this to justify 'all three arms are required'")

# STATUS 2.9.66 overrules a lane on the authority of three verbatim quotes from
# two lane-owned research files. Those lanes are live and may revise them, at
# which point my justification silently ceases to exist in its own source.
QUOTES = [
    ("m12 load rule", "docs/research/M160-amendment6-reachability.md",
     "Correctness arms may run under load; any absolute-time arm remains quarantined."),
    ("m12 root cause", "docs/research/M160-amendment6-reachability.md",
     "because reduction order changes with worker count"),
    ("m12 fix achievable", "docs/research/M166-bar-achievability.md",
     "can make all five outputs byte-identical"),
    ("m12s diagnostic fail", "docs/STATUS.md",
     "**M12-S, cross-worker scaling invariance** -- diagnostic FAIL."),
    ("m166 target holds", "docs/research/M166-reference-information-dominance-physical.md",
     "TARGET HOLDS AT 1.32x"),
    ("m166 rehearsal first", "docs/research/M166-reference-information-dominance-physical.md",
     "only a pass licenses the `1,147`-frame holdout sitting."),
    ("m166 weakest cell", "docs/research/M166-reference-information-dominance-physical.md",
     "1.03405"),
    ("m164 shared objective", "docs/research/M164-reference-dominance.md",
     "SHARED OBJECTIVE SUFFICIENT"),
    ("m164 strictly positive", "docs/research/M164-reference-identifiability.md",
     "must be strictly positive"),
    # Anchored on values with exactly one site in the source. "BATTERY
    # COMMISSIONED" occurs twice and "UNMEASURED_COMPARATOR_QUALIFICATION" five
    # times, so a presence check on either is satisfied by a duplicate after the
    # claim it guards has drifted.
    ("m169 commission sha", "docs/research/M169-m3-veil.md", "3d69bbcd"),
    ("m169 green recovery arm", "docs/research/M169-m3-veil.md", "0.005649"),
    ("m169 axis has no CI", "docs/research/M169-m3-veil.md",
     "confidence_interval=NO CI"),
    ("m175 exec sha", "experiments/M175-fork-arm/render-result.json",
     "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"),
    ("m175 sentinel slope", "experiments/M175-fork-arm/render-result.json",
     "1.0000000000000002"),
    ("m139 m12 memory fail", "docs/research/M139-m12-campaign.md", "8.9312"),
    # Amendment 8 quotes four documents it does not own. Three of the four are
    # lane-owned and live. Pin each quote at its SOURCE so that a lane revising
    # its own file fails my amendment rather than silently orphaning it.
    ("a8 split2 verdict", "docs/research/M-PHASE0-SPLIT2.md",
     "Final verdict: NOT ROBUST / NO BUILD."),
    ("a8 split2 fail rms", "docs/research/M-PHASE0-SPLIT2.md", "0.107703"),
    ("a8 split2 spatial", "docs/research/M-PHASE0-SPLIT2.md", "0.105202"),
    ("a8 phase filed verdict", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md",
     "Filed verdict: KILL at the measured rho, NOT ROBUST across the rho census."),
    ("a8 phase rho ci", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md",
     "(0.00185-0.01078)"),
    ("a8 phase rho 30x", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md", "30.49x"),
    ("a8 status phase closed", "docs/STATUS.md",
     "CLOSED. C1 is KILL at the measured"),
    ("a8 m133 phase not absent", "docs/research/M133-blocker-audit.md",
     "is false. Its result is filed in the"),
]
for label, rel, quote in QUOTES:
    p = ROOT / rel
    if not p.exists():
        check(label, False, "SOURCE MISSING %s" % rel)
        continue
    check(label, collapse(quote) in load(p),
          "%s quotes this verbatim from %s"
          % ("Amendment 8" if label.startswith("a8 ") else "STATUS 2.9.66", rel))

# ---- 2.9.75: re-derive M172's memory figures instead of matching them ----
#
# Three of the numbers in 2.9.75 are MINE, not any lane's: the GiB conversions,
# the ratio, and the headroom. Nothing in the corpus contains them, so a
# presence check against a source would be either a guaranteed RED or, worse,
# quietly repointed at some coincidental occurrence. They are re-derived here
# from the raw Job Object byte counts in M172's run records, which ARE primary,
# and compared against what STATUS actually says. If a lane re-runs and the
# bytes move, this fails -- which is the whole point.
M172R = E + "M172-worker-memory/out/candidate/records/"
GIB = 1024.0 ** 3
BAR_BYTES = 6442450944


def job_peak(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        return d["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]
    except Exception:
        return None


n33 = job_peak(M172R + "measured-n33-w16.json")
n299 = job_peak(M172R + "measured-n299-w16.json")
if n33 is None or n299 is None:
    check("m172 records readable", False,
          "missing or unparseable M172 run records; 2.9.75's memory "
          "figures cannot be re-derived and must not be trusted")
else:
    s75 = section_text(status_raw, "2.9.75")
    check("m172 n299 peak bytes", "%d" % n299 in collapse(s75).replace(",", ""),
          "2.9.75 states the N=299 Job Object peak as %d B" % n299)
    check("m172 n299 gib", "%.6f" % (n299 / GIB) in s75,
          "re-derived %.6f GiB from %d B" % (n299 / GIB, n299))
    check("m172 headroom gib", "%.3f" % ((BAR_BYTES - n299) / GIB) in s75,
          "re-derived %.3f GiB of headroom under the %d B bar"
          % ((BAR_BYTES - n299) / GIB, BAR_BYTES))
    check("m172 ratio", "%.6f" % (n299 / float(n33)) in s75,
          "re-derived ratio %.6f from %d/%d (DISQUALIFIED on provenance, "
          "not on value)" % (n299 / float(n33), n299, n33))
    check("m172 under bar", n299 < BAR_BYTES,
          "re-derived peak %d B is under the %d B bar; 2.9.75 must not "
          "call this a pass, only preliminary" % (n299, BAR_BYTES))

# ---- M8-O v1.5: the bar's normative text lives OUTSIDE the scorecard --------
# The scorecard delegates the v1.5 bar to a git blob rather than transcribing
# it, so the bar has one canonical site and cannot drift between two copies.
# That is the right call, but it makes the hex digits load-bearing: a single
# mistyped character leaves the bar with no text at all and nothing else in the
# repository would notice. The hash is READ FROM THE SCORECARD, never hardcoded
# here, so corrupting it there turns this check RED.
import subprocess

SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
V15_ANCHORS = ("final serialized source-support certificate",
               "crop origin, frame-site trace, or arithmetic metadata")


def git_blob(sha):
    """Return blob bytes, or None. Bytes, not a redirected stream: on Windows
    `git show ... > file` re-encodes and silently corrupts the comparison."""
    p = subprocess.run(["git", "cat-file", "-p", sha], cwd=str(ROOT),
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.stdout if p.returncode == 0 else None


if not SCORECARD.exists():
    check("m8o v1.5 blob pin", False, "scorecard not found at %s" % SCORECARD)
else:
    sc = SCORECARD.read_text(encoding="utf-8")
    m = re.search(r"v1\.5 bar is .{0,120}?pinned at git blob\s*`?([0-9a-f]{40})`?",
                  collapse(sc))
    if not m:
        check("m8o v1.5 blob pin", False,
              "scorecard no longer names a 40-hex blob for the v1.5 normative "
              "text; the bar may have been silently orphaned")
    else:
        sha = m.group(1)
        blob = git_blob(sha)
        check("m8o v1.5 blob resolves", blob is not None,
              "scorecard-referenced blob %s resolves to %d bytes"
              % (sha, len(blob) if blob else 0))
        if blob is not None:
            txt = blob.decode("utf-8", "replace")
            for anchor in V15_ANCHORS:
                check("m8o v1.5 anchor", anchor in txt,
                      "pinned blob contains %r" % anchor[:46])

print()

# ---- 2.9.76: the clamp ruling depends on the default NOT having moved --------
#
# STATUS 2.9.76 and docs/research/ORCH-clamp-default-decision.md N5 both rest on
# a live fact about the shipping code: the clamped kernel is still OPT-IN. If any
# lane flips DEFAULT_RESAMPLER_NAME, N5 is violated, 2.9.76's premise is false,
# and an M8 zero taken afterwards is defeated by the scorecard clause at :1631.
# Nothing else in this corpus would notice, so it is pinned here.
ALIGN_CMD = ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs"
RESTORE_RS = ROOT / "crates" / "strehl-core" / "src" / "restore.rs"
CLAMP_DOC = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"

if not ALIGN_CMD.exists():
    check("clamp default source", False,
         "crates/strehl-cli/src/align_cmd.rs is missing; 2.9.76's premise "
         "cannot be checked and must not be trusted")
else:
    align_src = ALIGN_CMD.read_text(encoding="utf-8", errors="replace")
    check("clamp still opt-in",
         'pub const DEFAULT_RESAMPLER_NAME: &str = "catmull-rom";' in align_src,
         "shipping default is still catmull-rom, so ORCH-clamp-default-decision "
         "N5 holds and 2.9.76's premise is intact")

if not RESTORE_RS.exists():
    check("restore source", False, "crates/strehl-core/src/restore.rs is missing")
else:
    restore_src = RESTORE_RS.read_text(encoding="utf-8", errors="replace")
    check("restoration refuses clamp",
         "!matches!(r, Resampler::ClampedCatmullRom)" in restore_src,
         "restoration_supported() still excludes ClampedCatmullRom, which is the "
         "cost G4 of the clamp decision is written against")

if not CLAMP_DOC.exists():
    check("clamp decision doc", False,
         "docs/research/ORCH-clamp-default-decision.md is missing; 2.9.76 cites "
         "a ruling that no longer exists")
else:
    clamp_txt = collapse(CLAMP_DOC.read_text(encoding="utf-8"))
    check("clamp N5 ruling present",
         collapse("A clamped shipping default is NOT a route to an M8 PASS while "
                  "M1 is absent.") in clamp_txt,
         "the N5 prohibition 2.9.76 quotes is present in the decision document")
    check("clamp decision unresolved",
         "**UNRESOLVED.** No arm has been read." in clamp_txt,
         "the clamp decision is still registered-and-unresolved; if this flips, "
         "2.9.76 needs rewriting rather than a footnote")

s76 = section_text(status_raw, "2.9.76")
check("2.9.76 present", bool(s76.strip()),
     "STATUS 2.9.76 exists and is non-empty")
check("2.9.76 keeps the scoreboard honest",
     collapse("The scoreboard is unchanged at `0 of 12`.") in collapse(s76),
     "2.9.76 still states the scoreboard is 0 of 12; no axis was quietly cashed")

# --- M165 fork arm: cross-document agreement, not mere presence ---------------
# Presence on one side proves a string exists. These pin the SAME figure in the
# owner-facing document and in the lane document that produced it, so a drift on
# either side is RED rather than silently one-sided.
_owner = collapse(re.sub(r"(?m)^[ \t]*>[ \t]?", "",
                         (ROOT / "docs" / "OWNER-ACTIONS.md").read_text(
                             encoding="utf-8", errors="replace")))
_m165 = collapse((ROOT / "docs" / "research" / "M165-common-input.md").read_text(
    encoding="utf-8", errors="replace"))

for _label, _fig in (
    ("fork revision", "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"),
    ("fork executable sha", "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"),
):
    check("%s agrees owner<->M165" % _label,
         (_fig in _owner) and (_fig in _m165),
         "%s is identical in OWNER-ACTIONS and M165-common-input; a one-sided "
         "edit fails this rather than passing on the untouched copy" % _label)

check("fork hash frozen before rendering",
     collapse("**before** any rendering") in _owner,
     "the owner text preserves the ordering claim; a hash frozen after "
     "rendering would prove nothing about what rendered")
check("fork arm does not discount the licence",
     collapse("The `$189` still buys the two Zerene arms and nothing else")
     in _owner,
     "closing the fork arm is not reported as reducing the purchase")
check("fork cross-host limit retained",
     collapse("Cross-host reproducibility is untested") in _owner,
     "M165's own stated limit survives into the owner document rather than "
     "being dropped on the way")

# --- M177 capture programme: totals agree with the lane, boundary preserved ---
_m177 = collapse((ROOT / "docs" / "research" /
                  "M177-capture-programme.md").read_text(
                      encoding="utf-8", errors="replace"))

for _label, _fig in (("specified floor", "3,716"),
                     ("registered capture floor", "2,309"),
                     ("landed envelope", "2,995")):
    check("%s agrees owner<->M177" % _label,
         (_fig in _owner) and (_fig in _m177),
         "%s is the same figure in OWNER-ACTIONS and M177-capture-programme" % _label)

for _expr, _total in (("2 + 1,092 + 1,215 + 686 + 64 + 657", "3,716"),
                      ("2 + 1,092 + 1,215", "2,309"),
                      ("2 + 1,092 + 1,215 + 686", "2,995")):
    _ok = _expr in _owner
    if _ok:
        _parts = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", _expr)]
        _ok = (sum(_parts) == int(_total.replace(",", ""))) and (_total in _owner)
    check("total %s re-derives from its own addends" % _total, _ok,
         "the addends printed in OWNER-ACTIONS actually sum to the total "
         "printed there; drifting any single addend fails this, which a "
         "hardcoded arithmetic assertion could never do")
check("capture does not clear blocker (a)",
     collapse("they are **not sufficient**, and no quantity of them clears "
              "`(a)`") in _owner,
     "the owner document still states plainly that frames alone cannot clear "
     "blocker (a); this is the claim most likely to be softened by accident")
check("the three 164 blocks stay unmerged",
     collapse("three distinct acquisitions") in _owner,
     "the non-share finding survives into the owner document; merging them "
     "would understate the shutter demand by 164 frames")
check("D8 kill reaches the owner",
     ("KILL" in _owner) and collapse("M-PHASE0-SPLIT.md:3") in _owner,
     "the owner is told the plan's own nominated detail instrument was killed "
     "at its gate, with the citation")

s77 = section_text(status_raw, "2.9.77")
check("2.9.77 present", bool(s77.strip()),
     "STATUS 2.9.77 exists and is non-empty")
_s77 = collapse(s77)
for _label, _quote in (
    ("2.9.77 keeps the scoreboard honest",
     "**The scoreboard is unchanged at `0 of 12`.**"),
    ("2.9.77 carries the D8 kill verbatim",
     'reads **"Verdict: KILL — STOP/REMOVE RUST; retain the split instrument '
     'offline."**'),
    ("2.9.77 states the M8 coupling",
     "**The structural consequence: M8 cannot be honestly passed before "
     "`(a)` closes.**"),
    ("2.9.77 flags N6's assumption rather than hiding it",
     "**This rests on an assumption I have flagged rather than hidden**"),
    ("2.9.77 keeps the M4 count attributed",
     "`178` is an **M152**-eligible count, not an M166-eligible one"),
    ("2.9.77 keeps the self-correction",
     "no quantity of them clears `(a)`"),
):
    check(_label, collapse(_quote) in _s77,
         "2.9.77 still carries this claim; each is a place where the record "
         "would quietly improve if it drifted")

check("2.9.77 M4 arithmetic re-derives",
     ("29" in _s77 and "83" in _s77 and "112" in _s77
      and 29 + 83 == 112 and collapse("`29` medication + `83` foam = `112`") in _s77),
     "the M4 shortfall is printed with its addends and they sum to the total "
     "printed beside them")

# ---- Amendment 8: the phase-0 audit -----------------------------------------
#
# Two kinds of pin here, and they are not equally strong.
#
#   (1) TRANSCRIPTION pins: the plan reproduces a quote that the QUOTES block
#       has separately confirmed still exists in its source. Together those two
#       halves catch both a lane revising the source and me mistyping it. Either
#       half alone is worthless.
#   (2) One LIVE pin on an ABSENCE. Amendment 8 asserts two phase-0 gates have
#       never produced a tracked result. An absence claim decays the moment
#       somebody does the work, and nothing in the prose would notice. This is
#       the thing that notices.
PLAN = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
if not PLAN.exists():
    check("a8 plan present", False, "MISSING %s" % PLAN)
else:
    _plan = load(PLAN)
    check("a8 section present", collapse("## 18. Amendment 8") in _plan,
          "Amendment 8 is registered in the plan")
    for _lbl, _q in [
        ("a8 cites split2", "Final verdict: NOT ROBUST / NO BUILD."),
        ("a8 cites phase", "Filed verdict: KILL at the measured rho, "
                           "NOT ROBUST across the rho census."),
        ("a8 cites rho ci", "(0.00185-0.01078)"),
        ("a8 cites rho 30x", "30.49x"),
    ]:
        check(_lbl, collapse(_q) in _plan,
              "Amendment 8 reproduces this verbatim from its pinned source")
    # THIRD occurrence of the blockquote/collapse defect. `load()` does not
    # strip `>` markers, so any quote spanning a line break inside a blockquote
    # silently fails. The ruling below is blockquoted and wraps, so it needs the
    # stripped copy; the transcription pins above do not, because each of those
    # quotes sits entirely on one line.
    _plan_bq = collapse(re.sub(r"(?m)^[ \t]*>[ \t]?", "",
                               PLAN.read_text(encoding="utf-8", errors="replace")))
    # The ruling itself. If this sentence is softened, C1 silently becomes
    # schedulable again, which is the exact failure Amendment 8 documents.
    check("a8 c1 ruling intact",
          collapse("It may not be scheduled as build-ready phase-3 work") in _plan_bq
          and collapse("and it may not be struck, because that same interval "
                       "contains SURVIVE") in _plan_bq,
          "C1 is held at BLOCKED -- neither schedulable nor struck")

_gate_hits = []
for _stem in ("M-PHASE0-MAKERNOTE", "M-PHASE0-TETHER"):
    for _d in (ROOT / "docs" / "research", ROOT / "experiments"):
        if _d.exists():
            _gate_hits += sorted(str(x.relative_to(ROOT)) for x in _d.glob(_stem + "*"))
check("a8 makernote/tether unrun", not _gate_hits,
      "Amendment 8 section 18.3 says neither gate has a tracked result; "
      "found %s" % (_gate_hits if _gate_hits else "none, as asserted"))

print()
print("RED                 : %d" % red)
print("not asserted (RED)  : %d  %s" % (len(missing_in_status), missing_in_status))
print("controls pass       : %d" % ctl_pass)
print("controls fail       : %d" % ctl_fail)
print("controls skipped    : %d  %s" % (ctl_skip, ctl_skip_reasons))
print("controls accounted  : %d of %d CLAIMS entries" % (ctl_pass + ctl_fail + ctl_skip, len(CLAIMS)))
print("header-scoped       : %d, commissioned separately by commission_header.py"
      % len(HEADER_ONLY))
print("checks accounted    : %d of %d green+red"
      % (ctl_pass + ctl_fail + ctl_skip + len(HEADER_ONLY), green + red))
print("xdoc derived pass   : %d" % xdoc_pass)
print("xdoc derived fail   : %d" % xdoc_fail)
print()
print("VERDICT: " + ("GREEN" if red == 0 and ctl_fail == 0 and xdoc_fail == 0 else "RED"))
sys.exit(0 if (red == 0 and ctl_fail == 0 and xdoc_fail == 0) else 1)
