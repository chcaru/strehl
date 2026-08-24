"""Fold the three-pixel closed negative.
Facts 1387-1388, discipline 691.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1387, "**THE THREE PIXELS THE ALIGNMENT WATERSHED DID NOT MOVE ARE DEEP-SHADOW QUANTISATION COLLISIONS, "
           "NOT A GEOMETRIC ARTIFACT. CLOSED NEGATIVE.** MEASURED. All three are **interior** -- none touches "
           "row 0, row H-1, col 0 or col W-1 -- refuting the edge/corner hypothesis. All three sit in the "
           "**darkest 2.7%** of the frame (luminance percentiles **1.28, 0.14, 2.66** against a median of "
           "11 502). At sample level (n = 29 572, not n = 3): **67.7% of all equal samples fall in the darkest "
           "three deciles and 36.9% in the darkest one**, 3.7x over uniform. Median per-pixel delta is "
           "**smallest in the darkest and brightest deciles** (522 and 487 DN) and **largest in the mid-tones** "
           "(2644 DN at decile 5). The shared column `x=2115` is coincidence: 24 equal samples against a mean "
           "of 8.31, but **89 of 3516 columns meet or beat it**.",
     "**Recorded as a closed negative so it is not re-investigated.** Mechanism, ARGUED by the verifier: "
     "alignment displaces sampling sub-pixel, so the induced change scales with the **local gradient**; in "
     "deep shadow the frame is low-signal background with little gradient, so the change often falls below one "
     "u16 rounding step and all three channels round to the same integer. **Corroborated by an asymmetry the "
     "hypothesis predicts and nothing else explains:** equal samples per channel are **R 14 498, G 4 170, "
     "B 10 904** -- green collides ~3x less often, consistent with G being averaged over **two** CFA sites per "
     "2x2 quad against one each for R and B, giving finer effective quantisation and fewer collisions. That is "
     "a CFA-structural prediction, not a fit.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED, turn 4), answering ORCH's fact-1380 question"),

    (1388, "**TWO ARMS OF THE THREE-PIXEL EXPLANATION REMAIN OPEN AND WERE REPORTED RATHER THAN DROPPED.** "
           "(a) **Local flatness is NOT established**: the three sit at flatness percentiles **8.6%, 40.5%, "
           "30.3%** against comparable-brightness neighbours -- only one is decisively flat. (b) Even "
           "conditioning on darkness, **three is ~40x above what channel-independence predicts** (~0.07 "
           "expected in decile 1); the residue is presumably within-pixel correlation, since all three "
           "channels see the same shift and the same local gradient, but **that was not measured**.",
     "**The verifier ran the flatness test, got an equivocal answer, and reported it against its own "
     "hypothesis.** Darkness is supported; flatness -- the other half of the low-gradient story -- is not, and "
     "the report says so rather than quietly resting on the one arm that worked. Item (b) is the sharper "
     "residue: the mechanism as stated under-predicts the observation by 40x, so it is **incomplete rather "
     "than confirmed**, and the fact is filed with that gap visible. A closed negative with two named open "
     "arms is more useful than a clean one, because it tells the next reader exactly where to push if the "
     "question ever matters.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED, self-disclosed gaps)"),
]

DISCIPLINES = [
    (691, "**A residue of n = 3 supports no statistics of its own; test its mechanism against the population "
          "it came from.** Three unmoved pixels invited a geometric story (edge, corner, column) and every "
          "such story was refuted -- but the refutation came from n = 29 572 samples, not from the three. "
          "Where a handful of outliers is all the evidence there is, find the larger population they are "
          "instances of and characterise **that**; the outliers can then only be reported as consistent with "
          "it, which is the honest strength of the claim. Facts 1387, 1388."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1386 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^690\. ", l))
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
    print(f"folded facts 1387-1388 after line {fact_idx}, discipline 691 after line {disc_idx}")


if __name__ == "__main__":
    main()
