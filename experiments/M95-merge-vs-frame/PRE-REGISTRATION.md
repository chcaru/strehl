# M95 (merge-vs-frame) — pre-registration

Frozen **before** any merge/frame comparison number was computed. Written at
pinned repository sha `1f17c1d547a996d05a412570a9257894005d786b`.

## The question

> Is the merged output as sharp as the sharpest single frame that went into it,
> in a region where that frame is in focus?

## Arms

All rendering goes through **one binary**, built once from the pinned sha at
`C:\dev\strehl-out\M95-pin\target\release\strehl.exe`, so no concurrent edit to
`merge.rs` can desynchronise the arms.

| arm | command | what it is |
|---|---|---|
| **M** | `STREHL_ALIGN=0 strehl stack <bee-3-cpl> --gate 0 --out …` | merged output, pure selection (`n_eff` = 1), unregistered — the path every corpus number and every image the owner has seen was made on |
| **F** | `STREHL_ALIGN=0 strehl stack <one-frame-dir> --gate 0 --out …` | **one frame, through the identical code path**: same decode, same black/white levels, same white balance, same binning, same writer, same grid, same crop |
| **M4** | as **M** with `--gate 4` | shipped default, for reference only |
| **C** | `strehl stack <bee-3-cpl> --gate 0 --out …` (alignment ON) | registered merge — resamples (Catmull-Rom) onto a zoomed grid |
| **Z** | `STREHL_ALIGN=zoom strehl stack <bee-3-cpl> --gate 0 --out …` | zoom-only null: identical resampling cost and field of view, registration discarded |

**M** and **F** are on the same 3516×2344 plane grid with **no resampler in
either**, so an ROI is literally the same pixels. **C** and **Z** are on a
different (zoomed) grid and are only ever compared with each other.

Measurement is on the **binned linear camera-native** output — no demosaic, no
colour matrix, no transfer curve. That is the byte-frozen measurement path.

## Metric

Radially averaged power spectrum of the Hann-windowed **green** plane of a
512×512 plane-pixel ROI, in linear DN. Reported as a full curve, and reduced to
a band-integrated **amplitude** ratio `R = sqrt(P_M / P_F)` over a band, then
converted to an **equivalent Gaussian blur `σ_eq`** by calibrating the same
band ratio against blurs of known σ planted into arm F.

`σ_eq > 0` means the merge is softer than the frame.

Green only, because green is the physically sampled luminance channel. Linear
only, because a transfer curve folds harmonics into the band under test. ROIs
containing any clipped sample are rejected.

## ROI selection rule (fixed before any M-vs-F number exists)

Candidate ROIs are chosen **from the frames alone**, never from the comparison:

1. 512×512 plane-pixel windows on a 256-px stride, ≥ 64 px from every border.
2. Reject any window containing a sample at or above the clipping level in the
   frames sampled.
3. Score each window by its **through-focus peak** high-band energy over a
   20-frame subsample of the stack.
4. Take the three highest-scoring windows subject to being at **different radii**
   from the image centre — one small, one middle, one large — because the drift
   that fact 1177 measures is a magnification change and therefore grows with
   radius. If the radius stratification is not achievable, say so.
5. One extra window with the **lowest** score is kept as the rule-9 flat control.

## The single frame ("the sharpest that went in")

Chosen **per ROI** as the frame maximising that ROI's high-band energy, computed
by an **independent instrument** (a `rawpy` decode and my own binning), not by
`strehl`'s focus measure.

Rule 4 applies to analysis scripts: a maximum over 299 noisy scores is biased
upward. Two defences, both required:

- **Cross-fit.** Choose the frame on ROI half A, evaluate the comparison on ROI
  half B, and vice versa. Report both.
- **Neighbourhood.** Report the comparison against the peak frame and against
  peak ± 1 and ± 2 as well; if the answer depends on which of five adjacent
  frames is used, the answer is not a measurement.

## Pre-registered bars

Let `σ_eq` be the equivalent Gaussian blur of the merge relative to the frame,
in plane pixels, in the detail ROIs.

- **CONCLUDE THE MERGE LOSES SHARPNESS** if `σ_eq ≥ 0.25 px` on **≥ 2 of the 3**
  detail ROIs, under both the raw and the noise-subtracted reduction, and stable
  across the peak ± 2 frame neighbourhood.
- **CONCLUDE THE MERGE DOES NOT LOSE SHARPNESS** if `σ_eq ≤ 0.10 px` on **all
  three** detail ROIs under both reductions.
- **INDETERMINATE** otherwise, and it will be reported as indeterminate rather
  than argued in either direction.

0.25 px is a third of M57's measured 0.496–0.740 px selector-vs-estimator price
(fact 813), so it is a bar this corpus already knows is a meaningful amount of
blur. 0.10 px is below anything this project has ever claimed to resolve.

## Controls the instrument must pass before any result is read

- **R1 responsiveness / positive control (discipline 594).** Plant Gaussian
  blurs σ = 0.25, 0.5, 1.0 px into arm F and require the metric to recover each
  within ±25%. An instrument that cannot say "this is blurred" cannot say "this
  is not".
- **R2 power control (discipline 595).** Compare **M** against a frame taken
  deliberately off the focus peak (peak ± 10 and ± 25 frames). The merge must
  read *sharper* than those, with a large margin. This proves the comparison has
  power in the direction of the test, not merely that the metric moves.
- **R3 flat-ROI control (rule 9).** Run the whole comparison on the flat control
  window. A ratio there is **not** evidence of retention; per M80's fact 1127,
  retention on zero resolved detail is undefined, not 1.0. It is reported and
  explicitly not interpreted as sharpness.
- **R4 loader control (rule 32).** Arm F's output must agree with an independent
  `rawpy` decode plus my own binning of the same `.ARW`, to quantisation. If it
  does not, arm F is not "the plain frame" and nothing else may be read.
- **R5 determinism.** Two runs of the same arm must be byte-identical, and the
  five arms must have distinct hashes. A flag that turns out to be inert voids
  everything above it.
- **R6 negative control made to fail.** A deliberately corrupted arm must be
  caught by the harness, and the failure reported.

## Second arm — the 74 cy/mm artifact floor (M85 §7)

Same data, one extra render each of **M** and **F** with `--demosaic`. The
plateau lives above the binned Nyquist (48.8 cy/mm) so it is only visible on the
full-resolution path. The partition is:

- plateau present in **F** at the same level as **M** → the floor is **not** the
  merge; it is demosaic, sensor or optics.
- plateau present in **M** but not **F** → the floor **is** the merge.

Then a demosaic-free arm: the green quincunx of a single frame, zero-filled and
transformed directly, which reaches 97.7 cy/mm on-axis with a known aliased
replica term. That separates the demosaic from the sensor and optics.

Effective aperture and diffraction cutoff are re-derived from primary optics in
this session and checked against the corpus's measured `N_eff` work; no cutoff
is taken on report.

## Scope declared in advance

One subject (`bee-3-cpl`), one gate axis, one metric family. M52 measured the
gate achieving a given `n_eff` varying 28.9× across the corpus, so nothing here
transfers to another stack without being re-run.
