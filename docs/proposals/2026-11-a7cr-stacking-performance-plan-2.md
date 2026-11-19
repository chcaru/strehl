# A7CR four-shot stacking performance, round 2: investigation and plan

**Status:** Partly implemented (2026-11-18): Q0, Q1a/c/d/e, Q2, Q3a-c, Q4, Q5a/b/f, Q6,
Q8, Q9a, Q10's read-ahead, Q12 and Q18 are on `main`; Q10's decode-ahead and Q5c were
measured and not kept; results per stage and what is not built in
[`implementation.md`](../../experiments/a7cr-stacking-performance-2026-11-18/implementation.md)
(later render 45.6 s to 23-24 s, first render 107.7 s to 48.8 s, bytes unchanged).
Evidence and prototypes:
[`experiments/a7cr-stacking-performance-2026-11-18/`](../../experiments/a7cr-stacking-performance-2026-11-18/results.md).
**Date:** 2026-11-18.
**Owner's direction (2026-11-18, after the first draft):** pull out all the stops. The GPU
route is the default. The archive format, the build, and every layer between the file and
the photograph may be replaced, provided archives stay compressed (the stacks are large)
and the result adapts to the machine and the drive it finds. Section 10 records what that
settled; sections 8 and 9 are therefore part of the plan, not an appendix.
**Baseline.** The measurements were taken on the owner's working tree of 2026-11-18,
which carries round 1's implementation (the GPU four-shot fold, the group journal, the
fused depth pass), committed to `main` as `ace830def` before the stages below were built.
**Scope:** `strehl-cli`, `strehl-gpu`, `strehl-core`, `strehl-raw`, `strehl-raw-codec`,
`strehl-capture`'s receiver, `strehl follow`, and the build.
**Audience:** an implementing agent, coordinated by the owner. Each stage says what to
change, why the output cannot change, how to prove it, and what it should save.
**Follows:** [round 1](2026-11-a7cr-stacking-performance-plan.md) (built 2026-11-18;
its section 12 is the starting state here) and
[the GPU fold record and planner](2026-11-gpu-resident-fold-and-planner.md).

**Goal.** On the owner's desktop, with bytes unchanged:

| Render of the scarab stack (196 four-shot planes, 48 GB) | Today | After Q1-Q12 | With every stop (sections 8, 9) |
| --- | --- | --- | --- |
| Later render, GPU route, stack on D: (980 PRO), cold | 49 s | about 16 s | about 14 s |
| The same with the stack on C: (SN8100) or in memory | not measured | about 14 s | about 11 s |
| First render of a stack (no map, no journal) | 108 s | about 24 s | about 17 s |
| Closing render after `strehl follow` | 49 s + 23 s alignment | about 14 s | about 11 s |
| Stack size on disk | 48 GB | 48 GB | about 45 GB (format 2) |
| CPU-only route | 198 s | about 180 s | the CPU fold is Q15 |

"Today" figures are MEASURED; the others are DERIVED in section 5 from the measurements
of section 3 and say what bounds them. Two facts set the floors. The capture drive D:
delivers 5.7 GB/s, so a cold fold of this stack there cannot take less than 8.4 s
whatever the software does. And the device needs 26-31 ms per twelve-plane frame, 5-6 s
for the stack, which is what a fold costs once the files arrive fast enough.

No milestone identifiers are allocated. Allocate one row per stage in
[milestone-ledger.md](../agents/milestone-ledger.md) before dispatch. Stage labels (Q1-Q19)
are plan-local. Labels: MEASURED, VERIFIED (read in the code), DERIVED, ARGUED, UNVERIFIED.

---

## 1. Summary

Round 1 moved the fold to the GPU. What is left is not arithmetic; it is plumbing. The
device is busy 30 % of the fold, the decoders run at a third of the rate the same code
reaches in isolation, and a fifth of a render is start-up, tear-down and repeated work.

| # | Finding (section 4) | Cost today |
| --- | --- | --- |
| 1 | Start-up and tear-down waste: a focus-metadata preflight for a camera it does not support, host accumulators allocated then freed, two GPU devices, slow exit | 4.5-6 s per render |
| 2 | Every file is read twice (prefetch threads copy it into a discard buffer, then the decoder reads it), and 75 % of it comes from the disk on every render | 49 CPU-s, 44 GB of extra copies |
| 3 | The fold thread copies 490 MB per plane into the upload buffer itself and reads 60 MB of luma back per plane | 67 ms of each plane's 100 ms |
| 4 | Decoders run at 310 ms per file inside the fold against 131-175 ms alone; helper threads sit on the decoders' sibling hardware threads | fold 19.6 s where the supply could be 8.7 s |
| 5 | The reference-tile pass gathers full-width bands, builds luma and variance nobody reads, and runs four slots | 11.9 s where about 1.5-2 s of work is needed |
| 6 | The tail reads 7.5 GB back, finishes two whole half-stacks for 200 tile crops, and convolves on the CPU with the device idle | 7.3 s |
| 7 | A first render aligns for 23 s on the CPU with a scalar search, and its group checks run on the shared pool at 4.4 CPU-s each | 59 s on top of the 49 |
| 8 | Nothing adapts: thread counts, windows, read mode and placement are constants, and the right ones differ between the two drives | every item above was found by hand |
| 9 | The archive format stores 6 % more than its data needs and costs three to four times more to decode | 3 GB per stack; decoding is what bounds a fold from a fast drive |

Stages, in the order to build them:

| Stage | Change | Saves on this host |
| --- | --- | --- |
| Q1 | Remove start-up and tear-down waste; one GPU context per process | 4.5 s (6 s on a new binary's first run) |
| Q2 | Reference tiles from column windows, without unused work, beside the tail | about 10 s |
| Q3 | Group check on the decoding thread, without what `measure` discards | about 28 s of a first render |
| Q4 | Reader threads hand whole files to decoders; no prefetch copies | part of Q5's figure |
| Q5 | Decode engine: row-buffered predictor, checksum in the row loop, file-sized jobs, samples written straight into upload memory, deliberate thread placement | fold 19.6 s to about 8.7 s (disk-bound) |
| Q6 | Depth energies on the device; the fold thread only submits | part of Q5's figure; 39 thread-seconds of CPU |
| Q7 | Collapse on the device; read back planes and tile crops, not accumulators | about 3 s |
| Q8 | Restoration's convolution on the device | about 1.4 s |
| Q9 | Alignment: offset lanes, tile reuse, no barriers | 23 s to about 3.5 s (first render) |
| Q10 | Preview: its own share of Q1-Q7, then overlap and optional retention | about 2 s |
| Q11 | The resource supervisor (section 7) | keeps the above true on other machines |
| Q12 | Pair journal and alignment during `strehl follow` (round 1's P9a-c, unchanged) | 23 s at the end of a capture |
| Q0 | The GPU route by default, behind a self-test; build changes (section 8) | makes the above the default |
| Q19 | Archive format 2: 6 % smaller, three to four times cheaper to decode, verified per chunk (section 9) | fold bound by the device, not by decoding; 3 GB per stack |
| Q13-Q18 | Group check on the device, small-memory devices, CPU fold, device kernels, Zstd's assembly decoder, speculative tile capture (section 8) | about 3 s more, and other machines |

---

## 2. Rules for the implementer

Round 1's section 2 applies in full (bytes, no reassociation, switches declared in
`scripts/check-defaults.py`, evidence, the shared tree, licences, the stop rule). Additions:

- **References.** Full default render SHA-256
  `02A6C8C2FAAFC3E266627F1E540F0E98A9690429BADC20B590EB5C32CBCC14CA`; `--limit 24`
  `E37E8E6F...`; `--limit 8` (depth cannot be measured) `A9F840B4...`; residual modes
  `off` `6F8A7C8C...` and `negate` `974EF829...` at `--limit 24`. All five must hold on
  both routes after every stage, and the A7C II byte-freeze must stay 5/5.
- **Scheduling is never arithmetic.** Everything the supervisor decides (threads, queues,
  placement, I/O mode, which bit-identical route) must be provably unable to change a
  sample. Canonical chunks stay derived from geometry and `MEMORY_BUDGET_BYTES`.
- **Measure with the timeline tools** of section 3.1, not only wall time: a stage is done
  when the resource it was meant to free is visibly free.
- **A cold file cache is the normal case.** This stack does not stay in memory between
  renders (finding F2). Quote cold and warm numbers separately, and say which.

---

## 3. Measurements

Host as in round 1: Ryzen 9 9950X3D (16 cores, 32 threads; cores 0-7 carry the 3D
V-Cache), 64 GB DDR5-6000, RTX 5090 (32 GB, PCIe 5 x16), captures on D: (Samsung 980 PRO
2 TB), C: is a WD SN8100. Host idle for every run (1-5 % CPU, device 1 %). Product binary:
`outputs/a7cr-perf-impl/bin/strehl-final.exe` (`cbca976b7e96-dirty`, round 1's final).
Instrumented binary: built from a copy of the working tree plus the timers and thread
names of `timers/` only (build id `unknown`, not kept; its output's pixels
were not compared, its timings match the product binary's within 1 %).

### 3.1 Tools (`experiments/a7cr-stacking-performance-2026-11-18/`)

- `trace.py --exe X --tag T [--threads] --env A=1 -- stack ...`: 100 ms timeline of
  process CPU (user and kernel), bytes read by the process, bytes read from the capture's
  physical drive, private bytes, page-cache standby, device utilisation; stderr lines
  stamped; with `--threads`, CPU per named thread.
- `stages.py T`: the timeline cut at the render's banner lines. `threads.py T t1 t2 ...`:
  CPU seconds per thread role and interval.
- `tp.py file.tp.csv`, `tp-threads.py`: the instrumented build's timers
  (`STREHL_TP_OUT=file`), per timer and per thread.
- `io-bench.py DIR`: read throughput by method, threads and cache state.
- `bench2/` (`pred`, `predparts`, `dec`, `pipe`, `ncc`, `fmt`): prototypes; not product
  code.
- `timers/`: the timers and thread names as exact-text patches (`patch-tp-*.py`,
  `trace-points.rs`) for a scratch copy of the tree; the copy they were applied to on
  2026-11-18 was deleted after the runs.

### 3.2 A later render, GPU route (MEASURED, four runs 47.7-49.6 s; this is run `t3-tp`)

Command: `STREHL_PIXEL_SHIFT=remosaic STREHL_GPU_FOLD=on strehl stack <dir> --demosaic --out o.tif`.

| Interval | Wall | Busy cores (kernel share) | Read by process / from disk | Device busy |
| --- | --- | --- | --- | --- |
| Preview pass: start to first frame line | 1.6 s | 0.4 | 0.82 GB / 0.2 | 0 % |
| Preview: host state and device set-up | 0.5-2.1 s | 1.6 | | |
| Preview fold, 25 planes | 2.9 s | 9.9 (21 %) | 8.9 GB / 2.6 | 15 % |
| Preview collapse and CA measurement | 2.1 s | 21.6 | | 2 % |
| Main pass: start | 0.8 s | 1.0 | 0.78 GB / 0 | 0 % |
| Main: host state and device set-up | 1.1 s | 1.3 | | |
| Main fold, 196 planes, to the depth map | 21.0 s | 19.9 (29 %) | 92.4 GB / 38.6 | 31 % |
| Reference tiles | 11.9 s | 19.4 (9 %) | 8.1 GB / 4.1 | 1 % |
| Half-stacks (with device tear-down) | 2.2 s | 11.9 | | 0 % |
| Full collapse, restoration | 3.1 s | 21.9 | | 0 % |
| Develop and write | 0.3 s | 12.4 | | |
| Process exit | 0.4 s | 0.8 (90 %) | | |
| **Total** | **49.6 s** | 16.7 | **111 GB / 46** | |

Timers inside it (instrumented build, means over the 221 planes of both passes unless
stated):

| What | Time |
| --- | --- |
| Fold thread per plane: staging copy of 490 MB (`gpu.stage`) | 38.3 ms |
| Fold thread per plane: luma read-back and copy (60 MB) | 29.1 ms |
| Fold thread per plane: waiting for the decoded plane | 24.9 ms (median 0.02, p90 65) |
| Fold thread per plane: probe collect, fold submit, probe submit | 2.3 + 2.4 + 1.1 ms |
| One archive decode inside the fold (881 of them) | 309.6 ms: read 60.2, Zstd 86.8, predictor 86.6, SHA-256 53.1 |
| The same on decoder threads 0-7 / 8-15 | 277 ms / 372 ms |
| One plane on a decoder thread (four members in series) | 1.28 s |
| Decoder threads waiting for window space | 48 thread-s of 336 |
| `depth_guide::record` per plane (wall on the 8-thread fold pool) | 198 ms |
| Reference pass per frame (153 frames, 4 slots) | 297 ms: row decode 122, gather 122, extract 24, luma 9.5, variance 5.5, observe 14.6 |
| `sony_focus_cmd::print_preflight` | 1.19 s and 0.73 s (once per pass) |
| `BandWorker::new` (host fold state, freed when the device attaches) | 0.25 s and 0.88 s |
| Shader module and 25 pipelines | 1.59 s on this binary's first run, 5 ms after |
| Vulkan instance, adapter, device | 0.25 s and 0.08 s |
| Accumulator read-back, 7.5 GB (`read_chunk`, both halves) | 0.45 s; `finish_chunk` 1.36 s with its allocations |
| Device tear-down (`drop(worker)`) | 0.29 s and 0.40 s |
| Half-stacks: even 1.05 s, odd 0.43 s, absorb 0.20 s, workspace 0.11 s | 1.78 s |
| `finish_with_report`, full stack / preview | 0.63 s / 0.42 s |
| Lateral-CA measurement (`measure_mosaic`) | 1.39 s |
| Restoration (`optical_restore::restore`) | 2.34 s |
| Chroma smoothing, develop and TIFF | 0.16 s, 0.12 s |

CPU by thread role during the main fold (21 s; user / kernel seconds): decoders
178.7 / 60.6; fold pool 106.3 / 7.2; prefetch threads 0.1 / 48.8; unnamed (drivers) 10.7 / 0.5.

### 3.3 A first render (MEASURED, empty `STREHL_CACHE_DIR`, run `t6-first`): 107.7 s

Alignment 23.3 s (22 cores busy, device idle). Preview fold 8.9 s against 2.9 s; main fold
51.5 s against 21.0 s: the 196 group checks add 36.5 s. Process CPU 2,383 s against 827 s.
Everything else as in 3.2.

### 3.4 CPU route (MEASURED, round 1's `final-cpu`): 197.5 s

Preview 16.2 s (fold 13.1 s, 0.52 s per plane); main fold 162.6 s (0.83 s per plane);
reference tiles 11.5 s; half-stacks 1.9 s; collapse and write 3.3 s.

### 3.5 Storage (MEASURED, `io-bench.py`, 48 files = 3 GB per row, files purged from the cache before each cold row)

| Method | 1 thread | 4 threads | 16 threads |
| --- | --- | --- | --- |
| Unbuffered read, cold | 5.15 GB/s | 5.72 | 5.55 |
| Buffered read, cold | 3.08 | 5.40 | 5.36 |
| Buffered read, cached | 8.21 | 13.43 | 14.54 |
| Mapped file with `PrefetchVirtualMemory`, cold / cached | 1.96 / 3.04 | 4.95 / 7.70 | 3.49 / 4.30 (9.4 s of kernel time) |

The drive's ceiling is 5.7 GB/s: 92 files/s, 23 planes/s, 8.4 s for this stack. Opening
a file with `FILE_FLAG_NO_BUFFERING` drops its cached pages (checked against the drive's
read counter), which is how the cold rows were made.

### 3.6 Decoding (MEASURED, `bench2 dec`, 64 files held in memory, decode only)

| Decoder | 1 thread | 16 threads, one per core | 32 threads |
| --- | --- | --- | --- |
| Product loop (predictor, then SHA-256 over the chunk) | 166 ms/file | 89.7 files/s | 127.1 |
| Row-buffered predictor, checksum fed row by row | 123 ms/file | 120.0 files/s | 136.9 |
| The same without the checksum | 77 ms/file | 152.2 files/s | 155.5 |

Eight threads on cores 0-7 against eight on cores 8-15: 127.4 against 125.1 ms per file.
The two halves of the CPU decode equally fast when nothing else runs.

The predictor (`bench2 pred`, `predparts`; identical samples on three real files and on
216 random shapes with full-range values): product 1.08 ns per sample, row-buffered
0.39 ns in cache (residuals 0.05, neighbour sums 0.07, the chains 0.22, copy out 0.02);
65.7 ms against 28.5 ms per file on cold chunks.

Readers feeding decoders (`bench2 pipe`, 320 files, row-buffered decoder with checksum):

| Readers to decoders | Files/s | Readers busy | Decoders busy |
| --- | --- | --- | --- |
| 4 buffered to 16, cold | 82.7 (5.1 GB/s) | 96 % | 79 % |
| 4 unbuffered to 16, cold | 90.2 (5.6 GB/s) | 96 % | 76 % |
| 4 buffered to 16, files just read | 94.5-96.0 | 65 % | 90 % |
| 4 buffered to 28, files just read | 86.7 | 88 % | 66 % |

### 3.7 Alignment search and group check (MEASURED)

- `bench2 ncc`: the NCC tile search with the x offsets of one search row as lanes, every
  score bit-identical on 64 searches per stage including tiles at every plane edge:
  5.0-6.2 times faster compiled for baseline x86-64, 10.3 times compiled for this CPU.
  The product form costs 11.5 microseconds per offset at 128 px, so 0.19 core-seconds per
  pair and 270 core-seconds for 1,413 pairs.
- Group check on one thread (`RAYON_NUM_THREADS=1`, round 1's harness): 1.36 s, of which
  three registrations 0.095 s each and the witness 1.08 s. On the whole idle pool 0.19 s.
  In the first render the checks cost about 4.4 CPU-s each (DERIVED: 856 CPU-s over 196).

### 3.8 The faster drive (MEASURED, `bench2 pipe` on 320 of the archives copied to C:, purged from the cache first)

| Readers to decoders | Files/s | Readers busy | Decoders busy |
| --- | --- | --- | --- |
| 4 unbuffered to 16 | 113.9 (7.1 GB/s) | 52 % | 96 % |
| 6 unbuffered to 26 | 116.9 | 35 % | 95 % |
| 6 unbuffered to 26, no checksum | 128.2 (8.0 GB/s) | 31 % | 94 % |
| 2 unbuffered to 16 | 111.8 | 51 % | 96 % |
| 4 buffered to 28 | 72.6 (4.5 GB/s) | 96 % | 44 % |

On C: the supply is bound by decoding, not by the drive, and only with unbuffered reads:
a cold buffered read through the system cache caps at 4.5 GB/s whatever the drive can do.

### 3.9 What a second format could store (MEASURED, `bench2 fmt`, three files, 184 M samples, bits per sample)

Format 1 as stored: 8.40, of which 0.26 is the 2 MB of original metadata and previews
each archive carries and 8.14 the samples.

| Code for the residuals | Format 1's predictor (left, up, up-left, up-right) | Row-above predictor `(a + 2b + c + 2) >> 2` |
| --- | --- | --- |
| Order-0 entropy | 7.91 | 8.12 |
| Entropy given a context (level x local activity, 192 contexts) | 7.70 | 7.91 |
| Split code: per block of 32, k low bits stored raw, the rest entropy-coded per k | 7.65 | 7.81 |
| Rice with the best k per block of 32 | 7.72 | 7.89 |
| Fixed width per block of 32 / with three exceptions | 8.25 / 8.22 | 8.38 / 8.36 |

Format 1 spends 0.23 bit per sample more than its own residuals' order-0 entropy (Zstd's
byte-wise Huffman over two byte planes), and a code that adapts per 32 samples needs
0.26 less than that entropy, because the noise scales with the signal.

---

## 4. Findings

**F1. A tenth of the render is start-up and tear-down (MEASURED, VERIFIED).**
`sony_focus_cmd::print_preflight` (`merge_cmd.rs`, called from `run_pyramid_attempt`)
opens every plane's archive serially through `archive::open_sparse`, decodes and hashes
the metadata chunks (0.82 GB of reads), and then `sony-focus.rs` rejects any model but the
ILCE-7CM2. It runs in both passes: 1.9 s for nothing on this camera. `BandWorker::new`
allocates and zeroes the whole CPU fold state (two 12-plane merges, a workspace, planes)
before `try_gpu` frees it: 1.1 s and a 23 GB spike of private memory. Each pass builds its
own Vulkan instance, device, shader module and 25 pipelines (`GpuFold::build`,
`cache: None`): 0.3 s, and 1.6 s more the first time a binary runs. Each pass decodes
frame 0 in full for its metadata, parses the capture journals and loads the map again.
Dropping the device takes 0.3-0.4 s per pass and the process takes 0.4 s to exit.

**F2. The stack is read 2.3 times, mostly from the disk (MEASURED, VERIFIED).** The
process reads 111 GB for a 48 GB stack. `RawPyramidSource::prefetch` reads each planned
file in 4 MB pieces into a thread-local buffer and discards it (four threads, 32 planes
ahead); the decoder then reads the file again from the system cache into its own buffer.
The prefetch threads spend 49 CPU-seconds in the kernel. And the system cache does not
hold the stack: private memory is 22-32 GB of 64, so about 12 GB of a 48 GB stack
survives, and 36-38 GB comes off the drive in every fold, at 1.7 GB/s where the drive can
deliver 5.7.

**F3. The fold thread is its own bottleneck (MEASURED, VERIFIED).** Per plane it spends
38 ms copying 490 MB into the mapped upload buffer (`GpuFold::stage`, through the 8-thread
fold pool) and 29 ms reading the kept luma back (`luma_collect`: a fresh 60 MB vector and
a copy from read-back memory), against 6 ms of submits and one probe round trip. With
decodes arriving instantly the fold could not exceed 14 planes per second. The device
shows it: 31 % busy.

**F4. Decoders run at a third of their speed (MEASURED).** 310 ms per file in the fold
against 175 ms for the same loop on 16 idle cores and 131 ms for the prototype of Q5.
Causes, each measured: the decoder reads its own file (60 ms); the helper threads (fold
pool, prefetchers, drivers) are unpinned and Windows puts them on cores 8-15, the
siblings of decoders 8-15, which run 34 % slower than decoders 0-7 although the two halves
are equal when idle; the predictor re-reads the row it is writing (1.08 ns per sample
where 0.39 is reachable); the checksum is a second pass over the chunk. A decoder also
owns a whole plane (four files in series, 1.28 s), so the window holds 18 planes (8.8 GB)
and decoders still wait 12 % of the time.

**F5. The reference pass does ten times the work it needs (MEASURED, VERIFIED).** Per
frame: 122 ms decoding rows, 122 ms gathering full-width 16-row bands for all twelve
sites where each crop is 136 columns of 4,752, 24 ms extracting, 15 ms of luma and
variance that only the fold reads, in four slots of 2.5 GB each
(`gather_restoration_references`). The work that is needed is about 130 core-milliseconds
per frame (DERIVED: the row decode is 20 % of four files).

**F6. The tail keeps the device idle (MEASURED, VERIFIED).** `finish_chunk` allocates two
3.77 GB host merges and reads both accumulators back; each half-stack is then resolved,
collapsed and clamped over the whole frame for twelve planes (1.5 s) although
`optical_restore::restore` reads only `crop(&half, ..)` at up to 200 tiles; the full
collapse is 0.63 s; the restoration is 2.34 s, of which the convolution is 1.44 s
(three channels of 0.48 s). The read-back itself is fast (0.45 s for 7.5 GB) and is not
the problem. In the write path the RGGB mosaic is built serially and dropped on the
carried route, and two normalisation loops are serial (0.1 s together).

**F7. A first render is dominated by two CPU stages the GPU waits for (MEASURED,
VERIFIED).** Alignment: 196 full decodes, then 1,413 pair fits whose inner loop
(`ncc_tile_impl`) runs three scalar f32 chains of 16,384 steps per search offset, in
batches of four frames with a barrier after each (`measure_ladder_streaming`); the tile's
own terms are recomputed for up to nine pairs. Group checks: `StackGroups::prepare_with`
calls `measure` on the global rayon pool from each of 16 decoder threads; the witness
(60 M sites, an f64 divide per site, six bounds-checked samples, and a photon-transfer
table with an `ln` call that `measure` then discards) is 79 % of its single-thread cost.

**F8. What bounds a fold depends on the drive (MEASURED).** On D:, 5.7 GB/s is 8.4 s for
48 GB; with readers handing files to decoders the supply reaches 83-90 files/s cold and
the decoders are 76-79 % busy, so after Q4-Q6 the drive bounds the fold. On C: the same
pipeline reaches 114-117 files/s with the decoders 96 % busy: there decoding bounds it,
just under the device's own rate (26-31 ms per plane, 129-154 files/s). And on C: a
buffered cold read is the wrong tool: 72.6 files/s against 114 unbuffered. One fixed
configuration cannot be right for both drives; section 7 is how it adapts.

**F9. Format 1 is neither as small nor as fast as its data allows (MEASURED).** It
stores 8.14 bits per sample where a block-adaptive split code needs 7.65 with the same
predictor (6 % less) and 7.81 with a predictor that reads only the row above (4 % less).
Its decode is two table-driven symbols per sample through Zstd (54 ms per file) plus a
predictor with a serial dependency along the row (24-66 ms) plus a SHA-256 of every
sample (46 ms); a format built for decoding needs about one coded symbol per sample, a
vector unpack and, if wanted, a predictor with no serial dependency at all.

**F10. What does not need fixing (MEASURED).** Accumulator read-back (16 GB/s). Streaming
stores for the decoder's output (no gain: 104.9 against 106.7 files/s). Memory-mapped
reads (slower than `ReadFile` in every case, 9 s of kernel time at 16 threads). The 3D
V-Cache half against the other half for decoding (equal when idle). Wavefront or
cross-chunk vector forms of the predictor (ARGUED: the scalar chains already reach
0.22 ns per sample and the gathers a vector form needs cost as much).

---

## 5. Budget

Seconds, scarab stack, this host, GPU route. DERIVED from section 3 unless marked.

| Line | Today (MEASURED) | After Q1-Q3 | After Q4-Q6 | After Q7-Q10 |
| --- | --- | --- | --- | --- |
| Process start, both passes' start-up | 2.7 | 0.6 | 0.6 | 0.6 |
| Host state, device set-up (both passes) | 1.6 (3.2 first run of a binary) | 0.4 | 0.4 | 0.4 |
| Preview fold, 25 planes | 2.9 | 2.9 | 1.3 | 1.3 |
| Preview collapse and CA measurement | 2.1 | 2.1 | 2.1 | 1.0 |
| Main fold, 196 planes | 19.6 | 19.6 | 8.7 cold, 6.5-7.5 cached | same |
| Accumulator read-back and host merges | 1.4 | 1.4 | 1.4 | 0.3 |
| Reference tiles | 11.9 | 2.0 | 2.0 | 1.5, beside the tail |
| Device tear-down | 0.7 | 0.1 | 0.1 | 0.1 |
| Half-stacks | 1.8 | 1.8 | 1.8 | 0.4 |
| Full collapse | 0.6 | 0.6 | 0.6 | 0.3 |
| Restoration, chroma, develop, write | 2.8 | 2.7 | 2.7 | 1.3 |
| Exit | 0.4 | 0.05 | 0.05 | 0.05 |
| **Later render** | **49.6** (the lines above sum to 48.5) | **about 34** | **about 22** | **about 16 (14 cached)** |
| First render adds: alignment | 23.3 | 23.3 | 23.3 | 3.5 (Q9) |
| First render adds: group checks | 36.5 | about 8 (Q3) | about 4 | about 4 (1 with Q13) |
| **First render** | **107.7** | **about 65** | **about 49** | **about 24** |

What bounds each "after" figure:

- Main fold: the drive (92 files/s on D:). With the files cached or on the SN8100 it is
  decoding at 120-137 files/s (MEASURED, decode only) less what readers and the fold cost,
  then the device at 26-31 ms per plane (5.1-6.0 s).
- Preview: 100 decodes at the same rate, 25 device planes, a 4-plane collapse and the
  1.4 s measurement (Q10 overlaps it with the main pass's first decodes).
- Group checks on a first render: about 0.6 core-seconds each after Q3 (ARGUED) on the
  decoding threads, about 120 core-seconds beside 105 core-seconds of decoding.
- A closing render after `strehl follow` (Q12) is the later render with the files still in
  the system cache: about 14 s.

**With every stop pulled** (sections 8 and 9; DERIVED, later render):

| Line | After Q1-Q10, D: cold | All stops, D: cold | All stops, C: or cached |
| --- | --- | --- | --- |
| Start-up, device, preview | 3.3 | 2.8 | 2.5 |
| Main fold | 8.7 (drive) | 8.0 (drive; 6 % fewer bytes) | 5.0-5.5 (device) |
| Reference tiles, tail, exit | 4.0 | 2.6 | 2.6 |
| **Later render** | **about 16** | **about 14** | **about 11** |

On D: the drive is then two thirds of the render and only the format's smaller files move
it. On C: or from memory the fold is the device's own time; Q16 is what moves that, by
perhaps a fifth. A first render adds about 3.5 s of alignment and 1-3 s of group checks
(Q13, or Q3 with the cores format 2 frees): about 17 s.

---

## 6. Stages

### Q1. Start-up, tear-down and one device per process

- **Q1a. Preflight.** `sony_focus_cmd::print_preflight`: decide support from the first
  file's identity (`strehl_raw::identity_cached`) and return before opening anything when
  the model is unsupported; when supported, run it once per process over a parallel
  iterator. In `archive::open_sparse` seek between chunk headers without refilling an
  8 KiB buffer per header, and do not hash metadata chunks whose hash is discarded.
  Check: `STREHL_SONY_FOCUS_AUDIT=0` and the default now read the same bytes on an A7CR
  stack; an A7C II stack prints the same audit as before. Saves 1.9 s.
- **Q1b. One stack context.** Build once in `ca_refine::run_refined` and pass to both
  passes: the path list, `StackGroups` (with the parsed capture journals and the open
  `GroupJournal`), the loaded and cover-fitted map, frame 0's geometry, levels, camera,
  ISO, white balance and matrix, and the identity. Today each is produced two to four
  times. Saves about 0.3 s and removes a class of drift between the passes.
- **Q1c. No host fold state under a device fold.** Decide the route before
  `BandWorker::new`; give `BandMerge` a constructor that builds the counting state
  `release_external_totals` leaves, without allocating totals, and build `FrameWorkspace`,
  `planes`, `luma` and `var` only on the CPU route or on fallback. Exactness: `try_gpu`
  already frees exactly these before the first frame. Saves 1.1 s and the 23 GB commit
  spike (the page cache keeps that much more of the stack).
- **Q1d. One GPU context.** Instance, adapter, device, queue, shader module and pipelines
  live in a process-wide context; `GpuFold::build` takes it and creates buffers only. Add
  a `wgpu::PipelineCache` stored under `cache_root()/gpu/`, keyed by adapter, driver
  version and a hash of the SPIR-V words; a cache that fails validation is ignored.
  Exactness: the same pipelines from the same words; the existing device tests cover it.
  Saves 0.3 s per render and 1.6 s on a binary's first run.
- **Q1e. Tear-down.** Drop the device and the large host vectors on a helper thread while
  the tail runs, and in the CLI binary only (not the engine library the desktop links)
  leave through `std::process::exit` once the output is closed and the journals flushed.
  Saves about 1 s.
- **Q1f. Small serial work in the tail.** On the carried route do not build the RGGB
  mosaic that is dropped; make the two `norm` loops parallel; in `finish_with_report`
  compute `ensemble_thresholds(k)` once per level and skip the report's sums when the
  caller is `finish`. Each element's expression is unchanged. Saves about 0.2 s.

### Q2. Reference tiles from windows

Build round 1's `gather_plane_window` (its P3b, "second version"), which was specified and
not built, and use it in `gather_restoration_references`:

1. Per (frame, tile): gather only the crop's columns widened by the taps, for the twelve
   sites, finishing each sample exactly as the fold does (round 1, P3b's three finishing
   expressions). `gather_rows_catmull_rom_checked` carries no state along a row, so a
   first-column argument is bit-identical per pixel.
2. Do not build luma or variance for a reference frame; call `optical_restore::observe`
   with the windows.
3. A slot then holds four row-decoded members and a few megabytes of windows, not 2.5 GB:
   run `min(workers / 2, 12)` slots, each decoding its rows on its own thread
   (`decode_archive_rows` serial per member) instead of sharing the pool.
4. Start the pass on its own threads as soon as `finish_tap` returns and let the
   accumulator read-back and the half-stacks proceed beside it; the restoration needs both
   and neither needs the other.

Exactness test (required): for at least three frames including the demoted frame 137 and
tiles in the first and last candidate rows and columns, every crop equals the crop of a
full `prepare_frame_into` bit for bit; then the five reference hashes. Saves about 10 s on
both routes (11.9 s to about 1.5-2 s; DERIVED from 153 frames x about 130 core-ms).

### Q3. The group check on a first render

- **Q3a. On the decoding thread.** Under decode-ahead, `StackGroups::prepare_with` runs
  `measure` on the calling thread (a one-thread scope), as the members already decode
  there. Its sums are collected per row and added in row order, so the pool size cannot
  change a bit (round 1's `a_group_measures_the_same_bits_on_any_pool`). MEASURED: 1.36
  core-seconds on one thread against about 4.4 CPU-seconds through the shared pool.
- **Q3b. Do not compute what `measure` discards.** Give the witness a mode without the
  photon-transfer bins (and their `ln`), the quadrant sums and anything else only
  `measure_with_witness` returns. The journaled fields come from the same chains in the
  same order. Test: `measurement_bits_are_pinned_to_the_check_version` passes unchanged.
- **Q3c. Integral buffers.** Take the four 121.5 MB integrals from a per-thread pool; run
  the column pass in place over column strips instead of building `strips` and copying
  back. Each element is still its row prefix plus the finished element above it.
- **Q3d. `normal`'s reference terms once.** `c`, `gx`, `gy` depend on the reference and
  the grid only; compute them per row once for the three members and their iterations.

Expected about 0.6 core-seconds per group (ARGUED from the single-thread split: witness
1.08 s of which the per-site divide and the discarded table are most). First render's
36.5 s of checks to about 4-8 s. `GROUP_CHECK_VERSION` does not change.

### Q4. Reader threads

Replace `run_prefetcher` and `RawPyramidSource::prefetch` for archive sources by reader
threads that read each planned file once, whole, into a pooled buffer, parse the envelope
and the chunk table, and hand `(plane, member, bytes, chunks)` to the decoders through a
bounded queue (decoders + readers + 4 files, about 1.5 GB). Decoders never open a file.

- Two read modes, chosen per volume by the supervisor (section 7), never by a constant.
  Unbuffered (`FILE_FLAG_NO_BUFFERING`, `O_DIRECT`, `F_NOCACHE`) when the files are not
  in the system cache: MEASURED 90.2 against 82.7 files/s on D: and 114 against 72.6 on
  C:, and it leaves the cache alone. Buffered when they are cached (13-14 GB/s from
  memory). Never mapped files.
- Start with two readers; the supervisor moves it. One reader is 3.1-5.2 GB/s cold; two
  reach D:'s limit and feed 16 decoders on C:.
- Exactness: bytes are bytes; the envelope and length checks move with the read.

### Q5. Decode engine

One change of shape, built as five parts that land together or in this order:

- **Q5a. Row-buffered predictor.** `unpredict_into` becomes a row producer: per pair of
  rows it builds the residuals and the three-neighbour sums of the rows above in small
  buffers (vectorised by the compiler), runs four carried chains in 32-bit registers, and
  hands each finished row to a sink. Nothing is read back from the destination. Prototype:
  `bench2/src/main.rs`, `unpredict_rows`. Tests: equality with the current function on
  every owned archive geometry and on random residuals at widths 2-257 and 1-17 rows with
  full-range values (the prototype's test); the existing corrupt, truncated and
  wrong-hash refusals.
- **Q5b. Checksum in the row loop.** Feed each finished row to the running SHA-256 from
  the row buffer (the bytes and their order are unchanged: prefix, samples in row order,
  suffix).
- **Q5c. File-sized jobs.** The unit of decode-ahead is `(plane, member)`; a plane is
  ready when its members are; decoders take the earliest job not started. The window is
  counted in files. Memory in flight falls from 18 planes (8.8 GB) to about decoders x 122 MB
  plus two or three finished planes.
- **Q5d. Decode into upload memory.** The row sink is either a `Vec<u16>` (CPU routes,
  alignment, `strehl follow`) or a member's region of a mapped upload slot. `GpuFold`
  exposes a ring of persistently mapped upload slots (start with four: 2 GB of
  host-visible device memory) and hands each to the decoders as a write-only region; the
  fold thread unmaps, submits the copy and re-maps, as it does today for two slots.
  `GpuFold::stage` no longer copies. This removes 38 ms per plane from the fold thread and
  96 GB of host copies per render.
- **Q5e. Placement.** One decoder per physical core as now, and the helpers placed on
  purpose: readers and the fold pool on the sibling threads of cores chosen evenly across
  the cache groups, not wherever the scheduler prefers (section 7 generalises this).

- **Q5f. Verify at ingest, not at every render** (the owner asked whether the checksum is
  needed). What it protects: the transfer from the camera's host, which the receiver
  already verifies by decoding every file against the sender's SHA-256 before it writes
  the receipt (`archive::retain`, `transfer-receipts.jsonl`); and damage at rest, which is
  rare and which a render need not pay 46 ms per file, 37 % of a decode, to look for every
  time. So: a full decode skips the SHA-256 when the file's name, length and declared hash
  match a receipt or an earlier verification recorded beside the group journal
  (`cache_root()/verified/`, written by the receiver's receipt, by `strehl follow`, by a
  render's first verified decode, and by a new `strehl verify <dir>`); any other file is
  verified in the row loop and recorded. `STREHL_ARCHIVE_VERIFY=always` restores today's
  behaviour (declare it). What this gives up for format 1: a file damaged on disk after
  its receipt decodes to wrong samples without an error unless the damage breaks the Zstd
  stream. Format 2 closes that with a per-chunk checksum that costs almost nothing
  (section 9), so there every decode is verified, row-range decodes included.

MEASURED with the prototype (Q5a and Q5b only): 166 to 123 ms per file on one thread,
89.7 to 120.0 files/s on 16, 136.9 on 32, every checksum correct; without the checksum
77 ms and 152 files/s. Exactness for the whole stage: decoding is a pure function of the
file.

### Q6. The fold thread only submits

- **Q6a. Depth energies on the device** (round 1's P10, now measured as the fold thread's
  second cost). Two kernels: the separable blur (taps computed on the CPU as today and
  uploaded; each pixel sums its taps from zero in tap order with clamped indices) at sigma
  1 and sqrt 3, and the cell energy (one invocation per 8 x 8 cell: 64 terms
  `f64(a - b)` squared, added in row-major order, divided by 64, rounded to f32). Write
  both bands' cells into a device buffer of `frames x cells x 2` floats (369 MB here) and
  read it once after the fold, or 1.9 MB per plane beside the probe's sums when memory is
  short. `depth_guide::record` remains for the CPU routes. Test: bit equality with
  `record` on real and random luma for both bands; then `STREHL_DEPTH_PASS=prepass`
  against the default.
- **Q6b.** Reuse the probe's read-back buffer instead of `create_buffer` per plane; keep
  the fold thread's timers as a permanent `STREHL_FOLD_TRACE` (declare it) so the
  supervisor and the next investigation read the same numbers.

After Q4-Q6 the fold thread spends about 6 ms per plane (MEASURED parts) and the fold
takes what the supply and the device take.

### Q7. Collapse on the device

Today the device hands back 7.5 GB so the CPU can resolve and collapse three times.

- Read back only the ensemble sums (`zmax`, `zsum`, `lsum`, `esum`: 4 x 80 MB per half)
  and the null windows; compute the blend maps on the CPU exactly as now (they use
  whole-line f64 prefix sums and the platform `ln`, and stay there); upload them.
- New kernels mirroring `finish_with_report` operand for operand: resolve
  (`div(num, den) * 65536`, the mean `usum * inv_n`, the blend lerp; the shader already
  evaluates f32 division through f64), the collapse (`expand` exists; add per level), the
  base blend's `reduce`, the hull clamp, and `absorb`'s elementwise combination of the two
  accumulators on the device.
- Per half-stack read back only the planned tiles' crops (the restoration reads nothing
  else of a half); for the full stack the twelve planes (722 MB).
- `averaged_fraction` and the desktop's accumulator views need `den`: read `den` (80 MB)
  or compute the count on the device.

Tests: a device test collapsing random accumulators with signed zeros, zero `den` and
infinities against `finish_with_report` bit for bit, for one and two halves; the five
hashes. Saves about 3 s (read-back and merges 1.4 to 0.3, half-stacks 1.8 to 0.4, full
collapse 0.6 to 0.3). On the CPU route, the smaller form: blend maps for the whole frame,
then resolve, expand and clamp the twelve planes on the tiles' footprints only (a 136 px
crop needs about 25,500 coefficients per plane against 20 million), about 1 s.

### Q8. Restoration on the device

`core::convolve` in the square-root domain, its squaring and the keep lerp are per-pixel
f32 with a fixed tap order (zero taps skipped, multiply then add, mirrored borders):
mirror them in one kernel per channel with the taps uploaded. The highlight guard (compare,
max filter, ordered Gaussian) is local f32 and can follow, or be uploaded as a 60 MB plane.
Spectra, cutoff fits and kernel design stay on the CPU (f64 FFTs on tile crops). Test: the
existing `tiled_convolution_equals_the_row_sweep` reference against the device on odd
sizes and radii 4, 5, 17 and 32; the hashes. Saves about 1.4 s. Do it after Q7, which
leaves the planes on the device.

### Q9. Alignment

- **Q9a. Offset lanes.** In `ncc_tile_impl`, for each search row compute the valid x
  offsets as lanes: lane `l` reads `moving[row + x + l]`, so each lane performs exactly
  the scalar operations of its offset in the same order (the two passes, the divide by
  the tile size, `num / (sa * sb).sqrt()`, the skips, and the raster-order argmax all
  stay scalar and per offset). Prototype: `bench2/src/ncc.rs`. Use fixed 16-lane arrays so
  the compiler vectorises without intrinsics; add a run-time-dispatched copy compiled for
  wider vectors (the lanes are independent, so width cannot change a bit).
- **Q9b. Tile terms once.** The mean-removed reference tile and `sa` depend on (frame,
  tile): compute them once per frame and stage, not once per pair.
- **Q9c. No barriers.** Replace the batch-of-four schedule by a dependency-driven one: a
  pair is measured when both planes exist; a plane is dropped when its last pair is done;
  edges are sorted by ordinal afterwards, as now.
- **Q9d. Decode.** Use the reader and decoder of Q4-Q5 (member 1 only), reuse buffers,
  and make `green_luma` and the 8 x 8 `downsample` parallel over rows (each output
  element's chain is unchanged).

Tests: the existing `the_streaming_ladder_measures_exactly_the_whole_stack_edges`; a new
test that the lane form returns the same scores, bit for bit, as the scalar form on tiles
at every edge; a sidecar from the new path byte-identical to today's. MEASURED kernel
gain 5-6 times (10 with wide vectors); alignment 23.3 s to about 3.5 s (DERIVED: 196
decodes at about 80 files/s, 54 core-seconds of fits on 32 threads, the solve).

### Q10. The preview

The preview is a second render and inherits Q1-Q7. Then:

- Start the main pass's readers and decoders when the preview's fold ends, so the first
  window of planes is decoded while the CA measurement runs (it needs no refinement to
  decode). Run the measurement on half the pool meanwhile.
- Profile `measure_mosaic` (1.39 s, 22 cores: an f64 FFT correlation and two upsampled-DFT
  refinements per tile and channel) before changing it; the green tile's transform is a
  candidate for reuse between red and blue.
- Optional, by the supervisor's memory budget: keep the preview's 25 decoded groups
  (12.2 GB, in device memory when it has room, else in host memory) so the main fold does
  not decode them again: about 1 s.
- Not recommended still: caching the measured refinement on disk. Its key is every input
  of the preview: the preview planes' files and their group members; the stride (RAW
  count, `STREHL_FRAME_PARITY`, `--limit`); the map with its cover fit and resampler and
  `STREHL_REFINE_FRAMES`; the group measurements and their modes; the CA profile; the
  noise model and the gate-floor mode; the pyramid configuration and its environment
  defaults; the self-flat, defect, axial and colour-component modes; white balance,
  levels and exposure gain; the code version. A wrong key is a silently wrong photograph.

Green is unaffected by the refinement (`optics.rs`: `Channel::Green => return t`), so
luma, weights and depth energies are the same in both passes. That does not remove the
preview: red and blue need the raw frames again once the refinement is known.

### Q11. The supervisor

Section 7. Build its measuring half with Q4-Q6 (they need the queues anyway) and its
deciding half after.

### Q12. Capture-time work

Round 1's P9a-c as written (pair journal; `strehl follow` measures pairs and journals
groups as planes arrive; the close solves and renders). With Q9 the pair fits are cheap
enough to run live at any cadence. Add: `follow` records each archive it has fully
verified (path, length, modified time, declared hash) so the closing render may skip the
checksum under Q5f.

---

## 7. The resource supervisor

One component measures the machine and the running pipeline and sets every scheduling
quantity. It never touches arithmetic. It replaces the constants in `decode_ahead`
(`DECODERS`, `PREFETCHERS`, the window formula, the pin rule), `GPU_PREP_FOLD_THREADS`,
the reference pass's slot count and `LADDER_WINDOW_BYTES`.

**What it knows at start (probed once, cached per machine).**

- Processor topology: physical cores, sibling threads, efficiency classes (hybrid CPUs),
  cache groups (`GetLogicalProcessorInformationEx`; sysfs on Linux; `sysctl` perf levels
  on macOS). Decoders go one per performance core; helpers go to sibling threads spread
  across cache groups; efficiency cores take readers and journal work.
- Memory: total, available now, the commit limit.
- Devices: adapters, type, memory budget, binding limits, f64 and passthrough support, and
  the result of a bit-identity self-test of the fold kernels on that adapter and driver
  (cached by adapter, driver version and shader hash). `auto` uses the device only when
  the self-test passed.
- Storage: nothing assumed; measured as the run starts.

**What it measures while running (every 250 ms, smoothed).** For each queue (files read,
files decoded, planes staged, planes in flight on the device) its fill and each side's
wait time; per stage its service rate (reader GB/s per thread, decode ms per file per
thread, device ms per plane, the fold thread's idle fraction); available memory and the
standby cache; device memory in use.

**What it sets.**

- Readers: more while decoders wait for files and the read rate still rises with readers;
  fewer when it stops rising (the drive is the limit) or when the queue is full.
- Decoders: more while planes are late and files/s still rises; fewer when they starve or
  when adding one lowers the per-thread rate (memory traffic). On this host that is the
  difference between 16 and 28 decoders in section 3.6.
- Read mode, per volume: the first files are read unbuffered and timed. If a buffered
  probe of the same file returns faster than any drive could deliver it, the stack is in
  the system cache and reads switch to buffered; otherwise they stay unbuffered. On this
  host that single rule is the difference between 72.6 and 114 files/s on C:, and it
  finds D:'s 5.7 GB/s limit within the first second and stops adding readers there.
- Where each stage runs. With format 2 the decode can run on the CPU or on the device;
  the supervisor puts it where the idle resource is (many idle cores: the CPU; few cores
  and an idle device: the device). The same rule already chooses the route.
- Windows: the file queue, the upload ring's depth, the reference pass's slots, the
  alignment window and the preview's retained groups, each from available memory less a
  reserve, never from a constant. If private memory would push the stack out of the
  system cache during a render that will read it again (preview then fold), prefer the
  smaller window.
- Device layout: accumulator banks, one or two accumulators (section 8, Q14), energies in
  device memory or per-plane read-back, the retained preview groups.
- Route: among bit-identical routes only (GPU preparation, GPU fold with CPU preparation,
  CPU), by the self-test and the memory budget, with the reason printed.

**How.** Worker threads park and unpark against an atomic target count; a controller
thread applies the rules above with hysteresis (change one quantity per interval, keep a
change only if the throughput it was meant to raise rose). The learned operating point
(per volume, geometry and route) is stored in `cache_root()/machine/` and used as the next
render's starting point; a hardware or driver change discards it.

**Everything is a named quantity.** Every scheduling decision lives in one `Plan` value
(readers, decoders, their placement, read mode, each queue's depth, upload slots, device
layout, reference slots, retained preview groups, route, where the decode runs). The
supervisor fills it; `STREHL_PLAN=<file.json>` or one switch per field overrides any part
of it; the resolved plan is printed in the banner and recorded with the output, as the
worker count is today. That makes every quantity tunable end to end and every timing
reproducible.

**What it prints.** The plan in the banner, as today, and at the end the stage that bound
the fold with its rate ("fold bound by the capture drive: 5.6 GB/s"). `STREHL_SUPERVISOR=off`
pins every quantity to today's constants (declare it); every individual quantity keeps an
override (`STREHL_DECODE_THREADS` exists).

**Tests.** A simulated pipeline (stages with configurable rates) checks that the
controller converges to the bottleneck and does not oscillate; the five hashes at three
forced operating points (minimum, default, maximum of each quantity) prove that
scheduling cannot change a byte.

---

## 8. The remaining stops

Part of the plan since the owner's direction. Order after Q1-Q12: Q0 as soon as Q5-Q7
hold on both drives; then Q19 (section 9), the largest remaining change; then Q16, Q13
and Q18; Q14 and Q15 are for other machines and can run beside any of them.

### Q0. The GPU route by default, and the build

- **Default route.** Build the CLI with the `gpu` feature in every release
  configuration, and treat an unset `STREHL_GPU_FOLD` as `auto`. `auto` uses a device
  only when the supervisor's self-test passes on that adapter and driver: a small
  synthetic fold through every kernel compared bit for bit with the CPU (about 0.1 s,
  cached by adapter, driver version and shader hash). Otherwise the CPU route, with the
  reason printed. `off` stays. Before the flip: the five hashes on both routes, and the
  A7C II byte-freeze run twice, once with `auto` on a host with a device and once with
  `off`.
- **Build.** Each item separate, behind a build switch, with before and after from one
  host; none may change a byte.
  - C dependencies compiled with clang-cl, which brings Zstd's assembly Huffman decoder
    (the Windows build has none: the object is absent from `zstd-sys`'s output and MSVC
    cannot assemble it). Zstd is 54 of a format-1 decode's 123 ms. UNVERIFIED gain (no
    clang on this host): measure with `bench2 dec` first.
  - Run-time dispatch for the few CPU kernels whose lanes are independent: the NCC
    offset lanes (MEASURED 5 times at baseline, 10 times with this CPU's vectors), the
    restoration's convolution (MEASURED 0.91 to 0.54 s per channel in round 1), the
    decoder's row helpers. One copy per feature level (x86-64-v3, v4, NEON), chosen once
    at start. No chain is reordered, so the levels cannot differ; test each against the
    scalar form bit for bit.
  - Profile-guided optimisation and fat LTO for release builds, profiled on one
    `--limit 24` render per route. UNVERIFIED; keep only if it measures at least 3 %.
  - Large pages for the big long-lived buffers where the system grants them, falling
    back silently. UNVERIFIED.

### Q13. Group check on the device

Members are already staged for the fold. Integrals (one invocation per row, then per
column, f64), `normal` (one per row, nine f64 accumulators), the witness (one per tile
row); row totals combined on the CPU in order. A large mirror with its own test against
the pinned digest. Worth about 3 s of a first render after Q3; do Q3 first.

### Q14. Devices with less memory

Two accumulators need 7.5 GB beside 2.4 GB of work and 1.1 GB of raw slots. Folding the
even planes, reading back, then the odd planes needs one accumulator; every plane is
still decoded once. It is exact only if nothing shared between the halves depends on the
interleaving: UNVERIFIED (the floor's running sums and the null windows must be shown to
be per-half or order-free; the test is the reference hash under a forced two-pass order).
The supervisor picks the layout from the device's memory budget.

### Q15. The CPU fold

For machines without an eligible device: 0.83 s per plane, bound by memory traffic
(7.5 GB of accumulators touched per frame). Candidate: resident level-0 bands, coarse
levels whole-frame, several frames per accumulator sweep with each element's additions in
frame order. Profile with `native-pyramid-profile` first.

### Q16. Device kernels

After Q19, or today with the stack on C:, the fold is bound by the device: 26.2 ms of
kernels per plane (MEASURED, round 1's profile): gather 9.3 (fourteen dispatches of 0.66),
accumulate 3.7, assemble 3.0, hull 2.3, expand 1.9, probe noise 1.7. Candidates, each
exact, each to be measured with `STREHL_GPU_PROFILE`:

- Accumulate several frames per sweep. The accumulators are 3.8 GB of traffic per frame
  and the sweep is memory-bound; with K frames' pyramids resident one sweep adds all K,
  each element still receiving its additions in frame order inside the kernel. DERIVED
  about 2 ms per plane at K = 4, for 3 GB more device memory.
- The hull's minimum and maximum inside the level-0 accumulate (each plane read once
  instead of twice).
- The gather's coordinates screened in f32 with the f64 form where a rounding boundary is
  near, as the GPU record did for `ln` and `exp`; they were 18 % of a gather there.
- The floor's `beta` on the device (an f64 mirror of `external_accept`): no round trip
  per plane, and two frames can be in flight.

Expected about a fifth of the device's time (ARGUED), 1 s of a fold.

### Q17. Zstd's assembly decoder

Now part of Q0's build items.

### Q18. Speculative reference capture

After Q2 the reference pass is about 1.5 s and re-reads 8 GB. It could disappear: run the
depth tap in the preview as well (25 planes), predict each candidate tile's focus from
that coarse curve, and copy the crops of the frames within a few planes of the prediction
as the main fold passes them (a crop kernel and about 12 MB of read-back per plane);
after the fold use the captured crops where the real plan asks for them and fall back to
Q2 for the rest. Exact by construction (device planes equal CPU planes). UNVERIFIED hit
rate: dump the tap's energies and the plan from one render and simulate before building.

## 9. Q19. Archive format 2

Format 1 was built to get files off the camera's host. Format 2 is built to be read. The
owner's constraint is that it must still compress, because the stacks are large; the
measurement of 3.9 says it can be smaller than format 1 and several times cheaper to
decode at once.

**Goals, in order.** Not larger than format 1. At least three times cheaper to decode per
core. Every chunk verified at a cost that cannot be noticed. A row range readable without
walking headers. Decodable one stream per invocation (a device) as well as by interleaved
streams (a CPU). Encodable on the Pi no slower than today. The original file still
restorable byte for byte.

**Container (`STRHARC2`).**

- The envelope as today (magic, original length, the SHA-256 of the original bytes). That
  hash stays the file's identity and is checked at ingest and by `strehl verify`, not at
  every decode.
- A chunk index after the envelope: per chunk its offset, stored length, kind, first row,
  row count and a 64-bit non-cryptographic checksum of the stored bytes (hardware CRC-32C
  pairs or XXH3; choose by a licence check and a measurement). A reader verifies a chunk
  before decoding it, while it is in cache: about 2 ms per file (DERIVED from 10+ GB/s),
  and a row-range decode is verified like any other.
- Metadata chunks (the original's bytes outside the sample strip, 2 MB per file) stored as
  now, so restoration stays exact.
- Sample chunks of 32 rows (200 per file, 614 KB of samples each), which fit a core's own
  cache with their residuals.

**Sample coding.**

1. *Predictor*, one of two profiles named in the envelope:
   - **S (small)**: format 1's four-neighbour predictor, decoded by Q5a's row-pair chains
     (MEASURED 0.39 ns per sample, 24 ms per file). 7.65 bits per sample.
   - **F (fast)**: the row-above predictor `(a + 2b + c + 2) >> 2`. No dependency along a
     row, so each row is one vector operation on a CPU and one dispatch per row of every
     chunk on a device. 7.81 bits per sample.
   Default S: size is the owner's constraint and its decode is already cheap. F is for
   hosts where the supervisor puts the decode on the device.
2. *Residuals*: the split code of 3.9. Each row's same-colour samples in blocks of 32;
   per block a 4-bit `k` chosen by the encoder from the block's magnitudes; the low `k`
   bits of each zigzag residual stored raw in a bit-packed plane (decoded by vector
   shifts); the high parts entropy-coded with one small static table per `k` per chunk
   (canonical codes capped at 12 bits, or tANS), in eight independent streams per chunk
   whose offsets are in the chunk's header; an escape for high parts past the table.
3. *Size* (MEASURED entropy plus DERIVED headers): about 7.67 bits per sample, 58.7 MB of
   samples and 2 MB of metadata per file against 64.3 MB: 5.6 % smaller, 48 GB to about
   45 GB for the scarab stack. Profile F: 4 % smaller than format 1.
4. *Decode cost per file on one core* (DERIVED; the prototype is the proof): raw bits
   about 3 ms; high parts about 20-25 ms (one coded symbol per sample where Zstd decodes
   two at 0.44 ns each today); predictor 24 ms (S, MEASURED) or about 4 ms (F); checksum
   2 ms. About 50 ms (S) or 30 ms (F) against 123-166 ms, so 16 cores decode 300 files/s
   or more and every fold is bound by the device or the drive.

**Writers.** The PC's receiver transcodes at ingest: it already decodes every arriving
file to verify it (`archive::retain`), so format 2 ships without touching the Pi. The
Pi's encoder may follow if it is not slower than today's 0.40 s per file (the split code
needs no match search; UNVERIFIED on the Pi), which would also shrink the transfer.
`strehl archive upgrade <dir>` rewrites a format-1 capture, each file checked against the
original's SHA-256 before the old one is removed; never automatic, and it is the one
command allowed to write a capture folder.

**Readers.** Everything reads through `strehl-raw-codec` (the engine and `strehl follow`,
the desktop preview, the capture client's storage tag, the receiver's duplicate check,
the restore tool, the Python cross-check); the version dispatch is the envelope magic.
Format 1 stays readable for good.

**Tests.** Round trips on every owned geometry and on hostile inputs (all zero,
full-range noise, clipped highlights, odd sizes); the restored original's SHA-256; a
damaged chunk reported by index; a row-range decode equal to the full decode; a device
decode, when built, bit-identical to the CPU's.

**Steps.** (1) A bench prototype of encoder and decoder for both profiles, measuring size
and files/s against 3.6 and 3.9; go on only at 4 % smaller and 2.5 times faster per core
or better. (2) The codec and the readers' dispatch. (3) The receiver's transcode and the
upgrade command. (4) The device decode and the supervisor's rule for it.

---

## 10. Decisions

**Taken by the owner on 2026-11-18.**

1. The GPU route is the default: Q0.
2. "Checksum policy, needed?": not at every render. Q5f verifies at ingest and records
   it; format 2 verifies every chunk for almost nothing.
3. Both drives, adaptively: Q4 and section 7, measured on both (3.6, 3.8).
4. A new archive format is on the table and must still compress: Q19, 6 % smaller.
5. Custom builds and custom components at every layer are acceptable: Q0, Q19.

**Taken by the owner on 2026-11-18, after this plan.**

1. Flip the GPU default: done (Q0, `2ea8017b9`), behind the device self-test.
2. Existing captures are not rewritten as format 2.
3. The original ARW stays restorable byte for byte.
4. Round 1's implementation is committed (`ace830def`).

## 11. Risks

- **Mapped upload memory as a decode target (Q5d).** It is device memory written through
  the bus; it must never be read, and several threads write disjoint regions of one
  mapping. The row sink enforces write-only by type. If the adapter's mapping is ordinary
  host memory the design still works; measure the write rate on both kinds.
- **New device kernels (Q6a, Q7, Q8)** each mirror a CPU expression. One fused or
  reordered operation moves pixels; each needs its unit test and the hashes.
- **The supervisor** can hide a regression behind adaptation. Keep `STREHL_SUPERVISOR=off`
  and report the bound stage every run.
- **`std::process::exit` (Q1e)** skips destructors: only after the output and journals are
  closed, only in the CLI binary.
- **A new archive format (Q19) holds the only copy of a capture.** A codec fault is data
  loss, not a slow render. Hence: the prototype gate before any product code; every
  written file decoded and compared with the original's SHA-256 before the format-1 file
  or the wire stream is let go; format 1 readable for good; the upgrade never automatic.
- **Skipping the SHA-256 at render time (Q5f)** leaves damage at rest undetected for
  format-1 files between verifications. `strehl verify` and `STREHL_ARCHIVE_VERIFY=always`
  are the answer until format 2's per-chunk checksum makes the question moot.
- **Timing figures marked DERIVED** rest on single runs of an idle host on one stack.
  Replace each with a measurement as its stage lands.

## 12. What was not verified

- That the mapped upload buffer is device-local on this adapter (taken from the earlier
  GPU record), and the write rate from 16 threads.
- The group check's cost after Q3 (argued from the single-thread split, not prototyped).
- Any device kernel of Q6a, Q7 or Q8 (none was written); their device time is assumed
  small because their CPU forms are simple and the device is idle.
- A whole fold from C: or from memory: 3.8 measured the supply there (320 files), not a
  render; 64 GB cannot hold the stack beside today's 22-32 GB of private memory.
- Format 2's decode cost and its encoder (section 9): only the entropy of its code was
  measured; no encoder or decoder exists.
- Zstd's assembly decoder, profile-guided builds and large pages (Q0); the even-then-odd
  fold order (Q14); the device-kernel candidates (Q16); the speculative capture's hit
  rate (Q18); `measure_mosaic`'s internals (Q10).
- The instrumented binary's output pixels (its timers cannot change them, but it was not
  compared).
- A second subject. Every number is from the scarab stack.

## 13. Evidence

[`experiments/a7cr-stacking-performance-2026-11-18/`](../../experiments/a7cr-stacking-performance-2026-11-18/results.md),
2026-11-18:

- `results.md`: what each file is and how to run it again.
- `evidence/`: `runs.txt` (every traced run's summary line and output hash), the stage
  tables and timer summaries of sections 3.2 and 3.3, and the bench outputs of 3.5-3.9
  (`io-bench.txt`, `dec-bench.txt`, `dec-bench2.txt`, `pipe-bench.txt`,
  `pipe-bench-c.txt`, `proto-bench.txt`, `fmt-bench.txt`).
- `trace.py`, `stages.py`, `threads.py`, `tp.py`, `tp-threads.py`, `io-bench.py`: the
  tools of 3.1.
- `bench2/`: the prototypes Q5, Q9 and Q19 start from (`unpredict_rows`, `decode_one`,
  `pipe` in `src/main.rs`; `scores_lanes` in `src/ncc.rs`; the code statistics in
  `src/fmt.rs`).
- `timers/`: the instrumented build's timers as patches; Q6b makes the useful ones
  permanent.
- `anchors.md`: where each stage's code is (functions and approximate lines on
  2026-11-18), condensed from five read-only code surveys (start-up and I/O, the fold
  loop, the codec, alignment and the group check, the tail and preview). The facts this
  plan relies on were confirmed by a timer or by reading the cited function; the line
  numbers will drift, the function names are the anchors.
