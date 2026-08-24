"""Fold the occlusion-contour finding and the one-sided bar that missed it.
Facts 1360-1362, disciplines 676-677.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1360, "**THE BOUNDARY-ELECTED POPULATION IS OCCLUSION CONTOURS, NOT MISSING COVERAGE.** MEASURED at "
           "`ef071f6` on `flowers-cpl` (176 frames) via `argmax-baseline --index-map`: **29.81 % of pixels elect "
           "frame 0 against 0.18 % electing frame 175** -- a **165x** asymmetry -- and they are spread evenly by "
           "region (centre 30.79 %, outer ring 27.53 %). Frame-0 election runs at **6.39 % in the lowest-contrast "
           "decile and 49.98 % in the highest**, a **7.8x concentration in HIGH-contrast pixels**, with a "
           "shuffled-map null control at **1.01x**. The rendered map shows **thin curved ribbons tracing the petal "
           "edges** -- contours, not a region.",
     "**This independently reproduces M96's disconnected-competitive-set result on a different stack, by a "
     "different method, with a different instrument.** M96 found *\"thin contours lying exactly along depth and "
     "occlusion boundaries\"* inside the shipped election; this finds the same geometry in the naive argmax index "
     "map. At an overlapping petal edge the pixel is a two-layer composite, **no frame contains a clean "
     "measurement of it**, the through-focus response has no interior optimum, and the election runs to the end of "
     "the range -- landing on frame 0 because that is where the search bottoms out, not because anything is in "
     "focus there. **Three hypotheses were tested and killed to get here**: tie-breaking toward the low index "
     "(refuted, and in the opposite direction -- the effect concentrates in high contrast, not low), an "
     "under-bracketed subject (refuted -- contours, not a surface), and a distant backdrop (refuted -- centre and "
     "periphery are equal).",
     "ORCH (MEASURED at `ef071f6`: `boundary_where.py`, `boundary_tiebreak.py`, `boundary-map.png`)"),

    (1361, "**`flowers-cpl` IS GEOMETRICALLY HARD, NOT BADLY SHOT, AND `boundary %` IS CLOSER TO AN OCCLUSION "
           "DETECTOR THAN A COVERAGE STATISTIC.** DERIVED from fact 1360 with the fact 1357 ranking: `flowers-cpl` "
           "33.74 %, `bee-3-cpl` 1.00 %, `leaf-2-cpl` 0.12 %. A flower of overlapping petals carries far more "
           "occluding edge per unit area than a bee or a leaf, and the statistic tracks that rather than tracking "
           "bracket span.",
     "**This withdraws the advice I had already written into `captures-needed.md` section 23.** That section told "
     "the owner to re-shoot with a wider sweep; a wider sweep would not have moved the number, because the missing "
     "information is not at either end of the bracket -- it is in **no frame at all**. Section 23 has been "
     "rewritten to say so, including the retraction. Two consequences worth carrying: **subject choice is a real "
     "variable** and self-occluding subjects are the hard case for every stacker including this one; and **the "
     "occlusion workstream now has a large, visible, real-photograph test population** that it previously "
     "lacked -- 33.74 % of a 33 MP frame, localised to contours. Genuine coverage failure remains distinguishable "
     "and would look different: a contiguous *region* rather than contours, concentrated in the low-contrast "
     "decile rather than the high one.",
     "ORCH (DERIVED at `ef071f6` from facts 1357 and 1360; `captures-needed.md` section 23 rewritten)"),

    (1362, "**A PRE-REGISTERED BAR WRITTEN ONE-SIDED REPORTED A 7.8x EFFECT AS A NULL.** `boundary_tiebreak.py` "
           "registered *\"above 3x reads as contamination; below 1.5x reads as depth\"* and measured **0.13x**, so "
           "it printed **\"VERDICT: DEPTH -- frame-0 election is independent of contrast\"**. The measurement is "
           "the reciprocal of a **7.8x concentration in the opposite direction**, which is a strong result and not "
           "a null at all. The null control passed at 1.01x, so the instrument was sound; only the bar was wrong.",
     "**The bar was written assuming the effect could only run one way, and a ratio below 1 was never given a "
     "meaning.** This is worse than an uninformative statistic: it produced a confident, wrong verdict in the "
     "project's own pre-registration idiom, which is exactly the form most likely to be believed and folded. It "
     "was caught in about one second by looking at the rendered map, which showed contours where the number had "
     "reported nothing. **Second occasion in one session that a scalar lost to an image** -- fact 1359 is the "
     "other, where a Laplacian metric rated a visible mosaic artifact 2.73x sharper than the correct render.",
     "ORCH (self-disclosed; `boundary_tiebreak.py` verdict block, overruled by `boundary-map.png`)"),
]

DISCIPLINES = [
    (676, "**Pre-register bars two-sided, and state in advance what a result on the *other* side of 1.0 would "
          "mean.** A ratio bar of the form *\"above 3x means A, below 1.5x means B\"* silently assumes the effect "
          "cannot invert, so a strong inverted effect is scored as the null: 0.13x -- a 7.8x concentration the "
          "other way -- was reported as *\"independent of contrast\"*. **If a statistic can in principle run "
          "either way, every bar must have three branches, not two.** Fact 1362."),
    (677, "**Render a spatial statistic as a map before interpreting any scalar summary of it.** A boundary rate, "
          "a confidence rate and a re-election rate are all fields, and their *shape* carries the mechanism while "
          "their mean carries almost none of it. Region summaries said centre 30.79 % against periphery 27.53 % -- "
          "near-identical, and read as *\"concentrated nowhere\"* -- while the map showed the population is thin "
          "contours tracing occlusion edges, which no region-average could have expressed because contours run "
          "through every region equally. **The scalar was not merely weak here, it was actively misleading in two "
          "independent ways at once.** Facts 1360, 1362."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1359 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^675\. ", l))
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
    print(f"folded facts 1360-1362 after line {fact_idx}, disciplines 676-677 after line {disc_idx}")


if __name__ == "__main__":
    main()
