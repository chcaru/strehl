# Strehl Studio 2: implementation log

Implements the locked spec, [`docs/proposals/2026-11-desktop-studio-2-implementation.md`](../../docs/proposals/2026-11-desktop-studio-2-implementation.md).

The owner started the run on the night of 2026-11-21 and went to sleep. Their instructions:

- "take the implementation forward now … work autonomously and finish the implementation e2e";
- "you can upgrade egui if you want";
- "keep a critical eye out for supporting large+ stacks and that everything is highly performant and responsive when working with them."

## Organisation

- The orchestrator integrates on branch `codex/pr-3-local-2026-10-31` in the main checkout and pushes `HEAD:main`.
- Phase agents work in git worktrees at short paths, because the default worktree location hit Windows path-length limits even with `core.longpaths`. Each has its own target directory.

| Phase | Worktree | Branch | Wave | Scope |
| --- | --- | --- | --- | --- |
| P1 | `C:\w\p1` | `studio2/p1-shell` | 1 | Tokens, widgets, fonts, route, shell frame, rig status, palette, notices, offscreen routes |
| P2 | `C:\w\p2` | `studio2/p2-evidence` | 1 | Per-plane maps from the GPU fold, evidence file, reader, archive cap, unplaced frames |
| P4 | `C:\w\p4` | `studio2/p4-catalog` | 1, then UI | Catalog format 2 (subjects) model; later the Library and Subject screens |
| P6 | `C:\w\p6` | `studio2/p6-capture` | 1, then UI | Typed host state, blockers, host H1-H3, test runs, stopped captures, follow detail, owned engine jobs, timeouts, histogram, incremental proof; later the Capture screens |
| P7 | `C:\w\p7` | `studio2/p7-edit` | 1, then UI | Recipe additions, white balance, export pipeline, metadata, export presets, heal/backdrop; later the Develop and Export screens |
| P3 | (after P1) | `studio2/p3-stack` | 2 | The Stack station |
| P5 | (after P1) | `studio2/p5-activities` | 2 | Activities, queue, ETA, Quiet |

## Baseline (P0)

MEASURED on build `61effa01b`, release, CPU load 1 % at start, 2026-11-21 02:37-02:42 local. Files are in `perf/baseline/`.

| Measurement | Result |
| --- | --- |
| `benchmark_finished_workspace_pointer_sweeps` (130 captures, 8 levels, 1600 × 1000) | Process view CPU paint plus tessellation 1.28-1.32 ms per frame (min 1.282); source view 0.45-0.48 ms per frame |
| `benchmark_real_stack_scrub_publication` (299 real RAWs, `D:\personal\macro\insects\bug-3\107MSDCF`, read-only) | Passes its zero-upload, zero-task warm assertions; resident warming 1,443.6 ms; full report in `resident-299.json` |

The resident benchmark accepts 12 to 512 RAWs, so long stacks need P3's extended benchmark.

## Progress

- 02:35: baseline started; worktrees created; wave 1 dispatched (P1, P2, P4, P6, P7).
- 03:20: P4 catalog model merged (`4648ba450`). On a copy of the owner's catalog: 35 stacks become 21 subjects. bug-3 is split across two projects, and migration never moves stacks between projects. Fixed a shared-worktree git setting that made plain `git` in the worktrees resolve to the main checkout; each worktree now has its own `core.worktree`.
- 03:57: P6 capture model and host changes merged (`d6238bac3`): typed host state, start blockers, host H1/H2 with compatibility tests, test-shot runs kept out of the lists, stopped captures listed, owned engine jobs with cancel, timeouts, preview histogram, incremental proof job. strehl-ui tests 1,097 passed. Not deployed to the Pi; needs a rig test.
- 04:09: P7 edit and export model merged (`e6c2f90e8`), plus its Stroke editor arms (`251928367`). Exports without new options are byte-identical (86 pinned hashes). Region culling makes a 128-region development about 17× faster. On the integration branch with P4, P6 and P7 merged: strehl-ui 1,122 tests passed, 0 failed (MEASURED). Wave 2: the P4, P6 and P7 agents are building their screens as standalone modules.
- 04:30-04:50: merged P4 Library stage 1 (`55a07d64c`), P1 shell (`cc039bc58`), P2 evidence (`4bd9a2193`), P6 Capture screens (`9e1f9b08f`) and P7 Develop/Export screens with the background depth repair. P5 activities stage 1 could not merge, because the shell had also created `activity.rs` and `activity-tray.rs`; reconciling them is the first step of P5 stage 2. On the merged tree: strehl-ui 1,259 tests passed, 0 failed; clippy `-D warnings` and fmt clean; strehl-edit 186 passed; the GPU fold and support-map tests pass on the real GPU (MEASURED). One flaky catalog test, caused by two tests sharing a scratch folder, is fixed.
- Stage 2 dispatched: Library composition (P1 agent), Capture (P6), Develop/Export (P7), activities wiring (P5), and CPU-fold log size plus large-stack measurements (P2). P3 Stack stage 1 is still running.
