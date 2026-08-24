"""Fold the kernel A/B: the switch already ships, the eye confirms the lever,
and the veil is exonerated of any resampler involvement.
Facts 1373-1376, discipline 684.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1373, "**THE RESAMPLER KERNEL IS ALREADY SWITCHABLE END TO END; ONLY THE PLUMBING WAS THOUGHT MISSING.** "
           "MEASURED at `1d468c1`. The sidecar serialises the choice (`warpmap.rs:597` writes `resampler "
           "<name>`, `:806` parses it) and the merge gathers with `map.resampler()` (`merge_cmd.rs:923`), so "
           "rewriting **one line** of an existing sidecar changes the gather kernel with no code change and no "
           "re-solve. Three arms on `bee-3-cpl`: **catmull-rom `E400A63A...7112`, nearest `50B94F31...F10D`, "
           "bilinear `AFDF3BE9...F25E`**, each reporting its own kernel back (`resampler : Nearest` etc.) and "
           "each `299 placed / 0 refused`, `sidecar-override`. Runtime **53.7 s / 34.7 s / 38.5 s** -- the "
           "sharpest arm is also the fastest. `experiments/ORCH-drift-check/kernel_ab.ps1`.",
     "**Second time in this session a milestone was commissioned to build a feature that already shipped** "
     "(cf. `19c0a61`, M105b). The correct first move on any \"make X switchable\" task is to grep the consumer "
     "for X before writing a line. **The validity control is what makes the rest of this readable and it is the "
     "part that could have failed:** the catmull-rom arm reproduced the previously shipped gallery render "
     "**byte-for-byte**, across a separate invocation, which proves the solve, the decode, the election and the "
     "render path were all held fixed and the gather kernel was the only free variable. Without that hash "
     "match the other two arms would be uninterpretable. Consequence for M85: the remaining work is **only "
     "adding a kernel to the enum**, not the plumbing to select it.",
     "ORCH (MEASURED at `1d468c1`; bars B1-B3 registered and committed before the run)"),

    (1374, "**BY EYE AT 1:1, THE GATHER KERNEL IS CONFIRMED AS THE DOMINANT SOFTNESS LEVER -- AND `nearest` IS "
           "NOT SHIPPABLE.** ARGUED-BY-INSPECTION on `ORCH-kernel/KERNEL-AB.png` (two regions of `bee-3-cpl`, "
           "1:1 pixels magnified x2 nearest, no sharpening or resize). Under `nearest`, individual thorax hairs "
           "separate cleanly and the cuticle net on the leg resolves; under the shipped `catmull-rom` the same "
           "hairs merge into a soft mass. `bilinear` sits between and much nearer `catmull-rom`. **But `nearest` "
           "visibly amplifies chromatic fringing on the hairs and adds speckle**, which is exactly what a "
           "zero-order hold must do -- it preserves every high frequency including the unwanted ones, and pays "
           "up to 0.5 px of positional error.",
     "**The eye and M85's metric agree, which is not something that could be assumed tonight** -- twice today a "
     "sharpness scalar preferred an image that inspection rejects (facts 1359, and M87's historical `+72.9%`). "
     "Independent by-eye confirmation of `-0.2360` dex promotes the kernel finding from a metric result to a "
     "seen one. **The conclusion is not \"default to nearest\"**: it aliases and it amplifies the very fringing "
     "M107 is chartered to explain. The target is a sharper *interpolating* kernel, and the default must not "
     "move until ringing is measured on real occluding edges -- Lanczos-3 rings 9.902x more than Catmull-Rom, "
     "and this stack's silhouettes are wall-to-wall occluding edges.",
     "ORCH (ARGUED-BY-INSPECTION at `1d468c1`; figure `ORCH-kernel/KERNEL-AB.png`)"),

    (1375, "**THE OCCLUSION VEIL IS UNCHANGED ACROSS ALL THREE GATHER KERNELS, SO IT IS NOT A RESAMPLER "
           "ARTIFACT.** MEASURED-BY-INSPECTION, free control from the fact 1373 arms: the bright band hugging "
           "the subject silhouette appears at the **same extent and same intensity** in `nearest`, `bilinear` "
           "and `catmull-rom` renders of `bee-3-cpl`, while the hair detail between them changes dramatically.",
     "**A control obtained without designing for it, and it partitions two workstreams cleanly.** A three-arm "
     "experiment aimed at sharpness happens to hold the veil against a variable that changes everything else "
     "in the image; the veil not moving is evidence its cause is upstream of the gather -- in the election or "
     "the forward model, which is M87's territory, not M85's. **Corollary for M107:** the chromatic fringing "
     "does the opposite, strengthening markedly under `nearest`, which is the signature of a defect **present "
     "in the data and merely blurred by the interpolating kernels** rather than created by them. That bounds "
     "candidate (d) small without a single dedicated measurement.",
     "ORCH (MEASURED-BY-INSPECTION at `1d468c1`; routed to M87 and M107)"),

    (1376, "**A SIDECAR FIELD IS A SINGLE-VARIABLE EXPERIMENT HANDLE.** MEASURED: rewriting one line of a "
           "299-frame sidecar and re-running `stack` isolates the gather kernel while holding the solve, the "
           "reference (149), the placements, the stack digest and the frame count **byte-identical** -- "
           "confirmed by the catmull-rom arm hashing equal to a render made in a separate session.",
     "**The sidecar was designed as a cache and turns out to be the project's cleanest ablation instrument.** "
     "Any solved quantity it serialises can be varied in isolation without a rebuild, without a re-solve, and "
     "with a built-in validity control -- the unmodified arm must reproduce the prior render exactly, and if it "
     "does not, the experiment announces its own contamination before any conclusion is drawn. Cost per arm "
     "here was ~40 s against ~110 s for align-plus-stack, and the rebuild that a code-level ablation would have "
     "required is avoided entirely. Contrast fact 1367, where the same file's persistence was a hazard: **the "
     "property that made it dangerous as a shared cache is what makes it precise as an instrument.**",
     "ORCH (MEASURED at `1d468c1`; `experiments/ORCH-drift-check/kernel_ab.ps1`)"),
]

DISCIPLINES = [
    (684, "**Before building a switch, grep the consumer for the value.** Twice in one session a milestone was "
          "commissioned to make something selectable that was already selectable end to end -- here the gather "
          "kernel, already serialised by `warpmap.rs:597`, parsed at `:806` and honoured at `merge_cmd.rs:923`. "
          "The check costs one grep of the *consumer* -- not the producer, which is where the earlier "
          "`align --out` mistake came from. Facts 1373, and `19c0a61`."),
    (685, "**When ablating, prefer varying a serialised field over changing code.** Rewriting one line of a "
          "sidecar holds every other solved quantity byte-identical and supplies a free validity control: the "
          "unmodified arm must reproduce a prior render exactly. A code-level ablation holds nothing fixed by "
          "construction, requires a rebuild, and offers no way to detect that something else moved underneath "
          "it. Fact 1376."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1372 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^683\. ", l))
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
    print(f"folded facts 1373-1376 after line {fact_idx}, disciplines 684-685 after line {disc_idx}")


if __name__ == "__main__":
    main()
