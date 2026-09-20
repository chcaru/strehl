# Independent fixed core-lineage truth screen

2026-09-19, before execution. Root builds/runs; numerical author does not
verify. Test-only actual rounded native gather, injected existing ISO100
noise, actual baseline and whole-AC Replay, terminal mean base and InputRange
hull. No RAW or full photograph run is admitted by implementation alone.

## Frozen algorithm contract reviewed

Original u16 active-local CFA planes supply positive `I-binomial5(I)` contrast.
Its variance uses the same injected model and the squared, combined original
sample coefficients of `delta-binomial5`; the field is the maximum positive
standardized contrast across all four planes. This maximum is not a calibrated
four-channel false-positive probability. No private fitted noise or WB change.

Max-tree: eight-connected pixels, equal-value batches, floor z5, leaf peak>=8,
peak-minus-saddle>=3, core above the peak/saddle midpoint. Any original code
>=Levels.white in any branch's exact5x5 contrast stencil refuses that branch.
Source-cell centre is active-local quad(x+.25,y+.25); use the inverse held
similarity about the full-quad midpoint, subtract the crop and take floor.
Odd decoded active origins affect storage addressing, not map coordinates.
Aliased branches contest the cell; scan order cannot choose a winner.

Adjacent frames require mutual unique footprint overlap. Split/merge invalidates
the connected lineage; missing correspondence ends it. At least three consecutive
nodes and at least two persistent intersection-core cells, including both
checkerboard subsets. The subsets' source sets above90% of their own peak
actual finest SoftPower weight must overlap; whole-core profile spread must
reach25% of its maximum. Normalize mean whole-core source weights, transport
only to observed branch union, reject conflicting lineages, and use3x3 support
occupancy for an internal taper without support expansion. These are frozen
heuristics, not measured optical constants or ownership confidence.

## One small actual-consumer screen

Run exact test `merge_cmd::core_lineage::independent_controls::independent_core_lineage_actual_truth_screen`
with `STREHL_CORE_LINEAGE_OUT` set to a new root-owned output directory. Suggested
generated-test limits120 wall seconds,180 CPU seconds,2 GiB committed memory.
Five original320x288 u16 frames, odd decoded active origin(7,11), asymmetric
quad crop[7,9,145,125], fixed fractional similarities and warm WB[1.7,1,2.3].
Existing shared-source-field truth fixtures/scoring are retained verbatim in
independent-fixtures.rs, except the declared no-glint twin, same-world toggle,
module imports and synthetic filenames. The old screen remains closed.

One three-cell/three-source arithmetic witness precedes the image screen:
checkerboard subset sizes2:1, weights[4,4,8]/[2,2,4]/[1,1,1] must yield source
memberships[16/27,8/27,3/27], not equal-subset weighting[.6,.3,.1]. Reverse
those fixed inputs and require the same support and reversed memberships;
occupancy cannot expand beyond the supplied cells. This enforces the frozen
whole-core mean and gives a lineage-only reversal witness independent of any
source-index-dependent probe. It is explicitly arithmetic, not image quality.

Flat noise is first: RGB and R-G/B-G truth error must be<=1.25x baseline.
The glint/depth scene must improve fan RGB truth error by>=5%, retain core and
real nearby structure within1.10x baseline RGB error, and retain>=90% of
baseline truth-capped component amplitude whenever baseline recovery>=.5.
The fan baseline error must exceed2x flat error, at least four fan quads must
actually activate, and output must change. Universal refusal cannot pass.
A deliberately forced late source must worsen fan error by>10% or fail core
component retention; Off must preserve complete CFA and RGB bits exactly.

Genuinely extended coloured radial detail, thin crossed depths, and the same
depth-boundary scene with its glint removed all have the1.10x RGB and90%
component-retention guards. Radial chroma also stays<=1.10x baseline. Their
baseline true components must be live (recovery>=.5). Fallback is allowed on
destroyers; an attractive component tree does not credit quality. Truth-error
and capped amplitude controls are commissioned with exact truth, half-amplitude,
colour-neutralized and overcontrast images; gradient energy is never a prize.

Reverse the actual live glint source/transform sequence. Alpha must be bit-exact,
source-reversed q differs by<=2e-5 and candidate normalized RGB by<=2e-6; f32
reduction-order noise is tolerated only at those fixed bounds. Test another
sequence-input identity witness in that same pair: retain reversed baseline RGB
maximum error and compare each original source's known4, guide, variance,
energy, floor and beta bits after reversing indices. If probe seeds keyed by
sequence index change these fields, the lineage-only reversal test is invalid
and cannot pass admission; report that cause instead of declaring a lineage
defect or relaxing output tolerances. No extra execution is required.

Test another
world where every source has the same fully focused latent but independent
noise: core/fan/boundary/real texture RGB and chroma must stay<=1.10x baseline
and preserve the same true components. A coherent wrong noise selector can fail.

Noiseless flat, constant-green/real-colour structure, one persistent unsaturated
original hot site, and a circular original clipped core must have alpha exactly
zero and full CFA/RGB fallback bits exact. These refusal controls remain binding
even if later real glints contain clipped samples. Original hashes, actual
replay known4 equality, finite fields, membership sum/coverage and zero-support
CFA identity are checked in every arm.

Scope is ISO100 only: the prior ISO400 fan plant failed its own exercise test,
so it supplies no higher-noise transfer claim here. A numerical test completion
is distinct from `photographic_replay_admitted`; every fixed image-truth and
exercise bar must pass for that boolean. Root independently decides any next
photo action. Failure closes this exact intervention without a threshold,
correspondence-radius or source-window sweep.
