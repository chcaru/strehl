"""Fold 28 -- the render is faithful and the capture is dark; the frames are
not the same brightness; and four probes for a hard election boundary all
came back empty. Plus the M100 ledger row.
"""
import io
import re

SYN = "docs/research/SYNTHESIS.md"
AG = "AGENTS.md"


def check(row, want=5):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == want, "row has %d unescaped pipes, need %d: %s" % (n, want, row[:170])
    return row


FACTS = [
    check(
        "| 1253 | **THE RENDER IS TONALLY FAITHFUL AND THE CAPTURE IS 1.76 "
        "STOPS DARK, SO THE PRODUCT LOOKS DULL FOR A REASON THAT IS NOT THE "
        "STACKING.** `bee-3-cpl`'s sRGB render puts the white background at "
        "**0.5734** where the RAW green level predicts **0.5752** -- 0.3% "
        "apart. Luma p99.9 is **0.5947**, so **0.75 stops** of output range go "
        "unused, and **0.000000%** of pixels sit at either clipping limit. In "
        "the RAWs the background is at **0.296** of the sensor's usable range "
        "and **no pixel of any of the 299 frames reaches 0.99 of white**. | The "
        "owner's verdict was that the stacks do not look good yet, and a large "
        "part of that is exposure, not merge quality. Exposure alone -- "
        "linearise, +1.57 stops, re-encode, no contrast curve, no saturation, "
        "no sharpening -- clips only **0.094%** of pixels and transforms the "
        "photograph. `--srgb` is documented as the mode for looking at, so "
        "shipping it 1.57 stops dark is a product defect even though the "
        "numbers are correct. Dispatched as M100. | orchestrator (MEASURED); "
        "`experiments/ORCH-drift-check/tone.py`, `rawlevel.py`, `expose.py` |"),
    check(
        "| 1254 | **THE FRAMES ARE NOT THE SAME BRIGHTNESS, AND THE ALIGNMENT "
        "SOLVE MAY ALREADY PREDICT BY HOW MUCH.** Across 30 of `bee-3-cpl`'s "
        "299 frames the background green level falls **0.2284 -> 0.2059**, a "
        "ratio of **1.1091 (0.149 stops)**. Breathing changes magnification and "
        "irradiance falls as 1/m^2, so M86's **232.7 px** over a **4226 px** "
        "half-diagonal predicts **1.1132** against **1.1091** measured. | If it "
        "holds, photometric normalisation is **free** for any stacker that "
        "solves alignment -- derived from geometry with no fitted gain -- and "
        "the merge currently has no photometric term at all, so every election "
        "boundary is a potential brightness step. **CONFOUNDED, AND M99 WAS "
        "TOLD SO AT DISPATCH**: the patches are in sensor rather than scene "
        "coordinates, so a 5.5% magnification change slides each one ~232 px "
        "across a background that is not evenly lit, and the top-left patch "
        "contains the wing -- its series is non-monotonic, which is subject "
        "structure, not photometry. Nothing here may be built on until M99 "
        "redoes it post-warp. | orchestrator (MEASURED but CONFOUNDED; the "
        "1/m^2 link is ARGUED); `experiments/ORCH-drift-check/photodrift.py` |"),
    check(
        "| 1255 | **FOUR INDEPENDENT PROBES FOR A HARD ELECTION BOUNDARY FOUND "
        "NONE; THE ARTIFACTS THAT ARE THERE ARE SMOOTH.** The orchestrator "
        "repeatedly saw hard-edged plateaus in the render and could not measure "
        "one. `step.py`: the profile across the halo is a monotonic ramp, and "
        "the one band that showed a step crossed the subject. `ridge.py`: zero "
        "long-thin discontinuities in the background. `cliff.py`: the top "
        "texture-cliff hits are ordinary object edges. `eyepatch2.py`: the "
        "low-texture region on the eye transitions over **~26 px** with a "
        "largest single-pixel change of **1.09x** in texture energy -- a ramp. | "
        "The likeliest explanation is perceptual: a smooth luminance ramp with "
        "a discontinuity in its *gradient* is rendered by the visual system as "
        "an edge, so 'I can see a hard boundary' is not evidence that one "
        "exists. Same lesson as fact 1250 and it is now the dominant failure "
        "mode of orchestrator-side observation. It does not exonerate the "
        "merge; it means the artifact has not been characterised and the "
        "instrument to characterise it does not exist yet. | orchestrator "
        "(MEASURED, four negative results); mechanism ARGUED |"),
    check(
        "| 1256 | **A MASK BUILT TO FIND AN ARTIFACT EXCLUDED THE ARTIFACT, "
        "THREE TIMES IN ONE SESSION, AND A CHEAP GUARD CAUGHT THE THIRD.** "
        "`step.py` sampled a band that crossed the subject; `ridge.py` masked "
        "to bright low-variance background, excluding both the location and -- "
        "via `sd < p25` -- the very local variation a step consists of; "
        "`eyepatch.py` masked to `eye < p45` and missed a patch that is "
        "*lighter* than the eye. `eyepatch2.py` asserted that the mask covers a "
        "known-artifact probe region before computing anything, and **the "
        "assertion fired at 49.0% coverage against a 50% bar**. | The guard is "
        "three lines and it converted a fourth silent wrong answer into a "
        "loud stop. Generalised as discipline 613. Note the assertion runs "
        "before any statistic is reported, so a failure is safe -- the same "
        "property that makes the fold scripts' pipe-count asserts safe. | "
        "orchestrator (MEASURED) |"),
]

DISC = [
    "613. **AFTER BUILDING A MASK, ASSERT THAT IT CONTAINS THE THING YOU ARE "
    "LOOKING FOR, BEFORE COMPUTING ANYTHING THROUGH IT.** Three masks in one "
    "session excluded the artifact they were built to find, and each would "
    "have returned a confident wrong answer. Selection criteria correlate with "
    "the target more often than is comfortable -- a smoothness criterion "
    "excludes steps, a darkness criterion excludes bright defects, a "
    "background criterion excludes anything on the subject. Pick a probe "
    "region you already believe contains the target, assert coverage, and let "
    "it abort. Three lines. (fact 1256)",

    "614. **A SMOOTH RAMP WITH A KINK LOOKS LIKE AN EDGE, SO SEEING A HARD "
    "BOUNDARY IS NOT EVIDENCE OF A DISCONTINUITY.** The orchestrator saw "
    "hard-edged plateaus in the render four times and measured a ramp every "
    "time -- ~26 px transitions with per-pixel changes under 1.1x. The visual "
    "system enhances gradient discontinuities into apparent steps, which is "
    "exactly the wrong bias for an imaging project whose artifacts are "
    "measured in DN. In this corpus a visual observation is a **hypothesis "
    "with a location attached**, never a measurement, and it must name the "
    "instrument that would confirm it. (facts 1250, 1255)",
]

L = io.open(SYN, encoding="utf-8").read().split("\n")
i609 = next(i for i, l in enumerate(L) if l.startswith("612. "))
end = i609 + 1
while end < len(L) and L[end].strip() and not re.match(r"^\d+\. ", L[end]):
    end += 1
L[end:end] = [""] + [x for p in ((d, "") for d in DISC) for x in p][:-1]

ilast = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[ilast].startswith("| 1252 |"), L[ilast][:80]
L[ilast + 1:ilast + 1] = FACTS
io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: facts 1253-1256, disciplines 613-614")

A = io.open(AG, encoding="utf-8").read().split("\n")
j = next(i for i, l in enumerate(A) if l.startswith("| `M99` |"))
row = check(
    "| `M100` | **THE VIEWING RENDER IS 1.57 STOPS DARK AND EVERY SCREENSHOT "
    "OF THIS PROJECT GOES THROUGH IT.** `--srgb` is documented as the mode for "
    "looking at, and it puts a white background at 0.5734 with 0.75 stops of "
    "headroom unused and nothing clipped, because the capture is ~1.76 stops "
    "under and strehl is faithful to it (fact 1253). Add `--exposure <STOPS>` "
    "applied in linear light before the transfer curve, and a reported, "
    "deterministic `--auto-exposure`; both errors without `--srgb`. **The "
    "binned linear default output is byte-frozen and must stay bit-identical** "
    "-- other agents are measuring against it right now -- so the proof is a "
    "byte comparison, not an assurance. Owns `color.rs`; routes `main.rs` and "
    "`merge_cmd.rs` patches through the orchestrator. |"
    " `docs/research/M100-exposure.md`, `crates/strehl-core/src/color.rs`, "
    "`experiments/M100-exposure/`, `C:\\dev\\strehl-out\\M100\\` |"
    " dispatched, running |", 5)
A[j + 1:j + 1] = [row]
io.open(AG, "w", encoding="utf-8", newline="\n").write("\n".join(A))
print("AGENTS.md: M100 ledger row after line %d" % j)
