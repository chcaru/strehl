# Independent review of the larger shared-pupil proposal

2026-09-07. **DERIVED mathematics / ARGUED design conditions; no new numerical
or quality run.** This reviews `next-larger-implementation.md` at SHA256
`987d7923577ffea261981b097190fa1886d03069d05b47ad10a17652b6e1bb61`
and the subsequent `../m194g-larger-pupil/preregister.md` draft at
`3341a470384bce735be53a9594fbdbd95bd1f4d989d1ebceff04113be58ca550`.
The latter narrows the first milestone to one textured optical scene and
releases geometry-only work first. Its separation of cost, float authority,
noise emission and production comparison is appropriate. The earlier proposed
flat/noise/36-TIFF population is onward planning, not M194g authority.

The full-layer reduction is valid for the declared continuous geometric model.
It is a useful bounded next step, conditional on the selector, independent
spatial oracle and actual cost controls below. The mathematics is not a reason
to skip the complete larger-image comparison. No prior result establishes
that its new extent meets the numerical or resource bars.

This review changes no frozen M194e/M194f source, result, tolerance or product
default. It does not commission physical optics, diffraction or capture transfer.

## Prior work read by content

Mechanical search actually run from the repository root:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe experiments/ORCH-drift-check/prior_art.py joint pupil full layer analytic transfer
```

The results included M194e, V-HEADTOHEAD2, M194f, M164-transfer-veto,
M92-null-averaging and M-CAND2. Ranking is not evidence that a report answers
this question, and this search establishes no absence claim. Relevant report,
implementation and decision-record content was then read:

- [M25](../../docs/research/M25-simulator-measured.md): its optical gate was
  blind to deleting diffraction; the corrected real-occlusion gate retained
  wrong-sign enrichment. Its already implemented disc transfer does not
  commission either physical optics or a new numerical tolerance.
- [BUILD-BLEND](../../docs/research/BUILD-BLEND.md), synthetic scene section:
  failed scene commissioning and a depth-oracle that is not a universal
  attainable floor. The report disqualifies the edge results; the earlier
  [source audit](../m194d-band-admission/next-occlusion-audit.md) records that
  the executable prints those rows before its warning and returns success.
  Preserve that distinction and the later correction of the claim that M63
  refuted all two-layer models.
- [M194d](../../docs/research/M194d-band-admission.md): lower flat temporal
  variance coexists with a small plane-detail cost and sparse worsening.
  A one-plane plant cannot adjudicate depth-boundary dilution. Positive band
  weights do not calibrate noise probabilities or establish better detail.
- [M194e](../../docs/research/M194e-joint-pupil.md), the frozen `model.py`,
  `render.py`, `independent-model.py`, `independent-reference.py` and
  `independent-design.md`: the complete model was commissioned, after retained
  angular, tangent-cell, local-allocation and coupled-budget failures. The
  final full comparison, rather than the successful partial images, admitted
  the model. Neither an exact-zero analytic indicator nor tighter requests
  automatically measure an error reduction.
- [Larger-fixture notes](../m194e-joint-pupil/next-quality-fixture-notes.md),
  the prior occlusion audit and relevant SYNTHESIS M25/model limitations:
  shared pupil **and cell** samples must remain coupled at a boundary. An
  analytic full-layer branch is not permission to separately blur and
  composite partially visible layers.

The order-one Poisson integral was also checked in the primary mathematical
reference [NIST DLMF 10.9.4](https://dlmf.nist.gov/10.9.E4). No external source
code was read. The derivation and chosen numerical oracle below are explicit;
calling the same Bessel routine twice will not serve as verification.

## Independent transfer derivation

Write the inverse map directly as `q=M*z+b`. The stored wave frequency is in
**cycles per canonical-coordinate pixel**, since `Field.evaluate` evaluates
that frequency against canonical `q`. Thus `omega=2*pi*frequency` is canonical
radians per pixel and `k=M^T*omega` is native radians per pixel. Correct the
implementation note's parenthesis saying cycles/native-pixel; make the same
units explicit in M194g, whose current wording is merely unspecified.

For one fully visible layer, a native cell displacement delta and pupil u give

```text
q = q0 + M*delta + d*M*u
exp(i*omega.q) = exp(i*omega.q0) exp(i*k.delta) exp(i*d*k.u).
```

The two normalized integrals factor because their supports are independent
and visibility is constant on their product. Integrating each native-square
coordinate from -.5 to .5 gives `sinc(kx/2)*sinc(ky/2)`. The unit-disc integral
is real: its imaginary part cancels under `u -> -u`. Rotate only this disc
integral to align k with its horizontal coordinate. With `a=abs(d)*norm(k)`,

```text
D(a) = (4/pi) integral_0^1 sqrt(1-t^2)*cos(a*t) dt
     = (4/pi) integral_0^(pi/2) cos(theta)^2*cos(a*sin(theta)) dtheta
     = 2*J1(a)/a, with D(0)=1.
```

The second expression is a smooth spatial integral suitable for an independent
reference; it is not the author's polar visibility/radial primitive. The first
also derives the series from disc moments:

```text
D(a) = sum_m>=0 (-1)^m*(a^2/4)^m / (m!*(m+1)!).
```

For rational test arguments, a finite exact-rational sum plus a descending
alternating-tail bound can certify a sign or near-zero limit independently
of floating Bessel evaluation. Do not describe that auxiliary sign enclosure
as independent physical evidence; it is mathematics of this same disc.

DC remains unchanged. The first moments of delta and u vanish, so a full-layer
affine field averages to its value at q0. There is no intensity Jacobian:
the average is with respect to normalized **native** cell and pupil measures.
Negative D is a phase reversal of a wave, not negative radiance; a sufficiently
positive DC keeps the evaluated field physical within this model. Absolute
value, zero-clamping, or replacing the native unit cell by a canonical unit
cell changes the integral.

The even D cannot detect global defocus sign, nor can its magnitude distinguish
M from M^T when M is a similarity: both give the same frequency norm. A test
of that radial magnitude alone is unpowered for rotation handedness. The
native-square factor and chief-ray phase are needed to detect that choice.

## Conservative visibility, and what exact arithmetic proves

At the foreground intersection the mask height is

```text
h + n'.delta + dF*n'.u,  n'=M^T*n.
```

The square's support function is `H=(abs(n'x)+abs(n'y))/2`; the disc's is
`R=abs(dF)*norm(n')`. Their extrema add, so the height range is exactly
`[h-H-R, h+H+R]` for the continuous map. This proves the proposed strict
foreground/background squared tests. The background's own defocus is
irrelevant to **visibility**; it enters only its visible radiance integral.
Mask states `full` and `absent` must remain explicit reductions, not be inferred
from an unrelated field's values. Zero defocus still requires the entire
sensor cell, rather than its centre, to be on one side.

M194g's exact-rational clause addresses an important ambiguity: form h from
the stored finite M, centre, translation, n and offset without rounding a
combined affine intercept first. Bound **every** intermediate, including
products/squares and common-denominator scaling, before allocating unbounded
integers. An over-limit value selects numerical fallback; it must not silently
use an approximate sign. Unsupported finite coefficients and invalid/nonfinite
model values have different dispositions. Preserve the original model's
validation on fallback.

Exact tests certify this continuous affine map, not every separately rounded
`Similarity.inverse` / `native_mask` / dot-product evaluation. The draft now
states that distinction correctly. Do not add a post-hoc floating exclusion
zone, or claim pointwise equivalence from a passing integrated error. Under
the fixed errors, one-ULP tangency cases may pass even when the selector is
wrong; therefore require both an independently predicted **branch disposition**
and a cell-value comparison. These are different instruments.

### Re-chosen selector fixtures

Freeze these before the geometry-only implementation. They require no radiance
to check classification. Use depths(1,2), inverse-focus5/8, K8, giving
`dF=-3,dB=1`; identity M, native centre(7,11), mask normal(3,4).
Here `n.z=65`, `H=3.5`, `R=15`. Foreground tangency has offset46.5;
background tangency has offset83.5. Both equalities must use numerical fallback.
Apply the registered offset-nextafter steps `-4,-2,-1,0,+1,+2,+4`. The strict
foreground side is smaller offset; the strict background side is larger offset.

Repeat with a power-of-two nonidentity map: forward scale2, rotation0,
centre(1,-2), translation(.5,-.25), same native centre and normal. Then
`q0=(3.75,4.625)`, `n.q0=29.75`, `H=1.75`, `R=7.5`; the tangent offsets are
20.5 and39. This is a real changed cell footprint with exactly representable
coefficients. A rotation case must bracket the independently computed tangent
with the adjacent binary64 offsets rather than call a rounded square root
exact. Use a separate phase/rotation test for transpose power below.

Also use mask scaling by8, and a canonical origin shift `(2^20,-2^19)` with
the corresponding centre/translation/offset representation. Bind the
continuous map and separately retain all actual rounded extreme-ray heights.
Power-of-two scaling can supply an exact algebraic gauge. Arbitrary scaling
or large translated representations need not preserve each rounded comparison;
record that effect without moving the boundary. Negative-normal changes are
not a positive mask-rescaling placebo.

Two later radiance controls make the visibility mistake observable, beyond
the ULP cases. In the identity fixture use constant F15000e/B9000e:

- Set h=12 and h=-12 (offset53 and77). The wrong background radius is5,
  so its false full-layer test admits these cells; the correct support reaches
 18.5 and they are partly occluded. Require the wrong branch's cell value to
  miss independent truth by more than.004e.
- Set h=16 and h=-16 (offset49 and81). The missing-square-support predicate
  falsely admits them since16>15, although16<18.5. Require the same live
  value discrepancy.

The independent oracle must report the actual excluded/visible mass and
contrast-weighted discrepancy. A different bit alone is not failure power.
Equal F/B12000 is the companion null: classification still has to be right,
but its scalar output cannot reveal visibility error. This distinction is
deliberate, not a waived numeric control.

## Independent spatial reference and required power

Use a new, separately source-bound adapter around the existing independent
Cartesian/chord and clipped-polygon equations. Do not import the author's
selector, inverse helper, Bessel value, polar primitives or error estimator.
The input scene records themselves may be shared and must be bound exactly.

For full-layer reference interiors use independent spatial quadrature of D
above and direct one-dimensional square integrals. The tuples may be cached
by the complete field/frame/frequency/target key. Commission that cache against
the unchanged general Cartesian/polygon reference on re-chosen full-layer
points/cells, including nonzero phase and negative transfer. A wrong cache key,
changed phase/field or layer swap must be detected on actual consuming paths.
There are at most20 transfer tuples per five-frame primary/refined reference
arm, not20 independent new measurements at every pixel.

For the reference's shortcut classifier, deliberately use a more conservative
box bound rather than reproduce the author's tight circle test. One viable
fixed choice is

```text
B = (abs(dF)+1.5)*(abs(n'x)+abs(n'y)); full only if h>B or h<-B.
```

The pupil disc lies within the unit box; the .5 term covers the native cell
and the added1 supplies a declared guard. Exact finite-coefficient arithmetic
or outward intervals can establish this looser bound. All other cells use
the independent clipped-cell/chord integral. This keeps an independently
defined wider transition strip and detects an overly permissive author branch.
It does not change the mathematical scene or author selector. The guard is
chosen here, before discrepancy measurements, and is never used to omit pixels.

Use absolute full-value targets .000125e and .0000078125e for the two reference
arms, zero relative tolerance and the existing128-subdivision per interval
limit. Allocate the target across wave terms using their absolute amplitudes
and across spatial factors; do not request .000125 per dimensionless transfer
then multiply by3200. For example, reserve half the full-value request for
the sum of cached transfer uncertainties and half for finite evaluation /
remaining quadrature accounting. With |D|,|sinc|<=1, propagate product errors
including the small cross term. Record indicators as estimates; refinement
and controls remain decisive. Analytic cell integration has no numerical
cell-resolution setting to refine.

Concrete additional choices for the later radiance preregistration:

1. **Transfer signs and normalization.** Replace the author's arguments5/6.4
   with4.75/6.25, and8.75 as a positive-lobe companion. Use a10000e DC,
   1000e cosine at phase0, direction(3/5,4/5), and d=2 with frequency chosen
   so `abs(d)*norm(k)` equals the specified argument. Exact-rational moment
   enclosures establish the intended lobe signs; independent spatial quadrature
   supplies amplitudes. Abs/clamp, missing pupil normalization and missing
   cell factor must each exceed.004e in a named component. Include exact zero
   and arguments2^-20,2^-8,1/8. Tiny arguments mainly test finiteness/stability;
   do not call their sub-tolerance difference from1 power against an always1
   approximation. The1/8 case supplies that power.
2. **Transpose and cell footprint.** Use a full-mask, zero-defocus wave with
   omega=(2.4,.8), amplitude1000e, DC10000e, phase chosen for zero centre phase.
   A directly specified independent inverse matrix
   `M=((.75,1),(-1,.75))` gives native k=(1,3); the transpose error gives
   (2.6,-1.8). Their disc factors are both1 and their square factors differ.
   If the public API only accepts scale/rotation, encode forward scale.8 and
   rotation atan2(4,3), and use its actual finite coefficients as data for
   the continuous-model comparison; do not pretend trigonometric rounding
   produces the exact dyadic matrix. Require wrong-vector error>.004e,
   while both correct methods pass. A second nonzero-centre/translation and
   nonzero-phase case powers the chief-ray convention separately. The exact
   lower-level matrix case can remain a reference component without inventing
   an unsupported public constructor.
3. **Relative defocus and joint visibility.** For the earlier dF=-3/dB=1
   frame, take unit n=(3/5,4/5), a point on the boundary, F12000 and local
   B=`10000+600*n.(q-q0)`. The continuous point value is
   `11000+400/pi`; taking abs(dF) changes it to `11000-400/pi`.
   A global sign reversal remains an inert pupil gauge. Restrict this local
   affine field to its evaluated footprint, where B is9400..10600e. This
   point control does not replace cell evidence. For separate cell power at
   K0, square[-.5,.5]^2, A=`1[x>=-.2]`, F16000 and B=`9000+800*x`,
   the exact mean is13816e; separate cell means give13900e. Those84e cannot
   be removed by the full-layer shortcut because the cell is partial.
4. **Tangent and branch equivalence.** Run every re-chosen tangent/ULP case
   through both enabled and disabled methods against the independent whole
   cell integral. Keep the historical M194e(30,4),(31,7) and(4,0) failures as
   separately named regression components on their original scenes; moving
   the main edge does not move those recorded facts. Compare whole cells;
   the previously refused tiny-triangle reference is not resurrected as an
   independent leaf-truth certificate.

These choices are prospective and unexecuted. Before code, fix the complete
component lists and exact encoding in the later release; do not tune phase,
threshold or coordinates after a destroyer is inert. A surviving destroyer
withholds the affected claim and is retained, alongside its valid companion.

## Precision, cost and execution conditions

Keep the draft's complete1152000 author values: five320x240 frames in each
of three arms. Every frame and its fixed `|x-.15*y-142|<=8` mask must pass
max.004e and RMS.0008e against the independently refined reference. This mask
uses the stated algebraic height; do not silently call it an8-native-pixel
Euclidean-distance band. Report numerical-fallback populations separately.
Retain max.001e author arm-refinement and max.0005e independent refinement.
All are float64 generator limits, not guarantees for later f32 merge/TIFF error.

Analytic interior values may be identical across author refinement arms by
construction. That is not independent corroboration. The separate spatial
controls and complete external comparison commission them; actual numerical
fallback rows must retain consumed orders, both point targets, weighted pupil
terms, global frontier law, depth/mass barriers and real branch occurrence.
No shared transient cache may replace a missing frame or refinement arm.

The proposed9600 numerical-cell bound is consistent with the support width;
it is at most2.5% of384000 cells per arm, **not** a2.5% runtime estimate.
The reference's deliberately larger box/guard strip has conservative per-row
integer bounds18,14,11,7,4, hence at most12960 numerical cells per reference
arm. This is an arithmetic bound on branch candidates, not integrand calls.
The previous independent64x48 record used6337002/7125594 normal integrand
evaluations and46.046875/52.453125 process-CPU seconds for primary/refined.
Those saved observations establish the old run only. They do not predict a
new boundary phase's adaptive depth or establish throughput on the current host.

Recommend retaining an independent ceiling of30000000 actual normal-integrand
evaluations,600 process-CPU seconds and1200 wall seconds per complete five-frame
reference arm, one worker and numerical-library thread limits<=2. Count cached
transfer quadrature calls as well; check elapsed time during analytic-only
rows too. Give the separate component-control batch its own same ceiling.
Freeze these limits before launch, or prospectively review different explicit
limits before generating references. A cap failure means uncommissioned,
not a passing subset. This is plausibly bounded with spatial transfer caching;
there is no measured promise that it will finish within those caps.

The author geometry-only preflight is necessary. Its60CPU/120wall-second cap
may itself be demanding because nominal low/high point traversal is substantial;
it is a real fail-capable condition, not an asserted completion estimate.
Use one clock across all15 frame/arm cases, explicit checks around the reused
geometry helpers and analytic-only enumeration, and exact owned-array accounting.
The old helpers do not automatically charge a new wrapper's wall/storage work.
Check the distinct per-frame8m point /1.2b angular-node stop rules on actual
counts. Half-cap nominal headroom does not bound adaptive work. Preserve
all failures; no radiance/Bessel/noise/product call belongs to this first run.

For independent geometry coverage, use a small non-square extent with integer
coordinate bitsets or a separately enumerated coordinate set, not only the
author's traversal hash. Exercise omitted and duplicate cells, omitted low
batch, omitted negative-height cuts and changed frame/order records on actual
counter paths. Valid no-op companions must pass. Unsupported-rational fallback
must be visited, and an all-analytic small fixture must still trip injected
time/storage limits. Socrates's independent source/schema/counter review is
complementary to these mathematical controls.

At320x240 one float64 array is614400bytes; two current arrays are1228800bytes.
A32MiB tracked-array ceiling permits complete-frame comparison scratch without
five-frame volumes. It is not measured RSS or an exact allocator peak. Keep
current-frame arrays, stream payloads and count all owned scratch; transfer
tables may be bounded independently. Repeated noise later consumes the admitted
expected arrays and must not rerun optical integration.

Observer off/count/placebo and traversal permutations must keep the actual
scalar and per-pixel numerical payloads byte-identical for the same algorithm.
Mode-dependent counts, observer witnesses and ordered traversal digests are
expected to differ and are not those invariant payloads. Hash actual files
and bind source before/after, imports, original interpreter arguments, fresh
cache prefix and numerical versions. Array/receipt/source mutations must be
rejected by a separately commissioned consumer before any float authority.

## Release disposition

The M194g geometry-only design is acceptable after the canonical-frequency
wording, literal selector fixtures and wrapper-wide counter/time/storage
semantics are made explicit in its committed dependencies. Later radiance
release still needs concrete source-bound independent oracle/control records,
the independent resource ceiling and admitted cost results. The completed
M194e/M194f scopes stay unchanged. No optical array, noise draw, CFA file,
quality result, speed result or SOTA claim was produced by this review.
