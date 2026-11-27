# Capture calibration mockups

Six screen states for the
[capture calibration specification](../../../docs/proposals/2026-11-capture-calibration-spec.md).
They are design intent drawn in HTML, in the visual language of the
[Strehl Studio 2 mockups](../../desktop-studio-2026-11-20/mockups/README.md). They are not
application code, and nothing here is built into the desktop.

They replace the five states drawn for the first proposal on 2026-11-26 (range, measuring,
measured, something changed, the automatic run), which described a design the
specification has since replaced.

## Build and view

```powershell
python experiments/capture-planning-flow-2026-11-26/mockups/build.py
```

This writes `outputs/capture-planning-flow-mockups.html`, one self-contained file with no
network requests. Open it in a browser. Arrow keys move between the screens; the buttons at
the top right switch the theme and hide the numbered notes.

| Screen | State |
| --- | --- |
| 1 · Ready | Camera connected, light on, subject framed. One button; Depth and Exposure say "not measured". |
| 2 · Calibrating | The pass is half-way through its RAW survey. The Depth lens from the 36 s live sweep is already on the stage; the readout fills a row at a time. |
| 3 · Review: depth | The plan is filled. The Depth lens from RAW, a pinned core sample, the rail counting tiles in focus, a step held by hand. |
| 4 · In focus here | The Depth lens keeping its colour only where the subject is in focus at the lens position. |
| 5 · Cover | Start dragged later than the calibration put it: the Cover lens shows what that leaves out. |
| 6 · Review: light | The Glints lens, the one treatment table, the proof plane's verdict. |

## Reference renders

```powershell
python experiments/capture-planning-flow-2026-11-26/mockups/render.py
```

Writes `outputs/reference/<screen>.png`: the application stage alone at 1680 × 1050. It
needs Edge or Chrome.

## What is real and what is not

- **The lenses and the rail are drawn from measurements.** `assets.py` builds the stage
  pictures and `rail.json` from the grounding experiment's scratch
  (`C:/strehl-scratch/plan-flow/dragonfly`, see
  [its results](../grounding/results.md)): the depth map of the 36 s live sweep of
  2026-11-27, the per-tile focus read from RAW, the highlights from the stack's 1/40 s
  frames, the tiles in focus at each position, and the core sample's three crops and
  curve. They are the owner's dragonfly: `outputs/` is ignored by Git, and without the
  pictures the build draws placeholders and the rail falls back to a formula.
- **The numbers in the column follow from those measurements** by the specification's
  rules (in focus 32,355 to 33,161, a sharp depth of 45, the body full at 1.6 s, the
  highlights 6 stops over it) and from measured timings (7.5 s a plane, 7.7 s a highlight
  group, 31.5 MB a stored RAW). The proof's "3 of 5" and the clock times are examples.
- The picture under the lenses is the finished stack of 2026-11-26 lifted, standing in
  for live view.
- The stage is fixed at 1680 × 1050.

## Files

| Path | Purpose |
| --- | --- |
| `build.py` | Borrows the Studio 2 mockups' shell, styles, script and icons unchanged and adds this folder's screens, pictures and measured rail data |
| `assets.py` | Draws the pictures and `rail.json` into `outputs/assets` from the grounding scratch |
| `render.py` | Reference images of the six states |
| `src/flow.css` | What this design adds: folded steps, the readout, the treatment table, the Run row, the lens switch and legend, the core sample, the lamp |
| `src/flow.js` | The depth rail (measured bars, the survey's grid, marks, the highlight line) and the core sample's curve |
| `src/screens/*.html` | One partial per state: a JSON `meta` comment, then `lede`, `body` and `notes` |
