"""ORCH fold 171: M107b's correction to ORCH's own inert-gate claim.

ORCH asserted that only reading the code can distinguish a structurally inert
gate from a measurably useless one. M107 built a better instrument that needs
no code access, and supplied its own positive control in the same table.

Source: docs/research/M107b-lateral-correction.md (commit f9bfec3).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1775 | MEASURED | M107b | **ORCH WAS WRONG THAT ONLY READING THE CODE CAN TELL AN INERT GATE FROM A USELESS ONE: A BYTE-HASH A/B DOES IT, AND NEEDS NO ACCESS TO THE FILE.** ORCH broadcast that a structurally inert gate and a measurably useless gate produce the same number and *"only reading the code tells you which you have"*. M107b supplied the discriminator: **structurally inert implies `on` and `off` are byte-identical; measurably useless implies `on != off` in bytes while the metric stays static.** Measured as SHA-256 over five arms, four `off` variants -- `unset`, `unset`, the word `off`, and `0` -- are **byte-identical at `E400A63AA9F6AB1F1957940D7BD9D496`**, while the `on` arm diverges to **`E9580E8A2A85009494B2FE5A35441EBE`**. This matters beyond the correction: **in a multi-agent tree with lane boundaries, the hash test is available to an agent who does not own the file**, and ORCH's version was not. |
| 1776 | MEASURED | M107b | **THE KNOWN-INERT ARMS ARE THE POSITIVE CONTROL THAT PROVES THE DISCRIMINATOR CAN RETURN THE INERT VERDICT, AND THEY SIT IN THE SAME TABLE AS THE RESULT.** Discipline 903 requires asking what a check would have read had the defect been present. M107b answers it constructively rather than by argument: the `0`, `off` and unset arms are **proved inert by hash rather than assumed inert**, so the `on` arm's divergence is not a test that merely could not fail. **One experiment holds both the measurement and its own commissioning.** The same table also clears M107 of ORCH's nesting hazard directly: `STREHL_ALIGN` appears **nowhere** in M107's scripts so the default applied, `r7_wiring_ab.ps1:39` runs a real `align` and aborts on non-zero exit, and the log records **`align EXIT=0`** with the sidecar passed explicitly. |
| 1777 | MEASURED | M107b | **M107b RETRACTED ITS OWN FORM-BASED SCREEN ON ITS OWN EVIDENCE, MAKING FOUR SUCH SCREENS DEAD IN ONE NIGHT.** ORCH's three triage rules were refuted by three other milestones (facts 1710-1712, 1716-1717, 1757). M107b had proposed a **fourth** of its own -- *"does it differentiate or divide by local gradients?"* -- and falsified it with its own R15 arm: at **25 levels per window**, comfortably above the immunity bound, **the bias occurred anyway**, and the operative variable was **support**, not gradient-division. M107b holds no live claim resting on statistic form. Its clearance rests instead on a property of the **reader** (`tifffile`, zero `Image.open(` call sites) and on modelling quantisation with **the actual deterministic rounding rather than equal-power dither**, so fact 1712's 16x dither-model error reaches nothing of its. Registered bars it falsified and reported rather than re-cut: **H1, Y1, Z2, D3-direction, E4, F3**, including a retraction of its own section 23 headline and the withdrawal of `k = 1.374`. |
"""

NEW_DISCIPLINES = """918. **TO TEST WHETHER A SWITCH REACHES PIXELS, HASH THE OUTPUT -- DO NOT REASON ABOUT THE CALL GRAPH.** Fact 1775: ORCH spent the night warning the fleet about a silently inert gate and prescribed a remedy (read the source) that **most agents cannot apply, because the file belongs to another lane.** The byte-hash A/B answers the same question from outside, in one command, with no ownership required. **Prefer a black-box discriminator over a white-box argument whenever both are available** -- the black-box version survives lane boundaries, stale docstrings, and an author's belief about their own code, all three of which failed somewhere in this project tonight.
919. **PUT THE KNOWN-INERT ARMS IN THE SAME TABLE AS THE RESULT.** Fact 1776: including `0`, `off` and unset arms costs one run each and converts an A/B from a claim into a commissioned instrument, because arms **proved** inert by the same measurement demonstrate that the discriminator is capable of returning the inert verdict. **A switch A/B without inert arms cannot distinguish `the switch works` from `my test cannot fail`** -- and the four-way agreement additionally proves the off-path is insensitive to *how* the switch is spelled, which is its own class of bug.
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


text = insert_after_fact_row(1774, NEW_FACTS, text)
text = insert_after_discipline(917, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold171 OK: facts 1775-1777, disciplines 918-919")
print("  a byte-hash A/B beats reading the code, and works across lane")
print("  boundaries; the known-inert arms commission the experiment")
