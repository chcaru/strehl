"""Insert the M99 ledger row at dispatch (rule 41)."""
import io
import re

P = "AGENTS.md"
L = io.open(P, encoding="utf-8").read().split("\n")
i = next(i for i, l in enumerate(L) if l.startswith("| `M98` |"))
assert "TWO COMPETENT MILESTONES NOW DISAGREE" in L[i]

row = (
    "| `M99` | **THE MERGE HAS NO PHOTOMETRIC TERM, AND THE FRAMES ARE NOT THE "
    "SAME BRIGHTNESS.** Sampling 30 of `bee-3-cpl`'s 299 frames, the background "
    "green level drifts **0.2284 -> 0.2059**, a ratio of **1.1091 (0.149 "
    "stops)**. A stacker elects a different source frame in adjacent regions, so "
    "an 11% inter-frame brightness difference becomes a **step at every election "
    "boundary** -- the likeliest cause of the mottling and silhouette-hugging "
    "banding in the shipped render. The hypothesis worth killing: breathing "
    "changes magnification and irradiance falls as 1/m^2, so the drift should be "
    "predicted by the scale ladder **the aligner already fits**, making "
    "photometric normalisation free rather than estimated. M86's 232.7 px over a "
    "4226 px half-diagonal predicts **1.1132** against **1.1091** measured, 0.37% "
    "apart. **But the orchestrator's measurement is confounded and M99 was told "
    "so at dispatch**: the patches are in sensor rather than scene coordinates, "
    "so a 5.5% magnification change slides each one ~232 px across a background "
    "that is not evenly lit, and the top-left patch contains the wing. Redo it "
    "post-warp, separate a global gain from a spatially varying field, replicate "
    "on a second stack, and only then build. | dispatched, running |")

n = len(re.findall(r"(?<!\\)\|", row))
assert n == 4, "ledger row has %d unescaped pipes, need 4 for 3 columns" % n

L[i + 1:i + 1] = [row]
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("inserted M99 ledger row after line %d" % i)
