# V-LINEAR2 pre-registration

Written **before** the band-signal sweep was run, and committed on its own so
that the git timestamp is evidence of the ordering. Nothing in this file was
edited after the first number came back; corrections, if any, appear in the
report as an explicit amendment with a reason.

Lane brief: replace the unrunnable comparator (Zerene, trial expired --
`docs/research/V-LINEAR.md` §1) with free/open stackers, and run the head-to-head
**only on a band that demonstrably contains signal**.

The reason this file exists: `docs/research/V-LINEAR.md` §5.3 measured that
0.20-0.48 cyc/px is a noise band on this corpus (in-focus/defocused power ratio
1.015, 1.043, 1.004, 1.138 over four frame pairs). If I now pick the comparison
band after seeing which band flatters strehl, the result is manufactured. So the
band is chosen by a criterion fixed here, from a test that never sees a
comparator's output.

---

## 1. The band-selection test

Instrument: `bandsignal.py` (this directory), a per-tile generalisation of
`../V-LINEAR/noisefloor.py`.

Inputs: the 63 linear develops in `C:\dev\strehl-out\V-LINEAR\lintiff\`, made by
strehl's own decoder (`--linear-srgb --demosaic`, `STREHL_ALIGN=0`). **No
comparator output is read by this test.**

For each tile position on a grid, over the 63-frame focus sweep:

1. **Best-focus frame** is the frame maximising power in the *selection band*
   0.05-0.20 cyc/px -- above the tone scale, below every contested band.
   Required to be an **interior** maximum (not frame 1 or 63), else the tile is
   dropped: a tile that never came into focus cannot answer the question.
2. **Defocused reference** is the mean power over the frames at best +/- 20
   steps (whichever exist) at the *same* tile.
3. `R_band = P_band(best-focus) / P_band(defocused)`, aggregated over tiles as a
   sum-of-power ratio, with a 95% bootstrap CI over tiles (10,000 resamples).

Selecting on 0.05-0.20 and reporting 0.20+ is deliberate: FFT bins of
approximately white noise are approximately independent, so selection on one band
does not bias the estimate in a disjoint band. The selection band's own ratio is
therefore reported *with* a winner's-curse caveat and is not eligible to be the
comparison band.

## 2. Decision rule -- fixed now

| outcome | criterion |
|---|---|
| **PASS** -- eligible to be the comparison band | `R >= 2.0` **and** bootstrap CI low >= 1.5 |
| **MARGINAL** -- reported, never the headline | `1.3 <= R < 2.0` |
| **FAIL** -- noise, no comparison may be reported there | `R < 1.3` |

**The comparison band is the highest-frequency PASSing band.** Not the one with
the best score, not the one the comparators disagree most about -- the finest one
that carries signal, because "fine-scale resolution" is the question.

**If no band above 0.10 cyc/px passes, that is the answer and I stop.** I do not
drop to a coarser band and report it as if it addressed the resolution question,
and I do not report a MARGINAL band as a result. In that case the deliverable is
the capture request, not a verdict.

## 3. What is measured once a band is selected

Per comparator, on the *same* 63 linear TIFFs, with geometry re-derived per
comparator (never assumed -- `docs/research/V-LINEAR.md` §3 and V-HEADTOHEAD2 §7):

- coarse-normalised band power, strehl vs comparator, over peak-gated ROIs;
- 95% bootstrap CI over ROIs;
- reported as a ratio, with the sign stated in words.

## 4. Floors and falsifiers -- armed before the comparison

1. **NULL identity bias** (measured, `V-LINEAR` §5.1): fitting a tone map from an
   image to itself and applying it already loses 1.0-1.4% of fine-band power.
   **Any difference below 5% is reported as LEVEL, not as a win.** Nothing this
   instrument says at 1-5% is a difference.
2. **BLUR falsifier** (`gradeatsource.py` BLUR arm): a real 0.6 px blur must be
   explained by the block-average tone fit at **< 10%**. If it is not, the
   estimator can manufacture resolution differences from tone and no number is
   reported.
3. **Tone-sufficiency gate** (`gradetest.py`, the V-HEADTOHEAD2 acceptance test):
   the 4x4-block tone fit must explain **< 50%** of the measured gap. At >= 50%
   the comparison is a tone measurement again and I report that instead of bands.
4. **Coherence caveat** (V-HEADTOHEAD2 §7, disclosed): `C` is inflated by noise
   common to both half-stacks (NOISE_COM arm scores 6.05). `C` is therefore not
   used as a headline statistic here.

## 5. Verdict vocabulary -- fixed now

- **AHEAD**: strehl's coarse-normalised power in the selected band exceeds the
  comparator's by > 5%, CI excluding 1.0, with falsifiers 1-3 passing.
- **LEVEL**: difference <= 5%, or CI including 1.0.
- **BEHIND**: comparator exceeds strehl by > 5%, CI excluding 1.0.
- **UNDETERMINED**: any falsifier fails, no band passes §2, or geometry cannot be
  established. This is an acceptable outcome and is preferred over a weaker band.

## 6. Comparators

Run, not vendored. No comparator's source enters this repository; licence stated
per comparator in the report. Each gets the identical 63 linear TIFFs and one
recorded command line.

Target set (at least two): Hugin `align_image_stack` + `enfuse --hard-mask`
(GPL); CombineZP (free); Photoshop auto-blend *only if already licensed here*;
ImageJ/Fiji EDF if it runs headless.

---

Written 2026-08-27, before `bandsignal.py` was run for the first time.
