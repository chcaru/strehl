# Registration literature follow-up, 2025–2026

2026-09-08. Primary-source reading only while the fixed AREA4 implementation is
reviewed. No model/source import, checkpoint download, image or numerical run.
This extends the earlier alternatives memo; it does not change the AREA4 arm or
claim an exhaustive current ranking, macro transfer, licensing clearance or SOTA.

**RoMa v2 (November2025 preprint).** PAPER CLAIM: the dense matcher combines a
frozen DINOv3 encoder, pair-conditioned coarse matching and fine refiners, and
predicts a pixelwise precision matrix. Section3.3 reports small training-dependent
subpixel biases and an exponential moving average remedy. Its covariance training
uses covisible regions with residuals below8 model pixels. Those conditions limit
what learned precision can certify on unseen defocus/outliers. INFERENCE: a relevant
future robustness-plus-localization comparator; its own precision cannot become
our support guard without independent calibration. This is not the same mechanism
as the measured OpenCV option effect. [Paper, sections3.3–3.5](https://arxiv.org/html/2511.15706v1).

VERIFIED UPSTREAM: repository licence is MIT, but its README explicitly excludes
DINOv3, which has a custom licence. Exact backbone/checkpoint terms and runtime
provenance must be examined before use; a top-level MIT badge does not clear the
whole model. No DINOv3 source was read or downloaded in this follow-up.
[Licence](https://github.com/Parskatt/RoMaV2/blob/main/LICENSE),
[README](https://github.com/Parskatt/RoMaV2/blob/main/README.md).

**CoMatch (ICCV2025).** PAPER CLAIM: its fine stage refines coordinates in both
views to subpixel locations, addressing the asymmetry of refining only the target.
INFERENCE: potentially relevant if a new detector-free branch is needed, but no
macro cross-defocus truth is established by that abstract. Repository licence is
MIT; checkpoint-specific permission/provenance remains unexamined. No code read. The paper uses epipolar supervision; that constraint alone does
not determine exact point placement along an epipolar line.
[Paper](https://openaccess.thecvf.com/content/ICCV2025/html/Li_CoMatch_Dynamic_Covisibility-Aware_Transformer_for_Bilateral_Subpixel-Level_Semi-Dense_Image_Matching_ICCV_2025_paper.html),
[Licence](https://github.com/ZizhuoLi/CoMatch/blob/main/LICENSE).

**MV-RoMa (March2026; arXiv marks CVPR2026 accepted).** ABSTRACT CLAIM: joint
source-to-multiple-target dense matching aims to improve multi-view track
consistency, using pairwise geometry as a prior and a multi-view refiner. Only
the primary abstract was read, not its implementation/licence. INFERENCE: retain
as a later track-level candidate; it does not remove our need for direct-edge
and per-frame placement validation or justify adjacent transform chaining.
[Primary abstract](https://arxiv.org/abs/2603.27542).

**Local preparation only.** A standard-library importlib.metadata query of the
selected Python reports torch2.11.0+cu128, torchvision0.26.0, safetensors0.7.0 and
transformers5.8.1 installed; kornia/lightglue absent. This is distribution metadata,
not successful import, GPU availability, ABI compatibility or a captured runtime.
Independent metadata inspection and a later root enumeration returned
torchvision0.26.0+cu128 at the same global package root. Preserve the initial
0.26.0 observation; its difference is unresolved, not a qualified runtime pin.
No package was imported/installed for this check. Do not make a speed/memory claim
from installed package names.

ARGUED: preserve the narrower SIFT-input LightGlue branch for association questions,
but include modern bilateral/dense localization methods in a later evidence-led
choice. The present AREA4 test can fail and remains first. Any learned arm needs
fixed preprocessing/coordinate inversion, checkpoint/source/runtime identity,
literal geometric truth, destructive controls and full fixed real pair reporting.
A predicted confidence is an uncalibrated model output on this corpus, not truth.

Independent primary-source review found these paper/licence scopes sound and
added the epipolar-supervision caution. Neither review changes the AREA4 arm.
