# Independent native sampler, geometry and caller review

Status: VERIFIED source review, 2026-10-28. No photographic conclusion follows.
This lane authored session-fusion.rs and is not its independent reviewer. Root
and corpus reviewed that consumer. This note reviews their other components.
Only owned Strehl source and the authorized experiment reports were inspected.

## Native sampling

The green guide represents the average of G1/G2 at active sensor (2x+.5,2y+.5).
The sampler's site conversion dx/2-.25,dy/2-.25 is consistent with that gauge;
the full-domain transform center is retained when output is cropped. Its
absolute-sensor ramp oracle uses nonzero odd active origins and a different
coordinate derivation. Source values come from Resampler::sample_checked;
negative black-subtracted values survive until normal final development.

Original-code clipping checks all participating taps, including negative
weights. The nonlinear clamped-cubic hull legitimately inspects nominally zero
weight taps. Lanczos separable factors can be nonzero while a unit two-dimensional
impulse underflows: the repaired control uses constant row/column impulses to
commission factor participation. This is a control repair, not relaxed production
clipping. Zero coverage storage is never a statistical observation.

The Rademacher probe uses known original variance and independent original CFA
sites; it does not fit its own denominator. Identity/quarter/half phases have
analytical variance foils. Review requested the additional split-color-phase
control: R/B identity transfer1 while the two green half-phase transfers and
luma are .25, with maximum-color transfer1. Corpus implemented this as a02 using
an independent seed. This is more discriminating than merely checking max(beta)
against its own array. Root schedules execution and retains its logs.

A spatial-average beta remains an approximation for scale/rotation/optical
phase variation and heterogeneous shot noise. Its observed maximum over colors
is not an upper confidence bound. Four full-domain realizations per source are
a correctness implementation with significant cost, not yet an optimization.
Any cheaper probe must preserve the full coordinate gauge and filter halo and
be compared against this actual source path on held-out seeds/phases.

Review initially raised possible double application of the old fitted optical
translation. Root correctly pointed out that profile_for_capture_env resolves
through applied_form to the RADIAL twin, whose translation is zero. Verified
against optics.rs and its existing tests: this concern does not apply to the
planned production resolver. The arbitrary nonzero profile in a unit test is
valid composition evidence. Still compare radial correction on/off in native
real outputs because changing the gather is independent of grouping.

The initial sampler preflight omitted part of full-source scratch arithmetic.
Corpus added checked sampling_bytes and ProbeMemoryEstimate, plus overflow
controls. Root integrates these before allocations.

## Session geometry

The implementation uses low-resolution scales only to propose direct native
measurements. The delivered map comes from native edges, one explicit-track
solve and an exact reference rebase. Automatic geometry reference does not
supply primary preference. Focus candidates remain explicitly unvalidated;
mutual nearest scale and a quarter-step bar do not establish equal focus, PSF,
rigidity or depth-independent geometry. Tiny scale derivatives refuse the hint.

Review found the first cache binding omitted green-plane and decode sources,
and load trusted serialized candidate indices/flags. Architecture reports both
fixed: relevant owned sources/Cargo.lock are bound, graph/report structure is
validated and focus hints are recomputed from the loaded map/config. A poisoned
out-of-range validated-hint control exercises that repair. Root rebuilds it.

The actual pilot still needs disjoint spatial validation sites chosen before
inspection, spanning depth and distinctive features. Fit RMS and graph cycles
are useful diagnostics but do not establish per-frame placement accuracy.
Keep native plane versus sensor units explicit. Evaluate wrong pairing,
periodic-texture distractors, reversed/unequal ladders and disconnected support.
A large depth-dependent viewpoint change belongs in refused geometry/layers,
not a nominal same-focus fusion group.

## Caller and product semantics

Source hashes are refreshed and duplicate contents refused before index-based
acquisition IDs reach the consumer. CFA channel reordering for the existing
writer is correct. Crop formation includes the site's affine offset and source
optical profile in the full coordinate gauge. Startup-only one-pass routing
preserves ordinary arithmetic and isolates legacy map/cache output.

Review found mixed-aperture Combine admitted unequal linear brightness with
gain1; root accepted refusal to aligned layers until pass photometry is measured.
Across-pass levels/matrices need a shared calibration contract. White balance
is an explicit anchor development choice, because raw sensor values have not
been white-balanced; record each pass's facts rather than claiming equality.
Every frame's lens identity should be checked, not only pass leads.

The primary scope is framing plus fallback on disagreeing matched overlap;
complementary-focus singletons remain useful. User text should communicate that
scope without promising arbitrary appearance preservation in unmatched ranges.
No-primary groups stay symmetric and the automatic reference is geometric only.

The existing binned writer does not emit the requested linear master. Root will
refuse binned multi-pass output until a master-producing path is implemented,
and make ordinary one-pass master availability explicit. Review also found a
stale STREHL_BAND_WORKERS name; the actual execution override is
STREHL_PYRAMID_WORKERS. Root owns those repairs.

Render provenance should bind the resolved recipe, agreement threshold,
resampler, exposure, effective optical coefficients, noise model, anchor writer
WB/matrix and producing build. A geometry cache hash alone cannot reproduce
fusion. Full native-single/native-pooled/native-grouped and legacy photographs,
with fixed development and complete output review, remain required before any
quality claim. Grouping gains must be separated from the changed native sampler.
