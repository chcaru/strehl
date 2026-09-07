# M194g — larger shared-pupil expected images

2026-09-07, root. Prospective registration. The first release is geometry-only
cost and selector commissioning. Component radiance controls and complete
expected-image generation require their independently reviewed, committed
source/configuration releases under the numerical bars below. No noise draws,
CFA emission, production comparison or default change belongs to this milestone.

## Consumer, prior work and fixed model

The consumer is a subsequent noise generator reading complete, independently
admitted scalar expected-electron arrays. A successful cost count is not that
admission. M194e commissioned the fixed 64×48 shared-pupil model and conversion;
M194f independently admitted eleven actual production TIFFs through its bridge.
M194b/M194d's one-plane quality plant cannot express depth-boundary dilution.
M25 already implements the full-disc transfer but its failed physical-optics
gates are unaffected. M194g changes numerical evaluation and image extent, not
that mathematical model's physical authority.

The mechanical prior-art search is retained in
`../m194f-production-bridge/next-larger-prior-art.log`; read the named M194e,
M194f, M194b and M194d reports plus the two larger-fixture design notes. The
source bindings are recorded separately before release. No SYNTHESIS fold or
numeric block is assigned.

One textured scene: native 320×240 integer-centred unit sensor cells; foreground
and background fields exactly as `m194e-joint-pupil/model.py::primary_scene`,
depths (1,2), normal (1,−.15), offset 142 (edge through 160,120). Five original
indices 0..4, inverse foci (.5,.625,.75,.875,1), K=12, identity placements in
reference-2 native coordinates. Scalar radiance, uniform unit disc, same pupil
ray for foreground visibility and both radiance intersections. Three complete
arms: primary, angle-refined, cell-refined. Each contains 384000 cells; all
1152000 arm/frame/cell records are required. A future flat/noise scene is not
silently added to this population.

Reuse the immutable M194e `model.py` and `render.py` through a pinned wrapper;
do not edit those sources or label new arrays with an old M194e schema. All
source imports are hashed and snapshotted with actual original arguments,
Python/library versions and thread environment. Fresh process/cache per run.

## Full-layer branch and exact meaning

For inverse linear map M and native centre z, let q0=M(z−centre−translation)+centre,
n'=Mᵀn, h=n·q0−offset, H=(|n'_x|+|n'_y|)/2, R²=d_f²(n'·n'). Full foreground
requires h−H>0 and (h−H)²>R². Full background requires −h−H>0 and
(−h−H)²>R². Both decisions use foreground defocus. All other cases, including
equality, use the unchanged coupled cell integrator.

These comparisons use exact binary-rational arithmetic on the stored finite
matrix, centre, translation, normal, offset and defocus, without first rounding
a combined translation. Bound every rational intermediate to 4096 bits; an
unsupported coefficient set falls back without moving model values. This
certifies a continuous real-affine model with those finite coefficients. It
does not certify the sequence of rounded inverse-map, clipping and point-mask
operations as pointwise equivalent. Independent cell-integral error bars apply
even where near-tangent rounded visibility disagrees. No epsilon, coordinate
snapping, dropped sliver or inferred zero numerical error is permitted.

For a selected layer wave A cos(ω·q+φ), ω=2π times its stored canonical spatial frequency,
k=Mᵀω. Multiply its centre value by
`2*J1(|d|*norm(k))/(|d|*norm(k)) * sinc(k_x/2)*sinc(k_y/2)`;
sinc(t)=sin(t)/t. The exact removable zero limits equal 1. Preserve negative
disc-transfer lobes. DC and affine terms average to their centre value.
SciPy `special.j1` may implement the author's branch; the independent spatial
oracle must not reuse that call. The disc relation follows from the order-1
case of [NIST DLMF 10.9.4](https://dlmf.nist.gov/10.9.E4); the installed function
is documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.j1.html).
This is a geometric uniform-disc radiance transfer, not a diffraction model.

## First release: geometry-only cost preflight

Traverse every native cell once in every frame and arm. Record exact coordinate
coverage and counts of foreground/background/numerical branches. At each
numerical cell, use the actual pinned `cell_triangles`, `tangent_indices`,
`triangle_rule`, mass checks and common-height `angular_cuts`. Count both low
and high cell-rule points, and both angular-rule nodes for each nonempty cut
interval. Do not evaluate radiance, Bessel values, integrals, noise or pixels.
The cut height must reproduce `render_points`: evaluate `Similarity.inverse(xy)`
and then the scene-normal dot product minus offset. Its radius and signed alpha
come from `native_mask` and signed foreground defocus exactly as in that source.
Do not substitute the selector's rational/precombined height. A powered small
cancellation and negative-height companion must expose changed ladder cuts
under that substitution. This tests counter fidelity to its actual consumer.
Retain per-frame roots, low/high points, nominal angular nodes, maximum interval
count, ordered coordinate/branch/point-cut digest and all refusal evidence.
Hold only bounded rule arrays; digesting coverage does not prove it unless
the enumerator itself passes the independent omission/duplicate controls.

Limits: 60 CPU seconds / 120 wall seconds for the complete three-arm preflight,
32 MiB tracked owned arrays (explicitly not RSS). The wrapper must explicitly
check one non-resetting clock across all fifteen arm/frame traversals, including
analytic-only cells, because the frozen geometric helpers do not call Meter.
Check work/time at least per cell and rule batch; account for all simultaneous
owned rule arrays and views by unique backing allocation. Merely constructing
a Meter does not enforce these bounds. The full per-frame nominal
counts must be strictly below 8 million points and 1.2 billion angular nodes.
Both limit crossings and geometry/mass/coverage failure return
`UNCOMMISSIONED_COST`; preserve partial counts and do not release images.
The factor-two headroom is an engineering stop rule, not a theorem bounding
adaptive work and not a speed claim. No direction/thermal timing comparison.

Before intended counting, independently chosen non-square and nonidentity
small fixtures must exercise both full-layer branches and fallback, both
defocus signs and zero defocus. Count actual helper roots/points separately.
Missing frame/cell/low-order/negative-height cuts, duplicate coordinate coverage,
unsupported coefficient handling and injected work/time/storage limits must
fail on their actual paths. Valid companions must pass. Author source and
independent controls are committed before intended preflight.

## Later numerical release: frozen acceptance limits

Before any intended radiance, freeze component records and independent oracle
implementation. Constant/affine, zero and near-zero argument, negative disc
lobes (arguments 5 and 6.4), nonzero square transfer, transformed centre/wave/
pupil vectors, both layer decisions and coupled relative-defocus signs are
required. Actual wrong-map, wrong-radius, centre-only, missing-sinc, abs/clamp,
zero-limit and normalization substitutions must fail. A common global pupil
sign reversal is an inert symmetry, not a relative-sign destroyer.

Exact identity and power-of-two nonidentity tangent cells use offset perturbations
of −4,−2,−1,0,+1,+2,+4 nextafter steps. Rotated cases bracket the high-precision
tangent by adjacent binary64 offsets; do not call a rounded centre exact.
Also vary mask scaling and a cancelling translated coordinate representation.
Record rational clearances and actual rounded extreme-ray heights. Enabled
and disabled analytic methods must each agree within .004 electrons with an
independent integral on every component; independent refinement must be at
most .0005 electrons. Refusals are failed commissioning, not omitted controls.

After component and cost admission, intended numerical limits are 16 million
points and 2.4 billion angular nodes per frame; 1800 CPU / 3600 wall seconds
per five-frame arm; 32 MiB tracked arrays, one scalar frame and 32768 node pairs.
M194e orders, depths, global frontier error law, mass guard and family point
budgets remain unchanged. The independent implementation receives its own
prospectively frozen resource ceiling before its launch. No peer termination
or exclusive host reservation; each process enforces its own caps.

Every complete frame in all three arms must agree with independently refined
truth at maximum absolute error ≤.004 electrons and RMS ≤.0008 electrons.
Primary versus either refinement must have maximum discrepancy ≤.001 electrons;
independent reference refinement ≤.0005 electrons. Apply the same external
max/RMS bars separately to a fixed |x−.15y−142|≤8 boundary band, and report
numerical-fallback populations separately so analytic interiors cannot hide
boundary errors. Masks are input-defined and not selected from output errors.
No successful subset, arm substitution or partial frame can grant admission.

Analytic cells carry branch and external evidence, never a fictitious measured
zero adaptive indicator. Finite values, shape/type, complete coverage and all
source/array digests must be independently checked; actual changed arrays,
NaNs, missing frames, source mismatch and changed scene/phase must refuse.
The same algorithm with observer off/count/placebo and reordered independent
cell traversal must produce byte-identical scalar and diagnostic payloads;
the count and placebo hooks must demonstrably execute. Here diagnostic payload
means numerical indicator/branch arrays, not mode-dependent counters, timing,
hook receipts or traversal-order digests, which intentionally differ. Independent methods
are compared numerically, not required to have equal bytes.

## Interpretation and onward work

A complete independent float commission can release a later versioned noise
emitter. Noise calibration, attainable versus pinhole truth, output support,
actual three-band levels, temporal flat variance and sparse adverse tails need
their own production-comparison registration. These expected values are not
evidence of SOTA, optical confidence, physical calibration, alignment accuracy
or improved merge quality. Failure can revise the numerical strategy while
retaining all earlier evidence and fixed model definitions.
