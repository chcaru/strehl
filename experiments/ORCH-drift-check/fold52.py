"""Fold the visual inspection of the exposure-corrected gallery. Facts 1341-1343,
discipline 666.

No metric is attached to any of this. It is direct observation of shipped
renders at 1:1, labelled OBSERVED rather than MEASURED, and its value is in
naming which defect is dominant -- not in quantifying it.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1341, "**WITH EXPOSURE CORRECTED, FOUR OF SEVEN GALLERY STACKS LOOK GOOD AND THE HALO IS WHAT IS LEFT.** "
           "Direct inspection of `CONTACT-SHEET.png`: `leaf-2-cpl`, `coffee-bean`, `bee-3-cpl` and `tweezers-cpl` "
           "render sharp, naturally coloured and correctly exposed, with resolved venation, bean surface texture "
           "and individual thoracic hairs. The three that do not are `flower-bud-alone-cpl`, `lavendar-cpl` and "
           "`flowers-cpl` -- **all three are subjects with fine structure silhouetted against a large bright "
           "near-clipping background**, which is the halo's regime.",
     "**This reorders the image-quality queue.** The owner's *\"those stacks don't look too good\"* was substantially "
     "the underexposure of fact 1293, which fact 1339 found was never in the binary; the sharpness work of M95 and "
     "M97b is real but second-order against a 1.5-3.7 stop error. Once exposure is applied the residual defect is "
     "**not softness, it is the halo**, and it is confined to a subject class the owner shoots constantly. M87's "
     "workstream, which had no shippable fix, becomes the highest-value open item for what the owner sees.",
     "ORCH (OBSERVED, visual inspection of 7 renders; no metric attached)"),

    (1342, "**THE HALO ON `flower-bud-alone-cpl` HAS THREE DISTINCT VISIBLE COMPONENTS, AND THEY MAY NOT SHARE A "
           "MECHANISM.** At 1:1: **(a)** a thick bright veil hugging the entire subject silhouette, roughly as "
           "bright as the white background, reading as background eaten inward across the occluding boundary; "
           "**(b)** a **scalloped, lobed boundary** to that veil on a lengthscale far larger than a pixel; **(c)** "
           "**detached hard-edged white islands tens of pixels across, floating inside the subject** in places the "
           "background cannot physically reach.",
     "**(a) is a two-layer composite at an occluding edge and is what the halo literature describes. (c) is not** -- "
     "an island interior to the subject looks like a winner-field pathology, the election choosing a "
     "background-focused frame in a cell where the subject carries no texture, which is fact 73's blind spot rather "
     "than an occlusion effect. If they are two mechanisms then a correction tuned on the veil will leave the "
     "islands untouched, and any metric averaging both will score a half-fix as a win. **(b) is a free "
     "diagnostic**: whatever sets that lengthscale -- focus window, regulariser neighbourhood, tile size -- "
     "identifies which stage produces the shape. Routed to M87 with the stack named as its test case; every prior "
     "halo measurement was on synthetic plants or M13's cells, never on this.",
     "ORCH (OBSERVED, 900 px 1:1 crop); routed to M87, unquantified"),

    (1343, "**THE GALLERY'S OWN CROP SELECTOR IS BIASED TOWARDS WHATEVER IS SHARPEST, WHICH NEED NOT BE THE "
           "SUBJECT.** `gallery.py`'s `detail_peak` picks the 900 px box maximising summed squared gradient on an "
           "8x-downsampled copy. On `flowers-cpl` it landed on **background fabric weave, rendered crisply, while "
           "every petal in the same crop is mush** -- so the emitted \"100% crop\" is evidence about the backdrop "
           "and not about the flowers.",
     "**A detail-seeking crop selector systematically shows the backdrop whenever the backdrop out-resolves the "
     "subject, which is exactly the failure case one wants to see.** The instrument hides the defect it should "
     "expose, and it does so silently because its output looks like a sharp crop. This does not invalidate the "
     "other six crops, but it means `flowers-cpl` has **not** been visually assessed and the apparent subject "
     "softness there is unadjudicated. A subject-aware or randomly-sited crop is the fix.",
     "ORCH (OBSERVED, against `gallery.py:detail_peak`); instrument defect, self-disclosed"),
]

DISCIPLINES = [
    (666, "**A crop selector that maximises a sharpness statistic is a biased instrument for judging how a subject "
          "rendered.** `gallery.py`'s `detail_peak` chooses the highest-gradient-energy box, so on `flowers-cpl` it "
          "returned sharp background fabric beside mushy petals and presented it as the stack's 100% crop. The "
          "selector will preferentially display the backdrop precisely when the subject is failing, which is the "
          "one case the crop exists to reveal. **Site detail crops by subject or at random, and never let the "
          "quantity being judged also choose where it is judged.** Fact 1343."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1340 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^665\. ", l))
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
    print(f"folded facts 1341-1343 after line {fact_idx}, disciplines 666 after line {disc_idx}")


if __name__ == "__main__":
    main()
