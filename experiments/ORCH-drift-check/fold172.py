"""ORCH fold 172: M121-halo-polarity.

The halo's WIDTH is set by strehl's own focus window, not by the optics.
Its POLARITY was never validly tested, and M121 killed its own most exciting
result to establish that. It also withdrew an explanation of its own and left
the residual anomaly unexplained rather than fitting a story to it.

Source: docs/research/M121-halo-polarity.md (commit 5607fdd).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1778 | MEASURED | M121 | **THE HALO'S WIDTH IS SET BY STREHL'S OWN FOCUS WINDOW, NOT BY THE OPTICS -- WHICH MAKES IT A SOFTWARE ARTEFACT WE CHOOSE.** `P-WIDTH` survives on three independent measurements. Derived from source, `focus.rs:83 WINDOW_RADIUS = 13` composed with `merge.rs:93 REGULARISER_RADIUS = 8` and `SOBEL_RADIUS = 1` predicts a spill of **22 px**; measured `w50` is **10.0 px** with a cutoff at **13.25** and the band table dead by **12 px**. **The measured extent matches the window radius and matches none of the three physical alternatives checked** -- not the defocus radius, not the object size, not the focus step. A halo whose scale is a compile-time constant is one the project can change, which is a materially different situation from one imposed by the lens. |
| 1779 | MEASURED | M121 | **THE HALO'S POLARITY IS NOT CONFIRMED AND NOT REFUTED, BECAUSE IT WAS NEVER VALIDLY TESTED -- AND M121 ESTABLISHED THAT BY KILLING ITS OWN MOST EXCITING RESULT.** Dark objects on bright surrounds show a rim of **+0.0634** (n = 70, 95 % CI **[+0.0533, +0.0754]**, **93 %** positive). Bright objects on dark surrounds read **+0.0009** (n = 18, CI **[-0.0141, +0.0289]**, **50 %** positive) -- **a null, not the predicted dark rim**, so it neither confirms nor kills. The cause is the subject, not the instrument: **only 5 of 18** bright-object edges straddle a depth discontinuity at all, since a pale hair on a dark bee body is same-depth and the mechanism predicts nothing there. On `tweezers` an apparent **+0.1326** was **rejected as a background gradient** because it **never ends within 30 px** and a **single unmerged frame reproduces its shape at one third amplitude**. **Verdict: survived on width, untested on polarity -- do not build the E5 fix on `P-WIDTH` alone.** |
| 1780 | MEASURED | M121 | **M121 WITHDREW ITS OWN EXPLANATION AFTER TWO OF ITS NUMBERS CAME OUT IMPOSSIBLE, AND LEFT THE RESIDUAL UNEXPLAINED RATHER THAN FITTING A STORY.** Chasing a **6.7x** gap between its implied correlation and ORCH's measured **+0.5109**, M121 found median per-edge \\|shift\\| **2.69 %** against a **pooled** shift of **3.85 %** -- an averaging gain of **0.70x** where **sqrt(57) = 7.55x** was expected, implying a correlation of **+2.06**. **Pooling increased the shift, and a correlation above 1 is impossible**, so the explanation rather than the data was at fault: its N8 averaging account is **WITHDRAWN**, having borrowed ORCH's **8.04 %** as the per-edge scale instead of measuring its own. The perturbation is **systematic, not zero-mean**. Its pre-registered follow-up `P-B` then **FAILED**: shift similarity is flat in level proximity (Spearman **+0.100**, far/near **1.245**), so **quantisation error here is not value-locked** -- a genuine tension with fact 1765's value-deterministic mechanism that M121 recorded as **UNEXPLAINED** instead of resolving rhetorically. |
| 1781 | MEASURED | M121 | **PROVENANCE BY REPRODUCTION BEATS TRUSTING A DTYPE FIELD, AND THE HASH TEST PROPAGATED TO A SECOND MILESTONE WITHIN THE HOUR.** M121 did use one differencing estimate on possibly-narrowed data -- `amp_probe.py` set `MIN_AMPLITUDE` from flat-ROI noise steps -- and cleared it not by inspecting metadata but by **re-rendering the input and finding it byte-identical** to the M93 gate-4 arm (`e6132cd0...`). It then applied fact 1775's discriminator to its own gate result: because it renders with `STREHL_ALIGN=0` it could have been structurally inert, and **a one-line SHA-256 proves it is merely useless instead** -- the arms are different files (`e6132cd0...` against `895e458d...`, **23 879** against **14 479** levels), so the gate changes the output and simply does not change the rim. **Had they been byte-identical its entire gate-0 comparison would have been vacuous.** Its control `N4` also caught a real instrument defect -- a flat ROI reading **-0.30** because the amplitude was noise -- fixed by a `MIN_AMPLITUDE = 2000 DN` floor **chosen before any verdict was read**; six instrument defects were found and fixed in total. |
"""

NEW_DISCIPLINES = """920. **A FEATURE WHOSE MEASURED SCALE MATCHES A COMPILE-TIME CONSTANT IS AN ARTEFACT YOU OWN, SO CHECK THE CONSTANTS BEFORE BLAMING THE PHYSICS.** Fact 1778: the halo's width matched `WINDOW_RADIUS` and matched no optical quantity -- defocus radius, object size and focus step were all excluded. **The discriminating test is cheap and should be routine:** derive the predicted extent from the source constants, then check whether the measurement tracks *those* or the physical alternatives. A defect attributed to the lens is a capture problem; the same defect attributed to a window radius is a one-line change.
921. **AN APPARENT EFFECT THAT NEVER ENDS IS A GRADIENT, AND A SINGLE UNMERGED FRAME IS THE CONTROL THAT SAYS SO.** Fact 1779: M121's largest and most exciting rim measurement (**+0.1326**) failed two checks it applied to itself -- it **did not terminate within 30 px**, and **one unmerged frame reproduced its shape**, which no merge artefact can do. Both checks cost minutes. **Require every claimed local artefact to demonstrate a spatial extent that ends, and to be absent from a single input frame**, because a background gradient, a vignette and an illumination falloff all masquerade as a rim when the profile window is too short to see them close.
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


text = insert_after_fact_row(1777, NEW_FACTS, text)
text = insert_after_discipline(919, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold172 OK: facts 1778-1781, disciplines 920-921")
print("  the halo's width is set by WINDOW_RADIUS, not by the lens;")
print("  and M121 killed its own headline and left the residual unexplained")
