"""Fold M87's occlusion milestone. Facts 1298-1303, disciplines 638-640.

DELIBERATELY NOT FOLDED: M87's headline "79x". Its own operands give
0.06804 / 0.000026 = 2617x, and as a significance it is ~9300 sigma. The
ratio does not follow from the stated numbers, so the claim is folded using
only what the operands support ("three orders of magnitude") and the exact
ratio is queried with M87.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1298, "**THE OCCLUSION HALO IS MANUFACTURED BY THE MERGE; IT IS NOT PRESENT IN THE FRAMES.** M87's "
           "isolation metric on `bee-3-cpl`: all **299 single frames** score `0.000026 ± 0.0000073`; the **merge** "
           "scores `0.06804` CI `[0.05981, 0.07982]`. The merged image's halo is **three orders of magnitude** above "
           "anything any input frame contains, and the interval does not approach the single-frame level.",
     "Settles the question the milestone existed to answer, and does it by measurement rather than by inspection. "
     "Combined with fact 1145 -- the halo survives at `--gate 0`, where every output pixel is literally one frame's "
     "pixel, unaveraged -- **the cause is the election, not the averaging and not the noise gate.** M87 separately "
     "confirmed on ground truth that **no selector can be correct at a veiled boundary**: the frame in which the "
     "background is sharpest is the frame in which it is *most veiled*, because the occluder is then maximally "
     "defocused. There is no right frame to pick, so no selection rule can be fixed into correctness -- only "
     "reconstruction can. **M87's own \"79x\" summary of this fact is not folded**: `0.06804 / 0.000026` = 2617, and "
     "as a significance it is ~9300 sigma, so the ratio does not follow from its operands and is under query.",
     "M87 (MEASURED); `docs/research/M87-occlusion.md`"),

    (1299, "**THE REGISTRATION HYPOTHESIS FOR THE HALO IS REFUTED, 92% PREDICTED AGAINST 6.6% OBSERVED.** The "
           "orchestrator argued the halo might be misregistration selecting whichever frame places an edge over a "
           "pixel. M87 gave it every chance and it failed quantitatively, not as a bare null: the mechanism is real "
           "(a no-occlusion plant with 30 px p-p planted drift reaches ISO **0.0645** against the real leg's "
           "**0.0680**), the magnitude is real (**63.04 px** p-p by mask centroid, **70.97 px** by the aligner's own "
           "solve, two instruments agreeing to 12.6%), the ladder has a threshold at **16-24 px** p-p, so removing "
           "the drift predicted **91.7%** of the halo would vanish. Measured: **6.6%** (0.06805 -> 0.06356, CIs "
           "overlapping). Validity gate passed at **21x** its bar.",
     "A negative with a number, which is worth far more than a null. **Restated without `E*` after fact 1295 "
     "invalidated it**: M87's original derivation of the post-alignment residual came from `E*` = 13.58 px, which "
     "fact 1295 proves is structurally blind to a common multiplicative gain error -- the very error present. M87 "
     "**struck its own §15.4 in place** rather than quietly repairing it, and restated the conclusion using only "
     "quantities that survive: the solve *applies* 70.97 px p-p in-ROI while just **30 px** p-p manufactures "
     "**94.8%** of the halo, so alignment removed **2.37x more drift than the amount that makes 95% of the "
     "artifact**, and the artifact moved 6.6%. Independent of `E*`, of the residual, and of the true span -- the "
     "three quantities that were wrong. **Consequence: alignment is still worth shipping and will not fix this, and "
     "a halo repair tuned after alignment is not tuned against a registration artifact.**",
     "M87 (MEASURED, hypothesis by ORCH, refuted); `docs/research/M87-occlusion.md` §15, §20.2"),

    (1300, "**THE HALO FIX IS AN OCCLUSION FIX RATHER THAN A GEOMETRY FIX, AND IT SHIPS OFF BY DEFAULT BECAUSE IT "
           "ERASES REAL DETAIL.** C-ZOOMNULL, run against an FOV- and resampler-matched null with registration "
           "discarded: aligned **0.06406 -> 0.01734 (−72.9%)**, registration-discarded **0.06878 -> 0.01186 "
           "(−82.8%)**, **ratio 1.135**. A fix whose benefit depended on alignment would be fixing geometry; this "
           "one does not. Shipped as `merge_cmd/halo.rs`, `d=40` defended by ladder, 6/6 tests green, gated behind "
           "`STREHL_FIX_HALO`.",
     "**M87 was instructed to ship it on by default and refused, correctly.** It shipped, rendered the full frame, "
     "looked, and found the correction removes the rim **and erases the abdomen hair fringe**, leaving a milky "
     "scalloped band worse than the halo -- the metric fell 72.9% while the photograph got worse. Its crop-scale "
     "evidence (unaligned, gate 0, 700x1100 ROI) did not transfer to the full frame (aligned, gate 2, 45.31% mask). "
     "**Default-on would have been visible damage to the owner's photograph.** The two-layer unmixing does "
     "reconstruct correctly on a plant with known truth (−78.8% halo *and* band RMSE 3.46% -> 1.82%, the far-field "
     "floor), and on the real bee it still fails (−28.2% per-pixel against a −50% bar). **So: the halo is understood, "
     "the mechanism is confirmed, and there is not yet a working fix for real captures.**",
     "M87 (MEASURED, shipped); `crates/strehl-cli/src/merge_cmd/halo.rs`, `docs/research/M87-occlusion.md` §16.9"),

    (1301, "**PHOTOMETRIC NORMALISATION DOES NOT FIX THE HALO, AND A SINGLE-POINT TEST SAYS IT DOES.** M87 swept "
           "correction strength instead of testing one setting. ISO against lambda: **0.00 -> 0.06804**, 0.25 -> "
           "0.06979, 0.50 -> 0.07120, 0.75 -> 0.07225, **1.00 -> 0.07379**. **Monotone increasing; the best "
           "correction strength is none.**",
     "The trap is explicit in the data: **a single point at lambda=1 reads −8.4% and looks like a win**; only the "
     "ladder shows the trend's sign. The mechanism is nonetheless real and fires on the right population -- gain "
     "normalisation re-elects **31.5%** of disconnected pixels against **3.6%** of connected ones, enrichment "
     "**8.80x**, shuffle null **0.989x**, median move **73 frames vs 2** -- so this is a case of a correct mechanism "
     "acting on the correct population and **not** improving the artifact. M87 also verified before running that the "
     "test *could* fail: the focus field scales as **sqrt(gain)**, so a scale-invariant focus measure would have made "
     "it vacuous. Cross-validation: pure-Python re-election **0.06804** vs the shipped Rust binary's **0.06805**, "
     "1 part in 6800, independent code.",
     "M87 (MEASURED, ladder); `docs/research/M87-occlusion.md`, M96 disconnected-set definition"),

    (1302, "**PIL SILENTLY 8-BIT-CONVERTS 16-BIT RGB TIFFs, AND THIS IS REPO-WIDE.** On the same image pair, PIL "
           "reports a maximum delta of **163** where `tifffile` reports **41887 of 65535**. M87 nearly reported its "
           "own fix inert because of it, and its first numbers were quantised; re-measuring moved its headline "
           "**74.5% -> 72.9%** and brought the Python and Rust masks into exact agreement at 45.31%.",
     "**Any corpus measurement that read a strehl TIFF through PIL needs re-checking.** The orchestrator audited its "
     "own instruments in `experiments/ORCH-drift-check/`: zero uses of `Image.open`, all reads via `tifffile`, PIL "
     "used only to *write* 8-bit PNGs -- so the drift, resample, demosaic, seam and exposure numbers are clear. The "
     "general lesson is that a silent precision downgrade on read is invisible to every downstream check, and the "
     "failure mode it produces is the worst kind: **a real effect measured as absent.**",
     "M87 (MEASURED, P40); ORCH (audit of `experiments/ORCH-drift-check/`)"),

    (1303, "**A THIRD INDEPENDENT ROUTE CONFIRMS THE SOLVE APPLIES ~54% OF THE DRIFT.** M87 decoded all 299 fitted "
           "f64 warps and found scale bottoming at `\\|a\\|` = **0.922414**, which reproduces fact 1295's sidecar span "
           "**0.92241 to six digits** by a route that renders nothing. Its apparent \"1.84x disagreement\" between "
           "three figures is exactly **1/0.543** -- the reciprocal of the solve's application rate.",
     "M87 filed this as a bookkeeping dispute between three sources, then recognised it as an independent "
     "re-derivation of M97's defect and said so. **Three routes now agree**: M97 by rendering, ORCH by ground truth, "
     "M87 by decoding the warps. Also filed: **the shipped binary still prints \"M86 measured 232.7 px of drift on "
     "bee-3-cpl\" at runtime**, which fact 1295 makes a user-visible wrong number.",
     "M87 (MEASURED, P42, self-corrected); cross-check of fact 1295"),
]

DISCIPLINES = [
    (638, "**An artifact-suppression metric is satisfied by destruction as readily as by reconstruction, so it can "
          "never certify a fix on its own.** M87 registered bar X4 to catch exactly this and **X4 FAILED**: three of "
          "four *deliberately broken* unmixings still improved the halo metric by **77-85%**, one of them wrong by "
          "six orders of magnitude. Flattening a near-edge profile satisfies the metric whether the veil was removed "
          "or the neighbourhood was obliterated. **Any suppression metric needs a paired fidelity term measured "
          "against truth** -- on the plant, the working reconstruction moved band RMSE 3.46% -> 1.82% while the "
          "cosmetic partition moved it **+254.6%**, and only the fidelity term could tell them apart. This "
          "generalises far past halos: it applies to every denoiser, deblurrer, and artifact remover this project "
          "will ever gate. Facts 1298, 1300."),
    (639, "**Sweep a correction's strength; never evaluate it at a single setting.** M87 tested photometric "
          "normalisation against the halo at five strengths and found the response **monotone increasing** -- the "
          "best correction is none. Evaluated only at full strength it reads **−8.4%**, which is a plausible-looking "
          "win pointing the wrong way. A one-point test cannot distinguish \"this helps\" from \"this hurts and the "
          "endpoint happens to sit low\", and the cost of the ladder was four extra runs. Fact 1301."),
    (640, "**Attribute from a current read, not merely from the right file.** The orchestrator attributed three lint "
          "violations to M87 by file -- the correct method, discipline 593 -- and was still wrong, because the read "
          "was stale: the violation had been fixed two commits earlier and the reported line number was 41 lines off. "
          "M87 disproved it with two independent instruments and told the orchestrator not to fold the thanks. "
          "**Re-run the check immediately before attributing it to someone**, and treat a line number that does not "
          "match as evidence the read is old rather than as a rounding error. Related: the orchestrator also briefed "
          "M87 with a falsifier whose test population did not exist -- three boundaries claimed to have reversed "
          "contrast polarity were reflectance edges at a single depth."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1297 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^637\. ", l))
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
    print(f"folded facts 1298-1303 after line {fact_idx}, disciplines 638-640 after line {disc_idx}")


if __name__ == "__main__":
    main()
