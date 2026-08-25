"""ORCH fold 170: the election-time masking KILL (M97 reading M123).

M97 was authorised an hour to run the kill-or-open test, found M123 had already
run it, and spent twenty minutes establishing that instead of duplicating it.
The KILL condition was met.

Sources: docs/research/M123-outlier-mask.md (commit 5bd4997),
docs/research/M97e-robust-election.md.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1770 | MEASURED | M123/M97 | **ELECTION-TIME MASKING IS KILLED ON BOTH CANDIDATE DISCRIMINATORS, AND THE PRE-REGISTERED KILL CONDITION WAS MET.** ORCH pre-registered two outcomes before the test: if the statistic fires harder on the stationary stack too, the direction is dead. It does. `ShiftFree` gates **29.55 %** of the stationary trap `109MSDCF` -- tripod, focus changing, nothing moving -- against **6.87 %** on `foam`, the stack with independently measured motion: **4.3x the wrong way**, matching M97e's independent **21.5x** on a different statistic. The positive control is worse than the trap: **24.51 %** of tiles gate at **0.00 px** planted translation, **23.54 %** at the 0.35 px bar, and **34.57 %** at 2.00 px -- **a displacement six times the bar moves the response ten points while a quarter of tiles fire on nothing at all.** |
| 1771 | DERIVED | M97 | **DISPLACEMENT-BASED GATES FAIL WORST EXACTLY WHERE DISPLACEMENT IS LARGEST -- THE FAILURE IS ANTI-CORRELATED WITH THE THING THEY DETECT.** Two different statistics, two different traps, two different milestones produced the **same inversion**: `foam`, the stack with the most independently measured motion, produced the **lowest** firing rate in both instruments (M97e **0.3431 %**, M123 **6.87 %**). M123's decomposition supplies the mechanism: `foam` yields only **26-91 informative tiles** against **357-593** for the stationary `109MSDCF`, because **large motion destroys the local gradient correspondence the statistic requires**. The gate abstains hardest precisely when it is most needed. **This is a mechanism, not a coincidence, and it explains why both approaches invert rather than merely underperform.** |
| 1772 | MEASURED | M123 | **THE MAGNITUDE BAR CANNOT SEPARATE DEFOCUS FROM MOTION ON REAL FRAMES AT ANY SETTING THAT KEEPS THE PLANT.** Real defocus alone -- no subject movement whatsoever -- yields a mean `\\|s\\|` of **0.9521 px**, roughly **2.7x** `DEFAULT_MIN_SHIFT_PX`. So the quantity the gate thresholds is already several times over its own bar before any motion exists to detect. **Raising the bar past the defocus floor discards the plant; leaving it below admits the entire stationary stack.** There is no threshold in between, which is why this is a kill rather than a tuning exercise. |
| 1773 | MEASURED | M97 | **A STALE MODULE HEADER CONTRADICTED ITS OWN ENUM FORTY LINES BELOW, AND A COMMISSIONING BRIEF WAS WRITTEN FROM THE HEADER.** `outlier.rs`'s header said *"This module implements two"* discriminators and described `LowFreq` as an arm where defocus *"largely cancels"*, forty lines above an enum documenting **four** and marking `LowFreq` a **MEASURED FAILURE**. ORCH's brief inherited the header's version. Worse, the header's sentence *"has not yet been measured on real frames"* about `DEFAULT_MIN_SHIFT_PX` **is what M123 was commissioned against** -- work commissioned by a claim its own file had already refuted. **This is the third propagation failure in one night** after `color.rs:221` (correct colour matrix, 4 h 26 m ahead of the corpus) and `geometry.py:44-51` (the quantisation defect documented before the fleet-wide audit), **and the first with a measurable cost in agent-hours.** Corrected at `bfbff8e`, docs only, 352 tests pass. |
| 1774 | MEASURED | M97/ORCH | **THIS DIRECTION HAS NOW BEEN KILLED FIVE TIMES, AND RULE 40 WOULD HAVE CAUGHT IT -- NEITHER PARTY RAN IT.** M123's own section 0 lists **four** prior reports reaching the same verdict, three of them on real data; M89 had already written *"The metric works and should be adopted. The mask, as specified, should not ship."* M97's is the fifth. Rule 40 requires searching `docs/research/` before commissioning: **ORCH commissioned the hour without searching, and M97 accepted it without searching either, going to the source file first.** M97 then found the duplication in **twenty minutes** and stopped rather than spend the authorised hour -- **the correct behaviour, but it recovered a cost that the rule existed to prevent entirely.** |
"""

NEW_DISCIPLINES = """915. **WHEN A GATE'S RESPONSE TO A PLANTED EFFECT IS SMALLER THAN ITS RESPONSE TO NOTHING, STOP TUNING AND KILL IT.** Fact 1770: **24.51 %** at zero planted displacement against **34.57 %** at six times the detection bar is not a threshold that needs adjusting -- it is a statistic that is mostly reading something other than displacement. **The diagnostic is the zero-dose arm, and it is cheap:** run the positive control at dose zero *first*, and if it fires substantially, no amount of ladder above it can rescue the instrument. Every earlier attempt on this direction tuned the bar; the zero-dose arm is what ended it.
916. **ASK WHETHER A DETECTOR'S FAILURE MODE IS CORRELATED OR ANTI-CORRELATED WITH ITS TARGET.** Fact 1771: both displacement gates abstained hardest on the stack with the most motion, because large motion destroys the correspondence they measure. **An anti-correlated failure is categorically worse than a noisy one** -- it does not merely add variance, it systematically inverts the ranking, so aggregate performance looks acceptable while every individual verdict is backwards. Where a detector needs local correspondence, large signal can be self-defeating, and that must be tested with a *large*-amplitude plant rather than a marginal one.
917. **A DOCSTRING CAN COMMISSION WORK, SO IT MUST BE MAINTAINED AS THOUGH IT WERE THE REPORT.** Fact 1773: three propagation failures in one night, and the third caused a milestone to be commissioned against a claim the same file had already refuted forty lines lower. **Correct knowledge sitting in the tree is not the same as correct knowledge in the corpus**, and the direction of the error is not symmetric -- a stale header is read by whoever opens the file next, which is precisely the person about to act on it. When a finding lands, fix the docstring **and** fold it; and when writing a brief, **quote the file's authoritative declaration rather than its prose summary.**
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


def insert_after_discipline(n, block, txt):
    anchor = f"\n{n}. **"
    i = txt.index(anchor)
    j = txt.index("\n", i + 1) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1769, NEW_FACTS, text)
text = insert_after_discipline(914, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold170 OK: facts 1770-1774, disciplines 915-917")
print("  election-time masking KILLED on both discriminators;")
print("  the gates fail worst exactly where displacement is largest")
