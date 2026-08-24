"""Fold 36 -- M87: the occlusion halo, shipped and switched off."""
import io
import re

SYN = "docs/research/SYNTHESIS.md"

DISC = [
    "**Accept a remedy on ground truth, never on the metric that named the "
    "defect.** M87's halo correction improves its own halo metric by **72.9%** "
    "on the owner's bee while **erasing the abdomen hairs and replacing them "
    "with a milky scalloped blob more objectionable than the halo it "
    "removed**. Against a synthetic scene with known truth the same correction "
    "cuts the halo metric **79.8%** and raises RMSE against truth by "
    "**254.6%**. In the author's words: *\"the metric and the eye disagree, "
    "and the eye is right.\"* An artifact metric measures the presence of the "
    "artifact, which is not the same quantity as the correctness of the "
    "picture, and optimising the first will happily destroy the second.",

    "**A remedy that also fires on a control containing no defect is keying "
    "on the wrong feature, however good its headline looks.** M87's mode "
    "partition cut the halo metric **63.9%** on a region built to contain no "
    "occlusion at all -- raising RMSE **558.4%** -- and on real data it moved "
    "**85.4%** of pixels at a *planted non-occluding disc* against **82.1%** "
    "at the bee's genuine occluding edge, i.e. slightly **more** where there "
    "was nothing to fix. The detector keys on silhouettes, not occlusions. "
    "Run the no-defect control before believing the defect one.",

    "**A model-fit statistic is not a correctness statistic; do not gate "
    "admission on R-squared.** M87's synthetic plant, where the unmixing "
    "genuinely works and band RMSE is **1.71%**, has a median band R-squared "
    "of **0.058** -- *lower* than `bee-3-cpl`'s **0.131**, where the same arm "
    "fails. A model can fit a wrong thing tightly and a right thing loosely. "
    "The quantity that matters here is the intercept, and on real data nothing "
    "currently checks it.",
]

FACTS = [
    "| 1275 | **THE OCCLUSION-HALO CORRECTION IS SHIPPED, DEFAULT OFF, AND ITS "
    "OWN AUTHOR RECOMMENDS AGAINST ENABLING IT -- BECAUSE IT IS COSMETIC AND "
    "MAKES THE IMAGE MEASURABLY MORE WRONG.** `crates/strehl-cli/src/merge_cmd/"
    "halo.rs`, reached by `STREHL_FIX_HALO=1`, runs as a third pass so that "
    "with it off **the default output is byte-for-byte unchanged**. Against a "
    "synthetic two-layer scene with known truth it cuts the halo metric "
    "**79.8%** (ISO 0.03060 -> 0.00618) and **raises RMSE against truth "
    "254.6%** (0.03462 -> 0.12276). At product scale on the owner's bee it "
    "**erases the abdomen hairs and leaves a milky scalloped blob**, while its "
    "own metric reports a **72.9%** improvement. | This is the project's "
    "thesis applied to the project itself: the artifact metric and the "
    "photograph disagreed, and the photograph won. M87 built the feature, "
    "measured it honestly at product scale, and argued against its own work; "
    "the corpus's frozen numbers cannot move because the default path is "
    "untouched. **This partially retires fact 412's \"try the cheap remedy "
    "first\" as a *quality* recommendation** -- it is a good diagnostic and a "
    "bad fix. | M87 (MEASURED, ground truth + product scale); "
    "`docs/research/M87-occlusion.md` §16, P6, P27, P28 |",

    "| 1276 | **THE DETECTOR KEYS ON SILHOUETTES, NOT OCCLUSIONS: THE HALO "
    "CORRECTION MOVES *MORE* PIXELS WHERE THERE IS NOTHING TO FIX.** On a "
    "control region built to contain no occlusion it still cut the halo metric "
    "**63.9%** and raised RMSE against truth **558.4%**. On real data it moved "
    "**82.1%** of treated pixels at the bee's genuine occluding edge and "
    "**85.4%** at a **planted non-occluding disc** in the same image's "
    "background. | This is precisely the placebo failure the brief warned "
    "about, caught by running the control rather than by reasoning, and it "
    "rules out depth-selectivity as the explanation for why the output "
    "*looked* better. One safety claim survives unconditionally: outside the "
    "treated set the correction changes **exactly 0.0 DN** at delta 20, 40 and "
    "80 on both real stacks, pinned by a unit test -- the fine-detail guard is "
    "structural, not statistical. | M87 (MEASURED, planted control on real "
    "data); `docs/research/M87-occlusion.md` P29, P30, P31 |",

    "| 1277 | **TWO-LAYER UNMIXING IS THE RIGHT PHYSICS AND THE RIGHT TARGET, "
    "AND IT DOES NOT YET WORK ON REAL CAPTURES.** On a plant with known truth "
    "it removes **78.8%** of the halo *and* takes band RMSE **3.46% -> "
    "1.82%**, the far-field noise floor -- the only arm measured to make the "
    "picture **more correct** rather than merely cleaner-looking. On "
    "`bee-3-cpl` `ROI_LEG` it scores **+3.7%** with a global depth and "
    "**-28.2%** with a per-pixel depth, against a registered **-50%** bar. | "
    "So the owner's proposed model is vindicated as physics and not yet as "
    "code. Depth resolution is worth about **30 points** and is necessary but "
    "not sufficient. M87 ranks the remaining causes: a semi-transparent hair "
    "fringe, a non-constant foreground term, **no inter-frame alignment** -- "
    "every regression assumes pixel `x` is the same scene point in all 299 "
    "frames, which fact 1271 says is false by 150.2 plane px -- and "
    "**frame-level photometric drift, which M87 measures at 18%** and calls a "
    "nuisance regressor the model does not carry. Both of those are now owned "
    "(M103, M99). | M87 (MEASURED, registered bar missed); "
    "`docs/research/M87-occlusion.md` P7, P8 |",

    "| 1278 | **THE HALO IS NOT A MISREGISTRATION ARTIFACT, AND THE NEGATIVE "
    "IS QUANTITATIVE RATHER THAN A NULL.** M87 tested it directly and "
    "reports: *\"Is the halo a misregistration artifact? NO.\"* Separately, "
    "**a global foreground focus frame is the wrong object whenever the "
    "occluder spans depth** -- mode partition scores **-63.4%** on a subject "
    "spanning 79 frames and **-1.2%** on one spanning 248, while per-pixel "
    "depth takes both to **-87.9%** and **-84.6%**. | The first half matters "
    "because fact 1271 had just made misregistration the obvious suspect for "
    "everything, and it is not the explanation here. The second half is a "
    "design constraint on any future occlusion stage in this codebase: **it "
    "must carry a per-pixel foreground depth map, not a scalar**, and that "
    "holds for both arms. Measured on two scenes with no refitting. | M87 "
    "(MEASURED, two scenes); `docs/research/M87-occlusion.md` §15, P10 |",
]

syn = io.open(SYN, encoding="utf-8").read()
L = syn.split("\n")

d = max(i for i, l in enumerate(L) if re.match(r"^6\d\d\. ", l))
assert L[d].startswith("624. "), L[d][:60]
f = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[f].startswith("| 1274 |"), L[f][:60]

for k, row in enumerate(FACTS):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == 5, "fact %d has %d pipes" % (k, n)
DROWS = ["%d. %s" % (625 + k, t) for k, t in enumerate(DISC)]

assert d != f
for idx, rows in sorted([(d, DROWS), (f, FACTS)], reverse=True):
    L[idx + 1:idx + 1] = rows

io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: facts 1275-1278, disciplines 625-627")
