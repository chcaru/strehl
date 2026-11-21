# P1: the shell

**Phase:** P1 of [the Studio 2 implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(sections 6.2-6.6, 7.1, 9 P1). Ledger row `desktop-studio-2-p1-2026-11-21`.
**Branch:** `studio2/p1-shell`, from `61effa01b`. **Date:** 2026-11-21.
**Evidence labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED, as in the plan.

## What was built

Every station shows today's panes inside the new frame; the station phases
replace them through the extension points below.

| Part | File | Notes |
| --- | --- | --- |
| Tokens | `studio-theme.rs` | Graphite (default), Instrument, Lightbox from appendix A; detail spectrum; canvas inks and lines for text on the surround; type scale; `tokens(ctx)` from context data; `scoped(ctx, theme, ..)` draws content in another theme and restores. |
| Legacy palette | `theme.rs` | `BG`, `PANEL`, `RAISED`, `LINE`, `INK`, `MUTED`, `ACCENT`, `GREEN`, `AMBER` keep their names and now hold the Graphite tokens (`MUTED` = `ink3`, `AMBER` = `warn`), plus `RED` (`bad`). `studio_style` builds egui's style from tokens: square corners, hairlines, popover shadow only, 24 px interact rows, Body 13 / Small 11.5 / Monospace 11.5 / Heading 15 strong. |
| Lettering | `studio-fonts.rs` | `din` = Bahnschrift (default instance), `din-strong` = Segoe UI Semibold, `din-light` = Segoe UI Light, each falling back to Segoe UI, Bahnschrift, then egui's fonts. Read once per process from `C:/Windows/Fonts`; nothing redistributed. Tracked capitals use `extra_letter_spacing`. |
| Widgets | `studio-widgets.rs` | Buttons (primary, standard, quiet, danger; 22/28/36), segmented choice (24), toggle (26 x 14, square knob), slider (rule, 2 px index, default tick), drawn status marks (circle, triangle, diamond, ring, half ring), chips, check row, key cap, lifecycle line, tabs, links (neutral; accent on a check that needs a look), section rule, progress rule, the brand mark from `assets/strehl.svg`. |
| Route | `studio-route.rs` | `Station`, `Route` (`Library`, `Subject`, `Capture`, `Stack{room}`, `Develop`, `Export`), `LaunchRoute`, `StackTab`, `Drawer`; `Navigator` with the one-way adapter to `Sidebar` / `process_view`. |
| Frame | `studio-shell.rs`, `studio-shell-bars.rs` | Top bar, hint bar, inspector, tools, control strip and rail slots, focus mode, Preferences, palette wiring, `tick`. |
| Rig status | `rig-status.rs` | Summary and lamp from `CaptureWorkspace::snapshot()` (read at most four times a second); popover rows for camera, light, power for a stack, camera host, receiver, phone remote; buttons send the existing `Power`, `PowerPlan`, `Connect` and `Disconnect` commands with the host's revisions. |
| Palette | `command-palette.rs` | Ctrl K; stations, actions with their keys, stacks, renders, projects and folders; prefix, then word prefix, then subsequence; arrows and Enter; the index is rebuilt only when the catalog key changes. |
| Activities | `activity.rs`, `activity-tray.rs` | 6.6 step 1: a read-only `ActivityStatus` per running task (stack, opening, import, export, view bundle, metadata, capture), the top-bar status with a progress rule, and the tray with Stop, the notices and the engine log. |
| Notices | `notices.rs` | A bounded list (64) of `{severity, text, source, time, action}`. Errors written to `error`, `editor.error` and `capture.error` become failure notices and resolve when cleared; finished stacks, exports and the capture client's success notices are pushed. `status` and `error` remain the snapshot's values. |
| Preferences | `studio-preferences.rs` | Theme, surround, reduced motion; inspector width and last station. Kept in `studio.json` beside the catalog. |
| Window chrome | `window-chrome.rs` | Minimise, maximise and close in the top bar's right end (3 x 42), in a foreground layer that still works over a modal and leaves the resize strips free; empty top-bar space is the move handle; the floating dock, `RAIL_WIDTH` and `dock_rect` are gone. |
| Offscreen | `main.rs`, `app-offscreen.rs`, `app.rs` | `--route library|subject|capture|stack|engine|develop|export`, `--theme graphite|instrument|lightbox`; readiness also waits for Develop's and Export's photograph. |
| Control | `scripts/strehl-control.py`, `docs/desktop-control.md` | `screenshot` forwards `--route`, `--theme`, `--edit`, `--export`, `--projects`. |
| Snapshot | `app-agent.rs` | Additive `route`, `notices`, `activities` keys. |

Station contents today: Library = the Projects pane in a left panel (300 wide, 232-440) beside
the process canvas; Capture = today's capture workspace, which still owns its body; Stack =
the process canvas with Adjust and Review as inspector tabs and the stack command in the
footer, plus the engine room (`E`, full width, also hosting the `--draft` / `--workbench`
diagnostic workbench); Develop = the Edit pane in the inspector, "Export this photograph"
in the footer; Export = the Export pane. Agent and the engine log open in the inspector
from the Strehl menu, the activity tray or Ctrl K, over any station.

### P0 items done here

- 4: the `bad` token and `theme::RED`. Drawing the capture FAULT in red is P6's.
- 5: `display_path()` (`display-path.rs`) strips `\\?\` and `\\?\UNC\` at the display and
  copy sites in `app*.rs`, `camera-metadata.rs` and four one-line sites in
  `project-explorer.rs`. Not changed (other phases' files): `jobs.rs` (11 sites),
  `capture-workspace.rs` (3), `capture-follow.rs` (3), `explorer-previews.rs` (4),
  `app-export.rs` (3), `workspace-history.rs` (2), `session-*.rs`, `source-preview.rs`.
- 6: the camera metadata window no longer forces `Visuals::light()`; its frame, title, error,
  plots and grid use the app's palette.
- 12: the README's "Photograph focus" and "Stack repair · next run" now read "Give
  photograph more room" and "Source repair"; `controls.rs`'s stale "CPU stacking · GPU
  display" names the GPU fold.

## Extension points for the station phases

All on `StrehlApp`, in `studio-shell.rs` (module `app::studio_shell`):

```rust
pub(super) fn station_layout(&self, station: Station) -> StationLayout;
//  StationLayout { sidebar: Option<f32>, tools: bool, inspector: bool,
//                  control_strip: bool, rail: Option<f32>, owns_body: bool }
pub(super) fn station_paints_legacy(&self, station: Station) -> bool;
pub(super) fn station_sidebar(&mut self, ui: &mut egui::Ui, station: Station);        // "library-nav"
pub(super) fn station_tools(&mut self, ui: &mut egui::Ui, station: Station);          // "studio-tools", 44 wide
pub(super) fn station_control_strip(&mut self, ui: &mut egui::Ui, station: Station);  // 36 high
pub(super) fn station_rail(&mut self, ui: &mut egui::Ui, station: Station);           // height from the layout
pub(super) fn station_canvas(&mut self, ui: &mut egui::Ui, station: Station);
pub(super) fn station_inspector_body(&mut self, ui: &mut egui::Ui, station: Station);
pub(super) fn station_inspector_footer(&mut self, ui: &mut egui::Ui, station: Station); // 53 high
```

Panel ids and sizes: `studio-top` 44, `studio-hints` 24, `studio-inspector` 348 (300-440,
persisted), `studio-control-strip` 36, `studio-rail`, `studio-tools` 44, `library-nav`.
Constants `TOP_BAR`, `HINT_BAR`, `CONTROL_STRIP`, `INSPECTOR_TABS`, `INSPECTOR_FOOTER`,
`TOOLS_WIDTH`, `RAIL_HEAD`. Navigation: `navigate(Route)`, `go_station(Station)`,
`set_room(Room)`, `open_drawer(Drawer)`, `apply_launch_route(LaunchRoute)`;
`shell.navigator.station()`, `.route()`, `.stack_tab`, `.drawer`, `.revision()`.

To migrate a station: draw it with `studio_theme::tokens(ctx)` and `studio_widgets`, return
`false` from `station_paints_legacy` for it, change its `station_layout` arm (for example the
Stack rail: `rail: Some(head + chart + filmstrip)`), and fill the functions above from a
station module (`stack-station.rs` and so on, declared in `app.rs`). Side effects belong in
`tick`, not in paint. New notices: `self.shell.notices.push(severity, source, text, action)`.
New activities: extend `activities()` until P5's per-job structs.

## Commands and results

All on this machine, shared with four other agents; `CARGO_BUILD_JOBS=8`.

| Check | Result |
| --- | --- |
| Baseline `cargo test --locked -p strehl-ui` at `61effa01b` | MEASURED: 1061 passed, 0 failed, 16 ignored |
| `cargo test --locked -p strehl-ui` (final) | MEASURED: 1120 passed, 0 failed, 17 ignored ("Compiling strehl-ui" seen) |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: fails only on the known `unnecessary_cast` at `capture-workspace.rs:1772` (P0 item 13, another phase). With that line fixed locally and restored afterwards, clippy passes ("Checking strehl-ui", no warnings) |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: clean |
| `cargo build --locked --release -p strehl-ui` | MEASURED: succeeds |

New tests (VERIFIED by running them): tokens against appendix A and contrast floors; style
and scoped theme; font family wiring with and without the system faces; every widget's
geometry, click behaviour and drawn marks (no glyphs); route adapter, adoption of legacy
writes and launch routes; notices bounding, legacy observation and dismissal; rig summary,
lamp, command encoding (`{"op":"power","device":"light","on":false}` and so on) and the
popover's buttons; palette ranking, cached index, keys and scrim; window buttons, resize
edges and drag space; and the shell itself: chrome rectangles on five routes at 1680 x 1050,
stations navigating to every pane, plan 10.1 check 7 (tray and rig popover exclude each
other), Ctrl K / F / E / Escape, focus-mode fade without relayout, state marks that never
move the labels, failures in the top bar until read, `tick` owning the side effects, and an
open palette that builds its index once and rebuilds nothing on pointer motion.

Existing tests that asserted the retired rail, dock or status bar now drive the same
actions through the frame (`app-v25-start-tests.rs`, `app-workspace-review-tests.rs`,
`app-v20-*.rs`, `window-chrome-tests.rs`, `bracket-browser-tests.rs`,
`camera-metadata-tests.rs`); none was deleted.

### Chrome rectangles

MEASURED by `every_route_matches_the_reference_chrome_rectangles` against `metrics.json`:
top bar 0, 0, 1680, 44; hint bar 0, 1026, 1680, 24; inspector 1332, 44, 348, 982 on Stack,
Develop and Export; control strip 0, 44, 1332, 36; all within the ±2 px tolerance. The rail
head (30) has no content until P3 builds the depth rail.

### Offscreen renders reviewed

Release build, `--offscreen-screenshot --catalog <copy of projects.json> --open-run
strehl-1793781369068-68052-3 --size 1680x1050`, each PNG looked at in full:
`--route stack`, `engine`, `library`, `develop`, `export`, `capture` (with an empty
`--capture-settings` path, so nothing contacted the Pi), `--theme instrument` and
`lightbox`; and, with a temporary uncommitted hook, the palette, rig popover, activity tray
(with a long failure notice), Preferences, the Agent drawer and focus mode. Fixed after
review: the tray's long notices ran under their Dismiss and Log controls; Preferences
stretched across the window; the control strip repeated the stack's name instead of
"Render 2 · saved"; `\\?\` showed under the Library pane.

On Lightbox the top bar, hint bar and popovers are paper and the stations' current panes
are drawn in the Graphite scope (MEASURED: top bar mean 237, inspector mean 44). This is
deliberate until each station paints from tokens.

### Performance

MEASURED on the P1 branch, release, `cargo test --locked --release -p strehl-ui -- --ignored
benchmark_finished_workspace_pointer_sweeps benchmark_shell_chrome_with_a_large_catalog
--nocapture`, CPU load 45 % at start (four other agents building), against P0's baseline at
`61effa01b` (load 1 %):

| Measurement | Baseline | P1 |
| --- | --- | --- |
| Process view CPU paint + tessellation, ms per frame (6 sweeps) | 1.28-1.32, min 1.282 | 1.26-1.34, min 1.262 |
| Source view, ms per frame | 0.450-0.476, min 0.450 | 0.459-0.475, min 0.459 |
| Final vertices (process, source) | 223,300, 112,006 | 223,300, 112,006 |
| Studio chrome alone: top bar, hint bar, inspector, palette closed, pointer sweeping the top bar, 440 catalog nodes | n/a | 0.036-0.038 |

The process benchmark paints `ProcessSpace` directly, so it shows that P1 left the process
paint path unchanged (identical vertex counts, times within noise); the chrome benchmark is
new. ARGUED: the shell adds no per-frame work proportional to the catalog: the breadcrumb is
cached on the catalog revision, the palette's index and matches are cached and pointer
motion rebuilds neither (tested), the rig summary is read at most four times a second, and
the activity list allocates nothing when idle. The resident scrub benchmark and live frame
times were not rerun: P1 does not touch `SourceBrowser`, the photograph viewer or the scrub
path.

## Deviations from the plan

- Constants, not functions: `theme.rs`'s colours stay `const` holding the Graphite values. Turning
  them into functions or a type that reads the theme would change hundreds of call sites in other
  phases' files (`painter.text` and many helpers take `Color32` by value). New code reads
  `studio_theme::tokens(ctx)`; legacy views are drawn in the Graphite scope on Lightbox so their
  light ink stays legible.
- Preferences live in `studio.json` beside the catalog, not in a `ui` section of the catalog's
  `layout`: adding a field to `WorkspaceLayout` breaks struct literals in P4's tests, and the
  catalog's format is being migrated (6.7). Offscreen and headless runs never write it.
- `Route`'s `stack` and `render` are `Option`s: a bracket can be open before it is a saved stack,
  and a photograph can be opened on its own.
- egui's Button text style stays 11 px: the Develop pane aligns its painted 11 px labels with
  the value fields that use it, and its tests check that alignment. Every text style is at
  least 10.5 px; Studio widgets size their own labels (12-13.5).
- Opening a stack or render from the Library tree stays in the Library (its canvas shows the
  stack); the palette and the breadcrumb go to the Stack station. Existing workflow tests
  depend on the tree staying visible.
- `--plane-hold N` is not added: there is no plane hold before P3.
- Notices observe the legacy `status`/`error` strings rather than replacing their ~70
  assignment sites.
- Not in P1: Quiet mode in Preferences and 6.6 step 2 (owned engine jobs; P6 has merged its own),
  station-scoped undo (the hint bar names the next undo globally), the tools strip's tools,
  the rail.

## Left for later phases

- P3 fills the rail slot and the Stack station; P4 the Library and subjects (the palette's
  index can add subjects when catalog format 2 lands); P5 activities and the queue (replace
  `activities()`); P6 the Capture station (stop owning the body); P7 Develop and Export
  (tools strip, footer actions).
- ~~Remaining `display_path` sites~~: done in the polish pass (below).
- Merge note: `main.rs`, `app-agent.rs` and `project-explorer.rs` also changed on the
  integration branch (P4, P7); the P1 hunks are small and not on the same lines as of
  `97120a109`.

## Stage 2 and the polish pass

- The Library route is P4's station (`app-station-library.rs`); today's project tree is the
  Project tree drawer (brand menu, palette, `--overlay projects`).
- Drawers open over a station and no longer rewrite its legacy flags, so Develop keeps
  editing under the tree; code that shows project-tree features reads `projects_visible()`.
  They are painted through `theme::follow_theme`, which recolours the Graphite token colours
  their legacy code uses into the theme in effect (Lightbox, Instrument). Stations that still
  paint legacy are drawn in the Graphite scope as before.
- Breadcrumbs follow the mockups: Library / subject / stack / render, then the version (Develop,
  Export, while the recipe is the saved or restored one) or Engine room; Capture shows the
  plan's subject and stack, then New stack or Capturing. In a narrow window the middle
  segments fold into one ellipsis.
- The top bar's right end has a fixed budget between the stations and the window buttons;
  see `fit_right_cluster` for the order in which its parts give way. The activity reads
  "Capturing 61 / 96 · 3:18 left" (no repeated kind); the rig says the light during a capture.
- Glance hides the window buttons until the pointer reaches the corner.
- `--overlay projects|activity|agent|palette|preferences`; `visual-check.py --size`.
