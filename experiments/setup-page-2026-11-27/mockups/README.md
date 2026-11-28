# Setup page mockups

Eight screen states for the
[Setup page specification](../../../docs/proposals/2026-11-setup-page-spec.md). They are
design intent drawn in HTML, in the visual language of the
[Strehl Studio 2 mockups](../../desktop-studio-2026-11-20/mockups/README.md). They are not
application code, and nothing here is built into the desktop.

## Build and view

```powershell
python experiments/setup-page-2026-11-27/mockups/build.py
```

This writes `outputs/setup-page-mockups.html`, one self-contained file with no network
requests. Open it in a browser. Arrow keys move between the screens; the buttons at the top
right switch the theme and hide the numbered notes.

| Screen | State |
| --- | --- |
| 1 · A new camera | A folder from a Canon EOS R5, no rig. The Dark sitting's shot list set large, a place to drop the folder, the noise said to be guessed. |
| 2 · Not dark | The Dark sitting stopped by its first check, with the levels measured on the rig when the light was on. |
| 3 · Dark | The Read noise plate: that night's unlit, uncapped bursts against the lens-capped series of 14 November and the engine's model. A new measurement waiting beside the shipped one. |
| 4 · Bright: noise | The Noise plate from the out-of-focus subject: every measured bin, the fitted model, the clip, and variance over signal with the fit's range. |
| 5 · Bright: levels | The Levels plate (exposure ratio against level, the clip, the files' declared white) and the Camera sheet in the inspector. |
| 6 · Scale | The calibration slide with a band along a row of dots, a tick on every dot counted, and the length typed by the person. |
| 7 · Motion | The Return plate: where the lens landed for each way of arriving, with the instrument's own precision as a band. |
| 8 · The setup | No sitting open: the four parts on one sheet, and the one thing most worth doing next. |

## Reference renders

```powershell
python experiments/setup-page-2026-11-27/mockups/render.py
```

Writes `outputs/reference/<screen>.png`: the application stage alone at 1680 × 1050. It
needs Edge or Chrome.

## What is real and what is not

- **The plates are drawn from measurements.** `plates.py` draws each as SVG from the small
  files in [`../plates/`](../plates) (numbers only, committed), which
  `../analysis/export-plates.py` wrote from the results of 2026-11-27
  ([results](../results.md)): the noise bins and the exposure ratios of the five ISO 100
  bursts, the unlit dark bursts with the 14 November series beside them, the arrivals of
  the return test. The warm-up and settle points are there too (`warm-up.json`,
  `settle.json`); `plates.py` can draw them, and no screen shows them yet.
- **The numbers in the inspector are the measured ones** where the results have them
  (gain, read noise, clip, the return test, the pitch of 108.46 pixels) and are examples
  where they do not: the Canon's black and file size are from the public sample file, its
  lens name is invented; the slide's pitch of 0.25 mm, the two halves of the band and the
  names of the other setups are invented; clock times are examples.
- **One picture is the owner's**: the calibration slide (`outputs/assets/setup-slide.jpg`,
  a crop of frame 9 of `stack-1795638138175-14989`). `outputs/` is ignored by Git, and
  without the picture the build draws a placeholder.
- The stage is fixed at 1680 × 1050. The sixth station is added to the Studio 2 shell's
  top bar by `build.py`; the rig and job chips at the top right are that shell's own
  examples.

## Files

| File | Holds |
| --- | --- |
| `build.py` | Assembles the page from the Studio 2 shell and this folder's screens |
| `plates.py` | The plates as SVG |
| `render.py` | Reference PNGs |
| `src/setup.css` | What this spec adds to the Studio 2 styles |
| `src/screens/*.html` | The eight screens |
