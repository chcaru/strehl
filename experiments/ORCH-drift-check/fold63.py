"""Fold the rendered-halo confirmation and the misreading it corrected.
Facts 1371-1372, discipline 683.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1371, "**THE OCCLUSION VEIL IS THE DOMINANT VISIBLE ARTIFACT IN THE SHIPPED DEFAULT RENDER, ON THE FLAGSHIP "
           "STACK.** MEASURED at `865c1ff` on `bee-3-cpl` (299 frames, `--srgb --auto-exposure`, **shipped "
           "default gate**, isolated sidecar per rule 45 reporting `sidecar-override`, reference 149, 299/299 "
           "placed). At 100% over `(700,3150) 1100x900`, the green plane stretched ~4x about its median shows **a "
           "bright veil hugging the entire subject silhouette** -- hair mass, leg and claw -- extending roughly "
           "**20-40 px** into the defocused background and following the outline into the concavities between "
           "individual hairs. Script `experiments/ORCH-drift-check/blob.py`; figure `ORCH-gallery3/BLOB.png`.",
     "**This is the artifact in the wild rather than in a test cell, and it is on the image the owner cares most "
     "about.** It corroborates M87's workstream from a completely different direction: not an occluding-edge cell "
     "population, but a rendered photograph at the default gate. A bee is the adversarial case -- thousands of "
     "hairs, each its own occluding edge -- which is why the veil is continuous rather than patchy here. "
     "**Registered hazard for the fix, and it is the reason the metric has already failed once: in this region "
     "the correct answer and the artifact are the same signal at the same spatial scale.** A veil that hugs a "
     "silhouette lives exactly where the hair detail lives, so any metric rewarding reduced background brightness "
     "near an edge also rewards erasing the hairs -- which is precisely what M87's earlier `+72.9%` correction "
     "did. A rendered before/after crop of this region must outrank any scalar. Separately flagged as **seen but "
     "not claimed**: concentric contour-like banding in the background around the claw, cause unseparated "
     "(veil falloff, stretch quantisation, or a distinct defect).",
     "ORCH (MEASURED at `865c1ff`; routed to M87 with the figure and the metric caution)"),

    (1372, "**THE SAME ARTIFACT WAS FIRST MISDIAGNOSED AS A POLYGONAL WINNER-FIELD MOSAIC, FROM A CROP ONE FIFTH "
           "THE SIZE.** In a 520 px crop the veil read as a flat-shaded grey region with hard, straight, "
           "piecewise-linear boundaries -- the signature of **tiling**, a different defect with a different cause "
           "and a different fix. Enlarging the same region to 1100x900 refuted it outright: **there is no "
           "polygon.** Every boundary is curved and organic and follows the subject silhouette; the background is "
           "a smooth gradient.",
     "**A crop is a sampling decision, and at small size it imposes shape.** The straight edges were the crop's "
     "own frame and the eye's completion across a truncated curve, not the data. Acting on the first reading "
     "would have sent M87 after a tiling artifact that does not exist, in a file (`merge_cmd.rs`) already "
     "contended by two other agents. **Third occasion this session where a smaller view produced a confident "
     "wrong answer that a larger view overturned** -- facts 1359 (a Laplacian metric preferring visible "
     "patchwork) and 1362 (a one-sided bar reporting a 7.8x effect as a null) are the other two, and in all "
     "three the wrong answer arrived with more apparent precision than the right one.",
     "ORCH (self-disclosed at `865c1ff`; correction sent to M87 with the instruction not to inherit the first "
     "reading)"),
]

DISCIPLINES = [
    (683, "**Do not name a mechanism from a small crop. Enlarge until the artifact's boundary is fully inside "
          "the frame, then name it.** A 520 px view of a silhouette veil read as hard-edged polygonal tiling; "
          "the same region at 1100x900 showed smooth organic contours and no straight edge anywhere. Small "
          "crops truncate curvature into apparent straight lines and truncate gradients into apparent flat "
          "regions, so they systematically bias a diagnosis **toward** the geometric, tiled, algorithmic-looking "
          "explanation -- which is the explanation an engineer is already primed to accept. The cost is not a "
          "wasted look but a misrouted milestone: the two readings have different owners, different files and "
          "different fixes. Facts 1371, 1372."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1370 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^682\. ", l))
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
    print(f"folded facts 1371-1372 after line {fact_idx}, discipline 683 after line {disc_idx}")


if __name__ == "__main__":
    main()
