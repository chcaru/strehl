"""ORCH fold 165: M97e -- the robust election fails its trap.

Decision-relevant: this is one of two independent lines now saying
STREHL_ROBUST_ELECTION must not be promoted. Forwarded to M126 as a prior.

Source: docs/research/M97e-robust-election.md.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1750 | MEASURED | M97e | **THE ROBUST ELECTION FIRES 21.5x HARDER ON A STACK WITH NO MOTION THAN ON THE STACK IT WAS BUILT FOR. DO NOT PROMOTE IT.** ORCH registered the bar **before** the build: the **plant** is `foam`, a stack with measured motion (the stack fact 1189 rests on); the **trap** is `coffee-bean`, stationary on a tripod, where a frame legitimately disagrees because **it is the only frame that resolves that pixel**. A gate firing on the trap is worse than no gate. Measured, both arms rendered back-to-back from **one pinned binary** with command lines identical but for the environment variable: trap (105 frames) **7.3723 %** of pixels changed their elected frame and **6.874 %** changed output value; plant (100 frames) **0.3431 %** and **0.314 %**. M97e's own verdict: *"That is not a motion gate. It is not a marginal miss, a threshold that wants tuning, or a bar that wants narrowing. The quantity is aimed at the wrong thing."* Status recorded in the report's own header: **LANDED BEHIND A FLAG, DEFAULT OFF, AND THE FLAG SHOULD STAY OFF.** |
| 1751 | MEASURED | M97e | **TWO INSTRUMENTS THAT CANNOT FAIL THE SAME WAY AGREED, WHICH IS HOW A MEASUREMENT SURVIVES A TEN-AGENT SHARED TREE.** The `moved` counter is computed **inside one process**, comparing the gated election against the ungated election on the same focus fields, so no between-run change can confound it. The changed-pixel fraction is computed **across two processes** by differencing the two output TIFFs, so it sees everything the first instrument is blind to. They agree within half a percentage point on both stacks (**7.37 / 6.87** and **0.34 / 0.31**). **That agreement is the evidence that no dependency drifted between the baseline and the gated render** -- the confound that matters most in this repository, where roughly twenty agents share one working tree. A within-process counter and a cross-process image diff cannot both be wrong in the same direction by accident. |
| 1752 | MEASURED | M97e | **FACT 1189 PRICED THE RIGHT *STAGE* AND THE WRONG *STATISTIC*, AND THE TRAP IS WHAT TOLD THEM APART.** Fact 1189 measured that masking the **election** removes 100 % of motion-elected pixels where masking the **average** recovers 6.0 % -- a 16.7x advantage to the election stage, and the whole basis for wiring `robust.rs` into pass one. The wiring is *"done, tested, controlled, and null-proven"*; what failed is the discriminator it carries. **A null would have passed**: on the motion stack the gate does what it should, at 0.3431 %. Only the stationary trap -- where firing is definitionally wrong rather than merely unhelpful -- exposed that the statistic responds to *resolution disagreement* rather than to motion. **The stage decision stands; the statistic does not.** |
"""

NEW_DISCIPLINES = """900. **A TRAP BEATS A NULL, BECAUSE A NULL CAN ONLY FAIL TO FIND AN EFFECT WHILE A TRAP CAN CONVICT.** Fact 1752: M97e's gate was *null-proven* and still wrong. A null asks `does it do nothing where nothing should happen?`; a **trap** asks `does it do something where doing anything is definitionally an error?` -- and only the second can distinguish a statistic aimed at the right quantity from one aimed at a correlated wrong quantity. Here the trap is a **stationary** stack in which a frame legitimately disagrees because it is the only frame resolving that pixel, so any firing is a false positive by construction. **Register the trap before you build, name what firing on it would prove, and accept that a gate can pass every null you own and still be aimed at the wrong thing.**
901. **IN A SHARED WORKING TREE, PAIR AN IN-PROCESS INSTRUMENT WITH A CROSS-PROCESS ONE AND REQUIRE THEM TO AGREE.** Fact 1751. The two are blind to different confounds -- the in-process counter cannot see between-run drift because it never leaves the process, and the cross-process image diff sees the shipped artefact including every dependency that moved. **Agreement between them is a positive measurement that nothing drifted**, which is stronger than any hash-based drift check and far stronger than an assertion that the tree was quiet. This is the cheap alternative when pinning a private copy of the dependency tree is impractical: not one instrument plus vigilance, but two instruments whose failure modes do not overlap.
902. **`LANDED BEHIND A FLAG` IS A COMPLETE AND HONOURABLE OUTCOME; SAY SO IN THE HEADER.** M97e's status line reads `LANDED BEHIND A FLAG, DEFAULT OFF, AND THE FLAG SHOULD STAY OFF` -- the build succeeded, the measurement refused it, and both facts are in the first line a reader sees. **A milestone that ships working code it then recommends against is not a failed milestone**, and a report that buries that recommendation under the engineering is how an unjustified default gets promoted later by someone reading only the summary. Lead with the recommendation, not the deliverable.
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


text = insert_after_fact_row(1749, NEW_FACTS, text)
text = insert_after_discipline(899, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold165 OK: facts 1750-1752, disciplines 900-902")
print("  the robust election fires 21.5x harder on a stationary stack than on a moving one;")
print("  a trap convicted a gate that every null had cleared")
