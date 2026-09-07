# M194b independent verification, before producer/consumer/scorer results

2026-09-07. Owner `roadmap_audit`. M194 baseline committed at
`19e230fbd44f58badd0959906ae1f1eb5519c60a`; M194b allocated separately in
AGENTS. Read AGENTS, the committed `review-production-truth/forward-model-plan.md`,
M194 review, and existing M25 optical/render/sensor primitives before choosing
these controls. No new producer, consumer or scorer source has been inspected
for expected outcomes yet. No RAW, sealed captures, product defaults, historical
M25 files, scorecard or holdout work is authorized here.

The admission is deliberately separable: a failed numerical optical control
withholds its dependent optical-reference claim. It does not erase successful
flat/noise, coordinate, CFA/color or consumer software checks. The first scope
is flat, one scalar constant-depth textured plane and analytic color. Two-layer
occlusion is outside this first implementation. No real-camera PSF, calibration,
physical-depth, occlusion-halo, image-quality frontier or SOTA claim follows.

## Independently chosen cases and failure inputs

1. **Declared numerical optics, not copied OTF formulas.** Numerically integrate
   the overlap of two unit pupil discs separated by twice normalized frequency,
   and separately the cosine response of a uniformly illuminated defocus disc.
   Use Gauss-Legendre integration of the geometric cross sections, orders256 and
   512, without `acos` overlap formula, Bessel `J1`, `OtfCache.total` or producer
   blur code in the expected calculation. Require quadrature self-convergence
   <=1e-5 absolute and model transfer agreement <=0.002. Include DC, below and
   above diffraction cutoff, and a negative defocus lobe. Zero/double disc
   diameter, absolute-valued defocus response, deleted diffraction and changed
   wavelength/aperture must fail the corresponding check; unchanged controls
   must pass. This commissions only the explicitly declared mathematical model.

2. **Re-choose dimensions and phase.** Prefer a separate 288x192 active sensor
   control, S4 and S8, margin48, physical scale center(157,89), with phases0.73
   and-0.46. Analytic wave frequencies `(1/12,1/24)` and `(1/16,-1/8)` fit the
   full 384x288 margin grid periodically. This differs from the producer's
   benchmark aspect ratio/phase while keeping FFT boundary leakage independently
   controllable. Test only the bounded noise-off component controls, not another
   entire eight-repeat benchmark. The supplied benchmark itself retains its
   registered dimensions, phases, masks and seeds. A half-sensor-pixel phase
   shift, point-sampling instead of finite cell integration, wrong CFA parity
   or omission of the supersampling-dependent center correction must change
   the tested actual samples; evaluate errors at all four CFA parities and
   off-axis landmarks. Finite midpoint quadrature and continuous cell integrals
   are distinct references, with the same registered convergence budgets.

3. **Inspect actual expected and exposed frames.** Require expected-electron
   cache shape/units/phase/content, not its descriptor alone. Independently
   compare constant/periodic signals with the declared model, and read emitted
   little-endian CFA frames. Observing delegate, original exposure path and
   allocated-but-disabled placebo must yield identical raw bytes and restore
   imported function state. Single-channel/frame changes cannot leak to another
   non-spatial axis. Freeze cached arrays before noise repetitions.

4. **Re-choose noise seed, mean and reference.** On cheap96x80 flat arrays,
   use80 independent exposure repeats, seed90217, at electron means0,1024,8192,
   32768. Compare per-site sample temporal variance, pooled separately by CFA
   parity, to the declared affine Poisson/read law. Compute dark rounding
   variance independently from rounded-normal bin probabilities; keep bright
   quantization's1/12-DN-squared term explicit. Require <=2% variance error in
   this independently chosen finite control, with reported estimates/counts.
   The primary benchmark's own registered noise bar remains unchanged. A
   same-mean gain/noise mismatch (`gain*2`, signal electrons/2), removed read
   noise on the dark input, repeated-identical draws, and added correlation0.25
   at preserved marginal variance must fail appropriate variance/covariance
   checks. The matched control must pass; absolute null correlation<=0.02 and
   planted correlation>0.15. No spatial SD of texture substitutes for temporal
   variance. None of these synthetic tests establishes real camera calibration.

5. **Consumer trust and mapping.** A trusted prerecord must bind the full
   nine-frame placement family, reference4, actual preflight Crop, synthetic
   noise/WB/levels and output settings before rendering. A single-best-frame
   comparison keeps that original nine-frame crop and placement gauge. Validate
   actual output dimensions, CFA/black/WB normalization, and the origin mapping
   `canonical_native=output_native+2*crop_origin`. A same-size wrong crop/origin,
   wrong inverse or scale center, endpoint-preserving interior/chord map,
   rehashed frame-content mismatch, or inconsistent metadata must be refused
   by an applicable binding/coordinate check or detected by the independent
   image check; record which mechanism detects each. Do not call a changed
   descriptor's own checksum an external binding. Legitimate copied paths and
   valid padding are inert controls. No public real-reference authenticity is
   claimed by this private test fixture.

6. **Scorer power with independent TIFFs and targets.** Use a separately phased
   analytic RGB target and fixed ROI, writing/decoding actual RGB16 TIFFs as
   needed. Independently calculate the delivered-unit bias/RMSE and temporal
   variance decomposition. A known constant20-DN shift, channel swap, phase
   error and0.6-pixel Gaussian blur of a noise-free wave must move their intended
   bias/color/phase/amplitude component. A flat/no-op/byte-copy placebo stays
   unchanged. Added independent noise increases repeated expected target error;
   sixteen-copy averaging reduces flat variance. A blur may lower noisy MSE, so
   never require every blur to worsen every RMSE. Compare producer expectation,
   ideal latent target, optical observation target and actual single-frame TIFF
   under their distinct names; no output-fitted gain, registration or crop.

7. **Selective admission and final baseline.** Read finite-control outcomes
   before accepting baseline rows, check every requested repeat/scene/arm is
   present, and verify source/manifest/input/TIFF hashes plus exact commands and
   environment. Inspect actual rendered outputs. Record negative/unrankable
   observations without tuning thresholds or hiding failed model scope. A
   combined summary cannot mark an optical/scene part commissioned merely
   because the binary exited0 or flat/noise checks passed. Preserve M194's
   production source and native release baseline; any new sources are test-only
   and separately hashed. No general metric search or candidate tuning occurs
   in this independent commission.

## Coordination and reproducibility

Producer and consumer authors have received the trust/mapping and cache/API
requirements before implementation. Exact callable interfaces and schemas may
be named in a short addendum once exposed; their names are not an acceptance
criterion. Any unavailable independent case, refinement or fixture change is
recorded with its reason before relying on it. Commands must return complete
status/logs; Cargo invocations need explicit rebuild evidence after source
changes. New scripts/artifacts stay in `independent-*`; implementation changes
belong to their assigned authors. This is a bounded verification of one fixed
first-scope benchmark, not a new optical research or capture campaign.

### API addendum, before producer component runs

The producer exposes `build_scalar`, `render_scalar`, `observe_exposure`,
`analytic_color_rgb`, `color_electrons` and `expose_cached`. Its scalar API
preserves the two frozen wave frequencies and applies a common phase offset.
The earlier independent OTF/FFT control already uses the different frequencies
and phases in item2. The actual-producer control instead uses288x192,
center(157,89), common phase shift0.53 (wave phases0.73 and1.63), three frames
with the frozen first/middle/last scales and focuses0/4/8. This is a component
re-choice, not a replacement benchmark. Run S4/S8 and the three observer modes;
compare actual cached electrons to independent finite-aperture pupil/disc
predictions on a fixed interior window, with0.5-DN RMS component budget and the
registered1-DN S4/S8 budget. Analytic-color checks use phase shift-0.46 and
independent continuous cell quadrature. Same-size wrong phase/map/center/CFA
and point/quad-pitch apertures are named rejecting inputs. No benchmark wave,
phase, numerical tolerance or acceptance mask is changed by this addendum.
