# Strehl Studio 2 mockups

Interactive mockups for the
[desktop redesign proposal](../../../docs/proposals/2026-11-desktop-studio-2.md). They are
design intent drawn in HTML. They are not application code, and nothing here is built into
the desktop.

## Build and view

```powershell
python experiments/desktop-studio-2026-11-20/mockups/build.py
```

This writes `outputs/strehl-studio-2-mockups.html`, one self-contained file with no network
requests. Open it in a browser. Thirteen screens: Overview, Today, Library, Subject,
Capture · plan, Capture · in flight, Glance, Stack, Engine room, Develop, Export, Shell and
themes, Design system.

- Arrow keys move between screens. The buttons at the top right switch the theme (Graphite,
  Instrument, Lightbox), open the rig popover, the job tray and the command palette, hide the
  numbered notes, and switch between fit-to-width and actual size (1680 × 1050).
- On **Stack**, move the pointer over the photograph: a region is marked and its core sample
  opens beside it, and the depth rail draws that region's detail by plane as a dashed line.
  Click to pin it. Move the pointer along the rail or the filmstrip: the photograph shows
  where that plane was kept and the plane appears above the rail with the same outline. Click
  a plane to hold the two side by side; Escape returns. Try the lens buttons and the three
  inspector tabs.
- While a plane is held, moving along the rail shows other planes in the two-up; a click
  holds the new one.
- Keys on Stack: `1`–`5` choose the lens, hold `Space` for the clean photograph, `E` opens
  the engine room (and `E` there returns). On Capture · in flight, `G` opens glance mode.
- On **Develop**, the rail shows the painted area's profile and the chosen range.
- A link can select a theme and a state:
  `strehl-studio-2-mockups.html?theme=lightbox&do=peek:128;tab:recipe;pop:jobs#stack`.
  `do` accepts `lens:photo|plane|depth|soft|align`, `tab:NAME`, `pop:rig|jobs|palette`,
  `peek:PLANE`, `hold:PLANE` and `hover:U,V` (a position on the photograph, 0 to 1).
- The lettering is Bahnschrift, which ships with Windows. Elsewhere the page falls back to
  another DIN-style face or the system face.

## Check

```powershell
python experiments/desktop-studio-2026-11-20/mockups/check-interactions.py
```

Loads the built file in a headless Chrome or Edge, dispatches pointer and key events (hover the
photograph, hover and click the rail, hold, scrub, Escape, lens keys, popovers on another
screen) and prints PASS or FAIL per check. It needs the pictures and data: with placeholders
the probe has nothing to read. It does not judge appearance.

## Pictures and data

The pictures are the owner's captures and are not committed. `outputs/` is ignored by Git.
Without `outputs/assets` the build still works and draws coloured placeholders; the linked
probe then shows no data.

```powershell
python experiments/desktop-studio-2026-11-20/mockups/make-assets.py SHOTS_DIR BRACKET_DIR
```

- `SHOTS_DIR` holds offscreen renders of the installed desktop: `hero-edit.png`,
  `hero-zoom-a.png`, `hero-zoom-b.png` at 3600 × 2250 (`--edit`, with `--photo-zoom` and
  `--photo-center` for the two details), and for the Today page `run-default.png`,
  `capture.png`, `run-edit.png`, `source-metadata.png` at 1680 × 1050.
- `BRACKET_DIR` is one source bracket of Sony ARW files. Only the embedded camera JPEGs are
  read: 33 evenly spaced planes become the filmstrip and the plane previews.
- Renders that `SHOTS_DIR` does not hold are skipped, so the data can be rebuilt on its own.
- Library thumbnails come from the desktop's explorer preview cache, read only.

**The depth map, per-plane bars, plane regions, core-sample grid, soft-spot mask and proof are
illustrations.** They are computed from the bracket's unaligned embedded camera JPEGs by local
Laplacian energy, smoothed, taking the sharpest plane per area. They show what the proposed displays would look
like. They are not engine output: the application would draw the engine's recorded evidence,
and a camera-JPEG composite cannot predict the RAW merge's detail or noise.

## Files

| Path | Purpose |
| --- | --- |
| `build.py` | Wraps each screen in the shared shell, inlines styles, script, icons, pictures and data |
| `make-assets.py` | Builds the pictures and the illustrative data into `outputs/assets` |
| `check-interactions.py`, `src/check.html` | Drive the built mockup with synthetic events and report PASS or FAIL |
| `src/index.html` | Page template and the prototype bar |
| `src/base.css` | Themes, shell and shared components |
| `src/screens.css` | Per-screen layout |
| `src/app.js` | Navigation, fit-to-width scaling, the depth rail and filmstrip, the plane lens, the core sample, small instruments |
| `src/icons.svg` | Line icons |
| `src/screens/*.html` | One partial per screen: a JSON `meta` comment, then `lede`, `body` and `notes` |
