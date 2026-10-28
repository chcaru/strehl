# Bounded session coefficient consumer

Allocation: multi-stack-2026-10-28-fusion-core. This is an additive consumer at
`strehl_core::pyramid::session_fusion`; ordinary BandMerge never calls it.
The exploratory API in ../challenge/coefficient-api.md is design history. The
implemented API below is authoritative for integration.

## Implemented contract

1. Create PreparedSource, GroupWorkspace and SessionMerge with the same quad
   dimensions and MergeConfig. GroupPolicy carries Repeat or Combine, optional
   primary bracket ID, and an explicit agreement_sigma (default 4). This bar is
   a heuristic, not a calibrated posterior probability.
2. Prepare one source with SourceKey, four black-subtracted f32 CFA planes in
   [R,G1,B,G2] order, the injected NoiseModel, optional actual-warp band beta,
   full gather/clipping support and a positive photometric gain. Native callers
   use prepare_with_masks with separate green-luma/maximum-color band gains,
   geometric coverage and uncensored eligibility. prepare and
   prepare_with_noise_gains retain their old behavior by passing one support
   mask as both coverage and eligibility. The caller
   gathers directly from immutable original u16 CFA; this module does not
   demosaic or store an aligned source volume. Unsupported samples are ignored,
   including poison NaNs. Supported nonfinite samples are refused.
3. Call SessionMerge::add_source(group, prepared) for each unique acquisition.
   A Repeat group permits at most one source per bracket. Copies and aliases
   must share acquisition identity and are refused across the whole session.
4. Call fold_group to commit and reset the bounded group sufficient statistics.
   finish refuses unfinished groups and returns four CFA planes plus an explicit
   valid mask and diagnostics. Invalid zero storage is not image content: the
   caller must mask, crop or refuse it before export.

Repeat uses an **equal-weight** Welford mean, not inverse-variance weighting:
C = sum(C_i)/n and V = sum(V_i)/(n*n). Variance is propagated separately from the
observed disagreement; disagreement never replaces the injected noise model.
This is deliberately suited to independent same-settings repeats. Accepting a
photometric gain in preparation does not make this an HDR estimator, an optimal
heteroscedastic average, or an automatic saturation-recovery implementation.

Four-color disagreement and its noise bound are smoothed, then the acceptance
mask is eroded over the energy footprint. Agreed means become one focus
observation with absolute group variance and no second beta multiplication.
Rejected Repeat groups contribute the eligible primary's original coefficient
when it covers that coefficient; otherwise all original ordinary contributions
remain symmetric. Combine always supplies ordinary source contributions.
Complementary-focus singletons must not be rejected by comparing their expected
blur with a different focus plane. Group membership still requires a separate
input-only correspondence proposal; the local gate cannot prove focus equality.

Coverage and uncensored eligibility propagate separately through every nonzero
reduction/expansion tap. Statistical agreement and ordinary focus evidence admit
only uncensored coefficients. A separate session accumulator retains actual
coverage-valid coefficients, including saturation. Only a final coefficient
without any statistical contribution may use this display fallback: primary
coverage if present, otherwise the symmetric mean of original covering sources.
It claims no noise gain and does not recover clipped information. Applying this
choice before reconstruction avoids final-pixel patch seams and clipping holes.
True absent coverage remains invalid after full reconstruction support.

Original level-zero values supply the hull, with uncensored bounds preferred
where available. First uncensored coverage resets earlier censored bounds; later
censored sources cannot widen a strict bound. Coverage-only bounds are retained
where no uncensored input exists. This prevents clipped sources from changing a
strict overshooting reconstruction through its final clamp.

## Deliberate approximations and resource scope

Each source retains the existing beta times Gaussian variance approximation.
The native API accepts a separate maximum-color beta for the color veto because
green-luma phase attenuation need not bound individual color noise. The legacy
prepare wrapper reuses one beta. The native sampler's actual-path noise controls must
commission this approximation; these controls cannot establish exact spatial
covariance or independence of fixed-pattern errors. Data-dependent admission
also means the frozen-membership variance is not conditional confidence.

Call workspace_bytes(width, height, config, policy) or MemoryEstimate::estimate
before image allocations. Checked preflight reserves all three workspaces plus
the larger of finish/reconstruction output or the uncached BandGain white-noise
probe. The detail struct exposes each reservation. Overflow and unsupported
configuration refuse without allocating image fields.

Memory scales with image area, not the number of sources or group size. One
PreparedSource, one GroupWorkspace and one SessionMerge are sufficient for serial
streaming. buffer_bytes reports numeric and mask allocations, excluding allocator
and collection overhead; GroupWorkspace deliberately reserves an extra full f32
field, so it is a conservative buffer bound. The caller must additionally budget
source gathering, native cache/decode, demosaic and export. The checked estimate
already includes finish reconstruction; individual buffer_bytes methods do not.
No GPU execution or measured performance claim is made here.

## Verification status

VERIFIED by root-scheduled test execution: outputs/multi-stack/checks/
fusion-flat-1.log records an actual strehl-core compile and the independent flat
control passing before the detail controls. fusion-suite-1.log records all ten
inline tests passing. The logs themselves do not embed the invocation; root
retains the command receipt and no command is reconstructed here.

The first control measures temporal residual variance and bias against the known
flat mean. Other controls exercise duplicate rejection, one-source roundtrip,
unfinished-group refusal, color-only drift with explicit primary, symmetric
ordinary fallback without primary, shifted/blurred edge rejection, poisoned and
clipped support, missing primary, gain/beta variance scaling, ordinary Combine
comparison, original source hull and unsupported recipe refusal.

Root reports fusion-suite-2.log passed twelve tests, including the eleventh
control: distinct color beta must change
color-only agreement/fallback while leaving luma variance unchanged; reusing the
smaller luma gain is the deliberately wrong arm. Nonfinite color gain refuses.
This tests routing, not physical kernel calibration. A twelfth control
counts capacities of actually allocated pixel buffers independently of planning
formulas, covers primary/no-primary and truncated/odd pyramids, and exercises
size overflow and invalid-policy refusal without allocating huge buffers.

Root then reports fusion-suite-3.log passed fifteen tests after compiling the
dual-mask implementation. Added controls preserve a bright clipped spot without
pyramid holes (unclamped reconstruction), retain all-censored display values
without statistical counts, prefer strict evidence from another group over a
censored primary, preserve symmetric/primary fallback under source/group order,
keep true missing-coverage poison invalid, reject eligibility without coverage,
and preserve old wrapper bits when masks agree.

A sixteenth test awaits root execution: crossing sharp edges first produce a
real clamp-sensitive overshoot, then an entirely censored bright source must not
widen the strict hull or change the bounded output in either arrival order.
The one-byte-per-pixel preferred-hull mask is included in preflight.

These author-written synthetic tests commission mechanics. Independent review
of the estimator, correspondence and null remains distinct. They establish no
photographic gain and replace neither complete real outputs nor independent
native-crop inspection with identical display transforms. Parent schedules
legacy single-stack regression, actual native-sampler noise controls, real
native-single/native-pooled/native-grouped comparisons and the optimization pass.
