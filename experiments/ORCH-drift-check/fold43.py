"""Fold the attribution of the owner's complaint. Fact 1297, discipline 637."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1297, "**THE OWNER'S \"THOSE STACKS DON'T LOOK TOO GOOD YET\" IS ABOUT SHARPNESS, NOT EXPOSURE, ESTABLISHED BY "
           "ELIMINATION.** The review artefact he was shown (`REVIEW-CROPS.png`, `REVIEW-FULL.png`) is built by "
           "`contact_sheet.py:60` from `*-exposed.tif`, **not** from the dark `*-srgb.tif`. Those exposed files are "
           "written by `gallery.py:135` using percentile-to-target gain in linear light with a clipping budget and a "
           "binary-search backoff -- **the same algorithm M100 derived independently** hours later and 30 files away. "
           "So the frames under review were already correctly exposed, and brightness cannot be what he saw.",
     "This **redirects the priority**. M100's exposure work is still correct and still worth shipping -- it fixes the "
     "default path, and `lead-1` at +3.74 stops is indefensible -- but it is **not** the fix for the complaint that "
     "prompted tonight's work. What remains after exposure is eliminated is the measured **2.34x high-frequency "
     "deficit** (fact 1286), of which the coverage rescale is **64.2%** (fact 1287) and the demosaic choice bounds "
     "the rest (fact 1292). A macro photographer inspecting 100% crops is looking at exactly the band where that "
     "deficit lives. **Predicted outcome of the rescale fix alone: the render moves from 2.34x below a single "
     "rawpy-AHD frame to about 1.35x below it**; the demosaic upgrade is the second free win and the two compose. "
     "Registered here before either lands, so it can be scored rather than claimed.",
     "ORCH (DERIVED by elimination from MEASURED components); `experiments/ORCH-drift-check/contact_sheet.py:60`, "
     "`gallery.py:110-137`, facts 1286, 1287, 1292, 1293"),
]

DISCIPLINES = [
    (637, "**Before attributing a complaint, establish which artefact the complainant actually looked at.** Hours "
          "went into deciding whether the owner judged the dark render or the exposed one, and the answer was sitting "
          "in one line of the script that built the thing he was shown. Two consequences: the fix you are most "
          "excited about is not automatically the fix for the complaint you received, and a defect being real is "
          "independent of it being *the* defect -- exposure was genuinely broken and genuinely not the answer. When "
          "elimination is the method, name what was eliminated and how, because an argument from elimination is only "
          "as strong as the completeness of the list. Facts 1293, 1297."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1296 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^636\. ", l))
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
    print(f"folded fact 1297 after line {fact_idx}, discipline 637 after line {disc_idx}")


if __name__ == "__main__":
    main()
