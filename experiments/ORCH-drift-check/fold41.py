"""Fold the demosaic spread, the --demosaic reconciliation, exposure and seams.

Facts 1291-1294, disciplines 634-635.
Splice the discipline block first; fact rows carry exactly 5 unescaped pipes;
asserts run before any write.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1291, "**THE DEFAULT OUTPUT IS BINNED, BUT NO FILE THE OWNER COMPLAINED ABOUT WAS.** `main.rs:79-83` documents the "
           "default as binned, camera-native RGB at **half the sensor's linear resolution**, byte-frozen as the "
           "measurement surface. But `gallery.py:63` and `gatesweep.py:62` both invoke `stack ... --srgb --demosaic`, "
           "so **every render in the owner's gallery and in the gate ladder took the full-resolution "
           "Malvar-He-Cutler path**.",
     "This reconciles M95's \"8.2 MP from a 32.9 MP capture\" with fact 1284's \"the merge is not binned\": the two "
     "measurements were made on **different files** and both are correct. The orchestrator dispatched M95 to fix the "
     "binning, then corrected itself, then withdrew half of the correction -- three messages, two of them wrong, "
     "because it reasoned about the default instead of reading the invocation. **Consequence for the owner's "
     "complaint: de-binning cannot explain it, and the byte-frozen default must not move or every number in this "
     "corpus is invalidated.**",
     "ORCH (MEASURED, read from the invocations); `crates/strehl-cli/src/main.rs:79-83`, "
     "`experiments/ORCH-drift-check/gallery.py:63`, `gatesweep.py:62`"),

    (1292, "**DEMOSAIC CHOICE ALONE SPANS 0.3518 dex -- MORE THAN THE ENTIRE SOFTNESS DEFICIT.** Same ARW, same tile "
           "set, same normalisation, six algorithms, over 0.30-0.48 cyc/px: **LINEAR -3.2552, VNG -3.0523, PPG "
           "-3.0457, AHD -3.0058, DHT -2.9438, AAHD -2.9033**. Controls: decoding twice with AHD agrees to "
           "**0.000000 dex**, and LINEAR reads lowest as required.",
     "The +0.1301 dex left unexplained by fact 1287 is **37% of this spread**, so demosaic difference is a sufficient "
     "explanation for the residual and no further mechanism need be invented. **This bounds; it does not identify** -- "
     "it does not prove the residual IS demosaic. The forward-looking half matters more: `demosaic.rs:19-48` ships "
     "Malvar-He-Cutler and says in its own docstring that \"it is not the best demosaic available. AHD, DDFAPD/DLMMSE, "
     "RCD and the learned methods all beat it.\" MHC should sit near the VNG/PPG rung, so **moving to an RCD or "
     "AAHD-class demosaic is worth up to ~0.15 dex and stacks with the rescale fix of fact 1287**; together they would "
     "put the render above a single rawpy-AHD frame rather than 2.34x below it. `AGENTS.md` bars the GPL "
     "implementations -- the algorithms are publishable, the code is not.",
     "ORCH (MEASURED, both controls passed); `experiments/ORCH-drift-check/demosaic_spread.py`"),

    (1293, "**THE VIEWING RENDERS ARE UNDEREXPOSED BY +1.54 STOPS ON `bee-3-cpl` AND +3.74 ON `lead-1-cpl`.** M100 "
           "measured per-stack choices of bee-2 +1.54, bee-3 +1.54, coffee-bean **-0.18**, flat-on-ruler +1.96, foam "
           "**-0.32**, highly-angled-ruler +1.19, lead-1 +3.74. It is a two-sided correction, not a brightener: "
           "`coffee-bean` goes from **1.4197%** blown to **0.0026%**. Two independent derivations agree -- M100 chose "
           "+1.54 from the render's luminance percentile, the orchestrator +1.57 from the RAW background level, "
           "**0.03 stops apart**, and `gallery.py`'s own gain lands within **0.013 mean display level** of M100's.",
     "**This is almost certainly a larger share of the owner's \"those stacks don't look too good\" than anything in "
     "the top octave**, and unlike the sharpness work it was already implemented and tested when found. A "
     "side-by-side of `bee-3-cpl` at three exposures confirms it visually: the plain `--srgb` render is dark and "
     "muddy with a grey background where the subject is on white. M100 measured a **clipping cliff** -- 0.0372% at "
     "target 0.90 against 0.7663% at 0.95, an **18x jump for 0.07 stops** -- because the background is a large flat "
     "field whose pixels cross 65535 together, so the target is not a free parameter. The choice is invariant to "
     "`--gate` (0.00 stops across 0/1/2/4) but **not** to frame count (+1.47/+1.48/+1.54 at 30/60/299).",
     "M100 (MEASURED; B3 and B4 each failed on 1 of 7 stacks and are reported, not rounded); "
     "`docs/research/M100-exposure.md` §3"),

    (1294, "**THE VISIBLE MERGE SEAMS ARE ISOLATED, NOT PERIODIC -- THEY FOLLOW CONTENT, NOT A TILING GRID.** Profiling "
           "mean \\|second difference\\| along each axis of the rendered `bee-3-cpl` and testing the strongest 12 peaks per "
           "axis for regular spacing: horizontal gaps 452/916/30/7/77/118/212/82/58/172/34 px, **0% within 5% of the "
           "median**; vertical **9%**. Both axes fail the periodicity test.",
     "This distinguishes two defects with completely different fixes. A regular grid would mean a structural tiling "
     "artefact in the merge; isolated content-following steps mean the **elected-frame index map has sharp boundaries "
     "and the frames are misregistered across them**, which is the classic selection artefact and is what the "
     "regularised winner field exists to remove. Fact 84 already prices regularisation at **-35% absolute error** and "
     "it remains **verified but unbuilt**. Note the visual identification of the seams is an OBSERVATION; only the "
     "non-periodicity is measured.",
     "ORCH (periodicity MEASURED, seam identification OBSERVED); "
     "`experiments/ORCH-drift-check/seam_check.py`"),
]

DISCIPLINES = [
    (634, "**Read the invocation that produced the file before drawing any conclusion from it -- the default path is "
          "almost never the path your artefacts took.** The orchestrator spent three messages and two reversals on "
          "whether the output was binned, arguing from `main.rs`'s documented default, while both of its own render "
          "scripts had been passing `--demosaic` all along. One grep of `gallery.py` settled what an hour of "
          "spectral measurement had left contested, and it should have come first. This is the same failure as "
          "mistaking a module filename for a command name, one level up: **a documented default is a claim about the "
          "program, not about your data.** Fact 1291."),

    (635, "**When a bound is offered as an explanation, state in the fact whether it identifies or merely permits.** "
          "The demosaic spread of 0.3518 dex makes a 0.1301 dex residual unsurprising, which is genuinely useful -- it "
          "means no new mechanism need be invented. It is **not** evidence that the residual *is* demosaic, and a "
          "fact that blurs the two would let a later milestone close an open question it never actually answered. "
          "Write the distinction into the fact itself rather than only into the script's docstring, because the fact "
          "is what gets read. Fact 1292."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1290 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^633\. ", l))
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
    print(f"folded facts 1291-1294 after line {fact_idx}, "
          f"disciplines 634-635 after line {disc_idx}")


if __name__ == "__main__":
    main()
