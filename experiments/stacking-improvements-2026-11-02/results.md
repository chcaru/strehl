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

**Cost.** About 3.5 GB more peak memory. Session implementation identity
hashes `merge_cmd.rs`, so cached session group merges recompute once.
