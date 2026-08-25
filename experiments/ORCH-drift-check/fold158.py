"""ORCH fold 158: V-FOLD's audit of facts 1560-1665.

The single most important fold of the night: it measures MY OWN error direction
rather than assuming it. 8 of 25 audited facts non-SAFE, all 8 strengthening.

Amends 1568 (matrix operation order -- CRITICAL, wrong in six files),
1571 (+-15 ppm is a cross-experiment splice), 1587 (headline overstated),
and inserts the audit result as new facts.
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

# ---------------------------------------------------------------- amendments

# --- fact 1568: the matrix itself is wrong, in six files.
OLD_1568 = (
    "so output red carries camera green at **10.4 %** and output green carries "
    "camera red at **20.3 %**"
)
NEW_1568 = (
    "so output red carries camera green at **27.4 %** and output green carries "
    "camera red at **7.7 %**"
)
assert text.count(OLD_1568) == 1, f"1568 anchor: {text.count(OLD_1568)}"
text = text.replace(OLD_1568, NEW_1568, 1)

# Append the amendment note to fact 1568's row.
ANCHOR_1568 = "| 1568 | MEASURED | M113 |"
i = text.index(ANCHOR_1568)
eol = text.index("\n", i)
row = text[i:eol]
assert row.rstrip().endswith("|"), "1568 row does not end in a pipe"
AMEND_1568 = (
    " **AMENDED by fact 1721 (V-FOLD, 2026-08-25): the matrix quoted in this row "
    "was WRONG, and the numbers above are the corrected ones.** The crate "
    "computes `inv(rownorm(A@S))` (`color.rs:191-208`: build, then row-normalise "
    "at step 2, then invert at step 3); every corpus copy quoted "
    "`rownorm(inv(A@S))`. Those are different operations. The percentages were "
    "not merely imprecise, they were **swapped and wrong in magnitude** "
    "(originally 10.4 % / 20.3 %). ORCH reproduced the correction independently "
    "and it agrees with `color.rs:221`'s own doc comment to 3 d.p. "
    "(computed green row `[-0.115165, 1.488971, -0.373806]` vs documented "
    "`[-0.115, +1.489, -0.374]`) -- **the shipped code had been documenting the "
    "right value the whole time and the corpus disagreed with it.** "
    "**The conclusion of this row is UNCHANGED and if anything strengthened**: "
    "the green-into-red leak the sRGB measurement was contaminated by is 27.4 %, "
    "not the 10.4 % originally claimed."
)
text = text[:eol] + AMEND_1568 + text[eol:]

# --- fact 1571: +-15 ppm is spliced from a different experiment.
OLD_1571 = (
    "is flat within **+/-15 ppm** from r = 0.11 to 0.87 on `couch-fibers-cpl` "
    "(bootstrap sd 8-23 ppm)"
)
NEW_1571 = (
    "is flat from r = 0.11 to 0.87 on `couch-fibers-cpl` **(the tolerance "
    "originally quoted here, `+/-15 ppm` with bootstrap sd 8-23 ppm, is "
    "RETRACTED -- see fact 1723)**"
)
assert text.count(OLD_1571) == 1, f"1571 anchor: {text.count(OLD_1571)}"
text = text.replace(OLD_1571, NEW_1571, 1)

# --- fact 1587: the headline is broader than the measurement.
OLD_1587 = "AND NO OVERSHOOT ANYWHERE.**"
NEW_1587 = (
    "AND NO OVERSHOOT ANYWHERE.** **HEADLINE REFUTED IN ITS SECOND CLAUSE by "
    "fact 1724 (V-FOLD): the radial rates below are exact, but "
    "`no overshoot ANYWHERE` is not what M110 measured.** M110 section 16.2 "
    "claimed only that there is **no discontinuity at the boundary**. Artefact "
    "`overshoot_pct` reaches **18.82 %**, and the real null runs "
    "**4.68-25.73 %** -- the `0.00 % exactly` quoted below is the "
    "**off-vs-off** control, which is a different thing from a null with the "
    "correction on. The no-discontinuity finding stands; the universal "
    "no-overshoot claim was ORCH's widening of it."
)
assert text.count(OLD_1587) == 1, f"1587 anchor: {text.count(OLD_1587)}"
text = text.replace(OLD_1587, NEW_1587, 1)

# ---------------------------------------------------------------- new facts

NEW_FACTS = """| 1721 | MEASURED | V-FOLD | **THE ORCHESTRATOR'S FOLD WAS AUDITED, AND ITS ERRORS ARE NOT SYMMETRIC: 8 OF 25 AUDITED FACTS ARE NON-SAFE AND ALL 8 STRENGTHEN THE CLAIM.** V-FOLD re-derived 25 facts in the range 1560-1665 from artefacts and by re-running the producing scripts. **8 non-SAFE, 0 of them weakening.** Under a fair-coin null that direction alone is **p = 0.0039**. Discipline 849 is therefore **CONFIRMED, not overstated**. Crucially, the auditor **looked for the weakening error and found two candidates, then dissolved both**: facts 1579 (an undercount) and 1592 (`returns nothing`) are false *as of today* but were **true when folded** -- `git log` dates the code they describe to **1 h 53 m** and **2 h 28 m AFTER** their respective folds (`identity.rs` added `43cee3b` 19:52:24 vs fold `a91be3e` 17:59:11; `STREHL_ROBUST_ELECTION` added `e028113` 20:00:49 vs fold `63f1799` 17:32:08). Both scored SAFE-at-fold. **The asymmetry survived a genuine search for its counterexample**, which is what distinguishes it from a selection effect in the auditor's sample. Source: `docs/research/V-FOLD-audit.md`, commit `c60f176`. |
| 1722 | MEASURED | V-FOLD | **THE FAILURE MODE IS SCOPE INFLATION INSIDE CORRECTLY-LABELLED ROWS, SO A LABEL AUDIT CATCHES NONE OF IT.** V-FOLD checked specifically for `ARGUED -> MEASURED` upgrades across the audited range and found **none** -- the one row that looked like a candidate (fact 1594) is ORCH labelling **its own** claim ARGUED, with reasons. Every one of the 8 defects sits in a row whose MEASURED/ARGUED tag is **correct**; what is wrong is the **scope of the sentence**, not its epistemic label. Concretely: a real rate measured at **one window of six** stated unqualified (1634); a tolerance from a **different experiment** (1571); a control's `0.00 %` presented as the null (1587); an exception list dropped (1658). **This kills the cheap defence.** ORCH cannot audit its own folding by re-reading labels, because the labels are right; only re-derivation from the artefact catches these. |
| 1723 | MEASURED | V-FOLD | **A TOLERANCE WAS SPLICED IN FROM A NEIGHBOURING EXPERIMENT, AND IT UNDERSTATED THE REAL SCATTER BY 5x.** The `+/-15 ppm` flatness quoted in fact 1571 and repeated into `docs/captures-needed.md` **occurs nowhere in `M113-spectral.md`**, the report it was attributed to; it came from `M113-ca.md`, **n = 1, a different experiment in the contaminated space**. The bootstrap sd at the innermost ring (r = 0.11) is **80.0 ppm** (`c10_rings.json`), not the 8-23 ppm claimed. The **shape** finding survives on the artefact; **the tightness claimed for it does not.** This is the exact failure mode fact 1595 already named, occurring afterwards, in the one row the owner's brief depended on -- **a discipline written down is not a discipline in force.** Corrected in the brief at `ce022ae`. |
| 1724 | MEASURED | V-FOLD | **AN `--srgb` MEASUREMENT REACHED SHIPPED CODE AS A QUALITY CLAIM.** `crates/strehl-raw/src/identity.rs`'s module doc quotes the **61.0 % / 58.7 %** chroma reduction verbatim as "the project's best-measured quality win", **unqualified**. Its source is `experiments/M110-sheet/sheet.py:262`, which renders with `--srgb` -- and `main.rs:116` says of that flag, in the project's own words, **"For looking at, NOT for measuring."** V-FOLD re-derived the arithmetic from raw band DN and **confirms the numbers**; what is refuted is the **space** they were measured in, for a **cross-channel** quantity, which is precisely the defect fact 1568 exists to record. The contamination therefore propagated *from* the corpus *into* the crate. Read-only finding: V-FOLD did not modify `crates/`. |
| 1725 | MEASURED | V-FOLD | **A PRE-REGISTRATION SCRIPT PRINTED THE FACT-1568 DEFECT AND WAS NEVER FOLDED.** `experiments/M110-sheet/ca_matrix_prereg.py` computed and **printed** the disagreement between the corpus matrix and the crate's, and the disagreement went into no fact. The wrong matrix then propagated to **six files** (`SYNTHESIS.md` 1568, `M113-ca.md` section 1, `experiments/M113-ca/src/c8_linear.py:11-12`, `experiments/ORCH-drift-check/fold125.py:43-44`, `ca_gain.py:8-9`), while `crates/strehl-core/src/color.rs:221` carried the right value in a doc comment the whole time. **An output nobody reads is not a measurement**, and the corpus's own audit trail contained its refutation for an unknown number of hours before anyone looked. |
"""

NEW_DISCIPLINES = """877. **AUDIT THE FOLD BY RE-DERIVATION, NEVER BY RE-READING LABELS.** MEASURED against ARGUED is the wrong axis: fact 1722 measured **zero** mislabelled rows among 8 defects. The errors live in the **scope of the sentence** -- one window presented as six, a control presented as a null, a tolerance borrowed from the experiment next door. All four are invisible to a reader who trusts the label and only visible to one who reopens the artefact. Budget the expensive check: **25 facts re-derived beats 105 skimmed**, and V-FOLD chose exactly that trade deliberately.
878. **WHEN A CORPUS FACT QUOTES A DERIVED CONSTANT, THE SHIPPED CODE'S OWN DOC COMMENT IS THE CHECK.** Fact 1568's matrix was wrong for six files' worth of propagation while `color.rs:221` documented the correct green row the entire time. The cross-check cost ORCH **one `view` call and one script run**, and the script's output matched the doc comment to 3 d.p. If a fact quotes a matrix, a coefficient or a threshold that the code also computes, **read the code's own statement of it before folding** -- and if the two disagree, the code wins until proven otherwise.
879. **A SCRIPT THAT PRINTS A DISAGREEMENT AND IS NEVER FOLDED IS WORSE THAN ONE THAT WAS NEVER RUN**, because it creates a false record of having checked. `ca_matrix_prereg.py` (fact 1725) is the case. A pre-registration whose output is not read back into the corpus has performed the ceremony of falsification without its substance.
880. **BEFORE QUOTING A TOLERANCE, CONFIRM THE EXPERIMENT THAT PRODUCED IT.** `+/-X ppm` reads like a property of the finding and is in fact a property of **one run** (fact 1723). The splice was undetectable by reading the sentence, and trivially detectable by grepping the cited report for the number -- which is exactly what `fold_check.py` rule 31b does, and rule 31b **postdates** the defect. Extend it: a tolerance must be found in the cited report, not merely somewhere in the corpus.
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    eol = txt.index("\n", i)
    return txt[: eol + 1] + block, txt[eol + 1 :]


head, tail = insert_after_fact_row(1720, NEW_FACTS, text)
text = head + tail

# Insert disciplines after entry 876.
m = re.search(r"^876\. .*?(?=\n\d+\. |\n## )", text, re.S | re.M)
assert m, "discipline 876 not found"
text = text[: m.end()] + "\n" + NEW_DISCIPLINES.rstrip() + text[m.end() :]

# ---------------------------------------------------------------- assertions

assert text != orig, "no change"
for n in (1721, 1722, 1723, 1724, 1725):
    assert text.count(f"| {n} | MEASURED | V-FOLD |") == 1, f"fact {n}"
for n in (877, 878, 879, 880):
    assert re.search(rf"^{n}\. \*\*", text, re.M), f"discipline {n}"

# The corrected matrix values must be present and the wrong ones gone from 1568.
i1568 = text.index("| 1568 |")
row1568 = text[i1568 : text.index("\n", i1568)]
assert "27.4 %" in row1568 and "7.7 %" in row1568, "1568 corrected values missing"
assert "camera green at **10.4 %**" not in row1568, "1568 stale value survives"

# 1571 must no longer assert the spliced tolerance as a live claim.
i1571 = text.index("| 1571 |")
row1571 = text[i1571 : text.index("\n", i1571)]
assert "flat within **+/-15 ppm**" not in row1571, "1571 stale tolerance survives"
assert "RETRACTED" in row1571, "1571 retraction missing"

# Pipe discipline on every new fact row.
for line in NEW_FACTS.strip().split("\n"):
    assert line.count("|") == 5, f"pipe count {line.count('|')}: {line[:80]}"
    stripped = re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, f"bold imbalance: {line[:80]}"

# Amended rows must still be single-line and pipe-clean.
for row in (row1568, row1571):
    assert row.count("|") == 5, f"amended row pipe count {row.count('|')}"
    stripped = re.sub(r"`[^`]*`", "", row)
    assert stripped.count("**") % 2 == 0, "amended row bold imbalance"

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold158 OK: facts 1721-1725, disciplines 877-880")
print("  amended 1568 (matrix 10.4/20.3 -> 27.4/7.7), 1571 (+-15ppm retracted), 1587 (headline)")

AMEND = AMEND_1568 + NEW_1571 + NEW_1587

