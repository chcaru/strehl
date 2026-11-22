# g-develop: Develop and Export actions after the owner's run-through

**Status:** results note. Branch `studio2/g-develop`, based on `7f83d3f22`; the fix,
tests and docs are `b70cae4b9`, which every check and screenshot below was run on.
**Date:** 2026-11-21. **Evidence labels** as in `AGENTS.md`.

The owner's feedback (verbatim):

- on the Develop page: clicking "Export..." did nothing after adjusting. same with "Save version"?
- on the Export page: remove "New" tags. the time option for AVIF encoding is gone. which is
  separate from quality i believe.

## Root causes

**Export… did nothing** (VERIFIED, reproduced). The footer button pushed
`DevelopIntent::Export`, and `handle_develop_intent` answered it with
`self.edit_pane.develop.export_requested = true`. Nothing ever read that flag: its comment
says "the shell routes to the Export station", but no code did. The unit test
`develop_intents_route_to_the_editor_or_the_app` asserted the flag, so it passed while the
button did nothing. The mockup's button is `data-go="export"`: it goes to the next
station. Adjusting first made no difference (ARGUED from the code; the regression test
drags Exposure first, as the owner did).

**Save version did nothing** (VERIFIED, reproduced). The intent called
`open_save_edit_version()`, which put a name draft into `photo_history.draft`. The only
code that draws that draft is `photo_history_panel`, which is called by the old Edit and
Export panes (not called since P7 UI stage 2) and by the Projects tree. In the Studio 2
Develop station nothing drew it, so the press made an invisible draft and saved nothing;
the stale field would have appeared later in the Projects drawer.

Reproduction, with the two regression tests added before any fix, run against `7f83d3f22`
(VERIFIED, `cargo test --locked -p strehl-ui actions::`, exit 101, output kept in
`C:\strehl-scratch\g-develop\repro-unfixed.txt`):

```text
test ...actions::export_goes_to_the_export_station_after_an_adjustment ... FAILED
  assertion `left == right` failed: Export… left the photograph in Develop
  left: Develop / right: Export
test ...actions::save_version_asks_for_a_name_and_saves_after_an_adjustment ... FAILED
  saving the version never happened
```

Both tests drive the real shell with egui input: open a photograph (a TIFF on disk with a
catalog beside it), drag the Exposure slider, click the drawn **Export…** or **Save
version**, then press Enter. After the fix both pass (VERIFIED, same command, exit 0).

## What changed

**Develop** (`app-develop.rs`, `develop-station.rs`, `app-station-develop.rs`,
`app-photo-history.rs`):

- **Export…** commits the edit in progress and goes to the Export station. It is always
  enabled while a photograph is open (it is navigation); the Export station says what an
  export waits for. `export_requested` is gone.
- **Save version** opens Versions with a name field at its head (**Save this edit as**,
  default "Version N", focused; Enter or **Save** saves, Escape or **Cancel** cancels).
  While it saves the head says "Saving “Version 2”…"; then "Saved version “Version 2”"
  with the version listed below, and a Done notice in the tray. Errors are shown there in
  words (with Retry when the catalog still needs saving).
- The station's notices (a look that cannot start, Recalculate with no look, a depth
  repair that cannot start, a version that cannot be carried) went only to the tray as
  warnings, and the top bar shows failures only. They now also head the Develop inspector,
  with Dismiss. Photograph-history errors raise a tray notice too.

**Export** (`export-station.rs`, `app-develop.rs`, `app-view-bundle-export.rs`):

- **"New" tags removed** from **Size** and **Sharpen for the size** (the only two; the
  row helper lost its flag).
- **Encoder effort** restored for AVIF presets, its own row under Quality (below).
- Every press answers. The result heads the inspector: "Wrote <file>" or "Wrote N files to
  <folder>" with **Open folder** and **Dismiss**, and a Done notice; a failed file, a
  catalog error or any refused action in words. Before, success showed only as a new row in
  the history table and errors only as tray warnings.
- Without a folder for the subject, the footer button reads **Choose a folder…** and opens
  the dialog (it was disabled, with the reason only in a tooltip). While something must
  finish first, **Export N files** stays enabled and the press says what it waits for
  (`develop_export_blocker`: the photograph opening, a version being saved, a look
  calculating, an open dialog...); Ctrl E likewise.
- Same class, also fixed: **Reveal** and **Open folder** dropped their worker, so a
  failure was lost (now reported); **Copy path** said nothing ("Copied <path>"); a failed
  folder dialog was ignored; **Export view bundle** was silently ignored while a file dialog
  was open (now says so) and its success now also heads the Export inspector.

**Offscreen states** (`main.rs`, `studio-shell.rs`, `visual-check.py`): `--overlay
develop-save-version`, `export-hdr` (the HDR preset in the editor) and `export-result` (a
sample result line; its words are a fixture). None writes anything.

**Other stations** were checked for leftover "New" tags (`tag(` and "new" labels across
`crates/strehl-ui/src`): none. The Library's "On the rig now" and the subject page's "Scale
bar ready" are status tags, not "New" (VERIFIED by search).

## The AVIF encoder's effort

History (VERIFIED, `git log -S speed` / `-S "Encoder effort"` on `crates/strehl-ui/src`):

| Commit | Control |
| --- | --- |
| `ea873c3c4` | "Encode speed" slider, 0 to 10, on `recipe.hdr.speed` |
| `a5f68a4a8` | "Speed" number field |
| `389fd54b2` (21 Oct) | Moved to `ExportSettings::speed` (default 6); the export pane's **Encoding options** showed **Encoder effort** = 10 - speed (default 4), separate from Quality, captioned "Less effort finishes faster. More effort searches longer and can improve compression or quality." |
| `d04eff50b` (P7 UI stage 1) | The Export station has no control; presets still carry `speed` (6) and the time estimate reads it. Stage 2 stopped calling the old pane, so the control was gone |

Now: an AVIF preset shows **Encoder effort** (0 fastest to 10 slowest, default 4, effort
= 10 - speed) under **Quality**, with the time it will take for this photograph. A change
is an `ExportIntent::Edit` of the preset, saved to the preset library like any preset
edit; `plan_batch` carries the setting into each file and `run_batch` hands it to the
encoder through `DevelopmentJob::export_with`.

Reaching the encoder (VERIFIED, `the_encoder_effort_reaches_the_encoder`): two AVIF presets
at effort 0 and 6 are planned with speeds 10 and 4; each batch file is byte-identical to a
direct `export_with` at its speed, and the two files differ. The drag test checks that more
effort asks for a lower speed and leaves Quality alone; JPEG shows Quality without effort.

The time estimate (MEASURED, release build of `strehl-edit`'s P7 probe, the copied weevil
master `strehl-1793781369068-68052-3`, 7032 x 4688, its own recipe, HDR Rec.2020 quality
100, host CPU load 4 % before and 2 % after, no other work of mine running):

| Effort (speed) | Time | File |
| --- | --- | --- |
| 0 (10) | 11.80 s | 61,338,534 bytes |
| 4 (6) | 39.04 s | 59,165,477 bytes |
| 8 (2) | 172.50 s | 57,631,824 bytes |

The old estimate (0.5 s/MP x (1 + 0.4 x effort)) said 16, 43 and 69 s: the curve is
geometric, not linear. `estimate_seconds` now uses 0.36 s/MP x 1.4^effort (DERIVED fit):
12, 46 and 175 s, within 20 % of each measurement (VERIFIED by
`the_time_estimate_follows_the_measured_effort_curve`). Effort 10 (about 5.6 min) is an
extrapolation (UNVERIFIED).

**Found, not changed:** the size estimate for AVIF (0.42 bytes a pixel, "13.8 MB" for this
photograph) is about four times low for HDR quality 100: the three files above are 1.75 to
1.86 bytes a pixel (MEASURED), and the history table's earlier `result-edited.avif` is
57 MB. Only quality 100 was measured, so the constant was left for a measurement across
qualities.

## Tests and checks

New tests (VERIFIED, all pass): `app-station-develop-actions-tests.rs` (Export… after an
adjustment; Save version after an adjustment, saved and listed with its result line; an
export through the shell writing the ticked preset and saying where; a blocked export
saying what it waits for, then Dismiss; a refused Develop action shown in the inspector,
then Dismiss) and `export-station-actions-tests.rs` (effort mapping; the effort row and no
"New" tag; effort reaching the encoder; the time curve; the footer answering every press).
`develop_intents_route_to_the_editor_or_the_app` now asserts the Export station, and
`export_fills_presets_footer_history_and_preview` expects **Choose a folder…** (its fixture
has no folder).

Commands, in `C:\w\g-develop`, `CARGO_BUILD_JOBS=12`, never `-q`:

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | 1478 passed, 0 failed, 36 ignored (VERIFIED, "Compiling strehl-ui", exit 0) |
| `cargo test --locked -p strehl-ui actions::` after the last edit | 10 passed (VERIFIED) |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | Clean, exit 0; re-run after touching `export-station.rs` with `-v` shows `clippy-driver` running on strehl-ui (VERIFIED) |
| `cargo fmt -p strehl-ui -- --check` | Clean (VERIFIED) |
| `cargo test --locked -p strehl-edit` | All 15 binaries pass, 186 tests, including `tests/export-freeze.rs` (2 passed) (VERIFIED, "Compiling strehl-edit", exit 0) |

`strehl-edit` is unchanged on this branch; its suite was run to confirm the export freeze.

## Screenshots

Release build, 1680 x 1050, under `C:\strehl-scratch\g-develop\shots` (VERIFIED by
looking at each):

- `visual-check.py` (opens the owner's render read-only): `develop`, `export`,
  `develop-lightbox`, `export-lightbox`, `develop-instrument`, each with `-compare.png`.
  Export shows no "New" tags and **Choose a folder…**; Develop's **Export…** is enabled.
- Against a copy of that render (`C:\strehl-scratch\g-develop\runs\…`) with a scratch
  catalog that points at the copy: `develop-save-version-{graphite,lightbox,instrument}`,
  `export-hdr-{…}` (Encoder effort under Quality, the time line wrapped, not clipped) and
  `export-result-{…}` (the result line with Open folder and Dismiss). A before/after listing
  of the copy showed no file changed by these renders.
- `export-hdr-lightbox-inspector-crop.png`: a native 348 x 450 crop of the inspector.

Every new part is square and ruled (hairlines, tracked capitals, drawn marks), in all three
themes.

## Not done

- No click-through in the windowed desktop: the presses were exercised through the shell
  with egui input and offscreen renders. The folder dialog that **Choose a folder…** opens
  is native and is not opened by any test.
- The AVIF size estimate (above).
