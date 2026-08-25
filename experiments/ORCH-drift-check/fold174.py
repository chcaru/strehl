"""ORCH fold 174: V-CA's revised verdict on the CA correction.

A verifier dismantled four of its own objections and reached the same verdict
anyway. That is the strongest form a NO can take.

Source: docs/research/V-CA-audit.md (commit 4bf7c72).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1783 | MEASURED | V-CA | **THE CHROMATIC-ABERRATION CORRECTION STAYS OFF BY DEFAULT -- AND THE VERDICT IS STRONGER FOR HAVING SURVIVED THE COLLAPSE OF FOUR OF ITS OWN SUPPORTING ARGUMENTS.** V-CA **withdrew from its own case against**: the blue/green harm (it was the colour matrix, not the correction), the resampling confound understood as a second-interpolation problem, and the measurement-space doubt -- the headline **grows** in the clean space rather than shrinking. **The blur worry the follow-up was specifically commissioned to press is measured and refuted in sign.** What survives is sufficient on its own: **no author recommends enabling it**; the transfer splits **0.950 / 0.541** against a **0.60** bar; the **23.6 %** scene-to-scene coefficient spread through the same glass is now **actively falsified rather than merely untested**, because `ddd683a` records that *"the spectral hypothesis dies, the effect survives"*, killing its one candidate explanation; and the dispatch gap **cannot fully close**, because there is no code joining the identity the software can read to the profile it would apply, and the CPL is **permanently unreadable**. |
| 1784 | MEASURED | V-CA | **THE CORRECTION SHIPPED POINTING THE WRONG WAY ONCE, 9/9 UNIT TESTS PLUS MUTATION TESTING MISSED IT, AND NO RENDER-DOMAIN SIGN CHECK HAS BEEN RUN SINCE.** Fact 1536 records the inverted sign; what V-CA adds is that **the only instrument that caught it was a render-domain preview nobody has repeated**, and that the unit suite which passed 9/9 through the defect included mutation testing and still could not see it. **A sign error is invisible to any test that checks magnitude**, which is most of them. V-CA names the remedy as the cheapest available change to its own verdict -- **the `anti` arm: one data-only profile entry and one render**, testing the exact failure this correction has already committed once. Turning the correction on by default before that arm runs would apply **an unverified sign to every user's photographs, through glass the product cannot identify, on the strength of a number no author ever recommended acting on.** |
"""

NEW_DISCIPLINES = """922. **A VERDICT THAT SURVIVES THE WITHDRAWAL OF ITS OWN SUPPORTING ARGUMENTS IS WORTH MORE THAN ONE THAT NEVER LOST ANY.** Fact 1783: V-CA entered with five objections, **destroyed four of them itself** -- including the one it had been commissioned to press, which was refuted *in sign* -- and reached the same conclusion on the remainder. **Record which arguments fell alongside the verdict they failed to change**, because a conclusion re-derived from a smaller base is better evidenced than the original, and because the withdrawn arguments are exactly the ones a future reader would otherwise re-litigate. The inverse is the warning: a case whose every limb still stands has usually not been pressed.
923. **A SIGN ERROR IS INVISIBLE TO EVERY TEST THAT CHECKS MAGNITUDE, SO IT NEEDS ITS OWN ARM.** Fact 1784: an inverted correction shipped past **9/9 unit tests and mutation testing**, and was caught only by looking at a render. Magnitude-based assertions -- tolerances, ratios, error norms, even mutation coverage -- are **symmetric in the quantity's sign** and cannot express the failure. **Any correction with a direction must carry an explicit `anti` arm** that applies the deliberately inverted profile and requires the metric to get *worse*; if it does not, the sign is untested no matter how green the suite is.
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


text = insert_after_fact_row(1782, NEW_FACTS, text)
text = insert_after_discipline(921, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold174 OK: facts 1783-1784, disciplines 922-923")
print("  CA stays off; the verdict survived four of its own arguments falling;")
print("  and a sign error is invisible to every magnitude-based test")
