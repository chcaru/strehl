# Frozen complete-photo review and placement consistency protocol

Allocation: independent photographic review of full bug-3 repeat outputs.
Baseline preparation only is completed here. Root schedules native full 598
outputs and any cache/RAW placement audit. No RAW or Cargo jobs ran in this lane.
The ten-source pilot is incomplete focus coverage and cannot support a
photographic-gain conclusion.

## Completed baseline commissioning

MEASURED, command actually run from the feature worktree:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/prepare-review.py prepare-baselines
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/prepare-review.py crops --rois outputs/multi-stack/independent-review/roi-draft.json

Both completed with exit0. Python 3.12.10, NumPy 2.4.4, Pillow 12.2.0,
tifffile 2026.5.2. This is a sequential baseline-TIFF read/analysis task, not an
engine benchmark. A second crops command with roi-frozen.json records the final
selection; the draft receipts are retained separately.

Both complete baseline masters are 7032x4688 RGB32F, BT.709/D65, linear pre-tone.
Their encoded photographs are RGB16 sRGB. Every master sample was checked finite
while making a complete display; files, scripts, pixels and transform hashes
are in outputs/multi-stack/independent-review. Neither source TIFF was changed.

The display transform is frozen from ONLY baseline106's embedded DisplayBaseline:
black=-0.0002594062, white=.20555225, contrast=.55, exposure_gain=1. It applies the
existing luminance soft toe, common RGB placement, luminance-preserving gamut
compression, sRGB and display S-curve with identical parameters to every arm.
No candidate histogram, fitted exposure, local sharpening or noise reduction
can alter this transform. Baseline107's independently stored white=.2615142 is
not used. Different black/white placement can hide a brightness difference.

VERIFIED causal display commission: the independent NumPy implementation
reproduced every 98,898,048 encoded channel of baseline106 photograph.tiff exactly:
maximum 0 u16 delta, mean 0, no differing channels. Baseline107's fixed display is
intentionally not expected to equal its separately auto-toned photograph.

A 384x384 known-pattern PNG commissions native tool viewing: one-pixel vertical
stripes, one-pixel checker, four-pixel stripes, single red column and green/blue
boundary rows. PNG readback is bit-exact and view_image(detail=original) was
inspected. This establishes unresampled artifact pixels/tool delivery, not any
arbitrary user's physical display calibration or zoom. Complete 1400x933
overviews are orientation only. All defect verdicts use native 384px crops.

## Independently selected witnesses

Complete baseline106 and 107 overviews were inspected before selecting these
regions. Both sets of native crops were then inspected; no candidate image was
viewed. The exact freeze is review-freeze.json and roi-frozen.json. Origins below
are top-left native pixels; every rectangle is 384x384. Identical origins retain
the same broad landmark in these two baselines but are not pixel registration.

| Witness | x,y | Main challenge |
| --- | --- | --- |
| Dark background |5750,600|Bias, colored streaks and outliers; not a known-flat temporal-noise measurement|
| Cyan wing scales |3100,2050|Real boundaries versus invented repeated/checker texture|
| Dark wing band |2730,2150|Low-contrast texture erased by smoothing|
| Upper leg hairs |1570,690|Thin tips, doubled contours and chromatic edge spread|
| Wing-leg occlusion |2500,2800|Depth boundary, hidden leg and occlusion halo|
| Bright wing glint |3400,1460|Highlight islands, color fringe and censored-support behavior|
| Blue/cyan chroma |2480,810|Saturated blue texture and hue continuity|
| Face edge |5100,2990|Dark curved boundary and eye-region structure|
| Antenna hairs |5290,2470|Isolated fine filaments and motion/registration doubles|

Baseline-only observations: both contain soft/doubled hair fringes, bright white
and colored glint edges, and faint colored diagonal background structure. These
are reference defects, not automatically regressions in a candidate. The
wing-leg occlusion has substantially more visible bright green/blue leg in 107
than 106. That may involve focus, occlusion or reflectance; it is not established
as noise or a single exposure factor. Bright neutral master pixels above 1 and
white display pixels do not alone certify which original photosites saturated.
Use the consumer's censored-support evidence for that claim.

## Candidate comparison rules

1. Inspect each complete fixed-transform overview first for framing, missing
   anatomy, incomplete focus coverage, seams and color changes. Overview
   sharpness cannot decide quality.
2. Compare native-single 106 and 107, native pooled 598, and grouped 598 with primary
   absent/present on one common geometry/domain where possible. This separates
   sampling changes from grouping. Legacy photographs provide context, not
   ground truth. Legacy106/107 used cover SCALE=.9824/.9811 (rounded log values);
   native sessions crop their full gauge. Map witness centers using exact saved
   geometry and record mapping/rounding, then take native 384pixel slices without
   resampling. Do not compare unmatched pixels numerically. If exact legacy scale
   is unavailable, use named landmarks and explicitly keep that scale caveat.
3. Reuse the frozen transform verbatim, with the same ICC. Never auto-tone each
   candidate or optimize witness placement after seeing its apparent benefit.
   A new failure outside frozen witnesses may be documented as an additional
   adverse witness, with its post-hoc status explicit.
4. Judge hair tips, separated edges, scale boundaries, repeated artificial
   patterns, false glint structure, occlusion trails and hue continuity. Keep
   losses and improvements per witness rather than a single sharpness score.
   Gradient energy can increase with noise/ringing and decrease with blur; it
   cannot establish quality. Agreement/FRC can share bias and is not resolution.
5. Dark-region mean/channel bias/outlier structure are descriptive measurements.
   Spatial SD/MAD contains scene structure and is not temporal sigma. A difference
   of two finished stacks also includes registration, focus and reflectance
   differences. Do not turn it into a sqrt(K) noise claim. Known-flat producing
   controls commission temporal noise mechanics separately.
6. Preserve full linear masters, complete fixed displays, source census, selected
   geometry, command/environment/build receipts and exact crop origins. A
   photographic conclusion requires complete outputs and independent inspection.

To render a released candidate without refitting display parameters:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/prepare-review.py render --master <released-master.tiff> --destination <fresh-review-directory> --label <arm> --transform outputs/multi-stack/independent-review/fixed-transform.json

Candidate ROI JSON must carry the mapped integer origins and its mapping
receipt. The current helper refuses non-float/nonlinear masters and nonfinite
samples; native crops are read back and checked for exact pixel equality.

## Planned held-out real placement audit; NOT executed

Consumer and gauge: per-frame full green-quad placements (two sensor pixels per
quad pixel), rebased to the delivered anchor. Estimate local residual vectors
against several independently measured partners; do not audit only one anchor
or score just the final merged photograph. Report all frames including refused
or unmeasurable ones. This is a CONSISTENCY audit, not physical placement truth.

Before any audit read, freeze a spatial site list from these baseline anatomical
regions plus background refusal controls. Reconstruct all guide/coarse/native
fit rectangles from the recorded configuration and exact tile grid. A held-out
site must be disjoint from their reference and mapped moving support, including
search/resampler footprints. Shifted grids are not automatically disjoint. If
there is insufficient untouched texture, explicitly reserve audit sites and
refit without them, or call the result a reused-data consistency diagnostic.

Choose distributed focus-index strata, both sweep ends, reversed/unequal partner
options, short/medium/long direct edges and actual cross-pass proposals. Obtain
only bounded original-cache green patches when root releases that job. Refine
local displacement using an independent float64 phase-correlation estimator and
challenge it with an alternative normalized-correlation fit. Neither estimator
gets to change the delivered map. Freeze frequency/contrast/ambiguity defaults
before real scoring. Repeated scale texture and specular differences may refuse
or bias either estimator, so retain score surfaces/second-peak diagnostics and
raw refusals instead of silently dropping hard frames.

Commission first: identity/self-pair positive; planted independent-noise latent
pair with known displacement; wrong map +0.5 sensor pixel translation and known
scale/rotation error; shuffled partners and periodic-texture distractor; flat
no-scene input must refuse. Test the actual extraction/gauge/units path. A plant
can validate that operator, not the real scene's optical calibration. For paired
real patches, focus mismatch and reflectance can violate correspondence even
when the camera is rigid. Such disagreement is not proof the map alone is wrong.

Summarize residual vectors per frame/partner/depth site, native and sensor units,
median/tail/max with sample counts and refusals. Include cycle consistency and
change of partner/reference; cycles can still share bias. Compare the unchanged
legacy geometry and joint geometry on the same held-out sites, not just fit RMS.
Never promote consistency into a same-focus/PSF certificate or absolute accuracy.
