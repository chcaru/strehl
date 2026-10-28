# Actual full299 band-budget result

2026-10-27. **MEASURED negative photographic result; VERIFIED diagnostic
completion.** The complete reconstruction remains rejected. This job changed no
image, objective or solver and makes no quality claim. It identifies a measured
coarse-AC weighting imbalance and a separate boundary/DC defect in the objective;
it does not establish a normal-matrix condition number or a useful exact optimum.

The rejected [complete photograph](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/complete-stack.jpg),
[RGB16 master](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/native/rgb16-master.tiff)
and [signed camera-RGB master](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/delivery/camera-rgb-dn.f32le)
remain available. Large colored rectilinear fields replace the insect's hairs and
scales in the independent complete-image review. The retained 64-step fit refused
convergence, with true projected-normal ratio 0.08320654. Numerical refusal and
photographic rejection both remain; the budget does not turn either into a pass.

## Executed observation and identity

Root ran the following command, exit 0, in a bounded Windows Job Object:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B -X faulthandler 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-27\direct-cfa-streamed-normal\band-budget.py' --out 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\direct-cfa-streamed-band-budget-1\output'
```

The [receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-band-budget-1/output/receipt.json)
reports `COMPLETE_FULL299_BAND_BUDGET`, all299 sources, both mechanical controls
passing, unchanged producer/cache bindings, zero fit/adjoint/RAW-read calls and
no ARW opened. It consumes the saved signed 4743x7109x3 latent, the same299
original-u16 7032x4688 caches, held source maps, supplied noise and clipping masks.
The common metric scale is 73572098048; the original observation count is
9856838784. There is no aligned-frame or RGB-source volume.

Wall time was 144.25s (worker 143.7744s), process-tree CPU 326.703125s, peak host
commit 6561054720 bytes, CUDA allocated/reserved peaks 3098637312/3246391296 bytes.
The device was RTX5090; Python3.12.10, Torch2.11.0+cu128, NumPy2.4.4; four CPU
workers and one interop worker, TF32/autocast off. The invocation binds all source,
library and input identities. `OMP_NUM_THREADS=4`, `MKL_NUM_THREADS=4`,
`OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, and
`CUBLAS_WORKSPACE_CONFIG=:4096:8`. These are measured job costs, not a new speed
claim or an estimate of a revised reconstruction.

Key SHA256 bindings:

| Artifact | SHA256 |
| --- | --- |
| Diagnostic source | `405e5ccbc644c6cfc3c11a3d3483227fc589476a39ee1728b53a71ce00541d1c` |
| Receipt | `5a21a39c3025cabbed45a9a99d2c03f7dc57b56bcc53f70930a266851122e7a5` |
| Budget | `0340d0734e13c5611bdc890cf0da7e37a71a0d4f5ca7e1205b9a195b652f2524` |
| Full-size Haar controls | `413418bb5481691e7542d92f053c5099b924f19d741dd66ad612f4a67108e1c9` |
| Original-sensor row controls | `8cebdcaa8d9cbb701bdf41f1fd7fd3339152f6a03e6b5134ba70a8d8418f97f3` |

## Producing-path controls

**VERIFIED:** all88 physical-phase/band coefficient arrays match the frozen CPU
Haar exactly at the actual full size, including the odd-carry levels. The
roundtrip maximum is 0.0048828125DN, normalized maximum/RMS
3.0766e-7/4.3001e-7. The independent coefficient-vector transpose matches CPU
exactly; normalized dot error is 8.1391e-12, Parseval error 3.9081e-7. All pass
the prospectively fixed bars in [band-budget-notes.md](band-budget-notes.md).

**VERIFIED:** 112 fixed original-sensor rows in each of sources0 and149 agree
with the frozen CPU integrated Lanczos3 operator on the saved global latent,
without crop/rebasing. Maximum differences are 0.0001220703125 and
0.00006103515625DN. The actual wrong-phase and shifted-origin foils fail the
same comparison bars. This supplies no evidence of the suspected full-size
Haar/index/measurement implementation failure at the exercised points.

**VERIFIED:** the same-source-order full-vector final and initial objectives
reproduce the saved solver exactly: 0.1743023544549942 and 10.370499610900879.
Per-band reductions differ by -2.3623e-8 and -4.2039e-7, inside the prospective
reconciliation bars. Actual constant Gram and `T'b` also reconcile. Thus the
photographic failure is not explained by this observer measuring a different
objective or silently using a different constant-only reference.

## What the actual objective emphasizes

**MEASURED:** the following aggregates include all299 sources, all four
physical phases and all three AC orientations. `q` is the actual coefficient
metric before common `qmax/N` scaling. Raw errors and observed energies cover
admitted coefficient support only; omitted support remains in the JSON census.
The error/target ratio is squared-error energy divided by observed coefficient
energy, not an independent-noise likelihood, component-recovery score or
photographic quality metric.

| Band | Nominal native support | Share of all q | Raw error / observed energy | Share of final weighted error |
| --- | --- | --- | --- | --- |
| AC0 | 4px | 0.00006123% | 1.04137 | 0.00009018% |
| AC1 | 8px | 0.00040262% | 1.06855 | 0.00127275% |
| AC2 | 16px | 0.00251519% | 1.11046 | 0.00743215% |
| AC3 | 32px | 0.04159522% | 1.07600 | 0.08362483% |
| AC4 | 64px | 0.98255063% | 0.92032 | 2.93427799% |
| AC5 | 128px | 14.45631431% | 0.62774 | 38.53405608% |
| AC6 | 256px | 84.51656075% | 0.12632 | 58.43924219% |
| Terminal LL | 256px nominal | 0.00000005100% | 0.90022 | 0.00000383% |

AC5+AC6 hold **98.97287507%** of total q; the same share is 97.45271% to
99.84776% in every individual source. This is coarse-AC dominance, **not LL
dominance**. Fine AC0-3 remain more erroneous than the energy of their observed
coefficients, while the coarsest AC is substantially represented. This supports
the scale-starvation explanation for this saved iterate, without proving the
cause of every block or the image at exact convergence.

**DERIVED:** orthonormal Haar step magnitude grows with support, whereas white
noise variance does not. For a fixed step, its AC coefficient grows roughly as
2^k; the frozen squared excess-energy admission can therefore grow roughly as
16^k. A per-band weighted average cancels a common weight multiplier. A joint
inverse with the raw weights does not cancel a multiplier that differs between
bands. Common qmax or source-count scaling changes neither this relative
objective nor its exact minimizer. More iterations or preconditioning alone
would pursue the same measured objective; no evidence here establishes that its
exact optimum preserves the photograph.

The boundary issue is distinct. Nominal partial supports account for 2.06354%
of q; the expanded boundary-admission neighborhood accounts for 2.44330%.
Thus most coarse q is interior. In contrast, **99.99850948% of actual `T=B*C`
energy lies in that boundary neighborhood**, and 99.99842070% lies in AC5.
The original odd carry is a correct orthonormal transform, but its unequal
support normalization permits a spatial constant to produce AC when those
supports are combined later. Exact nuisance projection includes those actual
columns; it does not prevent the focus gate from scoring that constant response.
Repairing only the boundary cannot remove the measured interior coarse weighting.

## One proposed changed objective; not implemented or released

**ARGUED, UNVERIFIED:** first preserve focus ordering within each level while
removing the unbounded average admission multiplier between levels. Let
`v=max(injected marginal coefficient variance,1DN^2)` and retain the existing
admission `a`. For AC level k, pool all admitted original coefficients over
all299 sources, phases and orientations:

```text
Qk = sum(a/v)
Rk = sum(1/v)
q_new[k] = (a/v) * (Rk/Qk)
q_new[terminal_LL] = 1/v
```

Use one shared positive scalar per level, not per source/color/orientation.
An empty admitted stratum remains omitted and is reported. A nonfinite or
nonpositive denominator with admitted support is a hard refusal. All metric
scales are computed before fitting and frozen. Existing common numerical
rescaling may then be applied to the whole metric, identically forward/adjoint.

This is a normalized risk with each level's total metric mass equal to the
supplied-noise, no-focus reference mass. It is not a likelihood, an estimated
post-selection covariance, or exact per-location source normalization. It
preserves every pairwise relative weight within a level, including source
preferences for independent colored structures. Setting `a=1` gives the
existing no-focus metric exactly. Multiplying all admissions in one level by
one positive constant leaves the new metric unchanged. Different source Haar
grids are not pretended to represent identical physical coefficients.

Use support-count-aware orthonormal Haar for unequal lowpass carries in the
same candidate, with child support counts nL,nR:

```text
low  = (sqrt(nL)*left + sqrt(nR)*right) / sqrt(nL+nR)
high = (sqrt(nR)*left - sqrt(nL)*right) / sqrt(nL+nR)
```

Equal supports retain the old pair; an unpaired child carries its actual count.
Apply separably, use the exact transpose and squared-coefficient variance
propagation. This removes mathematical constant AC response, apart from f32
and actual A(ones) error. It deliberately changes H and admission at the
affected boundaries; it is not a solver-only repair. Recompute actual T/Gram.

This choice is preferred here to `a=s^2/(1+s^2)`: the bounded alternative is
plausible reliability weighting but saturates all strong-focus evidence and
can weaken selection between sharp and defocused sources. Level normalization
keeps those rankings. Its own risks remain substantial: bright structures can
still dominate *within* a level, the normalization is global and content
dependent, fine noisy/aliased constraints regain influence, and old flat/color
failures are unresolved. No DC/noise/detail-preservation guarantee follows.
In particular, a flat whose admission is everywhere the floor returns to
`q_new=1/v`; normalization is not denoising. It supplies neither an occlusion
model nor a defocus forward model.

The smallest useful actual direction test is one unchanged all299 data pass
to obtain the new scalar budget followed by **one four-iteration full-field
pilot**, retaining complete fixed-development images/masters at iterations
1,2,4 and the unchanged numerical-refusal status. Do not replace this with a
favorable crop or a new synthetic campaign. Before that pilot, commission the
unequal-count Haar constant/transpose/null and literal per-level ratio
invariance, including zero evidence. The actual budget must verify that
constant AC no longer determines T and document the resulting fine/coarse
mass; those are mechanism checks, not quality admission.

Root should inspect every complete pilot image and all existing fixed witnesses
against the retained native baseline, failed inverse and source-supported
details. Stop if the result remains block-dominated or replaces blocks with
colored noise/false detail. Only visible directionally useful whole-image
behavior can justify continuing that same candidate with complete checkpoints
at8,16,32,64; numerical convergence alone is insufficient. No new thresholds,
parameter sweep, prior, channel borrowing or RAW reads are proposed here.
