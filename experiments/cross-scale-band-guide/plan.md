# Signed cross-scale band guide, development revision 1

Preparation, not a measured quality result. The 737-parameter predecessor saw
energy magnitude and smooth brightness/chroma plus their source-set means; it
never saw signed original CFA band coefficients or their relationship between
scales. Its failed fixed recipe remains failed. The separate truth-assisted
oracle constructs a near/far improvement within the existing tiny consumer:
RGB RMSE .785829 times current, with that case's protections passing. Its
seven-case conjunction fails chroma guards, and it is neither a learned model
nor a production-seven-band result. These findings motivate this richer
predictor without claiming that source weights can solve every defect.

The first fit uses ALL 19 retained cases as known developer data, including
the former seven held cases. None remains independent validation. Root permits
at most three documented development revisions and 20 cumulative GPU minutes;
this first fit costs at most 180 seconds. Fresh broader source/PSF/noise cases,
source-count stress, and actual seven-band support are separate work. No RAW
read, native photo render, default change, or photographic admission belongs
to this Python stage.

## Inputs and decision model

All arithmetic and tensors are f32. Per source and AC level, use 30 channels in
the exact order `FEATURE_NAMES` in train.py:

1. Four signed original CFA Laplacian coefficients divided by scale s.
2. Four source-set means and four source-set standard deviations, divided by s.
3. Four normalized signed parent-AC coefficients expanded to this grid by the
   actual finite pyramid expansion; four normalized child-AC coefficients
   reduced by the actual replicated-border [1,4,6,4,1]/16 Gaussian and even
   decimation. Each originating level uses its OWN scale before resampling.
4. The existing Gaussian G/range, (R-G)/range, (B-G)/range; existing
   log1p(E/max(F,1)) and log1p(F); one smoothed headroom feature
   1-max(G,R,B)/range reconstructed from those Gaussian channels.
5. Parent-present and child-present bits, level index divided by six, and
   log1p(s*16384/range).

At each level/location,
`s = sqrt(mean_source,channel(C*C) + (range/16384)^2)`.
Mean and SD summarize scene/focus variation, NOT sensor noise. E and F retain
the injected actual canonical decision-energy calibration. F is not asserted
to be an individual CFA coefficient's noise variance. The Gaussian headroom
feature is NOT a clipped-original-site detector. No aggregate input-hull value
is used as source clipping evidence. Missing child at the finest AC level or
parent beyond the coarsest AC level is zero with its validity bit false; the
terminal Mean is never disguised as parent AC. There is no source index or
ordinal feature, and no temporal-axis convolution.

Three shared 3x3 convolution layers, channels 30->32->32->32, each followed by
SiLU and replicated spatial boundaries, then a 1x1 scalar head: 27,201 f32
parameters. The spatial receptive field is 7x7 at each level, with additional
true cross-scale support from the declared inputs. A source's nonnegative
shared-four-CFA weight is `2*sigmoid(clamp(logit,-30,30))`. The clamp prevents
finite-score underflow from producing an empty denominator; it is a fixed
numerical range, not a fitted admission gate. Zero head produces weight 1
exactly. There is no raw argmax, categorical label, canonical multiplier,
canonical veto, learned RGB, or learned coefficient residual.

## Reconstruction, loss, and selection

The unmodified, pinned learned-band-guide/train.py consumer reconstructs
original source coefficients with the existing /65536 numerator scaling,
terminal Mean, InputRange and final MHC. Its SHA is
`b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987`;
the retained dataset SHA is
`0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19`.
The successful historical native/Python commission must bind both hashes.
The new script cannot silently import a changed reconstruction helper.

Per case, the fixed training objective is camera-linear RGB MSE + 0.5 times
(R-G,B-G) MSE + 0.25 times the mean x/y forward-green-gradient MSE. Add 0.01
times KL(normalized source weights || uniform), averaged over levels and
pixels, only for the four known flat developer cases. Average cases equally,
including differing source counts. The gradient term compares signed
differences WITH truth; gradient magnitude alone would reward manufactured
detail. Chroma and flat terms counter the prior model's colour/noise tradeoffs;
their coefficients are declared before this run, not measured optimum values.

Also add 0.25 times ROI-balanced (RGB MSE + 0.5 chroma MSE), so a small important
feature cannot disappear into the full-image average. Reuse exactly the old
Curved [55,43,135,130], Thin [66,42,130,138], genuine Glint [77,73,100,96], and
Colour [49,43,136,128] source-coordinate windows for their corresponding known
cases. Clipped glint uses Adjacent [127,49,156,134] and Spread [98,69,113,110].
Each ROI divides by its own valid pixel count, then the ROIs within a case are
averaged equally. The clipped-core exclusion below applies before counting;
all other cases have zero ROI term. This is a prospective root-requested loss
correction before any fit, not a change to the retained evaluation windows.

Only `held-clipped-point-glint-n5` excludes the old unqualified GLINT core
[77,73,100,96] in full source coordinates, or [61,57,84,80] after the fixed
(16,16) native crop. RGB/chroma divide by the count of valid pixels and their
channel count. Each gradient direction excludes any edge touching the core
and divides by its own valid edge count. This avoids supervising an explicitly
unrecoverable clipped core as sharp truth. The genuine UNCLIPPED core retains
full weight. Existing adjacent/spread evaluation windows remain unchanged,
including their overlap with the excluded training rectangle. No image-based
threshold or candidate-derived mask is used.

Adam, rate .001, epsilon 1e-8, seed 137; at most 2048 updates, deterministic
CUDA f32 with TF32 disabled. Save and evaluate the declared equal-case objective
at step 0, every 32 updates, and the final completed update. Choose the lowest
saved developer objective, breaking ties toward the earlier step. Save every
candidate checkpoint and score; this is explicit development selection, not
independent validation. Stop requesting updates after 170 seconds, reserving
10 seconds for the last evaluation/save, and refuse if the complete fit exceeds
180 seconds. Record live head/body gradients and objective reduction. A fit
that does not learn is informative failure, not a successful quality result.

## Commission and interface

Root runs `train.py commission|train|infer --dataset D --out O`; training also
requires `--commission C` (directory or commission.json), inference requires
`--weights M`. Predictions use the existing `write_prediction` case/array
layout, so the independent scorer can replay saved weights through the same
commissioned consumer. All 19 source cases remain bound by their blob hashes.

Before fitting, author arithmetic checks exercise odd rectangular corner and
signed samples against an independent 2D reduction oracle, known expansion
phases, zero-head identity, extreme finite negative scores, source permutation,
full source-set replication, sign changes with E/F held, both cross-scale
channels live under a fixed nonzero head, and full-array uniform/prescribed
native reconstruction including exercised hull clamps. Per-case scale arrays
are retained. A mutation inside the excluded clipped core must have zero loss
only in that clipped case; the same mutation in the genuine-glint case must
remain live. These are mechanical checks, not image-quality evidence.
Independent review also commissions gradients and scores; author verification
does not nominate the model.

## Complete native route and principal risk

The eventual actual-native adapter can stream two complete source passes:
first run the existing canonical BandWorker/gather/CA/probe route and accumulate
per-level four-CFA sum and square sum; retain canonical baseline, terminal Mean
and input hull. On the second pass, recompute each source's actual pyramids and
features, score spatial tiles with exact level/filter margins, and inject the
shared four-plane weights through rb-own-guide `add_fields`. Bounded positive
weights remove the need for a source-maximum pass. Storage is O(image plus one
active source), not an N-frame aligned volume. Source permutation/replication
is algebraically invariant; f32 reduction roundoff is tested with tolerances.

The convolution must run as bounded GPU/Torch source streaming or a GPU kernel;
scalar CPU convolution over every complete source is not a credible speed
claim. Existing wgpu support is in experiments/native-gpu-gather. No backend is
built here. A native replay must match original source/gather/coefficients,
preserve Mean/hull/MHC, use exact held development, and show the COMPLETE stack
output before any photographic improvement claim. The small Python N-volume
export is limited to these generated developer fixtures.

Highest risk: synthetic focus/visibility and residual alignment differ from
real minerals and fine hairs. Signed agreement can confuse true differing
depths with phase/misalignment, and source-set moments can lose rare focused
evidence in hundreds of defocused sources. Cross-scale input supplies missing
information; it does not prove occlusion identifiability. Fresh N/PSF/noise and
seven-band cases plus an independently inspected full photograph are necessary.

Prior scope: SYNTHESIS architecture sections retain injected noise, u16 RAW,
gather-at-consumption and bounded working sets. Earlier magnitude-only complex
fusion, XSPEC phase census and categorical source-field failures do not test
this signed, independently per-band learned predictor; their failed recipes
remain closed. The new route does not reopen the refused112/152 fan retouch
target or claim that its source haze has a known clean replacement.
