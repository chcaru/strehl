# Fixed dual-tree source and release review

2026-10-27. SOURCE-REVIEWED / DERIVED only; no compilation, RAW decoding, numerical execution or quality result. This reviewer independently read the root runner and producer consumer/transform. This reviewer authored the full adapter; its checks below are a wiring cross-check, not a substitute for the photographic reviewer's independent adapter review.

## Frozen checkpoint

| File | SHA-256 |
| --- | --- |
| `run.py` | `7a8927f897b07181be2f5855e5364081f8bd168fad73b9b6a46f8cf7bb54e104` |
| `full-adapter.rs` | `70f78c8728a2cb20bc834136e0898123aee6adc71f2bb06e49c029c432f63bb6` |
| `implementation.rs` | `eb6a51dbee5e65af9aec06c8e9e8a12dc4d29784572caa835c522df4029391e6` |
| `transform.rs` | `d49b6fe8ae336e2e25c3df506e38756201ad86ac7365543037b1390bc9598c65` |
| `controls.rs` | `9dbd8cc5e66fd79db3d043ed67ea1e9708d94ff507172be2066d71f8939e5517` |
| `design.md` | `ed4ffe0f17b2924fad6a2fbf298b34baf2eac836e95354926a4845758905c76f` |

No remaining source blocker was found at this checkpoint. Final controls use the prospectively corrected central angular ROI12..20 and disclose effective-band differences; their identity is included above and belongs to the root build manifest. No result was used to select the bank or thresholds.

## Runner and artifact contract

The registration and wrapper agree on `merge_cmd::dual_tree_cfa::independent_controls::generated_controls` and `::full::{weevil_source149_cost,weevil299_complete}`. The executable invocation uses `--ignored --exact --nocapture --test-threads=1`, with an exact one-test success assertion. The build targets the library test artifact, requires fresh `Compiling strehl-cli`, checks successful Cargo JSON completion, copies the identified executable, and binds tracked Rust/Cargo plus campaign Rust sources before/after. The corrected runner also binds itself, the reused runner helper, bounded-process helper and M12 job harness before/after execution. No test is inferred from a zero-test successful process.

The cleaned environment fixes four workers, CPU full-resolution gather, direct planes off, canonical green probe, parallel writeback, CA/defect/temporal/spatial floor interventions off, and Malvar demosaic. There is no environment mutation inside concurrent tests. Screen bounds are 120s/480CPU-s/4GiB; cost 300s/1200CPU-s/14GiB; full 1200s/4800CPU-s/14GiB. These are owned Windows job committed-memory limits, not RSS promises. Host load is recorded, not converted into a clean performance comparison.

The exact accepted statuses are `COMPLETE_DUAL_TREE_GENERATED_DIAGNOSTIC`, `SOURCE149_DUAL_TREE_COST_COMPLETE`, and `COMPLETE299_DUAL_TREE_DIAGNOSTIC`. A screen may retain `quality_pass=false`; all cases and mechanics must complete. Cost requires source149 and sixteen draws. Full requires the same executable's bound screen/cost and `299*source_phase_seconds + finish_seconds + 120 <= 1200`. All arms retain admission/photographic-admission false. A failed projection creates only a fresh refusal directory before any child launch.

Prerequisite checks rehash top-level scientific JSON and match the executable. Their nested image hashes are bound by those immutable receipts, but are not recursively rehashed by `complete_binding`; actual output verification remains required during final review. The adapter hashes complete delivered masters when writing its receipt. Build subprocess supervision is separate from the bounded numerical jobs.

## Producing path

Both canonical and candidate consume the same `BandWorker.planes`; no candidate-only source interpolation is substituted. The candidate callback explicitly invokes CPU `warp_frame_in_place` then canonical `extract_planes` for all four CFA phases, independently of the canonical green-only probe optimization. It counts exactly sixteen calls and retains original source ordinal149 in the cost test. Generated fractional pulls independently compare that callback's output bitwise against canonical gathered planes. Original u16 arrays are hashed before/after; full299 files/order/map and held masters are bound separately.

Canonical chunks retain [75,75,75,74], source order and original left-absorption order while holding combined/current accumulators only. Candidate accumulation stays ascending original ordinal without chunk reduction. The full canonical sensor payload, RGB16, linear RGB32 and material color/tone/ICC metadata must match the held CPU baseline; Software provenance may differ. The final writer uses the held exact tone, WB, matrix and crop with final MHC. Uniform is delivered as a third diagnostic arm, not an improvement claim.

The transform's synthesis indices are the transpose of its declared analysis; inverse y/x ordering reverses separable analysis. Packing/unpacking are algebraic inverses and four real reconstructed trees are averaged by1/4. Eight independent pair differences divided by16 estimate mean complex noise power before identical energy/floor smoothing. Running weight rescaling affects existing numerators and denominator together; one scalar controls both complex components and all four phases. The unchanged noise source helper rejects nonfinite or container-clipped construction; this does not identify physical sensor clipping.

Actual transform nulls precede the hull: each CFA phase must meet max0.05DN/RMS0.01DN for singleton reconstruction and uniform-versus-gathered mean. Singleton hull exactness is a distinct check. Six angular responses and one-sided sign/direction/scale foils remain executable prerequisites, not facts established by this source review.

## Limits retained

Small generated canonical ladders truncate while the candidate always has seven levels; their recorded exponent/size differences prevent attributing a relative synthetic gain solely to the basis. Weak green structure below the declared channel-retention threshold is not independently qualified by a joint projection or aggregate RGB error. The curved fixture is simplified coverage, not a calibrated pupil model.

Reflection and altered coefficients can create boundary artifacts despite perfect untouched inversion. Shared all-CFA energy can favor colored glare or discard a genuine depth component. Finite conditional probe power is not exact covariance whitening or a post-selection noise guarantee. Source149 cost is feasibility evidence, not a complete-workflow performance measurement. Only complete identical-display photographs and full masters can establish useful quality; a subsequent GPU route needs its own root allocation and parity evidence.
