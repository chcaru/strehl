# A7CR four-shot stacking performance: implementation plan

**Status:** Implemented in part, 2026-11-18 (stages P1-P7 and part of P9; uncommitted).
Section 12 records what was built, where it departs from this plan, and the measured
results; sections 1-11 are the plan as written on 2026-11-17. A second investigation of
what remains is in [round 2](2026-11-a7cr-stacking-performance-plan-2.md).
**Date:** 2026-11-17 (plan); 2026-11-18 (implementation).
**Scope:** `strehl-cli`, `strehl-gpu`, `strehl-core`, `strehl-raw`, `strehl-raw-codec`.
**Audience:** an implementing agent. Every stage states what to change, why the output
cannot change, how to prove it, and what it should save.
**Goal:** the default four-shot render (`STREHL_PIXEL_SHIFT=remosaic`, colour carry and
optical restoration on) from 346 s to about 25 s on the owner's desktop with the bytes
unchanged, and a closing render of that length at the end of a capture.

Read first: [AGENTS.md](../../AGENTS.md), [ARCHITECTURE.md](../ARCHITECTURE.md) section 9,
[the GPU fold record](2026-11-gpu-resident-fold-and-planner.md),
[the streaming plan](2026-11-a7cr-pixel-shift-streaming-plan.md) (decisions 2, 6 and 7 and
stages B, S1-S3 are assumed here), and
[the four-shot quality proposal](2026-11-a7cr-four-shot-quality-improvements.md).

No milestone identifiers are allocated. Allocate one row per stage in
[milestone-ledger.md](../agents/milestone-ledger.md) before dispatch. Stage labels
(P0-P10) are plan-local.

Labels: MEASURED (a command was run and its output read), VERIFIED (checked against the
code), DERIVED (arithmetic on measured or verified facts), ARGUED, UNVERIFIED.

---

## 1. Summary

The four-shot path is slow for five separable reasons, in order of cost:

1. **The GPU is never used.** The fold refuses more than four planes, device preparation
   refuses pixel shift, and colour carry and restoration refuse the GPU fold. All twelve
   planes are folded on the CPU (188 s).
2. **The depth measurement is a second full pass** (128 s) that decodes, checks and
   gathers every plane only to produce the same green luma the fold computes again.
3. **Every pass repeats the group check** and decodes every member again (three
   registrations and the witness per group, per pass).
4. **A first-time render aligns all 784 RAW files** as ordinary frames (110 s) and
   throws the result away.
5. **The tail is serial in places** (restoration spectra, parts of the collapse).

The plan removes each without changing a byte of output:

| Stage | Change | Saves (DERIVED unless stated) |
| --- | --- | --- |
| P1 | Stop the unused alignment; measure each group once per process | 110 s first-time; the check in every pass after a group's first |
| P2 | Persist group measurements in a journal shared with `strehl follow` | the check on every later render and at the end of a capture |
| P3 | Measure depth during the fold; gather the restoration's reference tiles afterwards from the few rows they need | about 125 s |
| P4 | GPU fold for twelve planes with both half-stack accumulators | fold add 0.85 s -> about 0.1 s per plane |
| P5 | GPU preparation of four-shot groups (one new kernel) | fold 188 s -> about 17 s; preview 20 s -> about 5 s |
| P6 | Tail: restoration spectra and convolution, collapse | about 5 s |
| P7 | A faster archive decode, which is what the GPU path then waits on | fold 17 s -> about 11 s |
| P8 | Wider vectors on the CPU path | measured 4 %; not recommended |
| P9 | First-time alignment and capture-time work (pair journal) | 23 s at the end of a capture |

Expected on this host, against 346 s today: about 230 s after P1 and P3 with the CPU
fold; about 40 s after P4, P5 and P2; about 25 s after P6 and P7. Section 4 gives the
budget line by line and says which numbers are measured.

---

## 2. Rules for the implementer

These repeat the project's contract where this work is most likely to break it.

- **Bytes.** The default render of the scarab run must stay byte-identical, and the
  A7C II byte-freeze must stay 5/5. A hash that moves is a bug in the change until shown
  otherwise. The GPU must be bit-identical to the CPU (`crates/strehl-gpu/src/lib.rs`
  module comment); every new kernel mirrors its CPU expression operand for operand.
- **No reassociation.** No change in this plan may reorder a floating-point sum, fuse a
  multiply-add, replace a division by a reciprocal, or change a chunk boundary. Where a
  loop is made parallel, each output element keeps its own operation order.
- **Switches.** Every new environment switch is declared in `scripts/check-defaults.py`.
  Defaults keep today's bytes.
- **Evidence.** Never `cargo -q`. Look for `Compiling`. Capture `$LASTEXITCODE` before
  piping. Record host load with every timing (the wrapper in section 3 does). Renders one
  at a time.
- **Tree.** Many unrelated uncommitted changes are present. Commit only when asked, with
  `git commit -- <paths>`. Run rustfmt on touched files only. Capture folders are
  read-only; caches and outputs go elsewhere.
- **Licences.** The do-not-open list in AGENTS.md applies.
- **Stop rule.** After each stage: the four checks of section 3.3. Do not start the next
  stage on a red check.

---

## 3. Baseline and harness

### 3.1 Input and build

- Host: Ryzen 9 9950X3D (16 cores, 32 threads), 61.6 GB RAM, RTX 5090 (32 GB, Vulkan
  `maxStorageBufferRange` 4,294,967,295), captures on a Samsung 980 PRO NVMe.
- Input: `D:/StrehlCaptures/stack-1794786793543-11226` (the scarab): 784
  `frame-NNNNNN.ARW.straw` files, 48 GB, 196 four-shot focal planes, buffer 9600 x 6376,
  active 9504 x 6336 at (32, 20), plane 4752 x 3168, seven Laplacian levels and a base.
- Baseline binary: `outputs/a7cr-fourshot-impl/bin/strehl-final.exe`, build id
  `cbca976b7e96-dirty`, CPU only, release profile (`lto = "thin"`, baseline x86-64).
- Command: `STREHL_PIXEL_SHIFT=remosaic strehl stack <dir> --demosaic --out <tif>`.
- Reference output SHA-256:
  `02A6C8C2FAAFC3E266627F1E540F0E98A9690429BADC20B590EB5C32CBCC14CA` (MEASURED again on
  2026-11-17, both baseline runs). The TIFF embeds the build id, so once a commit moves
  it compare decoded pixels and tags with `outputs/a7cr-perf/cmp.py` instead.

### 3.2 Measured baseline (2026-11-17, host idle: 1-2 % CPU, device 1 %)

| Stage | Warm (alignment cached) | Label |
| --- | --- | --- |
| Lateral-colour preview, 25 planes, 2 canonical chunks | 20.1 s | MEASURED |
| Depth map (196 planes) | 128.3 s | MEASURED |
| Fold (196 planes, 1 canonical chunk, two half-stacks) | 188.0 s | MEASURED |
| of which half-stacks finished | 1.8 s | MEASURED |
| Collapse and write | 7.7 s | MEASURED |
| of which optical restoration | 6.5 s | MEASURED |
| Render total (tool) / wall | 324.8 s / 345.6 s | MEASURED |
| CPU time, average cores | 8,078 s, 23.4 | MEASURED |
| Peak private memory | 23.7 GB | MEASURED |

First-time render (empty `STREHL_CACHE_DIR`), MEASURED: wall 478.4 s, CPU 11,241 s. The
extra 132.8 s is two alignments: the 196 planes the render uses (23.1 s, printed) and
the 784 RAW files nothing uses (about 110 s, by subtraction; the two maps' timestamps
agree). Every later stage matched the warm run within 1 %.

Per-call costs inside the passes (profiler, 24 planes, 2026-11-17 evening; the host may
have been in use, so treat as rough): decode with group check 0.38 s; gather 0.22 s;
gate-floor probe 0.30 s; pyramid add 0.85 s; fold 1.15 s per plane.

Micro-measurements (harness in `outputs/a7cr-perf/bench/`, idle host, files in the
system cache), all MEASURED:

| What | Result |
| --- | --- |
| One archive decode, alone (its chunks decode on the whole pool) | 73 ms wall |
| of which the SHA-256 of the samples, one thread | 45 ms (2.75 GB/s) |
| of which reading the 62 MB file | 11-30 ms |
| Decode throughput, 96 files, 1 / 4 / 8 / 16 / 32 outer threads | 11.8 / 33.5 / 44.8 / 48.2 / 49.3 files/s |
| The same at 16 threads without buffer reuse | 46.4 files/s |
| Group check, per group, idle 32-thread pool | 0.19 s: three registrations of 0.039 s, witness 0.073 s |
| Restoration convolution, one channel, radius 32 (3,209 live taps) | 0.91 s (0.54 s compiled for this CPU) |
| One spectrum pair (`SpectrumSum::add_pair`) | 2.14 ms; 1,200 per render, serial |
| Existing GPU path on the 784 files as ordinary 61 MP frames (four planes) | fold 21.7 s, 36 files/s, wall 27.6 s, 15.4 cores, 10.1 GB, device 3.75 GB |

One archive decoded on one thread (harness `split`, MEASURED): 0.196 s, of which
Zstd 0.067 s (1.82 GB/s of output), the predictor and the rest 0.070 s, SHA-256 0.045 s,
file read 0.011 s. An archive is 52 chunks, 50 of them 128-row CFA strips of 2.46 MB.

The device at this geometry (`crates/strehl-gpu/tests/timing.rs` with
`STREHL_TIMING_PLANE=4752x3168`, MEASURED, synthetic four-plane frames, no decoding):
13.8 ms per frame in production order; upload 4.2 ms per 122 MB frame (28.5 GB/s). The
per-kernel table is in section 4.

Prototypes in the harness, MEASURED (they exist to size P7; they are not product code):

| What | Result |
| --- | --- |
| Predictor inverse as it stands / with the row's two neighbours carried in locals | 0.066 s / 0.042 s per file, identical samples |
| Decode as it stands, 384 files, 16 threads | 49.6 files/s |
| The same with each file's chunks on its own thread instead of the shared pool | 43-48 files/s: the ceiling is not the nested pool |
| Cache-resident decode (one thread per file, chunks in order, reused buffers, checksum per chunk while hot), 384 files, 16 threads | 74.4 files/s, every checksum correct |
| The same without the checksum | 87.4 files/s |
| The same on 32 threads | 64 / 78 files/s: slower than 16 |
| Either predictor in the resident decode at 16 threads | 62.7 / 63.1 files/s: no difference under load |
| Restoration convolution, blocks of 16-64 pixels accumulated locally | 0.80-0.87 s per channel against 0.92 s: no real gain |
| Restoration convolution in tiles of 32 rows x 512 columns (the source neighbourhood copied once per tile) | 0.48 s per channel, bit-identical at full size |

Fixed cost of a GPU render, MEASURED: folding one frame of the 784 took 1.2 s of "fold"
(device set-up, one frame, and reading back 3 GB of accumulators in two chunks), so
set-up is under a second and readback is at least 2.5 GB/s.

### 3.3 Checks after every stage

1. Full default render of the scarab: SHA-256 equal to 3.1 (or `cmp.py` identical).
2. `STREHL_FREEZE_REQUIRE=1 cargo test --locked --release -p strehl-cli --test byte-freeze`
   reports 5 passed.
3. `cargo test --locked --release -p strehl-gpu -- --ignored` (GPU stages) and
   `cargo test --locked -p <touched crate>`; clippy with `-D warnings` on touched crates;
   `python scripts/check-defaults.py`.
4. Timing with the wrapper, stage table with `stages.py`, both saved under an ignored
   `outputs/` folder with the binary used.

Quick loop between full renders: the same command with `--limit 24` (about a minute
today). Make its reference with the baseline binary first. It exercises the preview at
stride 1, the depth measurement, both half-stacks and the restoration.

### 3.4 Tools (ignored folder `outputs/a7cr-perf/`)

- `measure.ps1 -Exe X -Log L -EnvPairs "A=1;B=2" -ArgLine "stack|DIR|--demosaic|--out|o.tif"`:
  wall, CPU seconds, peak private memory, device memory, host load before the run.
- `stages.py LOG...`: stage times side by side.
- `cmp.py A.tif B.tif`: decoded-pixel identity and tag differences.
- `baseline.ps1`: the two baseline runs.
- `bench/`: a standalone cargo project timing decode phases, the group check, the
  restoration's convolution and its spectra.
- Profiler: build with `--features native-pyramid-profile`, set
  `STREHL_PYRAMID_PROFILE=on` and `STREHL_PYRAMID_PROFILE_OUTPUT=<fresh path>`; one session
  per process, so add `--refine-ca=off`.
- GPU kernels: `STREHL_GPU_PROFILE=1` prints per-kernel device time (it serialises the
  device, so use it for attribution, not throughput).

---

## 4. Where the time goes, and the budget

### 4.1 What bounds each pass

Three resources matter, and after this plan only the first does.

**Decoding.** One archive costs 0.196 core-seconds alone and about 0.33 with every core
decoding; the ceiling is 48 files per second (section 3.2). A pass over the 784 files
cannot take less than 16 s until the decoder itself is improved (P7). Today's render
makes two full passes and one of 100 files.

**The group check.** 0.19 s per group with the whole pool to itself, so 37 s of
machine time for 196 groups, each time a process first sees them. Today that is paid
in every pass. It competes with decoding for the same cores.

**The device.** MEASURED on the existing four-plane kernels at this geometry
(`STREHL_GPU_PROFILE=1`, 65 frames):

| Kernel | Per dispatch | Per ordinary frame |
| --- | --- | --- |
| `gather` (one site, 15 MP) | 0.66 ms | 6 dispatches, 4.0 ms |
| `noise` (probe fill) | 1.79 ms | 1.8 ms |
| `accum` (four planes) | 0.15 ms | 8, 1.2 ms |
| `level` | 0.15 ms | 7, 1.1 ms |
| `mhc` | 0.47 ms | 2, 0.9 ms |
| `hull` | 0.20 ms | 4, 0.8 ms |
| reduce and expand kernels | | 1.6 ms for seven pyramids |
| the rest (variance, luma, smooth, sums) | | 1.2 ms |
| all kernels | | 12.6 ms |

A four-shot plane on the device, DERIVED from that table: assemble about 1.2 ms (twice
the loads of a full `mhc`), fourteen gathers 9.2 ms, the probe's own kernels 2.6 ms,
twelve hulls 2.4 ms, fourteen and a half pyramids 3.2 ms, levels and smoothing 1.5 ms,
three `accum` groups per level 3.7 ms, luma and variance 0.6 ms: about 27 ms, 5.3 s for
196 planes. Upload of a 490 MB group at the measured 28.5 GB/s is 17 ms, 3.4 s in all,
overlapped. The device can take about 37 planes per second; decoding supplies 12. **The
four-shot GPU fold will wait on decoding, not on the device.** The existing path already
does: it folded the 784 files as ordinary frames at 36 files/s while the device could
take 72.

### 4.2 Budget

Seconds, scarab stack, this host. "Later render" means the group journal (P2) holds the
stack, as it does after `strehl follow` or a first render. Lines without a label are
DERIVED from section 3.2 and 4.1.

| Line | Today | P1 + P3, CPU fold | + P4, P5, first render | + P2, later render | + P6, P7 |
| --- | --- | --- | --- | --- | --- |
| Start, map load | 0.7 (MEASURED, by subtraction) | 0.7 | 0.7 | 0.7 | 0.7 |
| Device set-up (two contexts, then one) | - | - | 2 | 2 | 1 |
| Preview: decode, device, its collapse and measurement | 20.1 (MEASURED) | 20 | 5 + 5 of checks | 5 | 4 |
| Depth pre-pass | 128.3 (MEASURED) | 0 | 0 | 0 | 0 |
| Fold | 188.0 (MEASURED) | 195 | 17 + 32 of checks | 17 | 11 |
| Accumulator readback (7.5 GB) | - | - | 2.5 | 2.5 | 2.5 |
| Reference tiles after the fold | - | 3 | 3 | 3 | 1 |
| Half-stacks | 1.8 (MEASURED) | 1.8 | 1.8 | 1.8 | 1 |
| Collapse, restoration, write | 7.7 (MEASURED) | 7.7 | 7.7 | 7.7 | 3.5 |
| **Total** | **346** | **about 230** | **about 77** | **about 40** | **about 25** |

Device set-up and readback are bounded by the one-frame measurement of section 3.2
(under 1.2 s for set-up plus 3 GB). The fold's 17 s is 784 decodes at 48 files/s plus
a second for staging; its 11 s is the same at the prototype's 74 files/s.

A first render with no journal after P6 and P7 is about 25 s plus the checks: 37 s of
them today, about 19 s after P1d, a few seconds if the check moves to the device (P10).
A first render also aligns (23 s, once). During a capture `strehl follow` pays both as
planes arrive (P9), so the closing render is the last column.

On a machine without an eligible device the second column is the end state, less P6
(about 5 s) and whatever P8 gives.

---

## 5. Findings (all VERIFIED by reading the code unless labelled)

Line numbers are those of the working tree on 2026-11-17 and will drift; the function
names are the anchors.

**F1. The preview's caller aligns the wrong list.** `ca_refine::run_refined`
(`merge_cmd.rs`, about line 8378) calls `alignment_for_observed` on
`only_frame(raw_paths(..))`, every RAW in the folder, "so a fresh stack's alignment is
visible". On a pixel-shift stack that is 784 files and 6,705 pair fits, while both
passes then align and use `StackGroups::planes` (196 files, 1,413 pairs,
`run_pyramid_once`). The 784-file map is never read. MEASURED: two maps in the cache
for this stack, `frames 784, reference 392` and `frames 196, reference 98`.

**F2. The group check runs on every decode.** `RawPyramidSource::decode_with` calls
`StackGroups::prepare` (`pixel-shift-cmd.rs`, about line 673), which decodes members 2-4
with plain `strehl_raw::decode` (a fresh 122 MB allocation each) and runs
`verdict_with`: three `pixel_shift::register` calls and the `witness`. The preview, the
depth pass and the fold each do it again. Inside the check, `register` builds two f64
integral images of about 15.2 M entries (121 MB each) per call, so six per group, and
the reference's integral three times identically (`pixel-shift.rs`, `register`); the
integral's column pass is serial.

**F3. The depth measurement is a pre-pass that recomputes the fold's luma.**
`depth_guide::install_if_requested` (`merge_cmd/depth-guide.rs`, about line 371) loops
serially over every frame through `load_frame` with four planes, no floor probe and no
defect plan, takes `luma = 0.5 * (G1 + G2)` and reduces it to band energies per 8 px
cell. The fold's `load_frame_impl_observed` computes the same native green planes
through the same warp and the same luma expression. With fusion off, the only consumer
of the pre-pass is `optical_restore::plan_tiles`, which needs band 0's depth and
confidence and (for a validity check) band 1's peak count. Band 2 and the `Coherence`
ring are computed and discarded. The source it reads is the plain one, so nothing is
decoded ahead.

**F4. The restoration needs its reference tiles only at the write.**
`optical_restore::observe` copies 136 x 136 crops of the prepared planes during the fold
for up to 200 tiles x 2 frames; `restore` reads them once, after the collapse. Nothing
between needs them. That is what lets F3's pre-pass go (P3).

**F5. The GPU path is closed to this stack.** `GpuFold::build` returns "GPU fold
supports at most four planes" (`strehl-gpu/src/lib.rs`, about line 798);
`gpu_prep_refusal` returns "pixel-shift assembly is prepared on the CPU"
(`merge_cmd.rs`, about line 5114); `colour_carry::activate_if_requested` and
`optical_restore::activate_if_requested` list "the GPU fold is requested" as a blocker;
the fold loop `ensure!`s that carry and restoration "need the CPU fold" (about line
8970). So `STREHL_GPU_FOLD=auto` (what the desktop sets) silently turns carry and
restoration off for four-shot stacks: the desktop and the CLI render different
photographs today. `finish_chunk_main` also builds the retained merge with `BAND_PLANES`
rather than `colour_carry::band_planes()` (about line 6346), which only the refusals
keep from mattering.

**F6. Nothing about the CPU fold is plane-specific.** `BandMerge` is generic in
`planes()`: `accumulate_level` adds the shared weight to `den` once and
`w * (l / 65536)` and `l` to each plane's `num` and `usum`; the hull is per plane; the
luma and every weight come from the caller's green luma. Twelve planes total
943,400,677 accumulator floats (3.77 GB), under the device's 4 GiB binding limit
(DERIVED from `Layout::new`).

**F7. The assembly is integer indexing plus fixed f32 arithmetic.**
`warp_fullres_banded`'s `measured_rows` (`align_cmd.rs`, about line 3571) reads each
site's colour from the member that holds it, `(dn - black) * (1 / gain_j) as f32`, times
the white-balance gain; green is `(a + b) * 0.5 * gain`. `compensate_rows`
(`pixel-shift.rs`) adds `r_k . grad C` with a central difference in x (span 1 at the
frame's edge, else 2) and `0.5 * (down - up)` in y on rows clamped to the frame. The
gather then pulls twelve sites (four native, eight `CARRIED_SITES`) with the same
Catmull-Rom the GPU `gather` kernel already reproduces, and quantises carried sites
exactly as native ones. The gate-floor probe runs after `scratch.measured.take()`, so
it is the ordinary green-only Malvar probe on member 1's geometry: unchanged for groups.

**F8. `strehl follow` already measures every group during capture** and journals the
verdict, but the closing `strehl stack` reads none of it, and the journal lacks the
residuals and the tile ratio the stack needs (`follow-cmd.rs`, `check_plane`).

**F9. Alignment stores only the solved transforms.** Pair measurements are not kept
(`warpmap.rs`), so a cache miss measures every pair again. The pair set is
`(i, i + s)` for `s` in `[1, 2, 4, 8, 16, 32, 64, 96, 128]` (`ladder_pairs`), so frame
`j`'s pairs are known as soon as it arrives; only the solve (under 1 s) depends on the
frame count (reference `n / 2`). At 61 MP the measuring window's batch clamps to 4, so
each step is at most 36 pairs and 4 decodes followed by a barrier
(`measure_ladder_streaming`). Source: a read-only survey agent; spot-check before
relying on a line number.

**F10. Wider vectors are not where the CPU time is.** The build targets baseline
x86-64 with no run-time dispatch. MEASURED: the same source compiled with
`-C target-cpu=native` (AVX-512 here) renders the default stack in 330.6 s against
345.6 s, 4 % faster, and the output is byte-identical (same SHA-256). The CPU path is
bound by memory traffic and scalar chains, not vector width.

**F11. The tail is three serial loops.** MEASURED with the harness: the restoration's
convolution is 0.91 s per channel (2.7 s), and its spectra are 1,200 pairs of 2.14 ms in
a serial tile loop (2.6 s); together 5.3 s of the restoration's 6.5 s.
`core::convolve` sweeps the whole output row once per tap, 3,209 passes over two 38 KB
rows, so it is bound by cache traffic rather than arithmetic. `finish_with_report`
resolves 20 M coefficients and clamps 15 M samples per plane in serial loops, for twelve
planes, three times (two halves, 1.8 s MEASURED, and the full stack).

**F12. Decoding is the floor of any pass.** MEASURED: about 48 archives per second with
every core decoding (0.33 core-seconds per file), flat from 8 outer threads up. A pass
over the 784 files is therefore at least 16 s. Today the render makes two full passes
and a 100-file one. The checksum is 45 ms of each decode and runs on one thread.

---

## 6. Stages

Order: P0, P1, P3, P4, P5, P2, P7, P6, P9; P10 as measurement dictates; P8 is recorded
as measured and not recommended. P1 and P3 alone take the CPU path from 346 s to about
230 s with contained changes. P4 and P5 are the large change and depend on P3 for their
simplest form (with P3 the device never has to hand planes back to the restoration).
P2 follows P5 directly, because without it the group check, not decoding, bounds a GPU
render.

### P0. References

Before touching source: build the tree as it is (`cargo build --release -p strehl-cli
--features gpu`), confirm the full default render reproduces the SHA of 3.1, and make
the `--limit 24` reference with the same binary. Keep both binaries and outputs in an
ignored folder. Run the byte-freeze and the ignored GPU tests once so a pre-existing
failure is not mistaken for a regression.

### P1. Stop repeated and unused work

**P1a. Align what the render uses.** In `ca_refine::run_refined`, build the list the
passes will use: `StackGroups::from_env(&opts.dir, opts.limit)?` and, when it is
`Some`, `only_frame(g.planes.clone())`, else the RAW list as now. Align that list.

- Keep the preview stride exactly as today. `begin_preview(frames)` derives the stride
  from the RAW file count (`stride_for(784) = 8`); with the plane count it would be 6,
  the preview would fold different planes, the measured refinement would move, and so
  would the output. Pass the RAW count for the stride and the plane count for the
  progress total (`TAKING` is `frames.div_ceil(stride)`, which today reports 98 for 25).
- Exactness: the removed alignment's result was never read. The map the passes load is
  keyed by the list they pass, unchanged.
- Test: with `STREHL_CACHE_DIR` pointing at an empty folder, the render writes one map
  (`frames 196`) and the output is identical. Saves 110 s on a first render (MEASURED
  cost of the removed step).

**P1b. Measure each group once per process.** Split `verdict_with` into a measurement
and a judgement:

```rust
/// Everything the checks compute from the four members. Pure function of the samples,
/// the noise model and the code version.
pub struct GroupMeasurement {
    pub offsets: [(isize, isize); 4],
    pub precision: [f64; 4],
    pub residual: [[f64; 2]; 4],
    pub gains: [f64; 4],
    pub parities: bool,
    /// None when the offsets do not cover the lattice (the witness is not run).
    pub witness: Option<WitnessSummary>,   // pair_shift, pair_members, tile_ratio, mean_z2
    pub margins: [usize; 4],
    pub reach: usize,
    pub levels_agree: bool,
}
pub fn measure(frames: [&Frame; 4], noise: &NoiseModel) -> GroupMeasurement;
/// The demotion reason, or None. Cheap; depends on the residual mode.
pub fn judge(m: &GroupMeasurement, residual: ResidualMode) -> Option<String>;
```

`tile_ratio` is computed inside `measure` with today's expression (sort, `q(0.99) /
q(0.5)`), so `judge` needs no tile map. `verdict_with` becomes `measure` then `judge`
and keeps its signature for `follow` and the report command (which wants the whole
`Witness`; keep a variant that returns it).

In `StackGroups` add `measured: Mutex<HashMap<usize, Arc<GroupMeasurement>>>`. In
`prepare`:

1. If the index has a measurement, `judge` it. If demoted, record the demotion and
   return without decoding the other members at all. Otherwise decode members 2-4 and
   park the group with the cached offsets, gains and residuals.
2. Otherwise decode, `measure`, store, `judge`, as now.

- Print the "demoted" line once per frame, not once per pass.
- Exactness: `measure` is deterministic (its parallel sums are collected per row and
  added in row order), so a stored result equals a recomputed one. Add a unit test that
  measures a synthetic group twice on pools of 1 and 8 threads and compares bits.
- Saves the check in every pass after the first that sees a group: all of the fold's
  for the 25 preview planes, and all of a pre-pass's or fold's whichever runs second.
  MEASURED cost of one check: 0.19 s with the pool to itself, roughly 3 core-seconds.

**P1c. Recycle member buffers.** Members 2-4 are allocated per group and dropped on
the fold thread when the gather's `measured` goes out of scope (3 x 122 MB of fresh
pages per plane). Give `StackGroups` a small pool (`Mutex<Vec<Vec<u16>>>`, capped at
about three groups) that `prepare` draws from with `strehl_raw::decode_into` and that
the gather returns buffers to (add `StackGroups::recycle(MeasuredGroup)`, called where
`warp_fullres_banded` finishes with `measured`, through the source like `retire`).
Exactness: `decode_into` overwrites every sample (existing contract).

**P1d. Faster measurement, same bits.** After P1b and P2 the check is paid once per
group ever, but that once is 37 s of machine time for this stack on a first render that
`strehl follow` did not precede, more than the rest of the render after P5. Worth doing
before P5 is called finished:

- Build the reference's `Integral` once per group and pass it to the three fits (it
  depends on member 1 and `balance(member 1)` only).
- Make the integral's column pass parallel by splitting columns into blocks, each block
  running the same top-to-bottom additions. Each element's sum order is unchanged.
- In `normal`, the terms `c`, `gx`, `gy` depend only on the reference and the grid;
  compute them once per group per row and reuse them across the three members and the
  two or three evaluations each. Keep each accumulator's addition order.
- In `witness`, `variance(s)` is evaluated up to three times per site and
  `site_members` once per site; hoist both (the site table has four entries, one per
  parity).

### P2. Group-measurement journal

Goal: a group measured once, by anyone, is never measured again: not by the next render
and not by the closing render of a capture.

- **File.** `cache_root()/groups/<run name>-<hash of canonical dir>.jsonl`, append-only,
  one line per group, never inside the capture folder (streaming plan decision 7).
- **Record.** `{"v": GROUP_CHECK_VERSION, "plane": u64, "sha256": [4 hex strings from
  events.jsonl], "noise": "<identity>", "m": {...}}` where every f64 in the
  measurement is written as the 16-hex-digit `to_bits()` value (serde_json's default
  float parser is not guaranteed to round-trip). Human-readable copies may sit beside
  them under other keys.
- **Key.** A record is used only if the version matches, the four SHA-256 strings equal
  the group's bound hashes in `events.jsonl` (`BoundFile::sha256`, already parsed), and
  the noise identity matches. The noise identity is a stable string of the injected
  model's parameters for the green planes (camera, ISO, black, white, gain and read
  noise as hex bits); add `NoiseModel::identity()` or format it in `pixel-shift-cmd.rs`.
- **Version.** `GROUP_CHECK_VERSION` is a constant beside `measure`. Add a test that
  pins `measure`'s output bits on a synthetic group; its failure message says to bump
  the version. Any change to `register`, `witness`, `balance`, `BLOCK`, the search
  radius or step bumps it.
- **Readers and writers.** `StackGroups::discover` loads matching records into
  `measured`. `prepare` appends a record after a fresh `measure` (one writer lock; flush
  per line). `strehl follow` calls the same `measure` and appends the same record (its
  own journal can keep its verdict line, or become this file). The residual mode is
  not part of the record: `judge` applies it.
- **Trust.** The hashes come from the capture journal and each archive verifies its
  SHA-256 on full decode, so a record cannot attach to different samples without a
  hash collision. A torn last line is ignored. `STREHL_GROUP_JOURNAL=off` ignores and
  does not write the journal (declare it).
- Exactness: the measurement stored is the measurement computed (hex-exact), and
  `judge` is the same function. Test: render with an empty cache, render again, compare
  outputs and assert the second log shows zero fresh measurements.

### P3. Measure depth during the fold

Today: pre-pass (decode, check, gather, luma, energies for every plane), then the fold
(the same again, plus the planes). After: one pass; the reference tiles are gathered
afterwards from the rows they need.

**Eligibility.** The fused route applies when all hold: restoration is active; fusion
is not requested (`depth_guide::requested()` false); not a lateral-colour preview;
`STREHL_FRAME_PARITY` is unset (the pre-pass measures every frame even when the fold
skips some); no defect plan (the pre-pass gathers without it, the fold with it); no
temporal energy. Otherwise the pre-pass runs exactly as today. Add
`STREHL_DEPTH_PASS=fused|prepass` (default `fused` where eligible; `prepass` forces
today's route for comparison). Declare it.

**P3a. Record energies as the fold prepares each frame.** New in `depth-guide.rs`:

```rust
pub(super) struct Tap { /* w, h, cw, ch, frames; energy: [Vec<f32>; 2] (NaN-filled);
                           placed: Vec<bool> */ }
pub(super) fn begin_tap(frames: usize, domain: PyramidDomain) -> Result<TapGuard>;
/// Bands 0 and 1 of this frame's cell energies, from the fold's own luma.
pub(super) fn record(index: usize, luma: &[f32]);
/// What `install_if_requested` does after its loop, for the restoration only:
/// curves, peak fits, band 0's filled depth map, then `optical_restore::plan_tiles`.
pub(super) fn finish_tap(frames: usize) -> Result<()>;
```

- `record` computes `g1 = blur(luma, 1.0)`, `g2 = blur(g1, sqrt(3))`, the two
  differences and `cell_energy` of each, with the existing functions (refactor
  `band_images` so the third band and its `sqrt(12)` blur are optional). Each frame
  writes its own slice of `energy`; there is no cross-frame state.
- `axial_colour::blur`'s horizontal pass clamps the column per tap per pixel, in scalar
  code (about 0.35 core-seconds per plane for these two blurs, DERIVED). Give it the
  vertical pass's shape for the interior columns: accumulate `acc[x] += k[t] *
  line[x + t - r]` tap by tap over a row buffer that starts at zero, and keep the
  clamped loop for the `r` columns at each edge. Each pixel still sums its taps in tap
  order from zero, so the result is bit-identical; test it against the current function.
  This matters under P5, where every core-second competes with decoding.
- Call it from `prepare_frame_into` right after `load_frame_impl_observed` returns
  `true`, where `luma` is final and before anything can change it. With look-ahead the
  calls run in parallel on different frames, which is fine.
- `finish_tap` moves the code after the pre-pass loop into a function both routes call:
  the `placed >= 7` check, `curve`, `fits` for bands 0 and 1 only, the
  `valid[1] > cells / 50` check, band 0's fill, `confident`, `folded`, `plan_tiles`,
  and the "depth map" banner line (say it was measured during the fold).
- Exactness: the luma is the same array the pre-pass would have computed (F3: same
  decode, same group measurement by P1b, same warp, same expression), the energy
  functions are the same code, and everything after is the same code on the same
  numbers. `STREHL_DEPTH_PASS=prepass` against the default must be byte-identical; that
  comparison is this stage's test, on the full stack and on `--limit 24`.

**P3b. Gather the reference tiles after the fold.** After the fold loop and
`finish_tap`, before the half-stacks are finished:

1. Ask the restoration for its planned crops: `(tile, slot, frame, x0, y0)` for every
   tile and both slots.
2. Group by frame. For each frame (in parallel across frames, bounded so that at most
   a few frames' buffers are live):
   a. Take the frame's transform as the fold did: `map.warp(k)`, then
      `frame_refine::adjust`.
   b. For each distinct tile row band of this frame (`y0 - MARGIN .. y0 + TP + MARGIN`,
      plus the analysis rectangle's origin), compute the source row span with
      `band_source_rows` over all twelve sites, widen by one row (compensation) and by
      the largest member offset.
   c. Decode only those rows of the four members (P3c).
   d. Gather those destination rows for all twelve sites with the same code the fold's
      gather uses (below), finish each site exactly as the fold does, and cut the
      crops.
3. Hand each crop to the restoration (`reference[slot] = Some(crop)`), as `observe`
   would have.

The gather: move the body of `warp_fullres_banded`'s per-band closure (span, measured
or Malvar rows, shares, the per-site `gather_rows_catmull_rom_checked` loop) into a
function that takes the band's destination row range and destination slices, and call
it from both the banded loop and a new

```rust
/// Planes in fold order (4 native, then the carried ones when `carry`), each
/// `rows.len() x cols.len()`, with the values `extract_planes` and
/// `colour_carry::copy_carried` deliver for those plane pixels.
pub(crate) fn gather_plane_window(
    frame: &strehl_raw::Frame, measured: Option<&MeasuredGroup>, flat: Option<&[f32]>,
    t: Similarity, geom: PlaneGeometry, carry: bool,
    rows: std::ops::Range<usize>, cols: std::ops::Range<usize>,
) -> Result<Vec<Vec<f32>>>;
```

Finishing, per sample, must be the fold's:

- native site, covered: `((v * inv + black).round().clamp(0, 65535) as u16 as f32 -
  black).max(0.0)` (`writeback_fullres_site` then `extract_planes`);
- native site, uncovered: `(black.round().clamp(0, 65535) as u16 as f32 - black).max(0.0)`;
- carried site: `((v * inv + black).round().clamp(0, 65535) - black).max(0.0)` when
  covered, else `0.0` (the block after the banded loop).

Put each in one small function used by both routes rather than writing it twice.

- First version: gather whole destination rows (the existing row function), then crop
  the columns. DERIVED cost: about 0.15 core-seconds per (frame, tile-row) pair, a few
  seconds of wall time in total.
- Second version: `gather_rows_catmull_rom_checked` computes each output from
  `(start + i) as f64 + ox` with no state carried along the row, so a variant with a
  first-column argument is bit-identical per pixel; the measured rows can likewise be
  built for a column window widened by the taps. That makes the post-pass well under a
  second.
- Exactness test (required, not optional): for at least three frames including a
  demoted one (frame 137 on the scarab) and tiles at the first and last candidate
  rows and columns, `gather_plane_window` equals the crop of `load_frame`'s planes bit
  for bit. Then the end-to-end comparison of P3a.

**P3c. Decode a row range.** The archive's CFA chunks are independent (each is its own
Zstd frame and its predictor restarts at the chunk's first two rows; `cfa.rs`,
`decode_archive` and `unpredict_into`), at most 4 MB of samples, row-aligned. Add

```rust
// strehl-raw-codec
pub fn decode_archive_rows(path: &Path, rows: Range<usize>, samples: &mut [u16])
    -> Result<Option<(CfaMeta, Range<usize>)>>;   // rows actually decoded (chunk-aligned)
// strehl-raw
pub fn decode_rows(path: &Path, rows: Range<usize>, buffer: Option<Vec<u16>>)
    -> Result<(Frame, Range<usize>), RawError>;
```

- Read the envelope and walk the 13-byte chunk headers by seeking (as
  `archive::open_sparse` does), read and decode only the prefix chunks and the CFA
  chunks that intersect `rows`. The `Frame` is built by the same metadata code as
  `decode_with` (share it); its `data` is full-sized with only the returned rows valid.
- No whole-file SHA-256 is possible here. Require that this process has already fully
  decoded and verified the same path (keep a process-wide set of `(path, length,
  modified time)` filled by successful archive decodes); otherwise fall back to a full
  `decode`. Files that are not plain-CFA archives also fall back.
- The caller must assert that every row its band reads lies inside the returned range.
- Test: for several files and row ranges, the returned rows equal the same rows of a
  full decode.

**P3d. When the depth measurement fails.** Today a defaulted restoration whose pre-pass
fails is abandoned before the fold, and the fold then runs without half-stacks in its
ordinary canonical chunks (two on this stack). In the fused route the failure is found
after a fold that used half-stacks in one chunk, whose sums are associated differently.
To keep that case's bytes, return a typed error from `finish_tap`; when restoration is
defaulted, the caller abandons restoration for this render (a flag that
`activate_if_requested` honours, cleared when the render ends) and runs the render
again. An explicit `STREHL_OPTICAL_RESTORE=on` still fails with the same error, later
than today. The retry costs one extra fold on stacks with no measurable depth; say so
in the banner. Two of the pre-pass's failures are knowable before the fold and should
still be raised there, as today: a frame too small for a depth map (`cw < 4 || ch < 4`)
and fewer than seven frames the alignment placed (count the map's placed warps; with
alignment off every frame counts).

- Saves: the whole pre-pass, 128 s here (MEASURED cost), less the post-pass (DERIVED,
  seconds) and the energy computation that moves into the fold (it was inside the
  pre-pass's time; about 0.07 s per frame by subtraction, rough).

### P4. GPU fold for twelve planes and two half-stacks

With preparation still on the CPU. This stage alone makes `STREHL_GPU_FOLD=on
STREHL_GPU_PREP=off` valid for the default four-shot render.

**In `strehl-gpu`:**

- Remove the `planes > 4` refusal. The binding-size check that follows already refuses
  a geometry whose arenas do not fit.
- `accum` takes four planes per dispatch. Record one dispatch per group of four planes
  and add `den` in the first only:

```wgsl
// a = (weight, den, n, count | 0x100 when this dispatch adds den)
let w = work[p.a.x + i];
if ((p.a.w & 0x100u) != 0u) { acc[p.a.y + i] = acc[p.a.y + i] + w; }
for (var c = 0u; c < (p.a.w & 0xffu); c = c + 1u) { /* unchanged body */ }
```

  `Recorder::accum` loops `for group in (0..planes).step_by(4)`. Each accumulator
  element still receives exactly one addition per frame, in frame order.
- A second accumulator buffer for the alternate half: `acc: Vec<wgpu::Buffer>` (one or
  two), bind groups per accumulator (`bind[target][param slot]`), a
  `pub fn select_accumulator(&mut self, target: usize)`, `reset_accumulators` over
  both, and `finish_chunk` / `absorb_chunk` taking the target. `pending_reset` stays
  lazy, so both can be read before the reset. Constructors gain a `halves: bool`.
  Device memory at this geometry: work about 2.2 GB, accumulators 3.77 GB each (DERIVED).
- `MAX_CALLS`: a twelve-plane frame records about 470 dispatches (13 Laplacians of 28,
  one Gaussian of 14, 12 hulls, 7 levels of 8, the base, gathers); the limit of 1024
  holds. Assert rather than assume.
- Tests (`tests/fold.rs`, ignored): the existing bit-identity test at 12 planes; a
  two-accumulator test folding frames alternately against two CPU merges; the absorb
  test at 12 planes.

**In `strehl-cli`:**

- `BandWorker::try_gpu`: pass `self.alt.is_some()`; release `alt`'s totals too.
- Where `swap_half` brackets an add (`fold_observed`, `add_prepared`), also select the
  accumulator: `gpu.select_accumulator(usize::from(self.half))` before the add.
- `finish_chunk`: under a GPU fold, fill `merged_alt` from accumulator 1 the way
  `finish_chunk_main` fills `merged` from accumulator 0 (new merge on the first chunk,
  `absorb_chunk` after, then `absorb_external_remainder` with the alternate counting
  merge). Replace `BAND_PLANES` by `colour_carry::band_planes()` in
  `finish_chunk_main`.
- The fold loop skips `finish_chunk` for a single-chunk half-stack fold so the worker's
  merges can be moved out; under a GPU fold call it (the totals are on the device).
- Remove the three refusals of F5 (the two blockers and the `ensure!`). Keep "depth
  fusion cannot combine with the GPU fold", but decide it in `attach_gpu` (the guide is
  installed before it) so that `auto` falls back to the CPU with a reason instead of
  failing.
- Update the module comments and banner text that say carry and restoration need the
  CPU fold.

Exactness: `BandMerge` is plane-generic (F6) and the device's per-plane kernels are the
ones the four-plane test already pins; the test above extends the pin. End to end:
`STREHL_GPU_FOLD=on STREHL_GPU_PREP=off` must reproduce the reference SHA.

Saves: pyramid add 0.85 s per plane to about 0.1 s (DERIVED: twelve 60 MB uploads and
the device time). The CPU preparation then bounds the fold at roughly 0.5 s per plane,
so this stage is a stepping stone; its own value is the fallback for switches P5
refuses.

### P5. GPU preparation of four-shot groups

Streaming plan decision 2 in code: one kernel in front of the existing `rgb` buffer.

**Raw slots.** `ensure_raw(samples, members)`: two frame slots of `members * samples`
and the probe's slot of `samples`; `raw_base(slot)` scales accordingly; the probe slot
follows the frame slots. At four members: 9 x 122.4 MB device, two 490 MB upload
buffers. `stage` uploads member 1 and, for a parked group, members 2-4 behind it in one
parallel fill and one copy. A single-shot or demoted plane uploads member 1 only.

**Pulls.** Twelve per slot. `xf` becomes `2 * 12 * 8 + 3` f64; the probe's level, sigma
and margin move from `xf[64..67]` to `xf[192..195]` (two places in `fold.wgsl`, and
`XF_NOISE`, `XF_LEN`). `SitePull` gains its site offset; the CLI builds twelve:
`compose(profile, channel_of(ci), t)` and `(dx * 0.5, dy * 0.5)` for the four native
sites then `align_cmd::CARRIED_SITES`, exactly as `warp_fullres_banded` builds `sites`.
The gather's site index becomes `12 * slot + s`.

**Kernel `assemble`** (append to `strict::ENTRY_POINTS` and to `Kernel`, in the same
position). One invocation per full-resolution sample, writing the three planar
channels at `l.rgb` that `mhc` writes for an ordinary frame. Sketch, not compiled:

```wgsl
// a = (rgb, fw, fh, flags: 1 = compensate)
// b = sample index of each member's active origin (slot base + j * samples + ay * stride + ax)
// c = (stride, offsets: 8 bits per member, (ox + 8) | (oy + 8) << 4,
//      site table: 8 bits per parity class (x & 1) | (y & 1) << 1, 2 bits per colour slot
//      [red, green a, green b, blue] as pixel_shift::site_members returns them)
// d, e = bitcast f32 residuals x and y per member, already multiplied by the sign
// f = (black, gain R, gain G, gain B);  g = (1 / exposure gain_j) as f32 per member
fn asm_at(j: u32, x: i32, y: i32) -> f32 {
    let o = (p.c.y >> (8u * j)) & 0xffu;
    let pos = i32(p.b[j]) + i32(p.c.x) * (y + i32(o >> 4u) - 8) + (x + i32(o & 0xfu) - 8);
    return (f32(sensel(0u, u32(pos))) - p.f.x) * p.g[j];
}
fn asm_sample(x: i32, y: i32) -> vec3<f32> {
    let t = (p.c.z >> (8u * (u32(x & 1) | (u32(y & 1) << 1u)))) & 0xffu;
    let r = asm_at(t & 3u, x, y) * p.f.y;
    let g = (asm_at((t >> 2u) & 3u, x, y) + asm_at((t >> 4u) & 3u, x, y)) * 0.5 * p.f.z;
    let b = asm_at((t >> 6u) & 3u, x, y) * p.f.w;
    return vec3(r, g, b);
}
```

The entry point computes `v = asm_sample(x, y)`. With compensation it also takes
`left = asm_sample(max(x - 1, 0), y)`, `right = asm_sample(min(x + 1, fw - 1), y)`,
`up = asm_sample(x, clamp(y - 1, 0, fh - 1))`, `down = asm_sample(x, clamp(y + 1, 0,
fh - 1))`, `span = f32(max(xp - xm, 1))`, and per channel `c`:
`gx = div(right[c] - left[c], span)`, `gy = 0.5 * (down[c] - up[c])`, then
`out = v[c] + (rx * gx + ry * gy)` where `(rx, ry)` is the residual of the member that
supplies the channel at `(x, y)` for red and blue and
`(0.5 * (rxa + rxb), 0.5 * (rya + ryb))` for green. Write every operation as a scalar
expression in this order; do not use `dot` or vector arithmetic.

Rules for the mirror: every float operation in `measured_rows` and `compensate_rows`
appears once, in the same order, on the same operand types; the residuals are converted
on the CPU exactly as `compensate_rows` does (`sign * v as f32`); the inverse gains as
`measured_rows` does (`(1.0 / g) as f32`); the site table comes from
`pixel_shift::site_members` evaluated at the four parities (it depends on parity only).

**Recording.** `record_gather` takes the site list and, for a parked group, records
`assemble` in place of `mhc`; then one `gather` per site into `plane_lv[c][0]`
(native sites to planes 0-3, carried sites to 4-11 in `CARRIED_SITES` order). A plane
without a parked group and with carry on records `mhc` and the same twelve gathers
(the CPU carries Malvar estimates there). The probe is unchanged: it reads member 1's
slot, writes green-only Malvar into `rgb` and gathers sites 1 and 2 through their
pulls.

**Luma for P3.** `record_fold` computes `luma_lv[0]` and then decomposes it in place.
Add a `luma_keep` region (one level-0 plane) to `Layout`, copy the luma into it with
the existing `pack` kernel right after `luma`, and copy that region to a mapped
readback buffer in the submission's `after` closure. A small pool of readback buffers
is recycled; the fold thread collects each a frame or two later without blocking the
device and hands it to a bounded worker queue that calls `depth_guide::record`. The
worker count bounds the fold if it is too small: measure the queue's wait.

**CLI.** `gpu_start` takes the parked group after the decode (`source.take_measured`),
applies `frame_refine::adjust` to the transform as `load_frame_impl_observed` does,
checks what the CPU checks (members agree in levels, stride and active area; a parked
group requires a placed warp), and stages the group. `fold_observed` returns into the
device route before its half-stack bracket, so `gpu_finish` needs the same bracket
around an accepted frame: `swap_half`, select the accumulator, then
`note_external_null_frame` and `add_staged` on the swapped merge, `swap_half` back,
`next_half`. The halves alternate over folded frames, as on the CPU. `gpu_prep_refusal` loses the
pixel-shift refusal and gains, each with its reason: a self-built flat field is
installed; `STREHL_CA_COMPONENTS` is not off; the restoration's tiles are planned by
the pre-pass route (P3 ineligible), because the fold would have to hand planes back for
`observe`. The decode-ahead window and decoder count follow P7.

**Tests.**

- An ignored test in `strehl-cli` under the `gpu` feature (the CPU reference lives
  there): a synthetic four-member group with planted offsets, gains and residuals; the
  device's twelve gathered planes, read back, against the CPU's (`load_frame` with
  twelve planes), bit for bit, for each residual mode, for a demoted group, and for a
  transform that leaves part of the frame uncovered. Add a read-back of the level-0
  planes to `GpuFold` for tests, like `probe_frame`.
- End to end: `STREHL_GPU_FOLD=on` reproduces the reference SHA; the lateral-colour
  preview's measured refinement lines are identical to the CPU's.

Saves: preparation leaves the CPU. Per plane, DERIVED from the measurements in section
4.1: stage about 17 ms (a 490 MB parallel copy at the measured upload rate), device
about 27 ms, against 1.15 s on the CPU. The device is then idle two thirds of the time
and the fold takes what decoding takes: about 17 s at today's ceiling. The preview's 25
planes are 100 decodes (2 s) plus its own collapse and measurement (2.1 s today).

CPU budget under P5. The cores are the scarce resource once the device prepares
frames. Per plane, in core-seconds: decoding 0.8-1.3, staging about 0.15, the depth
energies 0.1-0.45 (see P3a's note on `blur`), the group check about 3 when the journal
misses. Anything added to the fold's CPU side should be costed against the 16 cores
this way.

### P6. The tail

Today 9.5 s: half-stacks 1.8 s, collapse and write 7.7 s of which restoration 6.5 s
(F11).

**P6a. Spectra in parallel, summed in order.** In `optical_restore::restore`, split
`SpectrumSum::add_pair` into a pure `pair_terms(a, b)` (the two transforms and the
per-frequency `cross` and `auto - cross`) and an `add_terms` that performs the `+=` and
counts the tile. Decide which tiles are used first, in order, as now (`no_ref`,
`clipped`). Compute `tile_rgb` and the terms for the used tiles in parallel, in batches
of about 32 tiles (a tile's terms are about 6 MB), then add each batch in tile order.
Every accumulator element receives the same values in the same order. 2.6 s to about
0.2 s (DERIVED).

**P6b. Convolution in cache-sized tiles.** `core::convolve` builds 65 padded source
rows per output row (2.5 MB) and sweeps the whole row once per tap, so its working set
never fits a core's own cache. Accumulating blocks of pixels locally is not enough
(MEASURED: 0.80-0.87 s against 0.92 s). Tiling is: process tiles of about 32 rows by 512
columns, copy each tile's reflected source neighbourhood once into a per-thread buffer
(about 220 KB), and run the taps per block of 32 pixels in the same `(ky, kx)` order
with the same skip of zero taps. Per pixel the sequence stays `acc = 0; acc += t * v`
in tap order, with separate multiply and add. MEASURED with a prototype
(`convolve_tiled` in the harness): 0.48 s per channel against 0.92 s, bit-identical on
the full 9504 x 6336 plane and on small planes with odd sizes and radii 4, 5, 17 and 32.
Three channels: 2.7 s to 1.4 s. Keep the old function in the test as the reference.

**P6c. Kernel design per channel in parallel.** The three `gain_grid` and `kernel`
calls are independent; `par_iter` over channels and collect in channel order.

**P6d. Collapse.** In `finish_with_report` make the resolve loop and the hull clamp
parallel over elements; each element's expression is unchanged. Leave the per-plane
order and the collapse itself alone. Make `absorb`'s elementwise loops parallel the same
way (it adds the odd half-stack into the even one, 3.77 GB, serially). About half of the
2.7 s these take (DERIVED).

**P6e. Write path.** A survey reported serial normalisation and mosaic loops in
`write_merged_observed` (about lines 11021-11104) and `smooth_chroma`'s blur has a
scalar horizontal pass. Profile before touching either; about 1 s is left there.

Expected tail: 9.5 s to about 4.5 s.

### P7. A faster archive decode

Once P5 lands, the fold waits on decoding (section 4.1): 784 archives, 16 s at the
measured ceiling of 48 files/s, against 5 s of device work. One decode is 0.196
core-seconds alone but 0.33 at the ceiling. The harness shows why: the ceiling does not
move when each file's chunks stay on one thread, and a faster predictor makes no
difference under load, so the limit is memory traffic. Each decode writes and reads
about 800 MB: a fresh 62 MB file buffer, a fresh 2.5 MB buffer per chunk, the samples,
and a checksum pass over samples that have left the cache.

**P7a. One file, one thread, cache-resident.** Add a decode for callers that already
run many at once (the decode-ahead threads under GPU preparation):

- the calling thread walks the archive's chunks in order;
- per CFA chunk it decompresses into one reused scratch buffer
  (`zstd::bulk::Decompressor::decompress_to_buffer`), runs the predictor into the
  caller's sample buffer, and feeds those samples to the running SHA-256 while they are
  still in cache;
- prefix and suffix chunks are decoded and hashed in file order, as now, and the prefix
  is kept for the metadata parse;
- the file is read through a reused buffer (or a mapping), not a fresh allocation;
- the per-thread state (file buffer, scratch, decompressor) lives with the decoder
  thread.

Same samples, same checksum verdict, same errors (truncated chunk, trailing bytes,
wrong length, mismatch). Keep the pool-parallel `decode_archive` for a lone decode (the
first frame, the report commands); `strehl_raw::decode_into` chooses by a parameter or
a second entry point, not by guessing.

MEASURED with a prototype of this loop (`bench decode2`; every file's checksum matched
its envelope): 74.4 files/s on 16 threads against 49.6 as it stands, 87.4 with the
checksum skipped. More than one decoder per physical core is slower (64 files/s on 32
threads), which agrees with the existing pinning. A pass falls from 16 s to 10.5 s, or
9 s without the checksum.

Tests: sample-for-sample equality with `decode_archive` on every owned archive
geometry; the existing corrupt-chunk, truncated and wrong-hash refusals run against
the new entry point too.

**P7b. Members are decode jobs.** Today a decoder thread decodes member 1 and then
`StackGroups::prepare` decodes members 2-4 on the shared pool inside the same claim.
Under GPU preparation make the unit of work the file: the decode-ahead plan lists
`(plane, member)`, a plane is ready when its members are, and each decoder runs P7a's
loop. Keep the window in planes (490 MB each decoded): 16 decoders and a window of
about 8 planes is 4 GB. When the journal misses, the group measurement runs on the
shared pool after the plane's four decodes, at most two or three at a time (each holds
six 121 MB integrals before P1d).

**P7c. Prefetch every member.** `RawPyramidSource::prefetch` reads member 1 only; read
the group's other three as well (`StackGroups::members_of`). On a cold cache the pass
needs 48 GB from the disk in about 10 s, so use four prefetch threads for group stacks
and check that decoders do not wait on page faults (the existing A7C II measurement in
`decode-ahead.rs` is the method).

**P7d. Buffer reuse.** With P1c all four members' sample buffers cycle; none is
allocated in steady state.

**P7e. Checksum policy** (owner decision 3). The checksum is 0.045 core-seconds per
file and, in the resident loop, the difference between 74 and 87 files/s: about 1.5 s
of a pass. Options, in order of caution: verify every decode (today); verify a file's
first full decode in a process and skip later ones in that process (helps the 100
files the preview and the fold both read, and P3c already depends on that record);
record verified files in the journal of P2 by `(path, length, modified time)` and skip
on later renders too. Samples are identical in every case. Recommended: the second by
default, the third behind a switch, `STREHL_ARCHIVE_VERIFY=always` to restore today's
behaviour. Declare the switch.

**P7f. Staging.** `stage` copies the group into the mapped upload buffer on the fold
thread (4 ms per member MEASURED, parallel chunks) before each submit. If the per-kernel
profile shows the device idle while the fold thread stages, add upload slots and stage
plane `n + 1` while plane `n`'s probe is collected, as `fold_chunk_gpu` already orders
its work, or stage from the decoder side.

**P7g. The predictor, optionally.** Carrying the row's two running neighbours in locals
instead of reading them back from the row being written takes the predictor from
0.066 s to 0.042 s per file with identical samples (prototype `unpredict_carried` in
the harness, checked on real chunks and on random residuals at widths 2-33 and 1-9
rows). It does not move the 16-thread ceiling, so it only helps lone decodes.

Exactness for the whole stage: decoding is a pure function of the file; nothing here
changes a sample or a verdict.

### P8. Wider vectors on the CPU path

Not recommended. MEASURED (F10): compiling the whole product for this CPU changes no
byte and saves 4 %. The one loop that gains much from 16-float vectors is the
restoration's convolution (0.91 s to 0.54 s per channel), and P6b's restructuring is
worth more there on any CPU. A run-time dispatch layer would add build and test
surface for a few percent. If a CPU-only target ever matters, measure again after P1,
P3 and P6, when the remaining CPU time is the fold's pyramid arithmetic.

### P9. First-time alignment and work during capture

Measured tonight: aligning the 196 planes takes 23.1 s of a first render. During a
capture that work can be done as planes arrive, and the journals of P2 and this stage
make the closing render a warm render.

**P9a. Pair journal.** Store pair measurements, hex-exact, keyed like the warp map
(stack identity by file name and size, solve configuration without the reference) plus
the pair `(i, j)`. `measure_ladder_streaming_with` already takes any plane source and
tags edges with their ordinal; the pair set does not depend on the frame count (F9).
A static align consults the journal before measuring a pair and appends after. The
solve runs on the journaled edges and writes the standard sidecar. Test: a sidecar
solved from a fully journaled run is byte-identical to one solved from scratch.

**P9b. `strehl follow` does the work once.** Per admitted plane it already decodes the
four members and checks the group. Change it to: `measure` and append the P2 record;
build member 1's alignment plane (`green_luma` and `AlignPyramid`) from the frame it has
in hand; measure the new plane's pairs against the window (at most nine: spans 1 to
128) and append them (P9a); drop the frames. The alignment window holds up to 129
planes of 60 MB (7.7 GB; the streaming plan's B3 halves it). DERIVED live work per
plane: decode and check as today (0.2-0.35 s) plus nine pair fits of about 0.5-0.7
core-seconds each in parallel, under a second of wall time, inside the streaming plan's
budget.

**P9c. Close.** At the end `follow` solves from the journal (under a second), writes
the sidecar, and runs the ordinary render, which finds the map, the group journal and,
if memory allowed, the files in the system cache. The closing render is then the warm
render of section 4: about 25 s after the last plane, against 346 s plus alignment
today. The photograph is the offline result by construction (streaming plan decision
6): the same binary runs the same render on the same folder.

**P9d. Static first render.** With P1a the first render pays one alignment (23.1 s).
If that matters after the rest: replace the batch-and-barrier schedule in
`measure_ladder_streaming` by a dependency-driven one (a pair is measured as soon as
both planes are decoded; a plane is evicted when its last pair is done), reuse decode
buffers (`decode_into`), and overlap the first batch. The edge list is sorted by
ordinal afterwards, so the schedule cannot change the solve. A SIMD form of the NCC
inner loop that keeps each offset's own summation order is possible but is a larger
change with its own bit-identity test; do it last.

### P10. Later, by measurement

- **Depth energies on the device.** `blur` is a separable f32 convolution with clamped
  edges and `cell_energy` an f64 sum of 64 squares; both can be mirrored exactly (taps
  computed on the CPU as today and uploaded). Then only 2 MB of cell energies per plane
  crosses back instead of 60 MB of luma. Do it if P5's luma readback or the CPU workers
  bound the fold.
- **One device context per process.** The preview and the render each build a device,
  compile the shader and create 25 pipelines. Keep the device and pipelines in a
  process-wide context and rebuild only the buffers. Worth under a second per render
  (MEASURED bound in section 3.2).
- **Plane-batched pyramid dispatches.** A twelve-plane frame records 336 reduce and
  expand dispatches for the planes; one dispatch could cover all planes of a level
  (plane index from the invocation index, offsets in the parameter block). Same
  per-element operations. Do it if the per-kernel profile shows the gaps between
  dispatches matter at the small levels.
- **Provisional preview during capture** (streaming plan S1): P5's kernels with a
  provisional transform and reduced-resolution sources. Not byte-bound; out of scope
  here beyond noting that P5 is what makes it cheap.
- **Fusion modes.** `STREHL_FUSION=depth` and `calibrated` keep the pre-pass and the
  CPU fold. If they become defaults, give the pre-pass decode-ahead first (its loop
  reads the plain source), then consider the device.
- **The group check on the device.** For first renders that `strehl follow` did not
  precede. The members are already staged for the fold and the device is idle two
  thirds of the time. The integral images, the normal equations' per-row sums and the
  witness's per-tile-row sums are sequential f64 chains that run one invocation per
  row, column or tile row (the witness's pair sums run across a whole tile row, so that
  is their unit); row totals are added in order on the CPU, as now. `balance`'s sums
  are of integers and exact in any order. A large mirror with its own bit-identity
  test against `measure`; do P1d first and decide from what a first render then costs.
- **Accumulator readback in flight.** `read_chunk` copies and maps one 64 MB piece at a
  time. At 7.5 GB, submit several pieces to a small ring of mapped buffers and apply
  them as they arrive.
- **The preview's work, twice.** The preview decodes 100 files that the fold decodes
  again (2 s), and collapses and measures on the CPU (2 s). Keeping the preview's
  decoded planes costs 12 GB; caching the measured refinement needs a key that covers
  every input of the preview (map, groups, profile, every gather switch), and a wrong
  key is a silently wrong photograph. Neither is recommended before everything else
  is done.

---

## 7. Decisions for the owner

1. **Desktop output changes to match the CLI.** After P4 the desktop's
   `STREHL_GPU_FOLD=auto` no longer turns colour carry and restoration off for four-shot
   stacks (F5). Its four-shot renders will then equal the CLI default. Recommended:
   accept; it removes a silent difference.
2. **GPU by default.** `STREHL_GPU_FOLD` is off unless set, and the CLI is built without
   the `gpu` feature unless asked. The speed of this plan is reached only with both.
   Recommended once P5 passes its tests: build the CLI with `gpu` and treat an unset
   switch as `auto`. The A7C II freeze must pass in that configuration first.
3. **Checksum policy** (P7e): verify every decode (today), once per file per process
   (recommended default), or once per file ever, recorded in the journal (behind a
   switch). About 1.5 s per pass between the first and the last.
4. **Second render pass on unmeasurable stacks** (P3d): a defaulted restoration that
   cannot measure depth costs one extra fold to keep today's bytes. The alternative is
   to accept last-bit differences on such stacks.

---

## 8. Risks

- **The assemble kernel's exactness** is the largest. It is integer indexing and a dozen
  f32 operations, but one fused or reordered operation moves pixels. The unit test of P5
  and the end-to-end SHA are both required; neither alone is enough (the unit test can
  miss an input class, the SHA cannot say where).
- **Accumulator memory** at twelve planes is 3.77 GB of a 4.29 GB binding. A larger
  sensor, or one more per-plane accumulator, does not fit; the existing size check
  refuses cleanly and the CPU fold remains.
- **Device memory** about 12 GB (work 2.2, accumulators 7.5, raw 1.1, uploads 1.0 host
  visible). Fine on 32 GB; a 12 GB card would need single accumulators (no restoration)
  or the CPU fold. Report the refusal reason; do not degrade silently.
- **Row-range decode without a checksum** (P3c) relies on the earlier full decode in the
  same process. Keep the fallback to a full decode whenever that is not certain.
- **Journals** can outlive the code that wrote them. The version constants and the
  pinned-output tests are the guard; a mismatch re-measures, it never guesses.
- **Timing claims in this document** that are DERIVED rest on tonight's measurements of
  the four-plane device path at this geometry and of the harness. Replace each with a
  measurement as its stage lands.

---

## 9. Stage acceptance, in one table

Each row is checked with the wrapper on an idle host, after the four checks of 3.3.

| Stage | Done when |
| --- | --- |
| P1 | An empty-cache render writes one warp map; its wall time is the warm time plus one alignment (about 25 s here), not plus 133 s. The log shows each group measured once per process. |
| P3 | No "depth map" pre-pass in the default render; `STREHL_DEPTH_PASS=prepass` and the default are byte-identical on the full stack and on `--limit 24`; `gather_plane_window` equals `load_frame`'s crop bit for bit; total about 230 s with the CPU fold. |
| P4 | `STREHL_GPU_FOLD=on STREHL_GPU_PREP=off` reproduces the reference SHA; the twelve-plane and two-accumulator device tests pass. |
| P5 | `STREHL_GPU_FOLD=on` reproduces the reference SHA; the assembly device test passes for every residual mode, a demoted group and partial coverage; the preview's measured refinement equals the CPU's; fold under 20 s with a warm journal. |
| P2 | A second render measures no group and is byte-identical; a journal written by `strehl follow` is accepted by the render; a version or hash mismatch re-measures. |
| P6 | Restoration about 2.5 s, half-stacks about 1 s, bytes unchanged; the convolution's bit-equality test passes. |
| P7 | The resident decode equals `decode_archive` sample for sample on every owned geometry; fold about 11 s. |
| P9 | A sidecar solved from journaled pairs is byte-identical to `strehl align`'s; after `strehl follow` on a replayed run the closing render measures nothing and aligns nothing. |

## 10. What was not verified

- The assemble kernel sketch in P5 was not compiled. Its exactness argument is by
  reading `measured_rows` and `compensate_rows`; the tests in P5 are the proof.
- The four-shot device time (27 ms per plane) is DERIVED from per-kernel times of the
  four-plane path. Twelve gathers and thirteen pyramids may interact with the device's
  caches differently; measure with `STREHL_GPU_PROFILE=1` once P5 runs.
- Accumulator readback at 7.5 GB is bounded, not measured (at least 2.5 GB/s from the
  one-frame run). If it is slow, read both accumulators through several mapped buffers
  in flight instead of one synchronous 64 MB piece at a time (`read_chunk`).
- The prototypes (resident decode, carried predictor, tiled convolution) were checked
  for identical output and timed in the harness only. They are not product code and
  have had no review.
- The alignment facts in F9 come from a read-only survey agent and were not re-read
  line by line.
- Timings are single runs on an idle host. The warm baseline was reproduced twice
  within 1 % (345.6 s tonight, 341 s earlier the same day); nothing else was repeated.
- A second subject. Every number here is from the scarab stack. A stack with many
  demoted groups, or one whose depth cannot be measured, exercises P1b's and P3d's
  other branches; replay one if the owner has it.

## 11. Evidence from this investigation

All under the ignored folder `outputs/a7cr-perf/` on the owner's desktop, 2026-11-17,
build id `cbca976b7e96-dirty`:

- `baseline.txt`, `baseline-stages.txt`, `base-warm.log`, `base-fresh.log`: the two
  baseline renders (`baseline.ps1`), both outputs' SHA-256.
- `experiments.txt`: decode phases and throughput, the group check, the convolution
  and spectra, the same harness compiled for this CPU, and the existing GPU path on
  the 784 files as ordinary frames (`gpu784.log`).
- `experiments2.txt`: the decode split, device timing and the per-kernel profile at
  4752 x 3168, and the product compiled with `-C target-cpu=native` (`native.log`,
  identical SHA-256).
- `experiments3.txt`, `experiments4.txt`: the predictor and resident-decode prototypes
  and the one-frame GPU render (`gpu-one.log`).
- `experiments5.txt`: the blocked and tiled convolution prototypes.
- `bench/`: the harness source. Its `decode2`, `unpredict_carried` and `convolve_tiled`
  are prototypes for P7 and P6b and may be used as a starting point.
- `prof0.log`, `prof0.json`: the stage profiler's output for 24 planes.

---

## 12. Implementation, 2026-11-18

Built on the owner's desktop the night after the plan, in the order P0, P1, P3, P4, P5, P2,
P6, P7, then the `strehl follow` part of P9. Nothing is committed. Every switch added is in
`scripts/check-defaults.py`. Evidence: ignored `outputs/a7cr-perf-impl/` (`runs.txt` holds
every render's wrapper line and output SHA-256; `bin/` the binary of each stage).

### 12.1 Results (scarab, 196 four-shot planes; all MEASURED, single runs, idle host)

Every render below reproduced the reference output
`02A6C8C2FAAFC3E266627F1E540F0E98A9690429BADC20B590EB5C32CBCC14CA`; `--limit 24` renders
reproduced their own reference (`E37E8E6F...`). The A7C II byte-freeze passed 5/5.

| Render | Wall | CPU s | Peak private |
| --- | --- | --- | --- |
| Baseline (P0 binary), warm | 339.8 s | 8,031 | 23.8 GB |
| Baseline, first time (empty cache) | 478.4 s | 11,241 | |
| After P1, warm / first time | 312.6 s / 340.4 s | 7,411 / 7,896 | 23.4 GB |
| Default CPU route, final binary, group journal warm | 197.5 s | 5,285 | 28.0 GB |
| `STREHL_GPU_FOLD=on`, final binary, group journal warm | 49.0 s | 831 | 32.6 GB |
| `strehl follow` over the finished run, then its closing render (empty cache: follow's checks, one alignment, the render) | 139.7 s | | |

Stages of the GPU route (later render): preview 8.5 s; fold 21 s (from the start of the
fold to the depth map, accumulator read-back included); reference tiles 11.5 s; half-stacks
1.9 s; collapse and write 3.5 s, of which restoration 2.3 s.

Also checked byte for byte: `STREHL_DEPTH_PASS=prepass` against the default; the CPU, GPU
and baseline routes under `STREHL_PIXEL_SHIFT_RESIDUAL=off` and `negate` (`--limit 24`);
the preview's measured lateral-colour refinement, CPU against GPU; a stack whose depth cannot
be measured (`--limit 8`, P3d's re-render) against the baseline, CPU and GPU; a second render
reading the group journal; a closing render after `strehl follow`.

### 12.2 What was built

- **P1.** `ca_refine::run_refined` aligns the focal planes (`StackGroups::planes`); the
  preview stride still comes from the RAW count. Group measurements are split into
  `pixel_shift_cmd::measure` and `judge` (`GroupMeasurement`), cached for the process, and a
  demoted group's members are not decoded again. `pixel_shift::Reference` builds the
  reference integral once; the integral's column pass runs in column strips; the three fits run
  side by side; the witness reads `site_members` from a parity table. Member buffers are
  recycled.
- **P2.** `GroupJournal` (`cache_root()/groups/<run>-<hash>.jsonl`, `STREHL_GROUP_JOURNAL`):
  keyed by `GROUP_CHECK_VERSION`, each archive's declared SHA-256 (the hash its full decode
  verifies) and the noise model's identity; floats as exact bits. `strehl follow` writes the
  same records (`measure_journaled`). The version is pinned by a test of `measure`'s bits.
- **P3.** `STREHL_DEPTH_PASS=fused|prepass` (default fused where eligible). Band 0 and 1
  energies come from the fold's luma (`depth_guide::record`, buffers reused, the differences
  never materialised); `finish_tap` shares `analyse` and `plan_restoration` with the
  pre-pass. The reference tiles' frames are prepared again after the fold by the fold's own
  `prepare_frame_into`, gathering only the bands of rows the tiles need
  (`WarpScratch::bands`) from frames and members decoded over only the rows those bands can
  read (`strehl_raw::decode_rows`, `cfa::decode_archive_rows`, which reads only the chunks it
  decodes and is allowed only for a file this process already verified in full). A band that
  would read a row not decoded is an error, and that frame is prepared again in full.
- **P4.** `accum` takes four planes per dispatch with a flag for `den`; a second accumulator
  (`add_second_accumulator`, `select_accumulator`); the fold reads both back. The refusals
  that kept colour carry and restoration off under the GPU fold are gone.
- **P5.** The `assemble` kernel; members staged side by side in a frame slot
  (`reserve_members`, `RawGroup`); twelve pulls per slot; the probe unchanged; the level-0 luma
  copied for the depth measurement (`add_staged_keeping_luma`, `luma_collect`).
- **P6.** Tiled `core::convolve` (the row sweep kept as the test's reference); spectra
  transformed in parallel and added in tile order (`pair_terms`, `add_terms`); the three
  kernel designs in parallel; parallel resolve and hull clamp in `finish_with_report` and
  parallel elementwise loops in `absorb`.
- **P7 (part).** `cfa::decode_archive_serial` / `strehl_raw::decode_serial` (one thread,
  chunks in order, reused buffers, checksum per chunk), used for group members and for the
  decoders under GPU preparation; members prefetched with member 1; under GPU preparation the
  fold's execution pool has 8 threads; `strehl_raw::identity_cached`, warmed on the decoding
  threads.
- **P9 (part).** `strehl follow` journals every group it checks, so the closing render
  measures none.
- `STREHL_GPU_PROFILE` now prints the per-kernel device table at a GPU chunk's end.

### 12.3 Where the implementation departs from the plan

- **The binding limit is 2 GiB, not 4.** wgpu caps `max_storage_buffer_binding_size` at
  `i32::MAX` (`wgpu-hal` `MAX_I32_BINDING_SIZE`), so F6's claim was wrong: twelve planes'
  accumulators (3.77 GB) span two bindings, `acc` and `acc_hi`, the bank in bit 30 of an
  offset, and the full-resolution channels moved out of the work arena into their own binding
  (`rgbw`). Device tests force both banks with a small bank limit.
- **P3b reuses the fold's preparation instead of a new `gather_plane_window`.** Exactness then
  holds by construction; the cost is the work outside the gather (write-back, extraction,
  carried copy), which is restricted to the same bands. 64 s with whole frames, 11.5 s now.
- **P3d's analysis was wrong.** The pre-pass route plans the fold's chunks before its depth
  measurement fails, so an abandoned restoration still folds in one chunk. The re-render
  therefore activates the restoration and abandons it at the same point with the same message
  (`optical_restore::Without`); with that, `--limit 8` matches the baseline.
- **The GPU fold was not bound by decoding.** It folded at about 30 files/s against the
  48-74 measured for decoding alone. What held it was serial work on the fold thread and
  contention: `strehl_raw::identity` cost 20 ms per archive, reading 60 MB of luma back from
  mapped memory on one thread cost 36 ms (1.7 GB/s; in parallel it is fast), and 32 idle
  rayon workers spun against the decoders (270 CPU-seconds). Prefetching members and a larger
  member-buffer pool each gained little; eight reference slots cost 10 GB of committed memory
  for nothing.
- **P2 is keyed by the archive's declared SHA-256** rather than the capture journal's, so
  any process holding the files can use it.

### 12.4 Not done

- P7e (checksum policy, owner decision 3): every decode still verifies its checksum.
- P7f (staging off the fold thread), P7b as designed (members as decode jobs).
- P9a-P9d: the pair journal and alignment during `strehl follow`; a closing render still
  aligns once (23 s).
- P10.

### 12.5 Owner decisions, as they stand

1. Desktop output: with P4 the desktop's `STREHL_GPU_FOLD=auto` no longer turns colour carry
   and restoration off for four-shot stacks; its four-shot renders now equal the CLI's.
2. GPU by default: unchanged. The CLI still defaults to the CPU fold (`STREHL_GPU_FOLD`
   unset is off) and its default build has no `gpu` feature; the GPU route above needs both.
3. Checksum policy: unchanged (decision 3 open).
4. A defaulted restoration on a stack with no measurable depth renders twice, keeping
   today's bytes.
