"""ORCH fold 173: the qualification that makes the masking kill precise.

M123's M12 reconciliation shows the statistic is close to exact ON THE PLANT.
The kill is therefore about specificity, not sensitivity, and fact 1770 read
alone overstates it.

Source: docs/research/M123-outlier-mask.md (commit 7dab599).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1782 | MEASURED | M123 | **THE MASKING KILL IS A FAILURE OF SPECIFICITY, NOT OF SENSITIVITY -- ON THE MOVING STACK THE STATISTIC IS NEARLY EXACT, AND FACT 1770 READ ALONE OVERSTATES THE CASE.** Reconciled against fact 1189, `foam` carries motion contamination in **4.78 %** of its output pixels; `ShiftFree` gates **4.35 %**, an agreement of **98.9 %**. **So the discriminator does find the motion that is there.** What kills it is that it *also* fires on **29.55 %** of a stationary stack where the correct answer is zero, and that its planted-displacement response is flat across the whole range that matters: **24.51 / 23.44 / 23.54 / 24.71 %** at **0.00 / 0.15 / 0.35 / 0.50 px**, moving only at 1.0 px to **34.77 %**, a **1.4x** change for a displacement three times the bar. **A detector that is accurate on the positive case and fires constantly on the negative case is not a weak detector; it is a detector of something else that happens to correlate with motion where motion exists.** This is the honest form of the verdict and it should be quoted with fact 1770, not after it. |
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1781, NEW_FACTS, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold173 OK: fact 1782")
print("  the kill is about SPECIFICITY -- on the plant the statistic is 98.9% exact")
