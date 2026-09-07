# M194e — joint-pupil depth-boundary model

2026-09-07. **In progress; complete numerical commissioning has not passed.**
Both full image attempts stopped at registered sensor-cell error limits.
Each completed three primary frames; the fourth refused, and neither refinement
arm ran. There is no admitted CFA package or merge-quality result from this
milestone yet. Preserve both failures while investigating their causes.

## Purpose and scope

M194d reduced flat temporal noise with an experimental positive band-weight
pedestal, while retaining small detail costs and a sparse adverse tail. Its
single-plane benchmark cannot adjudicate occlusion-boundary fidelity. M194e
therefore supplies the missing, separately checked two-layer image formation
model before another production comparison. It is a scalar geometric model,
not a claim of physically calibrated optics or state-of-the-art image quality.

For each native sensor-cell location and one shared uniform-disc pupil ray,
evaluate the foreground mask and foreground radiance at that ray's foreground
intersection, and the visible background radiance at the same ray's background
intersection. Integrate their coupled radiance over pupil area and the unit
sensor cell. This preserves visibility/radiance covariance lost by multiplying
separately blurred layer means. Signed defocus and canonical/native coordinates
are explicit. There is no intensity Jacobian for this radiance-normalized map.

The registered scene is five 64x48 frames, a textured opaque foreground
half-plane in front of a textured background plane at depths 1 and 2,
inverse-focus values 0.5 through 1 in steps of 0.125,
K=12, and identity per-frame geometry. The independent analytic controls also
re-choose geometry, radiance, mask orientation and transformed coordinates.
Diffraction, aberrations, transparency, scattering, spectral effects, physical
calibration and real RAW transfer are outside this scope. The generator uses
f64 integration and emits u16 CFA only after independent mathematical admission;
production arithmetic and defaults are unchanged.

## Preregistration and independent responsibilities

The original design/release was committed at
`773f576299f58ea0b0a998a22243ee837f6f7d8d`.
The files in [the experiment](../../experiments/m194e-joint-pupil/) include
`implementation-plan.md`, `implementation-preregister.md`, `independent-design.md`
and the prior-art decisions. M25's and BUILD-BLEND's prior refusals are retained;
M87's failed propagation/gate argument is not relabeled as a refutation of all
two-component models. No SYNTHESIS fact fold is proposed here.

The producer integrates analytic radial primitives with polar angular
quadrature, then clipped sensor-cell triangles. The independent numerical
reference integrates pupil-normal Cartesian chords and analytic clipped-cell
Fourier/moment expressions. It does not reuse the author's integration code.
The independent emission reviewer uses a separately commissioned scalar
rounding/CFA oracle and actual file mutations. Root owns the emission/schema
boundary and program decisions; neither author verifies their own code.

## Failures that determined the implementation

**MEASURED original method refusal:** the independent 340-case map contains
170 point and 170 cell evaluations. All 170 point calls returned; 56 cell calls
refused at the angular depth limit. All 284 returned values met their applicable
discrepancy bars, but this was an incomplete method, not a passing subset.
The exact failing sources and results were committed at
`7d08462aa7b6ae5992976cf129baa8f16889aae5`.

The diagnosis found a narrow radial-visibility transition near a pupil-normal
projection zero. The prospective numerical amendment committed at
`d77bc3feccefb3a02d8d2c8e3911d681ead4f8f1` adds a fixed geometric ladder of
radial crossing angles. It changes subdivision, without truncating pupil mass
or relaxing model, error, depth or work limits. A shared-height/no-ladder
ablation retains the old refusal, separating the ladder from the simultaneous
algebraic-expression consistency change. The preserved
[author report](../../experiments/m194e-joint-pupil/author-report.md) also records
two harness defects: exact floating equality and an unobservable tiny CPU-clock
expiry assertion.

**VERIFIED component controls after numerical amendment 1:** the independently
chosen 31 analytic and 336 textured point/cell checks pass on that numerical
source. Textured discrepancy is at most 6.55099e-6 electrons, RMS 6.29635e-7.
This controls instrument accuracy; it does not replace the fixed full images.
A separate 19x11 traversal fixture crosses actual tile boundaries, proves
different complete visit orders, and retains byte-identical scalar and error
arrays with diagnostics off, active and placebo. The author's original 3x2
tile comparison did not exercise a tile boundary and is not that evidence.

**MEASURED and repaired metadata defect:** the independent emitter API first
passed 106 of 107 controls. A nested numerical receipt could declare an integer
dtype for the same floating-point array accepted by its parent. The schema now
binds resolved path, dtype, shape, length and hash together. The final independent
API run passes 109 controls. An intervening startup refusal came from root's
65-character transcription of a 64-character hash; source bytes were unchanged.
Private API fixture gates are never scientific authority for their invented
arrays. Details and preserved results are in the
[independent API report](../../experiments/m194e-joint-pupil/independent-emission-api-review.md).

## First complete-run attempt

The [full-float release](../../experiments/m194e-joint-pupil/full-float-release.md)
required every pixel of all five primary images and both refinement arms.
Final producer sources are committed at `b7007d47`; launch preceded that source
commit, with exact before/after hashes and snapshots recorded. The earlier
numerical preregistration was already committed before launch.

The actual command is recorded in
`experiments/m194e-joint-pupil/float-run-1/result.json`, including interpreter,
original arguments and isolated bytecode-cache settings. The full log and the
partial frame are retained. **Terminal result: UNCOMMISSIONED_NUMERICS.**
Primary frames 0, 1 and 2 completed. Frame 3 (inverse focus 0.875) refused at
the cell depth/error ceiling after 230 cells. This is a different failure from
the original angular-depth refusal. No time/work ceiling is identified as the
cause, no later arm ran, and no genuine float or CFA authority was issued.

Diagnosis and a prospectively reviewed correction are the next work. Existing
error tolerances and scientific scope remain fixed. In particular, a numerical
error indicator is not a rigorous error bound by itself, agreement on completed
frames cannot admit an incomplete population, and permissive file metadata
cannot substitute for independent image formation.

The fixed failed pixel is (30,4). Its failing leaf meets the foreground-pupil
tangency along an edge. The author's low/high cell-order discrepancy is
3.848784e-6 electrons against an allocated 2.141775e-6; the summed weighted
pupil indicators are about 7.19e-15. These are observed quadrature indicators,
not independently certified leaf errors. The independent whole-cell reference
is 15204.412150777305 electrons. A new diagnostic that generalized that
reference to the tiny leaf first used an invalid affine null and then refused
at its own quadrature warning after that control was corrected to zero defocus.
Both attempts are retained. They do not invalidate the previously frozen
whole-cell reference, and they do not establish the true local leaf error.
The proposed numerical correction must therefore still pass independent
whole-cell and complete-image comparisons.

## Numerical amendment 2: current implementation

The squared-distance cell-coordinate amendment and independent prospective
review were committed at `d839ce9b` before implementation. It changes variables
near a pupil tangency, with separately derived edge/vertex Jacobians. Its
fixed finite-arithmetic predicate only selects quadrature coordinates; it does
not snap vertices, discard slivers or establish exact physical incidence.
Orders, depths, error bars and work limits remain unchanged.

On numerical source
`a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5`,
the independently chosen map controls pass all 399 cases. The original failed
cell returns 15204.412150780796 electrons, differing from the frozen independent
reference by about 3.49e-9. The linear-map ablation still refuses. Independent
API4 passes the unchanged 31 analytic and 336 textured point/cell cases;
the textured maximum is 2.06892e-7 electrons and RMS 1.23375e-8. These are
component results, not admission of the subsequently incomplete image rerun.

Evidence is in `independent-map-controls-1/result.json`,
`independent-author-api-4/result.json` and the corresponding exact source
snapshots under the experiment. Updated observer/traversal controls likewise
remain separate from image-accuracy admission. Before the full rerun, root's
controller audit also requires freezing design bindings at entry and checking
them at exit; computing them only at exit would not establish which design
bytes accompanied the run. That administrative correction changes no renderer
arithmetic. Author controls8 bind the corrected controller and pass172/172;
the final independent emission API5 and CFA-reader controls3 pass109/109 and
26/26 respectively. The genuine reader again refuses fixture-only authority.

**Second complete-run outcome:** `float-run-2` also terminates
`UNCOMMISSIONED_NUMERICS`. It completes primary frames0,1,2 and refuses in
frame3 after255 cells, at (31,7). Its failing leaf correctly selects the vertex
map; the cell-order indicator3.44316831757e-6 exceeds its area-proportional
allocation3.17449881569e-6. The weighted pupil terms sum to about1.30e-14.
This is not a missed tangency predicate. The whole-cell independent reference
is15172.35081699726 electrons; no value from the refused author cell is admitted.
Source and design bindings are unchanged across this failed run. Its97.48-second
CPU observation is run provenance, not a comparative speed result.
Source commit `dd91182bc42b1fd7cd3fa4b6d5d52ba4cf8212fe` at 13:32:46 UTC
followed the run's 13:27:51.720232 UTC completion. The amendment preregistration
at `d839ce9b` preceded implementation; exact before/after source and design
snapshots identify the bytes used by the run.

**VERIFIED diagnostic, not admission:** `cell-allocation-2` retains all 508
nodes through depth 6. The independent reader reconstructs child geometry and
complete, disjoint frontiers. The original 34-leaf stopping frontier, including
the locally refusing leaf, has summed absolute-difference-plus-pupil indicator
8.85677475546e-5 and high-pupil sum 1.46237557330e-6, within the existing
whole-cell limits. Its value differs from the independent reference by
9.09e-12 electrons. The initial frontier instead fails at 0.02088286, so the
aggregate criterion can reject this input. A diagnostic global-priority sequence
reaches 18 leaves after 14 splits, with indicator 0.0006571524094. These are
one-cell observations, not full-image admission or a performance forecast.

The prospective third amendment replaces the area-proportional local allocation
with a complete-frontier, absolute-error aggregate and deterministic refinement
priority. It retains the whole-cell, separate pupil, independent full-image and
refinement limits, plus existing orders, depth and resource ceilings. The former
local condition becomes a diagnostic. This is an explicit change to the former
admission rule, and neither failed run is retroactively passed. Implementation
and new full-image evidence remain pending at this stage.

## Consequence for the following production experiment

The [source and size audit](../../experiments/m194e-joint-pupil/next-production-bridge.md)
finds an existing production handoff to reuse. A distinct strict reader is
needed for this input meaning; the old M194b input schema must remain intact.
The present 64x48 native fixture realizes only one Laplacian band plus a base,
with the floor probe falling back rather than measuring a three-band floor.
It can commission input-to-writer integration once admitted. A three-band
boundary-quality experiment needs a larger, prospectively placed scene and
noise population, with output coordinates, border support and sparse errors
explicitly retained. No quality population or production bridge has run yet.
