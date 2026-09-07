# Minimum next numerical registration

2026-09-07. Design-only refinement of
[next-larger-implementation.md](next-larger-implementation.md), read in full.
M194f's eleven-output bridge has passed its independent reader; this note
neither changes that evidence nor runs a new numerical or quality experiment.

The next bounded objective should be **commissioning the larger expected-value
producer**, not yet its proposed36-TIFF quality comparison. Use the stated
320×240 scene, offset142, identity five-frame geometry and reference2; preserve
all frozen M194e ray/numerical sources. A new wrapper owns the analytic branch,
receipt and cost counter. Noise generation and both product modes remain a
subsequent registered consumer of admitted expected frames. No repeated optical
rendering for noise seeds.

## 1. Name the two numerical meanings

The target is a continuous shared-pupil/native-unit-cell integral. For the
analytic selector, explicitly define the affine map using exact real
arithmetic on the stored binary64 matrix, centre, translation and defocus
coefficients. Form its native height coefficients **without** rounding a
precombined translation first. Exact rational squared-distance comparisons
then prove constant visibility for that real affine model. They do not prove
constant visibility for every rounded evaluation of `Similarity.inverse` and
the later mask dot product, nor equivalence with rounded clipping coefficients.
Those are numerical approximations with a discontinuous branch, not identical
expressions simply because their algebra agrees.

Record the finite matrix/defocus actually used, both source/config bindings,
and which layer or numerical fallback was selected. Exact equality goes to
fallback. The proposed4096-bit guard applies to all rational intermediates,
not just final reduced fractions; an unsupported set falls back without
changing its model values. Do not call that guard an accuracy proof.

The independent reference must specify the **same mathematical map**. It may
evaluate it at higher precision and choose Cartesian rather than polar
integration; silently recomputing different transcendental coefficients would
conflate a model difference with an integration error. A separate map-control
comparison may quantify coefficient-construction rounding, with its own label.
No point-mask byte-equivalence claim is required to accept the cell integral.
Conversely, good agreement at a few point masks cannot admit a wrong cell mean.

## 2. Geometry-only preflight, before any radiance

Freeze the scene/frames, selector, clipping/rule helpers and counter source.
Traverse every one of384000 native cells per arm, including analytic cells;
there are three separately counted arms. For numerical cells, call the actual
frozen `cell_triangles`, `tangent_indices`, `triangle_rule`, mass/area checks
and common-height `angular_cuts` used by the fallback. Count **both** low and
high cell rules and **both** angular rules at every resulting point. Do not
evaluate a field, Bessel function, pupil integral, noise draw or product output.
Only metadata and one cell's rule arrays need be retained.

The receipt needs per-frame/arm counts of all three branches, total visited
cells, numerical roots, low/high point calls, nominal angular nodes, maximum
intervals and rule/mass refusals, plus a digest of the ordered cell/branch and
point-cut stream. Every frame must cover exactly the intended coordinate set
once, not merely reach the right total. Preserve numerical cells at tangency,
negative heights and zero defocus. The earlier analytic triangle/point table
is an ideal-geometry upper bound; this actual helper traversal is authoritative
if floating clipping produces a different partition or refuses.

Keep the proposed60CPU/120wall-second and32MiB tracked-array preflight limits,
checked on the current process. Cross-check count arithmetic on a separately
chosen non-square fixture and actual roots. Kill omissions of one frame, one
cell, low-order terms and signed ladder cuts; also kill duplicate coverage and
an injected work-limit excess. A streamed digest is provenance, not proof
of coverage unless its enumerator has those powered controls.

Admission is fixed before the preflight: every frame's nominal work must be
strictly below8m points and1200m angular nodes, half the proposed16m/2400m
render ceilings. The factor-two headroom is an engineering stop rule, not a
bound on adaptation or a performance measurement. A failure means
`UNCOMMISSIONED_COST`; do not move the edge, omit a focus, relax accuracy or
raise the envelope because of the result. Root may consider a separately
registered design after retaining that failure.

## 3. Small controls that can reject the analytic branch

Run these only after their exact records and independent implementation are
registered. The external max.004e cell-value bar applies to every component;
preserve the independent reference's max.0005e refinement requirement.

| Control population | Required live failure or distinction |
|---|---|
| Constant and affine, both full layers; d=0; wave argument0 and2^-20 | DC/affine mean preserved; absent zero limit and changed cell normalization rejected |
| Disc arguments5 and6.4, positive DC plus phase-zero wave | Negative transfer retained; abs/clamp destroyers exceed.004e |
| Nonzero x/y square factors, rotated/scaled/translated map | Omitting sinc or using an untransformed wave/pupil vector exceeds.004e; identity companion still passes |
| n=(1,0), offset0, d_f=1, cell centre x=1.25 | Centre-only full-foreground predicate falsely admits a partly visible cell and must be rejected |
| n=(1,0), offset0, d_f=-3,d_b=1, centre x=-2 | Background-radius substitution falsely admits a partly visible background cell and must be rejected |
| Intermediate focus and nonconstant background | Unsigned relative defocus must change the independent shared-ray cell mean; common global sign reversal is an inert symmetry |

The two explicit geometric destroyers are realizable by the existing model:
depths(1,2), K4/inverse-focus1.25 gives d_f=1,d_b=3; K8/focus.625 gives
d_f=-3,d_b=1. Use unequal nonnegative layer constants to give the visibility
faults amplitude, and nonconstant radiance for the relative-sign control.
No noise or optical calibration is implied by these component records.

For exact tangent/ULP controls first use n=(1,0), offset1, d_f=1 and cell
centres x=2.5 and x=-.5. Both equalities are binary-representable. Change the
offset by -4,-2,-1,0,+1,+2,+4 `nextafter` steps; retain the exact rational
clearance and actual rounded heights at extreme cell/pupil points. Repeat
with a nonidentity power-of-two scale plus translated centre, for which an
exact tangent can still be constructed. Separately use a true nonzero rotation
and bracket its high-precision tangent by adjacent binary64 offsets; do not
call the rounded central value an exact equality. Mask rescaling and a
large cancelling coordinate representation are independent re-choices.

Analytic-enabled and disabled numerical methods must each meet the external
cell-value bar, even if their pointwise mask decisions differ at an ulp.
Any refusal remains a failed control. Do not use their pairwise agreement as
the reference or require bitwise equality across different algorithms. By
contrast, off/count/placebo observers and reordered independent-cell traversal
must produce identical value/indicator payloads for the same chosen algorithm;
count must show all intended branches and placebo must actually visit its hook.

## 4. Full-array admission remains a separate, complete test

After cost and component admission, render all five320×240 frames in primary,
angle-refined and cell-refined arms, with the unchanged M194e orders/depths,
mass guard, global leaf-error law and family inner-target policy. Resource
proposal:16m points/2400m angular nodes per frame,1800CPU/3600wall seconds per
five-frame arm,32MiB tracked arrays and32768 simultaneous node pairs. Native
failures retain partial arrays/last coordinate and no completed authority.
The resource caps can halt a run that passed nominal counting.

Compare **each complete frame/arm** with the independently refined reference:
max absolute error≤.004e and RMS≤.0008e. Report the same numbers separately on
numerical-fallback cells and a fixed boundary band, to expose an error diluted
by the large analytic population. Those diagnostics cannot replace the
all-pixel gates. All primary-versus-angle and primary-versus-cell max changes
must be≤.001e; reference refinement max≤.0005e. No successful subset or more
favorable arm can admit the population. Analytic cells need an explicit
branch-specific numerical-evidence field; a zero adaptive indicator is not
evidence of zero error.

Coverage/source/type/NaN faults, a changed radiance/phase and a nonperturbing
observer must reach these actual arrays and the eventual external commission.
Reference code must independently integrate the disc and square transfer,
rather than reuse the author's `j1` call. Cache that independent transfer only
after its own spatial/refinement controls pass. These requirements make wrong
analytic values falsifiable while retaining the legitimate cost reduction.

Only a genuine full-float commission can release later CFA/noise generation.
The larger producer needs a new schema and external source/array bindings;
M194e's old successful64×48 gate is lineage, not authority for new dimensions.
The subsequent flat/noisy36-output comparison needs its own preregistration,
including actual three-band domain, supported boundary mask, unchanged noise
seeds, both truth meanings, temporal variance and sparse adverse tails.

This followup used document and source reads only. It changes no frozen
producer, Rust source, old protocol, input or output. No geometry counter,
numeric control, image generation or quality measurement was run.
