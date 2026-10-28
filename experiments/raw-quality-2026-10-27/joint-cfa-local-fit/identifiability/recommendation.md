# Resolve the measured residual before adding an image prior

2026-10-27. **VERIFIED saved evidence / DERIVED operator equivalence / ARGUED next step.** Source and retained-report review only; no fit, RAW read, build or numerical campaign. The unchanged fourteen-fit screen and photographic path remain stopped.

## What the flat failure establishes

The [saved flat](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/independent-observations.json) reports convergence after45 iterations, yet central96 RGB error is303.055DN and chroma error374.289DN. Channel mean errors are approximately -155.79,+4.20,-184.27DN. This is not adequately described as increased chroma noise.

Root's [no-fit residual budget](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-residual-budget-1/output/residual-budget.json), SHA`a0a1ca4fbe720e2781d716a473941694c40c450ff6fa39811291bc7ab3aa98be`, reproduces saved delivery exactly and retains original/query/metric identities. It measures substantial error at the original sensels: R89.39-214.39DN and B112.06-249.39DN RMS across sources, approximately5-12 supplied temporal sigmas; both green phases also carry measurable error. These are RMS errors against known flat radiance, not estimates of temporal noise.

The original objective at the saved image is0.00453734, versus0.000368421 at the known constant: the constant is about12.3times better under the same frozen objective. Therefore this result is not merely an unseen between-photosite alias or a satisfactory minimum with an unfortunate display. Significant observable residual remains. DC-dominated relative stopping together with weak AC weighting is a plausible mechanism to challenge, not yet a complete causal attribution. My earlier proposed sampling-mode restriction is deferred; this evidence does not justify building it first.

## What prior work rules out

The [September Lanczos control](../../../quality-september14/joint-cfa-lanczos-verdict.md) improved all twelve noiseless RGB cases but raised fractional-phase flat chroma error above single-frame MHC. It already had a per-channel first-difference prior and a nonzero initializer. The [four-update backprojection](../../../quality-september14/joint-backprojection-verdict.md) improved signal but roughly doubled RGB noise and increased chroma noise2.6-2.7times relative to its initializer; [actual images](../../../quality-september14/results.md) retained soft rails and cyan stipple. Merely adding that prior, changing initialization or stopping after a few corrections is not a new supported quality recipe.

[BUILD-DEMOSAIC](../../../../docs/research/BUILD-DEMOSAIC.md) establishes why reduced R-B high-pass energy cannot certify correct colour: correlated reconstruction errors can lower that statistic. [M194f](../../../../docs/research/M194f-production-bridge.md) commissions values/coordinates through a tiny product adapter, not optical identification or a noise-safe inverse. The recent [known-blur result](../../raw-blur-compatibility/known-variance/independent-results.md) recovered component amplitudes while failing whole-image RGB/chroma. Keep complete-field error and independent coloured structures decisive.

## One concrete next question: exact constant deflation

Use the unchanged weighted producing operator B and right-hand side y. Let C contain three independent constant-colour latent fields and U=B C, evaluated through the actual operator. Define the orthogonal residual-space projector P=I-U(U^T U)^-1 U^T. Solve `min_z ||P(B z-y)||^2` with the same64-step cap, then restore `c=(U^T U)^-1 U^T(y-Bz)` and `X=z+C c`. A stable small solve replaces an explicit matrix inverse. Constants come from the observations, never supplied truth.

This analytically eliminates only three nuisance coefficients. It preserves the original objective and its minimizer set without tying R/B structure to green or penalizing every spatial gradient. It is distinct from simply initializing the old recurrence at a mean. In a rank-deficient system, however, zero-start projected CGLS can select a different minimum-correction solution than the original minimum-full-image-norm solution. Disclose that implicit selection; do not claim identical converged images.

Record the reconstructed original objective, true projected normal residual and restored constant-block normal residual. Normalize stopping by the initial projected normal, handle an exactly zero projected problem explicitly, and retain numerical refusal at64. An offset-invariance control must keep B, noise and data-dependent weights frozen: recomputing shot variance or admission after changing DC changes the problem. Include independent per-channel offsets and a nonconstant coloured positive so an implementation returning only fitted constants fails.

The first useful decision is whether this one fixed intervention removes the already observed flat defect while retaining the known detail/colour positive, with no cap, gate, prior or tolerance sweep. Failure closes this finite solver recipe. Success would resolve this numerical obstruction only; phase ambiguity, defocus/occlusion mismatch, noise amplification and full-photo practicality still require evidence. No photographic improvement is claimed.
