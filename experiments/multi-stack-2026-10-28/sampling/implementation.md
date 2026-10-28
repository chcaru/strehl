# Native CFA session sampler

Allocation: multi-stack-2026-10-28-native-sampling. Source owned here is
crates/strehl-cli/src/session-sampling.rs. Root exports the module and schedules
all builds and runs. No original captures are read by these controls.

## API and coordinate contract

NativeSampler::new(SamplingDomain) allocates one reusable same-color source
scratch and four reusable signed output planes. gather accepts any QuadSource,
Levels, a green-luma-gauge Similarity, optional OpticalProfile and Resampler.
It returns planes in R,G1,B,G2 order plus coverage, clipped and support vectors.
The source full quad geometry must equal domain.full. A crop changes output
extent but never the transform center. working_bytes reports pixel buffers only.
sampling_bytes(domain) and ProbeMemoryEstimate::estimate(domain,bands) perform
checked allocation-free byte accounting, including transient probe masks/workspace;
both reject arithmetic overflow and totals beyond the addressable isize limit.

DERIVED: the green guide's integer coordinate corresponds to active sensor
(2*x+0.5,2*y+0.5). A CFA site at (2*x+dx,2*y+dy) therefore has guide coordinate
(x+dx/2-0.25,y+dy/2-0.25). Apply the placement about the FULL guide center and
subtract the same offset to return to that source's same-color plane. Absolute
sensor origins cancel between the photosite and its center. QuadSource performs
active-origin addressing, so no synthetic padding enters the arithmetic.

OpticalProfile::compose is the existing source-frame PULL convention: apply the
alignment first, then multiply source-center-relative coordinates by (1+eps)
and add the optical translation. No reciprocal and no second interpolation.
The absolute-sensor analytic control encodes four different ramps in a padded
u16 buffer and derives transformed sensor positions directly; it does not reuse
the sampler's site conversion.

Values come from the core Resampler::sample_checked. They remain signed after
black subtraction. The mask enumerator mirrors the owned core stencil solely
for original-code clipping checks, including negative-weight taps. Linear zero
weights do not participate; the clamped cubic's nonlinear hull includes all
16 taps. Impulse-response controls exercise the enumerator against the actual
core value sampler. No demosaic function appears in this module.

Missing entries are zero SENTINELS and are never observations. Consumers must
propagate support through all filter dependencies before admitting coefficients.
The probe masks precisely follow the binomial REDUCE and two-phase EXPAND
footprints, excluding replicated borders as well as missing/clipped pixels.
A poison test replaces all unsupported samples by one million and requires
identical bits in every admitted coefficient.

## Actual-warp noise transfer

measure_band_transfer(domain,placement,profile,resampler,ProbeConfig) generates
independent deterministic original-u16 Rademacher photosites (8192 +/-32), with
black 8192 and known variance 1024 DN squared. It passes them through the exact
NativeSampler and core Pyramid. E[coefficient squared] is normalized by the
KNOWN input variance, never by a fitted sample variance or a re-estimated sensor
model. Green input variance is 512 because G1/G2 are independent. There is no
MHC probe, u16 writeback, aligned volume, or intermediate demosaic.

WarpBandTransfer returns four CFA beta vectors, luma_beta, max_color_beta, sample
counts, realization count and seed. max_color_beta is the observed maximum
among CFA estimates; it is NOT a statistical upper confidence bound. The
consumer must use separate luma and color transfers. A scalar spatial average
is an approximation when phase varies over a scale warp or signal-dependent
noise varies across a scene. It does not establish per-pixel calibration.

Nonlinear ClampedCatmullRom is refused for the quantitative transfer probe;
its variance is content-dependent. Inadequate valid interior or invalid transfer
estimates are explicit errors, with no silent identity/white-noise fallback.
The initial implementation probes the complete requested output domain. This
is a correctness path, not yet a measured performance choice. Four realizations
are the default; tests use explicit counts/seeds. The probe allocates original
synthetic u16 CFA, sampler scratch/output, one luma plane, one pyramid/workspace
and small support pyramids. The caller must budget these transient allocations.

## Controls and status

Root reported the flat-first control passed. The first session suite exposed a
test-oracle error: nonzero separable Lanczos weights can underflow in a 2-D
unit impulse. The corrected oracle probes row/column impulses independently,
retains every nonzero factor, and additionally checks full-range u16 impulses.
Production clipping was not weakened. Root subsequently reported all 34 session
tests passed, including the repaired oracle and split-color phase control.
These are implementation controls, not photographic validation. Source-only
rustfmt completed:

    rustfmt --edition 2024 crates/strehl-cli/src/session-sampling.rs

Prepared controls (12 tests):

- a00: flat independent temporal variance at bilinear identity, half and quarter
  phases against analytic 1, 1/4 and 25/64; wrong identity-beta foil must fail.
- a01: identity pyramid variance agrees with the existing BandGain control.
- a02: planted channel correction puts R/B at identity and greens at half/half;
  expected color beta is 1 versus luma beta 1/4, using a separate seed.
- b00: signed negatives, separate color constants, missing coverage and clipped
  buffer-padding poison with nonzero/odd active origins.
- b01: absolute-sensor scale, rotation and optical-composition oracle; cropped
  output equals corresponding full-domain samples bit for bit.
- b02: clipped contributions from every CFA plane and negative cubic weights;
  zero-weight neighbors excluded for linear cubic but included in nonlinear hull.
- b03: all linear kernel clip footprints match actual core impulse responses.
- b04: missing/clipped invalid-value poison cannot alter admitted pyramid bands.
- b05: nonlinear/unsupported transfer refusal, deterministic repeats, max-CFA rule.
- b06: invalid domain, levels and singular placement refusal.
- b07: allocation-free checked byte estimates and overflow refusal.
- b08: one versus sixteen workers produce identical original-u16 noise, all six
  kernels of signed samples/coverage/clipping, and all five linear kernels of
  CFA/luma/max-color transfer bits and counts, with scale/rotation/CA/crop.

There are twelve named test functions (a00 through a02,b00 through b08); several contain
multiple independently asserted phases/foils. No photographic or performance
claim follows from these synthetic mechanics controls. Root/challenge perform
independent review; complete photographs and complete-stack comparisons remain
necessary before any quality conclusion.

## Performance plan

Root retains the preoptimization binary for matched timings. Exact next steps
are row-parallel gather/mask propagation and skipping clipping-stencil scans
when an entire source color contains no clipped original taps. Known-seed
synthetic filling is independently parallelizable. Compare exact output and
probe bits with one and sixteen workers; compare measured matched workloads
before making a speed claim. Full-domain four-realization probing is likely a
large cost, but no smaller-domain approximation has been authorized or tested.

## Independent consumer review

The first fusion version conflated clipped measurements with missing geometry.
Propagating that mask through coarse bands would remove large highlight regions.
The revised dual-mask consumer preserves covered censored values in a separate
display fallback, while excluding them from repeat moments, residual evidence
and focus weights. Global strict coefficients outrank that fallback across
groups, and only missing geometric dependencies invalidate the final output.
Source inspection found the resulting mask logic consistent. One proposed foil
remains for the core owner: a coverage-only censored source can widen the global
InputRange hull and affect a fully strict reconstruction after pyramid overshoot.
Separate strict/coverage hull handling would isolate that display-bound influence.

## Exact optimization, candidate 2

Root completed the ten-source full-resolution candidate-1 pilot before this
edit and retained outputs/multi-stack/candidate-1/strehl.exe. Root reported
92.605 seconds elapsed, 130.5 CPU seconds, 3.919 GB peak private memory,
8.42 thousand clipped gathered pixels, ten singleton groups and zero invalid
outputs. This note records the orchestrator's baseline observation; it does
not independently re-measure or turn it into a quality claim.

The released optimization changes ONLY:

- independent destination rows execute in the caller's Rayon pool, retaining
  each sample's exact coordinate expression and core interpolation arithmetic;
- original synthetic u16 noise fills in parallel using the same pure function
  of seed, realization and original sensor index;
- source deinterleaving records whether any original code in that color clips;
  if none does, its clipping stencil scan is provably unnecessary and skipped.
  Otherwise the complete nonzero-tap scan remains unchanged.

Probe realizations stay at four, all five pyramid builds remain, and f64 moment
accumulation retains its serial iteration order. There are no extra pixel
buffers, global settings, phase approximations, or resampling changes. Support
propagation is unchanged. Root reported all 35 session tests passing, including b08. The candidate-2
pilot completed in 33.459447 s versus 92.605367 s for candidate 1; both retained
receipts and exact commands are recorded in accumulation-optimization.md.
Root compared all 10 source beta arrays and reported exact equality after JSON
decoding. This is end-to-end timing; cache warmth is a potential confound for
attributing the entire improvement to sampler work.
