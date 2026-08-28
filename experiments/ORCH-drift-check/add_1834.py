"""Insert facts 1834-1840 after row 1833 of the SYNTHESIS fact table.

Anchored on the full row-1833 prefix, and hard-errors if the anchor does not
land exactly once -- a bare replace would silently write nothing and the run
would still exit 0, which is the failure mode this project has been bitten by.
"""

import io
import sys
from pathlib import Path

SYN = Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"

ROWS = [
    (
        "1834",
        "MEASURED",
        "ORCH",
        "**EVERY RENDER IS UPSAMPLED, NO FRAME IS EVER PIXEL-EXACT INCLUDING THE "
        "REFERENCE, AND THE PENALTY GROWS WITH STACK DEPTH.** `fit_to_cover` "
        "(`crates/strehl-cli/src/align_cmd.rs`, doc L2225-2244, fn L2245) composes a "
        "uniform scale `k <= 1` about the plane centre into **every** frame placement so "
        "the reference grid maps strictly inside every source frame. Because the output "
        "keeps its pixel dimensions, the result is **upsampled by 1/k**. The doc comment "
        "states this outright and calls the alternative -- cropping -- follow-up work "
        "deferred because it \"would break the byte-frozen measurement path\". Measured "
        "from the `coverage` banner line at `3a312ba6`: `109MSDCF` N=22 -> **k = 0.9870** "
        "(1.3% of width dropped then upsampled); `bee-1-cpl` N=299 -> **k = 0.9321** "
        "(6.8%). Two consequences neither lane had isolated. (a) k SHRINKS AS N GROWS, "
        "because more frames accumulate more drift to cover, so there is an unconditional "
        "**N-dependent resampling blur** in every render, worst on the deepest stacks -- "
        "which are the showcase images. (b) Since `S_k` is composed into every placement, "
        "the reference frame, which would otherwise pass through untouched, is resampled "
        "too, so **no output pixel anywhere is uninterpolated**. This is a testing "
        "convenience charged to print quality. Candidate root cause for the owner's "
        "standing softness complaint; BUILD-CROP is implementing an opt-in unity-scale "
        "crop mode and V-REVIEW holds the adjudication.",
    ),
    (
        "1835",
        "MEASURED",
        "V-REVIEW",
        "**THE EXPOSURE FIX IS INDEPENDENTLY VERIFIED BY A LANE THAT DID NOT AUTHOR IT.** "
        "ORCH authored `5f367a94` and could not certify it. V-REVIEW, unasked, built it "
        "and re-ran the regression on `109MSDCF`: `--auto-exposure` now lands **identically "
        "to passing no flag at all** -- 0.0007% clipped, median 61122, 53.60% above 90% of "
        "ceiling, **all three statistics equal** across the two arms. The pre-fix HEAD "
        "figure was 92.03% clipped with a pure-white median. The banner's new "
        "`--auto-exposure is SUPERSEDED and applies NOTHING` is the tone-rule cancellation "
        "V-REVIEW had originally measured, now said out loud. Closes the regression: "
        "authored by one lane, measured by another, on a subject the author did not choose.",
    ),
    (
        "1836",
        "MEASURED",
        "V-REVIEW",
        "**A HEADLINE NUMBER THAT APPEARED THREE TIMES WAS ONE SATURATED ENDPOINT, NOT A "
        "STAGE -- WITHDRAWN BY ITS OWN AUTHOR.** V-REVIEW had reported a **+8.2707%** "
        "exposure overshoot, flagged as suspicious because it was *identical* across "
        "commanded 2x, 4x and 8x, with the responsible stage unisolated. Re-measured at "
        "`3a312ba6` on `109MSDCF`: the bright endpoint `--exposure 1` is **70.1609% "
        "clipped with median 65535**, and 73.62% of the frame sits above 90% of ceiling, so "
        "the unclipped survivors are compressed shoulder, not signal. All three pairs "
        "shared that one endpoint; that is why one number appeared three times. **There is "
        "no stage.** The instrument was reading saturation. WITHDRAWN as a gain error. What "
        "survives with both endpoints unsaturated: `-2 -> -1` and `-1 -> 0` deliver the "
        "commanded 2.0 **exact to seven decimals**, so the fix verdict is unchanged; the "
        "defensible highlight figure is the **+1.37%** below-half-ceiling residual. "
        "Generalises fact 1817: a structural metric on a saturated region reads CLEAN "
        "because saturation has no structure.",
    ),
    (
        "1837",
        "MEASURED",
        "V-REVIEW",
        "**THE `--exposure` CONTROL IS UNUSABLE IN THE POSITIVE DIRECTION AND WARNS OF "
        "NOTHING.** At `--exposure 0` the median is already **61122/65535 = 93.3% of full "
        "scale**, because the tone stage anchors p99.9 -> 0.90. Therefore **any positive "
        "`--exposure` saturates**, as the 70.16%-clipped `--exposure 1` arm shows, and the "
        "tool emits no warning. Not a false statement and not the auto-exposure regression "
        "-- a usability defect in the shipped user surface, which for a print-quality tool "
        "means the only brightness control a user reaches for silently destroys highlights. "
        "Routed to the `merge_cmd.rs` owner; queued rather than raced because BUILD-CROP "
        "holds that file.",
    ),
    (
        "1838",
        "MEASURED",
        "V-DILUTE",
        "**THE DILUTION HYPOTHESIS IS DEAD: THE MERGE GETS MORE COMMITTED AS N GROWS, NOT "
        "LESS.** ORCH hypothesised that deep stacks look worse because the merge averages "
        "ever more frames and dilutes detail. Measured on textured tiles at N=299: the "
        "merge averages the equivalent of **n_eff = 1.19 frames** -- effectively "
        "winner-take-all. The model required n_eff ~ 18. **Off by 15x.** The arithmetic was "
        "right and the input assumption was wrong: ORCH assumed competing frames sit at "
        "correlation r ~ 0.5-0.7, the measured value is **r ~ 0.36**, which gives "
        "share_winner = 0.92 at N=299. Independently consistent with V-HEADTOHEAD2's "
        "flat-region band-0 measurement of n_eff = 1.008. Deep-stack quality loss is "
        "therefore NOT a dilution effect and the fix must be sought elsewhere -- see fact "
        "1834 for the mechanism that does scale with N.",
    ),
    (
        "1839",
        "MEASURED",
        "V-DILUTE",
        "**FRAME COUNT PER SE DOES NOTHING: THE CLEANEST NULL IN THE CORPUS.** Merging 150 "
        "frames, versus the *same* 150 frames duplicated to N=300 with `STREHL_ALIGN=0`, "
        "gives confidence **0.4201 vs 0.4201** with **max |delta| = 1 DN** over the whole "
        "frame. Duplicating a stack adds frames and adds no information, and the merge "
        "correctly extracts no difference from it. Any future claim that some effect is "
        "caused by N alone must first beat this null, which cost one render to establish "
        "and rules out an entire class of explanation.",
    ),
    (
        "1840",
        "DISCIPLINE",
        "V-DILUTE",
        "**A PREDICTION THAT AN UNCHANGED SYSTEM ALREADY SATISFIES IS NOT A PREDICTION, AND "
        "A RANK STATISTIC WILL MANUFACTURE ONE.** ORCH pre-registered that confidence "
        "should rise with N. V-DILUTE showed the prediction was satisfiable **by a merge "
        "that changed nothing**: confidence is a rank statistic, and for the maximum of N "
        "draws E[v] ~ 1 - sqrt(2/(pi*N)), which rises with N **from sampling noise alone** "
        "-- 831.8 -> 953.8 across the tested range, with no merge behaviour involved. It "
        "bracketed the real measurement between a hard-max floor and a mean ceiling "
        "instead, and the measured confidence **falls**, 463 -> 419. Two rules follow. (1) "
        "Before pre-registering a directional prediction, compute what the statistic does "
        "under the null of an unchanged system; if the null already moves the right way, "
        "the experiment cannot discriminate. (2) Order statistics of noise drift "
        "monotonically with sample size, so any metric built on a max, an argmax or a rank "
        "is disqualified from testing an N-dependent claim until bracketed. Companion to "
        "the same lane's finding that its Experiment B was undiscriminating by "
        "construction, because the truncated arm had no in-focus data for the far half of "
        "the subject and *every* model predicts the full-range arm wins.",
    ),
]

ANCHOR = "| 1833 | MEASURED | V-LINEAR |"


def main() -> int:
    text = SYN.read_text(encoding="utf-8")
    lines = text.split("\n")

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR)]
    if len(hits) != 1:
        sys.stderr.write(
            f"ANCHOR NOT UNIQUE: {ANCHOR!r} matched {len(hits)} lines; refusing to write.\n"
        )
        return 2

    for _id, _status, _src, _txt in ROWS:
        if f"\n| {_id} |" in text:
            sys.stderr.write(f"FACT {_id} ALREADY PRESENT; refusing to write.\n")
            return 2

    new_rows = [f"| {i} | {s} | {src} | {t} |" for i, s, src, t in ROWS]
    at = hits[0] + 1
    lines[at:at] = new_rows

    out = "\n".join(lines)
    with io.open(SYN, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print(f"inserted {len(ROWS)} rows after line {hits[0] + 1} (fact 1833)")
    print(f"new tail: {ROWS[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
