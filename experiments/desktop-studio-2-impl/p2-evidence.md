# P2: evidence for every render

**Phase:** P2 of [Strehl Studio 2: implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(sections 3 items 1-3, 6.8, 8 E1 and E3, 9 P2, 11, 12).
**Date:** 2026-11-21. **Branch:** `studio2/p2-evidence`, based on `61effa01b`.
**Evidence labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED, as in the plan.

## What was built

**E1, the GPU fold's admission maps** (`crates/strehl-gpu`).

- `accum` now also samples the level's admission map from the weights it is already reading:
  its first `ceil(sites / 16)` threads write one 16-bit word each, `weight > 0` at each
  lattice site, stored as an exact f32 integer. There is no new dispatch and no new barrier.
  An earlier version used one extra `support` dispatch per level; it was replaced after the
  profile below.
- The sites are the CPU observer's: lattice `lattice(size)` (at most 128 x 96, aspect kept,
  never upsampled) and source `min((2 s + 1) n / (2 m), n - 1)` on each axis.
- The words are copied to a pooled `MAP_READ` buffer right behind each fold, in the fold's own
  command buffer, and mapped asynchronously. `GpuFold::collect_support(wait)` polls without
  blocking and takes finished copies in fold order. It looks only once 4 folds are in flight
  (`SUPPORT_BATCH`). It waits only for folds more than 8 behind (`SUPPORT_RING`), which the
  device finished long ago, or with `wait` at a chunk's end.
- API: `enable_support(lattices)`, `tag_support(frame)`, `collect_support(wait)`,
  `disable_support()`, `SupportMaps { tag, levels }`.

**The evidence file** (`crates/strehl-cli/src/ui-evidence.rs`).

- `<out dir>/evidence.strehl`, in the format of plan 6.8. Per-level extent is that level's
  coefficient grid; level 0's is the analysis domain.
- The log names it once: `STREHL_UI_PROGRESS event=evidence-file path=evidence.strehl version=1`.
- Every plane gets its gate-support maps. Focus energy and gate floor (kinds 2 and 3) are kept
  for at most 384 planes, `floor(j (N - 1) / 383)` for `j < 384`, first and last included.
- Kind 1 (averaging) is reserved: stack maps stay in the log, as instructed.
- The record sequence is the log's diagnostic sequence, so the two sources order as one
  stream.
- The CPU observer (`FrameTap`) and the GPU maps (`Progress::gpu_support`) both write it. A
  frame's GPU records go out in one write.
- Created only with `STREHL_UI_PROGRESS=1` and an output path. A render's later pass with
  the same geometry appends to it; any other pass keeps its maps in the log. A failed write
  falls back to hex lines.

**E3** (`ui-progress.rs`).

- `STREHL_UI_PROGRESS event=frame-unplaced frame=N reason=TOKEN total=T`, once per frame the
  alignment refused. It is emitted after every `align-result` with a map (cache, solved,
  override).
- The reason is made a single token: whitespace and `=` become `-`, other characters `_`, at
  most 160 characters.

**Desktop** (`crates/strehl-ui`).

- `evidence-file.rs` reads the format:
  - an incremental decoder holds a torn tail and skips records that disagree with their
    lattice;
  - untrustworthy framing stops reading;
  - `EvidenceTail` follows the file by length;
  - `read_into` reads a whole file as a stream.
- `jobs.rs`: the render job's thread tails the file only after the log has been read to its
  end, so the log's domain lines always arrive first. It sends `RenderEvent::Evidence`
  batches of at most 64 KiB of file. A full queue holds one batch, as the log does.
- `app.rs`: a five-line ingest arm.
- `pipeline-diagnostics.rs`: `PipelineProgress::ingest_evidence` gives each record the same
  stores as a hex map: the archive (bits packed off the UI thread), the per-position history
  and the recent ring.
  - It never advances the stage.
  - The ring is now ordered by the engine's sequence, so maps from the two readers interleave
    as one stream.
  - The log's own monotonic check moved to `last_log_surface`.
- `process-provenance.rs`: `MAX_ENTRIES` is 65,536.
  - The archive is one vector per level, shared between clones through `Arc`. A
    capture-ordered stream appends instead of shifting every later level. A probe task's
    clone copies no masks.
  - `ingest_packed` takes bits prepared on a worker.
- `workspace-history.rs` `reopen`: reads the evidence file the log names, after the log.
  - The name must be a plain file name inside the run.
  - A damaged file costs the maps, not the reopen.
  - `replay_limit` keeps 512 MiB for older hex-only runs and allows 4 GiB when the run has
    an evidence file.
- Old runs' hex lines still parse unchanged.
- **Accessor for the Stack station:** `PipelineProgress::plane_share(level, frame) ->
  Option<PlaneShare>`. It returns `PlaneShare { share: f32, source: ShareSource }`:
  - `ShareSource::Map` is the plane's own retained map (admitted sites over sampled sites);
  - `ShareSource::Bin { frames, observed }` is the pooled history bin when there is no map,
    an approximation the view must label.
  - `None` means nothing was observed. Cost: one binary search or one bin read.
- The agent snapshot gains `evidence_file`, `evidence_maps`, `evidence_refused` and
  `unplaced_frames` (additions only).
- `PipelineProgress` also keeps `unplaced_frames: BTreeMap<frame, reason>` from the E3 lines.

**Verifier** (`scripts/verify-ui-progress.py`).

- It reads the evidence file with its own decoder and interleaves its maps with the log's by
  sequence.
- It checks that an off or placebo arm neither names nor creates a file.
- It names `STREHL_GPU_FOLD=off`, the CPU fold whose per-step events it checks.
- It follows the engine's `base band :` banner for the base-support check.
- It gains `--merge-only`. Two of its checks were already stale at `61effa01b`; see Open
  issues.

## Commands

All renders read the capture folders and wrote only to `C:\strehl-scratch\p2`.

`p2-evidence-run.py` mirrors the desktop's render: `stack SRC --merge pyramid --srgb --out
DIR\result.partial.tiff --linear-master DIR\master.partial.tiff` (default settings, retained
master). The environment has every inherited `STREHL_*` removed, then `STREHL_UI_PROGRESS`,
`STREHL_GPU_FOLD`, `STREHL_TEMPORAL_ENERGY=off` and an isolated `STREHL_CACHE_DIR` set. It
records hashes, `folded` lines, log and file sizes, and host load from other processes.

```text
python -I experiments/desktop-studio-2-impl/p2-evidence-run.py ENGINE SOURCE OUT --progress {1,0,placebo} --gpu {on,off} --cache CACHE [--env STREHL_FOLD_TRACE=1|STREHL_GPU_PROFILE=1]
python -I experiments/desktop-studio-2-impl/p2-evidence-compare.py RUN_A RUN_B
python -I scripts/verify-ui-progress.py --engine ENGINE --source D:/personal/macro/insects/bug-3/107MSDCF --out OUT --limit 3 --merge-only
strehl-ui.exe --offscreen-screenshot PNG --catalog <copy of projects.json> --open-run RUN --size 1680x1050
```

Engines (release, `--features temporal-energy`, `gpu` by default, built in this worktree's
`target`):

- old, `61effa01b`: sha256 `848909617c1898d4311cabb7a5b601750c5653307513514278aa6387e2b6ed84`.
- final: sha256 `3f2cb01291041922373aa774f7c30756bf17d329d81c81073e8190d92d335f19`.
- Intermediate builds `f89f2b11`, `32a115b4` (extra-dispatch kernel) are reported where used.

Host: 32 logical processors, RTX 5090. Other agents were compiling throughout. Load from
other processes is given per figure.

## Results

### Output bytes, on/off/placebo (engineering ledger rule 26)

MEASURED, 299-plane bracket `bug-3\107MSDCF`, sha256 of the result and linear master:

| Engine | Fold | `STREHL_UI_PROGRESS` | result | master |
| --- | --- | --- | --- | --- |
| final | GPU | 1 / 0 / placebo | `93f480420510f847...6fa59e` | `9fd75acecd1d6b3f...a3954d` |
| final | CPU | 1 / 0 / placebo | same | same |
| old | GPU | 1 (x 15 runs) | same | same |
| old | CPU | 1 | same | same |
| f89f2b11 | GPU and CPU | 1 / 0 / placebo, and 6 timing runs | same | same |

Full hashes: result `93f480420510f847090cb20aeabc239c096b91deedf201e97f9bd0dfd66fa59e`,
master `9fd75acecd1d6b3fb4e331d954b93ba4621437188490dd72491b681049a3954d`.

MEASURED, 1,444-plane bracket `bug-7\100MSDCF`, GPU, progress on: old (x 2), `32a115b4`
(x 2) and final (x 1) all give result
`93cd74c965e52aede5671c7789f172343e8fe6c876015d804002fe2497d7a6c1` and master
`edd7d80950a5c2679ee1f21176d1f93228fa5f909fa2e389e255f73db6686b76`.

VERIFIED by `verify-ui-progress.py --merge-only`, 3 planes, CPU fold:

- The final engine passes every merge check with the plane maps read from the file (66
  records beside 52 log maps, 118 in all, as the old engine's 118 hex maps).
- Its off, on and placebo TIFFs are identical, `878b70dd3fefad3b...`, the old engine's
  bytes. Off and placebo arms created no file.

### CPU and GPU maps identical

MEASURED with `p2-evidence-compare.py` on the 299-plane bracket (final engine):

| A | B | gate-support maps compared | differing | sites compared (on) | float maps | differing |
| --- | --- | --- | --- | --- | --- | --- |
| old CPU, hex in the log | final CPU, file | 2,392 | 0 | 19,466,993 (16,311,283) | 4,186 | 0 |
| final CPU, file | final GPU, file | 2,392 | 0 | 19,466,993 | (GPU writes none) | |
| old CPU, hex in the log | final GPU, file | 2,392 | 0 | 19,466,993 | | |

- 2,392 is 299 planes x 8 levels. Keys are equal and file sequences increase; no torn tail.
- 1,444 planes: the `32a115b4` and final files match, 11,552 maps and 94,014,508 sites.

VERIFIED by tests:

- `crates/strehl-gpu/tests/support.rs` (needs the GPU): the device's maps equal the CPU
  observer's `weight > 0` at every site, frame and level. Fixtures are 193 x 131 (5 bands, 7
  frames) and 640 x 427 (7 bands, 12 frames).
- Its negative control, sampling one coefficient to the left, differs: the test can fail.
- The fold's `den` totals stay bit-identical, and `tests/fold.rs` (5 tests) and the
  self-test pass on the fused kernel.
- `ui-evidence-tests.rs`: every file record equals its hex line byte for byte (identity,
  sequence, bits, min, max, bytes). The GPU's bits give the same hex lines as the CPU
  observer.

### Fold-time cost

The plan's budget is 1 % of fold time. MEASURED, final engine against old, 299 planes:

- **Device.** `STREHL_GPU_PROFILE`, whole render:
  - `accum` 209.96 ms becomes 211.20 ms over 2,392 dispatches: +1.24 ms, 0.06 % of 1,997
    ms of kernel time;
  - total kernel time 1,997.2 ms becomes 1,999.3 ms (+0.1 %).
  - The earlier separate dispatch measured 3.42 ms of kernel time plus 32.6 ms of gaps
    under profiling (`32a115b4`), which is why it was fused.
- **Fold thread.** `STREHL_FOLD_TRACE`, 8 interleaved pairs:
  - "admission maps (collect, write)" is 0.04 s per fold in every new run;
  - "device draining queued fold work" is 0.03 s in every old run and 0.00 s in every new
    run, because the chunk-end collect already waited for the device. The net host addition
    is about 0.01 s, 0.3 % of a 3.2-3.6 s fold (DERIVED);
  - this thread also waits 0.49-2.03 s a fold for decodes, so the addition lands in slack
    (ARGUED).
- **Wall.** Main-pass `fold trace`, 0.01 s resolution, 8 interleaved pairs:
  - old 3.17-3.67 s (median 3.40), new 3.21-6.56 s (median 3.41);
  - paired median delta -0.14 %;
  - runs with other-process load under 30 %: old median 3.245 s (n 6), new 3.235 s (n 4).
  - The 6.56 s outlier ran at 61 % other-process load.
  - Run-to-run spread is about +/- 6 % at 17-61 % other load, so the wall figure cannot
    resolve 1 %. It bounds nothing smaller than the spread.
- **1,444 planes** (UNRESOLVED by wall time): fold 18.6 and 24.6 s (old), 26.2 and 19.0 s
  (`32a115b4`), 21.6 s (final), at 17-47 % other load. Admission maps took 0.09 s of a 26.15
  s traced fold, including the moved 0.03 s drain.

Conclusion: the added work is about 0.1 % of device time and about 0.3 % of fold-thread
time (MEASURED components, DERIVED total). That is under the 1 % budget. Wall-clock fold
time on this shared host shows no difference beyond its spread.

### Sizes

| | 299 planes | 1,444 planes |
| --- | --- | --- |
| Evidence file, GPU fold | 2,472,248 B MEASURED (8,268 B a plane) | 11,939,108 B MEASURED |
| Evidence file, CPU fold | 41,188,562 B MEASURED (float maps for all 299) | about 61.7 MB DERIVED: 11.9 MB support + 384 x 129,486 B float |
| Render log, GPU fold | 2.94 MB, old and new | 6.16 MB MEASURED |
| Render log, CPU fold | 274,467,559 B old; 157,042,383 B new MEASURED | about 0.76 GB DERIVED |
| Plane maps in the new log | 0 lines MEASURED (frame scope) | 0 |

- Both evidence files are under the plan's 100 MB for 1,444 planes.
- The CPU log still carries the live stack maps: per accepted plane, 8 averaging and 8
  coefficient maps and one 512 x 384 preview, about 0.53 MB a plane. That is why its reopen
  bound was raised (Open issues).
- Archive at the cap (MEASURED, `archive_memory_at_the_cap_is_bounded_and_reported`):
  65,536 masks of 128 x 96 in 8 levels, capacity 69,432, 109,984,736 B (104.9 MiB). The
  plan estimated about 96 MiB.

### Desktop reopen of the re-rendered 1,444-plane run

VERIFIED by the offscreen renderer, 1680 x 1050, catalog copy with the run added. The run
was re-rendered with the final engine (folder `runs\b7-final`). The PNGs are not committed
(D10).

- New desktop (release build of this branch, sha256 `38d0edc2a8f4b40d...`): the run reopens
  with diagnostics.
  - "Capture admission" shows 1444/1444 captures observed.
  - Capture contributions is drawn across every scale, and the admitted maps column is
    filled at every level.
  - Admitted detail reads "local 304/10880".
- Control, the same run with the previous desktop (`target-ui\release\strehl-ui.exe`, sha256
  `d58c071f3112151b...`, read only): 0/1444 captures observed, empty admitted column and
  traces, "awaiting aligned contribution". That is today's state of every GPU render.

## Tests and checks

- `cargo test --locked -p strehl-ui` on the committed code: 1,075 passed, 0 failed, 16
  ignored (MEASURED). New:
  - `evidence_file::tests` (6);
  - `workspace_history::evidence_tests` (4): reopen with a file, more than 8,192 maps,
    damaged file plus hex run plus escape name, replay limit;
  - `jobs::tests::evidence_follows_the_log_and_waits_behind_a_full_queue`;
  - provenance cap, clone sharing, packed masks and memory.
- `cargo test --locked -p strehl-gpu --test support --test fold --test self-test --
  --ignored`: 8 passed on the RTX 5090.
- `cargo test --locked -p strehl-cli --lib`, with and without `temporal-energy`: 263 and
  262 passed. All 21 `ui_progress` tests pass, including `ui_progress::evidence::tests`
  (6), and so do the merge observer tests. 13 fail, all research controls that need
  private data or variables this worktree lacks:
  - `STREHL_GREEN_PROBE_OUTPUT`, `STREHL_M194G_BRIDGE_PRIVATE_OUTPUT`, `STREHL_DEFECT=off`;
  - the m194f `cfa-emission-1` files, present only in the main checkout's untracked folders.
  The folders they left in this worktree were deleted.
- `cargo test --locked -p strehl-cli --features temporal-energy --bins --test byte-freeze`:
  5 passed. All five frozen renders HOLD (MEASURED; debug build, 637 s).
- `cargo clippy --locked -p strehl-gpu --all-targets --no-deps -- -D warnings`: clean.
- `cargo clippy` for `strehl-ui` (all targets): the only failure is the known
  `unnecessary_cast` at `capture-workspace.rs:1772` (P0 fixes it).
- `cargo clippy` for `strehl-cli --lib --bins --tests`: nothing in changed code. It fails in
  `image_out.rs`, `merge_cmd.rs:2343/3807`, `focus-step-cmd.rs`, `sensor-master-tests.rs`
  and experiment includes, lines this branch does not touch. That these predate it is
  ARGUED; clippy was not rerun at `61effa01b`.
- `cargo fmt --check`: no diff in changed hunks. Existing diffs remain in `image_out.rs`,
  `session-*.rs`, `lib.rs`, `merge-ui-observer-tests.rs` and eight older hunks of
  `merge_cmd.rs`.

## Deviations from the brief

- The map pass is fused into `accum` rather than being its own dispatch: the measured
  overhead of eight more dispatches per frame was the larger cost.
- The GPU path writes no float maps (focus energy, gate floor). A GPU render's scales view
  shows none, as before P2.
- The CPU path's live stack maps stay in the log, as instructed. To keep long CPU renders
  reopenable, `reopen`'s bound is 4 GiB for runs with an evidence file (a helper beside
  `reopen`). Older hex-only runs keep 512 MiB, as section 11 asks.
- `RenderEvent` has a new `Evidence` variant. Any exhaustive match elsewhere needs an arm;
  only `app.rs` and tests match it today.

## Open issues for the orchestrator

1. (Resolved in round 2.) **CPU-fold logs are still large** (0.53 MB a plane, about 0.76 GB at 1,444 planes),
   mostly the 512 x 384 live preview as hex. Moving the stack maps to the file (kind 1 is
   reserved) or thinning the preview would bring CPU logs in line with the GPU's 6 MB.
2. (Resolved in round 2.) **`verify-ui-progress.py` alignment checks are stale at `61effa01b`.**
   - The streaming alignment no longer reports a `pyramids` phase. Use `--merge-only` until
     they are updated.
   - Its base-support check assumed the plain-mean base; it now follows the engine's banner.
3. **The GPU float maps** could be sampled the same way (`sq` and `var_lv` at the lattice)
   for the 384 kept planes, if the Stack station wants focus energy on GPU renders.
4. **Rendering is decode-bound and noisy** on this shared host (about +/- 6 %). A quiet
   machine would be needed to confirm wall-clock fold time at better than 1 % directly.
5. **Merge order:** `pipeline.rs`, `jobs.rs`, `app.rs`, `main.rs` and the milestone row
   carry small additive hunks that other phases also edit.

## Round 2: the stack's live maps, and long stacks in the desktop

Second task, 2026-11-21, on the integration branch at `82ccbfd45`. Commits:

- `a27c282e7` engine;
- `a91588ade` desktop reader;
- `379d36aab` archive scans;
- `027e3d1ec` verifier.

Commands are as in round 1, plus `p2-stack-compare.py` (independent decoders of both forms of
the stack maps) and `p2-desktop-measure.py` (a native window driven only through the control
interface, on a catalog copy, with `LOCALAPPDATA` pointed into scratch for renders).

Engines:

- "before" is the integration head `82ccbfd45` (sha256 `94412618…`);
- "after" is `a27c282e7` (`ec0cffda…`).

Desktops:

- `a91588ade` (`6c6cf6f6…`);
- `379d36aab` (`76711aa7…`), used for the reopen measurements after the fixes.

### The stack's live maps leave the log

The log still carried each accepted generation's stack maps as hex: 16 averaging and coefficient
maps and a 512 x 384 coarse preview. The desktop needs every generation only for the averaging
history and the revision trace, and only the newest coefficient maps and preview. So now:

- `evidence.strehl` kind 1 holds each generation's averaging maps (bits after a `u32` accepted
  count);
- kind 6 holds each preview's bytes at the desktop's 64 x 48 revision lattice, with min and max;
- `live.strehl` holds the newest generation's coefficient maps and whole preview. It is gathered
  per generation and published whole by a rename. The last rename is retried for half a second
  if a reader holds the file;
- the log names it (`event=live-file path=live.strehl version=1`) and keeps only the
  reconstruction.

The desktop reads kind 1 into the history and the ring, and kind 6 into the revision trace only.
It reads the live file into the live view and the ring, tailing it by size and time during a
render and reading it once on reopen. Old logs' hex lines parse as before.

MEASURED, same input and fold, before and after:

| Run | Render log | Evidence file | Live file |
| --- | --- | --- | --- |
| 299 planes, CPU fold | 157,177,745 B -> 1,099,408 B | 41,188,562 -> 44,484,738 B | 194,335 B |
| 299 planes, GPU fold | 2,944,674 -> 858,548 B | 2,472,248 -> 2,516,344 B | 194,335 B |
| 1,444 planes, CPU fold | 758,439,948 -> 5,260,490 B | 61,661,732 -> 77,580,388 B | 194,335 B |
| 1,444 planes, GPU fold | 6,522,416 -> 4,072,898 B | 11,939,108 -> 11,983,204 B | 194,335 B |

MEASURED identity, `p2-stack-compare.py`, before's hex against after's files:

- 299 planes, CPU fold: all 2,392 averaging maps; all 299 previews at the revision lattice, with
  min and max; and the final preview and its 8 coefficient maps, byte for byte.
- 1,444 planes, CPU fold: 11,552 averaging maps and 1,444 previews, the same way.
- GPU fold: the 4 chunk-end generations.
- The plane maps (`p2-evidence-compare.py`) are unchanged.

VERIFIED by a desktop test: the revision trace from samples equals the trace from whole previews
(29 summaries and the latest field, bit for bit).

MEASURED output bytes. Result and master SHA-256 are equal before and after, on, off and
placebo, on both folds:

- 299 planes: `a801db89…`, `9fd75ace…`;
- 1,444 planes: `7fc03ae4…`, `edd7d809…`.

The result TIFF differs from round 1's `61effa01b` hash by 6 container bytes. Its pixel array and
the master are identical (MEASURED, 3-plane render), and the integration head without this work
already shows it. So it comes from another phase's merge, not from P2.

`verify-ui-progress.py` now passes in full (alignment, merge and bytes) on the current engine, 3
planes, CPU fold: on, off and placebo `49afb7d0…`. Its two stale alignment checks are fixed
(below). Byte-freeze on `027e3d1ec`: 5 passed, all five frozen renders HOLD (MEASURED).

### Long stacks in the desktop

**Process-view paint.** MEASURED, `benchmark_finished_workspace_pointer_sweeps`, release, ms per
frame of CPU paint plus tessellation. The fixture now takes `STREHL_UI_BENCH_FRAMES`.

| Captures | Before the fixes (`a91588ade`) | After (`379d36aab`) |
| --- | --- | --- |
| 130 | process 1.26-1.39, source 0.43-0.56 | process 0.82-1.08, source 0.40-0.48 |
| 1,444 | process 8.98-11.49, source 2.86-4.01 | process 2.97-4.57, source 2.40-3.26 |

The baseline at `61effa01b` was 1.28-1.32. Temporary section timers (not committed) found two
scans over every retained mask in each frame or pointer move:

- the fingerprint read each capture at the pin through a search and a new sample geometry. It
  went from 3.16 to 0.05 ms with `AdmissionArchive::samples_at`, which finds a level's nearest
  site once;
- the region probe recounted each capture's window through two searches and a map insert. It
  went from 1.9 to 1.0 ms with `window_counts_all` and an in-place ordered merge.

Remaining at 1,444: the probe's recount, about 1 ms whenever the pointer crosses a sample cell
(it counts every capture by design), and the source view's 2.4 ms. Neither is attributed further.

**Reopen.** MEASURED; native window; snapshots every 0.25 s; host load 21-51 % from other agents.
"Shown" means `photo_ready`.

| Run | Fully observed | Shown | UI p50 / p95 / max ms, after fixes | UI p50, before fixes |
| --- | --- | --- | --- | --- |
| 299, GPU | 0.40 s | 0.85 s | 1.10 / 1.64 / 12.5 | 2.12 |
| 299, CPU, after | 0.39 s | 0.83 s | 1.39 / 1.87 / 18.0 | 2.44 |
| 299, CPU, before (hex log, 157 MB) | 1.38 s | 1.38 s | 1.40 / 1.87 / 14.0 | 2.83 |
| 1,444, GPU | 0.42 s | 0.86 s | 1.48 / 2.11 / 14.5 | 8.07 |
| 1,444, CPU, after | 0.91 s | 1.39 s | 1.73 / 3.06 / 16.2 | 8.23 |
| 1,444, CPU, before (hex log, 758 MB) | 5.39 s | 5.88 s | 1.33 / 1.95 / 14.0 | 6.64 |

- Resident memory after reopen: 669-701 MiB. The first reopen of a session takes it from 228 to
  669 MiB, mostly the photograph and its tiers.
- Reopen replays on a worker. The two frames over 16 ms (18.0 and 16.2 ms) are single frames at
  the swap.

**Live 1,444-plane GPU render.** MEASURED; native window; desktop `379d36aab`. Two renders, at 78
and 99 % host load including the render.

| Stage | Frames | p95 ms | Max ms | Frames over 16 ms |
| --- | --- | --- | --- | --- |
| Merge (evidence streaming) | 4,033 / 5,322 | 5.72 / 4.67 | 36.3 / 19.6 | 16 / 4 |
| Rendering | 505 / 175 | 5.51 / 5.34 | 21.6 / 16.5 | 4 / 1 |

A diagnostic build (timers in `app.rs`, not committed) logged no frame in which event ingestion
took more than 2 ms, nor any in which the process-surface cache did, during the second render.
Ingest is not the cause of the slow frames (MEASURED). The 13-20 ms merge frames are paint work.
The plan's P3 items cover the candidates: region extraction on the paint path, uncached timeline
lanes, and the Image tier's upload on the UI thread. 47-91 ms frames also occur at stack start,
before any evidence.

### Verifier: the two stale checks

MEASURED at `61effa01b`: both fail the same way there. Both are now fixed:

- **The pyramids phase and per-frame pyramid events.** The streaming solve builds each plane's
  pyramid with its plane, so they are required only when the whole-stack reference reports the
  phase. Pyramid events without the phase are refused.
- **The single `solved` result.** A render that aligns first and then loads the solve for its fold
  (the lateral-CA refinement) reports a second `cache` result. The fresh solve ends at the first
  result. Later results must be cache reads that repeat it exactly, with no other alignment work
  after it.
- Commissioned with a valid streamed run and four negative controls.
- The base-band check follows the engine's `base band :` banner (round 1).
