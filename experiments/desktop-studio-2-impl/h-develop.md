# h-develop: the split line, the words an export writes, and the Strehl stamp

**Status:** results note for the owner-feedback round of 2026-11-22. Branch
`studio2/h-develop`, based on `d359bbe28`. **Date:** 2026-11-22. **Evidence labels** as in
`AGENTS.md`.

The owner's words (verbatim):

> on the Develop screen: "for the before/after split mode, i would like to be able to drag that line."
>
> general: "where is the copyright and description configured? i see the option in export to use it, but no idea what they'll be?" and "is there a way to stamp the image as being generated with Strehl? this wouldn't be configurable. every image would get it."

Signed provenance (C2PA) is not part of this lane.

## 1. The split line

### Why it could not be dragged

`develop-station.rs` gave the line a 12 x 40 pt grip at the vertical middle of the visible
photograph and drew nothing there: anywhere else along the line a press panned the
photograph. The split was a fraction of the **whole** photograph's width, so zooming in moved
the line with the photograph, usually off screen (VERIFIED: the new tests below, run against
the base with a test-only shim giving the base's line position, fail as expected: a press near
the top of the line leaves it where it was, "the line is at 688, the pointer left it at 367";
at 4x the line moves; only the control, panning away from the line, passes. Output kept in
`C:\strehl-scratch\h-develop\base-split-tests.txt`).

### What changed

- **Anywhere along the line.** The hit area is the line's full visible height, 6 pt either
  side of it (12 pt wide against the 1 pt line). The cursor is the horizontal resize arrow over
  it and while dragging. A press keeps its offset from the line, so the line does not jump to
  the pointer.
- **A grip you can see.** A square-cornered 9 x 30 pt tab with two ticks at the line's middle,
  dark fill and a hairline; line and tab turn the theme's accent while hovered or dragged.
  Square and ruled, no rounding (owner's taste).
- **On top of the tools.** The line takes the pointer after the tools' canvas, so it can be
  dragged with the crop, brush, heal or note tool out; while it is dragged the photograph does
  not pan (`owns_pointer`). Its shapes still paint under the crop frame and the tools (a
  reserved painter slot, filled once this frame's position is known, so there is no one-frame
  lag).
- **Clamped.** The line stays at least 8 pt inside either edge of the visible photograph, so
  it can always be taken again.
- **Keeps its place.** `split` is now a fraction of the **visible** photograph (the part on
  screen). In Studio 2's Develop the visible box is the fitted photograph, so zooming and
  panning move the picture under a line that stays put on screen (VERIFIED,
  `the_line_keeps_its_place_while_the_view_zooms_and_pans`). Re-renders do not touch it.

**Remembered per session, not saved (decision).** The position lives in `DevelopCanvas`, which
already keeps view choices across photographs (`reset_document` leaves it). It is a way of
looking, not part of the picture or its edit, so it does not belong in the recipe, and saving
it to `studio.json` would reopen Split with the line wherever it was last left, possibly at an
edge where Before is all but hidden. A new session starts in the middle. Compare (After,
Before, Split) itself was already per session; the line now matches it.

**Offscreen.** The screenshot path cannot drag, so `--develop-split F` opens Develop in Split
with the line at F (0 to 1). Offscreen readiness now waits for the "before" overview when
Split is shown, so a screenshot never catches "Before · developing".

### Smoothness (MEASURED)

`benchmark_develop_latency_on_a_real_master` (release, `STREHL_UI_BENCH_RUN` = a scratch copy of
the weevil render, 7032 x 4688; UI thread per frame: egui, the overlay, tessellation; no GPU in
this harness). **Before:** `git archive d359bbe28` built in `C:\strehl-scratch\h-develop\base-src`
with the same benchmark. **After:** this branch. 120 frames each; ms per frame, median / p95 /
max.

| Run | CPU load at start | Pointer sweep, fit, After | Split line drag, fit |
| --- | --- | --- | --- |
| Before | 0 % | 0.10 / 0.19 / 0.28 | 0.09 / 0.15 / 0.23 |
| After, run 1 | 1 % | 0.11 / 0.18 / 0.22 | 0.11 / 0.17 / 0.24 |
| After, run 2 | 21 % (another lane's build) | 0.10 / 0.20 / 0.51 | 0.13 / 0.21 / 0.28 |

The new benchmark section at 4x (full-resolution tiles on screen; after only, because the base's
line is off screen there), run 2: pointer sweep 0.13 / 0.20 / 1.62, split line drag 0.14 / 0.20 /
0.27. In every run the drag moved the line from 0.10 to 0.90, the photograph's revision did not
change and the viewport's job count stayed 44: dragging develops nothing and starts no tile.
The grip adds a few shapes; the drag costs about 0.01 to 0.03 ms a frame more than a plain sweep
(DERIVED from the table; within run-to-run spread). Run 1's first 4x pass did not move the line
because the benchmark pressed in the very frame Split was switched on, before the line had ever
been drawn; the benchmark now draws one frame first, as a person sees the line before taking it.

### Not done: the Before half when zoomed

Still the 1600 px SDR overview, soft at 100 % and above (`g-zoom.md` lists it;
`develop-split-30-400.png` shows it plainly at 400 %). A real fix is a second set of tiles, or
one detail patch of the visible region, developed with the before recipe on a worker after the
view settles, and painted under the Before half. That is a new worker competing with the tiles
and more GPU memory while Split is zoomed, not a cheap change; it is left open.

## 2. Copyright and description

### Why the text was always empty

`start_export_batch` (`app-develop.rs`) planned every batch with `BatchText::default()`: the
switch wrote nothing because there was nothing to write, and no screen held the text (VERIFIED
by reading; the new shell test fails at the first assertion without the change: nothing
shows "Chris Caruso").

### What changed

- **The owner's standing text** (artist, copyright) is in `studio.json`
  (`StudioPrefs::artist`, `copyright`; omitted when empty, so earlier files read and are written
  as before). Read and saved cleaned: trimmed, no control characters, within `strehl-edit`'s
  limits (256 and 512 bytes, cut at a character boundary). It is edited in **two** places:
  - the Strehl menu, **Preferences…**, a new **Exports** section (Artist, Copyright, and a line
    saying when they are written, that an empty field writes nothing, and that every export
    names Strehl);
  - Export itself (next point).
- **Export shows exactly what the switch writes.** Under **Copyright and description** in **In
  every file**: ruled lines **Artist**, **Copyright**, **Description**, each editable in place
  (a frameless field on a hairline that turns accent while typing), then **Software · Strehl ·
  every file, always**. With the switch off the values dim and the caption says none is written.
  An empty field shows "Not set · …" dimmed. Text is committed when the field loses the
  keyboard; the field shows the current text whenever it is not being typed in, so another
  photograph's description never lingers.
- **The description belongs to the picture (decision).** It is kept per photograph in the
  catalog (`Catalog::photo_descriptions`, keyed like `export_directories` by the photograph,
  omitted from the file when empty). It leaves with its render when a stack or subject is
  removed and comes back on undo (`catalog-removal.rs`). Why not the alternatives: a subject's
  notes are working notes (lighting, retakes) and would leak into published files; a version's
  name is a name; a per-export field typed every time is forgotten every time. Validated as
  `strehl-edit` validates it (2,048 bytes, no control characters but newlines, none of the
  wording Strehl reserves for its masters); a refusal heads the inspector in words.
- **Presets still never carry text.** The switch flips the two flags it always flipped
  (`copyright`, `description`); `ImagePreset::validate` still refuses text in a preset (VERIFIED,
  the presets file after a words export holds `"copyright": true` and neither the name nor the
  description).
- **Export again** reuses the switches the file was written with (text present then means the
  switch on now) with today's text; it used to drop the words.
- **The agent and MCP export paths** are unchanged: no personal text (the agent asks for a file,
  not the owner's name); they gain the stamp from `strehl-edit` (part 3).

## 3. Every export names Strehl

### What was missing

`strehl-edit` wrote `xmp:CreatorTool` "Strehl" and Exif Software (305) "Strehl" only when an
export carried text or a date (`xmp_packet` and `exif_block` returned `None` otherwise). The
desktop batch always passes a date, so its PNG, JPEG and AVIF files were stamped; the agent/MCP
path (`EditorState::export_with_settings`, no date) and the CLI's `strehl develop` wrote PNG,
JPEG and AVIF with no stamp at all (VERIFIED: none of the 67 PNG, JPEG and AVIF files of the
base's freeze set, dumped from the base build, names Strehl as software; 12 of its Display P3
and Rec.2020 JPEGs contain the word, inside the embedded ICC profile's description, for example
"Strehl Display P3 (D65, sRGB transfer)", which viewers do not report as the program). TIFF exports always carried Software "Strehl development v1".

### What every format now carries, whatever the switches say

| Output | Stamp | With text or a date |
| --- | --- | --- |
| TIFF export (Print, any TIFF preset, agent, CLI) | Software (305) "Strehl development v1", as before | plus Artist, Copyright, DateTime and an XMP packet (700) with `xmp:CreatorTool` |
| PNG | `tEXt` Software "Strehl" and an XMP `iTXt` with `xmp:CreatorTool` "Strehl", before the image data | dc:creator, dc:rights, dc:description, dates in the same XMP |
| JPEG | Exif APP1 with Software "Strehl", and an XMP APP1 with `xmp:CreatorTool` | Artist, Copyright, ImageDescription, DateTime in Exif; the same in XMP |
| AVIF (SDR and HDR) | Exif item with Software "Strehl" (avif-serialize has no XMP item) | Artist, Copyright, ImageDescription, DateTime in the Exif item |
| Archive preset (master copy) | the master's own Software, "Strehl scene-linear master v1", byte for byte | (a copy: nothing is added) |

The renders' own TIFFs are untouched: `image_out.rs`'s Software tag with the build commit
(`strehl <version> (<commit>)`), the measurement renders' `strehl <version>`, and the
scene-linear master's tag.

**No version in the stamp (decision).** `CREATOR_TOOL` is "Strehl", the same text the
metadata-bearing exports already wrote. The owner asked that a picture say it was made with
Strehl; that needs the name. A release or commit in every export would make an export's bytes
depend on the build that wrote it: re-exporting an unchanged edit after an update would give a
different file (the Export history's "unchanged" check and "Export again" compare bytes), and
the export byte freeze would move with every release, which is the failure `image_out.rs`
documents for render TIFFs (a hash that became "a function of which tree the test ran in").
Which build wrote a file is provenance, the question the separate C2PA answer addresses; the
master TIFF keeps its commit for that reason.

### How it is verified

- **Read back, container by container** (VERIFIED, `crates/strehl-edit/tests/export-stamp.rs`
  with a reader in `tests/common/mod.rs` that walks PNG chunks, JPEG segments, TIFF IFDs and the
  AVIF's ISOBMFF boxes through `iloc`, sharing no code with the writer): TIFF, TIFF with the
  recipe, PNG, JPEG, AVIF SDR, AVIF HDR, and the staged path (resize and sharpening) for JPEG and
  PNG: each names Strehl in exactly the containers above without text or date; beside the text
  and the date; and an empty artist or description writes nothing while the copyright is
  written. The scene-linear master reads "Strehl scene-linear master v1". Negative control:
  a PNG with its two stamp chunks removed reads as unstamped.
- **The stamp is purely additive** (VERIFIED, `tests/export-freeze.rs`): every option-free
  export still hashes to the bytes recorded at `61effa01b` once the stamp is taken out: the two
  PNG chunks, the two JPEG APP1 segments, and for AVIF the file is rebuilt with `avif-serialize`
  from its own AV1 payload, colour properties and light level without the Exif item. All 86
  fixtures match, so pixels, codecs and containers are otherwise unchanged. Negative control:
  with the stamp text changed to "Strehx", the freeze and two stamp tests fail.
- **Every path:** the desktop batch (Web JPEG, Print TIFF, Archive copy), the shell's export with
  and without the switch, and the agent's TIFF, PNG and JPEG exports (which also must not carry
  the owner's name) are checked in `strehl-ui` tests (below). The CLI's `strehl develop` calls the
  same `export_image` (ARGUED; not run).

## Files

- `crates/strehl-edit/src/metadata.rs`, `export.rs`, `avif.rs`, `lib.rs`: the stamp
  (`CREATOR_TOOL`, always-built XMP and Exif, PNG `tEXt` Software); TIFF unchanged without text.
- `crates/strehl-edit/tests/export-stamp.rs`, `tests/common/mod.rs` (new), `tests/export-freeze.rs`
  (unstamping against the 61effa01b hashes), `tests/export-pipeline.rs` and
  `src/metadata-tests.rs` (the stamp is now always there).
- `crates/strehl-ui/src/develop-station.rs`: the split line.
- `crates/strehl-ui/src/studio-preferences.rs`, `studio-shell-bars.rs` (Preferences, Exports),
  `export-station.rs` (the words lines, `Words`, `WordsField`, `ExportIntent::SetWords`),
  `app-develop.rs` (batch text, keeping the words, Export again, `--overlay export-words`),
  `workspace-history.rs` and `catalog-removal.rs` (`photo_descriptions`).
- Shared files, small local edits: `app.rs` (`--develop-split` at launch; offscreen readiness
  waits for Split's before overview), `main.rs` (`--develop-split`, two overlay names).
- Tests: `app-station-develop-split-tests.rs` (new), `app-station-develop-actions-tests.rs`,
  `app-station-develop-tests.rs` (benchmark at 4x), `export-station-tests.rs`,
  `export-station-actions-tests.rs`, `agent-export-tests.rs`, `catalog-removal-tests.rs`.
- `crates/strehl-ui/README.md`; `experiments/desktop-studio-2-impl/visual-check.py` (new routes).

## Tests and checks

New tests (VERIFIED, all pass):

- Split (`app-station-develop-split-tests.rs`, through the shell with egui input): the line drags
  from near its top, 4 pt beside the hairline, without panning, and keeps the press offset; it
  stops 4 to 16 pt inside either edge; it keeps its screen place at 4x and drags there without
  panning; the session keeps it across photographs; a drag away from the line still pans (the
  control). Three of four fail on the base (above).
- Words (`app-station-develop-actions-tests.rs`): Export shows the owner's artist and copyright
  and the stamp; the switch is pressed on screen; a description typed into its line is kept in
  the catalog and read back after a reload; the exported JPEG's Exif and XMP carry the three
  texts and Software; the presets file carries no text; switched off, the next file holds only
  Software and DateTime. An empty artist writes no Artist; a description of spaces is
  forgotten; reserved wording is refused in words and not kept.
- Batch (`export-station-tests.rs`): the Web JPEG, Print TIFF and Archive copy of a real
  scene-linear master all name Strehl. Agent (`agent-export-tests.rs`): TIFF, PNG and JPEG name
  Strehl and never carry the owner's name. Removal: a photograph's description leaves with its
  stack and returns on undo. Preferences: the text round-trips, is cleaned on read, and an empty
  text is not written.

Commands in `C:\w\h-develop`, never `-q`, after the last code edit:

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-edit --no-fail-fast` | 193 passed, 0 failed, 15 binaries; "Compiling strehl-edit" seen (VERIFIED) |
| `cargo test --locked -p strehl-ui --no-fail-fast` | 1,503 passed, 0 failed, 43 ignored; "Compiling strehl-ui" seen (VERIFIED) |
| `cargo test --release --locked -p strehl-ui benchmark_develop_latency -- --ignored --nocapture` | Passes; numbers in part 1 (MEASURED) |
| `cargo clippy --locked -p strehl-edit -p strehl-ui --all-targets --no-deps -- -D warnings` | Clean, exit 0, "Checking strehl-edit" and "Checking strehl-ui" seen (VERIFIED) |
| `cargo fmt -p strehl-ui -p strehl-edit -- --check` | Clean (VERIFIED) |

## Screenshots (looked at)

Release build, 1680 x 1050, `visual-check.py --run` on a scratch copy of the weevil render
(`C:\strehl-scratch\h-develop\weevil`; the catalog copy points at it, nothing is written beside
the original). They hold the owner's pictures and stay in `C:\strehl-scratch\h-develop\shots`:

- `develop-split-25`, `-50`, `-75` (Graphite), `-25-lightbox`, `-75-lightbox`,
  `-60-instrument`: the line at each place, Before left of it, the captions at its top, the grip
  at its middle; `grip-crops.png`: native 120 x 120 crops of the grip on Graphite and Lightbox.
- `develop-split-30-400`: 400 %, the line at 30 % of the visible photograph; the soft Before half
  (open, above).
- `export-words`, `-lightbox`, `-instrument`, `export-words-off`: the words lines with sample text
  (`--overlay export-words`, in memory only), and with the switch off;
  `words-crops.png`: native crops of the section in three states.
- `preferences`, `preferences-lightbox`: Preferences with the Exports section (sample text from a
  scratch `studio.json` beside the catalog copy).

Every new part is square and ruled in all three themes.

## Open, and for the owner

- **The Before half when zoomed** stays the 1600 px overview (above).
- **One switch for both texts**, as before. If you want copyright without a description on some
  presets, leave the description empty; separate switches are a small change if you prefer them.
- **No version in the stamp.** Say if you want "Strehl 0.1.0" written; the cost is that every
  release changes every export's bytes.
- **Not tried in the windowed desktop** (offscreen and egui-input tests only), and not on the
  owner's display.
