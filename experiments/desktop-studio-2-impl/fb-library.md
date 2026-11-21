# Owner feedback: Library management

**Date:** 2026-11-21. **Branch:** `studio2/fb-library` from `ef98da086`.
**Request (verbatim):** "the Library needs more basic management tools. for example, how do i
delete something there?"
**Environment:** Windows 11, debug and release builds of `strehl-ui`, `CARGO_BUILD_JOBS=8`,
other lanes building on the same PC.

## What was built

| Area | Change |
| --- | --- |
| Delete | Right-click a subject card, a list row, a stack row on a subject page or the subject's picture: **Delete…** (Del). The Delete key deletes the selection, else the card under the keyboard cursor (Library) or the stack whose lineage is open (subject page). The selection bar has **Delete…**. All open one modal confirmation. |
| Confirmation | Says what leaves the library with counts ("1 subject, 1 stack and 2 renders leave the library."), that Ctrl Z puts them back, and per category on disk: files, bytes, folders and where they go (Recycle Bin of which volume, or permanently and why). Sizes are measured on a worker; the dialog shows "measuring…" until then. Lists what will not be deleted and why, and stacks kept in the library. The source photographs need a second step that states the count, size, folders and whether they can be recovered. |
| Other tools | **Rename…** (F2, now also for stacks), **Move to collection** (submenu, with New collection; also drag cards onto a collection in the side list), **Merge into** another subject (one subject) or **Merge into one** (a selection), **Move to subject** for stacks (with New subject), **Show photographs in Explorer**, **Show renders in Explorer**, Stack / Stack next as before. |
| Selection | Ctrl click toggles, Shift click selects the range from the last clicked, Ctrl A selects everything shown, Escape clears; on the grid, the list and the subject page's stacks. A ruled bar along the bottom names the selection and offers its actions and keys. Plain click still opens. |
| Date bug | A subject whose stacks were never rendered was dated by the time of migration ("today"). Migration now dates it by the earliest of its first render and its photographs' recorded write time, else no date; the card and the stack row read the stacks' own records (renders, versions, exports, capture) and fall back to the subject's creation only when there are none. The journal gains "<stack> captured · N planes". |
| Look | `library-menu.rs`: a square, ruled menu drawn with the Library palette, keys on the right, one level of submenus (scrolling after 12 rows), the popover shadow of the theme; ticks and an accent rule mark selected items. Hint bar: Ctrl Click select, Del delete. |
| Offscreen | `--overlay library-menu|library-menu-move|library-select|library-list|library-delete|library-delete-sources|library-delete-confirm|subject-menu|subject-menu-move|subject-select`; matching routes in `visual-check.py`. |

New modules: `catalog-removal.rs` (model: remove, restore, merge, attribution),
`library-delete.rs` (measure and delete on workers, Recycle Bin), `library-menu.rs`
(menu, selection, bar), `app-library-manage.rs` (intents, dialog, overlays), each with a
`*-tests.rs` sibling. `windows-sys` gains the `Win32_System_Registry` feature
(`Cargo.lock` unchanged).

## Decisions (ARGUED)

- **Removal is always done and undoable.** A removed stack takes its render records, the
  versions developed from them and their export records out of the catalog with it;
  otherwise the next load turns its renders into "Imported stacks" and the versions fail
  validation. `RemovedRecords` keeps each record with its index, and undo restores the
  catalog exactly (tested on JSON equality). The removal is one entry of the existing
  project journal (`ProjectExplorer::organize_removing`), so Ctrl Z and Ctrl Shift Z in
  the window work as for any library edit and an earlier rename stays undoable.
- **Files are opt-in per category, both off by default.** Strehl's renders are its job
  folders (`strehl-<millis>-<pid>-<n>`), deleted whole; imported sessions, folders not
  named like a job folder, or a folder holding any record that stays (another stack's
  photographs, another render, an export that stays) are refused. Exported files written
  elsewhere are never deleted; ones inside a deleted render folder go with it, and the
  dialog says how many of each.
- **Source photographs are attributed file by file.** Only the files the stack recorded,
  all inside its folder, and not recorded by any stack that stays; in a capture folder the
  receiver made (`manifest.json` and `events.jsonl`) also its records and `frame-*` files.
  Anything else stays, and the folder goes only once empty (`remove_dir`, never
  recursive); with the Recycle Bin, a folder holding nothing else is recycled as one item.
  Each folder is checked again just before deletion.
- **The capture receiver and the Pi.** There is no desktop function that deletes a capture
  folder to reuse: the earlier bug was fixed on the Pi (`recover_journal` in
  `strehl-capture/src/transfer.rs` drops its active run when the PC folder is gone and the
  run has its `result.json`). The desktop keeps to that rule: a capture folder without
  `result.json`, or the folder the receiver is writing, is never deleted (checked when
  measured and again when deleted). The receiver tolerates missing registered folders
  (`only_the_newest_run_with_a_journal_and_no_result_is_in_progress`). DERIVED from the
  code; not exercised on the rig.
- **Recycle Bin or permanent, decided before asking.** For each category, the bin of every
  volume it touches must be on (`NukeOnDelete` 0) and hold that volume's share
  (`MaxCapacity` under `HKCU\…\BitBucket\Volume\{GUID}`); otherwise the category is
  deleted permanently and the dialog says so in the failure colour, naming the bin's
  size. Recycling uses `SHFileOperationW` with `FOF_ALLOWUNDO` and `FOF_WANTNUKEWARNING`,
  so a file Windows will not recycle after all raises Windows' own warning instead of
  being destroyed silently. When the bin would overflow its size, the dialog says Windows
  may empty older items.
- **In use.** Stacks rendering, waiting in the queue or being captured stay in the
  library (their subject too) and are listed. The open stack leaves the library but keeps
  its files: the workspace reads them and saves edits beside the render; the window stops
  pointing at it.
- **Collections.** In catalog format 2 a subject sits in exactly one collection, so "add
  to / remove from a collection" is **Move to collection** (and dragging onto one); no
  multiple membership was added.
- **Merge.** The chosen subject keeps its name and picture; the others' notes are
  appended, missing optics and scale are filled, the earliest date kept; the others leave
  through the same journal entry.

## Verification

Commands, from `C:\w\f-library`, with `TMP` and `TEMP` set to
`C:\strehl-scratch\f-library\tmp` so test fixtures are created there:

```powershell
cargo test --locked -p strehl-ui
cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -- --check
python experiments/desktop-studio-2-impl/visual-check.py --exe target\release\strehl-ui.exe --out C:\strehl-scratch\f-library\shots <routes> --reference <main checkout>\experiments\desktop-studio-2026-11-20\mockups\outputs\reference
```

- **Tests** (MEASURED): 1,419 passed, 0 failed, 34 ignored; "Compiling strehl-ui"
  observed. 36 new tests (two ignored, run by hand): removal and exact restore, refusal
  changing nothing, no "Imported stacks" after a reload, undo and redo without ending the
  history, merge and its undo, attribution (job folders, recorded photographs, shared
  folders, imported sessions, exports inside and outside); measuring and deleting on
  scratch fixtures (strangers kept, capture without result kept, capture being written
  kept, swapped folder refused, folder removed only when empty, the bin decision); the
  menu, its submenus, selection clicks, Ctrl A, Escape, Delete, F2, the bar, dragging
  onto a collection, list rows, the subject page's rows and picture; the dialog from the
  menu and the Delete key, removal undone by Ctrl Z, the two-step deletion of a scratch
  capture, stacks in use kept; the date regression. One existing assertion changed: a
  migrated subject with no recorded time is now dated 0, not the migration time.
- **Falsification** (MEASURED): with the migration's fallback restored to the current
  time, the date test fails; with the `result.json` check removed, the capture test
  fails; with every file of a capture folder counted as the stack's, the measuring test
  fails. Each passes when restored.
- **Clippy and format** (MEASURED): clean; "Checking strehl-ui" observed.
- **Recycle Bin** (VERIFIED): the ignored test
  `recycling_a_scratch_folder_moves_it_to_the_recycle_bin`, with
  `STREHL_RECYCLE_SCRATCH=C:\strehl-scratch\f-library\recycle`, moved
  `strehl-f-library-recycle-check` there; the Shell's Recycle Bin listing shows it from
  that folder. `bin_room` read 102,118,719,488 bytes for C:, the registry's 97,388 MB. The
  folder is still in the Recycle Bin.
- **No real data touched** (MEASURED): every deletion ran on fixtures under
  `C:\strehl-scratch\f-library`; offscreen pictures do not save, and the owner's
  `projects.json` SHA-256 stayed `8b877fd1…7de2f`.
- **Cost on the UI thread** (MEASURED, debug build, copy of the owner's catalog, ignored
  test `owner_catalog_copy_delete_plans_are_cheap`): the dialog's catalog work for one
  subject takes at most 22.4 ms, all 21 subjects at once 15.3 ms; once when the dialog
  opens, never per frame. Disk work (sizes, listings, bin) is on a worker. Pointer motion
  over 200 subjects with all selected and the bar shown rebuilds neither model nor list
  (test). On the copy, three session stacks spanning several folders are refused for
  sources ("records photographs outside its folder"), and two pairs of stacks sharing
  `bug-3` folders are refused unless both are deleted.
- **Look** (VERIFIED by viewing, release build, owner's catalog copied by
  `visual-check.py`): `C:\strehl-scratch\f-library\shots\` `library-menu.png`,
  `library-menu-move.png`, `library-menu-lightbox.png`, `library-menu-instrument.png`,
  `library-select.png`, `library-list.png`, `library-list-lightbox.png`,
  `library-delete.png`, `library-delete-sources.png`, `library-delete-confirm.png`,
  `library-delete-lightbox.png`, `library-delete-instrument.png`, `subject-menu.png`,
  `subject-menu-move.png`, `subject-select.png`, and `library-delete-permanent.png` (a
  scratch catalog whose capture holds a sparse 120 GB file: "deleted permanently, not
  moved to the Recycle Bin: larger than the Recycle Bin on C: (it holds 102 GB)"). Square
  corners, hairlines, tracked capitals and the theme's colours in all three themes. The
  `generated-smoke-input` card now reads "25 Oct" (its files' recorded write time), not
  "today".
- **UNVERIFIED:** the interactive window (no Computer Use; behaviour is covered by egui
  input tests); Show in Explorer end to end (it would open Explorer on the owner's
  screen; target resolution is tested, `reveal_path` is unchanged); a deletion with the
  receiver and Pi connected; Windows' behaviour when recycling would overflow the bin.

## Not built

- Dragging stacks between subjects (the menu and the bar do it); deleting collections;
  agent or control-interface commands for delete, move and merge.
- Removal undone after files were deleted puts the library entries back; files moved to
  the Recycle Bin return only when restored from it, and permanently deleted files do not.
