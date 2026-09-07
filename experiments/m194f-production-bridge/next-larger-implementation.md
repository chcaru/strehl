# Proposed larger joint-pupil fixture

2026-09-07, implementation audit. **Design only; no new renderer, noise draw,
product build or quality population was run for this proposal.** M194f's bridge
checks remain a separate task. This is a candidate for a new allocation and
prospective registration after bridge admission, not an extension of its claim.

## Smallest useful change

Use the frozen M194e `model.py` records and ray semantics through a separately
versioned experiment module. Import the pinned model/render sources under
isolated module names in a fresh process, or copy them into a new explicitly
hashed numerical fork; do not edit those sources or pass new data under an
M194e/M194b schema. Prefer a wrapper with one added full-layer cell branch and
the frozen `render_cell` as its fallback. No production arithmetic changes.

The initial quality population should use **identity placements**, five original
indices0..4 and reference2. This commissions three-band boundary/noise behavior
without silently importing a nonidentity filter-support guarantee. Nonidentity
similarities are mandatory component controls of the analytic method below,
but an intended curved placement population needs its own mapped-support
registration. This is not an alignment benchmark.

Proposed optical records: native320×240; depths(1,2); K12; inverse focus
(.5,.625,.75,.875,1); foreground/background fields exactly the frozen M194e
two-wave fields; normal(1,-.15), **offset142**, placing the boundary through
(160,120). Retain scalar radiance and declared CFA channel factors(.75,1,.6);
this supplies neither arbitrary scene chroma nor wavelength-dependent optics.
Add a flat control with both fields constant12000e, identical geometry and
focus records. Flat values may be computed exactly, but their active source,
noise injection and actual product output still need powered controls.

## Analytic cell branch and its boundary

Let T be the canonical-to-native map, M its inverse linear part, q0=T^-1(z)
at an integer native cell centre, n'=M^T n, h=n·q0-offset, H=(|n'_x|+|n'_y|)/2,
and R²=d_f²(n'·n'). Foreground-only requires h-H>0 and (h-H)²>R²;
background-only requires -h-H>0 and (-h-H)²>R². Both use the **foreground**
defocus, irrespective of the selected layer. Strict inequalities deliberately
route tangency/equality to the existing coupled numerical path.

For the small fixed coefficient set, an exact binary-rational predicate is a
simpler conservative choice than inventing a floating epsilon: take the finite
binary64 coefficients returned by the pinned inverse-matrix/defocus methods,
form the affine height coefficients and R² as exact rationals, then scale the
height coefficients to common integer units once per frame. Test the squared
inequalities with integers; do not take a rounded square root. Bound the
precomputed numerator/denominator bit lengths (proposed4096bits); an unsupported
coefficient set uses numerical fallback. No coordinate, mask, sliver or pupil
mass is moved or dropped. This predicate describes the pinned finite matrix
coefficients, not a theorem about arbitrary platform trigonometric accuracy;
the independent nonidentity comparisons remain required. Native height and
phase evaluation for the fallback stay the frozen implementation's arithmetic.

**Which model this certifies matters.** The rational predicate certifies
full-layer visibility for the real affine map whose coefficients are those
stored finite numbers. It does not certify the sequence of binary64 operations
used by `Similarity.inverse`, the subsequent dot product and the frozen
pointwise mask comparison. Rounding intermediate coordinates can change a
near-zero height's sign. It also does not certify that rounded `native_mask`
clipping and the separately evaluated chief-ray height are identical. Exact
rational arithmetic at the selector cannot retroactively make either floating
path exact. In particular, no bitwise equality of the hybrid and numerical
branches, or pointwise visibility equivalence arbitrarily near tangency, is
claimed. The target is the stated continuous cell integral; the two numerical
methods must meet the external discrepancy bars for that target.

Before implementation, freeze boundary controls with an independently derived
foreground/background tangent cell, then perturb its offset by each of
`nextafter` steps -4,-2,-1,0,+1,+2,+4. Repeat after a nonidentity similarity
and under positive rescaling of the mask equation, including a translated
coordinate representation that increases cancellation. Record the exact
rational clearance, the selector's branch, the frozen rounded point heights
at the relevant corners/tangent rays, and any visibility disagreement; do not
convert a disagreement into an alleged geometrical equivalence. Exact equality
must take fallback. Any new optional floating-roundoff exclusion zone must be
separately specified before code and counted by the cost preflight; its size
cannot be chosen from output discrepancies. No snapping or dropped rays.

On every boundary component, both enabled and disabled methods must return
within.004e of an independently integrated cell reference; report their
pairwise difference separately, without treating their shared rounded inputs
as independent authority. Refusals stay failures of commissioning. The complete
larger-array max.004e/RMS.0008e and separate refinement max.001e bars below
are unchanged. Near-ULP pointwise disagreement is therefore a recorded numerical
choice, not a waived cell-error bar. Off/count/placebo hash identity remains a
different requirement: identical numerical method/settings with only the
observer changed must still be byte-identical.

For a selected layer `c+b·q + Σ A cos(ω·q+φ)`, compute

```text
k = M^T ω                         (ω = 2π * cycles/native-pixel vector)
disc = 2 J1(|d| ||k||) / (|d| ||k||), with disc(0)=1
cell = sinc(k_x/2) sinc(k_y/2), with sinc(t)=sin(t)/t, sinc(0)=1
mean = c+b·q0 + Σ A*cos(ω·q0+φ)*disc*cell
```

Reuse the already available `scipy.special.j1` capability, **not** M25's
separate blurred-alpha composition or diffraction code. Precompute at most20
disc/square transfer tuples per five-frame two-layer arm. Keep negative lobes;
neither absolute value nor clipping is permissible. The signed d remains
unchanged in numerical partly occluded cells. Use an explicit exact zero
limit; any proposed near-zero series needs a bounded remainder and a separate
commission before use. Every emitted analytic value still needs finite,
nonnegative and source/model checks. Do not label an omitted adaptive estimate
as a measured zero error: record branch identity, transfer/control bindings and
external numerical discrepancy separately.

Suggested narrow API in the new directory:
`classify_full_layer(scene, frame, xy) -> foreground|background|numerical`;
`full_layer_cell(field, frame, xy) -> float`;
`hybrid_cell(..., analytic=True, meter=...) -> value, receipt`;
`render_expected(scene, frames, sensor, arm, directory)`.
The disabled branch always uses the original complete cell integrator. An
independent observer off/count/placebo records real branch counts and exact
cell coverage, with identical scalar/indicator bytes and a live hook witness.

## Cost, storage and a fail-capable preflight

Each arm contains384000 cells. For identity and the proposed mask, the
uncertain strip in each row has width `2*(|d_f|*sqrt(1.0225)+.575)`.
The following are **derived upper bounds**, not measured runtime:

| Original frame | abs(d_f) | Maximum uncertain integer cells/row | Whole-frame maximum |
|---|---:|---:|---:|
|0|6|14|3360|
|1|4.5|11|2640|
|2|3|8|1920|
|3|1.5|5|1200|
|4|0|2|480|

At most9600/384000 cells (2.5%) use coupled numerical integration; at least
374400 use the full-layer branch. This counts cells only, **not** 97.5% saved
time or angular work. Within a row, each of the three distinct parallel
clipping lines crosses at most two cells and adds at most two fan triangles
per crossing. Thus the initial numerical triangle totals are bounded by
[9600,8160,6720,5280,1920], the last using only the one distinct zero-defocus
line. Their sum is31680. Initial point calls are at most2534400 per primary
or angle arm, and10137600 per cell-refined arm; per-frame maxima768000 and
3072000 respectively. Refinement adds work and is not included in those bounds.

The finite68-interval angular bound alone is too loose to establish an
economical run: the cell-refined worst-frame nominal envelope is
`3072000*68*48 = 10027008000` angular nodes before adaptation. Therefore do
**not** promise the old600m-node cap will pass, or extrapolate a throughput
from M194e. First execute a separately allowed geometry-only preflight that
counts the exact common-height cuts at every consumed low/high point, all
three arms and all five frames, with no radiance/noise/product evaluation.
Preflight limits proposed:60CPU/120wall seconds and32MiB tracked arrays; failure
stops this proposal at `UNCOMMISSIONED_COST`. Preserve its source/counts before
freezing final numerical work caps. A larger cap must be justified prospectively
from those counts, not raised after an image run fails.

For planning, a proposed **upper authorization envelope**, not a success
prediction, is2400m angular nodes and16m point calls per frame,1800CPU/3600wall
seconds per five-frame arm,32MiB tracked arrays and32768 evaluated node pairs.
Exact preflight nominal counts must be below half the frame work ceilings;
otherwise return for design review before rendering. Keep angle depth10,
cell depth6, global error laws and mass checks unchanged. At most three
optical arms means5400CPU seconds/10800wall seconds total stop allowance;
the independent method gets its own explicit allowance, not this process's
unspent quota. No peer termination or scheduling exclusivity.

One scalar or indicator frame is614400bytes. Keep one scalar plus its current
indicator and bounded quadrature work, never all frames or repeats in memory.
Five scalar payloads are3072000bytes per arm; three arms with both scalar and
indicator payloads are18432000bytes per scene before NPY headers/receipts.
A CFA frame is153600bytes. Noise generation streams a single commissioned
primary expected frame at a time and never calls an optical renderer.

## Numerical and noise commissioning before a quality matrix

Retain M194e's all-pixel independent comparison bars: max.004e and RMS.0008e;
separate pupil/cell refinements max.001e; independent reference refinement
max.0005e. Every larger pixel, including the transition strip, participates.
An independent Cartesian/polygon reference may precompute transfer integrals,
but it must commission those with its spatial formulation; merely calling
the author's Bessel implementation twice is not independent verification.
No input CFA authority follows from author refinement alone.

Pre-register failures that exercise the actual branch:

- Constant and affine cell means; d=0; zero and near-zero wave arguments;
  both signed d and nonidentity rotation/scale/translation. Omit the inverse
  map or transform the centre without the wave/pupil vector: both must fail.
- Uniform-disc arguments5 and6.4 have negative transfer; use a positive DC
  offset and phase-zero wave so abs/clamp destroyers exceed the fixed error
  bar. Compare independently integrated disc and native-square responses;
  omit the square sinc as a separate live destroyer.
- Wholly foreground/background, exact tangent, one-ulp inside/outside and
  partly occluded cells; require the strict predicate's actual dispositions.
  A background-radius substitution and centre-only predicate must falsely
  admit a named partially occluded cell and fail independent truth. Signed
  defocus replacement must fail an intermediate-focus coupled cell.
- `analytic=False` versus hybrid on every selected component; full larger
  arrays versus the independent method; shuffled tiles and observer modes
  with hash identity. Denominator/coverage/source substitutions must refuse.
- Counters prove both full-layer branches and numerical fallback execute;
  the nonidentity controls must prove their maps are nonidentity. Work/depth
  fault injection must produce a refusal with partial evidence retained.

After float admission, inject the same explicit synthetic law used by the
algorithm: channel expected electrons, independent Poisson photoelectrons,
independent Gaussian read noise4e, gain.25DN/e, black512/white15360, ties-to-even
input quantization. It validates the algorithm under a supplied law, never
camera calibration. Reuse the fixed eight M194b seeds701,709,719,727,733,739,
743,751 plus noise-off; deterministic substreams bind scene/frame/site and
noise component. Do not select seeds after seeing flat variance or sparse
excursions. Record rails before clipping, expected-frame hashes, RNG identity
and draw/source binds. Noise-off identity, seed/frame liveness, stream
independence, known constant Poisson/read moments and real quantization/rails
need independent controls before the90 CFA files (2scenes×9bundles×5frames).

## Product handoff and interpretation

Use a new strict manifest/commission schema and new private child under the
existing prepared seam. Preserve M194f's bounded open-once/hash/decode order,
but validate153600-byte frames, source noise/repeat identity and actual
three-band levels. Bind runtime HardFloor/FloorPedestalV1 explicitly as M194d
did; neither name may masquerade as an unchanged default. Do not weaken
M194b, M194e or M194f readers. An input witness must reach actual gathering,
floor probing, collapse and TIFF writing.

Plan actual cover/domain first. For an initial fixed supported canonical
window propose x[104,216), y[104,136), with a boundary band |h|<=8 inside it.
The plan must prove its distance from every compact-output edge is at least
74native pixels for the identity/fixed-beta local support bound, or refuse
before pixels. It must also show four levels/three Laplacian bands and a
nonempty finite measured-beta prefix. The beta remains a domain-wide
estimate; the local guard does not make it independent of the rest of the
image. Retain whole-output and all-site sparse adverse diagnostics.

The minimal comparative matrix would be36 RGB TIFFs:2scenes×9bundles×2fixed
admission modes, all five frames, with exactly matched inputs/domain. Keep
ideal pinhole cell truth distinct from attainable optical observations; no
middle frame is a universal best-focus reference. Endpoint frame0/background
and frame4/foreground reference rows can be input-model diagnostics; if rendered
as single-input product arms, declare those additional outputs and probe seeds
prospectively. Root/independent scorers should freeze the exact score masks,
directional truth errors, temporal flat variance, bias and sparse tails before
this matrix. Positive weights, gradients or pooled error do not by themselves
establish better detail or lower noise. No default, calibration, capture or
SOTA conclusion is authorized by this proposal.

Read-only sources: `../m194e-joint-pupil/next-quality-fixture-notes.md`,
`../m194e-joint-pupil/next-production-bridge.md`, frozen M194e model/render,
M25 `optics.py`, current SYNTHESIS noise/admission decisions and M194f prereg.
Only source/record reads and this design edit were performed; no new numerical
count, timing experiment, renderer or noise generator was executed.

## Separate future documentation correction

`crates/strehl-core/src/demosaic.rs` opening property2 currently says a linear
interpolator cannot manufacture detail and therefore cannot inflate a downstream
sharpness metric. That inference is false: linear filters may amplify frequency
components, and these MHC stencils contain negative taps rather than convex
weights. The finite FIR bound is not a bound by the input sample range or by
unit frequency gain. [M189b's recorded common directional linear sharpening
counterexample](../../docs/research/M189b-directional-detail.md) reports the
actual frozen metric rising1.498791506×; that does not measure MHC's effect,
but directly refutes linearity as a general protection for a sharpness score.
The relevant replacement wording should say that phase-specific linearity makes
transfer and noise covariance calculable, while overshoot, aliasing, false
colour and metric inflation still require independent controls. Do not infer
independent photosite errors after gathering/merging merely from a linear
stencil; the quadratic variance law needs the actual covariance matrix.
This is a future scoped documentation edit, not an authorized change to the
current compiled demosaic source, and no new demosaic measurement was run here.
