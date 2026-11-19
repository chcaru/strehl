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
| Later render, GPU route, stack on D: | 45.6 s (49 s in the plan's runs) | 23.0-23.8 s | the main fold reads 47.5 GB from D: in 10.6 s (the drive's floor is 8.3 s); preview 4 s; reference tiles; restoration |
| The same with no switch set (`auto`, the new default) | CPU route, 197.5 s | 25.2 s (self-test recorded on the first run) | as above |
| First render (empty cache folder: no map, no journal) | 107.7 s (plan's run); 83.2 s at the start of Q3 | 48.8 s | group checks on the decoder threads (about 1.6 s a plane), alignment about 5.6 s |
| CPU route, full stack | 197.5 s | 181.3 s | the CPU fold (plan Q15, not built) |
| Process CPU, later render | 799 s | 335-345 s | |
| Peak private memory, later render | 32.6 GB | 26.7-27.1 GB | |

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

## Where the later render's time is now (MEASURED, `trace.py`, 24.7 s run)

Start 0.8 s; preview fold 2.0 s; preview collapse and colour measurement 2.0 s; main fold
10.6 s (45.9 GB from D:); half-stacks 1.9 s beside the reference tiles, which end 3.2 s
later (8 GB read at 1.6 GB/s, CPU-bound row decodes); restoration and write 3.4 s (tile
spectra 0.7 s, highlight guard 0.2 s, three channels 0.3 s each); exit 0.3 s.

## Not built

Q1b (one stack context), Q1f, Q5c-e (file-sized decode jobs, decoding into upload memory,
helper placement), Q7 (collapse on the device), Q11 (the supervisor: today's adaptivity is
the per-file read mode and the device self-test), Q12 (live alignment pairs during
`strehl follow`; `follow` already journals group checks), Q13-Q16, Q18, Q19 (archive
format 2; its prototype gate is the next step there).
