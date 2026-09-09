# Native sensor transfer: implementation contract

SOURCE-ONLY, 2026-09-09. This is the producer author's implementation contract,
not independent verification or numerical authority. The charter and amendments
1/2/3 govern. No RAW payload, candidate, probe, control, build or test has run in
this source lane. The patch remains outside crates and unapplied.

## Consumer and unchanged policy

Use the actual native path: one decoded strehl_raw::Frame, BandWorker::fold,
load_frame, extract_planes, luma_variance, BandMerge::add_frame_with_gain and
BandMerge::finish. The adapter changes orchestration to stream paired consumers;
it does not implement extraction, filtering, weighting or collapse itself.
The existing M194 production-source seam supplies this access. Its fixture
helper cannot accept real paths (it asserts nonexistent sentinels), and its
all-frame fixture Vec is not reused. The M194h hook is hardcoded to another
population and includes an intervention; it stays byte-for-byte unchanged.

The full source Frame must independently validate active7032x4688 at(0,0),
quad3516x2344, within its actual decoded storage. ONE Crop is quad
(1694,1108,128,128); native active-relative sensor rectangle is
(3388,2216,256,256). Full-native coordinates still govern gathering/CA.
Extraction happens before the compact pyramids. All128x128 sites in all four
planes are retained, R/G1/G2/B offsets(0,0)/(1,0)/(0,1)/(1,1). No residual mask,
crop adjustment, registration fit, or physical prediction is introduced.

Keep MergeConfig::default requested bands7, gate2, exponent2, sharpen1.4,
SoftPower, HardFloor, BaseMean, mean_coarse0, InputRange, hull_lambda2,
hull_low_onlyfalse, Mean fallback, fallback_k3, fallback_power4,
hull_from_level1, significance_scale0. Record actual enum values and every
f32 bit. Current level_sizes produces128/64/32/16/8, four Laplacians plus base;
exponent_at uses actualnb4. This is the opt-in Crop consumer, not default
full-native seven-band certification. All environment-derived defaults must
be explicitly admitted and recorded before OnceLock evaluation.

The noise constructor is profile::noise_model_for -> by_model ->
CameraProfile::noise_model, with Profile provenance and PRNU absent.
For ILCE-7CM2/ISO160 the frozen profile uses actual f32 gain160/436.8 and
read_noise_e4.20 copied to four PlaneNoise entries. Record actual ISO, levels,
gain/read-noise bits and constructor source identity. No measured-gain override,
PRNU, dark subtraction, quantization addend, correction/refit or private stage
noise estimator. luma_variance actually evaluates green_luma_sigma then squares
its result; preserve that rounding, not an algebraically substituted variance.

No-map and placed Similarity::IDENTITY are separate routes. Preserve default
fullres gathering, actual frame.path, gear-guarded CA resolution, WB/MHC scratch
and u16 roundtrip; geometric identity does not assert effective R/B identity.
The charter prohibits a new external RGB consumer, not these existing internals.
Defect policy must be the current default none, with its environment provenance
recorded; no hidden correction. Freeze unset/default CA selection and fullres
on; no white/debug/scaled floor override, restoration, confidence rerender or
other optional diagnostic pass. Record the effective channel maps and identities
where production obtains them; a second inferred resolution is not an actual
map observation. This last read-only CLI location is part of patch review.

## Fixed traversal and observer witnesses

Root adopted this finite proposal; coordinate's independent protocol will carry
the same list. Every row is a separately invoked paired traversal, in this order.
Each decoded original first feeds no-map and then placed-identity through the
same BandWorker::fold. One temporary Frame clone permits those two consumptions;
the original is moved into the second call. Neither full stack nor aligned frame
stack is retained. Maintain two route workers and their existing scratch plus two retained accumulators.
Per-route full-geometry planning, canonical_band_chunks, per_chunk, absorb and
reset ordering are copied from the current native orchestration. Interleaving
the routes does not replace either route's canonical arithmetic with a plain sum.

| Invocation | Original selection | Feature / observer | Native decodes | Folds | Real / probe fullres warps |
| --- | --- | --- | ---: | ---: | ---: |
| 0 | paper235..239 | on / on | 5 | 10 | 5 / 5 |
| 1 | dark872..893 | on / on | 22 | 44 | 22 / 22 |
| 2 | paper235..239 | on / off | 5 | 10 | 5 / 5 |
| 3 | paper235..239 | on / placebo | 5 | 10 | 5 / 5 |
| 4 | dark872..873 | on / on | 2 | 4 | 2 / 2 |
| 5 | dark872..873 | on / off | 2 | 4 | 2 / 2 |
| 6 | dark872..873 | on / placebo | 2 | 4 | 2 / 2 |
| 7 | paper235..239 | off / absent | 5 | 10 | 5 / 5 |
| 8 | dark872..873 | off / absent | 2 | 4 | 2 / 2 |
| Total | fixed originals only | 9 invocations | 50 | 100 | 50 / 50 |

The separate independent decoder needs27 original decodes. BandGain::measure also performs its existing once-per-process/depth
initialization:32 compact256x256 white-field pyramids for actualnb4,9 initializations/
288 compact synthetic fields across these fresh processes. This is separately
priced existing work, not one of the50 full-native gatefloor probes. No invocation reads
an original merely to prepare geometry then decodes it again: its first decoded
Frame supplies the metadata/model/domain prologue and remains the first frame
consumed. Count decoder calls separately from PyramidFrameSource::decode handoffs
(two per original), full native metadata identity reads inside both real/probe
warps (100 total calls expected), and synthetic probe template.clone/fill work.
Prologue/metadata/read failures remain charged and retained; none becomes a free
unperformed decode. Off/on/placebo are not three names for one invocation.

There are18 final route outputs. Compare exact little-endian f32 bits of all four
collapsed CFA planes AND whole native TIFF bytes within paper5 and dark2
off/on/placebo and against their feature-off counterparts. Each f32 payload is
262144 bytes; all18 total4718592. Call existing write_merged on the same
finished Merged::Bands, actual first-frame levels/WB/matrix provenance,
OutputSpace::CameraLinear, demosaic=true, Exposure::None, restore=None.
The native TIFF dimensions are256x256, each capped512KiB;18 reserve9437184 bytes.
These18 writer calls are additional work, but add no fold/decode/probe.
The original measurement writer is reused unchanged, with no external RGB path. The
primary paper/on output is reused as that actual witness, not called another run.
There is no whole22-dark byte-neutrality claim and no no-map/placed equality bar.
A feature-off binary is independently built from the same source set with only
the feature selection differing. Observer failures, partial fold counts and
output failures cannot be promoted to successful scientific traversals.

## Passive observation interface

Core feature native-sensor-transfer adds an experiment-owned include and calls
only after actual weights exist and after production's existing PlaneCache::ensure.
The observer NEVER prepares that cache, mutates weights/config, changes kernel
arithmetic or calls another pyramid. CLI hooks borrow source/prepared ROI and
actual fold inputs. One active frame session associates invocation, original
ordinal, route and local merge-frame index; all lengths/order are fixed, bounded,
and checked. Frame observations are drained before the next frame.

On retains actual arrays, with f32 serialized by to_bits little-endian:
original sensor ROI u16 before defect/warp; prepared ROI u16 immediately before
black subtraction; four consumed clamped CFA planes; actual green luma; injected
variance before and after the merge call; actual supplied beta prefix; all five
luma and Gaussian-variance levels; actual smoothed squared energy and weights for
four Laplacians; actual base weight; and all four plane coefficient pyramids from
the already prepared production cache. The black scalar plus original/prepared
codes permits independently reconstructed signed values; label those DERIVED.

Per-band context records requested/actual depth, level shape, selected white or
per-frame beta, actual beta bits, gate, exponent, significance and bypass/base
labels. Production's threshold is a scalar local inside the parallel weight
closure. A saved floor array is explicitly DERIVED from the recorded exact
operands gate*beta*max(V,0); it is never labelled the original scalar array.
Actual weight bits are the consuming observation. Independent comparison, with
its declared finite arithmetic tolerance, checks their relationship. BaseMean
is not a fifth gated band; no permanently green base/mean-coarse census.

Off retains common source/config/output identities but does not inspect arrays
through optional hooks. Placebo allocates/touches the identical optional shapes
with constants and never reads optional merge state; its zero arrays are labelled
placebo, not observations. Shared mandatory input/output hashes remain common.
All hooks are inert without an active session. A feature-off build contains no
core hook calls. RAII cleanup refuses nesting and prevents stale frame association.

On this crop gatefloor measures min(4,sizes.len()-2)=3 bands. k3 is NOT attempted;
the hypothetical12x12 trimmed population would also be below256, but that is not
the reached cause. No-map supplies an empty prefix; placed identity is expected
to supply three finite entries and k3 uses white BandGain. Preserve actual raw
probe prefix, finite truncation and selected fallback, never fill a desired beta.
A debug option would double probe work and is inadmissible in this fixed plan.

## Source-derived storage and remaining release work

An original ROI is131072 bytes. Per route, prepared ROI131072 plus consumed
planes/luma/variance393216 plus actual core arrays698112 gives1222400 bytes,
before framing/metadata and the second variance hash (no second variance array
required). Core arrays use21760 Laplacian sites plus64 base sites:
L/V174592, E/weights174080, base weight256, four plane pyramids349184.
A2MiB per-route frame record is a prospective ceiling, not measured normal size.
There are58 on folds and14 placebo folds; off frames retain bounded metadata only.
Original ROI snapshots for50 decode visits total6553600 bytes if all retained.
With72 maximum2MiB optional records,18 final plane payloads,50 original snapshots,
bounded per-frame JSON,18 native TIFFs capped512KiB each, and simultaneous
publication stages, a prospective208MiB
producer artifact lane is proposed for root's later finite ledger.
Independent-slot sum:72 traces*2MiB=144MiB;72 prepared ROIs*128KiB=9MiB;
50 original ROIs*128KiB=6.25MiB;18 collapsed planes*256KiB=4.5MiB;
18 TIFFs*512KiB=9MiB;100 frame JSON*64KiB=6.25MiB;9 each initial,
success and refusal JSON*64KiB=1.6875MiB. Subtotal180.6875MiB.
Nine possible orphan stage slots*2MiB add18MiB, giving198.6875MiB
(208338944 bytes), below208MiB(218103808) by9764864 bytes.
This charges all independent failure slots, without assuming a stop after the
first failure. The2MiB trace cap is separate from prepared ROI and JSON caps. No runtime
allocation or artifact ceiling is authorized by this source contract alone.

At the inherited full geometry, two WarpScratch objects reserve148347072 bytes
(src/dst f32 plus bool); two7168x5120 u16 Frame buffers add146800640; the four
simultaneous native MHC scratch planes add527456256. Sum822603968 bytes excludes
decoder/library memory, row scratch, allocator/threads, compact merges and observer
buffers. It is a source-derived live envelope component, not a measured peak or
proof1GiB is enough. Propose at least2GiB owned memory for later review; CPU/wall
must price50 real gathers plus50 probe gathers, not100 cheap128-square folds.
No automatic retries, added ROIs, full-frame pyramid or27*6 traversal.

Pending before execution: exact applied-source review/reverse proof, adapter
and hook metadata layout, independently fixed nuisance/control protocol, complete
source/binary/environment/command freeze, source-selected control power and an
owned-process/resource ledger. Root releases those separately. Independent operator reproduction is a software check; neither it nor exact
same-file decoder agreement establishes physical sensor calibration. No claim here of
complete native DLL closure, sensor calibration, physical stationarity, quality,
real alignment, restored M1/M2 evidence, or SOTA.

Preparation scope64MiB source/report reads,4MiB new retention,60CPU/120 active
process wall. The explicit12-file pin pass read883974 bytes; earlier source reads
were additional and not globally instrumented. Exact cumulative CPU is unknown;
the finite lane remains charged. Harmless source-navigation path/glob refusals
did not open RAW or run candidate code. No live crate or historical artifact
has been edited. SYNTHESIS architectural record and the charter's existing prior
query/report triage were read/reused; no new prior-art search was run.

Original patch anchors:
core Cargo478B/6ef45d6cecf366bc4a882850f14b2f2ce518dc9ff73f3a3169ee6df0bb04d331;
CLI Cargo912B/812de43881c1b29afd84eb9435e7764027bae5da0f6efaabd5b8ea41ce6a3bf5;
pyramid208956B/ea0a490d299b156c449b3de8c5633fcaeda2190d1c92d1d9c5356e6a9a92c02e;
merge_cmd425678B/ca829e45c7021c5c5df7b51da85859e3763a9a95d01d302a91ab7cd0687b2dcf.
