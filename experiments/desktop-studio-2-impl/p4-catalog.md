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

## For the orchestrator

- **Startup reconciliation** (one line, `app.rs`, `from_launch`, after `let mut app = Self { … };`):
  `app.catalog.reconcile_interrupted_runs(&[]);`
  No job exists yet at that point; the next catalog save writes the change.
- `git` in this worktree resolves its top level to the submodule's git directory (`core.worktree`
  is set in the shared config). Commits here used `git --work-tree=C:/w/p4`.
- The milestone row `desktop-studio-2-p4-2026-11-21` is still marked "reserved; not started";
  left for the orchestrator to avoid conflicting table edits across branches.
