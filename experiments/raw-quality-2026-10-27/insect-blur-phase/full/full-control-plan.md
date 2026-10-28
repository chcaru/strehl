# Minimal native graph commission and complete-photograph gates

2026-10-27, prospective source-only plan. Root alone builds/runs. The fixed
reader passed its prior screen; neither that screen nor this plan establishes
actual placement accuracy. No extra radius, window or confidence variant is
introduced here.

## Native adapter, before candidate graph use

Use root's actual ignored test `fit_and_solve_weevil_phase_maps` under
align_cmd, configured by `STREHL_INSECT_BLUR_PHASE_GRAPH_CONFIG`. Its strict
schema binds executable, observations, held map and original input order;
`mode=replay` and `mode=candidate` share the producing fit/solve helpers.

1. Replay all2340 retained observer pairs, in original order, including
   refusals. Decode saved f32/f64 bit fields, not rounded display strings.
   Preserve each correlated observation's original order and the actual old
   fit centers for this replay. Use `fit_similarity`, the literal existing
   one-pass MAD arithmetic and `finish_measured_map`. Verify every initial/final
   fit, refusal, mask, raw/survivor count and StageFit scalar supplied by the
   saved record; then require the complete native-text map bytes to equal the
   held map. This commissions the adapter without a new NCC fit or RAW decode.
   Do not apply the new centroid convention to old observations.
2. On the same parser, remove a requested pair and separately remove one of96
   tile slots. Both must refuse incomplete input, rather than yield a map with
   silently changed support. Duplicate/out-of-order IDs must likewise fail the
   parser's literal2340x96 contract. A refused tile is a present null with a
   linked detailed reason, not a missing row.
3. Exercise the same fit helper on one fixed asymmetric2-D site population,
   with exact dyadic similarity displacement (for example translation
   (3/8,-5/16), scale increment1/32, rotation coefficient1/64 in guide units).
   Include noncentral sites and the actual quarter-guide offset. Independent
   expected point displacements, rather than the fitted model's own residual,
   must catch reversing dx/dy and shifting only the supplied center by(+.25,+.25)
   guide pixels. The latter can preserve tiny fit residual while changing the
   transform intercept, so residual-only validation has no power. Use a tight
   prospective f64 parameter/placement bar justified by these exactly
   representable f32 observations; do not import a0.1-pixel photographic bar.

The literal existing MAD is upper median of f32 residuals, upper median
absolute deviation floored1e-3, cutoff median+3*1.4826*MAD, inclusive keep,
one refit and at least8 survivors. No generic statistics-library substitute.
Retain f32 residual/RMS reduction and f64 normal accumulation/order. New phase
scores are diagnostics, not NCC probabilities or graph edge weights.

## Actual-reader and candidate contract

Retain all2340x96 requested slots, both physical greens and both phase powers,
including every unavailable patch and refusal. All299 original-u16 cache
identities, active7032x4688 shapes, exact source order, held map and one noise
model are bound. No RGB/MHC, source interpolation, source-volume materialization
or unreported old-NCC fallback is allowed in this measurement.

G1/G2 origins are (2tx+1,2ty)/(2tx,2ty+1), centroid origin+(127,127).
The new fit point Pc is their mean: native(2tx+127.5,2ty+127.5), hence
(tx+63.75,ty+63.75) in guide coordinates. This is(-.25,-.25) guide relative
to the old nominal fit center. Pass (Pc-Cnative)/2 and mean(D1,D2)/2 to the
core. Mean affine displacement belongs exactly at Pc; no held-map slope is
added to the measured vector. Explicitly preserve this center in output.

The held relative map Mj composed with inverse(Mi) chooses integer moving
origins and the declared local branch. Both phases must be individually
accepted and their held-relative residuals agree within0.20 native pixels.
This is a heuristic, not a calibrated confidence interval. No single-phase
fallback, best-power selection, or seed edge is inserted. Candidate compact
rows carry all96 slots as `p1`/`p2` observation or null, joined to detailed
phase/status rows. Cast observation/score values to f32 explicitly before the
native fitting boundary; include finite checks and exact gauge disclosure.

## Bounded sequence and decision

The first actual job uses only the six predeclared pairs in the brief, all96
slots, fixed300s/12GiB host/6GiB Torch bounds. Separate hashing/setup/cache IO,
reader and serialization time; retain all failures even if no useful edges
result. Projection to2340 pairs must include all two-phase/two-power work and
the full source-binding policy; six pairs do not guarantee full cache or graph
coverage. Do not use their results to change the reader or its gates.

Only root releases the fixed full1500s job. All299 placed, adequate connected
component/cycle rank, complete populations and bounded resources are workflow
requirements, not physical truth. A failed graph remains failed; do not close
gaps using the seed map. Baseline/p1/p2 renders use the exact same fixed native
domain, source order,75/75/75/74 chunk fold, CA-off gather, noise, development
and writer. Exact baseline CFA/RGB16/developed-linear payload parity is required.
Candidate support is checked before rendering, without changing crop or adding
synthetic borders. Compare complete photographs and full-resolution masters,
then the ten fixed native witnesses; retain the separate Helicon geometry.
Only visible complete-image fidelity gains justify further transfer checks.

## Pixel-free actual geometry commission

Before the six-pair job, root runs `actual-controls.py --out <fresh-directory>`.
It imports only the SHA-pinned actual-reader module's standard-library helpers;
no corpus pixels, Torch, phase FFT, fit or map solve is executed. A separate
explicit2x2 matrix inverse/composition supplies expected native coordinates.
The fixed cases are identity, a half-lattice tie, unequal scale/rotation and
translation at a noncentral tile, and an unsupported edge tile. The independent
lattice rounding implements floor plus a tie-parity rule, not the producer's
`round` call. Native geometry must agree within1e-9 pixels, with exact integer
origins/support. Reader records synthesized from origin difference plus local
shift pass through the actual two-phase combiner for both powers. Combined
coordinates/displacements must agree within2e-5 guide pixels, allowing only the
declared f32 interface rounding; this is an implementation bar, not a physical
placement confidence interval.

Wrong inverse order, half-sized translation pitch, one-pixel moving origin and
half-native-pixel centroid perturbations must fail those same scorers. A wrong
origin's total displacement also traverses the actual combiner. A refused
phase, absent reader or0.25-native phase disagreement must produce null; an
entirely missing phase must fail instead of supplying a single-phase fallback.
The receipt preserves all positive/negative outcomes, source hashes before and
after, and `quality_claim=false`/`photographic_admission=false`. Any failed
mechanical control blocks the actual-reader job; no new search or threshold
variant is licensed by this commission.
