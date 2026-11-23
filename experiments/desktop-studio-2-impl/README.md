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
- 05:11: merged P3 Stack stage 1 (`9b29e0b10`): depth rail, filmstrip, plane lens, core sample, a sparse scrub tier and a disk cache for source previews. MEASURED by P3 (release, baseline and P3 binaries run alternately): the 130-plane process-view sweep fell from 1.243-1.269 to 0.712-0.727 ms per frame; on the 1,444-RAW bracket a sweep straight after opening shows a picture on 1,441 of 1,444 steps, where the baseline shows none. Not met yet: 6,000 planes cost 2.6-3.4 ms per frame in the existing theater; the fix is part of P3 stage 2, now dispatched. On the merged tree: 1,302 tests passed, clippy clean.
- 06:14: merged the station compositions: Develop/Export (P7), Library (P1 agent), Capture (P6), and the activities registry, stack queue, ETA and Quiet (P5). Conflicts were in station match arms (both sides kept), the activity model (P5's is the authority) and one offscreen helper. On the merged tree (`91ebd7e70`): strehl-ui 1,352 tests passed, 0 failed; clippy `-D warnings` and fmt clean (MEASURED). Also fixed: new stacks from a camera folder take the subject folder's name (P0 item 1, with a test that fails on the old naming).
- Dispatched: Stack station composition plus a photograph-only canvas for Develop/Export (P3); shell polish (P1 agent); depth signatures and queue actions (P4/P5 agent); E5 focus evidence, measured first (P6 agent); E4 region-only depth repair behind a measured gate (P7 agent); CPU-fold log size and large-stack measurements (P2).
- 06:48: merged the Stack station (P3 stage 2): the photograph room with plane lens, two-up size maps, core sample, depth rail and filmstrip; the engine room keeps the old process view; Develop and Export now draw the photograph alone. MEASURED by P3 (release, binaries alternated): engine-room process view 1.25-1.33 → 0.71-0.74 ms per frame at 130 planes; the station's photograph sweep 0.17 / 0.36 / 0.51-0.55 ms at 130 / 1,500 / 6,000 planes; on the real 1,444-plane render 0.43 ms. Develop's depth brush now uses the Stack station's rail (`b2924be80`). One timing-dependent filmstrip test failed once in a parallel run; P3 is making it deterministic.
- 07:20-07:42: merged the shell polish (breadcrumbs, a fixed-width top-bar status end, glance, drawers in every theme), depth signatures with Stack / Stack next, captures that finish during a render joining the queue, and E4 region-only depth repair (the desktop falls back to a full re-stack when a render does not qualify). The 6-byte result-TIFF difference P2 reported is the build stamp (`-dirty`) in tag 305, by design; pixels and master are identical (MEASURED). On the merged tree (`82b090279`): strehl-ui 1,375 passed, strehl-core 1,018 passed, engine byte-freeze 5 of 5, export freeze 2 of 2, clippy and fmt clean (MEASURED).
- 08:10-08:35: merged E5 focus evidence (off by default) and the Stack station's round 3 with P2's round 2 inside it; resolved the evidence format by hand so every record kind is numbered once (0-9, a table in `ui-evidence.rs`). On the merged tree: strehl-ui 1,385 passed, engine evidence and focus tests 55 passed, clippy and fmt clean (MEASURED). Final benchmark run below.

## Outcome

All phases P0-P7 are built and composed. P8 is built only as far as its measure-first engine half: the measurements say not to build the depth lens yet. Each phase's results note has its commands and numbers. The milestone ledger rows are marked.

### What the owner gets

- **Five stations in one shell:** Library, Capture, Stack, Develop and Export, with a top bar, hint bar, Ctrl K palette, Preferences, notices, the activity tray, focus mode (F) and the engine room (E). Three themes are built from one set of tokens: Graphite (the default), Instrument and Lightbox.
- **Library:** catalog format 2 groups stacks into subjects. The first save writes a verified backup of the format-1 file. The Library has a subject grid and subject pages with lineage, depth signatures, Locate for moved sources, and Stack / Stack next.
- **Stack:** the photograph comes first. It has the plane lens (hover to peek; hold for a two-up view with eight size maps), the core sample, the depth rail, the filmstrip with bar charts, and checks, recipe and renders.
- **Develop and Export:**
  - tools strip, scope, layers, versions, crop, white-balance pick, scale bar, heal, backdrop, depth brush on the Stack rail;
  - presets and batch export with history;
  - the recipe goes into TIFFs only when switched on.
- **Depth repair** runs in the background. The photograph stays open and Export keeps working. A render that qualifies is repaired region-only (E4): about 7 s instead of 15 s, with pixels outside the region bit-identical (MEASURED).
- **Capture:** plan with start blockers, test shot, focus rail, step table, in-flight proof, glance and stopped captures. Host changes H1 and H2 are additive and compatible both ways.
- **Activities:** one registry feeds the top bar and the tray. A serial stack queue is persisted, restored paused after a restart, and given a time-left estimate. Quiet mode holds heavy work while a full-screen program runs.
- **Evidence for every render (E1):** the GPU fold now writes per-plane maps, so reopening a 1,444-plane run shows 1,444 of 1,444 planes observed; the previous desktop showed none. The render log at 1,444 planes on the CPU fold fell from 758 MB to 5 MB (MEASURED).

### Final measurements (MEASURED)

Build `8e8531a43`, release, same script as the baseline, CPU load 1 % at start. Files in `perf/final/`.

| Measurement | Baseline `61effa01b` | Final |
| --- | --- | --- |
| Process-view pointer sweep, 130 captures | 1.28-1.32 ms per frame | 0.600-0.624 ms per frame |
| Source-view pointer sweep | 0.45-0.48 ms per frame | 0.320-0.322 ms per frame |
| 299 real RAWs, resident warming | 1,443.6 ms | 1,439.1 ms (warm assertions pass) |

From the phase agents (release, alternated binaries; details in their notes):

- **Stack station photograph sweep:** 0.122 ms at 130 planes and 0.137-0.141 ms at 6,000, which is within the 1.25× budget.
- **Live 1,444-plane GPU render:** no UI frame over 16 ms while maps stream in (longest 15.2 ms, p95 1.0).
- **Reopen at 1,444 planes:** fully observed in 0.42 s (GPU).
- **Develop:** slider to updated overview median 36.6 ms.

### Pi deploy (2026-11-21, after the desktop install)

At the owner's request the controller and bridge were cross-built from `b186a4da6` (`wsl -u root bash experiments/capture-implementation-2026-11-20/build-pi.sh`; strehl-capture compiled) and installed with `python experiments/capture-implementation-2026-11-20/deploy.py install <folder>`. The one host commit since the last install is `8ea93f2c9` (H1, H2).

- Installed SHA-256: `strehl-capture-headless` bd5a6726...bb80b, `strehl-sony-ptp` 1c4d1ada...d76 (equal to the build; full values and the state before in `pi-install-1795291285.json` and `pi-install-input-1795291285.json`). Backup of the previous binaries on the Pi: `/root/strehl-before-round4-1795291285` (the script's fixed prefix); roll back with `deploy.py rollback <backup>`.
- VERIFIED with the camera connected (USB 5000 Mbit/s, dial in M, ISO 100): `capabilities` = `{exposure_check: true, test_shot: true}`; `exposure.mode` `M`, `exposure.problem` null.
- The restart reset manage power to off; it needs a connected camera to switch on, so the camera was powered on, manage power set on, and the camera switched off. Left as found: camera and light off, manage power on, error correction off. The plan bounds reset to 0 (before the install neither bound was set).
- No test shot was taken; nothing was written to the capture folder.

### Not done, or not yet verified

- **Rig test of host changes H1 and H2 (test shot, exposure check):** the host was deployed to the Pi on 2026-11-21 (see below), but the rig test (P6 notes, items 2-6) has not been run. The desktop works with the old and the new host because it sends the new fields only when the host advertises them.
- **The depth lens (P8):** E5 is built and off by default. It costs 24-35× the render's time, and usable coverage is 3.8 % of pixels on the weevil and none on the 1,444-plane bracket. The evidence policy needs its own look first.
- **Still over budget:**
  - Engine room at 6,000 planes: 1.33-1.5× of its 130-plane cost against a 1.25× budget.
  - At the start of a 1,444-plane render, about 10 frames of 25-44 ms occur during alignment; the cause is not found.
  - Peek saturation is only a darkening.
- **Not built:** H3; Trim sources (decision D9); "Tell my phone" and the power-down grace, which the host does not support.
- **Agent interface:**
  - `import_stack` ignores `name` when `parent_id` is given.
  - A JPEG export requested without a colour space gets Rec.2020. This default predates tonight.
- **egui was not upgraded:** it stays at 0.33. Nothing in the plan needed a newer version, and an upgrade would have collided with seven parallel branches and the vendored egui-wgpu patch.

### Owner feedback round (2026-11-21 afternoon)

The owner's first look at the installed build asked for seven changes. Three agents built them in parallel worktrees (`studio2/fb-library`, `studio2/fb-live`, `studio2/fb-plan`); each branch's note has the decisions, measurements and screenshots:

- [fb-library.md](fb-library.md): Library management (delete with opt-in file removal, undoable removal from the library, move and merge, multi-select, Show in Explorer) and the "today" date of subjects without renders.
- [fb-live.md](fb-live.md): the depth rail's scale (wheel and slider), subject-box handles, and an antialiased Live View panel with a focus trace.
- [fb-plan.md](fb-plan.md): rig settings in the inspector, a typed step, settings guidance ("What changes"), and the rebuilt Schedule dialog in local time.

Merged into `main` (merge `3dde6668a`; one conflict, the route table in `visual-check.py`, kept both sides). On the merged tree: `cargo test --locked -p strehl-ui` 1,468 passed, 0 failed, 36 ignored; clippy `-D warnings` and fmt clean (VERIFIED, Compiling/Checking strehl-ui seen). Package `desktop-abbe71158bdff1c4` built with `scripts/package-desktop.ps1`; all 62 `visual-check.py` routes rendered from the packaged `Strehl.exe` on a catalog copy and were looked at (VERIFIED). No host change: the Pi needs no redeploy. Nothing in this round was tried on the rig.

### Owner feedback round 2 (2026-11-21 evening, after a full run-through)

The owner captured, stacked, developed and exported one subject (capture `stack-1795300522964-6430`: 211 planes, 49 retakes of 34 planes) and asked for fixes. Three agents built them in parallel worktrees (`studio2/g-flight`, `studio2/g-develop`, `studio2/g-zoom`); each note has root causes, decisions and measurements:

- [g-flight.md](g-flight.md): Capture while stacking: the rail follows the stack, a baseline-aligned progress header with fixed-width times and an eased time left, retakes counted apart from planes, the proof sized to its space and counted by plane (the owner's "proof didn't change" was not reproduced on their RAWs), the Show view's clipped header, and a scrolling, virtualised feed with one item per try, separate statuses, wrapped text, the retake policy in words, and an end-of-capture review. The retake policy was explained, not changed; one finding (shift-pattern failures may be retakeable) is left for the engine owner and a rig test.
- [g-develop.md](g-develop.md): Develop's Export… and Save version did nothing (a flag nobody read; a name field drawn only by panels Studio 2 no longer shows): both fixed with regression tests that failed first; every Develop/Export action now gives visible feedback; the "New" tags removed; AVIF encoder effort restored as its own control; AVIF size and time estimates refitted from measured encodes (the HDR preset read 13.8 MB against 59.2 MB written).
- [g-zoom.md](g-zoom.md): the Develop/Export viewer was capped (one 3072 px / 6 Mi-pixel detail patch), so on a 4K canvas 100 % showed half resolution; it now develops 1024 px tiles on the master's grid with the export's own code, nearest-neighbour at 100 % and above, and the Export view shows the preset's output pixels. At 100 % the screen equals the export (0 of 360,000 values differ, MEASURED on two real masters).

Merged into `main` with no conflicts. On the merged tree: `cargo test --locked -p strehl-ui` 1,497 passed, 0 failed, 43 ignored; `-p strehl-edit` all passed including the export byte-freeze; `-p strehl-capture` 63 passed; clippy `-D warnings` (ui, edit, capture) and fmt clean (VERIFIED, Compiling/Checking seen). Package `desktop-7990a64e93447314`; all 76 `visual-check.py` routes rendered from the packaged `Strehl.exe` and were looked at (VERIFIED). No host behaviour change (one constant made public); the Pi needs no redeploy. Nothing in this round was tried on the rig or in the owner's window.

### Owner feedback round 3 (2026-11-22, after using the installed build)

Before this round the application icon became round 2's Sunset (`d359bbe28`; candidates in `experiments/app-icon-2026-11-21/`). The owner then listed eleven fixes across Library, Capture, Develop and export metadata. Four agents built them in parallel worktrees (`studio2/h-subjects`, `studio2/h-proof`, `studio2/h-retake`, `studio2/h-develop`). Each note has the owner's words, decisions, measurements and open questions:

- [h-subjects.md](h-subjects.md):
  - Library: New subject > Empty subject… makes an empty subject on the spot (named, never a duplicate, undoable).
  - Moving stacks: Move to subject… on a stack's lineage and in the selection bar.
  - Every preview is drawn whole at its own aspect; the disk caches were never cropped.
  - Capture starts a new subject unless one is chosen on purpose. Start and Schedule wait for its name, and the plan says where the stack goes. Unnamed (agent) captures no longer land in the most recent subject.
- [h-proof.md](h-proof.md): "Proof so far" is replaced by a plane view:
  - The newest or a picked plane at full resolution, as the stack uses it (four shots combined), in 1024 px tiles.
  - Sharp and Checks overlays, the facts about the plane, and a history strip of every plane's sharp share.
  - It decodes RAWs only when the detail can be seen.
  - Open: 14–28 ms frames while zoomed in during full-resolution builds (cause not found; a separate process for the builds is the suggested fix).
- [h-retake.md](h-retake.md):
  - Retakes a plane is a per-run setting (0–5, default 2; an older host reports it fixed at 2).
  - Retake by hand: on a plane left to one shot, during the run or after it, into the same capture with the same plane numbers. The stack uses a plane's last complete group, so a passing retake wins.
  - A warning when a run of one-shot planes is wider than half the calibrated sharp width, with Retake planes A–B.
  - The host gains `queue_retakes`, `max_retakes` and follow-up runs: **a Pi deploy is needed**, and none of it is rig-tested.
- [h-develop.md](h-develop.md):
  - Develop's split line drags anywhere along it and stays put while zooming.
  - Artist and copyright, which nothing had ever set (Export always wrote empty text), live in Preferences > Exports and show in Export under the switch. The description is per photograph.
  - Every exported file names Strehl as its software, always: PNG, JPEG and AVIF from agent and CLI exports had no stamp before.

Merging: h-retake, h-develop and h-subjects merged cleanly apart from one overlay allow-list in `main.rs` (both kept). h-proof conflicted with h-retake in `capture-flight.rs` and `capture-station.rs`; I kept both lanes' fields and actions, h-proof's layout, and h-retake's feed context. Two fixes followed on the merged tree (`c0d33dc84`):

- The flight headline overlapped in a 1280 px window (row 2 with the owner's numbers, row 1 in `flight+long`). Its texts now give way in order, checked offscreen at 1280 and 1680 px.
- A library test raced a background sources check (1 failure in 4 full runs). It passed in all 6 runs after the fix.

On the merged tree:

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | 1,538 passed, 0 failed, 49 ignored (6 runs) |
| `cargo test --locked -p strehl-capture` | 75 passed |
| `cargo test --locked -p strehl-edit` | 193 passed (export byte-freeze included) |
| clippy `-D warnings` (ui, capture, edit) | clean |
| fmt (ui, edit) | clean; strehl-capture's `receiver.rs` differs as at base |
| `cargo test --locked -p strehl-cli` | 293 passed, 8 failed |
| clippy on strehl-cli | 33 findings |

The 8 strehl-cli failures are research controls (native probe and m194g private-corpus) and the clippy findings are in files untouched this round. Both are identical at base `d359bbe28` (the same 8 tests fail; 33 clippy errors), so they are not this round's. All VERIFIED (Compiling/Checking seen).

Nothing in this round was tried in the owner's window or on the rig.

### Package and install

- A source-inclusive package of `191e4fadb` was built with `scripts/package-desktop.ps1` (build id `desktop-2b8da1787c8409c4`). Five routes rendered offscreen from the packaged `Strehl.exe` on a copy of the catalog (VERIFIED).
- The session's permission check first refused the in-place install. The owner then asked for it, and it was installed on 2026-11-21 at 11:34 (backup `%LOCALAPPDATA%\Programs\Strehl-backup-20261121-pre-studio2`, catalog copy `projects.pre-studio2-20261121.json`; 9 files hash-verified; receiver restarted).
- The first save after installing converts the catalog to format 2 and writes a verified format-1 backup beside it. Older builds refuse format 2, so downgrading means restoring that backup.
- No receiver or RAW-archive change was needed: the archive codec did not change. The receiver runs from the installed desktop, so updating the desktop updates it.
