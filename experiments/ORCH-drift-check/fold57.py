"""Fold the retimed README claim, the thesis demonstration, and my regex error.
Facts 1354-1356, disciplines 672-673.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1354, "**THE README'S SHIPPED END-TO-END CLAIM IS STALE BY A FACTOR OF 2.2, AND THE FULL-RESOLUTION RENDER IS "
           "FREE.** MEASURED at `925d03d`, `bee-3-cpl`, 299 frames, warm, best of 3: default binned linear "
           "**51.43 s**, `--srgb --auto-exposure` at 7032 x 4688 **51.60 s**, `--srgb --binned` **53.10 s**. The "
           "README claims **23.1 s**.",
     "**M97's ledger row warned at dispatch that 23.1 s was a shipped claim that must be re-measured rather than "
     "assumed, and it was right.** The gap is alignment: `885e9f7` wired it into `strehl stack` default-ON after "
     "that number was taken, and it costs roughly **28 s** on a 299-frame stack. The second result is the more "
     "useful one: **M95's full-resolution demosaic costs +0.33 % over binned** (51.60 s against 51.43 s) and is "
     "within run-to-run spread of it, so doubling the linear resolution of the viewing render is free. `--binned` "
     "measuring *slower* than full resolution is inside the same spread and should not be read as a real ordering.",
     "ORCH (MEASURED at `925d03d`: `retime.py`, best of 3 warm runs)"),

    (1355, "**SELECTION VERSUS ESTIMATION, MEASURED ON THE OWNER'S OWN PHOTOGRAPH: 84.5 % LESS NOISE IN THE FLAT "
           "REGION AT NO VISIBLE COST IN DETAIL.** `leaf-2-cpl`, 182 frames, both arms at a **fixed** "
           "`--exposure=3.19` so the merge is the only difference. `--gate 0` reports **mean n_eff 1.000, "
           "n_eff = 1 at 100.00 % of pixels** -- confirmed pure selection, every output pixel exactly one frame's "
           "pixel. `--gate 2` reports **mean n_eff 15.077**, with 21.95 % of pixels still taking a single frame. In "
           "a 200 x 200 flat patch chosen on the **mean of both arms** so neither selected it, the Laplacian-"
           "residual noise falls **0.006381 -> 0.000987**, a ratio of **0.1546x**, equivalent to averaging "
           "**41.8 frames**. The matched detail crop is **visually indistinguishable** between the two arms.",
     "**The two numbers are different quantities and must not be conflated.** The tool's own model predicts a "
     "whole-image sigma gain of **0.4439x** at this gate, against **0.1546x** measured -- and both are right: the "
     "model's is the image-wide mean including the 21.95 % of pixels that average nothing, while the measurement is "
     "the flattest patch in the frame, which is exactly where the focus response is most ambiguous and therefore "
     "where the most frames fall inside the gate. **The flat-region figure is a best case and is quoted as one.** "
     "It is also the case the eye judges, because noise is seen in flat regions and not in texture. This is the "
     "thesis of the project -- *estimation, not selection* -- reduced to a single pair of images, and it is the "
     "first time the corpus has demonstrated it on a real photograph rather than a metric.",
     "ORCH (MEASURED at `925d03d`: `thesis_demo.py`, `C:\\dev\\strehl-out\\ORCH-thesis\\`)"),

    (1356, "**A REGEX SCRAPING A NUMBER OUT OF PROSE SCRAPED A CITATION INSTEAD, AND REPORTED IT AS A "
           "MEASUREMENT.** `thesis_demo.py` extracted the effective frame count with `n_eff[^0-9]*([0-9.]+)` and "
           "printed **`n_eff 212`** for *both* arms. The tool's report contains the sentence *\"Fact 212 measured "
           "nwide = 3 at full rule from this NOISE gate\"* immediately after the string `n_eff`, so the pattern "
           "matched a **fact number**. The real values are 1.000 and 15.077, in a fixed-width table further down.",
     "**The tell was free and I nearly walked past it: identical values for two arms that must differ.** A pure "
     "selector and a 15-frame average cannot both average 212 frames, and 212 is not even a possible n_eff on a "
     "182-frame stack. Caught before the number reached the owner, but only because the arms were designed to "
     "disagree -- **had I run one arm, `n_eff 212` would have been folded as a fact.** The corpus's own habit of "
     "citing fact numbers inline is what made its report hostile to scraping, which is a cost of that habit worth "
     "knowing.",
     "ORCH (self-disclosed; corrected against the fixed-width n_eff table)"),
]

DISCIPLINES = [
    (672, "**Parse machine output from its structured table, never by regex over its prose.** This corpus writes "
          "reports that cite fact numbers inline, so a pattern anchored on a label will sooner or later match a "
          "citation rather than a value -- `n_eff[^0-9]*([0-9.]+)` returned **212**, the fact number in the "
          "sentence following the label. **If a value must be scraped, anchor on the column structure and assert "
          "the result is in a possible range**: 212 effective frames from a 182-frame stack is impossible on its "
          "face and one bound would have caught it. Fact 1356."),
    (673, "**Design comparisons so the arms must disagree, because agreement where disagreement is compulsory is "
          "the cheapest instrument check there is.** The bogus `n_eff` was caught by nothing more than a pure "
          "selector and a 15-frame average reporting the same number. **A single-arm run would have folded it as a "
          "fact.** This generalises past parsing: whenever an arm's expected behaviour is qualitatively different, "
          "print the quantity for every arm and look at them together before interpreting any one of them. "
          "Fact 1356."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1353 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^671\. ", l))
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
    print(f"folded facts 1354-1356 after line {fact_idx}, disciplines 672-673 after line {disc_idx}")


if __name__ == "__main__":
    main()
