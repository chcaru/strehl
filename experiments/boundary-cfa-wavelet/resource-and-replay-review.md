# Full-image resource and replay review

Source-only review, 2026-09-19. **DERIVED allocation sizes; UNMEASURED full-image time and process peak.** No source changes, builds, RAW reads, or renders were performed for this note. The current fractional weak-red screen failed its quality guard; this note does **not** admit the current candidate to a RAW render.

## Allocation accounting

For the held vitamin-C crop, N = 3460 × 2306 = 7,978,760 quads. Original active geometry is 3516 × 2344 quads. Symmetric extension would produce P = 4096² = 16,777,216 quads, with left/top padding 318/895. Each padded f32 field is 64 MiB; each padded complex-f32 field is 128 MiB. Complete decomposition reaches **12** levels and 1×1 DC, rather than the small screen's seven levels. All figures below use binary MiB.

| Live allocation group | MiB | Source basis |
| --- | ---: | --- |
| Candidate sums and means, four complex planes each | 1024.00 | `implementation.rs`: `sums`, `means` |
| Candidate denominator, u16 participation counts, input low/high bounds, AC position indices | 467.49 | 64 + 32 + 243.49 + 128 |
| One actual baseline worker | 1582.56 | `BandWorker::new`, including merge 608.78, actual frame workspace 527.64, planes/guide/variance 182.62, gate-floor workspace 192.78, original-domain warp scratch 70.74 |
| Retained canonical baseline partial merge | 608.78 | Existing sequential four-chunk full adapter |
| Current source's four complex coefficient planes | 512.00 | Signal transform |
| Original active CFA variances; four padded coefficient variances | 381.75 | 125.75 + 256 |
| Diagnostic complex bias accumulator; probe AC position indices | 640.00 | 512 + 128; bias omitted when diagnostics are off |
| First member of current noise pair | 512.00 | `probe_from_wave`: `a` while constructing `b` |
| Conservative second-member transform transient | 1280.00 | Extended real planes 256; three completed complex planes 384; current input/output/rectangle/two-axis allocations at most 640 |
| Conservative remaining source/gather allowance | 332.48 | Two 70 MiB decoded buffers, four crop planes 121.75, extra original-domain warp scratch 70.74 |

This accounts for **7341 MiB (7.17 GiB)** of conservatively overlapping host allocations with diagnostics enabled and one active baseline worker. Some listed gather and transform allocations do not coexist. The GPU device-coordinate route additionally declares approximately **481.35 MiB device buffers**, and has about **78.60 MiB** packed-source/coverage host storage during a gather. Allocator retention, driver staging, decoder internals, executable/runtime memory, and small vectors are not peak-RSS-certified by this arithmetic. A **rough 8 GiB live working-set expectation**, rather than a 16 GiB guarantee, is justified by these arrays. Eight concurrent operator workers are not admissible; eight internal execution threads do not imply eight workers.

The generated convenience return also retains both RGB arrays (365.24 MiB each), two four-plane results, and inverse workspace. This is a later phase, after probe pairs are dropped; it does not dominate the estimate above. A photograph adapter should reuse `write_planes` and write/drop each result, without retaining both complete RGB arrays. No pixel arithmetic change is required for that lifetime change. Retaining all 70 decoded frames would add 4.79 GiB and is unnecessary; the existing source slice interface is therefore not the full-image entry point.

The baseline estimate uses the actual `FrameWorkspace` allocations, not its smaller legacy planning formula: reached sizes are 3460×2306, 1730×1153, 865×577, 433×289, 217×145, 109×73, 55×37, 28×19, with level-area sum 10,639,681.

## Minimal conditional replay seam

Reuse the held-source/config/profile/metadata checks and sequential `OneFrame` + `BandWorker::fold` loop in `donor-consistency/full-stack.rs`, plus `phase-packed-rgb/full-stack.rs::{chunk_plan,absorb_chunk,full_source_supported,write_planes}`. Preserve the exact four canonical baseline chunks and require the existing decoded-RGB16 baseline hash `2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`. Candidate signal coefficients must consume the actual `base.planes` after that fold. The noise members retain each original frame's path, WB, levels, active origin, and stride, so the existing GPU gather resolves and composes the same per-frame CA profile and held warp; coverage must be checked with that actual profile.

A new bounded full adapter would need explicit full-image extent/source-count/path/profile admission. The frozen generated code deliberately refuses real paths, CA, sources beyond 512 quads, crops other than 113×101, and more than 32 frames. Preserve those guards in the generated entry point. Source IDs remain the canonical 0…69 sequence for probe seeds; invalidate baseline probe state per frame as the current worker does. Retain only scalar/hash receipts across frames.

There is no source-level reason this **streamed allocation layout** must exceed 16 GiB or change fusion arithmetic. There are decisive admission blockers: the current fractional quality failure; uncommissioned 12-level and CA propagation; and unmeasured full-image runtime/peak. The source-space probe method already follows original-site reuse and reflection, but the no-CA small screen cannot certify the CA path by assertion alone. Existing noisy-source headroom refusals must remain explicit rather than be replaced by silent clipping.

Time cannot be inferred from the small screen: each of 70 frames requires one consumed signal transform plus **16 noisy-source GPU gathers and four-plane complete transforms**, totaling 1190 four-plane forward transforms and 1120 additional GPU gathers, besides baseline work. The current complete transform uses scalar tap loops and fresh work arrays. This is a concrete throughput risk, not a measured render duration. No performance or photographic improvement is claimed.
