# Conditional complete weevil phase-registration comparison

Root continuation2026-10-27 after the fixed40-pair controls passed in9.844s.
The independent receipt audit verifies all214 references and every80 arm error.
No photographic gain is established. This release preserves the frozen reader
SHA99bca095aa6c203ff248184f6c4b08801682565e65c03afabed5e9d5585f9410.

## Fixed changed workflow

This is held-map-initialized direct-pair refinement, not the old coarse
initializer with a larger new search. The local search remains+/-2 native
pixels at1/64native spacing. Both p1 and p2 receive identical original CFA
patches, seeds, window/noise/frequency rules, pair/tile populations, and fitting.
The old map only proposes search locations; never insert its transform as a
measured edge, silently use old NCC for a refused edge, or fit a stationary
correction. This cannot recover a match outside the declared local search and
does not establish that the initial map or final estimates are physical truth.
Any photographic gain belongs to this complete changed workflow; a p2-specific
causal claim also requires its p1 full-image comparison.

Reuse all2340 requested pairs and all96 original fine-grid tile slots from the
retained observer, including every original refusal and short/long span. The
actual input is original u16 cache7032x4688, exact ordered299 source identities;
no original capture write or new RAW decoding, no MHC/RGB guide, no source
interpolation and no aligned-frame volume. Retain all p1/p2 and G1/G2 records.

For source-i tile(tx,ty), physical first-sensel origins are G1=(2tx+1,2ty)
and G2=(2tx,2ty+1), sample centroids c=origin+(127,127). Native map convention
is M_k(x)=C+A_k*(x-C)+2b_k, C=(3516,2344). The direct proposal is
S_ji=M_j composed with inverse(M_i). Choose each moving origin as its physical
phase offset plus twice round-to-even((S_ji(c)-127-offset)/2); reader seed0.
The resulting held-predicted patch remainder is within[-1,+1]native per axis.
The fixed+/-2 search is about this integer-origin correspondence; its allowed
correction relative to the fractional held prediction is[-2-remainder,2-remainder].
Retain these bounds explicitly rather than claiming a symmetric correction box.
Total measured D_p is moving-origin minus reference-origin plus local patch
shift. Require both G phases accepted and the Euclidean difference of their
seed-relative residuals D_p-(S_ji(c_p)-c_p) <=0.20native pixels. No single-phase
fallback. This agreement is a heuristic, not independent physical validation.

The combined observation is at the exact mean physical centroid
Pc=(c_G1+c_G2)/2, with mean displacement D=(D_G1+D_G2)/2. Pass
ux=(Pc-C)/2 and dx=D/2 to the existing core similarity fit (and y likewise).
This averaging is exact for any similarity; do not use the held slope to
transport measured displacement to a different artificial centre. Keep at
least eight paired tiles, the existing one-pass3MAD outlier rule, and refit with
the existing core function. Preserve all initial/final residuals and refusals.

Use the existing unit-weighted measured-component global solve, smooth1/huber1,
reference149, guide3516x2344, Catmull-Rom. Report graph cycle rank and all
unplaced frames for each arm. Preserve pair order and fixed original spans.
Actual fit/cycle/held prediction numbers are consistency, not ground truth.
Commission the adapter by reproducing the exact existing observer map before
using it with new observations, plus physical-centroid/sign/missing-row foils.

## Ownership and bounded sequence

Cfa-residual owns `actual.py` and actual-reader notes. Root owns the thin Rust
pair/global adapter, wrapper/build/scheduling and runtime decisions.
Photo-review owns `render.rs` and render notes, derived from the normal held
BandWorker path described in ../full-render-plan.md. Integration-review owns
independent source and result challenges; authors do not verify their own
photographic conclusions. This allocation currently releases source work only.

After source review root can release one actual six-pair cost/control job,
fixed pairs(0,1),(0,128),(104,105),(148,149),(149,181),(170,298), all96 tiles.
No pair is chosen after seeing new scores. Bound300s wall/1200CPU seconds,
12GiB host and6GiB GPU, fourCPU/oneinterop. Record cache-byte and metadata
preservation, input gauges, source timing separately from binding, and all
outputs even if unusable. This is cost/mechanics, not photographic evidence.

If complete and practical, root can release one full2340-pair job with the same
frozen producer/configuration, bounded1500s wall/6000CPU seconds,16GiB host,
6GiB GPU. The six-pair screen is not a threshold-tuning set. If a supported
all299 map cannot be formed, retain the refusal and do not smooth it away or
discard short edges. Only root schedules GPU/RAW/numerical jobs and builds.

The final comparison uses complete baseline/p1/p2 renders, all299 sources,
fixed native crop(68,46,6896,4596), exact held development and the existing
normal worker's noise gates/probes, arithmetic chunks75/75/75/74, gather and
writer. Remove only historical extra guide arms and their extra16-draw probes.
The exact held consumer uses CPU full-resolution gather with
STREHL_GPU_GATHER=off and STREHL_DIRECT_PLANES=off. Compiled optional paths do
not authorize changing either backend; the phase reader uses the GPU separately.
Require exact baseline CFA/RGB16/developed-linear parity and explicit candidate
source support. A different automatic fusion domain followed by post-cropping
is not an acceptable fixed-domain comparison. Do not inverse-convert the saved
developed-linear TIFF to pretend it is camera RGB.

Root separately sets build/control/render bounds after source/cost evidence.
The legacy renderer's per-source MHC/remosaic limitation remains explicit;
this stage changes native-compatible geometry, not that reconstruction contract.

## Photographic decision

Show each complete JPEG and full RGB16/float master with all ten fixed384px
witnesses and the existing complete HeliconB4/B8 context. Retain more faithful
hair continuity, scale surfaces, color and depth contours without harder glints,
new halos or erased detail. New topology is not required for useful fidelity.
No gradient/phase/cycle score substitutes for this review. The independent
photographer found no demonstrated erased source topology and prefers a
fusion-boundary diagnostic; that dissent remains relevant. Stop this fixed
recipe on a complete null/regression rather than running a radius/window sweep.
Only a complete improvement justifies bug2 and flat60 transfer checks; broad
SOTA acceptance still requires the representative corpus and full workflows.
