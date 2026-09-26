# Native gain-only photometric normalization

2026-09-25. Experiment source prepared; no RAW, build, render or generated measurement.
One fixed native-consumer experiment, no production/default change or sweep.
The complete illuminant-color comparison was visually unhelpful. This different
route can remove brightness differences carried from source frames into mixed
detail; it cannot repair displaced hairs or recover clipped glare. Existing
marigold traces motivate a test of late brightening, not a finding of illumination
drift or permission to erase defocus-dependent radiance.

## Existing evidence and limits

Mechanical search run: `prior_art.py photometric normalization flux gain`.
Read M91, M99, M97q, M125, BUILD-GHOST, M87 and relevant SYNTHESIS records.
M91's two spatial-uniformity instruments failed their own uniform-drift controls;
gain application harmed two of six stacks. M99 refuted the geometric `1/a²`
rule and whole-frame flux as the background corrector. M97q retracted the old
un-eroded-mask quality headline: pure defocus gave 3.63% false gain; existing
16-pixel erosion fixed that particular plant. A fixed finite mask is still not
guaranteed flux-conserving at larger blur. M125's 1.84% auto threshold belongs to
33–100-frame legacy evidence and will not be ported. Its apparent advantage was
dominated by one stack. BUILD-GHOST's old native corpus review found little
visible need; M87 photometric changes did not establish occlusion-halo repair.
None is a positive quality claim for the present native marigold consumer.

## Exact estimator and consumer

Use one actual reference `BandWorker::fold`, then existing `FocusField::compute`
and `merge::regularise` on that consumed luma, followed by existing
`photometric::low_detail_mask(detail,luma,.40,.60)` and
`erode_mask(...,16,...)`; require existing total support minimum 1024 quad sites.
This explicitly selects the legacy fixed-window branch with no adaptive scale,
layer support, guide radius or plugin focus override. The default legacy
estimator's separate stack-derived acuity pass is not imported. No new focus
operator, mask, threshold or estimator is invented. The reference is a supplied
stack index, fixed before measurement. Reject incomplete gather support; masks
remain fixed in output coordinates. Root approved this exact branch before
implementation; the adaptive-depth-guide branch is not tested.

Stream actual unmodified `BandWorker` gathers. Fold black-subtracted green luma
with `Flux::fold_covered`; use the existing `PhotometricMap::from_flux` ratio to
the reference. Preserve its clipping, [0.5,2] gain and unusable-flux refusals.
The clipping threshold is the existing legacy container maximum minus black,
not a new sensor-white guard. A clipped reference has its own gain refused but
its mean still anchors other fitted gains, exactly as existing PhotometricMap
does. The receipt exposes this behavior; it does not imply global refusal.
No offset, image brightness matching, fitted geometric law or oracle plant gain.

There is no added spatial guard. Root explicitly rejected a proposed quadrant
test before implementation to keep this an unchanged-estimator port. Existing
frame refusals use gain exactly one while other fitted frames remain eligible,
as PhotometricMap already does. Missing total support or unusable reference is
`UNAVAILABLE`, never evidence of uniformity. The independent uniform-drift
positive must be admitted; refusal cannot count as a safe correction. If the
unchanged scalar estimator applies a harmful correction under spatially varying
illumination or defocus, that is failure of this recipe and stops the experiment.

Replay each frame through the actual gather, and apply the chosen scalar `c`
to its consumed f32 CFA planes and green luma. **First** obtain the existing
injected-noise variance from unscaled luma, exactly as `BandWorker::fold` does;
then multiply that variance by `c*c`. Do not evaluate the sensor model on scaled
DN. Retain the original dimensionless gather-probed beta: a uniform scalar
scales both signal/noise amplitudes and leaves this correlation ratio unchanged.
Call actual `BandMerge::add_frame_with_gain` with those arrays, then its actual
finish/input hull and final MHC. The hull and mean base intentionally describe
the corrected source radiances; they are not falsely claimed unchanged.

The experiment adapter can do this with existing private BandWorker fields and
public BandMerge APIs. Only one test-only CLI include is needed; no core edit or
change to BandWorker is necessary. It holds at most one frame's f32 fields and
fixed masks, plus normal O(image) accumulators. Originals remain u16. A reference
prepass plus two streaming passes avoids N aligned frames. Exact gain 1 bypasses
all multiplication. Disabled/unity/wholly-unavailable output must equal the original
canonical output and MHC bits; both-pass original inputs and beta are hashed.

## Small API and independent decision

`implementation.rs` is the sole owned adapter; sibling independent controls and
fixtures are reviewer-owned. Saved interface (all `pub(crate)`):

```rust
enum Mode { Off, Unity, Estimated }
fn scale_inputs(planes: &mut [Vec<f32>], luma: &mut [f32],
                variance: &mut [f32], gain: f32) -> anyhow::Result<()>;
fn compare_generated(frames: &[Frame], transforms: &[Similarity],
    crop: CropRect, reference: usize, noise: &NoiseModel,
    cfg: MergeConfig, mode: Mode) -> anyhow::Result<Comparison>;
fn estimate_generated(frames: &[Frame], transforms: &[Similarity],
    crop: CropRect, reference: usize, noise: &NoiseModel,
    cfg: MergeConfig) -> anyhow::Result<Fit>;
```

`Comparison` exposes baseline/candidate four CFA planes and actual MHC RGB,
native dimensions, mode, estimated/applied gain arrays, per-frame Flux
means/counts/clipping and existing refusals, mask count/hash, `fit_status`
(`AVAILABLE`, `UNAVAILABLE`, `PARTIAL_REFUSAL`), reasons, and
source/consumed-plane/luma/variance/beta hashes plus four fixed sample addresses
with before/after CFA, luma and variance values. An unavailable estimate applies
unity exactly but cannot qualify the positive quality claim. Individual refused
frames preserve PhotometricMap's existing unity behavior. No gain override
enters this estimator API.

Reviewer chooses compact fixtures and fixed bars before execution: flat/noise
first; actual estimated uniform drift with multiple real colored details at
different focus positions; its identical defocus-only/no-drift twin; spatially
varying opposite-side drift; insufficient eroded support; gain-squared
propagation and unity bit identity. Known wrong gain
and unscaled-variance destroyers must make the relevant tests fail. The positive
must improve actual known-truth output error and preserve true detail/color,
not merely lower spatial variation or through-focus disagreement. Generated
calibration validates the operator, not the Sony noise model. Stop on a failed
falsifier; no threshold tuning or fallback campaign. Only a passing, independently
reviewed screen can motivate a separately approved whole marigold comparison.
