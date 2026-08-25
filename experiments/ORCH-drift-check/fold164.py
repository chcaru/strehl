"""ORCH fold 164: M109-highlights.

The magenta-highlight fix, which is ON by default and ungated -- the first
measured improvement to reach the owner's renders without a switch.

Also folds M109's structural-immunity argument and the consequence it drew from
the corrected colour matrix that ORCH had not stated.

Source: docs/research/M109-highlights.md; crates/strehl-core/src/color.rs:236-307;
crates/strehl-cli/src/stack.rs:1086-1094.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1747 | MEASURED | M109 | **THE MAGENTA-HIGHLIGHT FIX IS THE ONE MEASURED IMPROVEMENT THAT REACHES THE OWNER'S RENDERS WITHOUT A SWITCH.** Blown neutral highlights rendered magenta because white balance carries red and blue past the container maximum while green is already pinned there, so the matrix reads a strong colour where the sensor recorded clipping. `Render::clip_highlights` (`color.rs:293-303`) brings a pinned triple down to the **neutral** ceiling `min_c ceiling[c]` **before** the matrix sees it. Measured: affected pixels **2.0017 % -> 0.5060 %**, green offset **-0.1028 -> -0.0260**, and **0 pixels overshot**. It is applied **unconditionally** at `stack.rs:1091-1093` (`matrix.map(\\|render\\| render.with_ceiling(...))`) with no environment gate -- so unlike the six switchable improvements it is live in the shipped render. **ORCH's brief said `exactly one improvement is switched on`; that was over-scoped and has been corrected to `switchable`** (commit `d5ba764`), the second instance in one night of the scope-inflation pattern fact 1721 measured. |
| 1748 | MEASURED | M109 | **THE FIX'S SAFETY IS STRUCTURAL, NOT TUNED: WHERE NOTHING IS PINNED IT IS EXACTLY THE IDENTITY.** `clip_highlights` returns its input unchanged unless some channel is at or above the ceiling, so an unsaturated stack **cannot move by one bit** -- a guarantee from the shape of the code rather than from a measured null. M109 states the discarded alternative and why it loses: an unconditional clamp would eat real, unclipped **red** highlights above roughly **6420 DN**, because red's ceiling is only `1/2.687` of the container in unbalanced terms. A blown *coloured* highlight keeps its hue direction because a channel already below the neutral ceiling is left alone. The stated cost is not hidden: headroom above the neutral ceiling in unpinned channels is discarded, slightly desaturating a strongly clipped colour -- justified because **a pinned channel is not a measurement of how saturated the object was**, so keeping that headroom would fabricate saturation the sensor never recorded. |
| 1749 | MEASURED | M109 | **THE CORRECTED COLOUR MATRIX MAKES THE MAGENTA DEFECT ~2.6x WORSE THAN THE CORPUS IMPLIED, WHICH STRENGTHENS THE PRE-MATRIX FIX -- A CONSEQUENCE ORCH'S OWN CORRECTION NOTICE FAILED TO DRAW.** Output red carries camera green at **-0.4486**, a *negative* coefficient. In a magenta blob camera green is the **suppressed** channel, so suppressing it **raises** output red: `cam_lin = (1.0971, 0.9051, 1.1887)` gives linear R **1.166** (clamped to 1.0) and G **0.777**, i.e. sRGB **0.8947**. At the corrected 27.4 % green-to-red leak rather than the corpus's 10.4 %, the matrix amplifies magenta about **2.6x harder** than believed -- so clipping *before* the matrix, which is where the fix already sits, is better justified than when it was designed. **M109 was itself unaffected by the matrix error** because `mechanism.py:60` *computes* the matrix from the crate's algorithm rather than quoting the constant, reproducing all nine corrected entries to 4 d.p. Independent corroboration: paper arithmetic predicts `R-G = +0.1053` and the rendered TIFF measured a green offset of **-0.1028**, agreeing to ~2 % **using the corrected matrix**. |
"""

NEW_DISCIPLINES = """897. **TRANSCRIBE THE OPERATION, NOT THE CONSTANT -- IT IS FREE AND IT IS IMMUNE TO THE CORPUS GOING STALE.** M109 survived the colour-matrix error (fact 1749) for one reason: its script recomputes the matrix by the crate's own algorithm instead of copying the number the corpus quoted. Five other files copied the number and all five were wrong. **A copied constant is a snapshot with no link back to its source; a transcribed operation re-derives itself every run and fails loudly if the source changes.** Where a value is computed by shipped code, compute it the same way rather than quoting it, and say in the docstring which function you are mirroring.
898. **A FIX WHOSE NO-OP CASE IS THE IDENTITY *BY CONSTRUCTION* NEEDS NO REGRESSION ARGUMENT, AND THAT IS WORTH DESIGNING FOR DELIBERATELY.** Fact 1748: `clip_highlights` takes an early return on every unpinned pixel, so `never worse` is a property of the control flow rather than a claim requiring a measured null on every stack. Contrast the switchable improvements, none of which can make that claim and all of which therefore need an audit before promotion. **When designing a correction, prefer the form that is exactly inert outside its trigger condition** -- it converts an open-ended empirical burden into a one-line reading of the code, and it is the reason this fix could ship ungated while better-measured ones could not.
899. **A CORRECTION NOTICE SHOULD STATE WHICH DESIGN DECISIONS IT STRENGTHENS, NOT ONLY WHICH NUMBERS IT INVALIDATES.** ORCH broadcast the matrix correction as a list of contaminated files and numbers to re-run. M109 replied with the consequence ORCH had missed: because the green-to-red coefficient is **negative** and green is the suppressed channel, the corrected leak makes the defect **2.6x stronger**, which is an argument *for* the fix's placement (fact 1749). **A correction changes the weight of evidence in both directions; a notice that only lists damage invites every recipient to check for damage and nobody to check for support.** Ask explicitly: does this make any existing decision better justified?
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


text = insert_after_fact_row(1746, NEW_FACTS, text)
text = insert_after_discipline(896, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold164 OK: facts 1747-1749, disciplines 897-899")
print("  the magenta-highlight fix is ON and ungated; its safety is structural;")
print("  the corrected matrix makes the defect 2.6x worse, strengthening the fix")
