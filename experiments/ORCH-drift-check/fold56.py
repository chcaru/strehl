"""Fold the exposed gallery and the halo look-at. Facts 1351-1353, discipline 671."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1351, "**THE SEVEN-STACK GALLERY NOW RENDERS AT FULL RESOLUTION WITH THE TOOL'S OWN EXPOSURE, AND THE "
           "AUTO-EXPOSURE IS TWO-SIDED IN PRACTICE, NOT ONLY IN DESIGN.** MEASURED at `925d03d` via "
           "`--srgb --auto-exposure`, no post-processing: `bee-3-cpl` **+1.54** stops, `lavendar-cpl` **+1.42**, "
           "`flowers-cpl` **+1.93**, `leaf-2-cpl` **+3.19**, `flower-bud-alone-cpl` **+1.49**, `tweezers-cpl` "
           "**+1.13**, `coffee-bean` **-0.18**. All seven at **32.97-33.00 MP**; clipping 0.0000-0.3538 %. "
           "1266 frames in **286 s** total, 19.2-92.1 s per stack.",
     "`coffee-bean` **darkening by 0.18 stops** is the result worth keeping: M100 designed the rule to be able to "
     "pull exposure down and pre-registered that `coffee-bean` and `foam` are already at the top of the range, and "
     "on the full 105-frame stack it does exactly that unprompted. The **+3.19** on `leaf-2-cpl` is a 9.13x gain, "
     "which is a capture 3.2 stops under -- consistent with question 22's median **+2.01** stops of unused sensor "
     "headroom and an independent route to the same conclusion: the largest single lever on this corpus is still "
     "at the camera, not in the software. `bee-3-cpl` chose **+1.54** on 299 frames against **+1.48** at "
     "`--limit 60`, so the statistic is stable to 0.06 stops across a 5x change in frame count.",
     "ORCH (MEASURED at `925d03d`: `gallery2.py`, `C:\\dev\\strehl-out\\ORCH-gallery2\\`)"),

    (1352, "**THE HALO CORRECTION REMOVES THE VEIL AND PUTS A WORSE ARTIFACT IN ITS PLACE, AND THE ORCHESTRATOR HAS "
           "NOW CONFIRMED THAT ON A PICTURE RATHER THAN A TABLE.** `flower-bud-alone-cpl` rendered twice at HEAD, "
           "identical flags, `STREHL_FIX_HALO=1` the only difference: **3.4715 %** of pixels change, max absolute "
           "difference **0.7901**, RMS over changed pixels **0.12831**. The comparison crop was chosen **on the "
           "difference image**, so neither render selected the view.",
     "**OFF** shows a soft, smooth bright veil hugging the silhouette plus a darker band standing off from it. "
     "**ON** genuinely flattens the veil, and replaces it with a **hard, stippled, ragged silhouette edge that "
     "reads as a compositing error, plus a new hard-edged white blob absent from the uncorrected render** -- the "
     "same class of artifact M97b called *waxy*. **A soft artifact that reads as glow is less objectionable than a "
     "hard artifact that reads as a cut-out**, so the picture agrees with M87's `+254.6 %` RMSE against truth and "
     "its `+558.4 %` on a region with *no occluding edge at all*. **Default stays OFF; the M103 ship gate stands.** "
     "Note what M87's three kills leave behind: not the gate (present at `--gate 0`), not misregistration "
     "(alignment removes 6.6 % against a predicted 91.7 %), not two depths (its unmix reached -28.2 % against a "
     "-50 % bar) -- **three refutations and no surviving mechanism**, which is now the sharpest open question in "
     "the render.",
     "ORCH (MEASURED at `925d03d`: `halo_look.py`, `C:\\dev\\strehl-out\\ORCH-halo\\`)"),

    (1353, "**THE EXTERNAL REVIEWER'S HEADLINE UNBUILT IDEA WAS ALREADY BUILT AND ALREADY FAILED.** The review "
           "proposed bimodal two-layer unmixing at occluding edges as *the first structural kill of the occlusion "
           "halo in any stacking tool* and ranked it second by expected value. M63 had already killed the two-layer "
           "model, and **M87 implemented the unmix and reached -28.2 % on real data against its own -50 % bar** "
           "before the review was written.",
     "ARGUED, and routed to M87 rather than concluded: **a failed implementation is not a failed model.** The open "
     "question is whether the -28.2 % was bounded by the two-component fit itself or by the winner field and `k_F` "
     "propagation feeding it -- if the latter, the reviewer's proposal survives its own refutation and is still "
     "live. This is the second time a third party's reading of this corpus has proposed as novel something the "
     "corpus had already measured (fact 1111 was the first, on the EDOF survey), which makes it a pattern rather "
     "than an accident: **an outside review reads the plan, not the fact table.**",
     "ORCH (ARGUED, from M87's `halo.rs` header + M63); mechanism question dispatched to M87"),
]

DISCIPLINES = [
    (671, "**A cosmetic correction must be judged on a picture, and the crop must be chosen on the difference so "
          "that neither render selects the view.** M87's table said `-79.8 %` halo metric and `+254.6 %` RMSE, "
          "which is enough to decide *fidelity* and not enough to decide *whether the owner will prefer it* -- "
          "those are different claims and only the first had been measured. Looking settled it in one image: the "
          "correction trades a smooth artifact for a hard one. **Choosing the crop on the difference is the part "
          "that makes it evidence** rather than illustration; picking it on either render is discipline 666's "
          "biased selector wearing a new hat. Fact 1352."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1350 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^670\. ", l))
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
    print(f"folded facts 1351-1353 after line {fact_idx}, discipline 671 after line {disc_idx}")


if __name__ == "__main__":
    main()
