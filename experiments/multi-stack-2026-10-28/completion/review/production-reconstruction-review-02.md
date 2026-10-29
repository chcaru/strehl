# Production reconstruction fix review, checkpoint02

Independent read-only rereview after [checkpoint01](production-reconstruction-review-01.md). No CLI/core edits, builds or engine/RAW jobs were performed by this reviewer. This is a source conclusion, not a full-producer photographic result.

## Resolved in the reviewed source

- Registration pairs now use star edges plus a chain through the non-anchor list. Every source belongs to a proposed anchor triangle for any anchor and3–64sources. The structural control checks every anchor, every leaf and the bounded edge count. Actual measured edges can still legitimately refuse; no threshold was relaxed.
- Tile reports are streamed one completed cohort at a time through a256KiB BufWriter, using create_new, flush and sync before its final receipt. Full per-source JSON trees no longer accumulate with the whole image.
- The tile plan has a separately checked reservation before allocation. This review caught a second defect in the first fix: clearing a refused source Vec retained arbitrarily broad capacity. The final source replaces both lists with empty Vec values. A2,000-source broad-focus fixture now checks capacity==0, not merely len==0.
- This review also found that ceil(native_extent/32) was not a true maximum leaf census for even subdivisions:70×34native pixels can yield8leaves rather than6. The current reservation uses16pixel cells, separately from vector-capacity factors. The new fixture asserts the8leaf case and verifies retained allocations fit the reservation. Transient nomination sets are separately allowed128bytes/session-frame.
- FocusSummary now stores the full SamplingDomain, verifies field dimensions/original global ordinals during construction, and the planner rejects a same-length map in a shifted crop gauge. The caller still supplies the provenance of the freshly computed domain; this is not a persisted external map importer.
- RegionSampler replaces complete source-plane conversion for guide and motion sampling. Motion now consumes the certificate's actual color pulls. Per-worker budget is explicit160MiB, including bounded region sampler, kernel, local registration, admission fields and overhead.

## RegionSampler audit

The gather forms physical CFA site offsets and centered transforms in the full original grid before subtracting the integer source-rectangle origin. Four-pixel halo plus the legal endpoint cell encloses the current six-tap samplers. It separately checks the original full-domain support, then calls the same owned sampler and exact clipping-footprint code on the unaligned source rectangle. One color's float values/mask are dropped before the next. Checked reservation and budget refusal precede source reads. I found no blocker in this bounded gather.

Root-run evidence was read: sr-region-sampling-controls-01 freshly compiled CLI and passed5controls, exit0. They cover all6kernels, nonzero optical profile, rotated/cropped gauge, active-origin clipping, tiny planes, far fractional phases, composed color pulls, and refusal before source access. sr-consumer-controls-04 passed11controls, exit0, but its log does not contain a fresh compile and predates the final capacity/16pixel-bound controls; it is not presented as validation of those later edits. Root must schedule the next affected build/tests.

## Remaining verification scope

Source review now finds no outstanding blocker in the four original fixes or the second capacity correction. Full producer outcome still needs bounded runtime measurement, actual controls for primary/disagreement behavior, full completed photographs plus coherent support/native-fallback maps, identical display transforms and independent review. Exact gather equality does not establish optical detail, noise gain or unconditional delivered variance. UI12 actual GPU and option checks are separately recorded in [ui12-actual-gpu-review.md](ui12-actual-gpu-review.md).

## Reviewed source SHA256

- `crates/strehl-cli/src/session-reconstruction-plan.rs`: `6c10449dbd133bfd1b88ce35707edfcba245d0bd6eb54a2476da856c62d09dd8`
- `crates/strehl-cli/src/session-reconstruction-consumer.rs`: `c7df567c15480b29623acd09eeeef9411d017ca9c7466992ca98930b0a475a20`
- `crates/strehl-cli/src/session-reconstruction-sampling.rs`: `1c4697f52afdd6cc0321de2d3557547b72a4f06222c24f56bb2143d2141fbb7f`
