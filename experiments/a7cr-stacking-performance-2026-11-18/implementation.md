# A7CR stacking performance, round 2: implementation results

The stages of [the round-2 plan](../../docs/proposals/2026-11-a7cr-stacking-performance-plan-2.md)
built on 2026-11-18, one commit per stage group on `main`, each checked against the
reference renders before it was committed. Every render in
[`evidence/implementation-runs.txt`](evidence/implementation-runs.txt) (command, binary,
environment, wall and CPU seconds, peak private memory, host load before the run, output
SHA-256).

Input: the scarab capture (196 four-shot planes, 784 archives, 48 GB) on D: (Samsung 980
PRO). Host: Ryzen 9 9950X3D, 64 GB, RTX 5090. Single runs on an idle host unless stated;
two runs of one binary differed by up to 4 s early on (page-cache state), less once reads
went around the cache.

## Results (MEASURED)

| Render | Round 1 final | Now | What bounds it now |
| --- | --- | --- | --- |
| Later render, GPU route, stack on D: | 45.6 s (49 s in the plan's runs) | 19.6-20.5 s (after Q18; 23.0-23.8 s before it) | the main fold, about 10 s: decoders 84 % busy in an 18-plane window behind an in-order fold thread that copies each plane into upload memory (4.3 s); preview 4 s; restoration |
| The same with no switch set (`auto`, the new default) | CPU route, 197.5 s | 25.2 s at Q0 (self-test recorded on the first run) | as above |
| Closing render after `strehl follow` | as a first render | 24.6 s at Q12 (30.2 s without its edge journal) | as a later render |
| First render (empty cache folder: no map, no journal) | 107.7 s (plan's run); 83.2 s at the start of Q3 | 41.2-42.0 s (48.8 s before Q18) | group checks on the decoder threads, about 16 s of wall time (Q13 below) |
| CPU route, full stack | 197.5 s | 179.5-181.3 s | the CPU fold (plan Q15, not built) |
| Process CPU, later render | 799 s | 286-298 s | |
| Peak private memory, later render | 32.6 GB | 30.3 GB (26.7-27.1 GB before Q18's 4,501 crops) | |

Every render above wrote the reference bytes (full `02A6C8C2...`); every commit also
reproduced `--limit 24`, `--limit 8` and both residual modes on the GPU route and
`--limit 24` on the CPU route. A7C II byte-freeze 5/5 after every stage, and under `auto`
and `off` after Q0.

## Stage by stage

| Stage | Commit | Later render | Notes |
| --- | --- | --- | --- |
| Q1a, c, d, e | `dccb54242` | 45.6 to 41.9 s (second run of a new binary) | Sony preflight skipped for unsupported cameras; host fold state never allocated under a GPU fold; one GPU context and an on-disk pipeline cache; worker and half-stack freed on helper threads |
| Q4, Q5a-b | `dccb54242` | 41.9 to 37.5 s | whole-file readers (unbuffered unless the file cache holds the file), row-buffered predictor, checksum fed per row |
| Q5f | `5c700c52a` | 37.5 to 35.1 s | decodes vouched for by transfer receipts or earlier verifications skip the SHA-256 (883 of 883 here) |
| Q2 (steps 1-3) | `463a3c983` | 35.1 to 28.8 s | reference tiles gathered over the tiles' columns only: 10.3 to 4.1 s; 153 of 153 frames checked bit for bit (`STREHL_REFERENCE_CHECK=1`) |
| Q6a-b | `4173f9d1c` | 28.7 to 25.6 s | depth energies on the device (196 of 196 frames bit-identical, `STREHL_DEPTH_CHECK=1`); `STREHL_FOLD_TRACE` |
| Q2 step 4, identity | `f9ce16422` | 25.6 to 24.8 s | identity from the decode's own metadata (72 ms to 0.1 ms a plane); reference tiles beside the half-stacks |
| Q3a-c, Q9a | `2e1af590e` | (first render) 83.2 to 50.9 s | checks on a one-thread pool per decoder; witness without the discarded bins; integral column pass in place; NCC offset lanes with an AVX-512 copy |
| Q0 | `2ea8017b9` | 25.2 s with no switch | GPU route by default behind `strehl_gpu::self_test` |
| Q8 | `7723e9fec` | 24.1 s | restoration convolutions on the device, bit-identical (device test; every scarab convolution under `STREHL_RESTORE_CHECK=1`) |
| Q10 (read-ahead) | `3203c0209` | 23.0-23.8 s | the main pass's first files read while the preview collapses |
| Q3 (witness rows) | `b4d0a3629` | (first render) 50.9 to 48.8 s | the witness's terms per row, then the sums in order: 588 to 400 ms a group on one thread |
| Q12 | `93d425bae` | (closing render after `strehl follow`) 30.2 to 24.6 s | an edge journal keyed by both archives' SHA-256 and the estimator; `follow` measures each plane's ladder pairs as it arrives (1,413 pairs); the solve decodes only frames an unjournalled pair needs; warp maps byte-identical (`9EBD2B78...`) fresh, journalled and without |
| Q18 | `b929f7d73` | 22.8 to 19.6-20.0 s (capture off against on, alternating) | the preview measures depth on the device and predicts 643 candidate tiles; the main fold copies their windows of each gathered plane for frames within 3 of the predicted focus (4,501 crops); the plan takes 373 of its 400 reference crops from them and gathers 10 frames instead of 153; peak memory +3.4 GB (30.3 GB) |
| Fold end | `0d106d3df` | main fold 10.2-10.4 to 9.9-10.1 s | the totals' readback after the fold was 1.45 s, mostly allocating the host totals on one thread (mimalloc zeroes reused memory); parallel fill, pipelined readback, parallel copy-out: 1.1-1.2 s |

## Measured and not kept

- A 16-thread fold pool instead of 8: 29.9 s against 28.5 s.
- Depth records on the 32-thread execution pool instead of the fold's pool: the decoders
  lost their cores (625 to 980 ms a plane), 30.8 s against 28.7 s. The device energies
  (Q6a) replaced both.
- Twelve reference slots instead of four: no faster (4.6 s against 4.1 s), 19 GB more peak
  memory.
- 28 decoder threads on a first render: 63.3 s against 62.3 s, 10 GB more memory.
- Reference-tile row decodes ahead of the slots on 12 threads: the pass fell from 5.1 to
  4.2 s but the half-stacks beside it rose from 1.9 to 5.8 s (the row decodes are CPU-bound
  too, about 53 ms a partial file); no net gain, reverted.
- The witness's terms gathered into arrays for vector code: 617 ms (baseline) and 606 ms
  (built for this CPU) against 400 ms for the row form.
- Q10's second half, as a deeper read-ahead of the main pass during the preview's tail
  (12, 24 or 40 planes, with the hand-off raised to match): the main fold stayed at
  10.3-11.0 s in every arm (`q10x-*`). The drive is not what bounds the main fold: about
  13 decoders are 84 % busy and idle the rest waiting for room in the 18-plane window,
  while the in-order fold thread spends 4.3 s copying planes into upload memory.
- Q5c, as members 2-4 offered to idle decoders as jobs (file-sized work without changing
  the window): decoder idle time 21 s to 9 s, main fold unchanged (9.95-10.08 s against
  9.88-10.07 s, three alternating pairs `ab-*`), 20 CPU-seconds more; first renders
  44.5/45.1 s against 45.9/45.3 s, within their noise. Reverted.

## Q18: the hit-rate simulation

[`evidence/q18-hit-rate.txt`](evidence/q18-hit-rate.txt). The preview's 25 planes predict
each planned tile's focus within a frame (p90 1.0, max 2.6 frames) but not which tiles the
plan ranks highest (81 of the 200 in the preview's own top 200). Capturing every preview
candidate (643 tiles) at three frames either side of its predicted focus holds both
reference crops for 186 of 200 tiles; the rest would fall back to Q2's gather. About 4 GB
of crops, read back over the fold. The simulation's first version reported a perfect
prediction because `analyse` builds its curves from every frame whatever its mask says;
its stride-1 control now reproduces the plan and the stride-8 run shows misses.

Built (Q18 row above). VERIFIED: under `STREHL_CAPTURE_CHECK=1` all 373 captured crops the
plan would use equal the gathered ones bit for bit, and a build that shifted every window by
one pixel failed that check (exit 1). The first build's output differed from the reference
although its crops were identical: after the fold, `observe` still wrote every tile a
gathered frame served, overwriting captured crops with windows that gather no longer
computed. Q2's `STREHL_REFERENCE_CHECK=1` caught it (frame 181); the fix skips slots a
capture filled, and the remaining 10 frames pass that check.

## Where the later render's time is now (MEASURED, `trace.py`, 24.7 s run)

Start 0.8 s; preview fold 2.0 s; preview collapse and colour measurement 2.0 s; main fold
10.6 s (45.9 GB from D:); half-stacks 1.9 s beside the reference tiles, which end 3.2 s
later (8 GB read at 1.6 GB/s, CPU-bound row decodes); restoration and write 3.4 s (tile
spectra 0.7 s, highlight guard 0.2 s, three channels 0.3 s each); exit 0.3 s.

## Q13: what a first render spends on group checks (MEASURED, not built)

A first render after Q18 took 41.2-42.0 s against 19.6-20.5 s for a later render. Under
`STREHL_FOLD_TRACE`, a first render's main fold took 23.4 s against about 10 s (members 2-4
1,555 ms a plane against about 375 ms when the journal holds the group) and its preview
4.6 s against 2.0 s: about 16 s of wall time are the group checks, CPU-bound on the
decoder threads (14.3 of 16 cores busy). The plan's estimate (about 3 s after Q3) was low.

Per group, with sixteen checks running at once (temporary timers, `tmpcheck` run): member
1's integral image 119 ms, the three members' fits 590 ms (each another integral of about
15 M f64 samples and up to seven Gauss-Newton passes), the witness 628 ms. Every value
reaches the journal and the gates, so a faster form must keep each f64 addition in its
order; the plan's device mirror does (integrals one invocation per row then per column,
`normal` one per row, the witness one per tile row, totals combined on the CPU in order),
with members already staged for the fold. Worth up to about 16 s of a first render, and
nothing for a render after `strehl follow`, which journals every group during the capture.

## The desktop (MEASURED, 2026-11-18, later)

Asked whether the work reached the desktop: the engine did (the desktop runs it in a child
process with `STREHL_GPU_FOLD=auto`), the four-shot path did not. Found by reading
`crates/strehl-ui/src/jobs.rs` and confirmed by running its render function (`run_render`,
the app's own request: every worker, a retained master, default settings) on the scarab
capture through an opt-in test (`desktop_render_of_a_real_capture`), with `LOCALAPPDATA`
pointed at an empty scratch folder so first and later renders are both measured.

- **Four-shot never assembled.** The desktop removes every inherited `STREHL_*` variable and
  never set `STREHL_PIXEL_SHIFT`, so a four-shot capture stacked as 784 ordinary frames.
  Now `strehl_cli::pixel_shift_cmd::four_shot_planes` lists a capture's focal planes; the
  desktop's scan shows them as its captures (timeline indices, capture limits and source
  ranges then count planes, as the engine does) and the render sets `remosaic`. `focus
  inspect` on a four-shot folder lists the same planes, so the metadata panel still matches.
- **Every render started cold.** Each render had its own new `STREHL_CACHE_DIR` inside its
  output folder, so no warp map, group or alignment-pair journal, verified-archive record or
  GPU self-test and pipeline cache ever carried over. Renders now use the engine's shared
  cache (`strehl_cli::default_cache_root`), as the CLI and `strehl follow` do.
- **Every full-resolution A7CR render failed publication** ("Memory limit exceeded"):
  `image` reserves the decoded buffer from the viewer's 512 MiB budget and gives the TIFF
  decoder what is left, so any 16-bit RGB TIFF over 44.7 MP was refused. The budget is now
  twice the viewer's own 80 MP limit at 16-bit RGBA; a test writes a 48 MP TIFF that the old
  budget refused.
- **The confidence map, on by default in the desktop, cost two passes.** The lateral-CA
  preview built one too (82 s, then overwritten); it no longer does. The render's own pass ran
  all 196 planes serially because an optically restored stack folds in one chunk; its integer
  counts are now split across workers by memory and cores (6 here), 81 s to 50 s.

| Desktop render, scarab | Four-shot on, before the confidence and publication fixes | Now |
| --- | --- | --- |
| First render (empty cache) | about 205 s of engine time (preview 94 s, render 102 s); publication of the same bytes failed in the next run | 97.4 s, published |
| Later render | (every render was a first render) | 73.8 s: preview 5.1 s, main fold 13.2 s, confidence pass 50.4 s |

All four runs wrote the same three files: result `FA5E8482...`, master `7F06B3CB...`,
confidence map `FE8A612A...`; the preview's skipped map and the split pass change no byte.
The confidence pass is now most of a later desktop render; it gathers every plane again on
the CPU (colour-carried, about 0.4 s of the machine a plane). Moving it to the device, where
the fold already gathers the same planes bit for bit, is the next step there.

## Stacking during capture in the desktop (MEASURED, 2026-11-19)

The owner asked for stacking during capture from the Capture screen, and for the confidence
map to be off by default. Both are built.

- **The checker.** While the newest run registered with this PC's receiver has a capture
  journal and no `result.json`, the desktop runs `strehl follow` on it. It runs as a child
  at below-normal priority, with the shared cache and no inherited `STREHL_*` overrides,
  the same environment its renders get. The Capture screen shows the plane journal: planes
  checked, four-shot groups that pass, planes needing attention, retake focus positions and
  alignment pairs. Once the checker has finished and the run verifies complete, the desktop
  opens it in Projects and stacks it with the current settings. It does this only if that
  interrupts nothing; otherwise it leaves a note. A run idle for 10 minutes with the camera
  not capturing stops being followed.
- **One checker per run.** `follow` now holds an exclusive operating-system lock beside its
  journal. A second `follow` on the same run exits with an error naming the lock. A second
  desktop window shows the first one's progress instead of checking again, and takes over
  if that checker ends while the capture is still running.
- **A receiver defect this exposed.** The receiver replaces `events.jsonl` with
  `MoveFileExW`. On Windows that fails with "Access is denied" while another process has the
  file open, even one opened as the engine opens it. With a checker reading the journal
  every second, an update can collide with a read. The camera host retries for 10 s, so a
  capture would have recovered, but each collision showed "Waiting for PC receiver" and
  stalled the queue. The receiver now retries the replace for up to 1 s. A test holds a
  reader open across an update, and it fails without the retry. The first end-to-end
  attempt hit exactly this in the replay script, which replaced the file the same way.
- **The confidence map** is off for new stacks; saved recipes keep their own setting.
- `scripts/replay-capture.py` re-creates a recorded run file by file at its recorded pace
  (scaled), hard-linking RAWs on the same volume. It can also register the run with a
  scratch receiver configuration.

The test was a release desktop, headless on the Capture tab, with `LOCALAPPDATA` pointed at
an empty scratch folder, following a 3x replay of the scarab capture: 196 four-shot planes,
784 RAWs, 1072 s.

| Scarab capture, desktop, empty cache | Wait after the capture ends |
| --- | --- |
| Before this round's changes (confidence map on) | 97.4 s (the first render above) |
| Confidence map off, stacked after the capture (no checker) | 51.8 s |
| Stacked during the capture | 27.7 s: `result.json` landed 01:22:02.9, photograph saved 01:22:30.5 |

During the capture the checker never fell more than one plane behind arrival. The closing
stack took 1413 of 1413 alignment pairs from the edge journal and reused 171 + 25 group
measurements, measuring none (engine 8.3 + 17.6 s). The master is `7F06B3CB...` in all three
rows. The result is `579111D0...`, which is `FA5E8482...` once the TIFF's Software tag
carries the earlier build's identity. Stacking during the capture therefore writes the same
photograph as stacking afterwards. At the real pace (one plane every 16 s) the checker is
idle most of the time.

**On the rig (2026-11-19, 6 planes x 4 shots, a short test range).** The first live stack found
a bug the replay could not: the desktop ranked registered runs by name. A hand-named test run
(`stack-wifi-check-...`) sorts after every timestamped one, so the real capture was never
followed. Runs are now ranked by their folders' last activity. Run again, the checker started
5 s after Start and checked each plane in 0.23-0.33 s. The photograph was saved 6.8 s after
the capture ended, taking 11 of 11 alignment pairs from the checker. Every plane was demoted
for too little scene structure, as the test range was mostly out of focus. `follow` had flagged
all six as retakes; it now flags only the reasons a retake can fix. Those are witness
misregistration, locally disagreeing witness tiles, and disagreeing black or white levels;
too little structure, a wrong shift pattern and photosites leaving the sensor are excluded.
Timing on the rig: a plane every 15.9 s, 14.2-14.5 s of it the four exposures. The fourth RAW
was durable on the PC 1.1-1.3 s after the camera finished.

## Not built

Q1b (one stack context), Q1f, Q5d-e (decoding into upload memory, helper placement; Q5c
was measured and not kept, above), Q7 (collapse on the device), Q11 (the supervisor:
today's adaptivity is the per-file read mode and the device self-test), Q13 (measured above)
to Q16, Q19
(archive format 2; its prototype gate is the next step there).
