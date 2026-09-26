# Fixed variance-stabilized decision guide

Generated-only actual native consumer experiment. No RAW reads, photographic
claim, new calibration, denoiser, inverse transform, parameter sweep, or default
change. The proposed bright-defocus preference is a hypothesis; external
tone-before-fusion results do not establish its cause in the mineral stacks.

For injected green-plane gains g1/g2 and read floors r1/r2 in DN, fix
`a=(g1+g2)/4`, `b=(r1*r1+r2*r2)/4`, `c=b+3*a*a/8`, and S0=2000 DN. For
the actual gathered mean green s=max((G1+G2)/2,0), use f32 arithmetic:

`H(s)=2*sqrt(a*S0+c)*s / (sqrt(a*s+c)+sqrt(c))`.

This rationalized centered generalized-Anscombe coordinate has H(0)=0 and
derivative one at S0. The mean-green affine parameterization assumes equal
local green signals and independent original green sites; it is not a claim
that the gathered MHC/warp guide has that distribution. H-units match DN only
locally at 2000. The existing numerical `floor.max(1)` remains one **H-unit
squared**, so its physical semantics are deliberately not claimed invariant.
First-order energy/floor normalization can cancel the transform locally;
nonlinear, spatially varying supports must provide any useful headroom.

Four arms share one canonical `BandWorker::fold` per source: canonical;
canonical fields replay (identity); matched-estimator linear guide; and H guide.
The last two use the same sixteen original-source draws, seeded by the existing
rb-own-guide content identity, grouped into the existing eight independent
pairs. Existing boundary helpers inject the supplied original-CFA variance into
u16 copies and perform the actual rounded GPU gather. Form mean green after
gather; run the same H function on the actual guide and every noisy draw.
For each guide/band, smooth sum(pair coefficient differences squared)/16 using
the current spatial kernel. Multiply that measured conditional variance by the
unchanged gate. No white-probe beta, unit-variance assumption, independent-green
post-gather assumption, or private noise estimate is substituted. These are
Gaussian conditional perturbations around already noisy samples, not a new
Poisson calibration or exact nonlinear unbiasedness result.

Use existing `fields_from_energy` and `add_fields`: SoftPower, HardFloor,
exponent schedule and all numerical constants stay fixed. All four original
linear CFA pyramids use the same resulting guide weights. Original terminal
means, input bounds, final hull and final MHC remain current arithmetic; no H
coefficients enter reconstruction. Store no stack of aligned images. The
comparison retains hashes of actual source/known-four inputs, guide fields,
weights and outputs; a diagnostics-off call must be image-identical. Independent
controls own flat-first, identity, bright-defocus, genuine bright detail and
weak-colour truth/retention decisions. A scientific failure is recorded rather
than tuned. Full-stack consideration also requires a separate one-source cost.

Prior boundaries: A-prior-corpus F7 failed VST **denoising** under the old noise
profile, not this decision-only recipe. The Phase1 B6 combined Anscombe with
new winner admission; its NO_COMMON_K refutation was withdrawn by Amendment3
as an unsatisfiable width gate (2026-09-phase1-design.md supersession notice).
It remains unvalidated, not rescued. `layered-raw-inverse/shot-prior-results.md`
fails flat RGB/chroma after changing sheet regularization. `rb-own-guide/results.md`
fails flat/developed-green guards despite colour headroom. Those failures remain
closed; the matched-linear arm here isolates the shared Monte Carlo floor from
the nonlinear guide, and four-plane shared guidance differs from R/B-own updates.

Integration: root adds only a CLI test include named `variance_stabilized_guide`
for implementation.rs under test + native-direct-planes +
native-correction-variance + native-gpu-gather. Existing rb-own-guide,
boundary-cfa-wavelet, phase-packed-rgb and shared-source-field modules supply
their already exposed helpers. No core/shared arithmetic edits are needed.
