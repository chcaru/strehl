# Independent boundary and rounded-gather controls

Preregistered before execution, 2026-09-19. Implementation author is
new_captures; independent choices/controls are full_context_placement; root
alone builds/runs. No RAW, calibration, CA fit, parameter sweep, or photographic
claim. The fixed eight independent noise pairs are the actual candidate floor.

## Fixed inputs and power to fail

Use five original-u16 frames, active320x288 at decoded origin(7,11), padded
stride349 with sentinel64999 outside the active area. Crop(7,9,113,101) quads
is reflected centrally to128x128. Test identity and the already commissioned
gatefloor::gpu_warp fractional similarity, held for all sources of an arm;
generate analytic scene values in its inverse reference coordinates. Both
ISO100 and400 use the injected production model and actual warm manual-WB
bits[1070374912,1065353216,1076715520]. No CA. Original-source hashes and
the active CFA routing are independently checked.

Three scenes, in this order: flat0.30; weak red carrier46/256 native cycles
with amplitude2 times injected red sigma and predetermined focused source2;
neutral broad corner/edge structure with spatially varying focus and energy
in candidate bands below the old baseline cutoff. The exact analytic fixture
is in the control source. No periodic wrapping or scoring trim. Fixed native
16-pixel boundary strips and16x16 corners receive separate RGB-error checks.
Baseline reached sizes and candidate complete sizes are reported honestly.

Per ISO/warp, every guard must pass: structured RGB RMSE <=1.10 baseline;
flat RGB/chroma <=1.25 baseline and <= fixed source2; >=5% RGB benefit in flat
or genuine weak colour. Weak red must retain >=90% of source2's truth-capped
component, whose recovery must be >=0.5; own-red positive evidence must occur.
Coarse truth-component recovery must be >=0.5 and RGB error <=0.70 of a
constant-base destroyer. Any baseline component >=0.5 retains >=90% of its
truth-capped value. Structured boundary-strip and corner error must each be
<=1.10 baseline. Exact truth, half-amplitude and constant destroyers commission
the scores. Error alone can reward smoothing; amplitude alone can reward
overcontrast, so neither substitutes for the other. Flat noise is tested first.

## Structural and noise choices

Independent index enumeration checks half-sample reflection, four distinct
CFA phases, exact extension/crop, rectangular transform inversion/Parseval,
complete terminal DC, and source immutability. Identity known4 must match
original addresses; the fractional route must actually differ and use
overlapping source support. Repeating a reflected value is not a new draw.

Two fixed nearby original sites, at native(16,20) and(18,20), each perturbed
by +/-32 DN, define four equally likely states. They are near the top/left
crop support. Enumerate actual rounded gather, extension and transform.
Require observed code transitions, overlap of both source responses, and
nonzero off-diagonal gathered covariance. Compare the literal coefficient
variance against its explicit finite-distribution covariance contraction;
a diagonal gathered-site approximation must disagree. This is an operator
test, not a sensor-noise calibration.

On one fixed flat source per warp at ISO100, compare the actual eight-pair
estimate against64 independently seeded complete source-noise realizations.
The candidate cannot consume these draws. Reference is unbiased sample
variance about the64-realization mean. Also form32 independent pair estimates
to estimate uncertainty across realizations, never across pixels. For each
AC band summed across four planes with squared WB, require difference from
the held-out pair mean <=4 combined standard errors plus2% of reference.
For levels0..2 pooled together, additionally require ratio0.75..1.33 against
the64-realization sample variance; this broad fixed bar detects factor-two
routing/scaling mistakes while acknowledging eight-pair Monte Carlo error.
Report all band ratios and response bias; no corrected or inflated floor is
substituted. Require the factor-two destroyer to fail the pooled bar.

Observer diagnostics on/off must produce exact baseline/candidate RGB and all
eight collapsed planes on one exercised weak-red fractional fixture. The
actual source simulation uses the existing quantized normal generator,
conditional original-DN variance and u16 rounding; it is not camera validation.

Root runs the existing bounded runner under its process limits. Two tests emit
BOUNDARY_CFA_STRUCTURAL and BOUNDARY_CFA_SCREEN; screen.json records all
decisions even when photographic admission is false. A failing fixed boundary,
variance or weak-colour guard closes this recipe without tuning or weakening.
