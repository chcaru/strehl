# M194h: one actual-consumer pedestal causality experiment

SOURCE ONLY. The core hook, bridge, controls and this protocol are not permission to build or execute. An independent source read, a root-frozen build/control contract and one exact release must precede any call. HardFloor stays the default. No public normal CLI option is added. This experiment addresses one already selected adverse flat development case; it does not establish defocus, occlusion or physical alignment accuracy and cannot admit P0 as a shipping policy.

## Question and fixed inputs

The fixed hypothesis is that newly admitted E<=F mass contributes to the positive adverse displacement in experimental FloorPedestalV1 at native red (202,104), conditional on its above-floor weight function. The improving comparison site is native red (205,113). Both sites were selected from already inspected M194g outputs; neither is holdout. Whole-window summaries use the unchanged input-defined window x=[104,216), y=[104,136), all three RGB channels and the existing common ideal.

Use only full existing M194g flat seed743 and noise-free five-frame CFA bundles. `development-bindings.json` lifts their exact ten CFA/audit associations from the original saved plans, and names the unchanged noise admission, complete38 matrix and independent quality verification. This is saved metadata, not a newly measured input admission. The bridge still invokes the real original Inputs::load authority. Frame indices are exactly0..4, identity placements, native reference2; dimensions320x240. Do not crop input arrays or replace the actual global beta computation with a local floor.

The actual consumer is the existing `run_pyramid_prepared` through `BandWorker::fold`, `BandMerge::add_frame_with_gain`, `accumulate_level`, canonical `absorb`, `finish`, `write_merged`, MHC, and the measurement TIFF writer. Its working domain is FOUR CFA quad planes: crop quad(5,4), size150x113, levels [[150,113],[75,57],[38,29],[19,15]]. The output is300x226 RGB at native offset(10,8). Calling these internal grids full-resolution RGB would be wrong.

## Three arms and the one intervention

H: unchanged HardFloor. P: unchanged FloorPedestalV1. P0: start with P's exact already computed f32 weight and set it to positive zero if and only if the actual energy E<=the actual floor F. It happens immediately before the existing accumulate_level. Positive-excess P weights are not recomputed or replaced by H. The original unweighted sums and frame counts remain, so an all-zero denominator still reaches the actual mean fallback. The coarse base remains the actual mean; no band is removed.

The feature-gated hook calls are additions only to pyramid.rs. Its old arithmetic statements remain in place. All hooks are compiled out unless `m194h-pedestal-causality` is enabled; a feature build without an explicitly armed Session has no active experiment. The RAII session is installed only by the new ignored bridge/control. It has no environment fallback. It restores after a caught failure. Unsupported shapes, plane counts, nonfinite recorded operands, altered admission/base/fallback/hull, excess calls, nested sessions and trace overflow refuse.

The original current worker source runs one reusable BandWorker inside one pool.install closure with serial ascending chunks/frames; two configured execution threads parallelize spatial operations. Preserve STREHL_PYRAMID_WORKERS=2 and RAYON_NUM_THREADS=2. Trace frame ordinal is the successive call in that source-proven loop, which here equals original/local input index0..4; chunk-local frame count and actual absorb/reset events are retained. The bridge keeps the original source Observer::Count fixed in every case and requires counts[1,1,1,1,1], hooks5. This identifies the five source indices without adding another decode wrapper. The independently variable instrumentation is the core trace off/on/placebo.

## Complete inverse support and exact retained operands

Core level0 roots are the union of two complete5x5 native MHC envelopes after subtracting native crop(10,8), mapped to quad coordinates. All four CFA planes at each resulting quad are retained as an explicit conservative superset of the exact red MHC taps. The primary pixel is a red sensel, while the improving pixel is at blue CFA phase and requires MHC red interpolation. The independent checker must verify both the exact MHC red-tap subset and this envelope union.

For each level, propagate the full nonzero inverse dependency of the actual expand: even phase uses clamped c-1,c,c+1; odd phase c,c+1. Cartesian products of the axes yield all coarser indices. Retain exact sorted unique sets, not just their bounding box/count. This includes all three Laplacian bands AND mean base. Current source-derived counts are[18,18,15,16]. The independent reader separately derives the dyadic influence coefficients and must not treat all descendants as equal-weight samples.

`trace.bin` is little-endian u32 TLV: tag, payload word count, payload. Every floating field is the original f32 bit pattern. There is no core decimal serialization. `trace.json` binds its exact hash/extent, schema m194h-core-trace-v1, grid, support, call counts and observer mode. Tags/payloads:

-1 frame: [ordinal, chunk_local_frames, measured_beta_prefix_len, gate_bits, exponent_bits, sharpen_bits, effective_beta0_bits, beta1_bits, beta2_bits]. A prefix can be short; never claim all betas measured from an effective vector alone.
-2 band: [frame, level, index, E_bits, F_bits, H_weight_bits, P_weight_bits, used_weight_bits, above_floor_0_or_1, L_R_bits, L_G1_bits, L_G2_bits, L_B_bits]. F uses the identical held expression gate*beta*max(var,0); the trace is an arithmetic witness, not an independent noise estimate. H/P hypothetical comparison weights use the same named functions; only used_weight drives accumulation. Every selected frame is represented, including zero used weights.
-3 base: [frame,index,L_R,L_G1,L_G2,L_B] as bits.
-4 resolved: [plane,level,index,num,den,usum,resolved,den_nonpositive_0_or_1]. Base den=0 is the configured mean-base route, not fine-band refusal. Preserve actual final accumulators and reconstruct their canonical chunk association from frame/absorb/reset records.
-5 pre-hull: [plane,index,collapsed_value,lo,hi] as bits.
-6 post-hull: [plane,index,value] as bits.
-7 actual absorb entry: [target_frames,source_frames].
-8 actual scratch reset entry: [prior_frames].

Header call counts complete only at5frames/15band calls/5bases/16resolved calls/4pre-hull/4post-hull. On retains all records. Off retains no payload records. Placebo traverses the same bounded selected operands and black_box observer payloads but stores only its count. Neither observer edits data; only P0 alters its declared weights. Output identity must establish nonperturbation; the source argument does not substitute for it.

## Fixed cases and controls

Exactly twelve bridge cases, one render each, no plan-only pass:

| Ordinals | Input | Arm | Core observer |
|---|---|---|---|
|0,1,2|flat743|H|off,on,placebo|
|3,4,5|flat743|P|off,on,placebo|
|6,7,8|flat743|P0|off,on,placebo|
|9,10,11|flat noise-free|H,P,P0 respectively|off|

All current noisy off/on/placebo TIFF files must match within each arm. H/P whole TIFF files and canonical RGB16 pixels must also match the archived corresponding M194g endpoints. All three null files must match archived noise-free H/P. CameraLinear actually uses MEASUREMENT_SOFTWARE without build ID (image_out.rs profile=None), so these whole-file archive gates are expressible. Do not spoof any metadata. Their known old ordinals are0/1(null),15(H743),14(P743). A failed gate stops the run; no archive rebaselining.

The one ignored core control `pyramid::m194h::controls::fixed_threshold_null_and_observer_controls` invokes26 fixed tiny actual merges/130frame folds, plus one entry refused before folding:

- Nine H/P/P0 merges at three already commissioned floor values99.9375,100,100.0625 on amplitude10 period-two stripes, fiveframes, onlyframe3 active. Interior expected output is4096 plus signed10 for cutoff/H just above floor, signed2 for their all-sub-floor mean, or the fixed analytical P share. Tolerance0.004DN is inherited. The actual support partition bit is flipped, passed through the same captured-row predicate, and restored; rejection is required.
- Three all-four-plane noise-free flat merges are bitwise4096 throughout.
- Eleven observer identity merges: unarmed H/P plus each arm off/on/placebo. These compare f32 bits throughout; current TIFF identities remain a separate bridge gate.
- Three amplitude96 strong-stripe merges reject a plain mean as the detail-collapse destroyer.
- Direct same-cutoff-function control: fixed E=[11,40,160],F=10 gives varying actual P weights and all entries strictly above floor. P0 must preserve their bits. Changing one E to exactly F must zero it and break identity; restoring the above-floor data restores identity. This powers the actual weight path, not a claim that every coefficient of a real image lies above floor.
- Nested-session and unsupported-consumer controls exercise actual guards and RAII restoration. No additional rendered fixtures are introduced by these metadata/entry controls.

Controls are source only until released; no expected value can be revised after its observation merely to gain admission. The full benchmark does not repeat the38-output matrix or sweep the pedestal, exponent, gates, geometry or beta.

## Authority, publication and proposed finite resources

The ignored bridge name is `merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case`. The separately built test binary runs with exact arguments `--exact NAME --ignored --test-threads=1 --nocapture`. Actual argv0 must resolve to the pinned binary, and the complete raw argv must equal the released command. Preserve original binaries and evidence. New externally hash-bound grant has exactly8keys: schema, source_bindings, noise_admission, matrix_index, quality_verification, binary, commands, cases. Schema is m194h-pedestal-causality-release-v1. Source map values are positive {bytes,sha256}; references are {path,bytes,sha256}; each case is {ordinal,seed,arm,observation,output_directory}. Fixed outputs are under experiments/m194h-pedestal-causality/subject-1/case-NN. Root supplies a later exact grant, no runtime search or discovery.

Only M194H_GRANT, M194H_GRANT_SHA256 and M194H_CASE select the new ignored test; the original five required STREHL/Rayon settings stay fixed. Old M194G bridge overrides and unknown M194H overrides refuse. The plan retains the original plan object and explicit P0 layer, and points to authenticated old endpoints. Initial canonical result is a fixed32KiB incomplete record before image work. Completed or refused results replace it from a fsynced32KiB stage. A caught render panic retains the bounded actual trace prefix, then refuses. Aborts can leave only the initial record/partial files. External actual exit/Job/log and canonical status jointly determine completion; a positive receipt cannot override a later failed process. No current terminal memory/CPU is inferred from file counts.

`trace-capacity.json` contains only metadata/encoding arithmetic: maximum8092words=32368B for this exact support, including fourabsorb/fourreset records, against128KiB core cap. Named per-case reservations: plan128KiB, binarytrace128KiB, header16KiB, TIFF512KiB, canonical32KiB+simultaneousstage32KiB, failure8KiB; total876544B/case and10518528B for12. The proposed16MiB subject-artifact envelope leaves room for bounded controller logs/index. Actual outer caps and final complete inventory must still be checked. The first metadata constructor rejected a mistaken handwritten total before creating the capacity file; the final sum is derived from named slots.

Root-accepted prospective envelopes, still requiring the exact reviewed release: isolated build300CPU/240wall/8GiB committed Job memory, separate fresh scratch<=4GiB and retained artifacts<=128MiB; core controls60CPU/60wall/1GiB/2MiB; each render20CPU/20wall/1GiB and aggregate subject120CPU/180wall/1GiB/16MiB; metadata preparation30CPU/60wall/8MiB; independent saved checker60CPU/120wall/1GiB/16MiB. These match build-and-execution-contract.md and resource-ledger.json; they are finite prospective bounds, not measured requirements or permission to execute. Root retains whole-phase accounting and exact stage releases.

## Interpretation and stop

The hypothesis fails at the discovery site if no newly admitted positive sub-floor weight exists in the needed support, or actual P0 does not reduce P absolute error there. Retain the raw signed and absolute differences. If P0 improves but is still worse than H, admission supplies only a conditional partial explanation. H/P0 preserves the alternate above-floor change. Compare pre/post-hull to expose clamp-mediated movement, not to award two independent confirmations to the same data. Formula decomposition is arithmetic; actual P0 supplies the intervention.

One repeat cannot estimate temporal variance, and selected-site improvement can reward lost detail. A source/controls/diagnostics pass is not quality admission. If the hypothesis fails, retain that result without tuning. If it succeeds, stop with the causal diagnosis; later multi-repeat/textured tests need a separate proposal. M89's failed post-selection robustness and M120's spatial/band patchwork warn against moving the proposed repair to a convenient downstream average. Identity geometry here neither fixes nor licenses real-stack placement.
