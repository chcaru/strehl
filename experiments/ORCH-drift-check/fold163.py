"""ORCH fold 163: M120-patchwork.

The background patchwork the owner can see is IN THE SHIPPED RENDER, its
mechanism is not what fact 1604 said, and M120 leaves behind a commissioned
invariant plus a falsifiable prediction against the soft gate.

Source: docs/research/M120-patchwork.md (commit c1fa3ae, PIL audit 23dfa78).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1742 | MEASURED | M120 | **THE BACKGROUND PATCHWORK IS IN THE SHIPPED DEFAULT RENDER, NOT ONLY IN THE GATE-0 IMAGE ORCH WAS SHOWN, AND IT VIOLATES A PROVEN BOUND BY 3.4x.** Define `Q = C(merge)/max_k C(f_k)` with `C(I) = \\|\\|G2 - G8 I\\|\\| / mean`. For any **constant** weighting `Q <= max mean / min mean = 1.284` -- a theorem, not a threshold. Measured: shipped **gate 4 = 4.337 (FAILS)**, gate 0 = 7.166 (FAILS), against plain mean **0.343**, single frame **0.308**. Replicated on a second stack (`bee3-g0/g1/full` = 3.269 / 2.269 / 2.149) and stable to 4 s.f. on a repeat render. **Commissioned in both directions**: an all-frames-identical placebo through the identical gate-4 admitted sets reads **0.3085** (passes), and a planted defect reads **6.694** (fails). Proposed as invariant **INV-PATCHWORK** with its failure direction stated and an in-merge implementation needing no extra renders. |
| 1743 | MEASURED | M120 | **FACT 1604 WAS WRONG IN TWO OF ITS THREE LIMBS, AND THE SURVIVING MECHANISM IS A BIAS RATHER THAN NOISE -- WHICH IS WHY AVERAGING 167 FRAMES DOES NOT REMOVE IT.** `R1a` (response flat / noise-dominated, so argmax is random) is **REFUTED**: the winner sits **15.0x** the pure-noise ceiling (0.6685 vs 0.0445), **0.0 %** of the ROI is at or below it, and the through-focus range spans **8.6 noise SD**. `R1b` (the regulariser snaps plateaus) is **NOT SUPPORTED**: the dominant scale is **21-26 px**, matching the **27x27 focus window** rather than the 17x17 regulariser -- independently corroborating M111 P3 on a second stack. `R1c` (each polygon is one frame plus exposure drift) is **REFUTED at gate 4**, where the shipped gate averages **166.8 of 299** frames per pixel and `n_eff = 1` on only 0.3 % of pixels; it is true only at gate 0. Tiling/block bug **DEAD** (26.2 % axis-aligned vs 22.2 % uniform, peaks unmatched). Photographic origin **DEAD** (all 299 frames featureless in the ROI, median Q 0.490). Demosaic/colour **DEAD** (present in a green-luma path with neither). **Corrected mechanism, ARGUED:** the response is strongly non-flat but **near-degenerate at its peak** -- median winner-to-runner-up gap **0.216 gate units** on a response of 0.6685 -- and near-tied frames differ in level by up to **28 %**, so the *admitted set* changes from pixel to pixel and the sets' means differ. **A bias survives averaging; noise would not.** |
| 1744 | MEASURED | M120 | **PHOTOMETRIC NORMALISATION IS THE LARGEST *MEASURED* LEVER ON THE PATCHWORK AND IT IS STILL NOT ENOUGH.** Level normalisation cuts `Q` from **4.337 to 1.697**, but **39.1 %** of the excess survives and the result remains above the 1.284 bound. **ORCH's first draft called this `the largest single lever`; that is not established** -- the reduction is **-60.9 %** against the exponential soft gate's **-59.8 %** (fact 1745), a 1.1-point margin, and the two are not comparable anyway because one is measured and the other is a prediction. `Largest measured` is the defensible claim. Separately, the election is exonerated as a *manufacturer* of structure: rho(\\|grad index\\|, \\|grad out\\|) is **+0.5465** at gate 0 with a shift null of +0.0077 and an edge ratio of **12.69x**, yet **-0.2424** at the shipped gate 4, and the decisive test is the placebo -- identical frames through the identical gate-4 admitted sets give **Q = 0.3085**. **The election alone manufactures nothing; the set-dependent mean does.** |
| 1745 | ARGUED | M120 | **PRE-REGISTERED PREDICTION, FILED FOR M116 TO FALSIFY: THE SOFT GATE HALVES THE PATCHWORK AND DOES NOT FIX IT.** Predicted `Q`: gaussian **4.337 -> 2.291** (-47.2 %), exponential **-> 1.744** (-59.8 %), touching **64.8 %** of the frame. **Neither reaches the 1.284 bound.** No hard gate works either -- `Q` crosses the bound only between gate 8 and gate 16, i.e. at the arithmetic mean, which is the setting that discards the focus stacking. Recorded here **before** M116 reports, so the prediction is falsifiable rather than retrofitted; ORCH's standing instruction not to recommend the soft gate is unchanged and now has a quantitative reason. |
| 1746 | MEASURED | M120 | **ORCH'S PIL BROADCAST STATED THE HAZARD'S DIRECTION WRONGLY, AND THE CORRECTION MATTERS FOR EVERY BAND-PASS STATISTIC IN THE PROJECT.** ORCH told the fleet that 8-bit laundering is a false-**null** risk (a small signal falls under the quantisation floor). M120 measured its own headline both ways: **PIL 4.407 vs true 4.337** -- the laundered read came out **higher**, because quantisation *adds* band-pass energy. **So for gradient, high-frequency and veil-energy statistics it is a false-**ALARM** hazard**, and a narrowing reader would make the proposed INV-PATCHWORK fire on a clean merge. M120 was itself **NOT EXPOSED** (every `.tif` read is `tifffile.imread`; the single `Image.open` reads 8-bit PNGs) and verified this by re-running rather than reasoning: all 11 TIFFs it consumed carry **6,199-15,019 distinct levels per channel** against <=256 for a laundered file. It also found a confirmed downstream victim: `M87-occlusion/src/40-ship-delta.py` persists `cache/ship-delta.npy` as **8-bit units under a uint16 dtype** (max 163, mean 1.621), and `43-ship-crops.py` divides that by 257.0, so **those crops are black**. |
"""

NEW_DISCIPLINES = """894. **PREFER AN INVARIANT WITH A PROVEN BOUND OVER A TUNED THRESHOLD, AND COMMISSION IT IN BOTH DIRECTIONS.** INV-PATCHWORK (fact 1742) is worth more than any measured number in M120's report because `Q <= 1.284` is a **theorem about constant weights**, not a level someone chose: a violation is a proof that the weighting varies spatially, and it cannot be argued down. It is also commissioned **both** ways -- a placebo that must pass (0.3085) and a plant that must fail (6.694) -- so a green means the instrument is quiet AND awake. **When a quantity admits an analytic bound under the null you care about, build the check on the bound; you get sensitivity, a failure direction and interpretability for free.**
895. **`SURVIVES AVERAGING` IS A DIAGNOSTIC, NOT AN ANOMALY: IT SEPARATES BIAS FROM NOISE AND SHOULD BE THE FIRST QUESTION ASKED OF ANY PERSISTENT ARTEFACT.** Fact 1743's artefact is visible after averaging **166.8 frames per pixel**, which alone refutes every noise-driven explanation without any further measurement -- 167-fold averaging would have removed it. ORCH's fact 1604 had proposed exactly such an explanation (a flat response giving a random argmax) and it was refuted at **15.0x** the noise ceiling. **Before theorising about a persistent structure, ask what `n_eff` it survived; the answer usually deletes half the candidate mechanisms for free.**
896. **WHEN YOU BROADCAST A HAZARD, STATE ITS DIRECTION AS A HYPOTHESIS AND ASK TO BE CORRECTED -- BECAUSE THE DIRECTION IS THE PART YOU ARE MOST LIKELY TO GET WRONG.** Fact 1746: ORCH broadcast the PIL hazard fleet-wide as a false-null risk, and the first agent to *measure* it found the opposite sign on band-pass statistics. The existence of the hazard was right; the sign was wrong; and a fleet acting on the sign would have dismissed inflated alarms as safe. **A hazard notice carries two claims -- that the mechanism exists, and what it does to your number -- and only the first is usually established when the notice goes out. Label the second ARGUED and invite the measurement.**
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


text = insert_after_fact_row(1741, NEW_FACTS, text)
text = insert_after_discipline(893, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold163 OK: facts 1742-1746, disciplines 894-896")
print("  the patchwork is in the SHIPPED render (Q=4.337 vs a proven bound of 1.284);")
print("  fact 1604 refuted in 2 of 3 limbs; soft-gate prediction filed for M116 to falsify")
