# Owner feedback round 3: subjects in the Library and Capture

**Date:** 2026-11-22. **Branch:** `studio2/h-subjects` from `d359bbe28`.
**Environment:** Windows 11, debug and release builds of `strehl-ui`, other lanes building
on the same PC (CPU load 34-62 % during the timings below).

## The owner's words

On the Library screen:

- "i would like a way to create a new empty subject right there, without choosing anything.
  this would allow me to move stacks around if needed."
- "the preview images aren't the correct ratio. they crop the actual subject."

On the Capture screen:

- "the default subject for capture is i guess the most recent subject? i think it should
  actually be a new one by default and force a new name. I've forgotten twice now to create a
  new subject and the stack went to the wrong subject, when it should have been new."

## What was built

| Area | Change |
| --- | --- |
| New empty subject | The Library's **New subject** menu has a third item, **Empty subject…**. It opens a modal that asks for the name and nothing else. The name is required and may not be another subject's name, compared trimmed and ignoring case. The modal says why **Make subject** is unavailable ("A subject named "bug-3" is already in the library"). It shows where the subject goes: the collection being viewed, else the collection of the card under the keyboard cursor, else the first collection, and any collection can be picked. Enter makes it and Escape cancels. The new card is selected and shown; a filter or search that would hide it is cleared. |
| Undo | Making a subject is one entry of the project journal (`ProjectExplorer::organize_creating`). Ctrl Z takes the subject out of the library again, and Ctrl Shift Z brings it back with the same id. Until now an undo never removed a subject, so "Move to subject > New subject" left an empty "bug-3 2" behind after Ctrl Z. Now Ctrl Z moves the stacks back and removes the subject. A failed edit leaves the catalog as it was (stacks back, made subjects and collections out). |
| Moving stacks | This already worked (fb-library): right-click a stack, **Move to subject**, or the selection bar. It was hard to find, so the stack's lineage (one click on a stack row) now has a **Move to subject…** button between "Shoot again" and "Reveal folder". It opens the stack menu's own submenu, already open: **New subject…** first, then every other subject with its collection. The list scrolls after 12 rows, so a large library fits on screen. It moves the selection when the stack is in one; the selection bar's **Move to subject** opens the same submenu. **New subject…** (here, in the right-click menu and in the selection bar) opens the naming modal, which moves the stacks into the new subject when it is made, as one undoable step. Before, it made "bug-3 2" and opened Rename. A subject page with no stacks says how stacks come to it. |
| Previews | Every Library and subject-page picture is drawn whole, with its aspect kept, centred in its cell on the cell's raised ground (`LibraryPreviews::paint_fit`, `fitted`). This covers the grid cards, the list rows, the rig strip, the subject's picture, the stack rows and the lineage (renders, versions, exports). The cells keep their size and rules. `paint_cover`, the only cropping code, is gone. The Projects drawer already fitted its pictures and now uses the same helper. |
| Capture subject | A capture starts a **new** subject unless an existing one is chosen on purpose: picked from the subject field's list ("Add this stack to", each subject with its collection and stack count), or asked for from the Library ("New stack of this subject", "Shoot again"). Typing a name means a new subject; typing an existing subject's name is not a choice. Under the names, one line says where the stack goes: "Goes to a new subject, "Harvestman", in Bugs", "Adds a stack to "bug-3" · Bugs · 2 stacks", or, with a warning mark, "Name the new subject this stack starts, or choose an existing one" or ""bug-3" is already a subject: choose it from the list…". "A new subject instead" leaves a chosen subject. |
| Start and Schedule | A new pre-flight check, **Subject** (`Check::Subject`, `Fix::NameSubject`), keeps Start, Enter and Schedule unavailable until the new subject has a name of its own or the chosen subject is still in the library. It has its own chip in the strip, the sentence beside Start, and a fix that puts the cursor in the field. |
| After a capture | The capture records the plan's names, including the chosen subject's id, as before. Once it is over and Back to planning returns to the plan, the subject, the choice and the stack name are cleared, so the next capture asks again. A finished capture lands in the chosen subject by id, or in the new subject by name (made then, in the collection the Library asked for, else beside the selected stack's subject, else "Captures"). A capture the plan named nothing for (started by an agent, or opened from the captures list) no longer goes to the most recently opened subject. It stays with an existing stack of its folder, else starts a subject named for the folder. |
| Offscreen | `--overlay library-new-menu|library-new-subject|library-new-subject-taken|subject-move|subject-new-subject`; `--capture-fixture plan+unnamed|plan+subjects|plan+existing|plan+taken`. |

New modules: `app-library-subject.rs` (the modal and making the subject) and `capture-subject.rs`
(where the stack goes, the sentence and Start's blocker), each with a `*-tests.rs` sibling.

Changed (small, local edits in shared files are marked *shared*):

- `catalog-subjects.rs` (`subject_named`, `new_subject_name`);
- `project-explorer.rs` (`organize_creating`, symmetric undo/redo);
- `library-station.rs` (intent, menu item, `launch_new_menu`);
- `library-previews.rs`, `subject-page.rs`, `library-menu.rs` (label "New subject…");
- `app-station-library.rs` (state, routing, `set_plan_subject` by id);
- `app-library-manage.rs` (*shared*: the old move-to-new-subject branch removed, overlays);
- `app-station-capture.rs` (subject list, `capture_home`, `capture_destination`);
- `capture-station.rs` (*shared*: names with the chosen id, reset, fix, fixtures);
- `capture-plan.rs` (*shared*: `PlanView.chosen`, `focus_subject`, `PlanInputs.subject_home`, the names block; nothing in the rig settings, steps or footer);
- `capture-preflight.rs`, `capture-workspace.rs` (module);
- `app.rs`, `main.rs` (*shared*: module, overlay names).

Not touched: `capture-rig-settings.rs`, `capture-flight.rs`, the preview disk caches.

## Decisions (ARGUED)

- **The disk caches needed no change.** The headers of the owner's caches were read without
  writing (MEASURED). `explorer-previews\`: 144 entries, all at the source's aspect (384 × 256 for
  7032 × 4688, 384 × 257 for 1616 × 1080). `source-previews\`: 268 entries (544 × 364 and 480 × 321
  for 9504 × 6336). The worker's `scale_to` keeps aspect too. The crop was made only at paint time
  (`paint_cover`), so nothing needs regenerating or rekeying.
- **Why the owner saw cropping.** The card's picture is the card's width by 172 px. At 1680 px
  wide that is 264 × 172 (1.53), nearly the photographs' 3:2; at 1280 px it is 318 × 172 (1.85),
  which cut about a fifth of the height. `narrow\compare-1280.png` shows base and new side by side.
- **The default for Capture.** The plan starts empty, so Start waits for a name. A default name
  ("Subject 17") was rejected: it would let a forgetful Start go through again, which is the
  failure the owner described. The clash rule makes "add to an existing subject" a deliberate
  choice, because typing its name is refused with a pointer to the list.
- **When the names clear.** They clear when the station is back on the plan after the capture
  (after its review), not at Start. Glance, the breadcrumb and the in-flight view keep showing
  them while it runs. A stopped capture also clears them: keeping them would recreate the
  "forgot to change it" case.
- **Test shots, calibration and surveys** make no stack and are not blocked (a test shot sends
  its command while unnamed; tested).
- **Agents.** `CaptureCommand` still goes straight to the host (`agent-control.rs` unchanged;
  its tests and the MCP tests pass). An agent-started capture takes the plan's names when there
  are any. Otherwise it gets a subject named for its folder, never the most recent subject. The
  owner can rename or merge that subject; it is never lost.
- **Dragging a stack onto a subject was not built.** In Studio 2 stacks and subjects are never on
  screen together: the grid shows subjects and a subject page shows one subject's stacks. A drop
  target would need a new panel. The lineage button and the scrolling menu do the same job in two
  clicks. The Projects drawer's tree still drags nodes as before.
- **Undo removes a subject only if it is empty.** The journal is cleared whenever the stacks or
  renders change outside it, so a made subject can only hold stacks moved by later journal
  entries, and those are undone first. If it holds something anyway, it stays (`remove_nodes`
  refuses to orphan a stack).

## Verification

Commands, from `C:\w\h-subjects`, `TMP`/`TEMP` = `C:\strehl-scratch\h-subjects\tmp`:

```powershell
cargo test --locked -p strehl-ui
cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -- --check
cargo test --locked --release -p strehl-ui -- --ignored benchmark_grid_scroll_with_pictures --nocapture
cargo test --locked --release -p strehl-ui -- --ignored benchmark_destination --nocapture
```

- **Tests** (MEASURED): 1,512 passed, 0 failed, 45 ignored; "Compiling strehl-ui" seen. Before
  this branch: 1,497 passed, 43 ignored. The new tests:
  - name rules;
  - the empty subject end to end through the menu and the modal: refused unnamed and for a
    clash, collection chosen, card selected, saved and reloaded, Ctrl Z and Ctrl Shift Z;
  - Escape keeps the Library's selection, and the Library's keys wait while the modal is open;
  - stacks into a new subject and back with no empty subject left, and a failed make changing
    nothing;
  - fitted geometry; grid and list pictures drawn whole at 3:2;
  - the lineage's Move to subject, and the selection bar's;
  - the destination rules and blocker; the strip chip and fix;
  - Start, Schedule and test shot with and without a subject, the names taken and cleared after
    review;
  - an unnamed capture not landing in the most recent subject; a chosen subject found by id,
    with the Library setting and clearing it;
  - the plan's line drawn.

  Tests changed: the preflight and station fixtures now name a new subject, so they keep
  testing what they tested. The fb-library move test now goes through the naming modal.
- **Falsification** (MEASURED):
  - Base `d359bbe28` with the new grid test fails: "Grid: the whole picture, uncropped; uv x 0..1
    y 0.03436333..0.9656367".
  - With undo ignoring made subjects, the Subject blocker removed and the reset removed (one
    build), four tests fail: both Library undo tests, the strip chip test and the station test.
    All pass again when restored.
- **Clippy and format** (MEASURED): clean; "Checking strehl-ui" seen.
- **Smoothness** (MEASURED, release, base and new test binaries alternated three times, CPU load
  34-62 % from other lanes). The benchmark scrolls the grid 40 px per frame, 120 frames, five
  runs, 200 subjects with every tile resident (0 decodes during the run), 16 pictures per frame,
  and times CPU paint plus tessellation:

  | Binary | ms per frame (min-max of 15 runs) |
  | --- | --- |
  | Base `d359bbe28` | 0.086-0.117 |
  | New | 0.079-0.093 |

  Fitting costs no more than cropping: one textured rectangle per cell either way. The subject
  check runs on every Start check, which is several times a frame on Capture. With 2,000
  subjects and a new name (every subject compared) it takes 6.5-7.4 µs; the comparison does
  not allocate.
- **Look** (VERIFIED by viewing; release build; copies of the owner's catalog under
  `C:\strehl-scratch\h-subjects\`, never in Git):
  - `v3\` (final build):
    - Library: `library.png`, `library-lightbox.png`, `library-list.png`, `library-new-menu.png`,
      `library-new-menu-lightbox.png`, `library-new-subject.png`, `library-new-subject-taken.png`,
      `library-new-subject-lightbox.png`;
    - subject page: `subject.png`, `subject-lightbox.png`, `subject-move.png`,
      `subject-move-lightbox.png`, `subject-new-subject.png`;
    - Capture: `capture-plan.png`, `capture-unnamed.png`, `capture-subjects.png`,
      `capture-existing.png`, `capture-taken.png`, `capture-unnamed-lightbox.png`,
      `capture-existing-lightbox.png`, `capture-flight.png`.
  - `v2\empty-subject.png`, `v2\empty-subject-lightbox.png`, `v2\empty-library.png`: a catalog
    copy with one empty subject added.
  - `narrow\library-{base,v2}-{1280x800,2560x1440}.png` and `narrow\compare-1280.png`.

  All of them have square corners, hairlines and the theme's colours. The Start button and
  Schedule are dimmed while the subject is unnamed. The in-flight view is unchanged.
- **The owner's data** (MEASURED): `projects.json` SHA-256 `4d1bcd49…7321c` before and after;
  every picture used a copy. As in earlier lanes' visual checks, offscreen pictures share the
  derived thumbnail caches beside the owner's catalog (`explorer-previews\`, `source-previews\`),
  which may have gained entries.
- **UNVERIFIED:**
  - the interactive window: no Computer Use, so behaviour is covered by egui input tests;
  - a real capture on the rig, including that the names are taken by a host-started (scheduled)
    run;
  - a library of hundreds of subjects in the move menu: its 12-row scrolling is fb-library's
    code, tested there.

## Open, or for the owner

- **Scheduled stacks** take the plan's names when the run starts, as before. Editing the names
  while a schedule waits changes where that stack goes. Snapshotting names per schedule would
  need the host to say which run a schedule started.
- **The collection of a new capture subject** stays as before (beside the selected stack's
  subject, else "Captures"), and the plan line now says which. The owner may prefer always
  asking, or always "Captures".
- **Agents** have no command to set the plan's subject. A subject named for the folder is the
  fallback; an `import_stack`-style `subject` argument for captures would let an agent choose.
- The Library grid's selection bar (subjects: Move to collection, Merge into one) still flattens
  its submenu into one list. Collections are few, so it was left as it is.
