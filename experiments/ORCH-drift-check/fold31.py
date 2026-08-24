"""Fold 31 -- the gallery, and an independent confirmation of the exposure
survey from a different statistic.
"""
import io
import re

SYN = "docs/research/SYNTHESIS.md"


def check(row, want=5):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == want, "row has %d unescaped pipes, need %d: %s" % (n, want, row[:170])
    return row


FACT = check(
    "| 1261 | **SEVEN DIVERSE STACKS RENDER CLEANLY UNDER EXPOSURE-ONLY "
    "CORRECTION, AND THE REQUIRED GAINS INDEPENDENTLY CONFIRM FACT 1257.** "
    "`bee-3-cpl`, `lavendar-cpl`, `flowers-cpl`, `leaf-2-cpl`, "
    "`flower-bud-alone-cpl`, `tweezers-cpl` and `coffee-bean` -- **1366 frames "
    "in 380 s** of stacking -- were merged at the default gate and given a "
    "single global gain in linear light, with **no** contrast curve, "
    "saturation, sharpening, local adjustment or noise reduction. Gains: "
    "**+1.16 to +3.19 stops**, clipping **0.0000-0.0721%**. `coffee-bean`, "
    "which the survey called correctly exposed at **+0.01 stops**, needed a "
    "gain of **0.920x (-0.12 stops)** -- a *reduction*. | The agreement matters "
    "because the two numbers come from different statistics on different data: "
    "the survey took `p99.9` of the black-subtracted RAW, the gallery took "
    "`p99.9` of the linearised merged sRGB render. They agree to **0.13 "
    "stops** on the one stack that should need nothing, so neither is an "
    "artifact of its own statistic. At 100% the `tweezers-cpl` render resolves "
    "individual machining striations and dust particles, and `leaf-2-cpl` -- "
    "pushed **+3.19 stops** -- shows clean vein and areole structure with no "
    "visible grain, which is what fact 1258's 0.097-0.134x noise ratio "
    "predicts and is the reason such a large push is survivable at all. | "
    "orchestrator (MEASURED); `experiments/ORCH-drift-check/gallery.py`; "
    "artifacts in `C:\\dev\\strehl-out\\ORCH-gallery\\` |")

L = io.open(SYN, encoding="utf-8").read().split("\n")
i = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[i].startswith("| 1260 |"), L[i][:80]
L[i + 1:i + 1] = [FACT]
io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: fact 1261")
