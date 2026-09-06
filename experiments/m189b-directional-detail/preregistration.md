# M189b directional common-filter challenge

Status: FROZEN BEFORE FIRST EXECUTION, 2026-09-06. The root must review before
commit; this file's pre-run SHA-256 is recorded in the tool transcript and output.
No capture access, scorecard changes, or edits to the M189 candidate are allowed.

## Prior disposition

The root ran `python experiments/ORCH-drift-check/prior_art.py noise colour covariance`.
Read the relevant conclusions of M189-noise-colour-detail, M71-flat-fields,
M69-focus-noise-sd, BUILD-PYRNOISE, M48-read-noise-measured, V-GATHER,
BUILD-PYRNOISE-ADJUDICATION, M85-output-correctness, V-REVIEW-noise-verification,
and BUILD-HIGHLIGHT. The direct sources are M189's metric_v2.py, Amendment 1,
V2-RESULT, and M189-repeat-referenced-detail section 2.1. Amendment 1 already
excludes anisotropic transfer hidden by radial bins; this experiment tests that
declared boundary, and does not claim to discover a new general pooling problem.

## Question and independent prediction

The implemented denominator is a maximum of radial-bin MEANS, not a maximum
over Fourier cells. For independent photosite noise with variance v_i and a
unitary DFT, the marginal noise power is mean(v_i) at every cell, even when
v_i depends on the scene. A common fixed periodic convolution therefore gives

    C_f' = |K_f|^2 C_f
    G_b' = mean_{f in b} |K_f|^2
    Q'/Q = [sum_f |K_f|^2 C_f / sum_f C_f]
           / max(1, max_b mean_{f in b} |K_f|^2)

for the unfiltered white-noise population baseline. The numerator averages
transfer against scene power; the denominator averages against modes. These
are different measures. Concentrating scene energy in the high-gain direction
can make this ratio exceed one, even with exact population noise knowledge.
Finite-repeat uncertainty is a separate effect, assessed using independent
batches. This plant shares its PTC constants with the metric and validates the
operator only; it cannot validate sensor calibration (rule 34).

## Frozen fixture and independent choices

- 256 x 256 output, 16 independent repeat pairs per batch, 8 independent batches.
- Continuous periodic latent sampled at output positions: 8000 DN plus three
  horizontal-coordinate cosines, each amplitude 600 DN, Fourier x-indices
  68, 71, 74 (frequencies index/256 cycles/output-pixel), phases 0.2, 1.1, 2.4.
  All y-indices are zero. This is a directional grating scene, not M189's random
  isotropic latent. No resampling or alias approximation is needed for these
  bandlimited modes.
- Gaussian optical transfer exp(-2*pi^2*sigma^2*f^2) applied to the latent
  BEFORE noise. Sigma base 0.85, improvement 0.45, degradation 1.30 output px.
- Noise: independent zero-mean Gaussian draws per photosite with
  variance = 0.221113 * scene + (0.221113 * 1.2392)^2 DN^2.
- Batch j=0..7 uses independent seeds 189200 + 2*j and 189201 + 2*j;
  draws are reused across paired optical/control arms within a batch.
- Horizontal sharpening on each COMPLETED repeat:
  y[x] = 1.75*x[x] - 0.375*x[x-1] - 0.375*x[x+1], periodic.
  Its transfer is K_x = 1 + 0.75*(1-cos(2*pi*f_x)); it is fixed, linear,
  shift-invariant, DC preserving, and common to scene and captured noise.
- Perpendicular placebo: identical three taps along y. It reshapes noise with
  the same population radial average while leaving the latent scene unchanged.
- Post-blur control: the three taps [0.25,0.5,0.25] along x after noise.
- Identity: independent array copies, no operation.
- No denoising, fresh re-noise, fitted parameters, clipping, tone, demosaic,
  PRNU, frame-axis filters, or optimization/sweep. All fixtures use floating
  arithmetic; this is a metric experiment, not CFA storage implementation.
- Frozen candidate: actual `experiments/M189-noise-colour-detail/metric_v2.py`,
  SHA256 104F7414CE70C245AF0F4D14475047C05565084CA60C4DAAF2CA1AD486BC831E.
  The candidate receives only repeat arrays and the two PTC constants.

## Execution order, controls, and power before execution

First reproduce M189 v2's original numerical payload by running its unmodified
main with only the output directory rebound in memory to this lane. Source files
remain unchanged. Stop if any measurement/ratio/scene hash does not reproduce.

Then evaluate all 8 flat batches at constant 8000 DN, and their common horizontal
sharpening, BEFORE evaluating any scene-detail arm. Signed flat scores are a null
with population value zero. Do not divide one near-zero flat score by another.
Require abs(mean) + 3*SEM < 100 DN^2 per licensed mode for both flat arms.
Known failure input: give the flat pair the SAME noise realization; it must score
>100, demonstrating specificity power against repeat-correlated false structure.
This sabotage is not part of candidate validity and is explicitly correlated.

After the flat gate: base, identity, physical improvement/degradation, horizontal
sharpening, perpendicular placebo, post-blur. Report each ratio's mean, standard
deviation, SEM, and all 8 values. Tests compare mean +/-3*SEM (not a distribution-
free interval). Require identity error <=1e-12; improvement lower bound >1.05;
physical degradation and post-blur upper bounds <0.95; each unfiltered optical
arm's weighted-noise mean +/-3*SEM inside [0.97,1.03]. The scene can fail these
controls: changing improvement to base makes its ratio one, and changing the
degradation/blur to identity makes their ratios one. Mutate stored results to
those values and require the checker to reject them.

Horizontal sharpening safety is the candidate question, not a harness assertion:
mean ratio +3*SEM <=1.01 supports only this fixture; mean ratio -3*SEM >1.01 is
a powered counterexample. Between these bounds is inconclusive. Require raw
coherent-power lower ratio >1.05 and noise gain lower bound >1.05 to prove the
intervention occurred. Require perpendicular placebo score upper ratio <0.95,
and raw-coherent-power mean +/-3*SEM inside [0.97,1.03], to separate direction
matching from the mere presence of filtering. Fail loudly if these controls fail.

Independent expected-power check: sum the analytically known cosine powers
(side^2 * amplitude^2 / 2 per harmonic), optical transfer, and stencil transfer;
calculate radial mean K^2 directly from the frequency grid. Do not call the
candidate or FFT an image for this population result. Also compare a spatial
stencil on the deterministic scene against the independently predicted cosine
amplitudes with max error <1e-8 DN; a sign/tap error can fail this check.
The expected population and finite ratios are reported separately; no tuning
after seeing the outputs. Repeat source hashes before and after all runs.

## Interpretation

A directional failure restricts M189's common-LSI language to the tested
isotropic fixtures and rejects radial-bin means as a general transfer envelope.
It does not erase M189's genuine-improvement response or establish failure on
actual strehl/Zerene/Helicon outputs. No M1 admission or capture is implied.
A safe general population bound would need a certified per-cell transfer upper
bound (or explicitly bounded within-bin variation), and finite-estimator control;
this experiment does not build or commission that replacement.

## Reproducible invocations

From `C:\dev\blog\death-of-software\projects\strehl`, Python 3.12 with numpy/scipy.
Both scripts set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS,
NUMEXPR_NUM_THREADS, VECLIB_MAXIMUM_THREADS to 1 before importing numeric packages.
No CLI options are implicit. No captures or stack CLI environment variables are
read. The evidence records exact argv, Python/numpy/scipy, HEAD, source byte sizes
and hashes. No performance claim is made.

    python experiments/m189b-directional-detail/reproduce.py
    python experiments/m189b-directional-detail/run.py

Independent verification remains assigned to the root, per rule 12.
