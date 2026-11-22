# g-develop: Develop and Export actions after the owner's run-through

**Status:** results note. Branch `studio2/g-develop`, based on `7f83d3f22`; the fix,
tests and docs are `b70cae4b9`, which every check below was run on. The screenshots come
from a release build one edit earlier: the effort field's drag rate (`speed(0.05)`, 20 px
a step), which does not change what is drawn.
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
geometric, not linear. `b70cae4b9` fitted 0.36 s/MP x 1.4^effort to these three points;
that fit ignored quality and was replaced by the model in the follow-up below.

## The AVIF size estimate (follow-up)

The Export station estimated every AVIF at 0.42 bytes a pixel ("13.8 MB" for the HDR preset
on this photograph); the HDR quality 100 files above are 1.75 to 1.86 bytes a pixel, and
the history table's earlier `result-edited.avif` is 57 MB. 0.42 is what HDR quality 85
measures below, so the constant ignored quality and range.

Measurements (MEASURED): the same probe, binary and inputs as the time table (P7 probe
built from this branch's unchanged `strehl-edit`, release, temporarily copied into
`crates/strehl-edit/examples` and removed again; the copied weevil master, 7032 x 4688 =
32,966,016 pixels, its own recipe). SDR is sRGB, HDR is Rec.2020 PQ. Script
`C:\strehl-scratch\g-develop\size-quality.ps1`, run as
`pwsh -NoProfile -File size-quality.ps1 [-speed S -qualities Q]`, which calls
`p7-export-freeze.exe export <master> <recipe> '{"format":"avif","color_space":…,"hdr":…,"quality":Q,"speed":S}' <out>`
and deletes each file after reading its size. Host CPU load 0 to 3 % before each run,
up to 14 % after; nothing else of mine ran.

| Quality | SDR bytes | SDR B/px | SDR time | HDR bytes | HDR B/px | HDR time |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | 1,962,728 | 0.0595 | 12.75 s | 1,704,501 | 0.0517 | 14.28 s |
| 70 | 3,769,846 | 0.1144 | 15.23 s | 5,812,210 | 0.1763 | 19.44 s |
| 85 | 6,656,658 | 0.2019 | 17.36 s | 13,876,666 | 0.4209 | 22.05 s |
| 90 | 9,236,099 | 0.2802 | 19.66 s | 20,899,095 | 0.6340 | 23.80 s |
| 95 | 15,871,122 | 0.4814 | 22.59 s | 33,442,454 | 1.0145 | 32.22 s |
| 100 | 36,276,821 | 1.1004 | 35.49 s | 59,165,477 | 1.7947 | 33.43 s |

All at effort 4 (speed 6). Effort spot-checks at quality 85: SDR 7,799,088 bytes at effort
0 (+17 %) and 6,285,604 at effort 8 (-6 %); HDR 15,062,561 (+9 %) and 13,328,217 (-4 %). At
HDR quality 100 (the time table): +4 % and -3 %. Effort changes size much less than
quality does, and lower effort makes larger files.

Model (DERIVED): `avif_bytes_per_pixel(quality, hdr)` interpolates the table on straight
lines in log size (size grows geometrically as rav1e's quantizer falls), with the first
segment's slope below quality 50; effort is left out. Quality 95 was measured after the
model was first written with the other five points, as a held-out check: it predicted
0.555 (SDR) and 1.067 (HDR) bytes a pixel against 0.481 and 1.015 measured (+15 % and
+5 %), and was then added to the table. The HDR preset now reads "59.2 MB". VERIFIED by
`the_avif_size_estimate_follows_quality_and_range` (each measured point within 1 %, the
HDR preset's label, size rising with quality from 1 to 100); with the old constant its
label assertion reads 13.8 MB and fails (ARGUED).

## The AVIF time estimate's quality (second follow-up)

Encode time also depends on quality: at effort 4, SDR quality 50 took 12.75 s and quality
100 took 35.49 s (the table above). The single quality-100 curve therefore said 46 s for
SDR quality 50. The estimate is now `avif_seconds_per_mp(quality, hdr, effort)` (DERIVED):

- **Quality and range:** the table's effort 4 times per megapixel (32.966 MP), interpolated
  in log time between qualities, the first segment's slope below 50. HDR quality 100 uses
  the mean of its two runs (39.04 s in the time table, 33.43 s in the size run: the
  run-to-run spread of one setting is about 15 %).
- **Effort:** a factor relative to effort 4, interpolated in log time through effort 0, 4
  and 8 and continued past 8 with the last slope. Effort 0 is 0.3455 and effort 8 is 4.851,
  the geometric means of the ratios measured at SDR quality 85 (0.320, 5.589), HDR quality
  85 (0.427, 4.622) and HDR quality 100 (0.302, 4.419). Effort changes time far more than
  quality does; the ratios differ by setting, so one factor is accurate to about 20 %.

Held out (MEASURED after the model's constants were fixed; same probe and script, a
fresh copy of only the master and recipe, deleted afterwards; host CPU load 0 to 11 %):

| Setting | Predicted | Measured |
| --- | --- | --- |
| SDR quality 50, effort 0 | 4.4 s | 4.65 s (-5 %) |
| SDR quality 50, effort 8 | 61.9 s | 74.25 s (-17 %) |
| HDR quality 70, effort 6 | 42.8 s | 47.88 s (-11 %) |

Every measured setting (19 fitted and 3 held out) is within 20 % of the estimate, largest
-19 % (HDR quality 85, effort 0) (VERIFIED by
`the_time_estimate_follows_quality_range_and_effort`, which also checks that time rises
with quality and with effort). Effort 9 and 10 are extrapolated (UNVERIFIED; about 6.5 min
for this photograph at HDR quality 100, effort 10). Neither model covers resized output
beyond scaling by its pixel count, or other photographs (one master measured).

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
| `cargo test --locked -p strehl-ui` | 1478 passed, 0 failed, 36 ignored at `b70cae4b9`; 1479 passed, 0 failed, 36 ignored with the size and time models (VERIFIED, "Compiling strehl-ui", exit 0) |
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
  of the copy showed no file changed by these renders. The copy was deleted after the size
  measurements.
- `export-hdr-lightbox-inspector-crop.png`: a native 348 x 450 crop of the inspector.

Every new part is square and ruled (hairlines, tracked capitals, drawn marks), in all three
themes. The screenshots predate the size and time models: their HDR preset line still reads
13.8 MB and its time "about 46 s" (now 59.2 MB and about 36 s).

## Not done

- No click-through in the windowed desktop: the presses were exercised through the shell
  with egui input and offscreen renders. The folder dialog that **Choose a folder…** opens
  is native and is not opened by any test.
- The size and time models rest on one photograph; another subject or a resized preset
  will differ.
