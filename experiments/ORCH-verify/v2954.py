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
SECTIONS = ["2.9.54", "2.9.55", "2.9.56"]


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
    ("manifest name", "m165-common-input-manifest-v2", R + "M165-common-input.md"),
    # --- scorecard ---
    ("m8r score", "1.030569", "docs/proposals/2026-09-sota-scorecard.md"),
    ("m1 withdrawn", "NO ADMISSIBLE BAR", "docs/proposals/2026-09-sota-scorecard.md"),
]

status_raw = STATUS.read_text(encoding="utf-8", errors="replace")
sec = collapse("\n".join(section_text(status_raw, s) for s in SECTIONS))

# Claims may carry a 4th element: a context literal that must occur within
# WINDOW characters of the value in the source. Presence alone is not enough
# when a neighbouring real value differs only in its last digit.
WINDOW = 160
CLAIMS = [(c + (None, None))[:5] for c in CLAIMS]


def found(src, needle, ctx):
    """True if needle occurs in src, and (if ctx given) ctx occurs near it."""
    for v in variants(needle):
        for m in re.finditer(re.escape(v), src):
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
    in_status = any(v in sec for v in variants(needle))
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

print()
print("claims checked      : %d" % (green + red))
print("GREEN               : %d" % green)
print("RED                 : %d" % red)
print("not asserted (RED)  : %d  %s" % (len(missing_in_status), missing_in_status))
print("controls pass       : %d" % ctl_pass)
print("controls fail       : %d" % ctl_fail)
print("controls skipped    : %d  %s" % (ctl_skip, ctl_skip_reasons))
print("controls accounted  : %d of %d claims" % (ctl_pass + ctl_fail + ctl_skip, len(CLAIMS)))
print()
print("VERDICT: " + ("GREEN" if red == 0 and ctl_fail == 0 else "RED"))
sys.exit(0 if (red == 0 and ctl_fail == 0) else 1)
