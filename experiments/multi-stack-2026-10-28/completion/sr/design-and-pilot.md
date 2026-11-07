# Direct original-CFA reconstruction: design and first pilot

Allocation: multi-stack-2026-10-28-completion-sr. Root approved an experiment-only
Rust module and bounded synthetic harness on 2026-10-28. No existing product
module, Cargo manifest, RAW capture or existing cache key is edited in this lane.

## Mechanism and source distinction

Wronski et al. reconstruct RGB from original CFA measurements with locally shaped
positive kernels, motion confidence and online per-channel normalization. Their
continuous representation permits a chosen output grid. They also identify
alias content and differing subpixel offsets as necessary ingredients; local
motion can reduce the result to a single acquisition. This motivates the direct
sample operator here, not transplantation of their phone tuning or quality claims.
Primary source: [Handheld Multi-Frame Super-Resolution, sections 3–5 and 7](https://storage.googleapis.com/gweb-research2023-media/pubtools/5211.pdf).

Repository precedents: B-algorithms-sota sections 6/8 and
2026-08-sota-path C1/C12 describe the same missing consumer. M95-demosaic shows
that band power can reward false detail; BUILD-DEMOSAIC shows that correlated
color errors can reduce a chroma statistic while worsening ground-truth error.
M95-chroma-cositing requires actual photosite positions. SYNTHESIS section 4.1
requires measured local phase opportunity, not a universal tripod-jitter veto.
The rejected native spectral reconstruction used projected band normal equations
and a global solver. This work uses bounded local positive sample kernels, no
spectral-band reconstruction or global inverse solve. It is a changed operator,
not a new set of knobs for that rejected recipe.

## Coordinates and output contract

All reconstruction coordinates are active-area sensor pixels: integer locations
are physical photosite centers. Full alignment coordinates retain their current
meaning: guide (qx,qy) is sensor (2qx+0.5,2qy+0.5). For a target sensor position r,
apply the existing channel-composed source pull to (r-0.5)/2 about the full guide
fitting origin (width/2,height/2), which is physical sensor
(width+0.5,height+0.5), not the array sample centroid. Original sample (sx,sy) is transformed back with the exact inverse of
that pull, giving its physical anchor position. No interpolator estimates its
value. Odd active origin is handled by QuadSource's original active row access;
no crop is allowed to recenter the global transform. CA uses the production
radial-only applied profile; synthetic nonzero-translation tests establish the
composition convention independently.

OutputLattice carries full anchor PlaneGeometry, sensor origin, positive sensor
steps and width/height. Noninteger output scale is allowed. Reconstruction returns
camera RGB f32, propagated temporal variance, validity and diagnostic maps. It
must bypass the existing final Bayer demosaic: these are already three complete
color planes. White balance/color development happen once afterward.

## First implementation API

The standalone kernel module imports existing core QuadSource, Similarity,
OpticalProfile and PlaneNoise. No new dependencies are required.

- OutputLattice: full anchor geometry, origin_sensor, step_sensor, width, height.
- SourceView: unique independent-acquisition ID, borrowed original QuadSource,
  channel pulls, four injected PlaneNoise values, photometric gain, borrowed
  output-tile focus weight, motion confidence, validity and placement uncertainty.
- FrozenGuide: borrowed expected camera-RGB signal, edge structure/kernel tensor,
  tested native fallback RGB/variance/validity. The guide is frozen independently
  of the target sensel used in a kernel weight.
- ReconstructionConfig: narrow-kernel bandwidth, edge anisotropy limit, maximum
  registration uncertainty, maximum phase condition, requested reconstruction
  scale and a checked 64 MiB tile budget. Runtime caps are explicit.
- reconstruct_tile(lattice, sources, guide, config): validates inputs, streams
  original same-color samples, returns TileResult and diagnostics.

Initial CPU implementation is row/pixel separable. Per-pixel accumulators are
fixed-size, structure-of-arrays-compatible arithmetic suitable for one GPU
invocation per output pixel. No scatter atomics, source-order reduction, global
GPU allocation or aligned source image is required. The first prototype is a
correctness reference; root schedules compilation and numerical runs, followed
by an exact performance pass and a separately checked GPU kernel if worthwhile.

## Weights, geometry and fallback

Each contributing raw u16 is promoted to signed f32 and black-subtracted once.
The photometric gain multiplies signal, and its square multiplies variance.
Clipping is tested on the original sample against that plane's white level.
Weights are nonnegative kernel × focus × motion / predicted variance. Variance
is evaluated at the frozen guide prediction in source DN, never at the same
noisy measurement whose value is being weighted. A dedicated heteroscedastic
flat control compares this with the biased same-sample inverse-variance foil.

R/B use their actual period-two sensor lattice. Green contributes its two actual
quincunx sites separately to geometric/sample sums but increments independent
acquisition count only once per frame. The local alias-design Gram matrix uses
noise-weighted accepted sample positions; its conditioning is evidence about
sampling geometry, never a measured resolution label. A native RGB grid needs
four period-two alias columns, a 1.5× grid nine, and a 2× grid sixteen. Green has
two measurements per CFA cell, so requires fewer independent acquisitions for
the same square bandwidth. R/B remain the conservative full-RGB constraint.

The prototype first computes a candidate and its phase certificate on the same
accepted samples. If a channel is under-supported, clipped, poorly conditioned,
outside the registration uncertainty bound, or rejected by focus/motion input,
that channel copies the supplied tested native fallback exactly. There is no
silent wide-kernel blur masquerading as success. Finer output grids require a
caller-supplied native fallback evaluated on that grid; its interpolation is
explicitly fallback only. The positive reconstruction never resizes a gathered
image. Coverage failure of both candidate and fallback remains invalid.

Fallback labels distinguish phase shortage, registration/focus/motion rejection,
clipping/support loss and missing fallback. Report independent frames, accepted
samples, phase condition and model-predicted variance separately. Phase diversity
without optical signal cannot establish or label newly resolved detail.

## Existing phase opportunity: measured geometry, not quality

Command (exit 0, one BLAS worker, 0.17 seconds):

    python -X faulthandler -I experiments/multi-stack-2026-10-28/completion/sr/phase-opportunity.py

Inputs: saved 598-frame full-geometry-2/alignment.json and insect-repeat-7 report;
whole-file hashes are retained in phase-opportunity.json. No RAWs were decoded.
The census uses 31 first-pass anchor scales and nine field locations (279 cases),
then scale-nearest candidate frames from each explicit pass. It does not assume
filename position is a focus value. All 598 sources cover the stored common crop;
277 have some clipped pixels, so the per-pixel pilot must narrow support further.

| Candidate neighborhood | Native RGB condition <=20 | 1.5x condition <=20 | 2x condition <=20 |
| --- | ---: | ---: | ---: |
| First pass, five nearby scales | 80/279 | 0/279 | 0/279 |
| Both passes, three nearby scales each | 175/279 | 0/279 | 0/279 |
| Both passes, five nearby scales each | 240/279 | 13/279 | 0/279 |
| Both passes, nine nearby scales each | 272/279 | 112/279 | 6/279 |

These are optimistic opportunities under a local similar-lattice approximation.
They omit actual local sharpness, motion, clipping, registration uncertainty,
optical bandwidth and radiometric weights. The first useful real target is 1×
color/alias reconstruction; arbitrary finer output remains implemented with
honest fallback and must earn any detail claim. The diagnostic was commissioned
first: a four-point 2D phase grid has condition 1; duplicates have rank 1 and an
x-only walk rank 2, both singular for the four-column problem.

Calibration-grid stacks b05–b09 and high-resolution slide b10–b15 are f/5.6,
ISO100, but periodic targets need local ambiguity checks. The slide has unequal
exposure and tilted variants, so use existing photometry/geometry support and
select unambiguous marked edges. Fabric f/11/f/14 and stopped-down razor edges
are useful optical-lowpass controls, not assumed SR positives. Metadata is in
../../corpus/inventory-table.md; it supplies no phase ground truth.

## Controls and pilot release

1. Flat first: independent temporal noise at several levels and gains, constant
   mean preservation, predicted versus measured temporal variance; duplicate
   content/IDs never count as independent gain. Negative black-subtracted noise
   remains signed. The same-noisy-sample variance-weight foil must exhibit bias.
2. Analytic quadratic and RGB-only sinusoidal/edge scenes evaluated directly at
   physical photosites, with known 2D phase shifts, rotation/scale and pixel
   aperture integration. At native and 1.5× lattices compare direct reconstruction,
   tested native fallback and truth; split true Fourier response from false
   frequency/color residual. No image-resampled plant creates its own truth.
3. Phase negatives: integer-only duplicate phases, x-only shifts, shuffled map
   assignment and missing phases; require local fallback and/or a measurable
   truth-error failure. A 2D geometric gate alone cannot detect shuffled image
   content, so the independent motion/photometric witness must reject it.
4. Optical lowpass: exact low-bandwidth truth. It may denoise but may not be
   labelled new resolution; planted sharpening/nearest-CFA replication must fail
   the truth-residual instrument despite increased high-frequency power.
5. Motion/clipping/active-origin poisons: move one colored edge, saturate a
   negative/positive neighborhood, poison padding, and change actual sensor origin.
   Require rejected samples not to alter admitted output or phase counts.
6. Tiling/resource controls: one tile versus split tiles at identical global
   coordinates, one/four-worker exactness, overflow/over-budget refusal and no
   allocation above the checked 64 MiB operator budget.
7. Root-scheduled real pilot: use saved original-CFA cache and current native
   master on fixed insect/chart ROIs; first verify exact cache/source binding.
   Gate on the common confidence prepass, retain fallback boundaries and an
   ablation with phases rounded/shuffled. Freeze candidate before full output.
   Full complete photographs, float masters and independent same-display review
   are required before photographic gain claims; a crop-only success is not the
   final outcome.

Current state: design/API approved, phase calculation measured, implementation and production-gauge controls verified by root; actual-weight and local-highlight revisions are undergoing checks. No photographic SR gain claimed.

## Prototype freeze and caller obligations

The first scalar operator and 12 synthetic tests are now written in
kernel-reconstruction.rs and kernel-reconstruction-tests.rs. Root must run the
flat-first test separately before the complete suite. Root did so: the flat-first
receipt sr-flat-01 records Compiling strehl-core and exit 0 (1 passed, 11 filtered,
1.14 s test execution), followed by sr-controls-01, exit 0 (12 passed, 1.35 s).
Exact commands and resource receipts are retained under outputs/multi-stack/completion/.
These tests validate synthetic mechanics, not photographic improvement.

The actual signature is reconstruct_tile(OutputLattice, &[SourceView],
FrozenGuide, Config) -> Result<TileResult, String>. Output sensor steps are
continuous within [0.5,1.0] per axis (1× through 2×); candidate sources are capped
at 64, operator plus borrowed confidence/guide inputs at 64 MiB per tile. The
original u16 source cache is external and must be reserved separately. Sources
are processed in fixed order; parallel independent tiles require the caller to
reserve the sum of tile budgets and cap concurrent workers.

Acquisition IDs are caller tokens allocated after full original-content duplicate
rejection, not substitute hashes. Green sample counts and acquisition counts are
separate. The caller supplies R/G/B source pulls composed through the production
optics resolver; channel_pulls is a convenience for the existing composition.

The guide prediction and tensor must be frozen. To claim the reported temporal
variance unconditionally, guide/admission decisions must be independent of the
sensels whose values are fused, or separately characterized with an adaptive
control. If the common prepass uses the same photons for focus/motion selection,
this prototype's sum-of-squared-weights variance is CONDITIONAL on those fixed
weights and is labelled accordingly. It does not price selection bias by itself.
Fallback variance is now optional. Some requires valid propagated variance; None
disables the relative-to-native variance gate explicitly. Fallback channels then
carry variance_valid=false and NaN numeric slots. Reconstructed channels retain
valid conditional injected variance. Test c05 challenges both paths; its root
execution passed in sr-controls-02. No missing fallback variance is replaced with a guessed zero.

The current phase Gram includes every original sample with positive numerical
candidate weight and excludes clipped, uncovered, focus/motion-refused or
uncertain-placement samples. It uses the **actual** weight: Gaussian taper times
injected precision times admission. The earlier available-sample certificate
omitted taper; that historical operator could accept phase diversity carried by
negligible estimator weights. Test c07 preserves this falsifying case.

Physical sigma_sensor is invariant to output grid spacing. A finer output grid
samples the same continuous reconstruction; it does not silently invent a narrower
kernel. Sparse phase sets may now retain the exact native fallback. Dense known-
truth plants verify positive reconstruction without relaxing condition20 or
widening the fallback. Four independent tile threads are compared bitwise, and
coincident output points on native/1.5x/2x grids must have identical RGB and variance.
Finer grids are output sampling unless measured bandwidth evidence supports more.


## First numerical checkpoint and bounded real pilot

VERIFIED: root ran the initial 12 controls with one test thread on Windows 11,
32 logical/16 physical CPUs. Flat-first command:
`cargo test --locked -p strehl-core --example session-reconstruction-controls a01_flat_first_temporal_mean_variance_and_gain_squared -- --test-threads=1 --nocapture`.
Complete suite command:
`cargo test --locked -p strehl-core --example session-reconstruction-controls -- --test-threads=1 --nocapture`.
Receipts: `outputs/multi-stack/completion/sr-flat-01/receipt.json` and
`outputs/multi-stack/completion/sr-controls-01/receipt.json`; elapsed including
Cargo/build was 6.584 s and 2.585 s respectively. Source hashes at that checkpoint
were reconstruction `52d7eedbe25f18db72b901ee7e91b0a444fd69f4750d99e1f2a0f23d7e311b8c`
and tests `d0c39bea170e543607502c6af85200d0dc44e144a8bd7f68e129e1fad51fff10`.
The subsequent optional-variance change is a new source revision and is not covered
by those historic receipts.

The real pilot uses only verified existing original-CFA cache loads; cache misses
must fail and never decode RAW. Whole-track focus evidence streams one source at
a time on a small ROI with full plugin halo, retaining flags from all 299 original
ordinals per pass. Selected reconstruction frames are 148�152 and 437�441.
Separate guide acquisitions 147,153,436,442 are not reconstructed. This makes
guide photon noise independent of the ten scored source images, conditional on
fixed geometry, but focus/motion admission still uses scored photons. The native
master fallback includes those photons and is not independent truth.

The first real pilot assumes 0.10 sensor-pixel registration uncertainty explicitly
for diagnostic inspection. It is not a measured uncertainty or safe production gate.
A measured local residual bound is required before any full-render claim. Scalar
and bounded independent-tile parallel execution use identical per-pixel source
order and arithmetic; image/variance/diagnostic bit comparisons precede timings.


## Production-gauge integration correction

READ-VERIFIED before any photographic run: the first kernel used the array
sample centroid `(width-1)/2` in guide units, whereas align.rs fitting, WarpMap
and NativeSampler use `width/2`. The independent analytic plant had chosen the
same wrong convention, so the initial 12 passing controls did not establish
compatibility with saved geometry. This is a failed integration assumption,
not a failure of the earlier numeric receipts or evidence of photographic gain.

The corrected physical sensor fitting origin is `(width+0.5,height+0.5)`.
Both direct pull and inverse original-sample placement use one `sensor_pull`
primitive. Test c06 retains the old-centre negative. The separate CLI
`gauge-integration-tests.rs` witnesses the actual production NativeSampler on
original u16 linear ramps, with nonzero active offsets, all four CFA sites,
nonzero scale/rotation/translation, optical composition and a cropped domain.
The old centre must produce a >0.5 DN disagreement in this witness. Root verified these controls: sr-controls-02 records 14 passed (1.36 s), and
sr-native-gauge-01 records the independent NativeSampler witness passed (0.01 s).

The geometry-opportunity Python calculation had the same midpoint convention.
Its original JSON is preserved as `phase-opportunity-centroid-v0.json`; rerun
with the exact stored-map origin used one BLAS worker, exit 0, 0.166 s, command
`python -X faulthandler -I experiments/multi-stack-2026-10-28/completion/sr/phase-opportunity.py`.
The tabulated condition<=20 counts above are unchanged, although individual
conditions and probe coordinates change. This remains optimistic geometry-only
opportunity; neither phase conditioning nor tests establish a photographic gain.


## Actual estimator weights and local highlight fallback

DERIVED: kernel-phase-limits.py/json records the continuous Gaussian Fourier
moment G_ij = exp(-0.5*(pi*sigma*(i-j))^2), with separable 2D design condition
equal to the 1D Gram eigenvalue ratio. The old output-scaled sigma had limiting
conditions 29.690 at 1.5x and 434.162 at 2x even with infinitely dense sampling.
Invariant physical sigma_sensor=.35 gives 6.720 and 10.180. This is an analytic
ideal-model calculation, not a measured camera or optical fact. Command:
`python -X faulthandler -I experiments/multi-stack-2026-10-28/completion/sr/kernel-phase-limits.py`,
one BLAS worker, exit 0. Native 1x physical support is unchanged.

Root's frozen diagnostic run01 (binary SHA256
`a39aba70ebc9e3122771172dafb5e88cdcfb5d373b747ba72dc8751392647a07`)
refused at local ROI(27,14) before cache/RAW processing because native highlight
treatment was not invertible. Receipt sr-roi-run-01 retains exit1, 1.712 s and
exact command; no candidate was produced. The revised harness handles this
locally: noninvertible native pixels are excluded from camera-DN reconstruction
and prediction, their fallback variance remains unknown, and their original
scene-linear BT709 triple is copied bit-for-bit after candidate development.
An isolated nonlinear-pixel test ensures neighboring eligible pixels still use
the candidate. The report and native-linear-eligible.u8 expose this mask.

Root sr-controls-03 found 15/16 passing after the actual-weight change. The
remaining a02 bias fixture accidentally reset its quarter-phase location to the
old integer location; its actual-hat condition is about29.6 and correctly fails
condition20. The repaired fixture retains that integer case as an explicit
IllConditioned control and uses the intended quarter-phase location for the
independent-guide mean64 versus same-noisy-sample inverse-variance mean63 foil.
No production threshold or kernel was loosened to make this test pass. New
fixture/control execution and local-highlight control passed: root sr-controls-04 records16/16, and sr-native-controls-02 records18/18 including native gauge and nonlinear fallback. The later complete central ROI was photographically rejected; see central-roi-negative.md for exact evidence and revised focus/coherent-color controls.
