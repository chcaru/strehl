# Next bounded check: natural boundaries through the actual rounded gather

**Source review and design only, 2026-09-19. No candidate, RAW decode or new
measurement was run.** The complete identity screen admits a composed check;
it does not yet admit a full photographic replay.

## The consumed samples really are interpolated

**VERIFIED by source:** `rounded` names intensity quantization, not rounding
the geometric pull to the nearest photosite. The current GPU path is:

- `experiments/native-direct-planes/implementation.rs:71`,
  `warp_frame_fullres_into_planes`, dispatches the actual rounded GPU sink.
- `experiments/native-gpu-gather/integration.rs:65-80` retains active origin,
  stride, normalized WB and gear-guarded composed pulls; `gpu_rounded_planes`
  at line146 unpacks the result at the original crop coordinates.
- `experiments/native-gpu-gather/src/gather.wgsl:56` first computes MHC RGB.
  `gather_one` at line90 uses the fractional coordinate plan's `fx/fy`, the
  four Catmull weights in each axis, and sixteen RGB taps. It then applies
  inverse WB, adds black and quantizes intensity. The sink subtracts black
  and clamps negative signal to zero (`integration.rs:175`).
- The CPU route has the same distinction: full-resolution MHC/Catmull in
  `crates/strehl-cli/src/align_cmd.rs:2210`; quantization and the final black
  clamp in `native-direct-planes/implementation.rs:29-42`.

Consequently, the four retained slots are **known output CFA addresses**.
They equal original photosites at identity; under a fractional similarity they
contain mixtures of original sites, often from several CFA colours. Rotation,
scale and CA need not be separable. Repeated source contributions and rounding
both matter. An alias-only nearest-sensel model would test a different sampler.
The source identity and active-region guards from the passed screen stay.

The existing `gatefloor::Probe::run` (`merge_cmd/gatefloor.rs:274`) is useful
plumbing, not a transferable answer: it injects uniform noise, retains only
green, and measures spatially pooled **Laplacian** gains. Only bands0..3 are
certified there. `luma_variance` is also the green-mean authority, not four
original-site variances. Neither can be applied to the new complex bands.

## One implementation to commission next

**ARGUED recommendation:** an explicitly defined symmetric extension plus a
matrix-free original-source noise replay, initially on a small generated crop.
Keep the actual rounded MHC/Catmull gather unchanged. The fixed small probe
estimate below is the candidate's actual propagated variance implementation,
not merely an offline oracle. Root's subsequent direction accepts testing its
quality before optimizing its cost; no accuracy is presumed from its formula.

For an arbitrary common covered crop of `w*h` quads, choose
`P=next_power_of_two(w)`, `Q=next_power_of_two(h)`. Place it centrally with
integer left/top offsets `floor((P-w)/2)`, `floor((Q-h)/2)`. Extend each of the
four gathered CFA planes by the same half-sample symmetric index map:
`u=i mod 2n; reflect_n(i)=u if u<n else 2n-1-u`. This operates on quad-plane
coordinates, preserving the four CFA phase identities. Record offsets and the
map; inverse and crop using exactly those offsets. A reflected copy is another
use of the same random variable, never an independent observation.

Decompose the extended rectangle completely to one DC coefficient, continuing
one-dimensional transforms if one axis reaches one first. Keep the commissioned
tap order, sum of four WB-scaled energies, shared weights, actual smooth5,
gate2, production exponent schedule for the reached candidate depth, mean
fallback and final native InputRange/developer. No regional LL image is left
as an unconditional mean. The baseline remains the actual product and reports
its reached sizes/exponents; these are not a matched-depth experiment.

This extension is a testable boundary choice, **not** a theorem that edges are
artifact-free. The cyclic join at the padded rectangle can still join unequal
reflected values. Complete support means no finite interior trim removes its
influence. Include full-domain and separately frozen edge/corner truth errors;
a failure closes this fixed extension, rather than widening padding after
seeing the image. Do not substitute uncovered black samples for a covered
crop or silently manufacture valid geometric coverage.

## Noise propagation: preserve the original random variables

Let `G_k` be the actual rounded four-plane consumer for one source, `E` the
fixed extension and `W` the complete complex transform. Obtain the four
per-site variances from the supplied `NoiseModel` at the original active CFA
DN, with explicit stored-plane order `[R,G1,G2,B]`. WB belongs to `G_k` as it
already does; the later all-CFA energy/floor uses the same squared output WB.

Generate independent source-noise realizations **before** MHC, interpolation,
rounding and extension. Each original photosite receives one draw per
realization. Every later use of that site receives that same draw. Reuse the
existing original-u16 injection/load pattern in
`experiments/native-correction-variance/implementation.rs:28,102,209`, but
retain all four consumed planes and run the complete operator. Stream one
pair and accumulated variance fields; do not retain a realization volume.

Fix **eight independent pairs**, sixteen noisy gathers per source. Within pair
`r`, make two independent original-source draws `eta_a,eta_b` and compute
`D_r = W E G_k(S+eta_a) - W E G_k(S+eta_b)`. The floor per coefficient is
`Vhat = sum_r |D_r|^2 / (2*8)`, then the existing smooth5 and squared-WB sum.
For iid inputs, `E |Z_a-Z_b|^2/2 = Var(Re Z)+Var(Im Z)` even through rounding
and clamps. This accounts for interpolation, CFA cross-talk, source reuse and
reflection covariance without a dense covariance matrix. It is an unbiased
estimate of the specified conditional simulation distribution, **not an exact
floor** or new calibration. Do not use antithetic plus/minus draws under this
identity: they are correlated and their difference is a different estimator
for a nonlinear operator.
The assumed signal is the supplied source, and the sensor distribution still
comes from the injected authority. Source quantization and the generator's
distribution must be disclosed and checked independently. Record response
bias against `W E G_k(S)` as well; clipping/nonlinear bias is not noise variance.

In the unclipped linear Gaussian limit, an unsmoothed rank-one coefficient's
relative variance-estimate SD is `sqrt(2/8)=50%`;16 pairs would give35.4% at
twice the gather cost. These are derived scale estimates, not measured
precision for the rounded path. Smoothing and the four-colour sum can improve
precision, but correlated sites do not provide independent samples. Freeze
eight pairs once; do not sweep counts after quality results. Use independent
held-out realizations for the floor check and carry uncertainty. Do not silently
set the floor to an upper confidence limit or fit a correction constant. The
flat, weak-colour and structure controls must detect an inadequate estimate.

For comparison, an exact **linear** treatment would require composing each
complex coefficient through extension, all MHC/Catmull taps and original-site
indices, coalescing paths before squaring. It is valid only when rounding and
clamps are separately accounted for. A general per-pixel covariance engine is
unnecessary, but a supposedly exact separable gathered-plane variance is
incorrect for the actual similarities/CA. Do not implement that shortcut.

## Cost and the full-RAW decision

**DERIVED estimates, not timings:** extension uses `P*Q < 4*w*h` samples for
non-dyadic axes. The current vitamin-C crop3460x2306 would become4096x4096,
about2.10 times its quad area. Four complex current fields plus four complex
sum and mean fields alone cost `96*P*Q` bytes (1.5GiB at4096 squared), before
variance/moment fields, native source/gather buffers, baseline and output.
Keep one current source and one realization workspace; no aligned-frame or
coefficient volume. Bound memory before any full-size job and use one worker
initially; copying the existing worker count would exceed the budget.

The complete transform remains linear-time per frame. The proposed candidate
costs16 additional MHC/gather/transform evaluations per source, while decoding
once. For70 sources that is1120 extra evaluations. That is17 signal/probe
passes per source before reuse, **not a17x wall-time prediction**: decode is
shared, GPU transfer/setup and CPU transform costs differ. Reuse the existing
GPU gather and source allocation; first measure the bounded case's phase costs.
No SOTA-speed claim follows. If the fixed generated quality/variance gates
pass, root can judge one resource-capped photographic prototype on its measured
cost. Future optimization must preserve this implementation's measured quality;
a lower probe count is not silently interchangeable with it.

The immediate code seam is an experiment-only `BoundaryPlan {input_width,
input_height,padded_width,padded_height,left,top}` plus three small helpers:
`extend_four`, `crop_four`, and `probe_variance8`. Generalize the existing
complete transform only to dyadic rectangular sizes and one-axis continuation.
`probe_variance8(frame,warp,domain,noise,boundary,scratch)` returns four packed
coefficient-variance fields. Evaluate the injected original-site variance once;
generate independent predetermined pair seeds, use the same actual `load_frame`
or rounded gather for both members, extend, transform, and accumulate norm
differences. The signal arm uses the same plan and the existing all-CFA weight
loop. Keep original-source hashes, exact dimensions/origins, per-plane model
routing, actual GPU route evidence and diagnostics on/off hashes. No shared
library, production default or general covariance API is needed.

## Small falsifier before more work

Use one generated nonperiodic113x101-quad crop, reflected to128 squared, with
the retained padded active-origin layout and both held ISOs. Reuse the existing
fixed M194c fractional similarity (`gatefloor`'s `variance_warp`) alongside
identity; require genuinely noninteger pull plans and overlapping original
tap support. Freeze no-CA scope explicitly. Keep finite exposure headroom.

Run flat first, one weak true-colour grating, and one broad neutral feature
crossing an edge/corner with spatially varying focus. Score full-domain known
truth, the frozen edge/corner region, and the predetermined focused source;
retain component and flat-noise protections. The coarse feature must carry
energy below the old truncated LL cutoff and actually activate the new coarse
bands. A source-independent noise draw after gather/extension is a deliberate
wrong-path control and must disagree with source-space propagation somewhere
the coefficient really reuses source support.

Independently commission covariance with two preselected noisy original
photosites and exact enumeration of their four balanced +/- amplitude states
through **actual** rounded gather, extension and transform. This has a literal
finite distribution and tests rounding/alias cross-terms without assuming a
Gaussian approximation. Choose amplitudes before running so output code
transitions occur; assert that they did. Separately compare the fixed8-pair
floor against an independent64-realization model propagation check with a
predeclared uncertainty rule; the candidate cannot consume those extra draws.
A floor mismatch, absent overlap, erased coarse feature, boundary
regression or weak-colour regression refuses the extension. Hash outputs with
diagnostics on/off. No original RAW is needed to make any of these fail.

Architecture scope: SYNTHESIS sections3.2,3.4 and3.4.2 require bounded current-
frame work, framework-owned geometry and an injected per-CFA noise authority.
No optical constant or new camera/lens profile is inferred here. Historical
numeric calibration examples in the prose do not override the actual injected
profile used by the current consumer.
