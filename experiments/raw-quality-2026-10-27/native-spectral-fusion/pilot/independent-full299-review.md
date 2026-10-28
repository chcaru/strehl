# Independent full299 completion and evidence audit

2026-10-27. **VERIFIED saved evidence; no reconstruction rerun.** The complete
native-spectral run and presentation are internally consistent and their owned
processes exited cleanly. This is an integrity finding, not photographic
admission. The six retained generated quality failures remain. Photographic
appearance is reviewed separately; this audit does not infer it from hashes.
The user requested a pause after the current complete-output review. No
final-color execution, new experiment, build, RAW decode or further numerical
work is released by this report.

## Command, process and practical cost

The actual command was Python3.12 `-B -X faulthandler`
`experiments/raw-quality-2026-10-27/native-spectral-fusion/pilot/stream.py`
`--mode full299 --out outputs/raw-quality-2026-10-27/native-spectral-full299-1/output`
`--renderer-binding outputs/raw-quality-2026-10-27/native-spectral-build-1/executable.json`
`--development-receipt outputs/raw-quality-2026-10-27/direct-cfa-streamed-delivery-controls-2/output/held-development.json`.
The [invocation](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/invocation.json)
retains the absolute executable, arguments, environment and limits.

The [process](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/process.json)
records exit0, direct exit and pipe EOF, completed drain, zero active children,
no termination attempt and no cleanup errors. Seven owned processes consumed
7605.390625 CPU seconds. Wall time was **7627.829s /127.13 minutes**, below the
9000s bound. Peak Job committed memory was **9,269,575,680B**, below24GiB;
it is not RSS. The separate presentation exited0 in9.828s with the same clean
terminal properties and peak Job commitment749,903,872B.

The full worker includes cache/input checking, compilation/startup, all signal
and noise batches, accumulation, final development and output writing. Its
measured batches total7570.1918834s; initialization0.2936576s,
warmup0.4635116s and final overlap-add1.5814172s are separately recorded.
The two native writers report3.2073972s and3.1446054s. Prior RAW cache export,
alignment, renderer build/controls and presentation are not included in the
7627.829s. Thus this is a completed research run, not a whole-workflow speed
win or a directly comparable Helicon/native product benchmark. The actual
full run supersedes the source149 projection. Host telemetry has3808 samples,
mean CPU10.734375%, maximum31.7%, and at least39,800,004,608B available RAM;
whole-host observations do not establish exclusive machine use.

## Bindings and input scope

Freshly hashed **1600 unique references totaling4,905,146,895B**, including all
full/view completion artifacts, both native output chains, producer/runtime
dependencies, prerequisites, compiled executable and all1418 bound Rust/Cargo
source references. There were no conflicting bindings or mismatches. The three
recorded CUDA/NVRTC DLL hashes were separately rechecked and matched. The
numerical manifest is exactly identical to controls5, cost16 and source149.

The executable is `174d3fd5221d4406140d6dcc5932f88139c03ae5fd8fcb0ac81f6b72efc856ff`.
Producer SHA is `378e42c1e13065cd90cf0ecc5468e4a8c41ab5c1fcf41c5397e90ea0392c36a2`;
streamer SHA is `5835e6249fb613b6` (prefix). The earlier build's documented
owned-descendant timeout and clean cached recovery remain historical facts;
this audit does not relabel that first compilation job clean. The copied
executable and the current bound sources match its saved identities.

All299 cache entries match the verified original export, source order, current
file lengths and literal16-byte headers: unaligned7032x4688 u16 CFA, no
development or clipping applied to the cache. The root worker hashed every
cache payload before and after; those299-entry manifests and its source
binding manifests are byte-identical. This independent audit checked the
census, export linkage, headers and current lengths, without repeating the
19.7GB cache payload hash. It read no original RAW bytes. Original RAW byte
preservation is inherited from the earlier verified export; this run checked
RAW metadata, not fresh RAW hashes. Independent decode overlap exists for
sources0/149/298, and the additional four native columns remain unverified by
that second decoder. These limitations are explicitly retained in the full
receipt, not erased by complete output coverage.

## Actual census, runtime and outputs

The original source IDs, pull maps, selected patches and accumulator all contain
exactly0..298. Independently checked the complete batch journal: **148,902
batches,2,379,143 source-patches**, with every source consuming the same ordered
7957-patch grid. The grid is109x73, stride64, delivered origin(68,46), and its
literal saved origins match the producing convention. No missing or duplicated
batch was found. Runtime148,903 signal/prepared batches include the separate
one-patch warmup;2,382,448 probe batches equal16 times that count. These are
16 source-keyed original-sensor noise fields evaluated over patches, not16 new
independent fields at every overlapping patch.

Runtime is RTX5090, Torch2.11.0+cu128, CUDA12.8, four CPU/one interop threads,
TF32/autocast off, f32/complex64 signal and f64 geometry. Torch peaks are
5,509,941,760B allocated and6,650,068,992B reserved, below12GiB; neither is
whole-device memory. Precise NVRTC options and PTX hash are bound. Protected
interpolation entries contain no floating fused instructions;20 fused sites
are confined to the disclosed extraction/noise entry, with zero unclassified
sites. This is the previously commissioned scoped guard, not a global no-FMA
claim or proof that each fused instruction came from libdevice.

Both arms retain complete6896x4596 signed CFA, normalized camera RGB, RGB16 and
linear RGB32 masters at physical origin(68,46). Fresh readback independently
matched both full RGB16 and linear payload hashes, ICC and descriptions. CFA,
camera and linear fields are finite. Coverage is positive everywhere,
min0.9999997615814209/max1.000000238418579. Each arm uses one actual final core
MHC stage,4596 row calls, no source RGB/MHC, no remosaic and no RAW read. The
native writer's held normalization includes max0 before WB/range; the original
signed CFA is retained exactly. Candidate contains1,380,216 negative CFA
samples, range[-1311.0172,17928.9297]; uniform contains none. These are observed
field properties, not by themselves a diagnosis of photographic artifacts.

| Arm | Full RGB16 file SHA256 | Full RGB16 pixel SHA256 |
| --- | --- | --- |
| Candidate | `4429231573f1a2fcb09b9a7b1c3b12567433c28c6e6923c2653413d127ef8a2c` | `f6e5f3d1d0acd6c20ae9967495b2853dbac0aff176ffa005fdb67c35a3bcc3ec` |
| Uniform | `506a7d7caecf641a37cb820ca6b9590376f591937497ec32c97d68852d8fffb7` | `3f450dab3bd75b994066b92369fa43d77bb24df3ca35611ab286356d21b2a9c0` |

The [presentation](../../../../outputs/raw-quality-2026-10-27/native-spectral-full-views-1/output/index.md)
binds those actual masters. Both complete JPEG dimensions/ICC and all20 fixed
384x384 PNG pixels/ICC were independently read back. Each PNG is exactly the
saved master subarray after `(RGB16+128)//257`, with no rescaling. The two arms
share held development/materials and the commissioned held-CFA writer null;
their new image pixels are not claimed identical to the native baseline.

## Interpretation and admission

Controls5 passed mechanics and failed quality. The six failed cases are
independent-colours, green-diamond, shared-bin-conflict,
red-cancellation-diverse, near-fine-far-coarse and crossed-glint-sign-inversion.
The full completion's nullable control fields do not supersede that prerequisite
receipt. Previously observed flat-noise amplification and the lower-bound-only
component test's over-enhancement blind spot also remain relevant limits.

Uniform is a mean through this same interpolant/window/overlap and final MHC
path. It isolates the effect of source weighting but is not an all-focus truth
or an optimal reference. Improved sharpness against that deliberately averaged
arm alone cannot establish fidelity. The native baseline changes more of the
reconstruction path; Helicon also has different alignment/development. Those
comparisons can assess whole photographs but cannot isolate a sole causal
mechanism. The saved-stage audit supports specific generated pre-/post-MHC
differences, not a blanket claim that MHC caused the actual photograph's flaws
or that another completion would repair them. No final-color result exists.

Completion SHA `38d45d7fa29d614603f08168cee5372d57e1a1bfe24c26a1f0ac50a3c4227c8c`;
scientific receipt `a7c128e2c69717ec229e817ad3484bca2864a3fcb36bbf4afabe03cc4479198b`;
views receipt `dfbf12a668e0410ec9e87dfd1215280a02964e3594c9b33c944f5d5faff9f118`.
All retain no photographic admission. **Audit complete; stop here.**
