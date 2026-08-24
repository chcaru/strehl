"""Fold M87's turn-8 settlements. Facts 1310-1312, disciplines 645-646.

Includes the orchestrator's own error: halting M99 over a sign "conflict"
that was a reciprocal convention mismatch between brightness and correction
gain. Both probes always agreed.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1310, "**THE HALO RATIO IS 79x AGAINST THE WORST SINGLE FRAME, AND THE QUERY THAT PRODUCED THAT ANSWER FOUND A "
           "REAL DEFECT.** M87's operands, re-derived from the saved 299-frame array `out/10-iso-k.npy` rather than "
           "from its own report: mean **2.6199e-05**, SE **7.3145e-06**, **max 8.6107e-04**, and **94.31% of frames "
           "score exactly zero**. Merge **0.0680424**. Against the **worst** frame that is **79.02x**; against the "
           "mean it is 2597x; as a significance it is **9299 SE**.",
     "The orchestrator refused to fold `79x` because it did not follow from the operands as quoted, and asked rather "
     "than guessing between three candidate typos. **The number that could not be reconciled was itself the wrong "
     "one**: M87's §0 had described 2597 as \"~2600 SE above the frame null\", which is a *ratio to the mean* "
     "mislabelled as a sigma count. Both were corrected at source with operands now inline. **79x against the worst "
     "frame is the conservative and correct statement of the claim** -- 94.31% of frames score exactly zero, so a "
     "ratio to the mean flatters it. Refusing to fold an unreconciled number cost one question and bought a "
     "corrected foundational claim.",
     "M87 (MEASURED, re-derived from saved array, self-corrected); `docs/research/M87-occlusion.md` §0, P1"),

    (1311, "**THE M87/M99 \"SIGN CONFLICT\" WAS A RECIPROCAL CONVENTION MISMATCH; THE TWO PROBES ALWAYS AGREED.** "
           "`photometric.rs:390` computes `reference / frame_flux` -- the **correction-gain** convention -- while "
           "M87's −3.18% was quoted as **brightness** (`lev/ref − 1`). In one convention: M87 far-background "
           "brightness −3.13% = gain **+3.23%**; M99 brightness −5.04% = gain **+5.31%**. **Same sign.** Both say "
           "the early frames are dim and need boosting; the residual is region, not error. A planted signed ramp "
           "(−8/−4/0/+4/+8% materialised into the real cube) recovers **slope 1.000000, max relative error 1.8e-07, "
           "correct sign everywhere**.",
     "**The orchestrator halted M99's milestone over this, and was wrong to.** Two numbers were compared across two "
     "reports without checking they were expressed in the same convention, and reciprocal conventions flip a sign "
     "and look exactly like a defect. The orchestrator's follow-up hypothesis -- that M99's probe was a whole-crop "
     "median tracking the subject through focus -- was **refuted at source**: `photometric.rs` explicitly rejects "
     "patch medians, justifies it in its header, and carries a `defocus_alone_does_not_move_the_estimated_gain` "
     "test. That is the second briefing of the night issued from something other than a current read (see discipline "
     "640). **A halt on a convention mismatch is a worse failure than the one it was meant to prevent.**",
     "M87 (MEASURED, read at source); ORCH (error acknowledged); `crates/strehl-core/src/photometric.rs:390`"),

    (1312, "**FOR A FLUX PROBE, THE CHOICE OF STATISTIC DOMINATES THE CHOICE OF REGION BY TWO ORDERS OF MAGNITUDE.** "
           "M87's defocus-only null (blur conserves flux, so a correct probe must read zero), on **identical "
           "pixels**: whole-crop **median 2.942%** against whole-crop **mean 0.030%** -- a ratio of **98.8x** -- "
           "versus only **5.0x** for changing the region at fixed statistic.",
     "Independent corroboration of M99's core design decision -- its rejection of patch medians, previously "
     "supported by its own 18.2 vs 8.7 -- reached from a different region and a different statistic by an agent that "
     "did not set out to check it. A median tracks the subject through focus because the subject's histogram moves "
     "as it sharpens; the mean does not, because blur conserves flux. **M87 also failed its own area control and "
     "disclosed it**: a contiguous same-area block drifts 0.041% against its `distance>60` mask's 0.206%, because a "
     "mask hugging the subject leaks flux across a long perimeter. **Compactness beats subject-avoidance**; M87's "
     "region is sound but not optimal.",
     "M87 (MEASURED, null + failed area control, self-disclosed); corroborates M99"),
]

DISCIPLINES = [
    (645, "**Before declaring two measurements in conflict, express them in the same convention.** The orchestrator "
          "halted a milestone over M87's −3.18% against M99's +5.31%, which were **brightness** and **correction "
          "gain** -- reciprocals. In one convention they were +3.23% and +5.31%: the same sign, agreeing, differing "
          "only by region. A reciprocal convention flips a sign and is indistinguishable from a defect at a glance, "
          "and the cost of the check is reading one line of the source that computes it. **Escalate after the "
          "conversion, never before.** Fact 1311."),
    (646, "**A probe region should be chosen for compactness, not merely for avoiding the subject.** M87 registered "
          "an area control on its `distance_transform_edt(~mask) > 60` far-background region and **the control "
          "failed**: a contiguous block of the same area drifts 0.041% where the distance mask drifts 0.206%, five "
          "times worse, because a mask that hugs the subject has a long perimeter and leaks flux across all of it. "
          "Subject-avoidance is necessary and not sufficient; perimeter is the term that was missing. Fact 1312."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1309 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^644\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1310-1312 after line {fact_idx}, disciplines 645-646 after line {disc_idx}")


if __name__ == "__main__":
    main()
