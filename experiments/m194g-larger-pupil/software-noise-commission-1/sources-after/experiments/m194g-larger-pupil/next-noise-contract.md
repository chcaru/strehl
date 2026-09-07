# Prospective software noise and CFA emission contract

2026-09-07, independent design. **DERIVED / UNEXECUTED.** This resolves the
noise-stage choices in `next-quality-design.md`; it is not an execution release
or a physical calibration result. No noise draws, optical calls, reference
images, production outputs or scores were made for this document. Register the
implementation, exact commands and independent controls before drawing.

Prospective review resolution: Curie's `next-noise-independent-review.md`
reviewed the original draft at
`2b34218d04dbac2d89a8efb28d93fc6e504cd400c6ce074dce2e67518798306d`.
Root authorized the explicit trace, pair, replay and bridge choices below
before any draws. The original accuracy, work, time and storage caps remain.

## Inputs and the complete population

Only a genuine complete M194g float commission can supply the five **primary**
320×240 scalar expected-electron arrays for scene `textured`. Bind the actual
commission and array bytes, dtype, shape, original frame indices 0–4, identity
placements and reference index 2. Neither refined/reference arrays nor a
successful subset can substitute. Scene `flat` uses both layers at exactly
12000 electrons with the identical geometry/focus records; its constant
expected array has a powered emitter check below and needs no optical rerender.

Each scene has noise-off plus seeds `[701,709,719,727,733,739,743,751]`:
**18 bundles, 90 active CFA files = 80 noisy + 10 noise-off**. Every bundle
contains original indices 0–4 exactly once. Each file is 153600 bytes, with no
storage padding. Equal flat noise-off bytes across frames are expected; the
file identities still remain distinct. Both later merge modes consume these
same files. No production TIFF or quality score belongs to this emission stage.

## Reproducible stream definition

Use explicit `Generator(PCG64DXSM(SeedSequence(words, pool_size=4)))`, targeting
Python 3.12.10 and NumPy 2.4.4 on the recorded Windows AMD64 environment. Before
the first draw, freeze the actual interpreter and loaded NumPy RNG/core module
paths and hashes, including compiled extensions, and record runtime versions,
machine/CPU information and thread environment. OMP, OpenBLAS, MKL and NumExpr
thread caps are 2 before import; one Python worker runs the stage. An unexpected
version/build/source requires refusal and a reviewed new stream version or
recommissioning. A version string alone is insufficient: NumPy's distribution
stream compatibility also depends on call arguments, build, environment and
machine. PCG64DXSM's stronger fixed-seed integer-stream guarantee does not
extend that guarantee to arbitrary changed Generator calls.
([NumPy compatibility](https://numpy.org/doc/2.4/reference/random/compatibility.html),
[PCG64DXSM](https://numpy.org/doc/2.4/reference/random/bit_generators/pcg64dxsm.html))

For every noisy frame and each component, encode this exact ASCII string with
LF separators, a final LF, decimal integers without leading zeros, and no BOM:

```text
strehl-software-noise-v1
scene=<scene-id>
seed=<seed>
frame=<original-frame-index>
component=<photo-or-read>
width=<width>
height=<height>
```

`component` is literally `photo` or `read`; scene IDs are the two intended names
above or the private names fixed below. SHA-256 these bytes. Interpret successive
four-byte chunks of the digest as eight **little-endian uint32** entropy words
for SeedSequence. Create separate Generator instances; do not use global state,
`default_rng`, schedule-dependent spawning or a shared photo/read instance.
SeedSequence accepts an explicit integer sequence for such stream identities.
([NumPy parallel streams](https://numpy.org/doc/2.4/reference/random/parallel.html))

Bind input arrays separately; their hashes are not additional RNG key fields.
Store each key string/digest, initial/final bit-generator state, actual call
signature/size and sampled-array hashes. State observation cannot draw. Using
the historical seed numbers does **not** promise historical M194b random bytes.
Seed, frame, width and height are genuine integers, never bools, floats or
numeric strings at the typed boundary. Scene IDs must be exact members of the
intended/private lists in this document. Key bytes and the little-endian
entropy words receive an independent deterministic check before sampling.

For each frame, flatten the contiguous float64 photosite means in native order
`t = y*width+x`. Call `photo.poisson(lam=mu_flat, size=None)` once, followed by
`read.standard_normal(size=width*height, dtype=np.float64)` once on the other
instance. No row/tile/CFA subdivision or changed vector size is equivalent by
contract. Reordering whole frames or scenes preserves each tuple's samples;
this is the declared traversal invariance. Noise-off has repeat `null`, no
Generator construction or sampling, and null stream records.
Changing a lambda array while keeping the tuple fixed does not promise
pixelwise Poisson correspondence: the changed vector can consume a different
number of PRNG words. An unchanged read tuple and call still gives the same
normal vector because its generator is separate.

## Sensor law and exact encoding

Native CFA origin is (0,0), RGGB: R at even y/even x, G1 at even y/odd x, G2 at
odd y/even x, B at odd y/odd x. For scalar expected `S`, use float64 factors
`c=(0.75,1,1,0.6)` in that order, including the represented float64 value of
0.6. The emitter consumes this law, without white balance:

```text
mu = c*S
P ~ Poisson(mu)                 # integer photoelectrons
R = 4*Z, Z ~ N(0,1)             # independent read electrons
E = P + R
X = 512 + 0.25*E               # prequantization DN, float64
Q = clip(rint(X), 0, 15360)    # ties to even, then rails
```

Noise-off uses `E=mu`. Encode `Q` as little-endian uint16, native row-major.
Reject nonfinite/negative expected means and nonfinite intermediate values
before conversion. Count `X<0`, `X>15360` and rounded values outside the rails
before clipping; all must be zero for intended emission admission. Preserve a
railed refusal; never censor pixels, redraw or change seeds. Values below black
512 are valid read-noise observations: do not clamp electrons or DN at black.
The product's later black subtraction is a different operation.

The flat noise-off 2×2 block is exactly `[[2762,3512],[3512,2312]]`. Later
production keeps its explicitly injected gain/read model and represented f32
WB `(4/3,1,5/3)`; emitter float64 and product f32 arithmetic are separate scopes.
In raw black-subtracted DN, mean d=.25*mu and variance .25*d+1. Thus the same
gain .25 DN/e and read SD4 e apply to all four planes; do not multiply either
injected constant by c. This is not a post-WB/demosaic/merge variance formula.
There is no profile lookup, fitted noise constant, PRNU, FPN, hot-pixel model,
charge coupling or physical camera-calibration claim.

## Independent commission, fixed before draws

The independent private reader consumes the actual raw draws, consumed
components, encoder input and Q through the trace representation below, not
the emitter's moment summaries. It may reuse an NPY library, but independently
checks array bytes/header/shape/dtype and the encoding equation. Use small
private arrays, not captures or optical calls. This private law commission and
the later intended CFA-file read have different evidence scopes.

**Trace stages and representation.** Name the raw Poisson int64 vector
`photo_draw` and raw standard-normal float64 vector `read_draw`. Name the
actual float64 addends `photo_used` and `read_used`; normally these are
`photo_draw.astype(float64)` and `4*read_draw`. The E, P and R moment checks
below read their actual consumed sum, `photo_used` and `read_used`, respectively.
The c-after-Poisson and cloned-green faults cannot pass by measuring the
unchanged raw draw instead. Record `pre_encoder_x` after the actually selected
gain and black offset, and `x_used` as the actual array passed to rounding.
Normally these are equal. The black-clamp fault changes `x_used`; retain that
changed array and both hashes, so its X moments see the alteration. Keep the
fixed nominal equation as an independent expected law, not a substitute trace.

Each private noisy call retains four NPY arrays: `photo_draw` as `<i8`,
`read_used` and `x_used` as `<f8`, and `q` as `<u2`, all shape [96,128].
The literal trace array keys are `photo_draw`, `read_used`, `x_used`, `q`,
`photo_used_override` and `read_draw_override`. The last two are null normally.
Retain a `<f8` photo override on the c-after-Poisson and cloned-green fault
populations; retain a `<f8` normal-draw override on the zero-read and correlated-
read fault populations. Restored populations use the normal representation.
All four exceptional populations are complete 64-repeat traces.

Bind hashes of actual `photo_used`, `read_draw`, E and `pre_encoder_x` as raw
contiguous little-endian float64 bytes. With null overrides, the independent
reader reconstructs photo_used by the stated int64-to-float64 cast and
read_draw by read_used/4, then requires their exact hashes. Multiplication and
division by this power of two are lossless for these finite normal samples;
the hash is still mandatory and a failed reconstruction refuses. With an
override it reads that actual array instead. Reconstruct E and the pre-encoder
value using the declared active gain (.5 only in its named fault), checking
their actual hashes as well as testing the separate nominal .25 law. Do not
silently infer an omitted exceptional array or exempt a mismatched hash.

Use one closed private-call record with keys `call_id`, `group`, `phase`,
`fault_id`, `observer_mode`, `input`, `streams`, `arrays`, `derived_hashes`,
`rail_counts`, `witness`. The input object has exactly `scene`, `seed`,
`frame_index`, `width`, `height`, `scalar_level`, `expected_scalar_sha256`;
the fixed sampling populations all use constant scalar_level. Streams has
exactly `photo` and `read`, each with `key`, `key_sha256`, `entropy_words`,
`initial_state`, `final_state`, `call`, `draw_sha256`. Call has `method`,
`size`, `dtype`, `lambda_sha256`: Poisson uses method `poisson`, size null,
dtype `<i8`, the actual lambda raw-byte hash; normal uses `standard_normal`,
size 12288, dtype `<f8`, lambda_sha256 null. Raw draw hashes use their declared
little-endian dtype. Derived_hashes has exactly `photo_used`, `read_draw`,
`electron_sum`, `pre_encoder_x`. Each nonnull ArrayRef has exactly `path`,
`sha256`, `bytes`, `dtype`, `shape`, with relative contained paths, file hashes
and fixed NPY containers. Parse bounded verified bytes once, reject extra
payload, object dtype, invalid shape/type, duplicate keys and nonfinite values.
Rail_counts has exactly `pre_encoder_x` and `x_used`, each with
`x_below_zero`, `x_above_white`, `rounded_below_zero`, `rounded_above_white`.
Witness has `sample_calls`, `encode_calls`, `hook_calls`, `collected_events`;
sampling counts remain mandatory in all modes, optional event collection is
count-only. Each noisy call has two sampling calls and one encoding call;
each noise-off call has zero sampling calls and one encoding call. The optional
hook runs once after each of those actual operations in count/placebo and
never in off: three noisy or one noise-off hook calls, with the same number
of collected events in count and zero collected events in off/placebo.
All counters are genuine nonnegative integers. Freeze the enclosing index and runtime/terminal record schema
with implementation before execution; these nested trace meanings are fixed.

All structural read checks apply even to a named fault, including coherence
of the actual saved key, entropy, state and sampled-array hashes. The
prospectively named repeated/shared-key overrides can violate the nominal
tuple law without violating their actual trace's structural coherence. Record
that nominal-law failure separately and continue the promised temporal and
correlation instruments. The omitted-component-field attempt is expressly
different: its original key guard refuses before any sampling, with no claimed
statistical rejection. Once a valid sampled fault
trace is read, retain each named numerical rejection rather than stopping at
an earlier expected law mismatch and falsely crediting an unexecuted variance
or covariance check. Actual fault IDs and stages cannot be inferred from the
values after the run.

**First, deterministic/null controls.** Through the actual encoding seam,
prequantization DN
`[-1.5,-.5,.5,1.5,511.5,512.5,513.5,15359.5,15360.5,15361.5]` must encode to
`[0,0,0,2,512,512,514,15360,15360,15360]`. NaN and either infinity refuse.
Use the literal 4×6 scalar array S(y,x)=1600+80*x+160*y at integer native
coordinates x=0..5,y=0..3, no noise. Its first encoded quad is
[[812,932],[952,788]]. Independently derive every code. Swap actual R/B
photosites within every quad, then restore; separately swap actual G1/G2
photosites, then restore. These are payload permutations, not a relabeling
of the identical green factors. A scalar flat cannot power the latter swap.
Verify the exact flat noise-off block and zero sampling calls before moment
work. Duplicate/missing indices, changed input bindings and a mislabeled reused
frame must fail the complete-population reader, even with newly computed hashes.

**Temporal population.** Fix 64 repeats of shape height 96, width 128 at each
scalar level `S=[0,64,4096,12000]`. Scene IDs are respectively `control-s0`,
`control-s64`, `control-s4096`, `control-s12000`; repeat r uses seed `100000+r`
for r=0…63, original frame 0. At each photosite compute the sample variance
across repeats with denominator 63, then aggregate the 3072 sites of each CFA
parity separately. Never substitute spatial SD or pool differing means first.
For each nondegenerate component, require aggregate mean residual at most
0.02 times its known sigma and temporal variance within 2% of:

| Quantity | Expected mean | Temporal variance |
| --- | --- | --- |
| P | mu | mu |
| R | 0 | 16 |
| E | mu | mu+16 |
| X | 512+0.25*mu | 0.25²*(mu+16) |

At mu=0, P must be identically zero; its variance ratio/correlation are
undefined and cannot count as passes. Thresholds are fixed engineering
acceptance limits, not claimed exact multiple-test probabilities. For scale,
the mean standard error is about 0.0023 sigma and a Gaussian variance-ratio
standard error about 0.0032 in this balanced population; these estimates are
DERIVED motivation, not measured performance or a calibration argument.

Require absolute Pearson correlation ≤0.02 on these exact pair lists. Subtract
the specified population means, then use ordinary centered Pearson on each
list; also retain the sample covariance with denominator pair_count-1.
Keep every scalar level separate and every originating CFA parity separate,
except the explicitly named G1/G2 comparison. Never average correlations.

- Photo/read: (photo_used-mu, read_used), all 64 repeats and all 3072 sites of
  each parity:196608 pairs per level/parity when mu>0.
- Adjacent repeats: component photo_used-mu and component read_used separately,
  pairs (r,t),(r+1,t) for r=0..62 and all3072 same-parity sites:193536 pairs.
  These overlapping pairs are not 193536 independent temporal replicates.
- Green photons: (2*i+1,2*j) G1 paired with (2*i,2*j+1) G2 for i=0..63,
  j=0..47, all 64 repeats:196608 pairs per positive scalar level.
- Read horizontal: (x,y),(x+2,y) for x+2<128, all 64 repeats, split by the
  first site's parity:193536 pairs each. Read vertical: (x,y),(x,y+2) for
  y+2<96 similarly:192512 pairs each. No wrapping enters the reader pairs,
  including when the correlated-read fault constructs its values periodically.

At mu=0 the photo/read, photo-repeat and green-photon correlations are
explicitly undefined; retain that disposition alongside exact zero photons.
All read correlations remain required. Any other zero denominator refuses a
healthy control; record it in a fault without inventing a correlation. The
cross-frame comparison uses all ten distinct pairs i<j of the five frames.
For each pair concatenate the corresponding read sites from three already
retained groups: control-live-a seed701, control-live-a seed709, and control-s0
seed701. Their read laws are all the same zero-mean, variance16 distribution;
this is the sole declared pooling across levels/parities. There are 36864
pairs per frame-pair test, with the unchanged .02 correlation bar. Report the
smaller individual group/parity correlations descriptively, without applying
that bar to their3072-site subsets (whose derived null scale is about .018).
In the shared-key fault, replace only the dark group in this comparison;
retain exact equality of its five read arrays and the combined correlation
rejection. These nulls test named dependence paths, not universal independence.

**Quantization.** At dark, prequantization residual is standard normal in DN.
Independently evaluate `p_0=erf(.5/sqrt(2))` and, for k=1..12,
`p_k=.5*(erfc((k-.5)/sqrt(2))-erfc((k+.5)/sqrt(2)))`, with p_-k=p_k;
sum `k²*p_k` for k=-12…12. Do not subtract two large positive CDF values
already rounded to one. The missing second moment is bounded by
`2*((L+1)+1.25/L)*phi(L)` with L=12.5, below 1e-30; farther rail effects fit
within that bound. This is a truncation bound, not a total floating-point
evaluation-error claim. The continuous normal law supplies the moment oracle;
actual finite-float encoding is separately reconstructed exactly. Require dark
encoded temporal variance within 2% of this
rounded-normal result and mean residual ≤0.02 times its sigma. Require dark
encoded fraction below black in [0.29,0.33] and R<0 fraction in [0.48,0.52],
separately for each CFA parity over its 196608 repeat/sites.

For bright, unrailed rounding error has absolute value ≤0.5 DN. Thus
`|Var(Q)-Var(X)| <= sqrt(Var(X))+0.25` and `|E(Q)-E(X)| <=0.5`; do not replace
either by an exact extra 1/12. The actual statistic uses the mean per-site
64-repeat sample variances vQ/vX (denominator63) for each parity and its two
aggregate means mQ/mX. With a=64/63, require
`abs(vQ-vX) <= sqrt(a*vX)+a/4 + .02*V` and
`abs(mQ-mX) <= .5 + .02*sqrt(V)`, where V=.25²*(mu+16) is the fixed nominal
prequantization variance. The a correction is the finite-sample bound;
the added .02 allowances retain the original prospective engineering slack.
Every unrailed site's actual rounding error must still be at most .5.
These are deliberately broad encoded-moment checks, supported by
the tighter prequantization checks and **exact** independently reconstructed Q
at every retained site. Report actual rounding error/variance movement without
calling it independent uniform noise.

**Replay, observer and stream identity.** At S=12000, shape 96×128, use scene
`control-live-a`, seeds 701/709, original indices 0–4, plus `control-live-b`,
seed701/index0 with the identical expected array. Each changed scene/seed/frame
must change its key/state and positive-noise payload. Original/on/placebo
observers for seed701/index0 and both forward/reversed complete-frame orders
must produce identical tuple-specific P/R/X/Q hashes. Require the on observer
to have reached sampling/encoding counters; placebo reaches its callback but
records no numerical statistic. No observer may request another variate.
At scene `control-s0`, seed701, indices0–4, retain the five read arrays for the
three-group cross-frame comparison defined above. A shared read-key mutation
must yield identical dark read arrays and fail the combined correlation bar.
Omitting the component field must fail the explicit distinct-key guard before
Generator construction or sampling:
do not assume Poisson and Gaussian transforms of a shared seed have a particular
correlation. Noise-off metadata requires a null seed and null streams, never a
successful seeded-noise liveness result. A private forbidden-sampler hook must
remain uncalled through its null/observer controls.

The supplemental noisy calls are exactly the following, each 96×128. Reuse the
already retained baseline files for comparisons, never redraw for a reader.

| Group | Exact calls | Count |
| --- | --- | --- |
| Live tuples | control-live-a, S12000, seeds701 then709, indices0..4 ascending, off; then control-live-b seed701/index0 off | 11 |
| Observer | control-live-a S12000 seed701/index0 count, then placebo | 2 |
| Reordered replay | control-live-a S12000 seed701 indices4..0, off | 5 |
| Dark frame baseline | control-s0 S0 seed701 indices0..4 ascending, off | 5 |
| Shared read-frame key | preceding dark five with read key forced to index0, followed by five restored calls in ascending order | 10 |
| Component-key restored | after the omitted-component-key pre-draw refusal, control-live-a S12000 seed701/index0 off | 1 |

Total 34. The omitted-key attempt requests zero variates. Component key/state
nulls reuse the retained live-tuple companion. Deterministic calls add no
variates: the ten-value rounding vector baseline/fault/restored; three separate
nonfinite input refusals; the tagged 4×6 baseline/RB-fault/restored/G-fault/
restored sequence; and constant12000 noise-off 96×128 off/count/placebo. The
noise-off calls have null seeds, exact code/hash identity, reached count and
placebo hooks, zero optional collection in off/placebo, and zero sample calls.
Metadata faults operate on bounded copies of these retained records, not fresh
sampled arrays. No undeclared random replays or reader resampling fit implicitly
inside the unused variate allowance.

## Fixed active destroyers and restored companions

Each row below runs the complete same 64-repeat private population at its
stated level. Keep the unmodified baseline, then the fault, then a complete
restored replay; restoration must recover every baseline raw-draw, consumed-
component, X and Q hash. No seed selection or threshold tuning follows a
failure. Mutations must intercept the
actual emitter path, with a witness that the changed value was consumed.

| Fault | Level | Required rejecting instrument |
| --- | --- | --- |
| Apply c after Poisson(S), before adding read noise | 12000 | R/B shot variance becomes c²*S instead of c*S; 2% variance gate rejects. Green is an explicitly inert companion. |
| Use gain 0.5 instead of 0.25 | 4096 | X mean and fourfold variance reject; changes are measured before rails. |
| Replace sampled R by zero | 0 | Read and encoded dark variance reject. Keep the draw call so the fault is omission at consumption. |
| Reuse repeat-0 key for every repeat | 0 | Temporal read variance collapses and repeat correlation is 1, although spatial noise remains. |
| Copy G1 photon counts into G2 in each quad | 4096 | Equal marginal laws remain; cross-green photon correlation is 1 and rejects. |
| Replace R_x by 4*(Z_x+Z_(x+2))/sqrt(2), periodic within row | 0 | Marginal variance remains 16; nonwrapping lag-2 covariance is 8 and correlation 0.5. Require variance within 2% and actual read correlation >0.2, rejecting the ≤0.02 null. |
| Clamp X at black512 before rounding | 0 | Below-black encoded frequency becomes zero; dark mean/variance also expose truncation. |

The covariance control's one shared Z term, rather than a desired correlation
label, determines its expected covariance. Read the realized covariance as
well as its marginal variance. Separately activate the fixed shared-frame and
component-key faults above, parity permutations, half-up rounding (512.5→513),
and metadata omissions/duplicates. Every fault needs its named rejection and
an unmodified/restored acceptance; an inert fault leaves that claim uncommissioned.
Sampling fluctuations are retained as failures, not excused by changing seeds.

## Bounded implementation and terminal evidence

Propose two small implementation files: a versioned emitter exposing the actual
sample/encode seam and an independent commission/90-file reader. Reuse frozen
input authority and narrow file-reading utilities where compatible; no generic
certificate framework or product change is required. Manifests bind source and
runtime hashes, exact input authority, scene/seed/original-frame identity, stream
records, all file sizes/hashes, CFA/levels/gain/read constants and rail counts.
Check the exact 90-entry matrix before writes and again at terminal completion.
Paths are relative to the manifest parent, contained there, and unique by file
identity. Input and source bindings must remain unchanged through final writes.

Commission budget: **120 CPU seconds / 240 wall seconds, 32 million requested
photo+normal variates, 32 MiB simultaneously live named array allocations**,
including baseline, faults, restored runs, observers and replay. The 4-level
baseline and seven full fault/restored pairs request 28,311,552 variates;
the 34 supplemental calls request 835,584, for an exact successful sampling
schedule of 29,147,136 requested variates across 1186 noisy calls. Deterministic
and pre-draw refusing controls request none. These are requested samples, not
unobservable internal PRNG word counts. The intended
90-file emission is separate: **120 CPU / 240 wall seconds**, the same array
ceiling, and exactly **12,288,000 requested variates** for its 80 noisy frames.
Record actual work and elapsed time, checking the limit after final persistence.
Caps are engineering refusal limits, not timing claims; do not expand them
silently after observing runtime.

Stream one expected frame and its sampled arrays at a time. Temporal controls
use per-site online moments and bounded pair buffers, never a 64-repeat or
five-frame volume. A reader may hold one previous repeat, or two retained
frames to calculate a declared pair; reopening files cannot draw. Per-site
online means/M2 for photo/read/E/X/Q require 983040 bytes at 96×128; pair buffers
and each owned sample/conversion array are counted separately. Track unique
backing allocations, including cast/copy/serialization buffers where backed
by arrays; no five-frame or 64-repeat array is permitted. Backing-array
accounting is explicit and is not measured process RSS. Retain actual private
traces for independent reconstruction and
moment reads, with a **512 MiB total commission-output ceiling** and a separate
**32 MiB intended-emission-output ceiling**, including metadata and retained
failures in each run directory. Existing read-only input packages are outside
those output ceilings. The private 1186 calls' four base arrays use
378,912,768 raw bytes, and four complete exceptional 64-repeat arrays add
25,165,824 bytes:404,078,592 total. The remaining 132,792,320 bytes under 512MiB
must cover all NPY headers, metadata, source snapshots and bounded negative
fixtures; do not retain redundant full raw/consumed arrays or copy whole trace
packages for each attack. Limit metadata-mutant packages to 1MiB each and 64MiB
in total within that same ceiling. Store all array/record bytes, including
partial failures, in the counted run directory. The cap is checked during
writes as well as after final persistence.

The intended 90 Q files use 13,824,000 bytes. Persist their actual stream states,
raw-draw/intermediate hashes and rail/count receipts, but no full P/R/X arrays
in that 32MiB output package. Full noisy intended traces would require
159,744,000 bytes before metadata and are expressly outside this contract.
The independent intended reader reads all actual CFA bytes, exact population,
source/input/runtime lineage, sample range and saved receipts; it independently
predicts each noise-off file. Its sampled/consumed-law evidence comes from the
full private commission. It must not claim to reconstruct every intended noisy
intermediate or silently perform another 12,288,000 draws. Later quality work
consumes the actual CFA/TIFF data under its own registered scope.

All budgets start once, before imports/setup, and include sampling, controls,
independent private trace reads, persistence and final source/input checks;
none resets at a scene, fault, restored call or observer boundary. Record a
post-write successful budget check; on failure retain the original exception
and any separate cleanup/snapshot failure, with no success authority. Success requires
every declared null, live destroyer, restored companion and complete-file check;
partial files never confer authority. The independently admitted emission then
permits the separately registered production/quality population, not a SOTA claim.

**Later versioned production bridge.** Preserve the frozen M194f reader's
64×48/6144-byte and [512,15360) contract. A separately registered new reader
for these inputs must require 320×240/153600-byte CFA files and the declared
inclusive sample range [0,15360]; below-black values are valid. Intended
pre-clipping rail counts still must be zero, including X>white even if it
would round to white. Reuse only compatible bounded-read/prepared-merge
helpers, not the old schema or hardcoded dimensions. Before production pixels,
commission the actual new source's short/appended/changed-file refusals and
the recomputed plan's cover/crop, reference2, identity frame order, three
Laplacian bands and nonempty measured-floor prefix. Inject four equal noise
pairs (gain.25/read4) and the stated baseline f32 WB, with CameraLinear
exposure0. Noise emission alone does not establish those consumer conditions.

## Prior evidence and limits

Read by content: M194b `produce.py`, `producer-preregister.json`,
`commission-forward.py` and its research report; M194d's fixed weighting report;
M48's measured read-noise/calibration correction; M71 §9's factor-two mistake
in a supposedly planted correlation. M194b drew sequentially from one generator
across frames, so its byte expectations do not apply to these tuple streams.
Its dark-CDF control is useful precedent; this contract does not inherit its
bright extra-1/12 approximation without a separate bound. M71 motivates the
explicit shared-term covariance derivation and actual covariance observation.

Mechanical prior-art search run during design:
`python -X utf8 experiments/ORCH-drift-check/prior_art.py software noise stream emission quantization`.
The selected project sources above supply the relevant conclusions; the search
itself and this document add no numerical noise evidence. A synthetic draw from
the same gain/read constants used in its oracle tests the software law, never
whether those constants describe a camera. Existing physical-calibration and
real-capture acceptance requirements remain unchanged.
