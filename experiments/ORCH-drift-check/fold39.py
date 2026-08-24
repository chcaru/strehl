"""Fold the full-resolution comparison into SYNTHESIS.md.

Facts 1284-1286, discipline 631.
Mechanics as fold38.py: disciplines are BELOW the fact table, so splice the
discipline block first; a fact row is exactly 5 unescaped pipes; all asserts run
before any write.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1284, "**THE MERGE OUTPUT IS NOT 2x-BINNED: IT CARRIES GENUINE DETAIL TO THE SENSOR'S NYQUIST.** "
           "Measured against two anchors built from `DSC00150.ARW` (frame 149, the merge's own reference frame, so its "
           "warp is identity) decoded at full resolution by rawpy/LibRaw -- a decoder sharing no code with strehl. Mean "
           "log10 normalised power over 0.30-0.48 cyc/px: **FULL -3.0058, BINNED -5.6621, MERGE -3.3751**. Anchor "
           "separation **2.6563 dex**. On the scale 0=BINNED, 1=FULL the merge sits at **0.861**, and reads nearer FULL "
           "in all 30 frequency bins.",
     "This refutes the orchestrator's reading of M95's \"8.2 MP from a 32.9 MP capture\" as a claim about the final "
     "file's luma resolution, and it was measured *after* M95 had already been dispatched to fix it -- the correction "
     "was issued mid-flight before the fix was built. `--gate 0` is what makes the comparison fair: fact 1283 measured "
     "mean n_eff = 1.000 with 100.00% of pixels at n_eff = 1, so every merge pixel carries single-frame noise and "
     "broadband noise cancels out of the high-frequency comparison instead of driving it. Tiles are the 40 sharpest of "
     "the single frame, so the single frame is in focus where it is judged.",
     "ORCH (MEASURED, independent decoder, anchor-separation gate enforced); "
     "`experiments/ORCH-drift-check/fullres_check.py`"),

    (1286, "**THE MERGE IS 2.34x DOWN IN HIGH-BAND POWER ON A SINGLE IN-FOCUS FRAME, AND THAT IS THE SOFTNESS.** "
           "Over 0.30-0.48 cyc/px the gate-0 render sits **0.3693 dex** below the same scene decoded from one ARW at "
           "full resolution -- a factor of **2.34x in power**, about **1.53x in amplitude** -- with the deficit growing "
           "monotonically with frequency.",
     "This is the first measurement that both matches the owner's complaint and is large enough to explain it: it is "
     "everywhere rather than at the edges, and it grows toward Nyquist. It is NOT binning (fact 1284), NOT the "
     "half-drift residual (fact 1280), and NOT a hard band limit from the coverage crop (fact 1282). The leading "
     "hypothesis is now RESAMPLING, and possibly two in series: at gate 0 the frame that wins a pixel is usually not "
     "the reference, so nearly every pixel has been through one CatmullRom warp gather at an arbitrary sub-pixel "
     "offset, and the coverage crop then rescales the whole field by 1/0.9315. **Stated as ARGUED, not measured.** "
     "One confound is unresolved and is an upper bound on the deficit: rawpy's demosaic is not strehl's, and demosaic "
     "differences bite hardest in exactly this octave. Separating the two requires comparing strehl's own single-frame "
     "path against its merge, which is inside the codebase; assigned to M95.",
     "ORCH (MEASURED deficit, ARGUED cause, demosaic confound OPEN); "
     "`experiments/ORCH-drift-check/fullres_check.py`"),

    (1285, "**THREE SUCCESSIVE ATTEMPTS TO ANSWER THE BINNING QUESTION FAILED THEIR OWN CONTROLS AND REPORTED NOTHING.** "
           "`upsample_check.py` exits 1 (its knee-finder returned the same 0.3169 cyc/px for the render and for a known "
           "round trip). `binned_check.py` exits 2 (controls landed at exactly **1.0000** and **0.1088**, but the render "
           "read **6.106**, above the upper anchor, breaking the readout). Only the third, `fullres_check.py`, passes an "
           "anchor-separation gate and is allowed to speak.",
     "Kept in the corpus deliberately, and committed still exiting non-zero, because the three failures share one cause "
     "worth more than the result: an anchor built by replicating binned values across their 2x2 block injects "
     "high-frequency energy at the block edges, so the \"binned\" reference carried **9x MORE** power at 0.445 cyc/px "
     "than the full-resolution frame it was built from, and the anchors crossed instead of bracketing. Had any of the "
     "three been allowed to report, it would have confirmed the binning hypothesis that fact 1284 refutes. See "
     "discipline 631.",
     "ORCH (three MEASURED nulls, all self-reported); `experiments/ORCH-drift-check/upsample_check.py`, "
     "`binned_check.py`, `fullres_check.py`"),
]

DISCIPLINES = [
    (631, "**A degraded anchor must be built the way the pipeline would emit it, not the way the degradation is "
          "defined.** Binning is defined as a block mean, and the obvious anchor replicates that mean across its block "
          "-- but a real binned pipeline scales back up smoothly and emits no blocks. The replicated anchor's block "
          "edges put 9x more power at 0.445 cyc/px than the full-resolution source, inverting the two anchors and "
          "sending the test toward the wrong verdict; switching the same anchor to a smooth rescale separated them by "
          "2.6563 dex and reversed the answer. Facts 1284, 1285. The general form: when an anchor is a synthetic "
          "degradation, ask what artefacts the synthesis introduces that the real process does not, and gate the test "
          "on the anchors actually bracketing the measurement before reading any verdict from it."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1283 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^630\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = []
    for did, body in DISCIPLINES:
        drows.append(f"{did}. {body}")

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1284-1286 after line {fact_idx}, discipline 631 after line {disc_idx}")


if __name__ == "__main__":
    main()
