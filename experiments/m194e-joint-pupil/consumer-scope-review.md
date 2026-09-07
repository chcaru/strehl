# M194e consumer and claim scope review

2026-09-07. **ARGUED scope review / DERIVED gauge relations / read-only source
audit.** No generator implementation, tests, outputs, production edits or new
quality bar were made for this review. The author and independent numerical
preregistrations were still being prepared when this review began.

The [charter](charter.md) and
[focused prior audit](../m194d-band-admission/next-occlusion-audit.md) support
commissioning the bounded joint-pupil geometric model first. They correctly
retain M25's failed physical gates, M87's corrected model/propagation
distinction, and M63's rejection of bimodality as evidence of two depths.
None of those conclusions needs to be reopened by this consumer audit.

The safe next product handoff is a separately scoped, versioned test consumer
that loads this model's actual CFA files and calls the existing prepared
Pyramid path. It must not call the new inputs M194b's `plane`, borrow its
producer identity, or relax the frozen M194b/M194d validators. No such Rust
change or quality run is authorized by the current commission.

## What a successful commission would establish

| Evidence | Admissible conclusion | Does not establish |
| --- | --- | --- |
| Actual joint sample/evaluate/accumulate controls, with signed-defocus and separate-mean destroyers | The implemented declared geometric model couples foreground visibility and background radiance on the same ray | Thin-lens/camera accuracy, diffraction, calibration or real occlusion transfer |
| Independent analytic limits and different pupil/cell integration | Agreement and bounded numerical error on the frozen cases, domains and resolutions actually checked | A uniform error bound over arbitrary scenes, frequencies, layer geometry or aperture |
| Expected-electron and CFA conversion checks | The declared radiance-to-electron/DN, CFA parity, rounding and clipping operations produce their promised bytes | Correct physical gain/read noise or a noise-free production estimator |
| Later actual prepared-source render and fresh output checks | The production gather, fold, collapse and writer consumed these declared inputs and placements | RAW decoding, alignment estimation, useful depth recovery or a passing quality comparison |
| A later separately approved fixed comparison | A measured development tradeoff under this specific model and reference | An attainable error floor, general occlusion quality, a repaired historical gate, default promotion or SOTA admission |

A geometric model can express a failure that a one-plane plant cannot express
without becoming physical truth. Conversely, a failed numerical control can
be a completed commissioning result: it should withhold dependent bridge or
quality claims, preserve its evidence, and not silently select new tolerances
or an easier scene.

## Freeze the gauge before either implementation

M194b's existing declared forward placement is

```text
canonical q -> native source z = c + a_k (q - c).
```

The production gather consumes that direction. For a generated native sensor
sample at pixel centre z plus unit-cell offset delta, the corresponding
canonical pinhole coordinate is therefore

```text
x_k(z, delta) = c + (z + delta - c) / a_k,
delta in [-1/2, 1/2]^2.
```

This is a gauge derivation, not an estimated placement. The author must state
where the signed pupil displacement is applied. For example, a **canonical
displacement** convention would evaluate a layer at
`x_k(z,delta) + d_layer(k) u`, with u on the unit disc. A **native displacement**
convention would instead evaluate `c + (z+delta+d_native_layer(k)u-c)/a_k`.
They differ by a scale factor. Either declared geometric convention can be
commissioned; mixing them between generator, reference and consumer cannot.
This review does not choose the author's final ray law.

Consequences that belong in the preregistration and future manifest:

- A native unit-square cell becomes a square of side `1/a_k` in canonical
  coordinates. Using a canonical unit square for every input frame omits the
  changing footprint. Integrating with native offsets keeps the averaging
  measure explicit. If integration instead changes variables to canonical
  area, its normalization must change consistently; the DC control is one
  necessary detector.
- Pixel centres, half-cell offsets, native versus quad coordinates, scale
  centre and reference index need exact definitions. The 320×240 input is
  native; its corresponding plane geometry is 160×120. Crop origins used by
  the Pyramid consumer are in plane coordinates. Active CFA parity belongs
  to the optical input coordinates, independently of padded storage origin.
- If the M103-derived scale track is used, keep all nine declared curved
  placements and their source binding. The focus coordinate used by the
  geometric defocus law is an explicitly synthetic parameter; layer order or
  real inverse depth must not be inferred from its numerical value.
- The two layers must share **both** the pupil sample and the sensor-cell
  sample before visibility selection. Integrating mask/background separately
  over a cell can lose another covariance term even at aperture zero. A
  constant-background edge-area limit cannot alone reject that error; the
  textured joint control must reach the actual integration path.

The pupil density and its normalization also belong to the model. Retain
weights for every ray, including those on which the background is hidden.
Renormalizing a layer by only its visible samples is a different operation
from integrating the visible radiance over the sensor's full pupil/cell measure.

## Signed defocus and the reference target

For a symmetric normalized disc, reversing **both** layer displacements is
the coordinate substitution `u -> -u`. The image cannot distinguish that
global sign convention. A finite quadrature may leave numerical error unless
its nodes/weights have the corresponding symmetry; that does not create a
physical sign observable. Do not commission global sign with two expected
different pictures when the stated model makes them identical.

By contrast, replacing the signed displacements by their absolute values
when focus lies between the two layers changes their relative direction.
It can alter which background texture is paired with an uncovered ray.
The independent control must actually use the between-layer case and an
asymmetric textured background. Foreground/background order is separately
declared and cannot switch to whichever surface is nearer the current focus.

The pinhole ideal target should compose the two layers at each canonical
sensor-cell sample and then integrate that visible radiance. It is not the
centre-sampled foreground/background composite, the product of separate cell
means, or a nearest-focus frame. No finite-aperture frame is simultaneously
focused at both distinct layer depths. A layerwise all-in-focus construction
or a composite assembled from separate best-depth frames is a counterfactual
reference and must remain named as such.

M194b's optical-observation target contains an explicitly different scalar
diffraction/aperture operation. It must not be imported as the new two-layer
observation target or called an attainable floor. Initial M194e commissioning
can deliver the declared geometric source frames and an ideal pinhole latent;
it need not invent a second quality target to complete a numerical test.
Later boundary masks should come from immutable canonical scene geometry,
not from the output's focus field or a fitted background level.

## Numerical and computational budget cautions

Freeze independent pupil and cell resolutions, refinement levels, tested
locations/regions, absolute units, maximum error and RMS error before intended
scene evaluation. Pupil refinement alone cannot diagnose cell-integration
error. Agreement on nested midpoint grids can share edge aliasing; a shifted
edge and a distinct integration basis provide different failure modes.
Errors must be read separately near visibility boundaries and in interiors:
a full-image mean can dilute the one region the new model is meant to test.

Do not inherit M194b's 1 DN RMS convergence allowance as evidence for the
much smaller M194d plane changes. M194d measured noise-off observation-RMSE
changes around 0.001–0.002 DN and wave changes below 0.009 DN. A numerical
generator can be adequate for a large boundary effect and inadequate for
resolving effects at that smaller scale. Choose and disclose the new engineering
budget from its intended claim before running; do not retrofit it to whichever
result is favorable. No tolerance value is selected by this scope review.

Retain continuous expected-electron values before quantization. Report how an
electron-domain error maps through the declared gain and consumed f32 WB to
input DN; do not extend that linear conversion into an unproved output-error
bound through a nonlinear merge. Separately check CFA rounding/clamping and
final TIFF quantization. Arbitrarily small continuous errors can cross a
rounding boundary, so general convergence need not mean byte identity.
Exact nulls and a true unchanged transport control can still require identity.
Noise-off generation also does not imply zero injected noise in the production
gate: those coefficients determine merge behavior and must remain explicit.

The integration workload grows with frame count, pixel count, cell samples
and pupil samples. A small scene description does not make a dense Cartesian
product of those arrays small. Keep pupil/cell accumulators bounded by tiles
or samples, emit at most one active u16 CFA frame at a time, and bind the
resource ceiling before refinement. A small mathematical control domain
does not automatically commission the eventual full input extent. These are
design constraints, not a measured timing or memory result.

## Smallest future production handoff

The current Rust `known-scene-benchmark.rs::Manifest` is explicitly
`m194b-known-scene-v1`; `Inputs::load` fixes M194b scene names, sensor dimensions,
frame count/reference, noise/levels and placement conventions. Its producer
fields are not a generic physical-model registry. The frozen Python readers
add exact M194b producer-case and source bindings. Giving the new bytes a
`scene: plane` label would therefore misdescribe their semantics even if a
low-level byte loader happened to accept them.

A later approved bridge should be a narrow versioned entry that:

1. Accepts a new explicit producer/model schema and an external expected
   manifest digest. Bind ordered layers, radiance/mask parameters, signed ray
   equation and units, pupil/cell measure, similarities, expected-electron
   artifacts, CFA conversion and actual indexed file hashes. Bind the exact
   passed commission record and source revision. A candidate-supplied
   `commissioned: true` flag is not that authority.
2. Converts that validated data to the same decoded `Frame` source,
   `PlaneGeometry`, injected `NoiseModel`, known `WarpMap` and WB expected by
   `run_pyramid_prepared`. Reuse that actual fold/collapse/TIFF writer. Share
   only small byte-loading or validated-data helpers if needed; do not create
   a second merge, general plugin registry, or aligned-frame stack.
3. Resolves the actual production crop before rendering and emits a new
   versioned plan under an external plan hash. The plan states which model,
   geometry, input files, noise coefficients and output interpretation it
   consumes. Rendering recomputes and matches it, and its receipt binds the
   actual TIFF and source reads. Model schema and output-grid schema have
   different jobs; neither should silently supply authority for the other.
4. Keeps the original M194b/M194d entry semantics intact. A small compatibility
   control can transport already bound CFA bytes through the new loading
   route, with that transport explicitly identified rather than claimed as a
   joint-pupil render. Pair it with a real changed-input case and a native/
   quad or crop-direction refusal. Preserve build/source and actual TIFF
   evidence using the already commissioned controller patterns. No new
   general evidence engine is needed.

The first real M194e handoff can be a noiseless model/source smoke with an
explicit production noise configuration. A full noisy quality matrix, a new
reference/ROI policy and any operator decision require the next separately
approved scope. Reusing frozen `score.py` numerical primitives is reasonable
where their contracts apply; its scene-target factory and M194b-specific
receipt validator do not automatically apply to these inputs.

This keeps the useful objective small: commission the missing visibility
interaction, then prove that its declared CFA bytes reach the existing
production consumer. It preserves all earlier physical and calibration limits
while providing the next experiment with an input that can express a genuine
two-depth boundary.

## Read-only basis

This review read the charter and focused prior audit above, M194b's
`producer-preregister.json`, the actual `known-scene-benchmark.rs` manifest,
input validation and prepare/render path, `merge_cmd.rs::run_pyramid_prepared`,
and the relevant storage/profile architecture decisions in SYNTHESIS.
M194d numerical scale references come from its independently verified complete
comparison, not a new run. No external repository source, test, renderer,
capture, numerical gate or performance command was executed for this review.
