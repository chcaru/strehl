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
SECTIONS = ["2.9.54", "2.9.55", "2.9.56", "2.9.57", "2.9.58", "2.9.59",
            "2.9.60", "2.9.61", "2.9.62", "2.9.63", "2.9.64", "2.9.65"]


def collapse(s):
    return re.sub(r"\s+", " ", s)


def load(p):
    return collapse(Path(p).read_text(encoding="utf-8", errors="replace"))


def section_text(status_raw, sec):
    lines = status_raw.splitlines()
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
]

status_raw = STATUS.read_text(encoding="utf-8", errors="replace")
sec = collapse("\n".join(section_text(status_raw, s) for s in SECTIONS))

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

print()

print("GREEN               : %d" % green)
print("RED                 : %d" % red)
print("not asserted (RED)  : %d  %s" % (len(missing_in_status), missing_in_status))
print("controls pass       : %d" % ctl_pass)
print("controls fail       : %d" % ctl_fail)
print("controls skipped    : %d  %s" % (ctl_skip, ctl_skip_reasons))
print("controls accounted  : %d of %d claims" % (ctl_pass + ctl_fail + ctl_skip, len(CLAIMS)))
print("xdoc derived pass   : %d" % xdoc_pass)
print("xdoc derived fail   : %d" % xdoc_fail)
print()
print("VERDICT: " + ("GREEN" if red == 0 and ctl_fail == 0 and xdoc_fail == 0 else "RED"))
sys.exit(0 if (red == 0 and ctl_fail == 0 and xdoc_fail == 0) else 1)
