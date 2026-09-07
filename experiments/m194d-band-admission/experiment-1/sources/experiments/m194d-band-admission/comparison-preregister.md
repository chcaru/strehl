# M194d fixed production comparison preregistration

2026-09-07, root, before M194d product edits, builds or output. This specifies
the controller/readout alongside Curie's implementation preregistration and
the independent designs. It is a development experiment, not Phase-1 or SOTA
admission. No capture, sealed input, new producer realization or scorecard edit.

## One operator, two delivered arms

Immediate baseline: committed M194c `04128e041dabc0bdb86c64526cd8155dd0a0fd07`,
candidate-2's existing40 TIFFs, run index SHA-256
`71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab`.
The M194b producer and numerical scorer stay byte unchanged.

The proposed new mode is `FloorPedestalV1`: with band energy E and
F=gate*beta*V in DN², q=max(E-F,0), a=q/max(F,1 DN²), give every frame
weight `(hypot(a,1)/64)^p`, including q=0. Existing exponent schedule,
base averaging, reconstruction, hull, gather, injected noise and measured
probe remain. This is a fixed heuristic, not an energy-standard-error model
or statistically calibrated confidence level. No parameter or seed sweep.

The implementation uses `exp(clamp(p*ln(hypot(a,1)/64),-80,80))`, with
explicit candidate-only refusal of nonfinite energy/floor, accumulated sums,
resolved coefficients and pre-hull collapse. A finite weight is insufficient
to bound its product with a coefficient. The prospective extreme-product
control must refuse before writing a plausible TIFF. The implementation
preregistration restricts supported candidate configurations; incompatible
modes refuse. These checks add scans without new image arrays and carry no
performance claim. They do not alter HardFloor arithmetic.

Root authorizes implementation only after reading the completed implementation
preregistration and independent operator-specific objections. The proposal
does not by itself authorize a different law or product default.

One bound executable must produce two full matrices on the same20 manifests:

1. `hard-floor`:40 outputs, two per case, must match M194c whole TIFF bytes.
2. `floor-pedestal-v1`:40 outputs, two per case, measured against hard-floor.

Both retain the full-nine and original-frame-4-only arms, including the latter's
existing local-zero probe index. All20 plans per mode freeze before that mode's
first output. No selecting cases or failures from the matrix after seeing them.
No post-sharpening, gain fitting, re-registration or target fitting.

## Explicit settings and source binding

The test adapter records `MergeConfig.admission`, the named formula/version,
and the required `STREHL_M194D_ADMISSION` mode. New plan/receipt schemas name
M194d. Unknown/missing mode must refuse rather than silently select a default.
The existing M194b entry retains its original semantics. There is no ordinary
CLI option or default promotion in this experiment.

Root owns versioned Python adapters derived narrowly from the commissioned
M194b build/driver/matrix/reader. Reuse its actual CFA/TIFF/geometry/schema/
command checks and unchanged `score.py` arithmetic. Explicitly record changes
required for the new test name, mode, schema, source closure and driver paths.
Do not remove the new setting from receipts to make a legacy verifier accept it.

Bind source bytes before/after build and every invocation, the visible compiler
rebuild, copied executable, exact parent/child argv and controlled environment,
all source snapshots, old producer/commission digests, all manifests/CFA,
plans/receipts/TIFF and scoring sources. Extra external Rust includes are part
of the source attestation. The original source snapshots may contain test-only
files that are not compiled into the CLI executable; do not count these as
proof of an independently executed component test.

Run component tests before freezing the final image executable. Do not rebuild
over its compiler-artifact path while the image run is in progress. Preserve
failed runs, with nonzero status and actual logs; repairs require a new run
directory. The two image modes share one binary, not two inferred-equivalent
builds. Program/test/controller files freeze during the complete80-output run.

## Primary comparisons and failure directions

Retain exact fixed native ROI x[64,256), y[64,176), native crop offset(18,14),
284x212 RGB16 CameraLinear output, allRGB channels and both optical-observation
and ideal-latent references. The producer's finite numerical approximation and
physical scope remain unchanged. Neither reference is a proven attainable floor.

- All existing per-case RMSE/bias/wave/colour readings and actual paired
  eight-repeat temporal variance. Lower noisy MSE or optical-target error can
  reward smoothing; ideal-target error and noise-off complex wave response must
  remain visible. Wave amplitude alone can reward sharpening or miss phase loss.
- Paired per-repeat MSE differences and their SEM; temporal variance differences
  with delete-one-repeat jackknife SE, as commissioned in M194c. Pixel count,
  colour channels, bands and repeated deterministic runs are not new repeats.
- Retain M194c's prospective engineering review triggers: >1 DN RMSE increase
  in any registered row/channel/target, >2% temporal-variance increase in flat
  or plane, or >1 DN noise-off plane-wave amplitude loss. These trigger explicit
  disposition. They are not SOTA admission, equivalence or probability bounds.

The claimed mechanism is removal of the zero-weight-to-singleton discontinuity.
Component controls can establish that algebraic behavior. They cannot establish
camera calibration or independent-noise averaging for data-dependent weights.
If the actual flat fixture worsens, the intended noise benefit fails there.
If detail/colour worsen, report the tradeoff; do not call a lower flat variance
an overall image-quality win. Sub-trigger changes remain recorded and do not
automatically establish equivalence or superiority.

## Sparse fidelity diagnostics, fixed prospectively

For every case/arm/reference/channel, use actual ROI truth residuals to retain
minimum/maximum signed error, maximum absolute error, and p99/p99.9 absolute
error using NumPy's linear quantile convention. Record coordinates and values
of extrema in the canonical native gauge. For a tie use first row-major site;
report that convention, not artificial location certainty.

Across each matching mode pair, retain the maximum increase and maximum decrease
in absolute truth error, and the largest absolute output movement with its signed
truth-error change. These are separate quantities. A large movement may repair
an error; a mean or quantile can hide a sparse worsening. Do not restrict this
read to M194c's previously worst pixel. These are descriptive diagnostics and
do not add new pass thresholds. Known isolated-error, sign-reversal, tied-extreme
and outside-mask controls must exercise the sparse reader before image scoring.

## Independent handoff and next decision

directional_detail re-chooses component/storage/numeric/mode controls;
roadmap_audit re-chooses actual-output and provenance checks. Root does not
self-verify the controller or final quality interpretation. Commission the actual
new option/schema bindings with rehashed contradictions and unchanged controls;
reuse established numerical tests rather than duplicate their implementation.

Once this fixed experiment is complete and independently reviewed, publish its
outcome and choose the next bounded step from the evidence. A losing setting
does not license tuning this experiment until it passes. A favorable result is
limited to these software fixtures and still needs broader geometry/occlusion/
real-capture work before any default or SOTA claim.
