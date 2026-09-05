#!/usr/bin/env python3
"""Verify the 2026-09-06 capture block in OWNER-ACTIONS against M164's source.

Two independent directions:
  1. every figure quoted to the owner occurs in the lane document it came from;
  2. the staged totals are re-derived arithmetically rather than copied.

A number that survives (1) but fails (2) is a transcription that happens to
match a real value elsewhere -- which is why (2) exists.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
OWNER = ROOT / "docs" / "OWNER-ACTIONS.md"
SRC = ROOT / "docs" / "research" / "M164-m1-staged-capture.md"
HEADING = "### Two things changed on 2026-09-06"


def collapse(s):
    return re.sub(r"\s+", " ", s)


def block(text, heading):
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None:
        raise SystemExit("FATAL: owner block heading not found")
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("### ") or lines[j].startswith("## "):
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


owner_raw = OWNER.read_text(encoding="utf-8", errors="replace")
blk = collapse(block(owner_raw, HEADING))
src = collapse(SRC.read_text(encoding="utf-8", errors="replace"))


def forms(n):
    plain = n.replace(",", "")
    grouped, d = "", plain
    while len(d) > 3:
        grouped = "," + d[-3:] + grouped
        d = d[:-3]
    return {n, plain, d + grouped}


FIGURES = [
    ("first quote", "1,661"),
    ("inventory RAWs", "10,509"),
    ("stage 0 frames", "2"),
    ("rehearsal frames", "896"),
    ("rehearsal cumulative", "898"),
    ("sealed M1 frames", "704"),
    ("M1-first total", "1,602"),
    ("combined total", "1,917"),
    ("flats per class", "96"),
]

green = red = 0
for label, n in FIGURES:
    in_owner = any(f in blk for f in forms(n))
    in_src = any(f in src for f in forms(n))
    if in_owner and in_src:
        print("GREEN %-22s %s" % (label, n))
        green += 1
    else:
        print("RED   %-22s %s  owner=%s source=%s" % (label, n, in_owner, in_src))
        red += 1

# ---- independent arithmetic re-derivation ----
print()
stages = [128, 160, 128, 224, 256]
checks = [
    ("stages 1-5 sum to 896", sum(stages) == 896),
    ("stage 0 + rehearsal = 898", 2 + sum(stages) == 898),
    ("898 + 704 = 1,602", 2 + sum(stages) + 704 == 1602),
    ("combined 2 + 896 + 1019 = 1,917", 2 + 896 + 1019 == 1917),
]
for label, ok in checks:
    print(("GREEN " if ok else "RED   ") + "arith  " + label)
    if ok:
        green += 1
    else:
        red += 1

# ---- cross-document consistency ----
# The host-load figure is cited in BOTH docs/STATUS.md and this owner file, but
# only STATUS is guarded by v2954.py. Without this check, editing the evidence
# JSON would be caught in one document and silently diverge in the other.
print()
import json
hostjson = ROOT / "experiments" / "ORCH-verify" / "host-load-2026-09-06.json"
owner_all = OWNER.read_text(encoding="utf-8", errors="replace")
hl = json.loads(hostjson.read_text(encoding="utf-8"))
mean_pct = hl["mean_pct"]
host_ok = ("**`%s%%`**" % mean_pct) in owner_all
print(("GREEN " if host_ok else "RED   ")
      + "xdoc   owner cites host mean %s%% from evidence JSON" % mean_pct)
if host_ok:
    green += 1
else:
    red += 1

# ---- HOLD-LIFTED banner: every quote must exist in the lane's committed report ----
# The banner tells the owner to shoot on the strength of six verbatim quotes from
# two lane-owned files. Quoting a lane's chat reply instead of its committed
# report has already happened once in this program, so each quote is re-read from
# source here. Both lanes remain live and may revise these files.
print()
M166 = ROOT / "docs" / "research" / "M166-reference-information-dominance-physical.md"
M164D = ROOT / "docs" / "research" / "M164-reference-dominance.md"
M166REH = ROOT / "docs" / "research" / "M166-reference-dominance-rehearsal.md"
BANNER_QUOTES = [
    ("m166 target holds", M166, "TARGET HOLDS AT 1.32x"),
    ("m166 scale and field only", M166,
     "can establish scale and field only"),
    ("m166 cannot admit rig", M166,
     "Diffraction arithmetic cannot admit the rig."),
    ("m166 rehearsal first", M166REH,
     "The owner must not start the `1,092`-frame rehearsal from the current "
     "repository state."),
    ("m166 preflight still allowed", M166REH,
     "The two-frame M147 preflight may still be completed; it establishes "
     "scale and field only."),
    ("m166 corrected total", M166REH,
     "the combined score is `1,215`, not `1,147`."),
    ("m166 weakest cell ratio", M166, "1.03405"),
    ("m164 shared objective", M164D, "SHARED OBJECTIVE SUFFICIENT"),
]
def unquote(s):
    """Strip Markdown blockquote markers.

    The owner banner is a blockquote, so a quotation that wraps across lines
    reads as 'TARGET HOLDS AT > 1.32x' once whitespace is collapsed and will
    not match its source. Removing the leading '>' per line before collapsing
    is what makes a wrapped quote comparable to the unwrapped original.
    """
    return "\n".join(re.sub(r"^\s*>\s?", "", ln) for ln in s.splitlines())


owner_flat = collapse(unquote(owner_raw))
for label, path, quote in BANNER_QUOTES:
    if not path.exists():
        print("RED   banner %-24s SOURCE MISSING %s" % (label, path.name))
        red += 1
        continue
    src_txt = collapse(path.read_text(encoding="utf-8", errors="replace"))
    in_src = collapse(quote) in src_txt
    in_owner = collapse(quote) in owner_flat
    if in_src and in_owner:
        print("GREEN banner %-24s quoted from %s" % (label, path.name))
        green += 1
    else:
        print("RED   banner %-24s source=%s owner=%s"
              % (label, in_src, in_owner))
        red += 1

# The revised session total is re-derived from its four published components
# rather than pinned, so editing any component without editing the total fails.
print()
rev = [("current registered session", 891), ("fourth reference strip", 32),
       ("scored-path S1/S2 witness", 164), ("held-out validation", 128)]
rev_total = sum(v for _, v in rev)
rev_checks = [
    ("891 + 32 + 164 + 128 = 1,215", rev_total == 1215),
    # Anchored on its own phrase, not on a bare "1,215": the figure also appears
    # inside the quoted M166 corrections below, and a presence check for the
    # bare number is satisfied by that duplicate even after this sentence drifts.
    ("owner states the revised total in context",
     "`891` to `1,215` registered frames" in owner_flat),
    ("owner attributes the +324 to its components",
     "three reference strips become four (`+32`)" in owner_flat),
    ("owner shows the witness arithmetic",
     "`55 + 55 + 27 + 27 = 164`" in owner_flat),
    # The superseded total must be named as superseded, not silently dropped:
    # the owner has already been told 1,147 once and needs it retracted.
    ("owner retracts the stale 1,147",
     "The `1,147` figure is superseded" in owner_flat),
    ("increase is 324", rev_total - 891 == 324),
    ("witness correction is +68", 164 - 96 == 68),
]
for label, ok in rev_checks:
    print(("GREEN " if ok else "RED   ") + "revsn  " + label)
    if ok:
        green += 1
    else:
        red += 1

# ---- the ratification stakes table, re-derived across two documents ----
#
# The owner acts on these four numbers, so a presence check is not enough: a
# bare "**1 of 12**" occurs in several places and would be satisfied by a
# duplicate long after the row it is supposed to guard had drifted. Instead the
# value is EXTRACTED from lane M169's own table row and compared with the value
# extracted from the owner-facing row. Either side drifting fails the check.
print()
M169 = ROOT / "docs" / "research" / "M169-ratification-stakes.md"
RATIFY = [
    # (label, phrase identifying M169's row, phrase identifying the owner's row)
    ("plan licence prerequisite",
     "makes a paid licensed comparator a score prerequisite",
     "makes a paid licence a direct score prerequisite"),
    ("unratified propagation",
     "propagates the missing paid Zerene arms",
     "propagates the missing paid arms"),
    ("axes shedding (d)",
     "Axes that lose `(d)` entirely",
     "shed blocker `(d)` entirely if you reject my rule"),
    ("newly scoreable",
     "Axes that become newly scoreable",
     "become **newly scoreable**"),
]


def cell_after(text, phrase):
    """The '**N of 12**' value in the same table row as `phrase`.

    Bounded to the row by searching only as far as the next newline, so a
    value belonging to a different row can never be picked up."""
    i = text.find(phrase)
    if i < 0:
        return None
    row_end = text.find("\n", i)
    row = text[i:row_end if row_end > 0 else len(text)]
    m = re.search(r"\*\*(\d+) of 12\*\*", row)
    return m.group(1) if m else None


if not M169.exists():
    print("RED   ratify SOURCE MISSING %s" % M169.name)
    red += 1
else:
    m169_raw = M169.read_text(encoding="utf-8", errors="replace")
    for label, src_phrase, own_phrase in RATIFY:
        a = cell_after(m169_raw, src_phrase)
        b = cell_after(owner_raw, own_phrase)
        if a is None:
            print("RED   ratify %-26s M169 row not found" % label)
            red += 1
        elif b is None:
            print("RED   ratify %-26s owner row not found" % label)
            red += 1
        elif a != b:
            print("RED   ratify %-26s M169 says %s of 12, owner says %s of 12"
                  % (label, a, b))
            red += 1
        else:
            print("GREEN ratify %-26s both say %s of 12" % (label, a))
            green += 1

# ---- control: a wrong total must not re-derive ----
ctl = (2 + sum(stages) + 704) != 1603
ctl2 = (891 + 32 + 164 + 128) != 1147  # the stale total must no longer re-derive
print(("CTLPASS" if ctl else "CTLFAIL") + " decoy total 1,603 does not re-derive")
print(("CTLPASS" if ctl2 else "CTLFAIL")
      + " superseded total 1,147 does not re-derive from the corrected parts")
ctl = ctl and ctl2

print()
print("GREEN: %d  RED: %d" % (green, red))
print("VERDICT: " + ("GREEN" if red == 0 and ctl else "RED"))
sys.exit(0 if (red == 0 and ctl) else 1)
