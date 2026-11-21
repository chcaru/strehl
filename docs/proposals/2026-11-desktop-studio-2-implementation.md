# Strehl Studio 2: implementation plan

**Status:** Implemented 2026-11-21 (P0-P7; P8's engine half only). See the
[implementation log and outcome](../../experiments/desktop-studio-2-impl/README.md). The spec was
locked on 2026-11-21: the owner approved the design after three mockup iterations and two polish
passes ("looks solid. lock in the plan").
**Date:** 2026-11-21.
**Owner's request:** "lock in the plan and produce a detailed writeup for another agent to carry
implementation forward with. it should be rust based as the current desktop app is." And: "it's
critical to maintain buttery smooth performance, such as the current filmstrip scrub and image
previews, etc. have, or even improve on it where possible."
**Implements:** [Strehl Studio 2](2026-11-desktop-studio-2.md) (the design, its evidence and its
reasoning) and the mockups in
[`experiments/desktop-studio-2026-11-20/mockups/`](../../experiments/desktop-studio-2026-11-20/mockups/README.md).
**Scope:** the desktop crate `crates/strehl-ui`, the editing model `crates/strehl-edit`, and the
engine (`crates/strehl-cli`, `crates/strehl-gpu`) and camera host (`crates/strehl-capture`) only
where a display needs data they do not yet produce.
**Audience:** an implementing agent with no other context. Read sections 1 to 5 before any code.
**Evidence labels:** MEASURED, VERIFIED (read in source by the author), REPORTED (read in source
by a delegated reader, not re-read by the author), DERIVED, ARGUED, UNVERIFIED. File and line
references were read at commit `2b0697d2a`. Lines drift; search by the quoted name.

---

## 1. Read this first

1. **The design is decided.** Do not redesign. Where this plan and the mockup differ, this plan
   wins: it corrects things the mockup could not know (section 3).
2. **Smoothness is a requirement, not a polish item.** Today's timeline scrub, image previews and
   photograph pan and zoom are fast because of specific mechanisms (section 5.1). Every phase
   keeps them, proves it with numbers, and improves the three known weak spots (section 5.5).
3. **The flagship displays need engine data that today's default render does not produce.** The
   depth rail's bars, the plane lens and the core sample read per-plane admission maps. The GPU
   fold, now the default, does not emit them (section 3, item 1). Phase P2 fixes that.
4. **Build in phases that each ship.** P0 fixes and baselines, P1 the shell, P2 the evidence, P3
   the Stack station, P4 the library, P5 activities, P6 Capture, P7 Develop and Export, P8 the
   depth lens (section 9).
5. **Reuse before rewriting.** Most of the data, caches and interaction logic already exist and
   are tested. Section 7 names what to reuse for each part.
6. **Keep every outside contract.** The agent and control snapshot keys, the camera host's command
   protocol, the catalog file, the recipe file and the engine's output bytes (section 11).
7. **Match the mockups.** Each new screen is checked by an offscreen render at 1680 × 1050 beside
   the matching reference image, with its rectangles compared to `metrics.json` (section 10.2).
8. **Port the mockup's interaction checks to Rust tests** (section 10.1).
9. **Respect the owner's machine and rig.** No heavy work while the owner uses the PC, camera and
   light off after use, ask before restarting the RAW receiver (section 4).
10. **Allocate the milestone rows** for each phase before starting it. The rows are reserved in
    [the milestone ledger](../agents/milestone-ledger.md#desktop-studio-2-2026-11-21).

## 2. Locked decisions

The proposal listed ten decisions for the owner. Locking the plan locks its recommendations,
with the changes the planning evidence required (marked "changed").

| # | Decision | Locked as |
| --- | --- | --- |
| D1 | Shell | Stations across the top (variant A). The left rail and its sidebar are retired. Focus mode (variant C) is `F` on any station. |
| D2 | Default theme | Graphite. Instrument (today's navy) and Lightbox (paper) are selectable in Preferences. |
| D3 | Vocabulary | Adopted (proposal section 8). Engine terms stay in the engine room as subtitles, and in logs. |
| D4 | Checks | A count against stated thresholds. A check carries a mark only after its threshold is validated on the corpus (research workflow); until then it shows its fact without a mark. |
| D5 | Subjects | Adopted, with catalog format 2 and a backup before migration (section 6.7). Nothing on disk moves. |
| D6 | Focus evidence for ordinary stacks | Changed: measure first (P8). The depth lens is hidden on any render without evidence. Memory is the risk: about 6.5 GB at the A7CR plane (DERIVED). |
| D7 | Depth repair | Changed: two steps. P7c makes today's full re-stack non-blocking. P7d adds an engine region-only rebuild, gated on its tests. |
| D8 | How far Develop goes | Macro finishing in: crop and straighten, white-balance pick, heal, backdrop, scale bar, output sharpening. Curves, colour mixing and heavy retouching go to an external editor. |
| D9 | Trimming sources from the library | Not built. The owner's 2026-11-20 decision stands: thinning stays numbers-only until the owner lifts it. |
| D10 | Mockup pictures in Git | Not committed. The repository is public; the pictures are the owner's unpublished captures. |
| D11 | Typeface (new) | System fonts only, as today (`theme.rs:81`: "font files are never redistributed"). Section 6.5. |
| D12 | Scale bar source (new) | A per-lens calibration, not the RAW. Nothing reads magnification today (section 3, item 5). |
| D13 | Extending a stack (new) | Deferred. Listing stopped captures ships in P6. Extending needs host and engine work the owner has not asked for. |

## 3. Corrections found while planning

1. **The default render emits no per-plane admission maps.** VERIFIED:
   - `gpu_fold_phases` (`crates/strehl-cli/src/merge_cmd.rs:5632-5643`) reports only fold phases: "Band surfaces are not produced: the GPU does not hand full-resolution fields back."
   - The desktop sets `STREHL_GPU_FOLD=auto` (`jobs.rs`, REPORTED near line 840).
   - MEASURED on the owner's newest long render, `strehl-1794295567732-51816-1` (1,488 planes, 2026-11-09): 52,053 progress events, 69 stack-wide diagnostics, 0 per-plane `gate-support` maps.

   An older CPU render of 1,444 planes has 11,552 maps (1,444 × 8 levels). Without these maps, today's timeline traces, plane regions and region probe are empty on GPU renders. The owner's reference screenshot is of a 130-frame stack. P2 makes the GPU fold emit the maps.
2. **Saved long stacks with maps cannot be reopened with their diagnostics.** MEASURED:
   - Render logs of 1.33 GB (1,444 planes) and 1.27 GB (1,381 planes).
   - 275 MB for 299 planes, about 0.92 MB a plane.
   - Reopening refuses logs over 512 MiB (`workspace-history.rs:911`, VERIFIED), so the limit falls near 580 planes (DERIVED).

   The maps are text in the log, beside two per-plane float maps (focus energy and the gate
   floor) at the same lattice. P2 moves them to a binary side file. The yes/no maps take about
   17 MB for 1,444 planes (DERIVED: 1,444 × 8 × 1.5 KiB). The float maps are kept for at most 384
   planes, so the file stays under 100 MB (6.8).
3. **Maps beyond about 1,000 planes are dropped even when emitted.** `AdmissionArchive` keeps at most `MAX_ENTRIES = 8192` maps (`process-provenance.rs:12, 159`, VERIFIED). At 8 levels that is 1,024 planes. P2 raises it.
4. **The camera host's bounds survey returns a sharpness profile.** `state.samples[{position, scores[24]}]`, a 6 × 4 tile grid per position (`crates/strehl-capture/src/worker.rs`, `scan` near 1636-1741, REPORTED). The desktop shows only the suggestion. The Capture rail draws this profile; no host change is needed.
5. **Nothing reads magnification or pixel pitch.** `strehl-raw` reads only focal length and f-number (REPORTED, `identity.rs:119`). The proposal's "scale from the lens data" becomes a per-lens calibration (D12).
6. **Region crops in today's popover are all the same final-photograph crop.** REPORTED, `process-region-visual.rs:102-108`. Per-plane crops in the core sample come from the camera preview of that plane: unregistered, so labelled approximate, like today's dashed outline.
7. **The proof cannot be built incrementally today.** `draft-preview.rs` is batch-only, capped at 512 frames and 480 px (REPORTED). P6 makes it incremental.
8. **The engine already prints stage timings.** These lines are printed but not parsed: `frames … (first decode X s)`, `alignment … X s`, `folded : N / M frames in X s (Y s per frame …)`, `collapse+write`, `total` (`merge_cmd.rs` near 9854, 9964, 10672, 11075, REPORTED). An ETA needs no engine change (section 7.6).
9. **There is a named-type clash.** `jobs::Task<T>` exists (`jobs.rs:90`, VERIFIED). The new task model is called `Activity`.

## 4. Rules for the implementer

**Repository**

- Read `AGENTS.md` at the repository and project roots, `CONTRIBUTING.md`, the
  [desktop README](../../crates/strehl-ui/README.md) and [desktop control](../desktop-control.md).
- Licensing: never open or copy enfuse/enblend, Hugin/`align_image_stack`, EPFL EDoF, ChimpStackr,
  darktable (including `exif.cc`), RawTherapee, ART, Filmulator, `librtprocess`, ExifTool Perl
  source, or `rawler`/`dnglab` source.
- New files are kebab-case and declared with `#[path = "name.rs"] mod name;`, as every module is
  today (`main.rs:8-116`, `app.rs:1-76`). Tests live in a sibling `name-tests.rs` declared
  `#[cfg(test)]`.
- Checks for any UI change. Never use `-q`. Confirm "Compiling" or "Checking" for the crate you
  changed.
  ```powershell
  cargo test --locked -p strehl-ui
  cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings
  cargo fmt -p strehl-ui -- --check
  ```
  Run the same for `strehl-edit`, `strehl-cli`, `strehl-gpu` and `strehl-capture` when they change.
  One known clippy failure predates this plan: `unnecessary_cast` near `capture-workspace.rs:1772`.
  P0 fixes it.
- Format only your own hunks. Scope commits with `git commit -- <paths>`; never `git add -A`.
  Audit with `git show --name-only`.
- Markdown ends with exactly one newline. Label claims with the evidence labels above.
- Visual checks use the offscreen renderer (`scripts/strehl-control.py screenshot`, or
  `Strehl.exe --offscreen-screenshot`). Never drive the desktop with Computer Use.

**Data and privacy**

- `%LOCALAPPDATA%\Strehl\capture.json`, the receiver's `receiver.json` and any `headless.json`
  hold pairing keys. Never print, quote or commit them.
- Capture folders (`D:\StrehlCaptures`, `D:\personal\macro`) are read-only. Delete only test runs
  you created, by name.
- Never open the owner's live catalog for a test. Copy `%LOCALAPPDATA%\Strehl\projects.json` to a
  scratch folder and pass `--catalog`.

**Outputs that must not change**

- A render's output bytes must not change because of UI work or new diagnostics. The engine
  emits diagnostics through observers. Prove each new observer with on, off and placebo hashes
  (engineering ledger rule 26; `scripts/verify-ui-progress.py`). `tests/byte-freeze.rs` parses
  log keys `alignment`, `workers` and `memory plan`; any new log line needs a distinct key.
- The camera host's safety rules (the A7CR capture plan, round 4, section 2) are not negotiable:
  - a shutter transition is marked uncertain before it is sent and is never retried;
  - a RAW is journalled before the next shutter;
  - an unexpected file stops the run.

**Honesty in displays**

- No display may imply more than the engine measured. Keep the engine's cautions next to its
  maps: kept marks are support at the noise gate, not a share of the blend; outlines on camera
  previews are approximate.
- Never derive a per-pixel "sharpest frame" from a raw argmax. Engineering ledger rule 4 and the
  selector invariant in `AGENTS.md` apply. The depth lens uses the regularised focus field only
  (P8). The depth brush suggests a plane range; it never picks frames per pixel.
- Never suggest opening the aperture. The owner shoots wide open (f/5.6 with the 2× converter is
  the lens's widest). Exposure controls offer ISO and shutter only.

**The owner's machine and rig**

- No renders, benchmarks or long builds while the owner uses the PC. Ask, or wait.
- After rig tests, switch the camera and light off. A controller restart turns "manage power"
  off; switch it back on. Run rig tests with "manage power" on, the owner's setting.
- Installing a build on the owner's machine:
  1. Build a package with `scripts/package-desktop.ps1`.
  2. Ask the owner before stopping the RAW receiver.
  3. Stop it with the "Stop receiver" script in `%LOCALAPPDATA%\StrehlCaptureReceiver`.
  4. Copy the package over `%LOCALAPPDATA%\Programs\Strehl`.
  5. Start "Start receiver automatically.ps1" as a detached process, for example with `Invoke-CimMethod Win32_Process Create`, so it does not inherit your shell. The firewall rule covers that path only.
- The camera host is cross-built in WSL as root (`wsl -u root`); the default WSL user has no cargo.

## 5. Performance contract

### 5.1 What makes it smooth today

All VERIFIED or REPORTED in the files named. Keep every one of these.

**Selection versus display** (`source-browser.rs:3-7`)

- A pointer move selects at once. The display keeps the last good picture until a better one is ready.
- `PhotoSlot` (`workbench.rs:22`) never downgrades the same capture. It swaps instantly to a different capture. It blends two tiers of one capture over 0.22 s.

**Preview tiers** (`source-browser.rs`)

| Tier | Side | Count / budget | Requested |
| --- | --- | --- | --- |
| Native contact | `THUMB_SIDE` 240 | 512 / 128 MiB | visible and near |
| Scrub | `SCRUB_SIDE` 640, down to 256 by count | `SCRUB_COUNT` 512 / `SCRUB_BYTES` 192 MiB | after `SCRUB_IDLE` 180 ms |
| Overview | `OVERVIEW_SIDE` 960 | 11 / 40 MiB | selection and ±`OVERVIEW_RADIUS` 4 |
| Image | `IMAGE_SIDE` 1920 | 6 / 48 MiB | after `SETTLE` 90 ms |

**Scheduling**

- At most one detail task plus one batch task, at most `FILMSTRIP_WORKERS` 3 decoders (`source-preview.rs:38`).
- No refinement inside `SETTLE`.
- Stale work is cancelled by a flag. Its lane stays busy until the thread returns, so pointer moves never add decoders.
- Reduced-IDCT JPEG decoding (`jpeg_decoder` scale) when the source is at least twice the target.

**Upload pacing**

- The scrub tier uploads at most `SCRUB_UPLOAD_BYTES` 2 MiB a poll, selected capture first.
- A warm sweep uploads nothing and starts no task. Tested in `source-browser-resident-tests.rs:28-105`.

**Same-frame display.** After the timeline sets `hover_source`, the photographs are re-synced
in the same paint (`process-theater.rs`, near 1107-1147). A warm hover adds no frame of latency.

**Photograph viewer** (`photo-viewport.rs`)

- One overview plus one detail patch of at most `MAX_PATCH_SIDE` 3072 px and `MAX_PATCH_PIXELS` 6 Mi.
- Patches are planned every frame; a worker starts only after `SETTLE` 80 ms.
- Uploads happen in the worker. Reveal takes `REVEAL` 120 ms with paced repaint.

**Frame discipline**

- No continuous repaint; wakes happen only while something moves. The HDR presenter's 750 ms heartbeat is the one exception.
- All work runs through `jobs::spawn_task` / `spawn_notifying_task` (`jobs.rs:114, 175`), polled once a frame with `try_recv`.
- Every heavy shape is cached behind a key:
  - the timeline's `EvidenceKey`, plot and band keys;
  - the overlay `Arc<Mesh>`;
  - `DenseRegionPainter`'s four meshes;
  - `BinaryPane` meshes.
- Overlays are thinned with `Density::cap`.
- Work pauses while a pointer button is down: the adaptive map, the hover region, catalog saves.

**Documented speed** (`docs/development/progressive-display-verification.md`, REPORTED; 2600 × 1300 on the owner's RTX 5090)

- Framework p95 4.29-4.73 ms per frame.
- App update about 2.2 ms per frame.

No scrub latency, scrub decode time or warm/cold benchmark result is recorded anywhere.

### 5.2 Invariants every change keeps

1. The UI thread never reads a file, decodes an image, parses a log chunk larger than today's
   8 KiB step, or runs any loop whose length grows with the number of planes, except over a
   cached result whose key changed.
2. A pointer move that does not change the data key rebuilds nothing: no mesh, layout or
   evidence aggregation. Test pattern: `process-participation-v25-tests.rs:340-393`,
   `process-overlay-v25-tests.rs:100-115`.
3. A warm hover or scrub over planes whose preview tiers are resident uploads no texture and
   starts no task. Test pattern: `source-browser-resident-tests.rs`.
4. New previews go through `SourceBrowser` and its tiers. No view spawns its own decoder.
5. The display never shows a lower tier of the same capture after a higher one. A different
   capture swaps without a fade.
6. Texture uploads from the UI thread are paced: at most the existing 2 MiB a poll for any
   tier added or touched.
7. Any work started on hover waits for its settle time: 90 ms for previews, 80 ms for the
   photograph.
8. Repaint only while something changes, using `request_paced_repaint` where a delay is wanted.
9. Per-plane series are pooled to at most one column per 2 px of screen before drawing
   (`process-participation.rs`, `Layout::new` near 1875).

### 5.3 Budgets and how to measure them

P0 records the baseline. Every later phase records the same measurements before and after, on
the same machine and build profile, with host load stated. Store them as
`experiments/desktop-studio-2-impl/perf/<phase>.md`.

| Measurement | How | Budget |
| --- | --- | --- |
| Warm scrub | Resident benchmark (`source-browser-resident-benchmark.rs`, ignored test) on a real 299-plane and a real 1,444-plane bracket | 0 uploads, 0 tasks, displayed = requested on every step (existing assertion) |
| Cold scrub | Same benchmark, cold trace | Record the time to first canonical tier; must not regress |
| Pointer sweep paint | `benchmark_finished_workspace_pointer_sweeps` (`process-theater-v26-perf-tests.rs:1426`), plus a new 1,500- and 6,000-plane fixture | CPU paint + tessellation ms per frame no worse than baseline; 6,000 within 1.25 × the 130-plane figure |
| Live frame time | `scripts/check-display-performance.py` against the `frame_performance` snapshot (p50/p95/max over 256 frames) while scrubbing 10 s and panning 10 s | p95 within 5 % of baseline; never above 8.3 ms (120 Hz) at 1680 × 1050 |
| New views | Tests per section 10.1: zero rebuilds on pointer-only motion; bounded columns | Pass |
| Memory | Resident texture bytes from `SourceBrowser` stats, process working set | No more than baseline + the new budgets this plan sets |

A regression of more than 5 % at p95, or any broken invariant, blocks the phase. The exception
is an explicit trade the owner accepts.

### 5.4 Rules for each new view

- **Depth rail** (one bar per plane, up to 6,000):
  - Aggregate only when the evidence revision, level or rect changes.
  - Pool to columns of at least 2 px.
  - Draw as one cached `Arc<Mesh>`, keyed on rect, pixels per point, revision and level.
  - The hover line, playhead and labels are separate cheap shapes.
  - Format tooltips only while hovered.
- **Plane peek and hold:**
  - Request previews through `SourceBrowser` with the hovered plane as the selection.
  - Display only `texture_snapshot` / inspection photos.
  - The region outline comes from `DenseAdmissionCache`.
  - `DenseRegion::extract` must move off the paint path (5.5).
- **Core sample:**
  - Quantise the region to sample cells (`SampleWindow`); recount only when the cell set changes.
  - Build strips once per window key.
  - The popover is shapes on a tooltip-layer painter, not widgets, as today (`process-region-probe.rs` near 434).
- **Library grid** (40-200 tiles):
  - Request only visible tiles plus one screen ahead; drop requests not seen in the last paint.
  - Decode on workers from the 384 px disk tier, scaled to 256 px; commit a row together.
  - Use `spawn_notifying_task` wakes, not polling.
- **Full-frame lens** (depth, soft spots):
  - Compute off the UI thread, keyed by image identity and settings.
  - Keep the previous result until the new one is ready; no work while a button is down.
  - Upload in the worker; draw one UV-cropped quad.
- **Top bar, inspector, palette, tray:**
  - Plain widgets; no per-frame allocation proportional to the catalog.
  - The palette's search index is built when the palette opens and kept until the catalog revision changes.

### 5.5 Improvements in scope

These go beyond keeping today's speed. Each has a phase and an acceptance figure.

1. **Long stacks scrub warm everywhere (P3).** Today only 512 planes are resident at 304 px, refilled after 180 ms idle, so a fast sweep over a 1,500-plane stack lands on cold frames.
   - Add a stack-wide sparse tier: every k-th plane at 160 px, resident from open.
   - Add a persistent disk derivative for the scrub tier, like `explorer-preview-cache.rs` (128 MiB / 512 entries).
   - Acceptance: a cold-cache sweep of the 1,444-plane bracket shows a picture of the right plane or its nearest resident neighbour on every step.
2. **Large uploads leave the UI thread (P3).** The Image tier's RGBA conversion and upload run on the UI thread unpaced (`source-browser.rs` `cache_image` near 1018). Prepare the `ColorImage` on the worker; pace uploads like the scrub tier.
3. **Region extraction leaves the paint path (P3).** `DenseRegion::extract` runs synchronously during paint (`process-admission-regions.rs` near 110-117). Compute on a worker and keep the previous region.
4. **The timeline's lanes are cached (P3).** Lane shapes, about 3 per 2 px column, are rebuilt every frame (`process-participation.rs` near 1076-1196). Cache them as a mesh.
5. **Uncached scans are cached (P3).** `process_fingerprint::cells` (`process-fingerprint.rs:113`) and the probe's `heatmap` scan every retained map each frame.
6. **Evidence holds up at 6,000 planes (P2).**
   - The binary side file and a raised archive cap. 48,000 maps at 1.5 KiB is about 72 MiB (DERIVED); measure it.
   - A history-backed series (`sampled_mask_history`) for any capture whose map is missing.
7. **Library thumbnails (P4).** Lift `ExplorerPreviews` out of the project tree. Raise `MAX_ENTRIES` from 40 to 240 and `MAX_BYTES` from 24 to 48 MiB (256 px tiles are about 175 KB each); 3 workers for a cold cache.

### 5.6 The gate for each phase

A phase is done only when the following are recorded, with the commands and figures, in its perf note:

- its own tests pass;
- the offscreen renders match the references (10.2);
- the 5.3 measurements are no worse than baseline.

## 6. Target architecture

### 6.1 New modules

All in `crates/strehl-ui/src/`. Each gets a `-tests.rs` sibling.

| File | Holds |
| --- | --- |
| `studio-route.rs` | `Station`, `Route`, per-station view state, the adapter to today's `Sidebar` flags (6.2) |
| `studio-shell.rs` | The frame: top bar, hint bar, inspector frame, focus mode, panel order (6.3) |
| `studio-theme.rs` | `Tokens`, the three themes, the spectrum, the type scale (6.4); `theme.rs` delegates to it during migration |
| `studio-widgets.rs` | Buttons, segments, toggles, sliders, status marks, checks, keys, lifecycle line, cards (6.4) |
| `studio-fonts.rs` | Font discovery and registration (6.5) |
| `activity.rs`, `activity-tray.rs` | The task model and its tray (6.6) |
| `notices.rs` | Replaces the single `status` / `error` strings with a bounded list of notices (6.6) |
| `rig-status.rs` | The rig popover over the capture client's state |
| `command-palette.rs` | Ctrl K: subjects, stacks, commands |
| `depth-rail.rs`, `filmstrip.rs` | The rail and the filmstrip (7.2) |
| `plane-lens.rs` | Peek, hold, the two-up and the size maps (7.2) |
| `core-sample.rs` | The region popover (7.2) |
| `stack-station.rs`, `stack-checks.rs`, `stack-recipe.rs`, `stack-renders.rs` | The Stack station (7.2) |
| `library-station.rs`, `library-previews.rs`, `subject-page.rs` | Library and subjects (7.3) |
| `capture-plan.rs`, `capture-preflight.rs`, `capture-rail.rs`, `capture-flight.rs`, `capture-glance.rs`, `capture-proof.rs` | Capture (7.4); `capture-workspace.rs` keeps its state and polling |
| `develop-station.rs`, `develop-layers.rs` | Develop (7.5) |
| `export-station.rs`, `export-presets.rs` | Export (7.6) |
| `evidence-file.rs` | Reader for the engine's binary evidence file (6.8) |

### 6.2 Navigation

Today four overlapping variables drive navigation:

- `sidebar: Option<Sidebar>` (`app.rs:171`; enum at `app-workspace.rs:6`);
- `process_view: bool`;
- `view: View`;
- `canvas_mode`.

Paint code has side effects tied to them (REPORTED):

- `poll_capture` opens the camera connection only when the sidebar is Capture (`app-workspace.rs:33-35`);
- auto-opening a finished capture depends on the sidebar (`:51`);
- the editor tool is forced every frame (`app.rs:2412-2419`);
- `sidebar()` saves recipe drafts while painting (`app-workspace.rs:721-778`).

Replace them with one route:

```rust
pub(crate) enum Station { Library, Capture, Stack, Develop, Export }

pub(crate) enum Route {
    Library(LibraryView),                  // All, Collection(NodeId), NeedsYou(Need)
    Subject(NodeId),
    Capture(CaptureMode),                  // Plan, Flight, Glance
    Stack { stack: NodeId, render: Option<PathBuf>, room: Room }, // Room: Photograph | Engine
    Develop { stack: NodeId, render: PathBuf },
    Export { stack: NodeId, render: PathBuf },
}
```

Steps, each with its own tests:

1. Add `Route` beside the old fields with a one-way adapter, `Route` → `(sidebar, process_view)`. Existing tests and agent commands keep working.
2. Move each side effect out of paint into `StrehlApp::tick(&mut self)`, which headless also calls (`headless_tick`, `app-headless.rs:195`):
   - **camera connection:** wanted while a capture is configured and either the Capture station is open or a sequence is running; see 7.4 for the polling cadence;
   - **finished-capture handoff;**
   - **draft saving;**
   - **tool selection.**
3. Draw from `Route` only, then delete `Sidebar`, `process_view`, `View` and the legacy layout:
   - `inspector`, `filmstrip`, `stack_ribbon` and `canvas` at `app.rs:1220-1916`;
   - `render_actions`;
   - the duplicate log list.

   Dropping an image file opens it in Develop. `--draft` and `--workbench` remain as diagnostics on the engine-room route.

Undo is scoped to the station (proposal 5.2): the hint bar names what the next undo will undo. `WorkspaceEdits` keeps its four domains; the station chooses which domain Ctrl Z addresses.

### 6.3 Frame layout

Panel order inside `update_workspace` (`app.rs:2824`). Keep the polls above the minimized guard. Keep `window_chrome::finish` last, for the resize edges.

| Panel | egui | Size (from `metrics.json`) |
| --- | --- | --- |
| Top bar | `TopBottomPanel::top("studio-top")` | 44 high |
| Hint bar | `TopBottomPanel::bottom("studio-hints")` | 24 high |
| Tools strip (Develop only) | `SidePanel::left("studio-tools")` | 44 wide |
| Inspector | `SidePanel::right("studio-inspector")` | 348 wide (resizable 300-440, persisted); tabs 36, footer 53 (86 on Capture plan) |
| Control strip | `TopBottomPanel::top(..).show_inside` in the central area | 36 high |
| Rail and filmstrip | `TopBottomPanel::bottom(..).show_inside` | head 30; chart 84 on Stack, 104 on Capture plan, 96 in flight, 70 in the engine room; filmstrip 75 with 74 × 63 frames |
| Canvas | the rest of `CentralPanel` | the photograph is centred at 3:2 with a 10 px margin; the millimetre rule sits under it |
| Library sidebar | `SidePanel::left("library-nav")` | 232 wide |
| Subject left column | `SidePanel::left("subject-hero")` | 500 wide |

**Window chrome**

- The top bar is the drag area: its empty space calls `window_chrome::drag_space` (`window-chrome.rs:43`).
- The minimise, maximise and close buttons move into the top bar's right end. The 192 × 30 floating dock (`window-chrome.rs:16`, `finish` at 128) goes.
- Edge resizing (`finish_resize`, 249) stays.
- Remove the hand-coded dock avoidance:
  - `process-space.rs:338`, `bracket-browser.rs:308`, `camera-metadata.rs:680`;
  - the `RAIL_WIDTH` insets (`bracket-browser.rs:260`, `camera-metadata.rs:682`).

### 6.4 Theme tokens and widgets

`studio-theme.rs`, with values copied from the mockups (`src/base.css`, `src/screens.css`):

```rust
#[derive(Clone, Copy)]
pub(crate) struct Tokens {
    pub bg: Color32, pub panel: Color32, pub raised: Color32, pub control: Color32,
    pub line: Color32, pub line2: Color32,
    pub ink: Color32, pub ink2: Color32, pub ink3: Color32,
    pub accent: Color32, pub accent_ink: Color32, pub accent_soft: Color32,
    pub ok: Color32, pub warn: Color32, pub bad: Color32, pub info: Color32,
    pub plane: Color32, pub surround: Color32,
    pub spectrum: [Color32; 8],
    pub canvas_ink: [Color32; 3],          // light inks for text on the dark photo surround
}
pub(crate) enum ThemeName { Graphite, Instrument, Lightbox }
pub(crate) fn tokens(ctx: &egui::Context) -> Tokens; // stored in ctx data, set by Preferences
```

Exact values are in appendix A.

**Migration**

- `theme.rs`'s constants (`BG`, `PANEL`, `RAISED`, `LINE`, `INK`, `MUTED`, `ACCENT`, `GREEN`, `AMBER`, `theme.rs:2-10`) become functions reading the current tokens.
- Then replace call sites module by module. Delete the constants when no caller remains.
- The Camera metadata window's `Visuals::light()` override (`camera-metadata.rs:651`) goes in P0.

**Rules** (proposal section 6, the "engraved" language)

- **Geometry:**
  - Corner radius 0 everywhere; it already is in `theme::install`.
  - One-physical-pixel rules via `theme::rule`.
  - No shadows except under popovers.
  - Controls are 28 px high (22 small, 36 large); segments 24; toggles 26 × 14 with a square knob; sliders are a 1 px rule with a 2 px index and a tick at the default.
- **Colour:**
  - Amber means selected or the main action, nothing else.
  - Links are neutral; they take the accent only on a check that needs a look.
- **Status marks are drawn shapes,** in `studio-widgets.rs` with the painter, never font glyphs:

  | Mark | Means |
  | --- | --- |
  | filled circle | fine |
  | triangle | look |
  | 45° diamond | failed |
  | ring | not yet |
  | half-filled ring | running |

- **The detail spectrum** (appendix A) colours detail size everywhere it appears: core-sample strips, filmstrip marks, the size switch, the engine room's grid.
- **States:**
  - hover lightens text or outlines;
  - keyboard focus is a 1 px accent outline offset 2 px;
  - no animation longer than 160 ms;
  - honour reduced motion (`ctx.options().reduce_motion` if present, else a Preferences switch).

### 6.5 Typeface

The design's lettering is Bahnschrift, the DIN-style face that ships with Windows. egui 0.33's
renderer (`ab_glyph`) cannot select a variable font's weight, and Bahnschrift is a variable
font. VERIFIED: no variation API in `epaint-0.33.3/src/text/fonts.rs`; `FontTweak::coords` exists
in `epaint-0.37.0/src/text/font_tweak.rs:48`. Locked approach, no font files redistributed:

| Family | Windows source | Use |
| --- | --- | --- |
| `din` | `C:/Windows/Fonts/bahnschrift.ttf` (default instance, Regular) | labels, tracked capitals, figures, body |
| `din-strong` | `seguisb.ttf` (Segoe UI Semibold) | titles and statements |
| `din-light` | `segoeuil.ttf` (Segoe UI Light) | large figures (64 px and up) |
| fallback | `segoeui.ttf`, then egui's default fonts | anything missing, and macOS/Linux |

All four Windows files are present on the owner's PC (VERIFIED). Letter spacing for tracked
capitals uses `TextFormat::extra_letter_spacing` (`epaint` 0.33, VERIFIED present).

An upgrade to egui 0.37 would give real Bahnschrift weights through `FontTweak::coords`. It is a
separate, optional task: rebase the vendored `third-party/egui-wgpu` fork (patched in the root
`Cargo.toml:55-56`) and re-run every visual and performance check. Do not mix it into a phase.

### 6.6 Activities and notices

Every long task gets one model: stacking, export, view-bundle export, focus-step measurement,
compaction estimate and apply, calibration, capture following, metadata reads and session import.
Interactive edit previews and thumbnails are not activities.

```rust
pub(crate) enum ActivityKind { Stack, Export, ViewBundle, FocusStep, CompactEstimate, CompactApply,
    Calibration, CaptureFollow, Capture, Metadata, Import }
pub(crate) enum ActivityState { Waiting { for_what: String, gives_up: Option<Instant> }, Running,
    NeedsYou { message: String, action: Option<ActionId> }, Stopped { message: String, kept: Option<String> },
    Done { summary: String, next: Option<ActionId> } }
pub(crate) enum Lane { Heavy, Background, Camera }      // Heavy is serial and holds in Quiet mode
pub(crate) enum CancelMode { None, Cooperative, Kill }
pub(crate) struct ActivityStatus { id: u64, kind: ActivityKind, title: String, stack: Option<NodeId>,
    state: ActivityState, phase: String, done: Option<u64>, total: Option<u64>,
    started: Option<Instant>, eta: Option<Duration>, cancel: CancelMode, lane: Lane, log: Option<PathBuf> }
pub(crate) trait Activity { fn status(&self) -> ActivityStatus; fn cancel(&mut self); }
```

Each state has an obligation: what it waits for, what it does, what it needs, what was kept,
and what happens next (proposal section 5.8).

**Migration order:**

1. **Read-only aggregation, the tray and the shell indicator.** Add an additive `activities` key to the agent snapshot.
2. **`EngineJob`** (`capture-tools.rs:24, 89`) stops detaching its child. It holds an `OwnedChild` (`jobs.rs:1295`) with cancel and elapsed time.
3. **The export chain** (three tasks, `app-photo-history.rs:235-509`) becomes one activity with three phases. The unused bundle observer (`session-bundle-export.rs:56`) gets wired.
4. **Stack render: the large step.**
   - `progress`, `logs`, `started`, `pending_run` and `pending_stack` move from `StrehlApp` into a per-job struct; today `StrehlApp.progress` doubles as the open document's view.
   - A queue of frozen requests (`RenderRequest` + `Run` + `NodeId` + output folder) runs on the Heavy lane.
5. **Follow and calibration adapters,** with their state machines unchanged. Calibration gains timeouts; it has none today.
6. **Persistence and ETA.**
   - Queue and history go in a new `%LOCALAPPDATA%\Strehl\activities.json`, never in `projects.json`.
   - ETA: timestamp `frame-finished` events on receipt; seed from the previous run of the same stack (its `render.log` stage lines, section 3 item 8); parse those lines in `pipeline.rs`.

**Quiet mode** holds the Heavy lane's next start while a full-screen program is in front, or
while the switch is on. Captures and transfers never wait. Candidate API (UNVERIFIED):
`SHQueryUserNotificationState` in `windows-sys` `Win32_UI_Shell`, already enabled in the crate's
features; treat `QUNS_RUNNING_D3D_FULL_SCREEN` and `QUNS_BUSY` as busy.

**Notices** replace the `status` / `error` pair (`app.rs:206-207`; about 35 and 32 assignment
sites). `notices.rs` holds a bounded list of `{severity, text, source, time, action}`.

- The top bar shows the newest unread failure; the tray lists all.
- Keep `status` and `error` as derived values for the agent snapshot.
- Capture's unread success notices (`capture-client.rs:516-563`) feed it.

**Hazards** (REPORTED):

- **Snapshot keys to keep:**
  - `busy.{stack, opening, photo, preset, export}`, `status`, `stage`, `stack_blocker`;
  - `export_capabilities.view_bundle.busy`, `photo_history.busy`, `session.selection_busy`;
  - `capture.follow.checker.*`, `capture.tools.{calibration.stage, focus_step, compact_estimate, compact}`;
  - `projects[].kind`;
  - replies `{"state":"queued"|"cancellation_requested", ...}`.
- `StartStack` already answers "queued" while meaning "started". Keep the word and make it true.
- **Shutdown and undo:**
  - `prepare_headless_shutdown` (`app-headless.rs:209`) must include the queue.
  - Projects and Recipe undo are disabled while a job runs. With a queue that is most of the time, so scope it to the running stack only.
- **A hard-killed desktop** leaves an engine child running and a run marked "Stacking". On start, reconcile such runs to "Interrupted".

### 6.7 Catalog format 2: subjects

Today (REPORTED, `workspace-history.rs`):

- **Types:** `Catalog` at 177; `NodeKind { Project, Folder, Stack }` at 108; `ProjectNode` at 156; `Run` at 42.
- **Save:** under a lock file, with an on-disk byte comparison, an atomic temp-and-rename write and a 32 MiB cap.
- **Load:** `migrate_runs` (710) runs on every load and is idempotent.
- **Unknown fields:** on `Catalog`, `ProjectNode` and `Run` they are dropped on save. `PhotoOwner` and related types use `deny_unknown_fields`.

Locked design:

- **Format version.** Add `format: u32` to `Catalog`, default 1 when absent. Version 2 adds `NodeKind::Subject`.
  - An older build meets the new variant, fails to load, sets `load_error` and refuses to save (`:244`). That is safe; it cannot silently strip subjects.
  - The owner runs one installed build, updated in place.
- **Subject metadata.** `ProjectNode` gains `subject: Option<SubjectMeta>` (`serde(default, skip_serializing_if = "Option::is_none")`):
  ```rust
  pub(crate) struct SubjectMeta { notes: String, hero: Option<PathBuf>, optics: Option<Optics>, scale: Option<ScaleCalibration>, created: u64 }
  pub(crate) struct ScaleCalibration { um_per_px: f64, source: ScaleSource }  // Measured(slide) | Entered{magnification, pitch_um}
  ```
- **Hierarchy.** UI names change: Project → Collection, Folder → sub-collection, Subject is new.
  - `validate` (755) and `check_container` (659) allow Collection > (Folder >)* Subject > Stack.
  - A stack directly under a collection or folder stays valid during migration.
- **Migration** (`migrate_subjects`, idempotent, run after `migrate_runs`):
  1. Before the first format-2 save, write `projects.v1-backup-<unix>.json` beside it and verify it re-reads.
  2. Every stack without a subject parent gets one. A stack named like a camera folder (`^\d{3}MSDCF$`) is grouped by its source's parent directory, named after that directory. Other stacks get their own subject, named after the stack.
  3. Stacks with the same grouping key share a subject. On the owner's catalog: 35 stacks become 20 subjects (DERIVED from a copy, 2026-11-20).
- **Undo.** `Organization::apply` (`project-explorer.rs:90`) deletes any non-stack node missing from its snapshot. Add `Subject` to `OrganizedNode` and treat subjects like stacks for deletion, or undo will delete subjects.
- **Agent commands.** Additive only: `CreateSubject`, `MoveNode`, `SetSubjectMeta`, and an optional `kind` on `CreateProject`.
- **Size.** Every `Run` stores the full `sources` list, and `StackDraft` repeats it (about 150-200 bytes a plane, pretty-printed). The owner's catalog is 8.7 MB with 50 runs (MEASURED).
  - Measure a 6,000-plane stack's effect on the 32 MiB cap in P4.
  - If needed, move `sources` to a per-run sidecar keyed by hash. That is a format-3 change; do not do it speculatively.
- **Missing sources.** A stack whose `source` directory is gone shows a "sources moved" state with Locate… This re-points `StackDraft.source` and the runs' `sources` after a scan matches names and sizes, instead of creating a second stack.

### 6.8 Evidence pipeline (engine to desktop)

**The evidence file**

- The engine writes per-plane maps to `<run>/evidence.strehl` and stops writing them as hex lines. One log line names the file: `STREHL_UI_PROGRESS event=evidence-file path=evidence.strehl version=1`.
- Format, little-endian, append-only:
  - Header: `"STRHEVD1"`, `u32 version`, `u32 levels`, per level `u16 lattice_w, u16 lattice_h, u32 extent_w, u32 extent_h`, `u32 frames_total`.
  - Records: `u32 frame, u8 level, u8 kind (0 gate-support, 1 averaging, 2 focus-energy, 3 gate-floor), u16 reserved, u32 sequence, u32 payload_len, payload`. Payload is bits for binary kinds; for others, quantised `u8` samples with `f32 min, max`.
  - Every plane gets its gate-support maps. Float kinds (2 and 3) are written for at most 384
    planes spread evenly through the stack, the desktop's own retention (`MAX_SURFACES` 384,
    `process-scales.rs:21`, VERIFIED). Bound: 384 × 8 levels × 2 kinds × about 11 KB, about
    67 MB (DERIVED).
- The lattice and sample sites are exactly those of `ui-diagnostics.rs` today (`GRID_WIDTH` 128, `GRID_HEIGHT` 96, aspect-preserving, coarse levels at full size), so old and new runs mean the same thing.

**The desktop side**

- `evidence-file.rs` tails the file during a run (length polling, as `capture-follow.rs` does for the journal) and reads it whole on reopen.
- `AdmissionArchive` takes records from either source. Old runs keep parsing hex lines.
- `MAX_ENTRIES` becomes 65,536.

**The GPU fold**

- After each frame's fold at each level, a compute pass writes one bit per lattice site (weight > 0) into a small buffer.
- The buffer is read back asynchronously through a ring of staging buffers. It must never stall the fold.
- CPU and GPU maps must be identical on a test fixture, as the pixels are.

**Cost budget:** under 1 % of fold time (UNVERIFIED until measured), and no change to output bytes.

## 7. Station specifications

Each subsection names: what to build, what to reuse, the data source, and how it fails honestly.
The mockup screen and reference image names are given for each.

### 7.1 Shell

Reference images: `stack.png`, `library-rig.png`, `capture-flight-jobs.png`, `stack-palette.png`.

**Top bar, left to right**

- The brand mark: the three-plane icon, today's `strehl.svg`, drawn in accent strokes.
- The breadcrumb:
  - Library / subject / stack / render / version, at most 430 px.
  - Middle segments ellipsize; each segment opens a switcher to its siblings.
- The stations, centred:
  - `01 Library | 02 Capture 03 Stack 04 Develop 05 Export`, 11 px tracked capitals.
  - Each of the four lifecycle stations reserves a slot for its state mark, so labels never move between screens.
- The rig status (7.1.1), the activity status (6.6), Ctrl K, and the window buttons.

**Hint bar**

- Left: the keys that apply on this station.
- Right: the open render's facts and the next undo.
- It replaces today's 23 px status bar (`app-workspace.rs:826`). Elapsed time, workers and RAW count move to the activity tray.

**Rig status** (`rig-status.rs`)

- A popover over the capture client's state: camera, light, power-for-a-stack, camera host, receiver on this PC, phone remote.
- It shows a lamp; it turns warn for a slow USB link (`usb_speed_mbps`) or a stopped receiver.
- Its buttons send the existing `Power`, `PowerPlan`, `Connect` and `Disconnect` commands.

**Command palette** (`command-palette.rs`)

- Contents: subjects, stacks, renders, and every station action with its key.
- Matching: case-insensitive prefix first, then subsequence; arrows to move, Enter to run.
- The index is rebuilt only when the catalog revision changes.

**Focus mode (`F`)**

- The canvas fills the window; the inspector and rail draw as opaque floating panels over it.
- They fade after 2 s without pointer motion; the fade is one animated alpha, so no relayout.

**Preferences** (new, in the palette and the brand menu)

- Theme, surround, reduced motion, Quiet mode.
- Inspector width and route persist in a new `ui` section of the catalog's `layout`.

### 7.2 Stack station

Reference images: `stack*.png`, `engine-room.png`.

**Layout**

- The control strip:
  - the lens switch: Photograph, Plane, Depth, Soft spots, Alignment;
  - the detail-size switch, 2 to 256, each value underlined in its spectrum colour;
  - the hold note;
  - Fit / 100 %;
  - Render N vs Render M.
- The canvas, then the depth rail with its filmstrip.
- The inspector: Checks, Recipe and Renders tabs.

**Depth rail** (`depth-rail.rs`)

- **Data:**
  - Bars are the share of sampled sites admitted per plane at the selected level (default 0, the finest).
  - Exact counts come from `AdmissionArchive::counts(level, frame)` when the plane's map exists.
  - Otherwise, from the `sampled_mask_history` entry of kind `GateSupport` at that level (`on_samples / samples`, pooled above 1,024 planes). This is the pattern in `process-ledger.rs:110-163`.
  - A plane observed at zero draws a 1 px baseline; an unobserved plane draws nothing but a
    hatched baseline segment, so the two never look alike.
- **Dashed line:** the same share inside the region under the pointer. Use `CaptureParticipation`'s window evidence (`EvidenceKey`, `SampleWindow::archive_counts`).
- **Brackets:** "no subject detail" brackets mark runs of planes whose bars are under a threshold. The threshold must be validated before it is shown as a check.
- **Drawing:**
  - One bar per plane with a 1 px gap when planes are at least 3 px apart; otherwise pooled columns.
  - A pale top outline, a dot per bar when planes are 3.4 px apart or more, a tick every 5 planes, a numeral every 25.
  - "NEAR" and "FAR" at the ends.
  - Numerals under the playhead or hover marker hide.
- **Cache:** one `Arc<Mesh>` keyed on (rect, pixels per point, evidence revision, level, theme).
- **Reuse:** `CaptureParticipation::update`, `update_plot`, `Layout::x/index/range` (`process-participation.rs`), and its selection logic (nine test files).
- **Rewrite:** the paint block, inline in an 860-line `show`.

**Filmstrip** (`filmstrip.rs`)

- 17 frames across 1,332 px, chosen evenly through the stack. Each has its plane number and 8 small marks in the spectrum, from `band_signature`'s data.
- Frames use `SourceBrowser`'s native contacts and canonical refinement. Keep `MAX_CONTACTS` (48) as the upper bound.
- The frame nearest the pointer gets a 1.5 px plane-colour outline; the held frame gets an accent outline.

**Plane lens** (`plane-lens.rs`)

- **Peek:** hovering the rail or a frame sets the inspected plane. The shared state is `ProcessTheater`'s `hover_source` / `inspected_source` (`process-theater.rs:81-83`, `inspection_frame` 694); keep it.
  - The photograph dims to 86 % brightness and 75 % saturation.
  - The plane's kept region is painted: fill at 23 % alpha, a 1 px contour, and sample dots on a 7 px lattice inside, all in the plane colour.
  - Regions come from `DenseAdmissionCache::region(archive, domain, frame, level, extent, settings)` (`process-admission-regions.rs:66`) and are painted with `DenseRegionPainter` (1068).
  - A 372 px card rises above the rail at the pointer. It holds the plane's camera preview with the same region in a dashed outline (`paint_approximate`), the plane number, its kept share, and "click to hold".
  - No relayout: delete today's 0.24 s workspace animation into the rail layout (`inspection_mix`, `inspection_layout` near 489, 951) for the Stack station. The engine room keeps it.
- **Hold:**
  - A click, or the Plane lens with a plane chosen, switches the canvas to two-up: final with the plane's region beside the plane's preview with the same outline.
  - Today's `source_relation_layout` (`process-theater.rs` near 3796) is the geometry.
  - Under it, eight small maps, one per detail size, each with its kept share; a click on one sets the size.
  - While holding, hovering the rail shows other planes in the two-up and leaving returns to the held plane. A click holds the new plane. Left and Right step by 1, Shift by 10. Escape releases.
- **Detail size:** the switch sets the level for the photograph region, the peek and the two-up.
- **Honesty:** the plane-side caption reads "camera preview · the outline is approximate, not a registration".

**Core sample** (`core-sample.rs`)

- **Region:** hovering the photograph marks a square with corner marks and sample dots. Today's size rule applies (`region_at`, `process-region-probe.rs:780`; 96 screen px, Ctrl + wheel 32-320). The popover opens beside it, with a hairline leader.
- **Contents, top to bottom:**
  - "CORE SAMPLE", live or pinned, and the region size in photograph pixels;
  - four crops: final, then the three leading planes, each with its kept share;
  - eight strips, one per detail size, plane by plane in the spectrum, with the leading planes marked;
  - one sentence;
  - the caution "Kept is support at the noise gate, not a share of the blend. Planes can overlap.";
  - when pinned: "Show the plane" (holds the leading plane), "Repair here…" (opens Develop with the depth brush on this region), "Note".
- **Data:**
  - `RegionProbe::update` already computes per-level, per-capture counts in the window.
  - Peers: the top three by admitted share at the selected level (`sync_spatial` near 593).
  - "Fallback average" uses the existing averaging packet (`set_fallback`).
  - The sentence uses the 50 % and 20 % spans of the region's profile (the mockup's `span`).
- **Crops:**
  - The final crop comes from the result overview texture, as today.
  - Plane crops use the plane's resident preview tier, UV-mapped. They draw only if resident; otherwise an empty frame with the plane number. They never trigger a decode on hover; a pinned sample may request the three planes' overview tier.
  - The crop caption carries "approximate" in the tooltip.
- **Reuse:** `RegionProbe`, `region_at`, `popup_placement` (799), the `PopupPaint` pattern.
- **Rewrite:** `diagnostic_tooltip` (`process-region-visual.rs:16`).

**Lenses**

| Lens | Built in | Source |
| --- | --- | --- |
| Photograph | P3 | |
| Plane | P3 | above |
| Detail kept | P3 | the existing admission overlay mesh |
| Soft spots | P3 | the averaging (fallback) map through `DenseRegion` |
| Alignment | | hidden until per-area data exists |
| Depth | P8 | engine focus evidence; hidden otherwise |

Each lens has its legend with the engine's caution. No lens draws a guess.

**Checks** (`stack-checks.rs`)

- The verdict block: the count of checks needing a look, in a 56 px light numeral, and a tally strip.
- The rig card:
  - Shown while the rig is on and a capture of this stack ended within the grace period.
  - It counts down the power-down; Keep the rig on, Reshoot…
  - "Extend the stack…" is hidden (D13).
- Then the check rows, with the sources from proposal section 5.3:
  - placed and refused (with names once P8's small engine addition lands);
  - alignment worst residual;
  - empty planes at the ends;
  - soft spots;
  - slices overlap (focus-step result stored with the stack);
  - range covers the subject;
  - light steady (four-shot gains only; otherwise "not measured");
  - observation balance.
- A check without a validated threshold shows its fact and no mark (D4).

**Recipe tab** (`stack-recipe.rs`)

- Intents: Balanced (engine defaults) and Draft (half size) only. "Maximum detail" and "Cleaner" ship only after a measured study sets their values (research workflow).
- "N changes from the defaults" lists overridden values. All options are grouped Merge, Exposure and colour, Geometry, Evidence, Performance, using the existing `controls.rs` fields renamed (proposal section 8).

**Renders tab** (`stack-renders.rs`)

- Renders of the stack (the catalog's `revisions`) and versions of the shown render.
- "Compare two…" opens a two-up of two renders through the same viewer.

**Engine room**

- Today's process view (`ProcessSpace::show`, `process-space.rs:236`) behind `E` or any check's Show.
- Re-tokened and relabelled, with engine terms as subtitles and one legend.
- The pipeline strip gains per-stage seconds (section 3, item 8). Keep its layout code and tests.

### 7.3 Library and subject

Reference images: `library.png`, `library-rig.png`, `subject.png`.

**Library** (`library-station.rs`)

- **Left list (232 px):**
  - All subjects, On the rig.
  - Needs you: To stack, To check, To develop, Exported (derived states).
  - Collections.
  - The storage card: disk free, Strehl's share, what compacting would free. Compaction estimates are per stack, cached with the stack; no new scan on paint.
- **Grid:**
  - Five columns of subject cards: 172 px picture, name, counts, date, size, four lifecycle bars, next step.
  - The capturing card has an accent outline.
- **The on-rig strip** for a running capture.
- **Search** over names, notes, lens and date.
- **Sort:** Recent, Name, Size.
- **New subject ▾:** from the camera, or from folders. Dropping several folders makes one stack each, grouped by parent; today only the last is kept.

**Subject page** (`subject-page.rs`)

- **Left column (500 px):** hero, name, collection, notes, optics and scale, on disk, New stack of this subject, Add folders.
- **Right column:**
  - Stacks newest first. Each row has a thumbnail, name, facts, lifecycle line, a depth signature (the rail's data at 230 × 46, cached per render), size and Open.
  - The open row shows lineage: renders, versions of the selected render, exports. "Shoot again with these settings" opens Capture with the stack's bounds, step, exposure and light.
  - The journal: a list of dated events from the catalog and run records.

**Previews** (`library-previews.rs`)

- Lift `ExplorerPreviews` (`explorer-previews.rs`) out of `project-explorer.rs`; budgets per 5.5 item 7.
- The disk tier stays at 384 px (`explorer-preview-cache.rs:17`).
- Representative image: the latest render's output, else the first source, as today (`project-explorer.rs` near 701).

### 7.4 Capture station

Reference images: `capture-plan.png`, `capture-flight*.png`, `glance.png`.

**Typed host state**

- Introduce `HostState`, a `#[serde(default)]` struct over the fields the desktop reads. Keep the raw `Value` for pass-through.
- Today the desktop reads almost everything as untyped `serde_json::Value` (`s.state["editable"]`), which hides misspellings.

**Plan, the inspector** (`capture-plan.rs`)

- Subject and stack name first.
- Then four numbered steps, each with a ready mark: Rig, Exposure, Depth, While it runs and after.
- **Rig:** a summary of the rig status.
- **Exposure:**
  - ISO and shutter pickers from `exposure.iso_options` / `shutter_options`; send the existing `Exposure{iso, shutter}` command.
  - Decode Sony codes: shutter is `num << 16 | den`, see `timing::shutter_seconds`.
- **Test shot:**
  - `CapturePositions{positions: [position], keep_power_on: true}`.
  - It creates a full run folder today. Mark it as a test run so it is not followed, not listed and not handed to the library.
  - H2 makes this a host capture kind.
  - Read the RAW's clipped share and shadow level on a worker with `strehl_raw::decode` (black and white levels from `Frame.levels`).
- **Depth:**
  - Start and end fields with Mark start here / Mark end here.
  - **Calibrate step,** today's calibration, gains timeouts and an activity.
  - **The step table:** for candidate steps (5, 7, 10, 16, plus the calibrated one), overlap = sharp width / step, planes, minutes and gigabytes:
    - planes from `Plan{step}.positions().len()` (the shared `strehl-capture` model);
    - minutes from the host's own timing formula (`session.rs` near 92-106: initial plane × n + setup + warmup);
    - gigabytes from `capacity::required` (worst case) and `StoredRaws::expected` (expected size).
  - The row beyond the measured detail limit is marked.
  - The staircase diagram: seven overlapping slices with an index line.
  - 4-shot pixel shift, settle.
- **While it runs:** check planes, retake failures, stack when finished, then power down after a grace period.

**Pre-flight strip** (`capture-preflight.rs`)

- One function is the single source of truth for both the strip and the Start button: `fn start_blockers(s: &Snapshot, ui: &CaptureWorkspace) -> Vec<Blocker>`.
- It covers today's condition (`capture-workspace.rs:1684-1697`, VERIFIED):
  - fresh;
  - editable;
  - start_set;
  - end_set;
  - plan_error null;
  - no unapplied edits;
  - no focus move pending or in flight;
  - capacity;
  - receiver ok or demo;
  - not pending;
  - not editing a schedule.
- Each `Blocker` has a chip, a sentence and an optional fix action.
- Exposure-mode problems are checked only on the host after Start today (M mode, fixed ISO, timed shutter; `worker.rs` near 1526). H1 exposes them in state so the chip can show them before Start.

**Focus rail** (`capture-rail.rs`)

- The lens travel in normalised focus units.
- The bars are the bounds survey's profile (`state.samples`): per position, the median of the 24 tile scores, or the subject-box tiles when a region is set. Planned planes are ticks; Start and End are accent handles; the lens is an index.
- Dragging a handle edits the draft. Keys: Left and Right move focus by 1, Shift by 16; S and E mark.
- There are no lens-limit values in state; the rail spans the survey or the plan, padded.

**In flight** (`capture-flight.rs`)

- The headline: plane, bar, time left, finishing time, all from `completed`, `total` and `timer`.
- The proof (below); the latest plane with its verdict.
- The last planes, from the follow journal. Keep each plane's parsed `Value`; `progress()` discards it today (`capture-follow.rs:57-93`).
- The rail filling: ticks are checked, retaken, on the host but not here (`storage.pending_frames`), or to come.
- The health column: transfer, checks, disk, rig.
- "When it finishes" switches; Pause, Stop… (confirm), Glance.

**The proof** (`capture-proof.rs`)

- Refactor `draft-preview.rs` for incremental use:
  - cache each frame's decode and pyramid at `DRAFT_SIDE`;
  - re-run the global solve and blend every 4 new planes or 5 s, on a below-normal worker;
  - above 512 frames, subsample evenly.
- Source frames: the receiver's newest RAW (`receiver.latest.path`) through `load_draft_source`.
- Labelled everywhere "from the camera previews, not the RAW stack". `draft-preview.rs:1-9` says such a composite cannot predict the RAW merge; keep that sentence in its docs.

**Glance** (`capture-glance.rs`)

- Full screen, with the colour bar, the dial (one tick per plane), four health lines and the next-step sentence.
- `G` from in flight; Escape returns.

**Stopped captures**

- List runs whose `result.json` says stopped or uncertain as "stopped · N planes". Use a relaxed variant of `verify_completed` (`capture-client.rs` near 681-756).
- Today they vanish from the desktop.
- They can be opened and stacked like any folder.

**Connection cadence**

- Keep the client connected while capture is configured.
- Poll state at 1 Hz when the Capture station is closed and no sequence runs; 5 Hz otherwise. The cadence is a field on the client's `Work` channel.

**Host changes** (all additive, capability-gated, following the `keep_power_on` precedent at `session.rs` 661-666 and its test)

| Change | Purpose | Needed for |
| --- | --- | --- |
| H1 | `exposure.mode` and `exposure.problem` in state | pre-flight exposure chip |
| H2 | `CapturePositions{..., kind: "test"}`, with `manifest.capture_kind = "test"` | a test shot that is not a stack |
| H3 | `plan.positions` in state (optional) | the desktop computes them today; H3 removes the duplication |

Command types are `deny_unknown_fields`, so new fields are `serde(default, skip_serializing_if)` and omitted when unused. The desktop reads a capability from state before sending them.

### 7.5 Develop station

Reference images: `develop*.png`.

**Layout and adjustments**

- The tools strip (44 px):
  - Move, Crop, White balance pick;
  - Depth brush, Heal, Backdrop;
  - Region, Scale bar, Note.
- The control strip shows the tool's options.
- The rail appears with the depth brush only.
- The inspector: Adjust, Layers and Versions tabs.
- **Scope switch:** Whole photograph, or a named layer. It sits above the sliders and shows today's `selected`; `current_adjustments` (`app-editing.rs:574-586`) already retargets.
- **Looks:** today's Adaptive profiles, with one line each. Picking one applies it. Recalculate keeps Amount; it resets Amount to 1.00 today (`app-adaptive.rs` near 446). Double-click resets to the chosen look, not to Natural (near 481).
- **Histogram** of the developed overview, computed on the preview worker.
- **Before / After / Split.** Split needs a second development job and viewport, composited where the photograph is painted (`app.rs` near 2494-2531).

**Model changes** (`crates/strehl-edit/src/recipe.rs`)

`DevelopmentRecipe` is `deny_unknown_fields`, `version` 1. Add only optional fields, with
`serde(default, skip_serializing_if)`, so files without them stay readable by older builds. A file
using a new feature is refused by an older build, which falls back to the master's baked recipe
with a warning (`edit-workspace.rs:355-372`). Keep `version` at 1.

| Field | Type | Notes |
| --- | --- | --- |
| `crop` | `Option<Crop{min, max, angle_deg}>` | Applied in export through mapped UV with `developed_sample` / `display_sample` (`image.rs:256, 298`) |
| `scale_bar` | `Option<ScaleBar{length_um, corner, style}>` | Uses the subject's `ScaleCalibration` |
| `heals` | `Vec<Heal{center, radius, source_offset}>` | A neighbourhood stage before `apply_pixel` (below) |
| `backdrop` | `Option<Backdrop{threshold, softness}>` | Same stage |
| `RegionShape::Stroke{points, radius}` | new variant | The depth brush's mask. Add bounding-box culling to `apply_pixel`, which visits every region for every pixel today |
| `layers_order` | `Vec<String>` | Explicit order of region ids; list order today is both application and repair-blend order |

**White-balance pick**

- A pure function in `strehl-edit`. Sample the post-`place` value, averaged over a small square.
- temperature = 100 · log2(B/R), tint = −200 · log2(√(RB)/G), clamped to ±100 (REPORTED derivation from `apply`).
- The clamp limits correction to 2×; say so in the tool's hint.

**The neighbourhood stage** (heal, backdrop, later sharpening)

- Runs before the per-pixel stage.
- The preview patch is padded by the stage's support: the heal's offset plus radius.
- `render_display_region_mode` (`display-region.rs:36`) and the export loops must use the same padding.

**Depth brush**

- **P7c:**
  - Painting creates a `Stroke` region with `source_range`. The rail shows the painted area's profile; drag a range on it.
  - The re-stack runs as a Heavy activity separate from `self.job`. The current photograph stays loaded: today `reset_document` unloads it (`app.rs` near 705).
  - Export stays enabled and uses the existing master with its baked repairs. `can_export` (`app-export.rs:189-197`) changes from "no pending repairs" to "export what is baked; say that a repair is pending".
- **P7d:** the engine rebuilds only the region (section 8, E4).
- **Preview:** shows the chosen planes' camera previews inside the stroke, labelled approximate. Never a per-pixel frame choice (rule 4).

### 7.6 Export station

Reference image: `export.png`.

**Presets** (`export-presets.rs`)

- `export-presets.json` beside the catalog, with the develop presets' library pattern: version, lock file, expected-bytes check, recovery file, unique names (`develop-presets.rs:250-331`).
- Defaults: Web (JPEG sRGB 2560 px, quality 90), HDR (AVIF Rec.2020 full size), Print (TIFF 16-bit Display P3), Archive (master and recipe).
- Settings persist; today they reset each launch (`app.rs:287`).

**Batch.** The ticked presets run as one Export activity with a phase per file. Naming uses a
template (`{subject}-{view}-{preset}`). The destination is remembered per subject. Files are
never overwritten (`publish::new_file_checked`).

**Pipeline** (`crates/strehl-edit/src/export.rs`)

- Split develop from encode: develop → f32 buffer → resize → output sharpening → scale bar → encode. Development is fused into the u16 loop (near 174-196) and the AVIF loop (`avif.rs` near 128-173) today.
- **Resize:** in linear light with the `image` crate's resize on `Rgb32F`, inserted before the format branch (near 143).
- **Output sharpening:** gated by engineering ledger rule 9 (a flat-ROI control first) and judged only on native crops of 400 px or smaller (rule 48).
- **Metadata:**
  - TIFF: Artist, Copyright, ImageDescription and DateTime via `write_tag`.
  - PNG and JPEG: an XMP packet built with `quick-xml` 0.41, already in the lock.
  - AVIF: after confirming `avif-serialize` 0.8.9 can carry XMP or EXIF (UNVERIFIED).
- **The development recipe in TIFF ImageDescription** (`export.rs:209-213`) becomes a switch, default off (P0).

**History** under the photograph, from the catalog's `photo_exports`. Each row shows its preset,
size, the version that made it, whether the file still matches its hash, and Reveal, Copy path,
Export again.

## 8. Engine and host changes

| Id | Crate | Change | Gate |
| --- | --- | --- | --- |
| E1 | `strehl-cli`, `strehl-gpu` | Per-plane gate-support maps from the GPU fold, and the binary evidence file (6.8) | CPU and GPU maps identical on a fixture; output bytes unchanged (on, off, placebo); fold time +1 % at most |
| E2 | `strehl-ui` | Parse stage timing lines; timestamp events; ETA | Tests on recorded logs |
| E3 | `strehl-cli` | Log unplaced and refused frame indices (`event=frame-unplaced frame=…`) | Byte-freeze unaffected; distinct key |
| E4 | `strehl-cli` | Region-only rebuild against an existing master (below) | See below |
| E5 | `strehl-cli`, `strehl-core` | Focus evidence for ordinary stacks (`--focus-evidence`), reusing `session_focus::compute_pass` with a frame-loader abstraction | Memory and time measured on the owner's stacks before any default |
| H1-H3 | `strehl-capture` | Section 7.4 | Older desktops and controllers unaffected; rig test with manage power on |

**E4 in detail** (REPORTED analysis of `crates/strehl-cli/src/merge_cmd/region-repair.rs`).

Today a repair re-runs the whole render, decode, alignment and fold, and then folds each
region's frames over the full analysis geometry.

A region-only rebuild needs:

1. The original run's resolved parameters. They are recorded in `render.log`, and in provenance only with `--sensor-master`.
2. An ROI domain: region bounds plus the coarsest level's plugin halo plus demosaic and warp support. The vehicle is `PyramidDomain{full, rect}`, used for `--cover crop` today.
3. A blend target: the master's RGB after the ROI is demosaiced and developed with the pinned tone (`resolve_tone` skips measurement when `dev.tone` is set).
4. Overlap rules: overlapping repairs re-run in list order.

**Acceptance:**

- Pixels outside the region's support are bit-identical to the old master.
- Inside, the result is compared with a full re-stack and the difference is reported. It will not be bit-identical, because a full re-stack re-measures tone.
- The existing repair tests (`region-repair-tests.rs:43-359`) still pass.

## 9. Phases

Each phase ships on its own, keeps 5.2, passes 5.6, and ends with the owner's desktop updated in
place and a short results note in `experiments/desktop-studio-2-impl/`. Allocate its ledger row
before starting. P2 is engine work and may run beside P1.

### P0: baseline and quick fixes

**Measure first**, before any change: section 5.3 on the current build, written to
`experiments/desktop-studio-2-impl/perf/baseline.md`. Use the owner's 299-plane weevil run and the
1,444-plane run.

**Quick fixes:**

1. **Name new stacks** after the parent folder when the folder is named like a camera folder, and offer the name for editing (`app-workspace.rs:440-447`).
2. **Show the first unmet start condition** beside Start. This introduces `start_blockers()` (7.4).
3. **Finished stacks open photograph-large** via the existing photograph-focus path (`process_space.set_edit_focus`), with the instruments on `E`.
4. **Red for failure:**
   - Add a red token and draw a capture FAULT in it; the phase colour follows link freshness today (`capture-workspace.rs:1618`).
   - Stop drawing a running render as failed: its status is written "Stacking" (`app.rs:680`) but the tree matches "Rendering" (`project-explorer.rs` near 955).
5. **Strip `\\?\`** from displayed paths: a `display_path()` helper at every display site.
6. **Camera metadata in the app's theme:** remove the `Visuals::light()` override (`camera-metadata.rs:651`).
7. **Confirmations and cancels:**
   - Confirm Stop, Disconnect and Shut down camera.
   - Own the child process in `EngineJob` and add Cancel to Measure focus step and the compaction estimate.
8. **Capture beyond its tab:** show a running capture in the status bar on every screen, and start checking without opening Capture (`app-workspace.rs:33-35`).
9. **Show Capture's success notices,** which are set and never read (`capture-client.rs:516-563`).
10. **Timeouts and "Stop waiting"** on the camera connect wait and every calibration stage.
11. **Make writing the recipe into exported TIFFs a visible switch,** default off (`strehl-edit/src/export.rs:209-213`).
12. **Bring labels back in line:**
    - the README: "Photograph focus" and "Stack repair · next run" against the app's real labels;
    - the Adaptive docs' "Analyze" and profile list;
    - `desktop-settings-audit.md`'s confidence-map default;
    - the stale "CPU stacking · GPU display" (`controls.rs:138`).
13. **Fix the pre-existing clippy `unnecessary_cast`** near `capture-workspace.rs:1772`.

**Acceptance:**

- The photograph takes at least 40 % of the window after a stack.
- No new stack is named after a camera folder.
- Every disabled Start shows a reason.
- The perf baseline is recorded.

### P1: the shell

- Tokens and widgets (6.4), fonts (6.5), route and adapter (6.2), frame layout (6.3).
- Top bar, hint bar, rig status, palette, Preferences, focus mode (7.1).
- Notices and read-only activities (6.6 steps 1-2).
- **Offscreen:**
  - Add `--route <library|subject|capture|stack|engine|develop|export>`, `--theme <graphite|instrument|lightbox>` and `--plane-hold N` to `LaunchOptions` (`main.rs:120-155`), applied in `from_launch`.
  - Add readiness clauses in `screenshot()` (`app.rs:2657-2823`).
  - Forward them, and today's unforwarded `--edit`, `--export` and `--projects`, in `scripts/strehl-control.py` (208-224, 289-304).
  - Document them in `docs/desktop-control.md`.
- **Acceptance:**
  - Every route renders offscreen at 1680 × 1050. Chrome rectangles match `metrics.json` within ±2 px: top 44, hint 24, inspector 348, control strip 36, rail head 30.
  - Today's tests pass through the adapter.
  - No text style under 10.5 px; no sentence under 12 px.
  - Perf gate.

### P2: evidence for every render (engine; may run beside P1)

- **The engine work:** E1 and E3.
- **Desktop:**
  - `evidence-file.rs`, and `AdmissionArchive` reading both sources, with the raised cap.
  - The history-backed series for planes without maps.
  - Reopen through the side file. The 512 MiB log limit no longer blocks diagnostics, because maps are no longer in the log.
- **Acceptance:**
  - A GPU render of the 299-plane stack has the same per-plane maps as a CPU render.
  - The 1,444-plane run, re-rendered, reopens with diagnostics.
  - Output bytes are unchanged.
  - Fold time grows by 1 % at most.
  - The evidence file is under 100 MB for 1,444 planes, and the render log no longer carries
    any per-plane map.

### P3: the Stack station

- Rail, filmstrip, plane lens, core sample, lenses, checks, recipe, renders and the engine room (7.2).
- Improvements 5.5 items 1-5.
- **Acceptance:**
  - Offscreen renders match `stack.png`, `stack-core-sample-live.png`, `stack-plane-peek.png`, `stack-plane-held.png`, `stack-plane-held-64px.png`, `stack-recipe.png`, `stack-renders.png` and `engine-room.png`.
  - The ported interaction tests pass (10.1).
  - The photograph takes at least 50 % of the window with the inspector open.
  - A 6,000-plane fixture meets 5.3.
  - The cold-cache sweep of the 1,444-plane bracket always shows a picture.

### P4: library and subjects

- Catalog format 2 and migration with backup (6.7).
- Library grid, subject page, previews (7.3). Missing-sources Locate.
- **Acceptance:**
  - Migration of a copy of the owner's catalog yields 20 subjects with no run lost; the backup re-reads.
  - An older build refuses the new file without damaging it.
  - Undo never deletes a subject.
  - Scrolling 200 tiles keeps 5.3.

### P5: activities and the queue

- 6.6 steps 3-6.
- **Acceptance:**
  - A capture left alone ends as a stacked render without opening Capture.
  - Two stacks queue and run in order.
  - Every long task can be stopped or says why not.
  - Quiet mode holds a queued stack while a full-screen program runs.
  - Snapshot keys unchanged, plus `activities`.

### P6: the Capture station

- Typed host state, plan, pre-flight, rail, step table, exposure and test shot, in flight, proof, glance, stopped captures, cadence (7.4). Host changes H1-H2, H3 optional.
- **Acceptance:**
  - From rig off to capturing without scrolling.
  - The proof appears within the first 10 planes.
  - A stopped capture is listed.
  - The test shot does not appear as a stack.
  - Tested on the rig with manage power on; the camera and light end off.

### P7: Develop and Export

| Part | Scope |
| --- | --- |
| P7a | Scope switch, layers list, looks fixes, before/after split, histogram, crop and straighten, white-balance pick, scale bar with calibration; export presets, batch, resize, metadata, history |
| P7b | Heal and backdrop (the neighbourhood stage), output sharpening (rules 9 and 48) |
| P7c | Depth brush with the non-blocking re-stack |
| P7d | E4 region-only rebuild |

**Acceptance:**

- A web copy and a full-size file leave in one action.
- A pending depth repair no longer disables Export.
- E4's tests pass.
- Recipes without new features stay readable by the previous build.

### P8: the depth lens

- E5 measured on the owner's stacks; then the Depth lens and the alignment lens if per-area data exists.
- **Acceptance:** the lens draws only where the evidence's `usable` flag is set, with the legend's caution. Memory and time are recorded.

## 10. Verification

### 10.1 Tests to write

Port the mockup's interaction checks (`experiments/desktop-studio-2026-11-20/mockups/src/check.html`)
into Rust tests in the station modules. Use the existing pattern:

- `StrehlApp::from_launch(4096, LaunchOptions::default())` (`app-tests.rs:8-10`);
- `egui::Context::default()` with `theme::install`;
- `ctx.run(RawInput{events, ..}, ..)`;
- assertions on `FullOutput.shapes` and app state.

Examples: `app-workspace-review-tests.rs:21-120`, `window-chrome-tests.rs:114-140`. The checks:

1. **Hovering the photograph:**
   - the core sample goes live and names three leading planes;
   - the rail's region line appears;
   - a click pins the sample where clicked.
2. **Hovering the rail:**
   - the peek opens with the plane's share;
   - the numeral under the marker hides.
3. **Clicking the rail holds:**
   - the lens becomes Plane;
   - eight size maps appear;
   - hovering shows another plane and leaving returns to the held one;
   - Right steps by 1; Shift+Left steps by 10;
   - exactly one filmstrip frame is marked held;
   - Escape releases.
4. **Detail size 64:** the caption and share change and that map is marked; clicking a size map moves the switch.
5. **Show the plane** in a pinned sample holds its leading plane.
6. **Keys:** 1-5 choose lenses; Space down cleans the photograph and up restores it; E toggles the engine room.
7. **On the Library:** the activity tray and the rig popover open, and opening one closes the other.
8. **In flight:** G opens glance; Escape returns.
9. **Performance:**
   - pointer-only motion over each new view rebuilds no cached mesh;
   - a warm hover sweep uploads nothing and starts no task;
   - the rail at 6,000 planes draws at most width/2 columns.

### 10.2 Visual comparison

**Reference images**

- Run `python experiments/desktop-studio-2026-11-20/mockups/build.py`, then `render-reference.py`.
- This writes 25 reference images at 1680 × 1050 and `outputs/reference/metrics.json`: the rectangles of the top bar, control strip, canvas, photograph, rail, filmstrip, inspector, tabs, footer, hint bar and so on.
- They need the private pictures, made by `make-assets.py`; they are not in Git.

**Comparing**

- For each station, render the app offscreen against a copy of the owner's catalog: `--offscreen-screenshot`, `--catalog <copy>`, `--open-run <run>`, `--route …`.
- Use the 299-plane weevil run `C:\Users\chris\Pictures\Strehl\strehl-1793781369068-68052-3`. It is a CPU render with maps.
- Review side by side with the reference.
- Chrome rectangles must match within ±2 px. Content need not match pixel for pixel: the mockup's data is illustrative (computed from camera JPEGs), the app's is real.

### 10.3 Performance

Section 5.3 for every phase.

### 10.4 Rig

Capture work (P6, H1-H3) is tested on the rig with manage power on, on a structured subject, and
ends with the camera and light off.

## 11. Compatibility

| Contract | Rule |
| --- | --- |
| Agent and control snapshot | Keys in 6.6 stay; additions only (`activities`, `route`, `notices`). `AgentCommand` is `deny_unknown_fields`: new commands are new variants; existing ones keep their fields |
| Camera host protocol | `deny_unknown_fields` on commands: new fields default and omitted; capability read from state first. New state fields are additive; absent means unsupported |
| Catalog | Format 2 with a verified backup (6.7); older builds refuse rather than strip |
| Recipe | Optional fields only; `version` stays 1; engine recipe cap 1 MiB (`region-repair.rs:34`); UI sidecar cap 2 MiB (`edit-workspace.rs:796`) |
| Render output | Bytes unchanged by any UI or diagnostics change (rule 26) |
| Old runs | Hex diagnostics in old logs still parse; reopen limit applies only to them |

## 12. Risks and unknowns

- **E1 cost on the GPU** is unmeasured; the readback must not stall the fold. Fallback: maps for every other plane, with the history series filling the rest, clearly marked.
- **E5 memory** may make focus evidence unaffordable at the A7CR plane; the depth lens then stays off.
- **Archive memory** at 65,536 maps is about 96 MiB (DERIVED); measure on a 6,000-plane run before raising further.
- **The catalog at 6,000 planes** may approach its 32 MiB cap (6.7).
- **The incremental proof** re-solves alignment; its cost at 512 frames on a below-normal worker during a capture must be measured against the checker's CPU use.
- **Fonts on other platforms** fall back to the system UI face; the look will be plainer there until the egui upgrade or an owner decision to bundle an open face.
- **The Quiet-mode API** is a candidate, not yet tried.
- **Typed host state** may expose fields the desktop misreads today. Treat differences as bugs to report, not to paper over.
- **The mockup's illustrative data** (depth map, plane regions, bars) came from unaligned camera JPEGs. Real engine data will look different; do not tune displays to the mockup's numbers.

---

## Appendix A: tokens

Values come from the mockups (`src/base.css`, `src/screens.css`), after the contrast pass: every
`ink3` is at least 4.5:1 on its surface.

| Token | Graphite | Instrument | Lightbox |
| --- | --- | --- | --- |
| `bg` | `#0b0b0c` | `#10141c` | `#e7e6e1` |
| `panel` | `#111112` | `#141821` | `#f3f2ee` |
| `raised` | `#171718` | `#1a1f29` | `#faf9f6` |
| `control` | `#1e1e20` | `#212835` | `#e9e7e1` |
| `line` | `#232326` | `#272e3a` | `#d8d5cd` |
| `line2` | `#37373c` | `#3a4353` | `#b9b5ab` |
| `ink` | `#e9e6de` | `#e2e0d8` | `#19191b` |
| `ink2` | `#a19f98` | `#99a2ae` | `#55544f` |
| `ink3` | `#807e77` | `#7c8799` | `#6f6d66` |
| `accent` | `#e6b450` | `#e6b450` | `#a46300` |
| `accent_ink` | `#171204` | `#171204` | `#ffffff` |
| `accent_soft` | accent at 12 % | accent at 12 % | accent at 10 % |
| `ok` | `#a9c779` | `#a9c779` | `#4f7d2c` |
| `warn` | `#f08a4b` | `#f08a4b` | `#b9520c` |
| `bad` | `#e5604c` | `#e5604c` | `#b83224` |
| `info` | `#8ab4e8` | `#8ab4e8` | `#2a66ad` |
| `plane` | `#55d6c4` | `#55d6c4` | `#0c8a7c` |
| `surround` | `#0e0e0f` | `#0c0f15` | `#2a2a2b` |

On Lightbox, text placed on the dark surround uses `ink #e9e6de`, `ink2 #a19f98`,
`ink3 #96948d`, `line #3a3a3d`, `line2 #57575c`; panels floating over it use the paper inks.

**Detail spectrum** (2, 4, 8, 16, 32, 64, 128, 256 px):

- Dark themes: `#5fd9cf #7fd3ea #a7c9f2 #c8c0ef #e2b9dc #f1b7b4 #f4c18a #edd06c`.
- Lightbox: `#0f9d92 #1f8fb5 #3f78c9 #6a5fc4 #a2529f #c2524d #c47a1c #a58a00`.

**Type scale** (points at 1.0 pixels per point):

| Size and weight | Use |
| --- | --- |
| 64 light | headline figures (136 in glance) |
| 24 strong | titles |
| 15 strong | statements |
| 13 regular | body and controls |
| 12 regular | secondary; the smallest sentence size |
| 10.5 strong | capitals tracked at 0.13 em; labels, stations, links |

Figures are tabular wherever they change.

## Appendix B: layout rectangles

From `outputs/reference/metrics.json` (x, y, width, height at 1680 × 1050), Stack station:

| Part | Rectangle |
| --- | --- |
| top bar | 0, 0, 1680, 44 |
| stations | 570, 0, 541, 43 |
| control strip | 0, 44, 1332, 36 |
| canvas | 0, 80, 1332, 756 |
| photograph | 128, 94, 1076, 718 |
| core sample | 330 × 415 |
| peek card | 372 × 276 |
| rail | 0, 836, 1332, 190 |
| rail head | 0, 837, 1332, 30 |
| rail chart | 0, 867, 1332, 84 |
| filmstrip | 0, 951, 1332, 75 |
| filmstrip frame | 74 × 63 |
| inspector | 1332, 44, 348, 982 |
| inspector tabs | 36 high |
| inspector footer | 1333, 973, 347, 53 |
| hint bar | 0, 1026, 1680, 24 |
| two-up (held) | 16, 162, 1300, 591 |
| check row | 315 × 54 |

**Other stations:**

- **Capture plan:** canvas 0, 80, 1332, 811; rail chart 104 high; inspector footer 86 high with the 208 × 36 Start button.
- **In flight:** headline 24, 64, 1284, 108; proof 930 × 620; latest plane 340 × 227.
- **Library:** sidebar 232 wide.
- **Subject:** left column 500 wide.
- **Develop:** tools 44 wide; rail 193 high.
- **Engine room:** pipeline strip 58 high; rail chart 70 high.

## Appendix C: keys

| Where | Keys |
| --- | --- |
| Everywhere | Ctrl K palette · F focus mode · Ctrl Z / Ctrl Shift Z undo and redo in the station's scope · Escape closes popovers, releases a held plane, leaves glance |
| Library | Enter open · F2 rename · drop folders to make subjects |
| Stack | 1-5 lenses · hold Space for the clean photograph · E engine room · ← → step a held plane, Shift for 10 · Ctrl Enter render again |
| Capture plan | ← → focus by 1, Shift for 16 · S mark start · E mark end · T test shot · Enter start |
| In flight | Space pause · G glance · P proof full screen |
| Develop | B depth brush · [ ] brush size · \ before and after · Alt inspect planes under the pointer |
| Export | Ctrl E export the ticked presets · Ctrl Shift E export again as last time |

Keys are per station. S and E on Capture do not conflict with E on Stack.

## Appendix D: where to start in the code

| For | Start at |
| --- | --- |
| App state and the frame | `StrehlApp` `app.rs:121`; `update_workspace` `app.rs:2824`; `impl eframe::App` `app.rs:2931` |
| Today's navigation | `Sidebar` `app-workspace.rs:6`; `navigation_rail` 532; `status_bar` 826; `poll_capture` 32 |
| Window chrome | `window-chrome.rs` `finish` 128, `drag_space` 43, `finish_resize` 249 |
| Offscreen and headless | `app-offscreen.rs` `run_offscreen` 17; `StrehlApp::screenshot` `app.rs:2657`; `app-headless.rs` 155, 195, 209 |
| Tasks | `jobs::Task` `jobs.rs:90`; `spawn_task` 114; `spawn_notifying_task` 175; `OwnedChild` 1295 |
| Catalog | `Catalog` `workspace-history.rs:177`; `NodeKind` 108; `migrate_runs` 710; `validate` 755; reopen limit 911 |
| Previews | `SourceBrowser` (`source-browser.rs`, constants 25-53); `PhotoSlot` `workbench.rs:22`; `FILMSTRIP_WORKERS` `source-preview.rs:38` |
| Photograph viewer | `photo-viewport.rs` constants 15-18; `PhotoPresenter` `hdr-display.rs` |
| Timeline | `process-participation.rs` (`MAX_CONTACTS` 16, `update`, `update_plot`, `band_signature`) |
| Evidence | `AdmissionArchive` `process-provenance.rs` (`SAMPLE_LIMIT` 10, `MAX_ENTRIES` 12); `PipelineProgress` `pipeline.rs` |
| Plane regions | `DenseAdmissionCache` `process-admission-regions.rs:66`; `DenseRegionPainter` 1068 |
| Region probe | `RegionProbe` `process-region-probe.rs:217`; `region_at` 780; `popup_placement` 799; `diagnostic_tooltip` `process-region-visual.rs:16` |
| Shared inspection state | `ProcessTheater` `hover_source` / `inspected_source` `process-theater.rs:81-83`; `inspection_frame` 694 |
| Capture | `CaptureWorkspace` `capture-workspace.rs:25`; Start condition 1684; `Command` `crates/strehl-capture/src/session.rs:604` |
| Editing | `DevelopmentRecipe` `crates/strehl-edit/src/recipe.rs`; `EditorState` `edit-workspace.rs:49`; recipe sidecar cap 796 |
| Engine diagnostics | `crates/strehl-cli/src/ui-diagnostics.rs` (`FrameTap`, `gate-support` 117); `gpu_fold_phases` `merge_cmd.rs:5636` |
| Region repair | `crates/strehl-cli/src/merge_cmd/region-repair.rs`; its tests `region-repair-tests.rs` |
