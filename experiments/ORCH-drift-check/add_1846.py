"""Insert facts 1846-1848 after row 1845 of the SYNTHESIS fact table.

Same guards as add_1843.py: the anchor must land exactly once, no raw `|` in
cell text (corpus_lint S1 -- an unescaped pipe silently DISCARDS every cell past
the header count), and an even asterisk count (S5 -- an odd count leaves an
italic span open). Both failures render invisibly, so they are prevented by
construction rather than caught afterwards.

These three rows record the first end-to-end VISUAL adjudication of the whole
delivered corpus by the orchestrator's own eye, the resulting suspicion that the
halo instrument is emitting false positives, and the discovery of a visible
chroma defect that turns out to have been sitting inside an already-measured
but undiagnosed channel asymmetry.
"""

import io
import sys
from pathlib import Path

SYN = Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"

ROWS = [
    (
        "1846",
        "MEASURED",
        "ORCH",
        "**FIRST FULL 1:1 VISUAL ADJUDICATION OF ALL 26 DELIVERED MASTERS: 24 CLEAN TO THE "
        "EYE, 2 WITH VISIBLE DEFECTS.** Every prior quality claim in this corpus came from "
        "a statistic or from a downscaled contact sheet, and both have now demonstrably "
        "lied in both directions -- the contact sheet read `wrapped-text-2` as mush when "
        "the master resolves individual toner particles and paper fibre. `orch_corpuseye.py` "
        "cuts two native-resolution 520 px crops per subject under one fixed per-subject "
        "display transform taken from that subject's own 99.9th percentile, never "
        "resampled and never per-crop autoscaled, using two DIFFERENT site rules so the "
        "crops cannot land on the same feature: a BOUNDARY rule ranking low-frequency "
        "level step times gradient, where halos and occlusion artifacts live, and a "
        "TEXTURE rule ranking box-filtered gradient, where sharpness lives. All 26 masters "
        "read and rendered, **0 failed**, 9 sheets. VERDICT BY EYE: genuinely excellent on "
        "`bee-1-cpl`, which resolves **individual ommatidia** of the compound eye at N=299 "
        "with two hairs crossing it, and on `wrapped-text-1/2`, `flower-inner-edge-cpl`, "
        "`highly-angled-ruler-mm-cpl`, `coffee-bean`, `foam`, `lavendar-cpl`, "
        "`tweezers-cpl`; acceptable but visibly grainy on `112MSDCF` and `113MSDCF`, which "
        "are the high-ISO members; visibly SOFT on `flower-bud-alone-cpl`, "
        "`pencil-flatter-angle-cpl`, `lead-1-cpl` and `leaf-2-cpl`; and outright DEFECTIVE "
        "on exactly two, `flowers-cpl` and `dry-erase-marker-head-cpl`. The headline the "
        "instruments had obscured: **the product is far closer to print-worthy than the "
        "7-clean-of-26 halo partition implied**, and the remaining risk is concentrated in "
        "a small named set rather than spread across the corpus.",
    ),
    (
        "1847",
        "ARGUED",
        "ORCH",
        "**THE TWO WORST HALO-FLAGGED SUBJECTS SHOW NO VISIBLE RIM AT 1:1, SO THE HALO "
        "PARTITION IS SUSPECTED OF FALSE POSITIVES AND NO PRINT DECISION MAY REST ON IT "
        "UNTIL MEASURED.** `flat-on-ruler-cpl` is flagged at overshoot **+4481.8 DN**, "
        "roughly 6.8 percent of full scale, which should be plainly visible; at six "
        "boundary-selected sites the brushed-metal striations resolve cleanly and the metal "
        "immediately adjacent to the dark tick marks reads at the same level as the far "
        "field. `tweezers-cpl` is flagged on bump 1542.3 with overshoot **−15502.0**, and "
        "the SIGN is the tell: a strongly negative overshoot means the near-silhouette "
        "backdrop is DARKER than the far field, which is not a bright halo at all, and this "
        "subject visibly has a genuine graduated backdrop in the scene. Candidate "
        "mechanisms, all unmeasured: a real scene gradient satisfying the non-monotone-ramp "
        "test with no artifact present; subject texture entering the near-silhouette "
        "annulus; or an unrepresentative far-field reference, so that the comparison is "
        "against the wrong baseline rather than the near field being wrong. THIS IS NOT A "
        "CLAIM THAT THE HALOS ARE ABSENT -- a low-frequency 6.8 percent lift spread over a "
        "wide region is genuinely hard to see without a side-by-side reference, and the "
        "eye that made this call had already misread a downscaled preview once the same "
        "night. The test that settles it is a **calibration ladder**: plant halos of known "
        "amplitude bracketing 4481.8 DN into a currently-clean subject and render them at "
        "1:1, establishing what the flagged statistic LOOKS like, plus a far-field "
        "reference taken from several independent locations to see whether the verdict is "
        "a property of the image or of the reference choice.",
    ),
    (
        "1848",
        "MEASURED",
        "ORCH",
        "**A VISIBLE CHROMA DEFECT IN A DELIVERED MASTER ON THE DEFAULT PATH, AND IT IS THE "
        "IMAGE-DOMAIN FACE OF AN ALREADY-MEASURED BUT UNDIAGNOSED CHANNEL ASYMMETRY.** On "
        "`dry-erase-marker-head-cpl` at y=1250 x=6060, dark marker ink against blown white, "
        "the ink boundary carries **blocky saturated magenta patches**, visible at 1:1 and "
        "unmistakable at 3x nearest-neighbour zoom. Measured over that 256 px rect as "
        "signed log2 channel ratios: R-G mean +0.0107 sd 0.1034 range **−0.830 to +1.651**, "
        "B-G mean +0.0137 sd 0.0758 range **−0.535 to +1.793**, so R reaches **3.1x** G and "
        "B reaches **3.5x** G at individual pixels. The chroma pane shows a saturated "
        "magenta rim on ONE side of the edge and cyan on the OTHER, which is the signature "
        "of R and B displaced with respect to G. THE CONNECTION: BUILD-CROP's null had "
        "already measured **G bit-identical at 100.0000 percent and 0 DN over 8.19M "
        "samples, while R differs on 4.82 percent at max 1402 DN and B on 12.51 percent at "
        "max 399 DN** -- green untouched, red and blue altered -- and could not diagnose "
        "the cause. That number and this picture are the same defect described twice. "
        "LEADING HYPOTHESIS, UNMEASURED: in a CFA-native pipeline the 2x2 Bayer cell "
        "carries two G sites but one R and one B, so a focus or weight field computed at "
        "G's density and applied to R and B at their coarser density, or with a half-site "
        "offset, makes R and B take their value from a different frame than G wherever the "
        "winner changes across a boundary. THE CONTROL THAT MUST PRECEDE ANY FIX: the Sony "
        "FE 100mm GM has real lateral CA and several stacks used the 2x teleconverter which "
        "roughly doubles it, so the single best-focused SOURCE frame must be measured "
        "across the same edge -- a smooth radially-oriented fringe of comparable magnitude "
        "means the optics did it and the merge is innocent. The most diagnostic single "
        "number is the **modal block size in native pixels**: 2 px implicates the Bayer "
        "cell, a pyramid level's footprint implicates the weight field's resolution, and a "
        "tile implicates the alignment tiling.",
    ),
]

ANCHOR = "| 1845 | DISCIPLINE | V-NEVERWORSE |"


def main() -> int:
    text = SYN.read_text(encoding="utf-8")
    lines = text.split("\n")

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR)]
    if len(hits) != 1:
        sys.stderr.write(
            f"ANCHOR NOT UNIQUE: {ANCHOR!r} matched {len(hits)} lines; refusing to write.\n"
        )
        return 2

    for _id, _s, _src, txt in ROWS:
        if f"\n| {_id} |" in text:
            sys.stderr.write(f"FACT {_id} ALREADY PRESENT; refusing to write.\n")
            return 2
        if "|" in txt:
            sys.stderr.write(f"FACT {_id} CONTAINS A RAW PIPE; would truncate the row.\n")
            return 2
        if txt.count("*") % 2 != 0:
            sys.stderr.write(f"FACT {_id} HAS AN ODD ASTERISK COUNT; italic never closes.\n")
            return 2

    new_rows = [f"| {i} | {s} | {src} | {t} |" for i, s, src, t in ROWS]
    at = hits[0] + 1
    lines[at:at] = new_rows

    with io.open(SYN, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines))

    print(f"inserted {len(ROWS)} rows after line {hits[0] + 1} (fact 1845)")
    print(f"new tail: {ROWS[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
