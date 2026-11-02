# Overall stacking improvements

Owner request (2026-11-02): look for overall improvements in focus stacking,
research, experiment, and implement the top five; always ensure improvement and
no regression. Allocation `stacking-improvements-2026-11-02`.

Host: Windows 11, 16 cores / 32 threads, 64 GB. Release builds from the commit
named per item. Timings are single runs through
`experiments/multi-stack-2026-10-28/run-command.py` (wall, sampled peak private
bytes) with isolated `STREHL_WARPMAP` and `STREHL_CACHE_DIR`; host otherwise idle
apart from this lane.

## 1. Ordinary stacks: use every core and prepare frames ahead (implemented)

**Finding (MEASURED, `native-pyramid-profile` build, bug-4 102MSDCF, 299
frames, `--srgb`).** The pyramid fold ran frames strictly one after another and
defaulted to as many execution threads as arithmetic chunks (4 here), on a
32-thread host. Phase wall time at 4 threads: decode 20 s, gather 95 s, floor
probe 69 s, luma 4 s, pyramid add 25 s, total 215 s. At 32 threads the phases
were still serial (decode 12, gather 29, probe 27, add 23 s; 96 s).

**Change.** (a) Execution threads default to the machine's cores. Threads are
execution only; the arithmetic partition stays `canonical_band_chunks`.
(b) Up to 8 frames are prepared concurrently (decode, defect, gather, floor
probe, luma, variance, measured band floor), each in its own buffers, then
folded strictly in index order. Preparation reads no accumulator state, so the
additions and their order are those of the serial loop. The count is bounded by
a 4 GiB slot allowance at a calibrated ~128 bytes per plane site (4 slots for
A7C II planes). `STREHL_PYRAMID_LOOKAHEAD=1` restores the serial path;
`STREHL_PYRAMID_WORKERS` still sets threads. Research features that observe
per-frame inputs keep the serial path. Applies to the CLI `stack` and the
desktop's ordinary renders (which already pass their thread count); session
modes use their own fusion and are unchanged.

**Evidence (MEASURED; decoded pixels compared, not file hashes, because the
TIFF records the build).**

| Subject | Frames | Old (4 threads, serial) | New default | Peak memory old -> new | Pixels |
| --- | --- | --- | --- | --- | --- |
| bug-4 102MSDCF | 299 | 225.2 s | 84-86 s (4-slot interpolated; 80.1 s at 7 slots) | 2.8 -> ~6 GB | identical |
| leaf-2-cpl | 182 | 124.3 s | 48.9 s | 2.8 -> 6.3 GB | identical |
| 109MSDCF | 22 | 17.2 s | 7.2 s | 2.8 -> 5.8 GB | identical |

Slot sweep on bug-4 (threads 32): 3 slots 86.0 s / 5.3 GB, 5 slots 81.7 s /
7.3 GB, 7 slots 80.1 s / 9.3 GB; threads alone (serial preparation): 16
threads 104 s, 32 threads 99.6 s. All arms pixel-identical to the 4-thread
serial render.

**Controls.** `lookahead_preparation_folds_bit_identically_to_the_serial_fold`
folds seven generated frames (distinct content, sub-pixel placements, one
refused, measured floor on) both ways and requires identical accepted frames,
floors and merged planes to the bit; reversing the fold order inside a batch
makes it fail (mutation check run). `the_merge_environment_channels_behave` now
pins the new thread default and that a too-large worker still leaves one
chunk. Byte-freeze rows other than the pre-existing
`coffee-bean-20-gate2-unaligned` failure (identical on PR head `03c243f`) pass.

**Pipelining (second commit).** With batches, the serial pyramid add (24 s
on bug-4) waited for each whole batch. The slots are now two half-size sets:
while one set is folded in index order, the next batch is prepared into the
other (`rayon::join`). Default 4 slots (2+2). MEASURED, pixels identical in
every arm: bug-4 102MSDCF 79.4 s / 5.2 GB (8 slots 76.6 s / 8.0 GB, 12 slots
76.4 s / 11.0 GB); leaf-2-cpl 128.3 -> 47.0 s (5.15 GB); 109MSDCF 17.2 -> 7.2 s
(4.9 GB). Old arm: `STREHL_PYRAMID_WORKERS=4 STREHL_PYRAMID_LOOKAHEAD=1`, the
previous default.

**Cost.** About 2.4 GB more peak memory (2.8 -> 5.2 GB). Session implementation identity
hashes `merge_cmd.rs`, so cached session group merges recompute once.

## 2. Best result: parallel source preparation and group fold (implemented)

**Finding (MEASURED, bug-4 Best result, 5 passes, 1,231 sources, cached
alignment, `--threads 32 --memory-limit-gib 32`).** With the phase totals now
saved per lighting group, a 299-source group spent prepare 120 s, fold_group
72 s, gather 43 s, accumulate 42 s of 302 s. Inside `PreparedSource::
prepare_with_masks` the pixel copy with gain, green average, the two noise-
variance fields, the band-gain scaling and finite checks were single-threaded
element-wise loops, and the 5x5 support reduce/expand/erode masks were serial
per-pixel loops. In `fold_group`, every coefficient of every level was absorbed
serially. Best result groups are singletons (one source per group), so the
fold ran once per source.

**Change (`session-fusion.rs`).** The element-wise loops and the support-mask
operators run in parallel (rows or elements; each output is a pure function of
the same inputs). In `fold_group`, when repeat averaging cannot apply (fewer
than two sources, or another mode) and no attribution is kept, only the
"absorb ordinary contribution" branch is reachable; it now runs in parallel
chunks with integer diagnostic counts reduced afterwards. Other cases keep the
existing loop.

**Evidence (MEASURED; decoded photograph and master compared with the earlier
`out-auto-11`, which predates both changes):**

| Build | Wall | CPU use | Peak | Photograph / master |
| --- | --- | --- | --- | --- |
| Before (serial arm, same commit otherwise) | 549.6 s | 36% | 12.0 GB | identical |
| Parallel prepare | 467.7 s | 50% | 12.1 GB | identical |
| + parallel ordinary fold | 397.0 s | 67% | 12.1 GB | identical |

Per 299-source group after both: prepare 71 s, gather 55 s, fold_group 33 s,
accumulate 31 s (218 s against 302 s). `strehl-core` 742 tests and
`strehl-cli` 399 library tests pass.

## 3. Changing the RAM budget no longer re-aligns a session (implemented)

**Finding (MEASURED).** The session alignment cache was addressed by the whole
alignment config, including `memory_limit_bytes`, so a different RAM budget
(desktop setting, or another machine's half-of-memory default) re-ran the full
alignment: 843 s at 45 GiB and 1,138 s at 40 GiB for bug-4's 1,231 sources.
The warp maps from 32, 40 and 45 GiB are byte-identical (`warpmap_sha256`
equal); only timings and the stored budget differ.

**Change (`session-consumer.rs`, `cached_alignment`).** The cache file is
addressed with the budget normalised out; a saved envelope is loaded against
the budget it was bound with, so `SessionAlignment::load` still verifies every
other binding field exactly. Entries saved under the older budget-specific
address are still found. `session-align.rs` and its bound identity are
untouched; threads remain in the key (not tested).

**Evidence (MEASURED).** 40 GiB run: fresh alignment, saved as
`alignment-4beb3c92...`; then a 32 GiB run printed `reusing verified geometry
cache 4beb3c92...` and finished in 362 s instead of re-aligning. Photograph and
master of both runs identical to `out-auto-11`.

## 4. Best result hashes its RAW files concurrently (implemented)

Every Best result run SHA-256 hashes every original RAW twice (identity at the
start, an unchanged check before completion), one file at a time: 1,231 files,
about 40 GB, for bug-4. An independent hashlib timing on one 299-file pass
(warm cache) read 5.8 s serial against 1.0 s with 8 workers, identical digests.
`session-consumer.rs` now hashes concurrently with results in frame order and
the duplicate-content refusal applied in that order. The serial
`ResolvedSession::hash_sources` is unchanged because `session-input.rs` is
bound into the alignment cache identity (editing it would force every saved
session to re-align).

MEASURED, bug-4 Best result with cached alignment: 362.1 s -> 341.0 s;
`source-identities.json` identical to `out-auto-11`'s; photograph and master
identical.

## Investigated and not changed

### Best result group merges: prepared-ahead sources (no gain, reverted)

bug-4 Best result (5 passes, 1,231 sources, cached alignment, 32 threads,
32 GiB): 549.6 s serial. The same per-source look-ahead in the session group
fold (load serially, gather + prepare 4 sources concurrently, add in plan
order) gave identical photograph and master pixels but 579.3 s and 20.6 GB
peak against 12.0 GB. Reverted. Phase totals per 299-source group, now saved
in each lighting group's summary as `phase_seconds` (diagnostic): prepare
120 s, fold_group 72 s, gather 43 s, accumulate 42 s, probe 0.2 s of 302 s.
Three concurrent lanes ran at about 15 cores; one group alone took 0.70 s per
source against 1.01 s with three lanes, so the lanes contend for memory
bandwidth rather than threads (ARGUED from those two rates). A faster session
needs less memory traffic per source in `session_fusion`, not more
concurrency.

Side finding, since fixed (item 3): the session alignment cache key included
the RAM budget.

### Deep-stack softening is not present at HEAD on bug-4 102MSDCF

SYNTHESIS facts 1789/1790/1794 report the pyramid merge getting softer as the
stack deepens. Test: the same pass rendered from all 299 frames and from every
second frame (150, same focus range), current default, `--srgb`. Instrument
`depth-softening.py`: per 128 px block, phase-correlation registration (the
two renders use reference frames 149 and 150), then fine-band luma power,
binned by an independent coarser-band texture measure. Commissioned with
`--self-test`: sub-pixel shift reads 1.00 in every decile, Gaussian blur 0.25,
added white noise 1.41-1.51.

MEASURED, 1,877 registered blocks, ratio full/half: 0.20-0.35 cyc/px
0.986-1.035 across all ten texture deciles; 0.12-0.20 cyc/px 0.982-1.036.
The deeper stack is not softer here, so no merge change is warranted on this
evidence. Scope: one subject, one bracket; the record's softening was measured
on other subjects with earlier builds.

### Best result: parallel source-plane extraction in the sampler (no gain, reverted)

`NativeSampler::gather` converts each source's CFA rows to a float plane on one
thread. Doing it row-parallel cut gather from 55 s to 31 s per 299-source
group, but the bug-4 Best result took 391.9 s against 362-397 s before
(identical pixels): group wall time did not move, consistent with the memory-
bandwidth limit above. Because `session-sampling.rs` is bound into the noise-
transfer probe cache, the change also cost a one-time 280 s per-lane probe
recompute for every existing session. Reverted.
