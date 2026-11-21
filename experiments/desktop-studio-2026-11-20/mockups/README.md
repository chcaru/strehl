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
- On **Stack**, move the pointer over the photograph: the loupe shows the Depth lens, the
  core sample updates, and the depth rail draws the detail at the pointer by plane. Click the
  lens buttons and the three inspector tabs.
- On **Develop**, the rail shows the painted area's trace and the chosen range.
- A link can select a theme and a state:
  `strehl-studio-2-mockups.html?theme=lightbox&do=lens:depth;tab:recipe;pop:jobs#stack`.
  `do` accepts `lens:photo|depth|soft|align`, `tab:NAME`, `pop:rig|jobs|palette` and
  `hover:U,V` (a position on the photograph, 0 to 1).

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
  read.
- Library thumbnails come from the desktop's explorer preview cache, read only.

**The depth map, ridge, core-sample grid, soft-spot mask and proof are illustrations.** They
are computed from the bracket's unaligned embedded camera JPEGs by local Laplacian energy,
smoothed, taking the sharpest plane per area. They show what the proposed displays would look
like. They are not engine output: the application would draw the engine's recorded evidence,
and a camera-JPEG composite cannot predict the RAW merge's detail or noise.

## Files

| Path | Purpose |
| --- | --- |
| `build.py` | Wraps each screen in the shared shell, inlines styles, script, icons, pictures and data |
| `make-assets.py` | Builds the pictures and the illustrative data into `outputs/assets` |
| `src/index.html` | Page template and the prototype bar |
| `src/base.css` | Themes, shell and shared components |
| `src/screens.css` | Per-screen layout |
| `src/app.js` | Navigation, fit-to-width scaling, the depth rail, the linked probe, small instruments |
| `src/icons.svg` | Line icons |
| `src/screens/*.html` | One partial per screen: a JSON `meta` comment, then `lede`, `body` and `notes` |
