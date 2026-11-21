# P4 model: catalog format 2 (subjects)

**Date:** 2026-11-21. **Branch:** `studio2/p4-catalog` from `61effa01b`.
**Scope:** the model half of P4 in
[the implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(sections 6.6 hazard, 6.7, 9 P4): catalog format 2, migration with backup, hierarchy, undo,
lifecycle, Locate, interrupted runs, agent commands, minimal subject display in today's
project tree. The library grid and subject page are not built here.
**Environment:** Windows 11, rustc 1.98.0, `CARGO_BUILD_JOBS=8`, debug builds.

## What changed

| Area | Change |
| --- | --- |
| Format | `Catalog.format` (absent reads 1). Loading a format-1 file migrates it in memory; the first save over it writes `projects.v1-backup-<unix>.json` beside it, reads it back (bytes equal, parses as format 1, validates) and only then replaces the catalog. A failed backup removes its partial copy and saves nothing. A file newer than format 2 is refused like a damaged one. |
| Types | `NodeKind::Subject`; `ProjectNode.subject: Option<SubjectMeta>` (present exactly on subjects); `SubjectMeta { hero, optics, scale, created }`; `Optics { camera, lens }`; `ScaleCalibration { um_per_px, source: Measured { slide } \| Entered { magnification, pitch_um } }`. Subject types refuse unknown fields. |
| Hierarchy | Project (collection) > folder* > subject > stack. A stack directly in a project or folder stays valid (format-1 placement). `validate`, `create_*` and `can_move` check the parent by kind. |
| Migration | `migrate_subjects`, after `migrate_runs`, on every load; idempotent. A stack outside a subject joins one in the same container: grouped by its source's parent folder when the stack's name or its source folder's name is a camera folder (`^\d{3}MSDCF$`, a drive root or `DCIM` excepted), otherwise by its own source folder. Existing subjects claim their stacks' keys first, so a later format-1 placement joins its subject rather than founding a duplicate. Subjects are inserted where their first stack sat; selection and expansion are kept; runs, recipes, versions and exports are untouched. |
| Undo | `OrganizedNode` carries the subject record. Undo never deletes a subject, nor a container still holding a subject or stack. Subject metadata edits are undoable. |
| Display | Today's project tree shows subjects as containers ("N stacks", the hero or newest stack's picture, no "New folder" inside). |
| Agent | Additive `CreateSubject`, `MoveNode`, `SetSubjectMeta` (absent keeps, null clears; the picture is a saved render of the subject's own stack, never a path). Snapshot `projects[]` gains `subject`; `kind` gains the value `"Subject"`. MCP schema lists the three. |
| Interrupted runs | `reconcile_interrupted_runs(active)` marks runs left "Stacking" (or the older "Rendering") as "Interrupted" unless one of `active` or a live process owns them. The owner is read from the job folder name `strehl-<millis>-<pid>-<seq>`; on Windows the process must also have started no later than the run (reused ids). Not yet called: see "For the orchestrator". |
| Cargo | `strehl-ui` declares `windows-sys` `Win32_System_Threading` (already compiled through `strehl-cli`; `Cargo.lock` unchanged). |

Deviations from the plan text, both ARGUED:

- **Subject notes live in `ProjectNode.notes`,** not a second `notes` in `SubjectMeta`. Every node
  already has notes, edited in the tree and captured by undo; two notes fields on one node would
  disagree. `set_subject_meta` and `SetSubjectMeta` write `notes`.
- **No optional `kind` on `CreateProject`:** `CreateSubject` covers it and keeps each command's
  fields fixed.

## Model API for the library UI

All on `Catalog` unless noted; no I/O except `sources_present` and `relocate_stack`.

```rust
pub fn create_subject(&mut self, parent: NodeId, name: &str) -> anyhow::Result<NodeId>
pub fn move_node(&mut self, id: NodeId, parent: Option<NodeId>) -> anyhow::Result<()> // kind-aware
pub fn set_subject_meta(&mut self, id: NodeId, edit: SubjectEdit) -> anyhow::Result<()>
pub fn subject_of(&self, stack: NodeId) -> Option<NodeId>
pub fn stacks_of(&self, subject: NodeId) -> Vec<NodeId>
pub fn revision(&self, stack: NodeId, index: usize) -> Option<&Run>
pub fn stack_lifecycle(&self, stack: NodeId) -> Option<StackLifecycle>
pub fn subject_summary(&self, subject: NodeId) -> Option<SubjectSummary>
pub fn library_index(&self) -> LibraryIndex // every stack and subject in one pass
pub fn sources_present(&self, stack: NodeId) -> Option<SourcesState> // one listing per folder, names only
pub fn relocate_stack(&mut self, stack: NodeId, new_dir: &Path) -> anyhow::Result<RelocateReport>
pub fn relocate_stack_to_scan(&mut self, stack: NodeId, scan: &jobs::StackScan) -> anyhow::Result<RelocateReport>
pub fn reconcile_interrupted_runs(&mut self, active: &[&Path]) -> usize
pub(crate) fn legacy_backup(&self) -> Option<PathBuf>
pub(crate) fn default_stack_name(source: &Path) -> String
pub(crate) fn is_camera_folder(name: &str) -> bool
```

`StackLifecycle` has `captured / stacked / developed / exported: StepState`
(`NotYet < NeedsLook < Running < Done`), counts, `last_activity`, `needs_a_look()` (latest render
Failed, Cancelled, Interrupted or unknown) and `next_step()` (`Stack`, `Check`, `Wait`, `Develop`,
`Export`, `Done`). `SubjectSummary` adds the "needs you" counts (`to_stack`, `to_check`,
`stacking`, `to_develop`, `to_export`, `exported`) and the strongest state of each step.
`relocate_stack` scans like opening a stack (blocking; use `relocate_stack_to_scan` from a
background scan) and refuses with a `RelocateMismatch` (missing, resized, unrecorded frames;
downcast from the `anyhow::Error`) without changing anything. Multi-folder session stacks are
refused. Accepted folders re-point the recipe, the renders' `source` and their source records,
including modification times, so the renders reopen against the new folder.

## Results

Commands, from the worktree:

```powershell
cargo test --locked -p strehl-ui
cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -- --check
$env:STREHL_P4_CATALOG='C:\strehl-scratch\p4\projects.json'
cargo test --locked -p strehl-ui -- owner_catalog_copy six_thousand --include-ignored --nocapture
```

- **Tests** (MEASURED): 1,079 passed, 0 failed, 17 ignored (16 before, plus the owner harness);
  "Compiling strehl-ui" observed. 18 new tests: 14 in `catalog-subjects-tests.rs`, two agent
  command tests, one MCP schema test, one tree display test, and one existing test updated
  (`project_catalog_roundtrips…`: the stack placed directly in a folder now gains its subject on
  reload, 3 nodes become 4, and a second reload stays at 4).
- **Falsification** (MEASURED): with undo allowed to delete subjects, the undo test and the agent
  undo test fail; with the live-process check removed, the reconciliation test fails. Both pass
  when restored.
- **Clippy** (MEASURED): the only failure is the known `unnecessary_cast` at
  `capture-workspace.rs:1772` (fixed by P0 elsewhere); with that lint allowed, clean, "Checking
  strehl-ui" observed. The macOS and Linux branches of the process check were not compiled here
  (UNVERIFIED; no other target installed).
- **Format** (MEASURED): `cargo fmt -p strehl-ui -- --check` clean; only files of this change
  were reformatted.

### The owner's catalog (a copy)

Input: a copy of `%LOCALAPPDATA%\Strehl\projects.json`, 8,777,191 bytes, SHA-256
`8b877fd1…7de2f`, format 1 (no `format` key). The original was never opened for writing; its hash
was unchanged afterwards (MEASURED).

- **Subjects** (MEASURED): 35 stacks become **21 subjects**, not the 20 the plan DERIVED. The
  stacks have 20 grouping keys; `bug-3` has four stacks in "Imported stacks" and three in "Bugs",
  and migration keeps every stack in its project, so there are two `bug-3` subjects. Merging them
  would move three stacks between projects without being asked; moving them in the tree (or
  `MoveNode`) does it in one step if wanted.
- **No loss** (MEASURED): all 50 runs, 11 versions and 10 exports serialize identically before
  and after; every run keeps its owning stack; every stack has a subject; the catalog grows
  8,777,191 to 8,782,414 bytes.
- **Backup** (MEASURED): written once on the first save, byte-identical to the input, re-read and
  validated; a reload and a second save write no other.
- **Older build** (VERIFIED): the installed desktop (`desktop-3649b4172aa5ad3e`) run offscreen
  with `--catalog` on the migrated copy shows "Projects could not be read; original retained:
  unknown variant `Subject` …" and leaves the file's SHA-256 unchanged. This build, run the same
  way on the format-1 copy, draws the subjects in the project tree (offscreen does not save).
- **Anomalies:** the 119MSDCF stack's subject is named `macro` (its parent is the general macro
  folder, not a specimen); two test stacks (`input`, `generated-smoke-input`) became subjects;
  the sources of 11 stacks are missing (their `bug-1`, `bug-2`, `bug-5` and `bug-6` folders under
  `D:\personal\macro\insects` no longer exist), the Locate case; one test stack is partial; no run
  was left "Stacking".
- **Lifecycle** (MEASURED): next steps across the 21 subjects: 12 develop, 5 done, 3 stack,
  1 check (bug-3 in "Imported stacks": one stack's latest render was cancelled, another's
  failed).

### Size against the 32 MiB cap

- MEASURED: one 6,000-plane stack with five renders adds 6,510,708 bytes (6.21 MiB, 19.4 % of the
  cap): 180.9 bytes per source identity, repeated in the recipe and every render.
- DERIVED: with the owner's catalog at 8.78 MB, three such stacks fit and a fourth would exceed
  the cap ((33,554,432 - 8,782,414) / 6,510,708 = 3.8). The owner's longest stacks today are about
  1,500 planes (about 1.6 MB with five renders). The sources format is unchanged, as instructed;
  the per-run sidecar of plan 6.7 is the remedy if long stacks multiply.

## Library UI, stage 1 (self-contained screens)

**Scope:** plan 7.3, 5.4 "Library grid", 5.5 item 7. The Library station and the subject page
are modules that take their inputs as parameters and return intents; composing them into the
P1 shell (route, top bar, hint bar, theme tokens) is stage 2. Nothing in `app.rs`,
`app-workspace.rs` or `theme.rs` changed; `main.rs` gained four `#[path]` module lines.

| Module | What it is |
| --- | --- |
| `library-previews.rs` | `ExplorerPreviews` lifted out of the project tree as `LibraryPreviews`; the tree uses it unchanged. Budgets per 5.5 item 7: 240 entries, 48 MiB, 3 workers; 256 px tiles scaled on the worker from the 384 px disk tier; visible requests run before one screen of prefetch; requests not repeated in the last paint are dropped; a row (`group`) uploads together; at most 2 MiB uploaded a poll; `spawn_notifying_task` wakes; `poll` counts once per egui pass so views can share it. |
| `library-paint.rs` | `LibraryPalette` (Graphite defaults from the mockup's `base.css`), the drawn marks (lamp, triangle, diamond, ring, half), tracked capitals, hairlines, square buttons, segments, the four lifecycle bars, badges, tags, size and date formats. |
| `library-station.rs` | Left list (232 px: All subjects, On the rig, Needs you, Collections, storage card), header (counts, legend, search, Recent/Name/Size, grid/list, New subject ▾), on-rig strip, virtualised grid of cards (5 columns at 1448 px), list view, keys, folder drops. |
| `subject-page.rs` | Left column (500 px: back, hero, name and collection, notes, optics and scale, on disk, New stack of this subject, Add folders) and right column (stacks newest first or by name, lifecycle line, depth signature hook, size, Open; the open row's lineage renders → versions → exports, Shoot again, Reveal folder; the journal). Inline editor for name, notes, optics and scale. Trim sources is not built (D9). |

API for the shell:

```rust
LibraryStation::show(&mut self, ui: &mut Ui, inputs: LibraryInputs<'_>) -> Option<LibraryIntent>
LibraryInputs { catalog: &Catalog, revision: u64, previews: &mut LibraryPreviews,
    palette: &LibraryPalette, rig: Option<&RigCapture>, storage: Option<&StorageCard> }
LibraryStation::sources(&self) -> &HashMap<NodeId, SourcesState>   // pass to the subject page
SubjectPage::show(&mut self, ui: &mut Ui, inputs: SubjectInputs<'_>) -> Option<LibraryIntent>
SubjectInputs { catalog, revision, subject: NodeId, previews, palette, rig,
    sources: &HashMap<NodeId, SourcesState>, signatures: Option<&HashMap<NodeId, Vec<f32>>> }
enum LibraryIntent { OpenSubject(NodeId), OpenStack(NodeId), OpenRender { stack, run: PathBuf },
    OpenVersion(String), OpenCapture, NewStackFromCamera { collection, subject },
    PickFolders { collection, subject }, ImportFolders { collection, subject, groups: Vec<ImportGroup> },
    Locate(NodeId), ShootAgain(NodeId), RevealPath(PathBuf), Rename(NodeId),
    EditSubject { id, name, edit: SubjectEdit }, NewCollection, ReviewStorage, Back }
Catalog::generation(&self) -> u64      // bumped by every save; a ready-made `revision`
import_plan(&[PathBuf]) -> Vec<ImportGroup>   // one stack per folder, camera folders by parent
```

The station caches its model (cards, needs-you counts, collections, search text) per
(revision, record counts), the visible list per (model, filter, search, sort, rig subject), and
checks every stack's sources on a worker once per revision (one listing per folder, names only).
The subject page caches its model per (revision, subject) and pools a depth signature to at most
one column per 2 px, cached per series identity and width.

Decisions (ARGUED):

- A card's picture is the first of up to six candidates that loads: the chosen hero, the newest
  stacks' saved renders, then a first source. On the owner's catalog several outputs and source
  folders are gone; without the fallback those subjects had blank cards.
- "Recent" orders by the newest render, version or export, else the subject's creation, so a
  subject made today but never stacked sorts first.
- The subject page's second order is "By name", not the mockup's "By view": the catalog has no
  view field.
- On disk shows the recorded source bytes and the render count only. Render sizes and "could be
  freed" need disk reads or a compaction estimate; the storage card takes the volume's free and
  total space and the compactable total from the shell (`StorageCard`).

### Library UI results

Commands as before (`cargo test --locked -p strehl-ui`, clippy, fmt). Pictures:
`$env:STREHL_P4_SHOTS=<dir>; cargo test --locked -p strehl-ui -- offscreen_library_and_subject --ignored --nocapture`,
with `STREHL_P4_CATALOG=<copy>` for a catalog copy.

- **Tests** (MEASURED): 1,092 passed, 0 failed, 18 ignored (the offscreen-pictures test added).
  New: six station tests (intents, filters, search, sort, virtualisation, preview budgets while
  scrolling), four subject-page tests (order, lineage, journal, every control's intent, editing,
  pooled signature), two preview tests (a row uploads whole; uploads paced), one import-plan test.
  The tree's ten preview tests pass on the lifted service; one independent review test now
  derives its capacity from the byte budget (85 tree pictures of 384 px fit 48 MiB) instead of
  the old 40-entry count.
- **Falsification** (MEASURED): with row grouping disabled the row test fails (2 or 3 of 4 tiles
  shown); with a 128 MiB upload budget the pacing test fails (one uploading poll, three needed).
- **Clippy and format** (MEASURED): clean apart from the known `unnecessary_cast`; "Checking
  strehl-ui" observed after touching the changed files.
- **Paint cost** (MEASURED, debug build, egui included, this PC with other agents building):
  40 and 200 subjects both lay out 16 cards; across 30 pointer-motion frames the model and the
  list are built once; frame median 0.42-0.70 ms, worst 1.2-4.9 ms. The 200-subject shape count
  is within 3 % of the 40-subject one. Release figures are not measured.
- **Previews** (MEASURED, scroll test, 200 subjects with 420 × 280 PNG heroes): at most 3
  decoders; at most 50 tiles requested while still and 100 while scrolling (this paint's and the
  last); after scrolling the full list, 75 decodes, 75 uploads, 12.5 MiB resident, largest poll
  upload 684 KiB; a warm view started no task and uploaded nothing on pointer motion.
- **Look** (VERIFIED by viewing; pictures not committed, D10): offscreen renders at 1680 × 982
  (the area under the top bar) of a fixture with the mockup's subjects, and of a copy of the
  owner's catalog with its real renders, beside `library.png` and `subject.png`. Layout,
  hairlines, capitals, marks, badges, lifecycle bars, rig strip, storage card, lineage and
  journal match; the fonts are the system face until P1, and names are not bold.
- **Owner copy** (MEASURED): 21 subjects; Needs you 4 / 1 / 14 / 8; collections "Imported
  stacks" 15, "Bugs" 6; 11 stacks show "sources moved" (as found by the model's check).

Open for stage 2: route and offscreen `--route library|subject`, theme tokens into
`LibraryPalette`, the shell's revision (or `Catalog::generation`), `RigCapture` from the capture
client, `StorageCard` from a disk-space worker, applying `EditSubject` through
`ProjectExplorer::organize`, executing `ImportFolders` (scan, then one stack per folder in a new
or existing subject), and the depth signatures from the Stack station.

## Depth signatures and Stack next (after P5)

**Date:** 2026-11-21. **Branch:** `studio2/p4-signatures` from `91ebd7e70`.

- **Definition** (VERIFIED by test): the depth rail's own series at its default detail size
  (level 0): per plane, the share of sampled sites whose gate admitted it. `depth-signature.rs`
  replays a saved run as a reopen does (the log, then `evidence.strehl`) into a
  `PipelineProgress` and runs `DepthRail::update` on it; the test checks equality with
  `DepthRail::share` on the same progress. At most 128 values, planes pooled by the ratio of
  sums as the rail pools columns; a column with no observed plane is negative and draws
  nothing. A run without per-plane evidence (older GPU renders, imported sessions, a log over
  the replay bound, a moved run) has no signature and shows none.
- **Cache:** `depth-signatures.json` beside the catalog, keyed by run folder (a saved run's log
  does not change), at most 4,096 entries (oldest computed leave first), written atomically on
  a worker at most every 5 s. A missing, unreadable or newer file starts empty and is left as
  it is until the next save. Offscreen pictures keep theirs in memory. Nothing is written in a
  run or capture folder.
- **Work:** one replay at a time on a worker, only for the rows painted (list rows; the open
  subject's stacks), newest request first, at most 64 waiting; never while a stack renders or
  Quiet holds (a replay in flight is cancelled when a stack starts and asked for again by its
  row). Offscreen pictures wait for it (`library_loading`). Per frame: one key compare, then
  O(rows painted) look-ups; the index of newest saved runs is rebuilt per catalog revision.
- **Where:** the subject page's stack rows (the 230 x 46 slot the mockup has) and the Library's
  list rows (200 x 40, between the progress words and the badge), the subject's newest render.
  Grid cards are unchanged: the mockup's cards carry no signature. One spark painter
  (`library_paint::spark`) serves both, cached per row, series and width.
- **Stack / Stack next:** a subject page row has Stack left of Open ("Stack next" while a stack
  renders; STACKING or QUEUED in its place when that stack is running or waiting; nothing while
  it is capturing). A Library card or list row offers "Stack · N stacks" or "Stack next · N
  stacks" on right-click for the subject's stacks without a saved render that are not already
  running or waiting. Both go through `queue_stack`, which starts at once when nothing renders.
- **Also (P5 open issues):** a capture that finishes while a stack renders joins the queue
  (`queue_finished_capture`; `capture_destination` factored out of `capture_names`); the
  estimate before the merge no longer needs the seed's `frames` line (see `p5-activities.md`).

### Signature results

- **Tests** (MEASURED): `cargo test --locked -p strehl-ui` 1,363 passed, 0 failed, 31 ignored
  ("Compiling strehl-ui" observed); clippy `-D warnings` and `fmt --check` clean. New: rail equality and missing planes, pooling and no-evidence, replay and cancel, the
  worker and cache (computed once, reloaded, unreadable file left alone, a moved run not
  retried, nothing while a stack renders), list rows draw bars and the grid none, right-click
  intents in both states, row buttons and queue states, app-level signatures from a worker,
  queue intents, a finished capture queued, the ETA seed fix.
- **Look** (VERIFIED by viewing): `visual-check.py subject subject-lightbox library` (release,
  the owner's catalog copied to scratch): subject rows show signatures for renders with
  evidence and a bare baseline for the others, Stack beside Open, in both themes; the grid is
  unchanged. A list-view picture with synthetic signatures (`offscreen_list_rows_with_signatures`)
  reads as ruled rows with square bars. The subject route took 8.7 s offscreen including three
  signature replays of the owner's logs, against 5.1 s for the grid (one sample each).
- **Performance** (MEASURED, release, `--test-threads 1`): the list view with a 128-value signature on all 13 painted rows of 200 subjects, pointer sweeping, 0.19-0.62 ms a frame (paint plus tessellation; no signature pooled again after the first frames); the grid, 0.17-0.20 ms (40 and 200 subjects; model and list built once). Host load was high during these runs (about 82 % CPU: other lanes' engine renders and builds, which this lane did not start or stop), so the P0 pointer sweep read process 0.84-2.40 ms (medians 1.66-2.09) and source 0.45-1.25 ms, against the P0 baseline of 1.28-1.32 and 0.45-0.48 measured on a quiet machine; nothing in this change runs in that view. Repeat on a quiet machine before quoting.

## For the orchestrator

- **Startup reconciliation** (one line, `app.rs`, `from_launch`, after `let mut app = Self { … };`):
  `app.catalog.reconcile_interrupted_runs(&[]);`
  No job exists yet at that point; the next catalog save writes the change.
- The milestone row `desktop-studio-2-p4-2026-11-21` is still marked "reserved; not started";
  left for the orchestrator to avoid conflicting table edits across branches.
