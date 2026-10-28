# Independent challenge of the multi-stack proposal

**Proceed with explicit sessions, common-gauge geometry, conservative fusion and
aligned layers.** Repeat denoising is credible. Scale pairing, scalar noise
propagation, FRC and mosaic warps need stronger qualifications before becoming
product guarantees. This review establishes no photographic gain.

Reviewed 2026-10-28 against origin/main c149e52834fc1c86c2af0fe022713c39fa25f33c.
No RAW pixels were opened, no holdout inspected, and no production code changed.
The attached documents are hypotheses. VERIFIED below means inspected source or
primary publications; DERIVED means analytical controls; ARGUED means a proposed
implementation or implication.

## Prior findings that change the proposal

**VERIFIED.** M-FRC-VIABILITY allows commissioning, not admission of its Hann-tiled
crossing as a resolution measure. The later
[M-FRC-NODE-GATE](../../../docs/research/M-FRC-NODE-GATE.md) proves that start/end
witnesses cannot certify interior focus nodes. FocusPosition2/FocusDistance2 were
too coarse. A separately commissioned input-only gate on actual nodes or real
per-node telemetry is needed for the old scientific same-node claim.

[M135](../../../docs/research/M135-detail-instrument.md),
[M167](../../../docs/research/M167-detail-battery.md) and
[M189](../../../docs/research/M189-repeat-referenced-detail.md) reject repeat FRC
as a standalone delivered-detail or resolution instrument. M189 derives the
common post-acquisition blur/sharpening invariance; finite ring pooling has a
residual of either sign. M167's existing implementation gave both scene and
no-scene flat a crossing censored above Nyquist.

Those scientific protocols do not prohibit a product from estimating
correspondence. They prevent calling an estimate proven physical node equality,
or recycling retired resolution claims. Reproducible structure/disagreement is
a useful diagnostic whose shared errors remain invisible. It cannot be the sole
quality gate or automatic tuning objective.

**VERIFIED.** [M-PHASE0-SPLIT2](../../../docs/research/M-PHASE0-SPLIT2.md) failed
the second lighting block's nontranslation gate: 0.107703 native px, independently
0.105202, against 0.10. The light levels were never paired for FRC. This is old
fixed-focus evidence, not a measurement of the newly suggested capture pairs.

## Focus pairing: search coordinate, not identity

**ARGUED from the model and prior geometry results.** Separate breathing tracks
have independent scale gauges. Scale also confounds magnification, distance,
fit bias and lens-state changes. A cross-pass log-scale offset retrieves
candidates, but does not identify PSFs. A nearly telecentric stack is a decisive
counterexample: different focus states can have nearly identical scale. One
offset can also hide nonlinear ladder mismatch. Sony's relative step changes
with aperture and initial focus (M-FRC-NODE-GATE section 4).

Recommended pipeline:

1. Preserve bracket identity, direction and metadata; use separate initial
   solves only for retrieval, followed by a global direct-edge solve.
2. Propose multiple partners using track position, scale and coarse content;
   allow reverse order, skipped/missing nodes and unequal lengths.
3. Match monotone sequences of spatial focus descriptors where supported; hold
   out spatial tiles for challenge. Periodic grids need an aperiodic witness.
4. Report focus intervals/ambiguity and local residuals. Where uncertainty is
   too large, retain distinct complementary-focus inputs or separate layers.
5. Require local signal compatibility before repeat averaging.

A quarter-step threshold is not portable: price scale uncertainty relative to
measured step and refuse when the derivative is too small. Change estimator or
spatial support in independent verification. Score actual per-frame placement
in the anchor gauge, following engineering rule 6/M103, not endpoint fit alone.

## Repeat noise: correct derivation, narrow domain

**DERIVED.** For equal independent observations of one latent value,
v = g*S + (RN*g)^2 and mean variance v/K. The proposal's g/K and RN*sqrt(K)
reproduce this exactly: 229.2080838348 for its example.

It does not describe every proposed mixture:

- For fixed normalized weights, temporal variance is sum(w_i^2*v_i), with
  covariance terms for dependent observations. Three copies of one RAW retain
  full variance; the naive model understates it by 3.
- Exposure gain c multiplies variance by c^2. The control's 1 and 1/4 exposures
  give oracle inverse-variance merged variance 536.6860 DN^2, versus 335.1934
  from the equal-repeat shortcut.
- Weights estimated from the same noisy sample can bias the mean. Disagreement
  gates change the conditional distribution. Use a shared signal guide and
  test mean bias/variance under the actual policy.
- Interpolation creates covariance. Two adjacent half-pixel averages have
  variance 0.5 and covariance 0.25; their difference has variance 0.5, versus
  1.0 from a diagonal-only model.
- Production [gatefloor.rs](../../../crates/strehl-cli/src/merge_cmd/gatefloor.rs)
  already measures warp-dependent band transfer. Its documented beta ratio
  0.3432–0.9981 precludes using one representative warp for a grouped input.

The practical solution is coefficient-domain grouping with absolute band
variance, described in [coefficient-api.md](coefficient-api.md). Do not collapse
a grouped image and rebuild its pyramid merely to reuse a scalar PlaneNoise.
Source independence does not remove DSNU, PRNU, illumination drift or shared
calibration-master error. A rejected repeat must fall back to a designated
reference or ordinary admission, never raw argmax.

## Diverse captures carry different information

**VERIFIED primary art; product implications are ARGUED.**

[Hasinoff and Kutulakos, Confocal Stereo](https://www.cs.toronto.edu/~kyros/pubs/09.ijcv.confocal.pdf)
uses aperture-by-focus data with geometric and radiometric calibration. Its
constancy assumption concerns incoming radiance over the aperture cone; the
discussion identifies texture and occlusion limitations. It supports aperture
research, not exchangeability of differently blurred samples. Keep aperture
layers visible and compare mixed fusion to the better single-aperture output
at threads, bright points and occlusion boundaries.

[Debevec and Malik](https://www.pauldebevec.com/Research/HDR/debevec-siggraph97.pdf)
recover radiance from calibrated exposure changes. Linear RAW fusion needs
exposure normalization, active-area levels and clipped-sample exclusion.
Changing illumination is not automatically HDR: shadows/speculars can move.
Distinguish all-clipped regions from recovered highlights.

[Shape from Mixed Polarization](https://arxiv.org/abs/1605.02066) addresses real
surfaces with mixed diffuse/specular polarization using additional viewpoint and
polarization information. Two arbitrary CPL rotations do not identify complete
components. Preserve aligned layers and label their difference literally; do not
promise calibrated relighting or normals without an acquisition model.

Useful outcomes remain when repeats fail eligibility: complementary focus
coverage where geometry/calibration permit, aligned layer export/comparison,
and per-pass diagnostics.

## Mosaic approximation versus a supported warp

**DERIVED.** Pure lateral pinhole motion gives relative parallax s*dz/(D+dz);
s*dz/D is first order. At D=120 mm, dz=5 mm and s=4922.4 px, exact=196.896 px
and approximate=205.1 px, a 4.17% difference. The arithmetic reasonably illustrates
the problem. Unknown pupil position, occlusion and motion are bigger uncertainties.

**ARGUED.** Same-focus images still contain off-plane blur; broad high-contrast
structure can dominate whole-image correlation. Fit supported in-focus regions,
then challenge held-out positions and slices. A translation curve T(k) presumes
restricted motion and a common focus coordinate; rotation/pupil shifts can
produce spatially varying residuals. Its vector components need not be monotone.
Independent overlap ramps need not close around a multi-tile loop.

Before a depth-aware canvas claim require common-canvas cycle consistency,
propagated depth/pose uncertainty, no unsupported depth extrapolation, positive
local warp Jacobians, visibility/coverage masks, held-out boundary residuals,
and flat-field treatment. Smoothness cannot supply missing geometry.
Untextured interiors may hide error; neighboring boundaries can still reveal it.
Multiband blending can conceal double edges without correcting them.

[Agarwala et al.](https://grail.cs.washington.edu/projects/multipano/agarwala_sig06.pdf)
optimize large perspective regions using a dominant plane; the paper reports
depth-variation limitations and difficulty recovering depth boundaries.
Multi-perspective output is a valid deliberate product, not guaranteed seam-free
geometry. If existing captures are reframings rather than overlapping tiles,
joint layers are supported; a depth-aware mosaic claim is not. A planar-only
mode needs a plane gate that demonstrably rejects a stepped-depth target.

## Super-resolution: informative phases, not frame count

[Wronski et al.](https://arxiv.org/html/1905.03277v2) requires aliasing and distinct
sampling phases and uses direct CFA reconstruction with local robust weights.
It retains failures from ambiguous alignment and small scene changes.
This supports direct-sample fusion research; arbitrary repeat stacks are not
automatically valid SR input.

**DERIVED.** The four-column 2-D 2x alias matrix has rank 1 for four identical
phases, rank 2 for four distinct x-only phases, and rank 4 for a two-axis square.
Count/radius is insufficient. Check noise-weighted conditioning per CFA color
among sources that actually pass focus and motion gates.

**ARGUED.** A nudge may improve color sampling without new luma bandwidth.
Distinguish larger image dimensions from resolved information. Zero motion can
still improve SNR: the control must demand no sampling-derived gain, not no
visual improvement. Existing optical-ceiling disputes and the rejected native
spectral pilot make full photographs decisive.

## Commissioning sequence

Root freezes bars before candidate outcomes. Historical bars are precedents,
not automatic product thresholds.

| Stage | Positive and consumer | Failure/control | Decision evidence |
| --- | --- | --- | --- |
| Session | Single bracket unchanged; track order/identity retained. | Duplicate RAW, stale/reordered cache, prior across boundaries. | Exact fixed-worker baseline and session regressions. |
| Pair/pose | Curved/reversed/unequal ladders; per-frame anchor-gauge poses. | Flat scale, shuffled pairs, periodic-grid shift, disconnected graph, local motion. | Grid/ruler and independent spatial estimator; ambiguous pairs stay distinct. |
| Repeat | Flat independent noise first, then edge/texture; mean bias and temporal variance. | Duplicate, misregistered edge, light drift, shared FPN, wrong noise. | Complete outputs: both singles, ordinary pooled merge, grouped merge. |
| HDR | Known exposure ratio with supported unclipped highlight. | All clipped, wrong black/exposure, moved specular. | Reference-exposure comparisons only where supported. |
| Aperture/layers | Separate outputs and common coordinates; occlusion witness. | Mismatched PSF averaged, guide values leaked. | Full fabric/ruler/razor scenes against better single arm. |
| Mosaic | Flat and stepped-depth overlap; held-out spatial/slice predictions. | Constant-shift foil, wrong depth, loop error, occlusion, no overlap. | Actual overlap and full native canvas; otherwise record limitation. |
| SR | Original CFA colored patterns with independent known truth and 2-D phase. | Zero/x-only phase, shuffled poses, optical low-pass, local motion. | Chart and full subject comparison; FRC auxiliary only. |
| Resources/UI | Same inputs at varied bounded resources; open/edit/reload/export. | Underestimated peak, cancellation partial output, corrupt cache, wrong IDs. | Wall time, peak owned memory, host load and actual UI exercise. |

Independent review changes estimator/reference choices, retains failures, inspects
complete photographs before native witnesses, and uses identical transforms.
A textured flat, depth boundary and complex organic/specular subject are distinct
evidence classes; chart mechanics alone cannot establish the last class.

## Reproduction

Executed from the named worktree:

- python scripts/research.py search focus scale --limit 10
- python scripts/research.py search FRC --limit 8
- python experiments/ORCH-drift-check/prior_art.py repeat focus FRC
- Explicit reads of the cited reports, rule 6/M103, noise.rs::PlaneNoise::variance
  and gatefloor.rs.
- python -I experiments/multi-stack-2026-10-28/challenge/derive-assumption-controls.py

The final command exited 0 on Python 3.12.10; exact result is
[assumption-controls.json](assumption-controls.json). Source SHA-256:
85a1b719154127626cb3bdddb0497d08f02a0159cdc80d757ffbcd3bafc4dc07.
These are analytical counterexamples, not product tests or camera measurements.
Some Windows glob-path searches failed and were replaced with explicit reads.
Only successfully accessed primary papers are used. No prohibited external
implementation source was consulted.
