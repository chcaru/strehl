# M194g independent geometry controls

2026-09-07. Prospective, before the independent control implementation and
before executing author geometry. Root release is commit `a59a1c47`. This
records literal choices from the committed mathematical review
`../m194f-production-bridge/next-larger-independent-math-review.md`, SHA256
`fa7fb6fbbe4c300da9ca58095c48e6f9de7bd21062d91f3d512a177c3704a7bc`.
No radiance integral, Bessel value, intended320x240 count, noise, CFA or
production image is authorized by these controls. Socrates separately owns
`independent-preflight-controls.py` and its counter/resource/source checks.

The consumer is the actual `geometry.py::ExactSelector` and the actual
`preflight.py::point_cuts` used by the preflight counter. Proposed API, agreed
with Curie before code: `ExactSelector(scene,frame,bit_limit=4096,budget=None)`
with `classify(xy)`, `exact_height(xy)`, `coefficients()` and
`unsupported_reason`; `point_cuts(bound,scene,frame,xy,budget)` returns one
record per point. The pinned loader supplies `.model`, `.render`, `.bindings`
and `.assert_unchanged()`. The adapter may follow final record key names but
must not change the fixtures, expectations or thresholds to obtain a pass.

## Literal selector population

Use constant positive dummy Fields, without evaluating radiance. Scene depths
are(1,2), normal n=(3,4), K8, inverse-focus5/8, hence dF=-3,dB=1. Native
centre is(7,11). The primary forward similarity is identity. Its exact
`n.q0=65`, H=3.5 and foreground radius R=15 give tangent offsets46.5
(foreground) and83.5(background). Equality is numerical fallback.

The second map is forward scale2, rotation0, centre(1,-2),
translation(.5,-.25). Its inverse at(7,11) is(3.75,4.625), n.q0=29.75,
H=1.75, R=7.5. Tangent offsets are20.5 and39.

For each map, each foreground/background tangent, mask multiplier1 or8,
and canonical-origin shift s=(0,0) or(2^20,-2^19), perturb the resulting
offset by exactly -4,-2,-1,0,+1,+2,+4 binary64 `nextafter` steps. Apply the
origin change as forward centre'=centre+s, translation'=translation-s,
offset'=offset+n.s, then multiply n and offset by the positive multiplier.
Perturb only after those transformations. The112 records are immutable:
foreground negative steps classify foreground; background positive steps
classify background; the opposite signs and equality classify numerical.
The transformed0-step cases remain exactly tangent in the continuous model.
Retain exact rational heights, support data and actual rounded extreme-ray
heights. The scalar integral cannot power one-ULP branch correctness; these
are explicit disposition controls, not pixel tolerance tests.

Add a rotated map: forward scale.8, rotation atan2(4,3), centre(2.25,-1.5),
translation(.375,-.625), native centre(7,11), same dF/dB and normal.
Using the independently reconstructed finite inverse coefficients, calculate
the two tangent offsets with100-decimal-digit arithmetic and bracket each
between adjacent binary64 values. Verify the bracket at200 digits. Test the
bracketing offsets and one `nextafter` outward value per side. The scalar
representation is the input; a rounded square root is not exact tangency.
The high-precision oracle uses square-root support at the four cell corners;
the author's integer squared predicate is not called to choose the answer.

Additional literal identity heights are -30,-18.5,-16,-12,0,12,16,18.5,30.
The ±12 and ±16 cells must be numerical; ±30 must be full background /
foreground. A wrong background-radius substitution makes ±12 falsely full;
omitting the square support makes ±16 falsely full. These analytic wrong-rule
expectations are instrument power, not a radiance result. Require actual
author classification at all these points and a genuinely changed classifier
call for any in-memory substitution whose implementation hook is exposed.
Preserve the distinction between an algebraic wrong-rule witness and a tested
mutation of the actual consuming helper; do not count the former as the latter.

Use19x13 cells, independent enumeration, with each of identity and the scale2
map. Their offsets are51 and22.75 respectively. Use inverse foci5/8,1,9/8
at K8, giving negative, zero and positive foreground defocus. Compare every
classification with the independent continuous support oracle, and require
foreground, background and numerical branches to occur in each map's combined
population. This is1482 small fixture cells, not the intended population.
Explicit `full`/`absent` mask states at(7,11) must select their named layer.

For a finite but unsupported arithmetic companion, use a low requested
`bit_limit=8` and the large cancelling centre from the cut fixture below.
Require numerical fallback plus a nonempty unsupported reason. The same
valid inputs with4096 bits must have the correctly predicted disposition.
This configurable-limit fault is not proof of arbitrary4096-bit allocation
safety; inspect the actual intermediate bounds separately. NaN/infinite
coordinates must refuse, never be reported as a valid full layer.

## Literal point-cut population and independent oracle

For identity geometry, n=(3,4), offset0, evaluate native points `(h/3,0)`
at h=(-15,-7.5,-15/8,-15/64,0,15/64,15/8,7.5,15). Use inverse foci5/8,
1,11/8 at K8: dF=-3,0,+3. Include half-plane, full and absent masks.
The81 records must come from actual `point_cuts`, without invoking radiance.
Record height, radius, signed alpha and every returned cut.

An independent geometric oracle solves
`radius*cos(theta-alpha)=-height/r` with `acos` for r=1,2^-1,...,2^-32
when the strict crossing exists. Add the projection-zero split and periodic
endpoints; do not reuse the author's `asin` construction. Compare the ordered
cuts within1e-12 radians and their counts on this nondegenerate literal set.
The full/absent or zero-radius cases have one interval. A zero-height
half-plane with nonzero radius has two. For the nonzero-radius half-plane,
|h|/R values1,.5,1/8,1/64 yield1,4,8,14 intervals respectively. The signs
must change the crossing positions, not their interval count. Omitted
negative-height cuts must be detectably wrong while positive companions pass.
Duplicate/omitted returned points must fail the independent point association.

The counter must consume the rounded height of `render_points`, not the
selector's exact height. Use scale1/rotation0, centre(2^42,0), translation0,
n=(3,4), offset0 and the dF=-3 frame. The native points `(2^-12,0)` and
`(-2^-12,0)` round to q0.x=0 in the literal subtract/add inverse sequence,
so their actual height is0. The exact precombined affine heights are
±3*2^-12. Require the actual helper's two cuts populations to match the
rounded path, and require the substituted rational-height ladder to differ.
This is a fidelity test of the nominal work counter, not an optical error.

The untouched call is the null. A separately recorded in-memory replacement
of the inverse operation by `M*z+(c-M*c-M*t)` can provide a live actual-helper
fault; restore the original callable immediately in a `finally` block.
The replacement has the same continuous affine model but different binary64
evaluation. Record both actual results and the restored-null equality.
No on-disk author source changes are permitted. All sources and bindings are
checked before/after, including during any temporary callable substitutions.

## Outcome and bounds

All required groups must execute; one refusal or failed assertion makes the
overall result `UNCOMMISSIONED_GEOMETRY`, with every completed check and
traceback retained. A failed adapter is `INSTRUMENT_INVALID`, not an author
mathematical failure. No passing subset grants cost or float authority.

Use one Python process, common numeric-library threads<=2, a fresh pycache
prefix, and record original interpreter arguments, executable/version,
library versions, environment, commands and timestamps. Bound this small
control batch at60 process-CPU/120 wall seconds and32MiB tracked owned arrays;
this is not RSS or a comparative performance measurement. Record complete
source/preregistration hashes, copy snapshots before execution, and reject
changed bindings afterward. No peer is paused or terminated. Do not execute
until Curie supplies the numerical/geometry source-freeze notice and exact
point-cut/budget record interface.
