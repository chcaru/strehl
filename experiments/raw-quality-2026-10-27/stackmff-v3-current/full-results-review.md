# Independent completed V3 integrity review

2026-10-27. **VERIFIED: the complete external comparator and its views are intact and reviewable. Photographic quality is not admitted by this audit.** The photo reviewer separately assesses appearance. No new model/numerical experiment, RAW decode or source modification was performed; checks read existing records and saved output artifacts only.

## Execution and bindings

The actual [full command/process record](../../../outputs/raw-quality-2026-10-27/stackmff-v3-full-1/process.json) invokes Python3.12 with `-B -X faulthandler`, the frozen `stackmff-v3-current/worker.py`, pinned `stackmff-v3-upstream-2`, fresh `stackmff-v3-full-1/output`, and `--stage full`; every path is absolute in that record. Exit0,2445.797s, terminal Job accounting, zero active processes, no kill and no cleanup errors establish completion. Views independently exit0 in3.250s. Both retained sources and dependencies rehash correctly.

I freshly checked **139 unique referenced files,258,551,205 bytes**, covering full/views completion artifacts, their sources/upstream/runtime bindings, logs, and the controls/cost prerequisite reports and sources. Every size/SHA matches. Three additional frozen input metadata bindings also rehash exactly: the299-TIFF export receipt, original input order, and held map. This is not a redundant59GB source-payload sweep; the root-run before/after evidence is checked separately below.

| Record | SHA256 |
| --- | --- |
| Full completion | 2744c1a5fad225ce9cb8b3002b622b52ea2cdb673676d433a12d90a7b213237c |
| Full process | f7375d18283d43fe4ace75005c5def10f7effe1515e935ca2d34c8aa15623f38 |
| Full scientific receipt | aa824cb6c1a863125e42329a8ac09504959503ffb9606141e6224ebaf7bee1d9 |
| Views completion | fca9bc3d82dd25c845b429dab35b6b484d4f0169f7d8655623eba207ba718699 |
| Views receipt | 01dce609ecb911b77275d7cb07033350d89dc925430267455b280d1bc41018ce |
| RGB16 master | 908259e71e6b88d2134c0fb81dcdb257d79d773323c6dd8dbeb579d0306fd1c6 |

The fixed model/bridge/controls hashes remain those in [model-review.md](model-review.md). The full worker is `f0515af01f82d9933f80516978d23b9d7239e44949f01f507cada4b9c567c4af`, runner `be17f84e6f53ca028f126dbfeff0afd9af71a7026d54255f837c223db32aa705`; no substituted implementation or new checkpoint appeared.

## Complete source and spatial census

All299 pre/post records are exactly equal, including hashes, sizes, mtimes and order, and each matches its ordinal in the original export receipt. The standalone preservation record equals the embedded receipt. All299 headers record7032x4688 interleaved uncompressed RGB16 and the common ICC, with covered cubic support across the entire requested canvas. This confirms the retained developed inputs were unchanged in the actual job; it is not a fresh original-RAW census or independent radiometric calibration.

I compared every retained map f64 bit string with its literal row in the held map:299/299 match, including reference149's tiny nonidentity roundoff. The explicit reference149, crop offset(68,46), native center(3516,2344) and6896x4596 canvas agree with the frozen bridge. The map's Catmull label does not make OpenCV cubic equivalent; that declared resampler difference persists.

The486 tile rows match the entire expected row-major256-core partition exactly, with no missing/duplicate/overlapping core. Their total is31,694,016 native pixels. Every row retains299 jointly attended sources, no source-axis subsets, scales(1,0.75), sigma0.5, soft fusion, float32, TF32/autocast off, the same eight upstream bindings, halo128 and the correct global6912x4608 padded lattice. Maximum recorded probability-normalization error is5.66245e-6, within the producing guard. This establishes execution of the commissioned route; it does not establish scene detail, noise calibration or absence of visible tile seams.

## Actual outputs and viewing checks

The [complete master](../../../outputs/raw-quality-2026-10-27/stackmff-v3-full-1/output/stack-master.tiff) freshly hashes to the value above and has one uncompressed RGB uint16 page, shape4596x6896x3,190,164,096 pixel-payload bytes and190,167,088 total bytes. Its literal ICC SHA is `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`. There is no independent camera-linear or RAW master for this developed-image comparator; RGB16 is its full-resolution result.

The [complete JPEG](../../../outputs/raw-quality-2026-10-27/stackmff-v3-views-1/output/complete-stack.jpg) is6896x4596 with the same ICC. All ten PNG names/origins/sizes exactly match the frozen baseline witness list. I independently read each384x384 PNG and compared it with the corresponding saved-master subarray converted by integer `(RGB16+128)//257`: all ten match exactly, without resampling, extra tone or sharpening. JPEG is a viewing export, not a lossless pixel master. These checks commission the presentation, not its visual quality.

## Admission and practical limits

Receipt flags correctly remain `quality_claim:false`, `native_RAW_reconstruction:false`, `whole_workflow_comparison:false`. The [workflow accounting](workflow-accounting-review.md) adds the complete cost and explains inherited development/alignment. Host peak20,473,892,864 bytes and Torch allocated/reserved peaks15,420,138,496/16,414,408,704 bytes stay within the declared separate24GiB bounds; both jobs are terminal. The whole inference/gather worker takes40m45.797s, excluding earlier development/alignment and views. There is no competitive-speed improvement established.

The model consumes predeveloped, tone-encoded RGB16; this work does not advance the native original-CFA contract by itself. Shared native geometry removes one source of comparison ambiguity but leaves a different interpolation kernel, RGB quantization, timing of development, and consumer. Helicon additionally has an independent output gauge. Full/tile fidelity was commissioned numerically on the fixed controls; the -100 shifted-attention mask prevents a universal exact-locality theorem, and no full-size monolithic299-frame inference was performed. A better or worse complete image can therefore establish utility of this exact external workflow, not isolate a physical or native-pipeline cause. Preserve the complete result and await the separate whole-image/native-crop verdict; no SOTA or production-promotion conclusion follows from integrity passing.
