"""Fold M122: the blotch has a confirmed mechanism, and the fix is still refused.

Facts 1675-1681, disciplines 854-856.

This is the first confirmed mechanism for a defect the owner can SEE, and the
first result tonight that is not a refusal all the way down. It still ends in
KEEP-OFF, and the reason it ends there is the interesting part.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits, "no section heading matching %r" % pattern
    start = hits[-1]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _re.match(r"^#{1,3} ", lines[i]):
            end = i
            break
    return start, end


def insert_after_fact_row(number, block):
    hits = [i for i, l in enumerate(lines) if l.startswith("| %d |" % number)]
    assert len(hits) == 1, "fact row %d appears %d times" % (number, len(hits))
    for k, text in enumerate(block):
        lines.insert(hits[0] + 1 + k, text)
    return "fact table"


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times in %s" % (
        number, len(hits), lines[start].strip())
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_FACTS = [
    (
        1675,
        "MEASURED",
        "M122",
        "**THE BLOTCH DEFECT THE OWNER CAN SEE TRACKS MEASURED INTER-FRAME LEVEL "
        "DRIFT.** Spearman **rho = +0.7011** between per-stack drift `Dpp` and "
        "blotch improvement `1 - B12`, one-sided **p = 0.0035** over **20 000 label "
        "permutations** (MC se ~0.0004), **n = 14** stacks, **2.5 null-sd** from zero "
        "against a permutation null sd of 0.2778. **This is the project's first "
        "confirmed mechanism for a defect the owner reported by eye.** Registered "
        "power check, declared in advance so it could not be invoked selectively: "
        "IQR(`B12`) = 0.0323 and IQR(`Dpp`) = 7.087 pp, both clearing their floors -- "
        "**the corpus carried real variation in both axes, so the test had power to "
        "fail.**",
    ),
    (
        1676,
        "MEASURED",
        "M122",
        "**THE REGISTERED CONFOUND IS NOT ONLY REFUTED, IT WAS SUPPRESSING THE "
        "EFFECT.** The pre-registered worry was that a stack's baseline "
        "high-frequency content `hf0` drives both axes -- that the result is merely "
        "*smooth backgrounds are smooth*. Measured: **rho(`Dpp`, `hf0`) = -0.029** "
        "(no relationship at all), and the **partial rho(`Dpp`, 1-`B12`) "
        "controlling for `hf0` = +0.7550**, i.e. **stronger with the baseline "
        "removed**, against a registered "
        "floor of +0.20. A confound that was actually driving the correlation would "
        "have shrunk it toward zero; this one was hiding it.",
    ),
    (
        1677,
        "MEASURED",
        "M122",
        "**THE CODE'S OWN FITTED CORRECTION INDEPENDENTLY MEASURES THE SAME PHYSICAL "
        "QUANTITY.** **rho(`Dpp`, gain span - 1) = +0.7714**: the per-frame gain the "
        "photometric solver fits, computed inside `crates/` and never shown the "
        "drift estimator, tracks a drift number computed outside it by M24's "
        "published method. Two independent instruments, one physical cause. This is "
        "the corroboration that lifts the mechanism above a single correlation.",
    ),
    (
        1678,
        "MEASURED",
        "M122",
        "**THE EFFECT IS SIGNED AND CONDITIONAL, WHICH IS WHY THE DEFAULT STILL DOES "
        "NOT MOVE.** `B12` = laplacian-RMS(photometric) / laplacian-RMS(default) in "
        "smooth background windows, so **below 1 is less blotch**. At the top of the "
        "drift range `--photometric` is a large win -- `tweezers-cpl` at 13.765 % "
        "drift reads **0.7102, a 29 % reduction in blotch**; `coffee-bean` 0.9052; "
        "`bee-1-cpl` 0.9485. At the bottom it does **harm** -- **`bee-3-cpl` at "
        "1.629 % drift reads 1.0638, 6.4 % WORSE**, and `113MSDCF` reads 1.0699. "
        "Pre-registered criterion **P3 (no stack may exceed 1.03) FAILS on exactly "
        "those two**, so the verdict is **KEEP-OFF** with P1, P2, P4, P5 and the "
        "power check all passing. **The mechanism is confirmed and the fix is still "
        "refused, and those are two different questions.**",
    ),
    (
        1679,
        "MEASURED",
        "M122",
        "**THE INSTRUMENT WAS COMMISSIONED AGAINST TWO PRIOR MILESTONES BEFORE IT WAS "
        "TRUSTED.** (a) Its A0/A1 arms are **byte-identical to M116's published "
        "SHA-256s, 3/3**, from a warp map it solved **independently in an isolated "
        "cache dir** -- the render path is reproduced, not merely re-run. (b) Its "
        "drift estimator reproduces **M24's four published numbers and M93's** with "
        "deltas of **+0.001, -0.002, +0.001, -0.004 pp**. Registration was **frozen "
        "per subject** into a sidecar and both arms rendered with `STREHL_WARPMAP` "
        "pinned, so **the arms differ only in `--photometric`** and the solve cannot "
        "confound the comparison.",
    ),
    (
        1680,
        "MEASURED",
        "M122",
        "**NEITHER ARM CHOOSES THE PIXELS IT IS JUDGED ON.** The 12 scoring windows "
        "are selected from the **symmetric mean `(A0+A1)/2`** -- brightest 20 % pool, "
        "then the 12 lowest `w[::8,::8].std()` -- rather than from either arm. A "
        "variant that selected windows separately per arm **fails** (0.8846 on "
        "`tweezers-cpl`), and M122 reports that the registered criterion is the "
        "symmetric one and the separated variant's failure **is a defect in the "
        "variant**, not a result.",
    ),
    (
        1681,
        "MEASURED",
        "M122",
        "**THE STATISTICAL CLAIM WAS CONFIRMED BY EYE AT COORDINATES A PRIOR FACT "
        "NAMED BY HAND.** The rule-based window selection independently landed on "
        "both coordinates fact 1638 cites. At `tweezers-cpl` **x=912 y=400** under a "
        "single shared stretch, the default arm shows the soft oval patches and the "
        "photometric arm shows **none** (**hf 78.7 -> 49.7**). Discipline 572 says a "
        "visual impression is a hypothesis with a milestone attached; this is the "
        "rarer converse -- **a measured effect returning to the eye and being "
        "confirmed at a location chosen by rule rather than by the author.**",
    ),
]

NEW_DISCIPLINES = [
    (
        854,
        "**A confirmed mechanism and a shippable fix are two different verdicts, and "
        "conflating them is how a correlation gets promoted into a default.** M122 "
        "established the blotch's cause at **rho = +0.70, p = 0.0035**, with the "
        "confound refuted and the code's own fitted gain corroborating it -- and "
        "still returned **KEEP-OFF**, because one pre-registered no-harm criterion "
        "failed on two stacks. *Why does this defect happen* is answered by a "
        "correlation; *should this correction be on for everyone* is answered by the "
        "worst stack, not the average one. **Report both, and never let the strength "
        "of the first argue for the second.**",
    ),
    (
        855,
        "**When a confound is registered in advance, report the partial correlation "
        "even when the raw one already passes -- and read its direction.** M122's "
        "partial came back **+0.7550 against a raw +0.7011**: the confound was "
        "*suppressing* the effect, not creating it. That is information a bare "
        "'confound refuted' would have destroyed, and it is only available because "
        "the worry was written down before the numbers existed. **A confound that "
        "shrinks the effect and a confound that hides it look identical until you "
        "compute the partial.**",
    ),
    (
        856,
        "**In a two-arm image comparison, choose the scored pixels from the "
        "symmetric mean of both arms, so neither arm selects the region it is judged "
        "on.** M122 pooled windows on `(A0+A1)/2`; the variant that selected per arm "
        "produced a different verdict on `tweezers-cpl`. Selecting on one arm lets "
        "the metric find that arm's quietest pixels, which is a search for a "
        "favourable ROI dressed as a measurement -- the same family as fact 1601's "
        "700x1100 window and discipline 849's systematic sign.",
    ),
]

log = []
for number, status, source, text in NEW_FACTS:
    row = "| %d | %s | %s | %s |" % (number, status, source, text)
    assert row.count("|") == 5, "fact %d: pipe count %d" % (number, row.count("|"))
    bare = _re.sub(r"`[^`]*`", "", row)
    assert bare.count("**") % 2 == 0, "fact %d: unbalanced bold" % number
    for ch in row:
        assert ch == "\t" or ord(ch) >= 32, "fact %d: control char" % number
    log.append((number, row))

dlog = []
for number, text in NEW_DISCIPLINES:
    entry = "%d. %s" % (number, text)
    bare = _re.sub(r"`[^`]*`", "", entry)
    assert bare.count("**") % 2 == 0, "discipline %d: unbalanced bold" % number
    for ch in entry:
        assert ch == "\t" or ord(ch) >= 32, "discipline %d: control char" % number
    dlog.append((number, entry))

# All assertions above run before any mutation, so a failed fold leaves
# SYNTHESIS.md untouched.
prev = 1674
for number, row in log:
    where = insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d -> %s" % (number, where))

dprev = 853
for number, entry in dlog:
    where = insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d -> %s" % (number, where))

out = "\n".join(lines)
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number
assert "M122" in out

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
