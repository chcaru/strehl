# Independent fixed learned-guide screen

Prospective, 2026-09-26. This is one small feasibility experiment, not photographic
qualification. Root executes; source_trace authors the score/reconstruction path;
trace_review owns the fixtures, final score and export/replay controls; opal owns
the separately chosen arithmetic checks and scientific choice review. No results
were used to choose the following scenes, windows or bars.

## Scope and family separation

Original storage is u16 CFA, active192x176 inside a larger sentinel-filled buffer.
All image arithmetic is f32. The current injected ILCE-7CM2 noise model supplies
shot/read draws after physical illumination and before rounding/clipping at the
known white15360. Reusing that model tests the operator, not camera calibration.
Supplied small scale/rotation/translation transforms are applied once in source
generation and once through the actual current gather. Crop[8,8,80,72] quads gives
native160x144; fixed scoring coordinates below are in the original native gauge,
so addressing subtracts[16,16] exactly once.

The compact renderer reuses the layered-raw-inverse finite-pupil visibility
equation: premultiplied near radiance plus the same ray's transmittance times far
radiance, averaged over64 antithetic rays, then a fixed sigma.7 spatial optical
blur. Two surfaces are at focus coordinates0 and1, with10native maximum ray
displacement. Finite raster/bilinear sampling and this pupil approximation are
explicit limitations; the older continuum-pupil adequacy failure is not erased.
No new inverse renderer or camera/lens calibration is claimed. Arithmetic checks
reject separately averaged visibility, preserve constant radiance, and test
actual original flat-noise draws/sentinel addressing before detail export.

Twelve training cases, all N5: two flat intensities, four single-depth oriented
cosines, four straight two-layer checker/cosine occlusions, two Gaussian blobs.
Even variants use ISO100 and odd variants ISO400, under a circular disk pupil.
Seven held cases in six whole families use ISO100 only:

| Held case | N | Pupil | Role |
|---|---:|---|---|
| flat |5|ellipse .55, rotated .60rad|flat protection|
| flat |9|same ellipse|changed-source-count flat protection|
| curved bright ellipse occlusion, near stipple/far narrow structure |9|same ellipse|fixed positive|
| sinuous near fine strip/far radial coarse pattern |5|same ellipse|fixed positive|
| genuine unclipped narrow point glint, adjacent line motif |5|annulus inner radius .45|bright-detail protection|
| original clipped point glint |5|same annulus|recoverable adjacent/spread protection|
| weak signed coloured dots and far narrow line |5|same annulus|colour protection|

Neither held pupil form nor held texture/occluding geometry occurs in training.
This is more than seed/phase holdout. It is still a tiny finite synthetic corpus;
N9 is not a 299/488-source stress test. There is no held ISO400/high-ISO safety
claim. Original clipping must be live in the clipped case and absent elsewhere.
The clipped core is outside the held bounded-source reconstruction target;
no clipped-core recovery is tested. No actual mineral clipping diagnosis follows.

## Scoring before learning

Actual canonical and uniform reconstructions are the two references. Zero-head
and uniform must be byte-identical and count as one comparator. All held flat
cases precede held structured cases in export/replay. Scores use actual final
camera RGB after original CFA synthesis, mean base, input hull and MHC.

Fixed native xyxy windows: interior[30,30,162,146]; curved positive
[55,43,135,130]; near/far positive[66,42,130,138]; genuine glint
[77,73,100,96]; glint adjacent[127,49,156,134]; spread[98,69,113,110];
colour[49,43,136,128]. Curved and near/far use interior plus their positive;
unclipped glint uses interior/core/adjacent/spread; clipped uses adjacent/spread;
colour uses interior/colour; flat uses interior. No recentering or target search.

Both fixed positives must reduce RGB truth RMSE by at least5% against the better
of canonical/uniform. Every fixed window must preserve RGB, green and R-G/B-G
error within1.10 of both references. Signed mean error is also reported. These
absolute errors reject added noise, offset loss and overshoot; a signed detail
projection alone can reward overshoot or hide an offset.

Near and far detail are fitted jointly with an intercept after subtracting the
known broad background; the final absolute errors do not subtract that background.
Template SD must reach.001; joint normalized determinant must exceed.05, otherwise
the coefficient is unavailable. Rank/conditioning and signed coefficients are
saved. Every reference coefficient>=.5 requires candidate bounded[0,1] recovery
at least90% of that reference bounded above by1. Reference<.5 is unqualified local
retention, not a permanent failure even for perfect truth. It remains reported.

Before training, fixed Thin green near/far, genuine Glint green far, and Colour
red/blue near coefficients must each reach.5 in at least one reference. Every
eligible reference/channel still carries the90% protection. The two positive
reference errors must separately exceed twice the same-N flat errors, with
canonical/uniform maximum RGB difference>1e-6 in the exact positive window.
Flat brightness is.25 and is not matched to the bright scene's entire signal
range; this is a source-count/noise-model control, not exact local noise truth.

The complete final score must accept exact known truth and reject erased near,
erased far/wrong-depth, added.10 independent RGB noise and erased-image controls.
Half-near is disclosed but has no required disposition: half truth can legitimately
retain90% of a reference recovering only.5. This correction is prospective and
does not change any quality bar. Pretraining qualification is exactly truth-pass
AND positive-headroom-live AND fixed-protected-witnesses-live AND required
destroyers-rejected. A false result stops training; no new masks/targets/bar rescue.
Truth passing the scorer does not prove expressivity through positive source
weights with held mean base/hull; no such oracle representability claim is made.

## Native arithmetic and one training attempt

Three tests: `independent_arithmetic_controls`, `export_dataset`, `replay_dataset`
under `merge_cmd::learned_band_guide::independent_controls`. Config environment
`STREHL_LEARNED_BAND_GUIDE_CONFIG` names JSON `{out,dataset?,weights?,inference?}`.
Outputs are arithmetic.json; dataset.json/fixture-labels.json/pretraining.json;
and screen.json respectively. Dataset contains exactly12 training and7 held paths.
The wrapper owns source/build/process binding and forces fresh compilation.

Arithmetic controls use an independently expanded, nonzero single-tap model
oracle, a live incorrect-border destroyer, shape/nonfinite refusals and literal
zero uniform weights. Source permutation and whole-set duplication operate on
frozen feature tensors, including set means, and their normalized weighted sums.
They are not claims about re-decoded RAW stacks: canonical probe seeds depend on
source ordinal, and duplication is not independent-noise reduction.

Before fitting, Python reconstruction must match Rust uniform and prescribed
spatially varying positive weights on complete CFA/RGB arrays including borders;
the training-only commission requires an actually exercised hull clamp. The fixed
737-parameter model trains once with seed137, Adam lr.001,1024steps, final-step
checkpoint, at most300s. Loss is full-native equal-case camera-RGB MSE. Only twelve
training paths enter training; no held family/metric chooses a checkpoint.

After fitting, native replay regenerates all seven held originals and requires
source/gather metadata, features, truth, canonical and uniform exact against
export. Actual nonzero learned weights must agree with Python at max2e-5,
complete CFA at .02DN, and complete camera RGB at5e-6. These are fixed arithmetic
port bounds, not quality tolerances. Terminal mean and zero-head identity remain
exact. Learning must change RGB from uniform by>1e-6 somewhere. A fixed rotation
of learned weights by two sources on the held near/far case is replayed through
the actual CFA consumer: it must change RGB by>1e-6 and fail that case's final
score. No raw argmax is introduced.

Nomination is all held scientific guards AND learning-live AND shuffled-weight
destroyer-live/rejected after all mechanical checks. Every failure and absolute
measurement remains in the receipt. Even a pass only permits root to consider
one separately commissioned complete photograph; photographic_replay_admitted
is always false here. Fixed source-weight inference has no established full-stack
memory/speed path, and no production/default/SOTA claim follows.
