# M194e independent model commission: prospective design

Status: **preregistration, no implementation or run**. The reviewer read the
root charter, the local prior audit and the author's proposed polar/radial
method before writing this file. The independent fixture, Cartesian integration
and analytic controls were chosen in coordination before either implementation.
The companion [author plan](implementation-plan.md) and
[author preregistration](implementation-preregister.md) were then read in full;
the API, five-frame scope and numerical/resource budget are aligned below.
The final emission-stage/child-schema clarification was read and accepted at
author plan SHA256 `dbac8c9ce4ff2d555bd49291de325e3f3494459b23b9cd83ec4ff180cf93f1a0`
and preregistration SHA256 `2196166ee9a36af8cc73e272e97d430d4478b2b8e05fc3af2215afc64de0e500`.
This file does not authorize a merge-quality comparison.

Prospective revision during design, before implementation: root selected the
more stringent full-fixture comparison budget `0.004` electron maximum and
`0.0008` electron RMS on the author's latest 64×48 five-focus fixture. Earlier
draft thresholds of1.0 electron maximum /0.2 electron RMS would not certify
that requirement and are superseded below, not described as measured failures.

## Scope and prior objections

The allocated task is to commission one geometric two-plane generator. It is
not to make M25 pass its real-occlusion bar, commission diffraction or camera
calibration, or choose a merge operator. The [prior audit](../m194d-band-admission/next-occlusion-audit.md)
records the mechanical searches, M25's existing implementation and failures,
M63's detector limitation, M87's corrected propagation/model distinction and
BUILD-BLEND's printed-but-disqualified rows. Root selected joint-pupil integration
because separately blurred alpha/background means omit a joint term on textured
backgrounds. Preserve the old model and its bars as a named legacy comparison.

An additional search was run:

```text
python experiments/ORCH-drift-check/prior_art.py joint pupil visibility sensor cell
```

Its highest matches were sensor/defect reports (BUILD-DEFECT, M92, M101, M46,
M50, M48c, M1, M22), not a commission of this visibility integrator. The earlier
targeted occlusion search and actual M25 source are the pertinent evidence; no
absence claim follows from this ranking. M92's real-noise averaging refusal is
retained and is outside this noiseless model commission.

The main independently chosen objections are:

- A shared pupil distribution is insufficient if the foreground and background
  are evaluated at different pupil samples. Equal marginal means can conceal
  either error direction. The sensor-cell sample must also be shared: averaging
  visibility and background separately across the cell loses the same relation
  even at zero aperture.
- Under a symmetric circular pupil, reversing **both** signed defocus
  displacements is a change of pupil coordinates. No image test can reject
  that global convention. Taking each magnitude instead changes the relative
  layer displacement at an intermediate focus and is independently testable.
- A similarity must transform the native cell and native pupil displacement,
  not just the chief ray. Identity-only evidence cannot commission this API.
- Refinement on the same mask phase may alias the same edge. Test noncentral,
  tilted and shifted edges, and integrate cell area separately from pupil area.
- A passed two-ray function does not prove a separate analytic quadrature
  implementation. A continuous affine-radiance oracle must exercise the actual
  `render_point` / `render_cell` path as well.

## Equation and API to bind

The agreed prospective equation is

```text
d_l = K (f - 1/z_l)
q_l = T(x + delta + d_l u)
I(x) = integral_delta integral_u
       [ A(q_F) F(q_F) + (1-A(q_F)) B(q_B) ] dmu(u) ddelta
```

`x` is a native pixel center; `delta` spans its native unit square; `u` is a
uniform unit-disc pupil sample; `T` is one declared native-to-canonical
similarity; `f` is inverse focus distance, `z_F < z_B` are positive model depths;
`K` has native-pixel times depth units. Layers have opaque surface radiance in
expected electrons and the foreground mask is binary. Integrals are normalized
by pupil area and native cell area. `T` maps pupil displacement as well as cell
position; there is no additional intensity Jacobian in this radiance-normalized
model. This is the declared mathematical model, not a calibration of a lens.

The agreed author functions are `evaluate_rays(scene, frame, xy, pupil_uv)`,
`render_point(scene, frame, xy, integrator)` and
`render_cell(scene, frame, xy, integrator)`, with the last two returning scalar
electrons plus numerical-error metadata. `render_frame` retains uncommissioned
scalar float output; `emit_cfa_bundle` consumes externally commissioned float
receipts. All three evaluation semantics must remain inspectable. The
author's complete generated frame must consume the commissioned cell function
or a source-bound equivalent whose agreement is checked. Diagnostic-only code
cannot stand in for the emitted-frame path.

For a nonidentity test use `T(q)=c + 1.037 R(0.071)(q-c) + (0.31,-0.27)`,
`c=(37.23,24.61)`. Its inverse is calculated independently. No geometry fitting,
source-derived registration, gain fitting, image registration or RAW access.
No breathing claim is made for the initial identity series. If a later full
breathing track is added it needs the measured curvature requirement; this
single coordinate control does not replace it.

The author serializes the **forward** canonical-to-native similarity, whereas
T above is native-to-canonical. Therefore the independently chosen control is
encoded with `a=1/1.037`, `theta=-.071` and
`t=-a*R(theta)*(.31,-.27)`, about the same c. Independent reference coordinates
use the displayed T matrix directly, without calling the author's inverse
helper. This prevents an accidental convention agreement in the control.

## Independently chosen fixture and cheap exact oracles

Use a distinct 83×61 native extent, foreground depth `z_F=1.25`, background
depth `z_B=2.5`, `K=11`, inverse focus `f=.53`, and foreground half-plane

```text
n=(12,5)/13, c=(37.23,24.61), A(q)=1[n dot (q-c) >= 0].
```

The between-layer focus gives `d_F=-2.97`, `d_B=1.43` native pixels. This is
chosen to express relative-sign failure rather than reproduce the author's
latest 64×48, depths1/2, K12 fixture. Unclipped electron values are compared before
sensor quantization. All tolerances below are engineering error budgets, not
estimates fitted to the intended output.

**R1: finite-ray order and shared-pupil control.** At the boundary use two
equally weighted pupils `u=-n,+n`, constant foreground30 and affine background
whose two values are10 and20 in that order. Since `d_F<0`, the first ray sees
foreground and the second sees background: exact mean25. Reverse only the
background slope: exact mean20. Separate marginal compositing gives22.5 in
both cases. Assert each individual ray as well as its mean within `1e-10`
electrons. Use actual `evaluate_rays`; label it discrete model evidence only.
Unchanged input is the placebo. Independently pairing the two background
samples in reverse is the destroyer, with an analytically nonzero effect.
This affine background is a local component field evaluated only at this
point's pupil footprint, where it is bounded10..20; it is not emitted across
an arbitrary photographic scene.

**R2: continuous-disc shared-pupil and relative-sign oracle.** At `q=c`,
identity T, let `F=12000` and `B(q)=10000+800 n dot(q-c)`. The exact point
integral is

```text
11000 + 800*d_B*2/(3*pi) electrons.
```

The last term follows by integrating `t*2*sqrt(1-t*t)/pi` over the visible
background half of the disc. It is nonzero without texture fitting or a
numerical pupil rule. Separating means gives11000; replacing `d_F` with
`abs(d_F)` changes the sign of the last term. Reversing both d values together
is the pupil substitution `u -> -u`: test the corresponding sample permutation
in `evaluate_rays` and retain the integral identity as DERIVED. Do not send
illegal negative K to the public API merely to express that coordinate gauge.
This tests the actual continuous integrator,
not only `evaluate_rays`. Its absolute numerical error budget is `0.02`
electrons. Test background-slope zero as a powered null and slope reversal as
an independent change of error direction.
The affine field is evaluated locally, where R2's background footprint has
radiance8856..11144. R5's transformed point/cell footprints are bounded
analytically before evaluation and must remain nonnegative. These affine
component laws are not full-frame emitted radiance fields.

**R3: pupil area and focused limits.** Constant layers12000/9000 are tested at
signed foreground offsets corresponding to disc cuts `h=-.73,-.21,.34,.81`.
For a unit disc the fraction with `t>=h` is
`(acos(h)-h*sqrt(1-h*h))/pi`. Choose cell centers from the desired h and the
declared signed d, not from an observed image. Compare point integrals within
`0.02` electrons. Include absent foreground, full foreground and equal
constant layers; change invisible-layer radiance strongly and require
invariance. A pupil-center-only destroyer must fail at the partial cuts.
At `f=1/z_F` the foreground position is pupil-invariant; at `f=1/z_B` the
background position is pupil-invariant. Neither statement makes the other
layer sharp or fully visible.

**R4: cell integration and coordinate convention.** Set K0 and constant
foreground/background12000/9000. Compute exact foreground coverage by clipping
the native unit square with the pulled-back half-plane and applying polygon
area. Rechoose subpixel offsets so coverage is fractional, including a
noncentral tilted cut. This is independent of author pupil/cell quadrature.
Require cell error at most `0.02` electrons; a center-point-only cell must fail
by at least10 electrons on one declared case. Apply the nonidentity T above
and compare to the independently pulled-back polygon. This exposes wrong cell
footprint and translation conventions without a learned alignment.

A second aperture-zero cell has local square coordinates
`[-.5,.5]^2`, foreground `A=1[x>=.1]`, F30 and B=`10+4x`. The exact cell
integral is17.52, from `30*.4 + integral(-.5,.1)(10+4x) dx`; separate cell
means give18. Reversing the background slope gives18.48, while separate means
remain18. Require error at most `0.02` electrons. This powers same-cell-sample
visibility independently of the pupil covariance. For transformed/tilted
variants integrate affine radiance with polygon area and first moments;
do not use a product of mean opacity and mean background.
This local cell's background is bounded8..12. Evaluate the law only on its
declared cell footprint, not as an unbounded full-frame stimulus.

**R5: nonidentity displacement.** Use the R2 affine field and nonidentity T.
Evaluate the disc in a native pupil basis and derive foreground cut and
background affine coefficients by applying T independently. Compare point
values within `0.02` electrons and at least one boundary cell with the
independent numerical method below. The destroyer `T(x+delta)+d_l*u`, which
leaves native displacement outside T, must disagree; if the chosen scene is
accidentally inert the gauge claim is unpowered and is withheld, not rescued
by a post-hoc angle/scale sweep.
Require the wrong mapping to exceed `0.02` electron on at least one of the
declared R5 point/cell cases; merely different floating-point bits are not power.

## Independent numerical method and convergence power

The author proposes polar pupil coordinates, analytic radial integration and
angular splitting. The independent implementation will use **Cartesian pupil
chords**. Rotate the native pupil basis to the pulled-back mask normal; at each
normal coordinate t the tangential coordinate spans
`[-sqrt(1-t*t),+sqrt(1-t*t)]`. Split the t integral at the exact foreground
crossing. Integrate affine/sinusoidal radiance along tangential chords, then
use adaptive quadrature in t. This does not call the author's radial primitive,
polar nodes, mask split routine, pupil integral or error estimator.

Cell integration uses the native square directly, with independent adaptive
integration and explicit boundary/transition breakpoints. The planned full-cell
reference reduces this further: at fixed pupil-normal coordinate t, foreground
visibility clips the native unit square by a half-plane. Compute the visible
polygon independently, then integrate a constant by area, an affine field by
area/first moments, and a Fourier component by a boundary integral. For nonzero
native frequency vector k, the latter follows from
`div[k*exp(i*k dot delta)/(i*|k|^2)] = exp(i*k dot delta)`;
each polygon-edge exponential integral has a stable sinc expression. Zero
frequency uses area directly. Integrate the complementary cell region for the
background, with its own signed pupil phase. The remaining pupil-normal
integral uses the analytic tangential chord factor and adaptive quadrature.
This leaves one numerical dimension while retaining the same cell/pupil sample
in visibility. It does not call the author's polar primitives or cell polygons.

Commission the polygon Fourier integral against an independent direct
unit-square integral on no-mask sinusoids and the R4 area/first-moment limits.
The R4 same-cell covariance control must still fail a product-of-means
destroyer. A direct nested Cartesian cell/chord evaluation on the fixed small
analytic cases is a cross-check on the reduction, not a substitute for the
required whole-fixture comparison. The analytic cell reduction has no sampling
resolution to refine; record its separate polygon/oracle and direct-cell
cross-checks, not an invented cell-resolution number. Refine the remaining
pupil quadrature and record its error report plus the actual refinement
difference. Independently read the author's separate pupil/cell refinement
arms. An error estimate is not a proof of its own accuracy. R2–R4 and
wrong-operation controls calibrate the paths independently.
Use float64 for commissioning calculations; do not quantize away a discrepancy.

For a textured control use

```text
F(q)=12000+900*cos(2*pi*(.073*q.x+.019*q.y)+.41)
B(q)=10000+700*cos(2*pi*(-.031*q.x+.087*q.y)+1.13)
```

with the independent geometry above. Fix native sample centers before runs:
points/cells on the line at y=`6,15,24,35,46,55`, each displaced by
normal distances `-4.1,-1.3,-.17,.29,1.7,4.7` (36 continuous centers, retained
even when they are not integer pixels). Evaluate identity and the declared
nonidentity T, and also the actual integer cells nearest the six central
crossings. A fixed phase shift of the mask by `.137` native pixels along its
normal supplies a second edge phase. No random search or favorable crop choice.

The engineering comparison budget is `0.0008` electron RMS and `0.004` electron
maximum across the fixed textured samples, corresponding to `0.0002` and
`0.001` raw DN at declared gain `.25 DN/e`. The same comparison must cover
**every pixel of all five author 64×48 noiseless frames**, with the declared
edge band reported separately and subject to the same RMS and maximum budgets.
The main scene has foreground depth1, background depth2, K12 and inverse-focus
values `[.5,.625,.75,.875,1]`; its precise two-wave fields and
`x >= 32+.15*(y-24)` mask are bound by the author plan. The edge band includes
native centers within8 pixels of that line. The re-chosen samples do not substitute for
that whole-fixture comparison. Tighten the independent numerical request by a
factor16 once, with a required maximum refinement change at most `0.0005`
electron on the full compared domain. The initial absolute target is
`0.000125` electron per final point/cell, refined to `0.0000078125` electron;
allocate that target across the exact normal-coordinate intervals so their
absolute requests sum to the final target. Use zero relative tolerance and
at most128 adaptive subdivisions per interval. Exceeding this depth/work
boundary is a refusal, not a larger implicit tolerance.

The full-fixture reference has **only normal-quadrature refinement**: its cell
integral is analytic. Cell evidence is the polygon area/moment/Fourier oracle,
small direct nested Cartesian cross-check and boundary-phase controls above.
Only the author's numerical cell integrator has the separate registered
cell-resolution refinement arm. No inert cell-tolerance arm will be reported
for the analytic reduction. If precision or the frozen computational budget fails, retain
the failure and withhold the dependent claim; do not reduce it to a favorable
subset or widen the tolerance.

These are float64 **generator arithmetic** requirements. They are not a bound
on product f32 arithmetic, TIFF error, or nonlinear merge sensitivity. The
looser0.02-electron analytic R2–R5 controls are diagnostic power checks only;
their pass cannot certify the stringent full-fixture numerical requirement.

Independent work is capped at30,000,000 pupil-normal integrand evaluations,
600 process-CPU seconds and1200 wall seconds per complete five-frame reference
arm, checked within bounded evaluation batches. One integrand evaluation
computes at most two visible/complementary polygon-field integrals, with at
most two cosine terms per field; count actual calls rather than borrowing the
author's unrelated angular-node counter. The same ceilings bound the separate
analytic/re-chosen-control batch. Each primary/refined arm keeps its own
counts and terminal status, so one cannot silently borrow another arm's budget.
Use one worker and set common numeric-library thread limits to at most2.
Retain at most the current author scalar array, current reference/refined arrays
and comparison scratch; explicitly counted ndarray storage is capped at32MiB.
Do not allocate the five-frame volume. Own-script budget exhaustion records
an incomplete numerical commission and returns nonzero; it never terminates
or pauses a peer. No runtime/RSS/performance result is implied by these limits.

A deliberately coarse pupil-center rule and a one-sample sensor-cell rule
must each fail at least one appropriate R2/R3 or R4 case. A separate-means
control must fail R2; unsigned relative defocus must fail R2; pupil-decorrelation
must fail R1. Thus numerical agreement cannot all be a DC identity. No claim
that every coarse angular grid must fail: aliasing is exactly the concern.

## Emitted data, observers and refusal boundaries

After the model tests pass, inspect all five actual noiseless CFA files through
the source-bound writer: 64×48 tightly packed native RGGB, active origin0,
little-endian u16, scalar factors R=.75/G=1/B=.6, black512, gain.25 DN/e,
white15360 and ties-to-even rounding. No WB or shot/read noise is applied.
Compare every author's scalar expected-electron value against the independently
commissioned reference, then independently form each expected CFA value and
quantize the actual bound scalar values. Test all four parities, including
both greens, across every file. Changing phase, one factor, black offset or
gain supplies explicit conversion destroyers; an unchanged conversion is the
placebo. Reject nonfinite/out-of-rail values rather than clipping away failure.
Near a rounding tie, numerical error can change an integer code; report the
distance to the tie and do not demand byte equality to an uncertain analytic
reference. The author's on/off/placebo observer runs themselves must be
byte-identical because those use exactly the same evaluation and rounding.

The new top-level manifest is `m194e-joint-pupil-v1`, with keys schema, status,
producer, sensor, scene, ray_model, numerical_contract and frames. The exact
FileRef, ArrayRef, frame, scene and sensor children in the bound author plan
are accepted: shape `[48,64]`, dtype `<f8`/`<u2`, nonnegative byte length,
relative nontraversing paths, lowercase64-hex hashes, ordered indices0..4 and
the exact fixed scene/sensor constants. Require the paired post-emission
`expected_cfa`/`cfa` fields together. Reject bool-as-integer, duplicate/unknown keys, malformed types,
nonfinite values and false order/dimensions/length/hash. Mutate source,
float-file and external commission bindings independently after retaining a
valid no-op copy. `m194e-float-frame-v1` starts uncommissioned;
`m194e-float-commission-v1` PASS permits emission with manifest status
`float-commissioned-cfa-unverified`; `m194e-cfa-commission-v1` then checks the
actual emitted data. Actual CFA and final-manifest checks must not be claimed
before those files exist. This is a stage distinction, not a circular final certificate.
No real noise draw or profile calibration
claim belongs to these independent controls. A failed shared-pupil, cell or
numeric check cannot yield a successful commissioned-manifest status. Preserve
failed receipts and return refusal. Do not modify historical M25/M194b files,
production Rust, the M194d operator, a benchmark score or its acceptance bar.

Release condition: root reviews author and independent preregistrations and
commits them before implementation. If a later API correction is necessary,
record an explicit prospective amendment and preserve the earlier failure;
do not count a corrected harness result as independent proof of the old one.
