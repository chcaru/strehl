# Registration alternatives: primary-source decision notes

2026-09-08. SOURCE RESEARCH ONLY. No model, image or numerical experiment executed;
no weights downloaded. Conditional investigation order, not a next-arm selection,
deployment or exhaustive SOTA ranking. Await the saved refusal trace and audit.

**1. Sparse matching, if associations warrant investigation.**
PAPER CLAIM: LightGlue learns sparse correspondences and adapts computation to
pair difficulty. Its benchmark evidence does not establish macro-stack transfer.
[ICCV 2023 paper](https://openaccess.thecvf.com/content/ICCV2023/papers/Lindenberger_LightGlue_Local_Feature_Matching_at_Light_Speed_ICCV_2023_paper.pdf).

VERIFIED UPSTREAM: SIFT-input weights exist. The authors explicitly release
LightGlue code and pretrained weights under Apache-2.0, excluding the restrictive
SuperPoint inference file/weights. Do not use that branch.
[README](https://github.com/cvg/LightGlue#license),
[licence](https://github.com/cvg/LightGlue/blob/main/LICENSE).
SOURCE FINDING: the SIFT model uses128-D descriptors plus scale/orientation; its
extractor defaults to RootSIFT and automatic resize. It differs from our frozen
extractor. [Matcher contract](https://github.com/cvg/LightGlue/blob/main/lightglue/lightglue.py),
[SIFT adapter](https://github.com/cvg/LightGlue/blob/main/lightglue/sift.py).
INFERENCE: this is the narrower learned alternative when useful sparse sites
exist but associations are suspect. It cannot repair their coordinates. A future
arm must fix normalization, scale/orientation units, coordinate gauge, resize and
source/checkpoint pins; swapping extractors would confound the matching question.

VERIFIED LOCAL: all nine feature JSONs retain coordinates, counts, representation
receipts and descriptors_sha256/keys_sha256, not descriptor matrices or scale/
orientation values. The producer writes hashes. Existing JSON cannot feed SIFT
LightGlue as if those inputs survived. New authenticated extraction/export must be
separately costed and first reproduce existing coordinates/descriptor hashes.
[Saved record](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/real-precise-1/worker/feature-1.json),
[producer](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/factor-eight-run.py).

**2. Detector-free matching, if sparse-site coverage/localization is the concern.**
PAPER CLAIM: EfficientLoFTR combines aggregated attention with two-stage correlation
for semi-dense subpixel correspondences. Its reported evaluations do not establish
macro cross-defocus performance. [CVPR 2024 paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Wang_Efficient_LoFTR_Semi-Dense_Local_Feature_Matching_with_Sparse-Like_Speed_CVPR_2024_paper.pdf).

VERIFIED UPSTREAM: examples use normalized grayscale, resize each axis to a multiple
of32, and reparameterize the model. The README names MegaDepth training/outdoor
preference and a possible indoor gap; the linked Transformers processor defaults
to480x640. [README](https://github.com/zju3dv/EfficientLoFTR).
The repository is Apache-2.0. Its external checkpoint link lacks the explicit
code-and-weights statement found in LightGlue: exact checkpoint provenance and
licence scope remain to be established before use/redistribution.
[Licence](https://github.com/zju3dv/EfficientLoFTR/blob/main/LICENSE).

INFERENCE: prioritize this over sparse matching only when fixed sites warrant a
new localization/coverage hypothesis. It changes detection, description and
matching and requires images. Pin preprocessing and invert both resize axes and
centre offsets before native scoring. The AREA8 lift cannot silently absorb another
resize. Macro defocus transfer, memory and cost remain unmeasured here; benchmark
speed is not strehl timing. Neither learned option qualifies our coarse guard.

**3. Calibration reference, not a substitute matcher for these files.**
PAPER CLAIM: Finite Aperture Stereo §4.1 captures a calibration plane in multiple
orientations at each focus setting, with small- and large-aperture images; features
from small-aperture captures estimate per-setting intrinsics/distortion. §4.2 uses
those calibration correspondences to fit scale plus translation after distortion
removal, initialized by effective-focal-length ratios. This is not a demonstrated
uncalibrated cross-defocus scene matcher.
[IJCV 2022 §§4.1–4.2](https://link.springer.com/article/10.1007/s11263-022-01658-w).
INFERENCE: useful for independent capture truth or a calibration-aware research
branch. These inputs cannot be retroactively supplied by the current stack or
justify baking per-stack geometry into a camera profile.

**Local counterevidence and conditional order.**
MEASURED LOCALLY, not rerun here: M78 Gaussian cross-blur improved conservation but
worsened paired held-out prediction; its phase arm also did not ship. M103 later
showed that end-to-end improvement need not improve per-frame placement in the
merge's gauge. M78's old bar is not a universal impossibility proof, but its failed
remedy cannot be advertised as established repair.
[M78](C:/dev/blog/death-of-software/projects/strehl/docs/research/M78-blur-equalised-edges.md),
[M103, retraction §16](C:/dev/blog/death-of-software/projects/strehl/docs/research/M103-halfdrift.md).

INFERENCE: first inspect actual seed/gate deficits, all-match residuals and spatial
support. Narrow misses favor investigating localization/representation before
changing matchers; broad disagreement makes SIFT LightGlue the first narrower
association investigation, followed by EfficientLoFTR when fixed sparse sites are
inadequate. None of those patterns identifies a cause by itself. Ambiguity calls
for independent truth. Any next arm requires a known-map positive, association
destroyer/restoration, explicit resize/gauge controls and consumer-relevant per-frame
truth before graph/merge claims. This memo selects no threshold relaxation, chaining,
fixed-reference shortcut or revival of the failed blur remedy.
