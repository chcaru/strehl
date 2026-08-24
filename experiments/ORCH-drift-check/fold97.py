"""Fold M109's radial null: a degenerate statistic and a frame-wide support limit."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1457,
     "**A RADIAL-TREND INSTRUMENT RETURNED PERFECT CORRELATION ON STRUCTURELESS DATA, AND ONLY THE NULL "
     "CAUGHT IT.** M109 asked whether its residual magenta fringe is radial (which would make it M107's "
     "lateral-CA object) by binning into 20 annuli and taking a Spearman correlation. The denominator "
     "floor left **only 2 of 20 annuli** populated, both outer, so the statistic ran on two points -- "
     "**and a 2-bin Spearman is ±1 by construction.** The real arm read **+1.0000**. **The "
     "uniform-random null read +1.0000 as well.** Bar B10 was registered with this control in advance, "
     "failed at **exit 4** with both controls failing, and the instrument was left exactly as written.",
     "**Had the real arm been run alone it would have reported perfect radial structure, with a "
     "correlation coefficient, for a population that has none** -- and I would have been told RADIAL and "
     "believed it, because the number is not merely wrong but maximally confident. **The failure is not "
     "in the correlation; it is that a filter upstream silently reduced the sample to the size at which "
     "the correlation is a tautology.** This is the sharpest instance yet of a pattern the corpus keeps "
     "rediscovering (facts 1359, 1443, disciplines 738, 740): **an instrument that cannot detect its own "
     "inapplicability reports confidently on nothing**, and the only thing standing between that and the "
     "corpus is a null that was run because it was pre-registered rather than because anyone suspected "
     "trouble.",
     "M109-highlights section 12, bar B10 (registered, FAILED, instrument left untouched)"),
    (1458,
     "**THE MARKER FRAME HAS ALMOST NO OUTER-FIELD CONTENT, SO NO RADIAL QUESTION CAN BE ANSWERED ON IT "
     "-- INCLUDING A LATERAL-CA ONE.** Two independent denominators collapse in the same place. The "
     "partial-clip population is **empty in 11 of 20 annuli** with **90.1 %** of itself in two adjacent "
     "bins. An entirely separate luminance-edge denominator (Sobel p99, luma > 0.15) falls from **47 597 "
     "pixels at r = 0.225 to 88 at r = 0.825** -- a factor of **540** across comparable areas -- with "
     "nothing beyond r = 0.85 reaching the support floor. The subject is a macro subject in a band, with "
     "defocused background past r ≈ 0.7.",
     "**The corners are not measured as clean; they are not measured at all, and those are opposite "
     "findings that produce identical-looking output.** M109's own verdict was UNDECIDABLE rather than "
     "NOT-RADIAL, correctly refusing the conclusion its data could not support. **The consequence "
     "reaches beyond its milestone: lateral CA is zero at the optical centre and grows with field "
     "height, so any radial coefficient fitted on this subject is extrapolating into exactly the region "
     "where the effect it models is largest and where the frame holds no evidence.** A high goodness-of-"
     "fit over a narrow radial band says nothing about that extrapolation. M109 reached this "
     "requirement independently, without sight of `docs/captures-needed.md` section 24, which had "
     "already been amended tonight to demand fine detail reaching the corners -- **two agents arriving "
     "at the same missing capture from different directions is the strongest argument the corpus has "
     "produced for shooting it.**",
     "M109-highlights section 12, bars B11/B12 (both UNDECIDABLE-BY-SUPPORT, predicted in advance)"),
]

DISCIPLINES = [
    (743,
     "**Before asking whether an effect is present, ask whether the population samples the covariate at "
     "all -- and report that support check first.** M109 registered this as a precondition and it "
     "converted two unanswerable questions into *stated* ones instead of two spurious numbers. **The "
     "distinction that matters is between \"measured and absent\" and \"not measured\", because they "
     "produce identical-looking output** and only the first is a result. Concretely: **a trend statistic "
     "needs a minimum populated-bin count as a hard precondition, not a nicety** -- a denominator filter "
     "can silently reduce it to the degenerate case where the correlation is ±1 by construction (fact "
     "1457) -- and **the denominator profile must be printed before the gate**, so an UNDECIDABLE "
     "verdict ships with its evidence rather than as an assertion."),
    (744,
     "**When a bar disqualifies itself, leave the instrument untouched and register the next question "
     "separately.** M109's B10 failed its own controls; it left `radial.py` exactly as written, did not "
     "quote its readings (per the bar's own registered consequence), and opened B11 and B12 as new "
     "pre-registered bars rather than adjusting B10 until it passed. **Editing a failed instrument "
     "converts a reported failure into a silent repair**, and the repaired version carries the "
     "authority of the original registration without having earned it. The failed instrument is also "
     "evidence in its own right -- fact 1457 exists only because `radial.py` still demonstrates the "
     "degeneracy on demand."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1456 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^742\. ", l))
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
    print("folded facts 1457-1458, disciplines 743-744")


if __name__ == "__main__":
    main()
