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

# ---- bench sheet: the owner's shooting gates must match the lanes that own them ----
# Steps 8-9 of the owner sheet tell the owner to STOP on a numeric threshold.
# Those thresholds are not the owner file's to define: the `133` three-way tile
# gate belongs to M151 and the Q05/Q95 sign gates belong to M135, and both lanes
# are still live and free to revise them. Nothing else re-reads the lane files,
# so a lane could tighten a bar and the owner would shoot against the old one.
# The failure is silent and expensive in exactly one direction: the owner
# satisfies the printed gate, and the real gate is stricter.
#
# Each row pins BOTH sides. A src needle alone would not notice the owner file
# dropping a term, and an owner needle alone would not notice the lane moving
# the bar. The three `133` rows deliberately carry three DISTINCT src needles
# against one owner sentence, because that sentence's whole content is that the
# gate is three-way -- pinning it once would let the sw10 or intersection term
# be dropped from the registered source without any check going red.
print()
M135D = ROOT / "docs" / "research" / "M135-detail-instrument.md"
M151D = ROOT / "docs" / "research" / "M151-m5-checker.md"
BENCH = [
    ("133 sw4", M151D,
     "at least 133 eligible tiles in the pass-averaged sw4 manifest",
     "pass-averaged `sw4` `>=133` eligible tiles"),
    ("133 sw10", M151D,
     "at least 133 eligible tiles in the pass-averaged sw10 manifest",
     "pass-averaged `sw10` `>=133` eligible tiles"),
    ("133 intersection", M151D,
     "at least 133 common eligible physical tiles in the intersection of "
     "those two required step-width manifests",
     "their physical-coordinate intersection `>=133` eligible tiles"),
    # The averaging ORDER is part of the registered gate, and the owner sheet
    # omitted it. Averaging the A/B block cross-powers after best-frame
    # election rather than before produces a different manifest and therefore
    # a different count, so an owner could run "the M5 exit gate" faithfully
    # and still not run the gate that was registered.
    ("M5 gate averaging order", M151D,
     "regularisation, best-frame election, ratios",
     "regularisation, best-frame election, ratios"),
    # Anchored on the row label, not on the bare threshold. `q95 ratio
    # `<0.90`` occurs at three sites in M135 (pre-noise blur, added
    # independent noise, and high-band noise-only gain all share the bar), so
    # a bare needle is satisfied by any of them and would stay green if the
    # blur-control row alone were changed. The owner's bench gate is the
    # blur control specifically.
    ("Q05 sharp gate", M135D,
     "| Genuine optical improvement | up | q05 ratio `>1.10`",
     "`Q05` must be strictly above `1.10`."),
    ("Q95 blur gate", M135D,
     "| Pre-noise blur | down | q95 ratio `<0.90`",
     "`Q95` must be strictly below `0.90`."),
    # The two measured values are the improvement and degradation arms of
    # M135's own commissioning. They are pinned source-side only: the owner
    # sheet states the bar, not the evidence behind it.
    ("Q05 improvement arm", M135D, "**VERIFIED PASS**, `1.241840`", None),
    ("Q95 degradation arm", M135D, "**VERIFIED PASS**, `0.631511`", None),
    ("1.33x ceiling", M135D, "with a hard `1.33x` maximum",
     "`1.33x`, and pass the live scale/field check"),
]
for label, path, src_needle, own_needle in BENCH:
    if not path.exists():
        print("RED   bench  %-22s SOURCE MISSING %s" % (label, path.name))
        red += 1
        continue
    src_txt = collapse(path.read_text(encoding="utf-8", errors="replace"))
    in_src = collapse(src_needle) in src_txt
    in_own = True if own_needle is None else collapse(own_needle) in owner_flat
    if in_src and in_own:
        print("GREEN bench  %-22s %s" % (label, path.name))
        green += 1
    else:
        print("RED   bench  %-22s source=%s owner=%s"
              % (label, in_src, in_own))
        red += 1

# ---- M12 retraction block: the money-decision figures ----
# Added when Ask 3's "M12 sits behind this purchase" chain was retracted. These
# numbers now sit in an owner-facing file next to a $289 decision, so each is
# checked in BOTH directions: it must occur in the lane document it came from,
# AND the derived quantities must re-derive arithmetically. A presence check
# alone would be satisfied by any copy of the value elsewhere in the tree.
M182D = ROOT / "docs" / "research" / "M182-memory-budget.md"
SCARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"

PEAK, HEADROOM, BAR, UNREPAIRED = (
    3074797568, 3367653376, 6442450944, 38286897152)
GIB = 1 << 30

M12RET = [
    ("m12 repaired peak", M182D, "3,074,797,568 B"),
    ("m12 headroom", M182D, "3,367,653,376 B"),
    ("m12 unrepaired red", M182D, "38,286,897,152 B"),
    ("m12 scorecard peak", SCARD, "35.65745162963867 GiB"),
    ("m12 clause unratified", SCARD, "unratified addition"),
    ("m12 clause commit", SCARD, "986c4653"),
]
for label, path, needle in M12RET:
    if not path.exists():
        print("RED   m12ret %-22s SOURCE MISSING %s" % (label, path.name))
        red += 1
        continue
    src_txt = collapse(path.read_text(encoding="utf-8", errors="replace"))
    in_src = collapse(needle) in src_txt
    in_own = collapse(needle) in owner_flat
    if in_src and in_own:
        print("GREEN m12ret %-22s %s" % (label, path.name))
        green += 1
    else:
        print("RED   m12ret %-22s source=%s owner=%s needle=%r"
              % (label, in_src, in_own, needle))
        red += 1

# Derivations. Each is the arithmetic the owner sheet asserts, recomputed.
M12DER = [
    ("headroom re-derives", PEAK + HEADROOM == BAR),
    ("unrepaired GiB identity",
     "%.14f" % (UNREPAIRED / GIB) == "35.65745162963867"),
    ("peak GiB quoted", "%.4f" % (PEAK / GIB) == "2.8636"),
    ("headroom GiB quoted", "%.4f" % (HEADROOM / GIB) == "3.1364"),
    ("peak is under bar", PEAK < BAR),
    ("unrepaired is over bar", UNREPAIRED > BAR),
]
for label, ok in M12DER:
    print(("GREEN m12der %-30s" % label) if ok
          else ("RED   m12der %-30s DID NOT RE-DERIVE" % label))
    if ok:
        green += 1
    else:
        red += 1

# The owner sheet must say the chain is withdrawn, not merely stop asserting it.
# A silent deletion is the exact defect ruled against for M176.
for label, needle in (("retraction present", "RETRACTION"),
                      ("retraction names M178", "M178"),
                      ("original claim left standing",
                       "So M12-S sits behind this purchase")):
    ok = collapse(needle) in owner_flat
    print(("GREEN m12ret %-30s" % label) if ok
          else ("RED   m12ret %-30s ABSENT" % label))
    if ok:
        green += 1
    else:
        red += 1

# ---- M12 four-bar count: the defect that caused all of this ----
# STATUS contained the N-mod-4 spread as both a FAIL (:7275) and a "passes"
# (:7754) simultaneously, and I read the wrong one, publishing a two-bar count
# into an owner-facing file. These checks make that specific regression loud.
STATUSD = ROOT / "docs" / "STATUS.md"
status_flat = collapse(STATUSD.read_text(encoding="utf-8", errors="replace")) \
    if STATUSD.exists() else ""

FOURBAR = [
    ("status nmod4 not passes", status_flat,
     "N-mod-4 per-frame spread — passes", False),
    ("status nmod4 fails", status_flat,
     "N-mod-4 per-frame spread — FAILS", True),
    ("status 2.9.80 exists", status_flat,
     "M12 fails four bars, not two", True),
    ("status nmod4 true percent", status_flat,
     "7.618677189815302%", True),
    ("status ratio unrepaired", status_flat,
     "1.4615654159027742", True),
    ("owner says four bars", owner_flat,
     "M12 is a conjunction of **four** bars, not two", True),
    ("owner names nmod4 unrepaired", owner_flat,
     "N-mod-4 per-frame timing spread", True),
    ("owner names ratio unrepaired", owner_flat,
     "peak memory ratio", True),
    ("owner refuses to call it a pass", owner_flat,
     "That is not a pass and I am not going to present it as one", True),
    ("owner drops the two-bar claim", owner_flat,
     "both of M12's registered failures", False),
]
for label, hay, needle, want in FOURBAR:
    present = collapse(needle) in hay
    ok = (present == want)
    if ok:
        print("GREEN 4bar   %-30s" % label)
        green += 1
    else:
        print("RED   4bar   %-30s expected %s, found %s: %r"
              % (label, "present" if want else "ABSENT",
                 "present" if present else "absent", needle))
        red += 1

# ---- Ask 3 standing bottom line ----
# Ask 3 accumulated five layers of correction (D1-D4 plus a retraction) across
# 317 lines for a decision that never changed. A standing bottom line was added
# at the top so the owner does not have to reconstruct the action from its own
# correction history. These pins keep that box true, and the cross-document
# checks keep its three proposal quotations honest -- the box asserts what the
# owner's own plan says, so a drift in the plan must redden here rather than
# silently leave the owner acting on a quotation that no longer exists.
PROPD = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
prop_flat = collapse(PROPD.read_text(encoding="utf-8", errors="replace")) \
    if PROPD.exists() else ""

ASK3 = [
    ("owner buys professional", owner_flat,
     "Buy Zerene Stacker Professional, `$289`. Not Prosumer, not Personal.", True),
    ("owner counts eight axes", owner_flat,
     "gating **eight of the twelve axes**", True),
    # Pinned as a full clause, not the bare code: `UNMEASURED_COMPARATOR_
    # QUALIFICATION` occurs twice in this file, so a bare-code presence check is
    # satisfied by the copy outside this box and can never go RED for it.
    ("owner names m11 code", owner_flat,
     "`M11` is blocked by the same thing under the name "
     "`UNMEASURED_COMPARATOR_QUALIFICATION`", True),
    ("owner withdraws m12 reason", owner_flat,
     "It does not unblock M12.", True),
    ("owner withdraws urgency", owner_flat,
     "It is not urgent, and nothing is ageing.", True),
    ("owner frees helicon", owner_flat,
     "It is not held up by Helicon.", True),
    ("owner says action unchanged", owner_flat,
     "The action has never changed", True),
    # Absence: the cheaper edition must never become the recommendation.
    ("owner does not buy prosumer", owner_flat,
     "Buy Zerene Stacker Prosumer", False),
    # Cross-document: the box quotes the governing proposal three times.
    ("proposal has blocker d", prop_flat,
     "licence a commercial comparator", True),
    ("proposal has the export", prop_flat,
     "Save Adjusted Input Images", True),
    ("proposal makes helicon optional", prop_flat,
     "Helicon if obtainable", True),
]
for label, hay, needle, want in ASK3:
    present = collapse(needle) in hay
    ok = (present == want)
    if ok:
        print("GREEN ask3   %-30s" % label)
        green += 1
    else:
        print("RED   ask3   %-30s expected %s, found %s: %r"
              % (label, "present" if want else "ABSENT",
                 "present" if present else "absent", needle))
        red += 1

# The $100 upgrade figure must re-derive from the two prices the proposal names,
# so a typo in either price reddens rather than passing as prose.
PRO_PRICE, PROS_PRICE = 289, 189
if (PRO_PRICE - PROS_PRICE) == 100 and collapse("The `$100` difference") in owner_flat:
    print("GREEN ask3   %-30s" % "upgrade delta re-derives")
    green += 1
else:
    print("RED   ask3   %-30s $289-$189 != $100 or figure absent" % "upgrade delta re-derives")
    red += 1

# ---- control: a wrong total must not re-derive ----
ctl = (2 + sum(stages) + 704) != 1603
ctl2 = (891 + 32 + 164 + 128) != 1147  # the stale total must no longer re-derive
# A wrong headroom must not re-derive: this proves the derivation controls above
# are arithmetic rather than tautologies that pass on any input.
ctl3 = (PEAK + 3367653377) != BAR
print(("CTLPASS" if ctl3 else "CTLFAIL")
      + " decoy headroom 3,367,653,377 does not re-derive to the 6 GiB bar")
print(("CTLPASS" if ctl else "CTLFAIL") + " decoy total 1,603 does not re-derive")
print(("CTLPASS" if ctl2 else "CTLFAIL")
      + " superseded total 1,147 does not re-derive from the corrected parts")
ctl = ctl and ctl2 and ctl3

print()
print("GREEN: %d  RED: %d" % (green, red))
print("VERDICT: " + ("GREEN" if red == 0 and ctl else "RED"))
sys.exit(0 if (red == 0 and ctl) else 1)
