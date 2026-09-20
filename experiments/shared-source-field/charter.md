# Fixed shared-source field and whole-AC replay

2026-09-19. Root owns execution; new_captures owns implementation;
full_context_placement owns independent choices and controls. This charter
author does not execute or verify the candidate. One generated screen may
admit one complete70-frame vitamin-C baseline/candidate pair. No manual donor,
ROI, corrected-tail coordinate, parameter sweep or automatic promotion enters
the algorithm. The rejected boundary-wavelet result remains rejected.

## Scope and hypothesis

Late sources contain real bright fan structure that independent band weights
can prefer. Test whether one spatially aggregated categorical source-cost field,
replayed coherently across reconstructed AC and all four CFA planes, reduces
that error without erasing cores, true colour or other-depth thin structures.
The corrected donor oracle establishes local headroom, not an automatic rule.
Helicon B is a photographic comparator, not this algorithm's specification.

Reuse the actual current gather/CA, injected guide variance and per-frame beta,
canonical baseline chunks, original u16 storage, f32 arithmetic, pyramid sizes,
terminal mean base, InputRange hull, final MHC and developer. No wavelet change,
new noise probe, aligned-frame collection or RGB re-estimation is required.
Implementation is test-only and default-off. Ordinary production calls remain
unchanged.

## Exact source evidence

On the actual consumed quad domain, after each `BandWorker::fold`, access the
current `FrameWorkspace.luma.level(0)` and `FrameWorkspace.var.level(0)` through
a small feature-gated child of `strehl_core::pyramid`. The fields are retained;
`ws.sq` and `ws.weight` are NOT finest-band evidence after the call, because
later bands overwrite them.

Recompute only `E = smooth5(L0 * L0)` using the existing production kernel.
Use `F = cfg.gate * BandMerge::beta_for(&merge.gain, frame_beta, 0) * max(V0,0)`
with that multiplication order and the existing measured-beta fallback. F is
NOT additionally smoothed. This is exactly the current finest-band evidence,
not an independent variance model. See `pyramid.rs::add_frame_with_gain_impl`,
`native-correction-variance/core-bridge.rs`, and `BandWorker::fold`.

For each source k and output quad p, define f32

```
r[k,p] = max(E[k,p] - F[k,p], 0) / max(F[k,p], 1)
rmax[p] = max_k r[k,p]
D[k,p] = 1 - r[k,p] / rmax[p]     if rmax[p] > 0
         1                       otherwise
```

Require finite nonnegative E/F/r, and finite D in [0,1] (clamp only the last
division's roundoff to this interval). The 1 is the existing one-DN-squared
floor convention, not a new sensor calibration. This preserves relative
above-floor focus response; it does not turn it into a probability.

**Pre-execution amendment:** the earlier review suggested
`(E-F)+/(E+F)`. That saturates distinct high-SNR sources near1, so a fixed soft
width can treat materially different sharp responses as equal. Normalize the
existing unbounded excess/floor ratio across sources instead. An independent
strong-signal ratio control must distinguish these two choices. No candidate
output existed when this amendment was made.

## Fixed categorical aggregation

Hold one common guide `J[p] = 0.5 * (baseline_G1[p] + baseline_G2[p])`, using
the actual collapsed, InputRange-limited, black-subtracted CFA planes before
WB/development. Do not use a different guide per source. For neighbouring
quads p and q define

```
g(p,q) = abs(J[p]-J[q]) / (abs(J[p])+abs(J[q])+1)
P(p,q) = 0.25 / (1 + (g(p,q)/0.05)^2)
```

The constants0.25 and0.05 are fixed heuristic cost/edge scales, not optical
measurements. No guide normalization or scene-fit parameter is permitted.
The +1 has units of guide DN and only stabilizes the black denominator.

Use exactly four scanline paths, in fixed aggregation order: left-to-right,
right-to-left, top-to-bottom, bottom-to-top. At the first pixel of a path,
`L_r(p,k)=D(p,k)`. Else, with predecessor q:

```
m = min_j L_r(q,j)
L_r(p,k) = D(p,k) + min(L_r(q,k), m + P(p,q)) - m
A(p,k) = sum_r L_r(p,k) - 3*D(p,k)
```

This is four-path Potts cost aggregation, NOT an exact global-MAP solver.
Different source labels all pay the same transition cost; never average frame
indices or penalize a numerical frame-index distance as metric depth. Minima
are value reductions; choose lowest index only for a diagnostic tied argmin.
Path start/end semantics apply on every row/column without wrapping/padding.
Parallel rows/columns may be used, with fixed per-output arithmetic order.

## Fixed soft memberships and local fallback

Let `tau=0.125` and `H(t)=u*u*(3-2*u)`, where `u=clamp(t,0,1)`.

```
amin[p] = min_k A(p,k)
v[k,p] = max(0, 1 - (A(p,k)-amin[p])/tau)
w[k,p] = v[k,p] / sum_j v[j,p]
dspread[p] = max_k D(p,k) - min_k D(p,k)
alpha[p] = H((rmax[p]-1)/3) * H((dspread[p]-tau)/tau)
q[k,p] = alpha[p] * w[k,p]
```

`alpha` is **evidence activation**, not calibrated confidence or proof of
ownership. It is exactly zero when local rmax<=1 OR local raw-cost spread<=.125;
it reaches full activation only when rmax>=4 AND raw-cost spread>=.25. These
inequalities precede spatial aggregation, so strong neighbours cannot turn an
uninformative local green field into evidence. Source memberships remain soft;
there is no hard-argmax image arm and no requirement to select one source.

**Pre-execution amendment:** use raw D spread, not aggregated A spread, for
activation. Otherwise spatial propagation itself could activate locally
equal-cost green evidence. Two equally good depths plus a poor third source
still have large raw spread and can activate: that is an explicit adversarial
control, not a hidden claim that this fallback recognizes multimodal depth.

Weak-colour-only structure with uninformative green must retain its baseline
through this fallback; this candidate makes no claim to recover colour that
the baseline already missed. Genuine red/blue texture near conflicting green
depth can still be damaged and must be truth-tested. A coherent wrong field
must be able to fail the screen.

## Exact image consumer

Use the existing `SpatialDonor` reconstruction order from
`donor-consistency/spatial-donor.rs`, with a new streaming membership interface.
For each currently gathered source and each of [R,G1,G2,B], build the existing
Laplacian pyramid, set only its terminal base to zero, and collapse to obtain
the full-domain source AC. Accumulate `S_c[p] += q[k,p]*AC_k,c[p]` in canonical
source order. No per-band reweighting, source-specific mask pyramid, or warped
RGB frame volume is introduced.

Let Bpre be the actual normalized baseline reconstruction before its final
hull and BAC its reconstruction with the terminal base zeroed. Finish with

```
out_c[p] = Bpre_c[p] + (S_c[p] - alpha[p]*BAC_c[p])
out_c[p] = clamp(out_c[p], actual_source_min_c[p], actual_source_max_c[p])
```

At alpha=0 use the actual baseline post-hull value verbatim, avoiding new
arithmetic. If alpha is everywhere zero/off, call the actual baseline finish.
Keep a streamed sum of q and require agreement with alpha within8e-6 absolute
(f32 normalization/accumulation only); refuse nonfinite or negative membership.
Use alpha in the subtraction, so the consumer contract is fixed independently
of last-bit accumulation order. The terminal mean-base coefficient array is
unchanged. Verify reconstruction/base accounting with tolerances on the
actual consumer; do not claim subtraction/readdition is universally bit-exact.

The candidate then uses the unchanged actual four-plane writer and held tone,
WB and matrix. Every source index is eligible; none is a prescribed donor.

## Bounded layout and APIs

Use two contiguous f32 scalar volumes, pixel-major with index `p*N+k`:
the first initially stores r and is normalized in place to D; the second is
the accumulated path cost and later overwritten in place with memberships q.
Retain only O(P) rmax, raw-spread/alpha, common guide, denominator/coverage and
four AC sums, plus O(N) path state per parallel scanline. Do not store four
direction volumes. Release D after memberships are formed and hash any
diagnostic cost summaries before overwrite. Retain no N-source image, source
pyramid or AC volume. All arithmetic/storage here is f32, not f16.

DERIVED for the fixed full domain P=3460*2306=7,978,760, N=70: each scalar volume
is2,234,052,800 bytes; both are4,468,105,600 bytes before other buffers. This
prototype is bounded to70 sources and this domain, not a new O(1)-in-N product
claim. Checked multiplication and a whole-process16GiB ceiling are mandatory;
canonical baseline chunk planning must remain unchanged. Release baseline
worker scratch before allocating the second volume where possible. Root owns
the resource/time limit and can refuse a full job on cost.

Suggested concrete interfaces (minor Rust ownership details may change before
source freeze; numerical contract cannot):

```
core::finest_evidence(merge:&BandMerge, ws:&FrameWorkspace,
                     frame_beta:Option<&[f32]>) -> Result<Fields{energy,floor}>
CostVolume::new(width,height,frames) -> Result<Self>
CostVolume::set_source(index, energy, floor) -> Result<()>
CostVolume::normalize() -> Result<RawCosts{costs,rmax,spread}>
aggregate_costs(raw_costs, common_guide,width,height,frames) -> Result<Vec<f32>>
memberships(aggregated_costs:Vec<f32>,rmax,raw_spread,width,height,frames)
    -> Result<Memberships{pixel_major_q,alpha,evidence}>
Replay::new(sizes,alpha) -> Result<Self>
Replay::add_source(membership_slice,actual_gathered_planes4) -> Result<()>
Replay::finish(actual_baseline_merge,workspace) -> Result<Vec<Vec<f32>>>
compare_generated(frames,transforms,crop,noise,cfg,mode:Off|SharedPotts)
    -> Result<Comparison>
```

Generated inputs are original u16 frames with nonexistent paths, <=70 sources
and <=512native pixels per axis, exercising actual BandWorker/gather/probe.
Nonflat quality cases remain <=16 sources;70 sources are allowed only for the
flat control that exercises the source-count dependence of the maximum.
Expose baseline/candidate planes and linear RGB, source/guide/variance hashes,
beta, actual reached level sizes, alpha/membership summaries, fallback counts,
and source immutability evidence. Independent controls need direct pure cost,
path and membership entry points plus the same replay accumulator. Full adapter
comes only after the generated screen admits; it reuses the held actual map,
crop[28,19,3460,2306], all70 original sources, CA and tone. Freeze full config
and retain complete baseline/candidate RGB16 with exact baseline pixel identity.

## Independent rejection before one photograph

The independent plan owns fixtures and must be frozen before execution. Reuse
existing u16 actual-consumer truth/noise fixtures rather than building another
physical simulator. Run flat first. Commission literal small categorical
paths, source-label permutation, ties/soft averaging, high-SNR ratio ordering,
local alpha0 despite strong neighbours, exact off/zero baseline, all-ones AC
witness, shared4/base/hull, and source immutability. Exercise fractional gather
and crop origin through the existing injected floor, not a private estimator.

Quality must include compact-core/late-fan truth, a genuine late-focused radial
pattern, thin crossing detail at another depth with equal mean green, and
green-absent genuine colour. Require live memberships and an exercised wrong-
source destroyer; an unchanged candidate cannot earn admission. Retain the
existing <=1.10 baseline RGB-error guard, >=90% truth-capped baseline component
retention where baseline recovery>=.5, and <=1.25 baseline flat RGB/chroma error.
The predeclared core/fan case must improve truth error by at least5% at each
tested ISO while retaining its compact core; flat-only gain is insufficient.
The baseline-preserving weak-colour branch is not newly required to recover
90% of a focused source that the baseline itself cannot recover. Disclose that
scope, rather than claim the older absolute weak-colour screen passed.

If admitted, root runs exactly one complete vitamin-C pair. Independent native
review judges both dark branches, facet core, nearby different-depth structure,
transition/flat fields, and full output against baseline and held Helicon B.
No new donor coordinates, image-conditioned penalty, or parameter rescue is
allowed. A negative photographic result closes this exact rule.

Prior constraints: `BUILD-ELECT.md` sections11–16 (coherent wrong-depth collars),
`BUILD-BLEND.md` (hard-join avoidance, coarse-energy ambiguity), `M13` and the
rejected radius32 fine pool (depth borrowing), `M65` (labels versus consumed
admission), `M63`/`M96` (peak/coherence is not ownership), `V-DILUTE` (do not fix
imagined dilution), and the closed source-concentration radial/124-track scan.
No calibration, PSF, SOTA, or performance claim follows from this charter.
