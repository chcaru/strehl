"""Insert facts 1843-1845 after row 1842 of the SYNTHESIS fact table.

Same guards as add_1841.py: the anchor must land exactly once, no raw `|` in
cell text (corpus_lint S1 -- an unescaped pipe silently DISCARDS every cell past
the header count), and an even asterisk count (S5 -- an odd count leaves an
italic span open). Both failures are invisible in the rendered table, so they
are prevented by construction rather than caught after the fact.

These three rows record V-NEVERWORSE's root-cause finding for the N-dependent
softening, the refutation of ORCH's dilution hypothesis, and the measurement
that disqualifies the confidence fix at depth.
"""

import io
import sys
from pathlib import Path

SYN = Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"

ROWS = [
    (
        "1843",
        "MEASURED",
        "V-NEVERWORSE",
        "**THE N-DEPENDENT SOFTENING IS THE SELECTION PREMIUM, NOT DILUTION OF THE "
        "WINNER'S SHARE.** ORCH hypothesised that `SoftPower` normalisation dilutes the "
        "best frame's weight as near-ties multiply with N, so deep stacks drift toward an "
        "average. **Refuted by a control the hypothesis cannot survive:** an argmax arm "
        "has winner share exactly 1.000 and `n_eff` exactly 1.000 at every N, verified to "
        "1e-9, so it **has no dilution to have** -- and it still softens **105 percent** "
        "(coffee-bubbles) and **98 percent** (112MSDCF) as much as the shipping merge. On "
        "both subjects the maximally diluting arm, plain mean, softens **least**. The "
        "EFFECT reproduces independently on different subjects with a different "
        "instrument: noise-corrected SNR at 0.30-0.35 cyc/px falls monotonically with "
        "depth, coffee-bubbles 0.49 to 0.37 to 0.30 at N=4/9/19 and 112MSDCF 1.53 to 1.37 "
        "to 1.28 at N=19/39/79. THE MECHANISM: on a synthetic twin carrying identical "
        "scene content, independent noise, and **no focus signal at all**, selecting "
        "rather than averaging multiplies manufactured 0.30-0.35 noise power by "
        "**2.16x, 6.79x, 24.82x** at N=4/9/19 (coffee-bubbles) and **23.24x, 80.78x, "
        "240.70x** at N=19/39/79 (112MSDCF). Every selecting arm grows noise about "
        "**1.6x faster than signal** (shipping, N=4 to 19: signal 1.476x, noise 2.419x). "
        "The plain mean is **the only N-invariant arm**, SNR flat at 0.68/0.68/0.69. This "
        "is the max-of-N order statistic operating on a noisy focus measure, so ANY "
        "reduction in selectivity helps flat regions while the premium keeps growing with "
        "N. CAVEAT STATED BY THE LANE: corr(dilution, softening) is −0.929 on "
        "coffee-bubbles but only −0.155 on 112MSDCF, so it does not replicate and must "
        "not be quoted; the refutation rests on the argmax control alone. The lane also "
        "recorded a **refuted pre-registration of its own**, having written 153.2 with "
        "interval 102.1-229.7 to disk before running 112MSDCF and measured 240.70, a miss "
        "4.8 percent outside; the interval was **not** widened afterward, and the fitted "
        "exponents N^1.566 and N^1.640 are labelled descriptive rather than predictive, so "
        "no 299-frame extrapolation may lean on a curve that has already failed once.",
    ),
    (
        "1844",
        "MEASURED",
        "V-NEVERWORSE",
        "**THE CONFIDENCE-DEPENDENT EXPONENT DOES NOT RESTORE N-INVARIANCE AND IS HARMFUL "
        "AT DEPTH; DO NOT ACCEPT IT ON AN N-INVARIANCE CRITERION.** Measured against the "
        "shipping merge on the softening between adjacent depths: coffee-bubbles 9 to 19 "
        "frames, shipping −0.1843 against confidence −0.1342, so the fix removes **27.2 "
        "percent** of the softening; but 112MSDCF 39 to 79 frames, shipping −0.0622 "
        "against confidence −0.0900, so the fix removes **−44.6 percent** -- it makes the "
        "deeper case **worse**. Depth is precisely where it matters: the owner's deepest "
        "capture is a **299-frame** bee and `flower-bud-alone-cpl` at N=205 is already "
        "refused by the print gate, so the merge degrades most on the most ambitious "
        "captures a print would come from. The lane additionally reported its own "
        "prediction refuted: it expected the fix to read identical to shipping at real "
        "detail, and at the top focus-response decile the fix runs `n_eff` **7.38 against "
        "1.78** (coffee-bubbles) and **19.22 against 3.60** (112MSDCF) -- right "
        "conclusion, wrong reason. CONSEQUENCE FOR THE MERGE DESIGN: N-invariance is "
        "necessary but **not sufficient** as an acceptance criterion, because the plain "
        "mean achieves it perfectly while destroying fine grain to 0.229x; it must always "
        "be paired with sharpness measured on the same pixels. The flat-region defect and "
        "the depth-softening defect need **different** remedies: exponent control "
        "addresses the first, while the premium must be attacked directly through control "
        "of the candidate set.",
    ),
    (
        "1845",
        "DISCIPLINE",
        "V-NEVERWORSE",
        "**A VERIFIER THAT TESTS FOR THE PRESENCE OF A WORD CANNOT DETECT A REVERSED "
        "CONCLUSION.** The lane's own report verifier checked that the string \"refuted\" "
        "appeared in the relevant section. Flipping that section's verdict to "
        "\"confirmed\" while leaving **every number in the document intact** passed **712 "
        "green checks**. The verifier now parses the verdict word itself rather than "
        "testing for its presence somewhere in the section. This is the same family as the "
        "presence-satisfied-by-a-duplicate defect recorded earlier in this corpus, and the "
        "same family as ORCH clearing the `--exposure` defect on a file hash: in all three "
        "cases the instrument answered a question adjacent to the one being asked. The "
        "general rule this project now holds: a check must be pinned to the specific "
        "claim it certifies, at a site where no duplicate or paraphrase can satisfy it, "
        "and it must be commissioned by a mutation that flips the CONCLUSION rather than "
        "one that merely perturbs a number.",
    ),
]

ANCHOR = "| 1842 | MEASURED | V-LINEAR |"


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

    print(f"inserted {len(ROWS)} rows after line {hits[0] + 1} (fact 1842)")
    print(f"new tail: {ROWS[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
