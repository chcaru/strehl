# Independent fixed-visibility diagnostic

This is a causal test of the coverage degree of freedom, not an automatic
stacker, a repaired composite prior, or a renewed RAW admission. The completed
composite experiment remains rejected. Only flat and layered cases are used.

Root runs these commands, in order; neither implementation author executes:

```text
visibility-oracle-controls.py prepare --out <run/alpha>
visibility-oracle.py --source <screen-1/output> --alpha-root <run/alpha> --out <run/output>
visibility-oracle-controls.py score --source <screen-1/output> --oracle <run/output> --reference <composite-1/output> --out <run/scored>
```

`prepare` defaults to the existing screen-1 source directory. It checks the
frozen model and independent generator hashes, then exports only
`flat-alpha-f32.npy`, `layered-alpha-f32.npy` and `manifest.json`. The two arrays
are full 96×96 f32 coverage in [0,1], byte-bound to the frozen scene. No truth
radiances, pinhole truth, or held-out samples enter the optimizer through this
export. Preparing coverage is not a numerical fit or a new fixture.

The implementation restores screen-1 two-layer radiance parameters exactly,
replaces coverage with this oracle array, and optimizes near/far radiances only.
It uses the original hidden-sheet image prior, all original coefficients,
likelihood, discrete 64-ray optics, seven training frames and fixed LBFGS budget
from composite-1 (1000 iterations, nominal 1400 evaluations, hard 1800 actual
evaluations). Coverage-prior terms remain constants. The starting **pinhole**
changes deliberately although starting **sheet images and parameters** must be
exact. Thus this tests fixed known coverage versus free coverage; it does not
hold the initial rendered image fixed or claim the true sheets were supplied.
Score the saved initial pinhole with the same frozen `quality` function and
references as `initial_quality`, separately from final quality, so a gain from
correct-matte recomposition is not attributed entirely to later optimization.
This initial checkpoint is diagnostic only and cannot be selected as the result.

Scoring uses only each prescribed final checkpoint under `case/fixed-alpha`.
Reference is the same-case `composite-1/output/case/original`, not the failed
composite-prior arm or an iteration chosen by truth. Receipts must show exact
sheet initialization, fixed alpha, only near/far parameters, training-only
read indices, original checkpoint linkage, accepted finite returned state and
bounded evaluation count. Numerical refusal is explicit and is not reported
as a completed image-quality rejection. Hashes protect source, references,
coverage exports and new outputs. Initial sheet images and final alpha are
checked directly in saved arrays, independently of receipt assertions.

The frozen independent image and prediction functions are imported unchanged:

- Flat RGB/chroma errors must each be ≤1.05 the training-only mean and ≤1.05
  the paired free-alpha original-prior result. A better likelihood cannot hide
  a worsened flat image. Evaluate this case first.
- Layered whole/core/ridge comparisons to the original mean and restricted
  far-only model, original component guards and both withheld predictions stay
  unchanged, including the bright stratum. The far-only model cannot represent
  the near sheet and remains a limited reference.
- Fixed-alpha core/ridge RGB error must be ≤1.02 the free-alpha result. Glint
  and the fixed glint-free filament segment y31..41 must retain ≥.98 of capped
  free-alpha per-channel recovery, with every reference component live and
  recovery ≥.5. None is silently skipped. The original absolute ≥.8 component
  guard still applies.

The inherited half-component and wrong-colour destroyers give these metrics
power to reject a smooth highlight-free or decoloured result. RGB error can
reward blurred flat images, so true glint/filament components and held-out
predictions remain separate requirements. Component projection can credit
correlated excess amplitude, so recovery is capped for comparisons and paired
RGB error remains mandatory. No latent quantile becomes a quality criterion.

Report raw-parameter stationarity separately from image/prediction quality;
neither implies a global optimum. Report the existing 64-versus-1024 pupil
adequacy failure unchanged. Even a passing oracle diagnostic only locates a
harmful free variable in this known discrete plant: it provides neither an
estimated coverage field for photographs nor calibration or SOTA evidence.
