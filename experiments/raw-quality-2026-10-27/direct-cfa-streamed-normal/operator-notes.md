# Streamed original-CFA normal operator and fixed CG

2026-10-27. **SOURCE-PREPARED; no author numerical execution.** This checkpoint
implements the brief's original-CFA objective without an all-source residual
volume. It is not a successful reconstruction or photographic improvement.
The earlier flat-color/noise failure and64-step nonconvergence remain recorded.

## Implemented interface

`bands-gpu.py` exposes `Noise(shot4,read4,black4,saturation)`,
`HaarPlan(torch,observed_hw,origin_xy)`, and
`prepare_source(torch,codes,origin_xy,noise,mode="candidate",metric_override=None,
frozen_valid=None,diagnostic_admission_window=True,collect_evidence=True)`.
Haar methods are `forward`, `inverse`, `variance`, and `support`; the packed
`bands`, `sizes` and `count` follow the frozen CPU layout. `SourceBands` exposes
signed `observed`, `d`, marginal `variance`, `admission`, `metric`, original and
coefficient validity masks, and `factors(global_metric_scale,original_count)`.

`normal-operator.py` exposes:

```python
Source(source_id, source_xywh, affine, load_codes, frozen_valid=None)
StreamedProblem(torch, field_hw, sources, noise, mode="candidate",
                metric_override=None, device_limit_bytes=8 << 30,
                measurement=None, diagnostic_admission_window=True)
```

The loader returns one original unaligned u16 H,W array/tensor. Its source
rectangle is absolute original active-area `(x,y,width,height)`; the f64 affine
maps those coordinates to the single global latent field. The constructor scans
the sources for a common metric scale, then forms actual constants/Gram/G and
the projected RHS in separate streamed passes. It retains no all-source
observed, coefficient, metric, factor or residual array. Original source storage
and input-byte preservation belong to the bound loader/runner.

Methods: `current_source(source_or_id)`, diagnostic `weighted_forward(x,id)` and
`weighted_adjoint(coefficients,id)`, `normal(x,projected=True)`,
`rhs(projected=True)`, `restore(z)`, `evaluate(z)` and `metadata()`.
`normal` and `rhs` return global CUDA f32 HWC fields. `evaluate` returns restored
`x`, actual `full_normal` and `projected_normal`, raw/normalized nuisance
coordinates, objective objects and restored constants. Public attributes
`metric_scale`, `count`, `gram`, `tb`, `G`, `projected_rhs`, `calls`, and `field_hw`
support independent controls. `projected=False` is an explicit projection foil.

The supplied optional measurement may be root's separately commissioned
`PairedMeasurementGpu`: `forward_with_dc(x,rect,map)` returns both actual A(x)
and A(ones) using the same rows. Otherwise both calls use the frozen measurement
independently. The normal implementation does not replace A(ones) by exact ones.
All Haar operations cover the **entire current source**; only measurement and
adjoint calls are divided into at most1,048,576-sensel rectangles. Neither the
Haar basis nor the global inverse is tiled independently.

## Frozen data metric and explicit clipping omission

The producing GPU Haar reproduces the CPU's x-then-y operations,7-level maximum,
physical R,G1,G2,B phase extraction, rectangular detail packing, and unchanged
odd carry. The true transpose reverses those operations. Marginal variance uses
the half-sum in both branches, with unchanged odd variance carry. It is a
diagonal surrogate; cross-coefficient covariance is not claimed absent.

The only variance is the injected `shot*max(code-black,0)+read_variance` in DN².
There is no extra quantization term. AC admission uses the frozen y-major3x3
replicated-neighborhood sum/divide9 and
`max(1e-4,(max(E-2V,0)/(64*max(V,1)))²)`; LL admission is one. Every admitted
coefficient has `q=admission/max(marginal_variance,1)` and exact factor order
`(sqrt(q)/sqrt(global_max_q))/sqrt(N)`. N counts all original sensels, so clipping
does not silently introduce per-source rescaling. Zero factors explicitly omit
invalid observations from that same common-normalized objective.

Original `code>=saturation` is unobserved. Boolean AND follows each exact Haar
dependency; odd carries retain only their real source support. AC coefficient
validity is then eroded by its replicated3x3 admission window. LL uses actual
LL support. Invalid codes are never imputed; their finite values may pass
through scratch arithmetic, but no admitted coefficient or its admission
neighborhood depends on them. Counts per phase/band distinguish raw Haar
support invalidity from the expanded omission. All omitted color-constant
support causes refusal. The diagnostic fixed-mask override and omitted-window
foil are explicit; independent poison controls must exercise their difference.
The first source scan collects counts; repeated passes skip receipt reductions
while recomputing the exact same factors from original u16.

## Streamed nuisance projection

Let B include the above factors and source-grid Haar after A. For three global
camera-color constants C, actual T=B C has color-disjoint coefficient support.
One green constant covers both green phases. The implementation computes actual
T via A(ones), including small floating detail terms and genuine odd-carry
details. It accumulates three positive Gram entries, `tb=T'b`, and G=B'T in one
HWC image: each channel stores its corresponding constant's backprojection.
Absent/nonfinite Gram support is refused.

For an image v, `alpha_c=<G_c,v_c>/Gram_c`. The normal pass forms, separately
for each current source, `B_i v - T_i alpha`, then applies its weighted Haar
transpose and A transpose. This avoids subtracting two large global images.
The RHS similarly subtracts `T_i(tb/Gram)` in coefficient space before the
adjoint. Restoration is `X=z+(tb-G'z)/Gram`. Full true physical residuals and
their nuisance coordinates are recomputed at the end; a second streamed pass
forms the final projected normal by coefficient subtraction.

This is algebraically B'PB, not a new prior. Floating differences from the CPU
are explicit: raw diagonal Gram versus normalized column rows, stable rescaled
f32 dot reductions, one P versus the CPU wrapper's repeated f32 P, GPU Haar
reductions and atomic A transpose. Independent operator comparisons are needed;
bit identity is not asserted. G is not a claim of a measured scene nullspace.

## Fixed64-step solver and retained failures

`solver.py` exposes `fit(problem)` and a result with `x`, `correction_z`,
`status`, `converged`, `iterations`, `history`, `evidence`, and `save(out)`.
It performs normal CG from zero correction, at most64 iterations, with no
restart, preconditioner, new regularizer or parameter sweep. Norms use f32
mantissas plus integer binary exponents; dot products are rescaled f32 rather
than f64. Nonpositive curvature, underflowed/nonfinite steps and nonfinite
iterates refuse. The last complete finite iterate remains available.

Intermediate histories contain **recursive normal residuals only**. There are
no hidden per-iteration A/adjoint truth checks and no intermediate objective
monotonicity claim. Constant-only initial and final physical objectives, actual
final full/projected normals and constant-direction residuals are evaluated.
The unchanged1e-5 normal criterion and nonincreasing final-versus-initial
objective decide numerical convergence; recursive convergence alone cannot
pass. CG arithmetic is not claimed identical to the old CGLS recurrence.
Zero-start minimum correction norm need not mean minimum physical-image norm.

The result saves whole latent/correction f32 fields and status. It does not
silently equate latent coefficients with reference-cell-integrated output RGB:
final direct-RGB integration/development remains a later, separately released
full-photograph step. All receipt admission/quality claims remain false.

## Memory, cost and verification boundary

Retained state is original-u16 loader state, a few global f32 HWC vectors, three
scalars per color and one source's f32/Boolean scratch. Repeated normal passes
recompute source factors; they do not cache a roughly39GB299-source factor or
residual volume. Fallback A(ones) adds a real forward pass and is counted. The
paired path removes duplicate row construction only after its independent
comparison; it is not an LL-only substitution. Constructor passes and final
audit passes are exposed in counters and belong in whole-workflow timings.

Torch allocated/reserved high-water is checked against the declared limit.
Root's bound process and QPC timing govern actual resource/performance claims.
No speed is inferred from the earlier elementary A test. A complete weighted
normal/RHS cost must precede any299-source export or fitting release.

Author verification is source-only standard-library AST parsing and interface
inspection. Frozen measurement SHA8328b11c… and CPU formula SHA536aa094… are
checked at runtime and were not edited. Independent controls own Haar, phase,
projection, masking/poison, transpose and wrong-path comparisons. No author
Torch import, compilation, CUDA execution, RAW decoding or photographic fit
was performed.
