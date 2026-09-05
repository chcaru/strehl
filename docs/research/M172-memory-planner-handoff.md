# M172 memory-planner handoff

**Status:** PLANNING CLOSED BY ORCHESTRATOR. NO IMPLEMENTATION AUTHORIZED.

**Source:** completed output from `m172-memory-planner`
`aaa12e33-42a2-42a0-843b-ed5a8ed20a23`, commissioned against the
post-D9/pre-memory-repair `fc2abb499126a56302de7f21f527de5613be34e7`
tree. The planner was already idle when the deconfliction order arrived. Its
sync-mode session could not accept a follow-up commit request, so M172 preserved
the useful planning result here instead of starting a prohibited replacement
agent.

This is a handoff to the orchestrator, not a new M172 memory workstream. M172
does not own the memory repair, does not direct M182, and makes no current
scorecard claim from this plan.

## Three-line conclusion

1. The old fold retained about `2,385,817,108 B = 2.222 GiB` of full-frame
   state per active chunk; `BandMerge`, `FrameWorkspace`, and full-resolution
   gather/warp temporaries dominate it.
2. Four concurrent canonical chunks model about `8.888 GiB`, closely matching
   M139's `8.931 GiB` W4 observation; multiplying whole-frame state, not N
   itself, is the governing memory mechanism.
3. `<=6 GiB` at W16 is reachable by a bounded streaming/recycling change:
   process the same canonical chunks serially through one reusable frame
   worker plus one retained and one scratch accumulator while keeping spatial
   Rayon work at 16 threads. Tiling is not required.

## Allocation model

For the 3516x2344 reference plane (`8,241,504` samples) and eight pyramid
levels (`10,988,941` samples), the planner counted:

| Simultaneously allocated consumer | Bytes per active chunk | MiB |
|:--|--:|--:|
| `BandMerge` | `659,330,004` | `628.79` |
| `FrameWorkspace` | `571,460,668` | `544.99` |
| `WarpScratch` | `74,173,536` | `70.74` |
| four planes, luma, and variance | `197,796,096` | `188.63` |
| gate-floor `Probe` | `208,799,908` | `199.13` |
| decoded frame and probe clone | `146,800,640` | `140.00` |
| full-resolution gather/warp temporaries | `527,456,256` | `503.02` |
| **Total** | **`2,385,817,108`** | **`2,275.29 MiB / 2.222 GiB`** |

The largest owners were:

- `BandMerge` in `crates/strehl-core/src/pyramid.rs`;
- `FrameWorkspace`, including `ghull` and `PlaneCache` workspace, in the same
  file;
- gate-floor state and the cloned probe frame under
  `crates/strehl-cli/src/merge_cmd/gatefloor.rs`;
- warp scratch and full-resolution gather temporaries reached through
  `crates/strehl-cli/src/align_cmd.rs`.

The contemporary banner modeled only `1,392,085,228 B` per worker. It omitted
about `993,731,880 B`, including full-resolution gather state and workspace
storage not counted by `FrameWorkspace::floats`. The planner therefore treated
the banner as a partition-compatibility estimate, not a process-peak model.

## Recommended bounded shape

The recommended design preserves D9's exact arithmetic topology:

1. Keep the canonical chunk count and
   `per_chunk = ceil(N / canonical_chunks)` unchanged.
2. Fold one canonical chunk at a time through one reusable `BandWorker`.
3. Move the first partial into the final accumulator without adding it to a
   zero accumulator.
4. For each later chunk, absorb left-to-right and reset the scratch
   accumulator to every constructor identity without releasing its storage.
5. Retain the requested Rayon thread count for disjoint spatial row and plane
   work.

The modeled live vector payload is
`3,045,147,112 B = 2.836 GiB`. Allowing allocator, decoder, writer, and Rayon
overhead, the planner expected roughly `3.0-3.3 GiB` at W16 and an
N299/N33 peak ratio around `1.00-1.03`. A measured peak above `4 GiB` was its
recommended investigation trigger, not a replacement for the registered
`6 GiB` bar.

The rejected alternatives were:

- one accumulator over all frames, because it changes D9's four-chunk
  floating-point association and therefore output bytes;
- spatial tiling, because pyramid halos, per-level hulls, collapse boundaries,
  and full-resolution warp state make exact-bit preservation substantially
  harder without being necessary to reach the bar.

This is bounded streaming/recycling rather than a fundamental tiled rewrite.
It is a real execution-shape change, not bookkeeping, but it is local to the
Pyramid fold and accumulator lifecycle.

## Risks and proof obligations

- Reset every additive, extrema, fallback, hull, diagnostic, winner-index, and
  frame-count identity; compare reset storage against a fresh accumulator and
  assert capacities/pointers are retained.
- Keep honest memory accounting separate from the frozen compatibility
  estimate that determines canonical chunking.
- Prove the recycled result bit-for-bit equal to retained canonical partials;
  do not rebaseline byte freezes.
- Measure W1 and W16 throughput because serial top-level chunks remove
  decode/warp overlap even though spatial Rayon parallelism remains.
- Use a single commit-bound binary, Job Object process-tree accounting, and all
  six repetitions in the registered N33/N105/N299 worker matrix.
- Never use the broad M139 tree snapshot for this work: it recursively
  enumerates `D:\personal\macro` and can reach the prohibited holdout.

No capture, holdout, source file, or M179 artifact was modified while
preserving this handoff.
