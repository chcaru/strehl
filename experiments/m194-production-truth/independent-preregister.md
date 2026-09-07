# M194 independent path commissioning

2026-09-07. Written before inspecting the prospective source-seam code.
Prior sources: `experiments/review-production-truth/audit.md`, the current
`merge_cmd` Pyramid/fold/load/confidence/writer call graph, AGENTS rules 6,
8, 11, 12, 20, 24, 26, 32 and 33, and the existing byte-freeze registry.

This verifies software reach and unchanged behavior, not optical accuracy,
image quality, a calibrated noise model, live alignment, or SOTA. The old
`blend-truth` warning is not a successful scene gate and its one-channel
BandMerge is not the target production path.

## Independent choices and falsifiers

1. Use a short, non-square u16 CFA bracket. Proposed active sensor extent is
   208x152 (104x76 per plane), with nonzero even active-buffer origin, padded
   stride, distinct R/G1/G2/B levels, and off-axis spatial variation. Padding
   is not scene data. Exact fixture construction will be recorded beside its
   source after agreement on the test bridge. Changing dimensions, CFA site
   addressing, stride or crop origin must change the checked output as implied
   by those coordinates; a constant or one-green-channel wrapper must fail.
2. The sole folding implementation must remain the production BandWorker,
   measured gate floor, four-plane BandMerge, canonical chunk absorb/reset,
   collapse and writer. A delegating decoded source and its direct source
   must produce byte-identical TIFFs under identical settings. This proves
   source-seam equivalence only; an authorized development RAW before/after
   byte comparison separately tests the normal RAW wrapper.
3. Change one interior input frame with a deliberately large spatial patch,
   retaining all metadata and placements. Assert the output bytes/pixels
   change, and assert the changed source index was actually decoded. A plant
   whose change the merge legitimately ignores is not evidence of reach.
4. Supply a known per-frame placement track, then perturb interior placements
   while keeping both endpoints and the reference exactly equal. Assert an
   interior placement differs and output changes in the same per-frame writer
   gauge. Identity and a curved track are separate arms. This catches ignoring
   interior transforms; it does not establish placement accuracy against an
   optical scene or use an endpoint-only alignment bar.
5. Exercise a compact crop with nonzero, preferably odd, plane origin; verify
   actual TIFF dimensions and the supplied origin. Exercise linear output and
   an independently chosen display/output setting, full-resolution demosaic,
   and distinct CFA channel content. Check decoded TIFF tags/channels and the
   actual Software lineage tag, not only a nonempty output file.
6. A source that fails one decode must return an error and not publish a
   successful image. A placement-refused frame must not enter the fold; an
   all-refused bracket must fail. Assert index-specific decode/placement
   counters so neither fixture can pass without exercising the refusal.
7. Use source labels/paths that do not exist on disk and commission confidence
   plus debug confidence through the same decoded source. Assert the second
   traversal occurs. Confidence on/off must leave merged output bytes exactly
   equal, including a null/constant-source control. A disk fallback, silently
   skipped observer, or observer that perturbs the merge must fail.
8. Record actual compile/rebuild proof and complete commands/environment.
   Do not infer a successful build from an old cached test result. Any real
   RAW check uses an explicitly permitted development subset, before/after
   input hashes, alignment-off or a pinned isolated sidecar, isolated cache
   and output, and preserved source/build provenance. No sealed capture,
   implicit live solve, whole-corpus sweep, or full M192 campaign is permitted.

The first controls are deterministic identity, changed-input and malformed-
path tests. No estimated sharpness metric or spatial/temporal noise ratio is
introduced. The bridge must return enough information to prove the production
path and intended input case executed; a hand-written copy of merge arithmetic
or a success exit after a warning cannot commission it.
