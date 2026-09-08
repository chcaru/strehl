# Pre-outcome localization hypothesis

2026-09-07, recorded before factor-eight-plan-1.json or factor-eight-1 exists.
SOURCE VERIFIED / inference unmeasured. The held current arm is unchanged.

The owned reference.extract_features uses SIFT_create(nfeatures=2048,
nOctaveLayers=3, contrastThreshold=0.01, edgeThreshold=12, sigma=1.6), omitting
enable_precise_upscale. The [OpenCV4.13 API](https://docs.opencv.org/4.13.0/d7/d60/classcv_1_1SIFT.html)
documents that option as false by default and says enabling it prevents
localization bias. The implementation agent checked owned source and the
primary documentation; no fixture, numerical helper or option toggle ran.

INFERENCE: a common detector coordinate offset can survive an exact90-degree
image permutation and become visible under the factor-eight native lift.
DERIVED illustrative model: if each endpoint's detector offset is delta and
its true rotation is R, fitted translation gains (I-R)delta. For the hypothetical
delta=(0.25,0.25) coarse pixels, this plant would gain(0.5,0) coarse or(4,0)
native pixels. Neither the magnitude nor sign is established by the docs.
This is not a prediction that the fixture has this defect or an explanation
of a result that has not run.

If the current known-rotation positive fails, preserve it and stop the real
phase as registered. An explicit-default versus precise-upscale comparison
would then be a separately frozen follow-up on the same known image content,
with the same native accuracy oracle and active coordinate destroyers. No
threshold change or alternate fixture is justified by this hypothesis alone.
