# M95 arm 4 — pre-registration

Written before any arm-4 measurement was read. Rule 12.

## The question

The orchestrator measured a **0.3693 dex (2.34x power, 1.53x amplitude)** deficit in the
band 0.30–0.48 cyc/px between a rawpy/LibRaw full-resolution decode of `DSC00150.ARW` and
strehl's full-resolution `--gate 0` merge of `bee-3-cpl`. They named a confound they could
not price from outside the codebase: **rawpy's demosaic is not strehl's**, and demosaic
differences bite hardest in exactly this top octave.

This arm prices that confound and decomposes what is left.

## Terms

All four are 7032 x 4688, 16-bit, **linear camera-native** (no `--srgb`), rendered by the
same binary in this session. Keeping every term linear removes the transfer curve from the
comparison; a nonlinearity would redistribute power across the band and is not the subject.

| Term | What it is | Demosaic | Election | Warp | Coverage zoom |
| --- | --- | --- | --- | --- | --- |
| **A** | rawpy/LibRaw decode of `DSC00150.ARW` | LibRaw | no | no | no |
| **B** | strehl render of a 1-frame directory holding only `DSC00150.ARW` | strehl MHC | trivial | no | no |
| **D** | strehl 299-frame merge, `--gate 0`, `STREHL_ALIGN=0` | strehl MHC | yes | no | no |
| **C** | strehl 299-frame merge, `--gate 0`, alignment ON | strehl MHC | yes | yes | yes (0.9315) |

`DSC00150.ARW` is frame 149, which is the merge's own reference frame, so its warp is
identity and it is the one frame whose content reaches C without a warp gather.

## The decomposition

- **A -> B** is the **demosaic-algorithm difference** and nothing else. Same photons, same
  sensor, same geometry, two demosaic implementations. This is the orchestrator's unpriced
  confound, isolated.
- **B -> D** is the **election** and nothing else. Same geometry, no resampling anywhere.
  At gate 0 a different frame may win each pixel, so this is the price of the mosaic of
  elected frames relative to one frame.
- **D -> C** is the **cost of alignment**: one CatmullRom warp gather per pixel plus the
  0.9315 coverage zoom. This is the resample price the orchestrator asked me to find.

A -> B + B -> D + D -> C is not required to sum to 0.3693 dex, because A -> C is not the
same pair the orchestrator measured (they measured an sRGB-path file and I am measuring
linear). The decomposition is claimed on its own terms, not as an audit of their number.

## Pre-registered bars

Stated before results were read.

- **B4 — resampling is the dominant cause.** Fires if `D -> C` costs **>= 0.20 dex**
  (>= 1.58x power) in 0.30–0.48 cyc/px. If B4 fires, a resample fix is worth building and
  I will price whether the coverage zoom is avoidable.
- **B5 — the orchestrator's number is substantially demosaic difference.** Fires if
  `A -> B` is **>= 0.20 dex**. If B5 fires, a material share of 0.3693 dex is algorithmic
  difference between two demosaic implementations and not loss, and I must say so plainly
  even though it makes the defect smaller than the orchestrator currently believes.
- **B6 — resampling is NOT the cause.** Fires if `D -> C` costs **< 0.05 dex** (< 1.12x).
  If B6 fires I must report that resampling is not the softness, redirect, and not build
  a fix.

B4 and B5 are **not exclusive**. Both can fire; the deficit can have two causes.
B4 and B6 are exclusive by construction. If `D -> C` lands in [0.05, 0.20) dex the result
is "real but minor" and no bar fires; I will report the number and say no bar fired.

## The geometry hazard, and how I handle it

C's field of view is scaled to 0.9315 and then written at full output dimensions. Its
sampling is therefore **1/0.9315 = 1.0735x finer per unit of scene** than B or D. The same
scene feature sits at a **7.35% lower** spatial frequency in cyc/px in C than in B.

This biases a naive cyc/px comparison **against C**: the band 0.30–0.48 cyc/px in C samples
scene frequencies 0.322–0.515 in B's units, which is higher up a falling spectrum and
therefore has less power. Some unknown part of any C deficit measured in raw cyc/px is this
stretch rather than loss.

I handle it two ways and report both:

1. **Band matching.** C is integrated over `[0.30, 0.48] / 1.0735 = [0.2795, 0.4471]`
   cyc/px so that both files cover the same **scene** frequency band. No pixel data is
   resampled to achieve this; only the integration limits move.
2. **Round-trip price (`K12`).** Independent of any geometry argument: take B, apply the
   coverage zoom with an independently written CatmullRom, then apply its inverse. The
   result is back in B's geometry and has paid **two** resamples where C paid one, so
   `B -> B''` measured in B's own band is an upper bound on twice the single-resample cost,
   with **zero** geometry confound. If half of `B -> B''` disagrees badly with the
   band-matched `D -> C`, I do not have a result and must say so.

## Controls — every one must be reported, including failures

- **K6 — sensitivity (discipline 594).** Plant a known sigma = 0.5 px Gaussian blur on B
  and require the instrument to read a deficit in the correct direction. An instrument that
  cannot see half a pixel of blur cannot claim `D -> C` is small. **Report the response.**
- **K7 — null.** B against itself must read **0.000 dex**. Any nonzero is a bug.
- **K8 — anchor separation gate.** Require the separation between the null (K7) and the
  planted blur (K6) to be **>= 0.30 dex** before the instrument is allowed to speak, and
  require every reported quantity to lie inside the anchors. This is the orchestrator's own
  gate and it is the reason their third attempt was trustworthy where two earlier ones
  were not.
- **K9 — in-focus tile selection.** Tiles are the sharpest by gradient energy **on B**, so
  the single frame is in focus in them. Selecting on the merge would flatter the merge.
- **K10 — registration check.** Tiles in C must land on the same scene content as in B.
  Verify by cross-correlation and refuse to report if the residual offset exceeds 2 px.
- **K11 — instrument mutation.** Mutate the band definition in the analysis code and
  confirm the reported numbers move. A number that survives a mutation of the code that
  produced it was not produced by that code.
- **K13 — power control (discipline 595).** If the headline is an absence (B6 fires), hand
  the instrument a disturbance of the size I am claiming is absent and show it detects it
  on the same tiles. Absence claims without this are inadmissible.

## What would falsify a fix

If I propose emitting the cropped region at native sampling instead of stretching it back
to sensor dimensions, the fix is falsified if a render built that way does **not** reduce
the band-matched `D -> C` deficit by at least the `K12` single-resample price. A fix that
changes which frame wins a pixel is a **finding to report**, not something to absorb: the
byte-exact election result from arm 1 is now a regression test.

## Scope declared up front

- This arm measures the **full-resolution `--demosaic` branch only**. It says nothing about
  the default binned viewing path, which arm 3 already measured separately.
- `--demosaic`'s own help says its extra samples are interpolated and its resolution is not
  to be measured. That warning is about **absolute** high-band content. This arm compares
  B, D and C, which all carry the **same** MHC interpolation, so the interpolation cancels
  from B -> D and D -> C. It does **not** cancel from A -> B, which is precisely why A -> B
  is reported as the demosaic difference and not as loss.
- Any fix in `merge_cmd.rs` is out of my ownership. I report and stop, with a verbatim
  patch.
