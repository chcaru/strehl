"""Fold the boundary-flag separation, the flowers verdict, and the metric that
preferred the artifact. Facts 1357-1359, disciplines 674-675.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1357, "**THE TOOL'S OWN BOUNDARY FLAG SEPARATES THE ONE VISUALLY BROKEN STACK FROM THE GOOD ONES BY 281x, "
           "WITHOUT BEING TOLD WHICH IS WHICH.** MEASURED at `e47cf81`, `--gate 2`, full resolution, the "
           "`boundary %` column the merge already prints: **`flowers-cpl` 33.74 %**, `bee-3-cpl` **1.00 %**, "
           "`leaf-2-cpl` **0.12 %**. `flowers-cpl` is the stack that renders as a featureless waxy blob in the "
           "gallery; the other two are the two that look right. The prediction was registered before the run.",
     "**This is the confidence-as-output thesis paying off for the first time on a real defect, and it inverts "
     "where the blame sits.** A third of `flowers-cpl` elects a frame at the first or last rung of the bracket -- "
     "the structural signal for *no frame in focus here* -- so the focus sweep did not cover the subject depth. "
     "The random-election floor on a stack this size is roughly 2/N, of order 3 %, so 33.74 % is an order of "
     "magnitude above noise. **The tool detected an under-bracketed capture that I was about to blame on the "
     "merge.** It is also the realisable form of the *reshoot-this versus retouch-this* product idea: the number "
     "needed to tell the owner to re-shoot with a wider sweep was already on screen and nothing was reading it.",
     "ORCH (MEASURED at `e47cf81`: `boundary_probe.py`, `C:\\dev\\strehl-out\\ORCH-boundary\\`)"),

    (1358, "**THE `flowers-cpl` MUSH IS THE CAPTURE, NOT THE MERGE, AND NOT EXPOSURE.** MEASURED at `e47cf81`, "
           "both arms at a **fixed** `--exposure=+1.92` so the merge is the only variable, centre 900 x 900 crop "
           "fixed in advance: `--gate 0` reports **mean n_eff 1.000, 100.00 % of pixels at n_eff = 1** -- pure "
           "selection, the upper bound on what selection can show -- and **contains no real detail either**. "
           "Saturation is ruled out on the linear render, where clipping is unambiguous: **maximum 0.6002 of full "
           "scale, 0.000 % of the crop within 1 % of maximum**.",
     "**Pure selection is the correct control for *did the merge destroy detail*, and it exonerates the merge "
     "here.** If `--gate 0` shows detail and `--gate 2` does not, the average ate it; if neither shows it, no "
     "single frame ever held it and the capture is at fault. Combined with fact 1357's 33.74 % boundary rate the "
     "diagnosis is complete and it is a shooting instruction, not a code change: **the bracket did not span the "
     "subject.** Note the exposure was resolved once by `--auto-exposure` and then **pinned as a literal for both "
     "arms**, because an auto-exposure that re-solves per arm makes the render the variable instead of the merge.",
     "ORCH (MEASURED at `e47cf81`: `flowers_blame.py`, `C:\\dev\\strehl-out\\ORCH-flowers\\`)"),

    (1359, "**A HIGH-FREQUENCY ENERGY METRIC SCORED THE SELECTION ARTIFACT 2.73x ABOVE THE CORRECT RENDER.** "
           "MEASURED at `e47cf81` on the `flowers-cpl` centre crop: standard deviation of the Laplacian on "
           "luminance is **0.013526** for `--gate 0` against **0.004957** for `--gate 2`. Looking at the picture "
           "reverses the verdict completely: gate 0's excess energy is **hard-edged polygonal patchwork** -- flat-"
           "shaded tiles with visible straight boundaries, where the winner field elected different frames in "
           "adjacent low-texture areas and their brightnesses do not match -- and gate 2 removes it.",
     "**Selection artifacts are high-frequency, so every sharpness proxy of this family rates them as detail.** "
     "This is not a subtle miss: the metric preferred a visible mosaic to a clean gradient by nearly a factor of "
     "three, and any benchmark scoring stackers on acutance, Laplacian energy or gradient variance would rank the "
     "broken renderer first. It is a second, independent demonstration of the project's thesis -- fact 1355 showed "
     "estimation removing noise at no cost in detail, this shows it removing a **structured** artifact that "
     "selection cannot avoid in flat regions -- and it is a direct warning about the planned benchmark: **the "
     "quality metric must be perceptual or reference-based, never an unreferenced sharpness proxy.** The patchwork "
     "shares its mechanism with the open halo question -- an ambiguous winner field in a low-signal region -- and "
     "is offered to M87 as such.",
     "ORCH (MEASURED at `e47cf81`: `flowers_blame.py`, `SBS-centre-gate0-vs-gate2.png`, judged by eye)"),
]

DISCIPLINES = [
    (674, "**Never score sharpness with an unreferenced high-frequency metric, because artifacts are "
          "high-frequency and the metric cannot tell them from detail.** Laplacian energy on a `flowers-cpl` crop "
          "rated pure selection **2.73x sharper** than the estimation merge; the picture shows the excess is "
          "polygonal winner-field patchwork with hard tile edges. **A sharpness proxy is only meaningful against a "
          "reference or a perceptual model** -- and when neither exists, the fallback is not a different proxy, it "
          "is looking at the image. Fact 1359."),
    (675, "**Before blaming the merge for a soft render, render `--gate 0` and look: pure selection is the upper "
          "bound on what selection can show.** If gate 0 is also soft, no single frame held the detail and the "
          "fault is upstream in the capture, which is a shooting instruction rather than a code change. Pin the "
          "exposure to a literal for both arms first, or the render becomes the variable instead of the merge. On "
          "`flowers-cpl` this took one script and moved the diagnosis from *the merge over-averages* to *the "
          "bracket did not span the subject*, corroborated independently by a 33.74 % boundary rate. Facts 1357, "
          "1358."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1356 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^673\. ", l))
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
    print(f"folded facts 1357-1359 after line {fact_idx}, disciplines 674-675 after line {disc_idx}")


if __name__ == "__main__":
    main()
