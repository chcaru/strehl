"""Fold the CA/kernel coupling and the orchestrator's sequencing failure."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1452,
     "**THE SHIPPED DEFAULT IS PAYING FOR CHROMATIC-ABERRATION SUPPRESSION IN BLUR, AND THE CORRECTION "
     "THAT WOULD LET IT STOP IS BUILT AND UNWIRED.** Three results only compose when read together. "
     "**(a)** Fact 1374: `nearest` resolves thorax hairs the shipped `catmull-rom` merges into a soft "
     "mass, but is unshippable because it *\"visibly amplifies chromatic fringing\"*. **(b)** M95's "
     "differential-chroma-overshoot table -- `nearest` **0.000000**, `bilinear` **0.000000**, "
     "`catmull-rom` **2.480280**, `lanczos3` **4.852171**, monotone kernels provably unable to overshoot "
     "and reading exactly zero -- shows the two zero-DCO kernels sit at **opposite ends of sharpness**, "
     "so DCO is not a sharpness metric in disguise; and a kernel cannot create *lateral* CA at all, "
     "since it shifts every channel alike. **(c)** Fact 1449: `optics.rs`, holding the measured "
     "`-704.5 ppm` lateral-CA correction (`R^2 = 0.9969`, fact 1414), has **no consumer anywhere in the "
     "pipeline.**",
     "**So the fringing `nearest` reveals was never made by `nearest` -- it is optical, it is already in "
     "the data, and `catmull-rom` has been hiding it by low-passing the hairs along with it.** That "
     "reframes the default kernel from a quality choice into a **concealment**: the pipeline is "
     "spending sharpness, everywhere, to suppress an artifact it already knows how to remove exactly. "
     "**The dependency runs CA-correction -> sharper kernel, and both halves already exist**, which "
     "makes wiring `optics.rs` a prerequisite for fact 1420's +0.1343 dex rather than the independent "
     "3-px-at-the-corner tidy-up I first briefed it as. Two agents measured the two halves without "
     "either being able to see the other; **the composition was available only from the orchestrator's "
     "seat, and only because a third instrument (`unwired.py`) had just established that (c) was "
     "true.**",
     "ORCH synthesis of facts 1374, 1414, 1420, 1449 + M95/M85's DCO table (ARGUED from MEASURED parts)"),
]

DISCIPLINES = [
    (734,
     "**When a verified patch's stated blocker is \"file ownership\", that is a scheduling failure by "
     "the orchestrator, and it must be escalated as one rather than re-measured.** Fact 1420 said it in "
     "as many words -- *\"the largest single measured quality gain available to the shipping binary... "
     "already written and controlled... **the blocker is file ownership, not evidence** -- `align.rs` "
     "has been written by M86, M97 and M103 in the last twelve hours. **Sequencing it, rather than "
     "measuring it further, is the remaining work**\"* -- and it still sat unlanded, because the one "
     "actor who can resolve a lane conflict is the one who assigns lanes. **A subordinate cannot "
     "unblock this by working harder; it can only keep measuring, which is what happened.** Treat the "
     "phrase \"blocked on ownership\" in any report as an interrupt addressed to the orchestrator "
     "personally, and answer it in that turn. Compare discipline 729: **seven unanswered requests for a "
     "`merge.rs` lane produced the same waste by the same mechanism, and I did not recognise the second "
     "instance from the first.**"),
    (735,
     "**Ask each long-running agent what it is blocked on, and read the answers against each other -- "
     "the composition is often invisible from every individual seat.** Fact 1452 exists only because "
     "three findings from three agents were held side by side: a kernel result that could not ship "
     "because of fringing, a chroma measurement showing the fringing was optical rather than kernel-"
     "made, and an inventory showing the optical correction was built and connected to nothing. **Each "
     "agent had one third and no way to see the other two.** The orchestrator's distinctive product is "
     "not more measurement; it is the join, and the join only happens if the parts are asked for and "
     "actually read."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1451 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^733\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded fact 1452, disciplines 734-735")


if __name__ == "__main__":
    main()
