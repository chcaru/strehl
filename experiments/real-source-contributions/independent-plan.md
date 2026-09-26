# Independent source-contribution trace plan

Status: pre-execution design review on 2026-09-25. No RAW job, build, new merge,
or quality result is claimed by this document. The reviewer did not author the
trace implementation. This is a bounded diagnostic of the corrected full
488-source marigold4 merge, not a replacement for a complete-image comparison.

## Question with power to change the next action

The fixed whole-radiance source substitutions already demonstrate two real
hair depths and persistent haze. Another plot showing two source populations
would add no actionable evidence. The question here is narrower: **does the
actual consumer suppress a spatial contrast that is present at these same
addresses in its gathered sources, and can that suppression be assigned to
weighted AC mixing, the separate mean base, or the final input-range bound?**

Actual gathered radiance and signed centre-minus-flank contrasts are recorded
alongside coefficient contributions. Temporal weights alone cannot answer this.
A weak contrast in an original may mean defocus, occlusion, geometry error,
noise or actual absence; neither a maximum over frames nor absolute gradient
energy is admissible as truth or quality evidence. A measured loss relative to
a fixed source witness is local headroom only, not ground-truth recovery.

## Frozen coordinates, temporal partition and gauge

Use the corrected source-pure baseline: native output6268x4176,
reference244, common CFA-plane crop[191,128,3134,2088], native origin[382,256].
The five short spatial profiles in independent-plan.json each contain five
even/even output-native quad representatives, offsets -8,-4,0,4,8 native pixels.
All four actual CFA-plane values must be kept separately. These are not five
individual Bayer colours at one identical optical position. Within-plane
comparisons use the same phase and map; the four plane offsets remain explicit.

Profiles were chosen from already existing unresampled384-native baseline,
source112 and source152 fan views and the existing rim/bud control views,
before any contribution trace was available. The three fan profiles are inside
[3230,3000,384,384]. The protected controls use the existing rim-hair rectangle
[1436,1596,384,384] and inner-bud rectangle[4320,1540,384,384].

The central signed contrast is centre minus the mean of the outer +/-8-native
flanks. The +/-4 samples disclose a missed centre or changed profile shape.
Do not shift centres, choose the best flank distance or maximize over frames
after seeing results. If the prescribed gathered sources do not show a
recognizable local witness, record that witness as inadequate and do not use
it to justify an intervention. These natural regions are not calibrated flat
controls and cannot establish noise neutrality.

Use five exhaustive disjoint source bins:0-79,80-168,169-319,320-400,401-487
(inclusive). Sources112/152 are prescribed near/far witnesses,320 a prescribed
defocused control. No winner or top-source statistic is needed. The bins
have80/89/151/81/87 members; any interval-renormalized diagnostic must explicitly
handle that unequal count. Ordinary contribution accounting keeps the actual
full-consumer denominator and cannot silently renormalize a bin.

## Consumer accounting and compulsory controls

1. Observe immutable actual gathered planes, their actual pyramid coefficients,
   canonical gate/weights, and the final accumulator. Do not recompute an
   alternate focus measure, private noise model or resampled witness. Bind the
   exact ordered RAW identities, plan, crop, threads/chunks, CA, noise settings,
   native gather mode, baseline cache and complete output.
2. Trace the full recursive expansion footprint for each output quad at every
   band, including the terminal Gaussian base. Reading only the nearest coarse
   coefficient misstates what the consumer reads. Record final weighted and
   fallback arithmetic, the numerator scale65536, and fallback activation.
3. Keep unweighted terminal mean separate from all AC bands. Report signed DN
   contributions and absolute DN contribution mass together. Cancelling signed
   contributions have no stable percentage denominator. Absolute mass measures
   activity, not quality, support or probability. Report actual denominator
   shares separately; plain source count alone already predicts the base share.
4. Record pre-hull reconstruction, lower/upper bounds and final CFA. A clipped
   output cannot be linearly attributed to sources without a separately named
   nonlinear clamp residual. A residual of zero does not prove no other error.
5. Reproduce final sampled coefficients using the actual canonical chunk and
   source order, then recompose sampled output CFA through the actual positive
   expansion taps. State exact-bit versus bounded-f32 checks separately. A
   high-precision contribution sum will not generally match f32 bit-for-bit.
6. Prove complete output and cache identity with observer on/off in the same
   held configuration. A zero observer payload or no-op observation is not a
   substitute for an enabled trace that exercises actual addresses and bins.
7. Generated commissioning must include signed cancelling sources, all-zero
   weights/fallback, nonzero terminal mean, a live final clamp and odd/even
   expansion positions. Every case must assert that its distinctive property
   occurred. The closure test must fail when a noncentral expansion tap is
   omitted; a clamp test must fail if the clamp residual is treated as zero;
   a temporal test must fail when one source is assigned to the wrong bin.
   These validate accounting, not real sensor-noise calibration or image quality.
8. Identity, a constant source signal and a prescribed translated/spatially
   altered source must be distinguishable by the signed profile comparison.
   In particular the analysis must not label a uniform brightness offset as
   improved local contrast. A reversal of the hair-like profile must reverse
   the signed contrast, rather than raising an absolute sharpness score.

## Decisions, including nulls

If a fixed focused source has a coherent signed profile and the final merge
attenuates or reverses it, inspect the signed per-band/bin difference and the
clamp residual. Only a specific, counterfactually removable term with the
correct spatial sign can motivate a next treatment. Mere distant-source weight,
source counts or absolute mass are insufficient: distant contributions can
cancel required blur or preserve another real structure. If the actual source
already carries the broad spill and the output preserves its profile, selection
alone is not shown to be the cause. If opposite profile signs or displaced
centres appear across the fixed source neighbourhood, placement/visibility
remains confounded; do not announce a merge defect from an arbitrary donor.

Both near and far witnesses must be retained in any later quality comparison,
plus unchanged rim/bud controls and complete outputs. This trace itself cannot
claim restored detail, cleaner images, calibrated noise or SOTA. If the fixed
sites are inadequate, the trace ends with that limitation; it does not expand
into a spatial, interval or donor search.

## The earlier interval proposal

A read-only search of current proposal and experiment Markdown finds the
80-168 versus320-400 coarse-support proposal only in the September25 diagnosis;
no execution/result record was found. The later full coarse-source prior,
single-source whole-radiance substitutions, optical-support veto and garnet
weighted-base comparison are different interventions, and all remain closed.
In particular source purity failed while retaining haze, so temporal support
cannot be assumed to solve it.

The old fixed interval therefore survives only as a **conditional diagnostic
question**, not an approved new merge or reopened mask/donor sweep. First this
trace must identify a concrete unwanted contribution whose omission has a
falsifiable predicted effect at both real hair witnesses. If that is absent,
do not run the interval arm. If it is present, root may separately authorize one
fixed coarse-only counterfactual with held finest coefficients and held tone;
the wrong interval and protected depths must be tested together. No strength,
mask, endpoint or interval sweep follows.
