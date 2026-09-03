# M-PHASE0-LCA — preregistration

**Status:** REGISTERED BEFORE THIS LANE'S REAL-CAPTURE FOCUS STATISTIC WAS
COMPUTED.

**Registered:** 2026-09-02.

This lane gates claim **C2** in
`docs/proposals/2026-08-sota-path.md`, especially the section headed
“C2. Chromatic z-diversity — the bracket is three focus sweeps.”

## 1. Correction to the dispatch summary

The dispatch summary calls C2 *lateral* chromatic aberration: a radial
magnification difference. That is not the proposal's C2. C2 is
**longitudinal/axial chromatic aberration (LoCA)**: red, green, and blue have
different best-focus positions along the bracket's focus axis. The registered
quantity is therefore the per-channel through-focus peak displacement in frame
indices, not a radial spatial displacement in pixels.

The proposed product action is also different. The default merge elects from
green and reuses that frame/weight for all four CFA planes. If a channel's
focus peak is displaced, C2 proposes keeping green election but gathering red
and blue at a per-channel focus-index offset. Lateral CA is already handled by
the distinct spatial profile in `strehl-core::optics`.

## 2. Prior-art search completed before registration

The required mechanical search was run as:

```powershell
python experiments\ORCH-drift-check\prior_art.py `
  "longitudinal chromatic aberration through-focus peak channel offset"
```

It returned `NO PRIOR REPORTS`, a false negative: direct vocabulary searches
found the following existing evidence.

* `docs/research/SYNTHESIS.md`, fact 1413: M107 measured
  `k_R-k_G = -0.67..-1.07` and `k_B-k_G = -0.36..-0.75` frames on five of five
  stacks, against a `|k_G1-k_G2| <= 0.008`-frame null. It reported a red
  gradient-energy cost of 8.96–14.74%.
* `experiments/M107-chroma/PRE-REGISTRATION.md`, Instrument B and bar B3:
  the question, statistic, 0.5-frame bar, same-sensor null, and achromatic
  subject control were registered before M107 measured. Current SYNTHESIS fact
  1413 identifies four controls including a zero-free-parameter label swap.
  No retraction of fact 1413 was found.
* `docs/research/BUILD-CHROMA.md`: a different whole-field instrument
  replicated red at -0.66..-0.90 and blue at -0.48..-0.75 frames on four
  stacks, with a +0.0005..+0.0113-frame G1-G2 null and 4.2–7.5% / 3.5–7.1%
  red/blue energy costs. Its headline says this was an independent
  replication. Its original outputs under `C:\dev\strehl-out\BUILD-CHROMA`
  are no longer present, and it used a linear-domain three-point parabola
  rather than C2's mandated M33 log-domain fit. It is corroboration, not a
  substitute for this audit.

The corpus therefore appears to have answered C2 before C2 was written into
the proposal. This lane will return **ALREADY ANSWERED IN CORPUS** if the
M107→BUILD-CHROMA chain passes the trust audit below. New decoding is an
independent audit on controlled captures, not a claim of novelty.

## 3. Exact question

On three controlled, previously unused subjects, does the red focus-energy
peak precede the average green peak by at least the already-registered
**0.5-frame M107 bar**, consistently across the field, when peak position is
estimated with M33's baseline-subtracted log-domain parabola?

Blue is a registered secondary quantity. It can strengthen C2 but cannot
rescue a failed red primary after the fact.

## 4. Captures and fixed analysis choices

All captures are read-only. The three primary subject strata are:

| subject stratum | exact stack | frames | role |
|---|---|---:|---|
| planar periodic grid | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55 | low-colour, near-planar primary |
| fabric weave | `D:\personal\macro\requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl` | 109 | dense natural texture primary |
| tilted metal ruler | `D:\personal\macro\requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f11-sw7-cpl` | 65 | known depth-gradient primary |

The grid's `sw1` (91 frames) and `sw10` (23 frames) captures are a registered
focus-step ladder around its primary `sw4` capture. They are not extra
independent subjects and never increase the primary `n`.

The loader is `rawpy 0.27.0`. `raw_image_visible` is copied inside the context
manager. The observed contract checked before registration is RGGB
`[[0,1],[3,2]]`, `RGBG`, 4688×7028 visible pixels, black 512, container white
16383. The independent `target\release\strehl.exe probe --limit 1` path reports
the same height, camera, ISO and black but a 7032-pixel rawler active width and
white 15360. Analysis uses only rawpy's common 7028 columns and records both
contracts; no statistic touches decoder padding.

Fixed choices:

* native CFA only: R, G1, G2, B; no white balance, demosaic, colour matrix, or
  rendered image;
* 8×6 fixed tile centres spanning the common field, with a 144-plane-pixel
  primary tile and 96/192-pixel ladder;
* Sobel `Gx²+Gy²`, spatially averaged inside each tile, per channel and frame;
* direct-to-reference phase correlation on G1 only, robustly fitted over frame
  index, rounded to integer plane pixels, then applied identically to every
  channel; never a channel-specific registration and never subpixel
  resampling;
* per-curve baseline = fifth percentile; fit a quadratic through
  `log(F[k-1]-baseline), log(F[k]-baseline), log(F[k+1]-baseline)` around the
  discrete argmax;
* a valid tile must have an interior argmax, positive baseline-subtracted
  triple, concave fit with `|vertex offset| <= 0.75`, one dominant local
  maximum, prominence at least 1.5, and registration residual at most
  2.0 plane pixels in the registered arm;
* green peak `k_G=(k_G1+k_G2)/2`;
  `delta_R=k_R-k_G`, `delta_B=k_B-k_G`, and
  `delta_null=k_G1-k_G2`.

## 5. Primary statistic, uncertainty, and verdict bar

For each primary stack, first take the median `delta_R` across valid tiles.
Tiles, not pixels or frames, are the independent units.

The single deciding number is

```text
A = min over the three subjects of abs(median_tile(delta_R)).
```

The sign is not discarded operationally: every subject median must be
negative, the direction established a priori by facts 1413/1416. `A` uses
absolute value only to express the magnitude bar. Its 95% interval is a
10,000-draw stratified cluster bootstrap that resamples tiles independently
within each subject, recomputes each subject median, and then recomputes the
minimum.

The historic 0.5-frame threshold is retained rather than replaced with an
easier post-discovery bar:

* **SURVIVE:** lower 95% bound of `A >= 0.50` frame, all three red medians have
  the registered negative sign, and the null gate below passes.
* **NARROWED:** a replicated negative red displacement is resolved from zero
  but the lower 95% bound is in `[0.25, 0.50)` frame. Record it, but do not
  build a shifted gather from this lane.
* **KILL:** upper 95% bound of `A < 0.25` frame, or the sign fails to replicate
  on at least two subjects.
* **NOT ROBUST:** the categorical result changes on any registered ladder in
  §8. This overrides a clean primary result.
* **ALREADY ANSWERED IN CORPUS:** the current M107 fact and independent
  BUILD-CHROMA replication directly measure this quantity, M107's
  preregistration and commissioning are intact, no retraction applies, and
  this lane finds no load-bearing invalidity. The audit's own SURVIVE /
  NARROWED / KILL classification is still reported beside this verdict.

**Null gate:** for each primary stack,
`abs(median(delta_null)) + 95% bootstrap half-width < 0.125 frame`.
Failure voids the real-capture result as an instrument failure; it cannot be
relabeled NARROWED.

The 0.25 lower boundary is half M107's registered action bar. It creates an
honest grey zone rather than turning any statistically nonzero sub-step into a
product mandate.

## 6. Bias direction declared before measuring

The dominant risk is a **false SURVIVE**.

| source | direction | control |
|---|---|---|
| The prior -0.7..-1.1-frame result is known while implementing this audit | favours SURVIVE through analyst choice | every path, tile, threshold, fit, seed, and bar is frozen here |
| Different colours carry different scene texture and SNR | favours a spurious channel offset / SURVIVE | low-colour grid, G1-G2 null, three subjects |
| Static lateral CA makes channels sample slightly different positions; on a tilted/deep subject that can mimic a focus-axis shift | favours SURVIVE and radial growth | planar grid, radial annuli, centre-field stratum, common registration |
| A channel-specific registration could absorb or manufacture the signal | either direction | registration is estimated on G1 once and shared unchanged |
| Integer registration broadens curves relative to exact subpixel tracking | biases toward KILL | registered and unregistered arms plus three tile sizes |
| Coarse focus steps attenuate a sub-step fit and can hit the estimator's response ceiling | biases toward KILL | fixed external dose ladder and real `sw1/sw4/sw10` ladder |
| Tile medians suppress a real effect confined to richly textured points | biases toward KILL | prominence ladder and valid-tile counts are reported |
| Field curvature can differ with wavelength | favours SURVIVE, but is physically part of chromatic focus displacement rather than lateral magnification | report four radial annuli; do not call a radial term uniform LoCA |

No visual verdict is used.

## 7. Commissioning plan — every control gets a red plant

Commissioning runs before any real-capture focus measurement. It writes one
machine-readable record under `out/` and exits nonzero unless every untreated
control is green **and** every planted defect is red.

1. **Fixed external peak predicate (cancellation-immune).** The estimator reads
   a committed table of response values and a separately committed predicate
   containing fixed R/G1/G2/B peak positions. The measurement code did not
   generate either. Plant: replace the log-domain fit with the linear-domain
   parabola. It must go RED.
2. **Sign and units.** The same fixed predicate checks signed `delta_R`,
   `delta_B`, and the G1-G2 null. Plants: invert the vertex sign and multiply
   frame coordinates by two. Both must go RED.
3. **CFA layout.** A fixed mosaic whose four sites carry distinct externally
   declared constants must split to R/G1/G2/B in the declared order. Plant:
   swap B and G2 indices. It must go RED.
4. **Registration convention.** A deterministic texture is moved by fixed
   `numpy.roll` displacements, a code path independent of the phase correlator.
   Plant: invert the returned shift. It must go RED.
5. **Null sensitivity.** Equal G1/G2 fixed curves must read below 0.01 frame.
   Plant: shift G2 by one sample. It must go RED.
6. **Dose/ceiling ladder.** Known focus-axis doses
   `{0, 0.25, 0.5, 1, 2}` are applied outside the estimator. Report what the
   estimator actually reads at every dose; require monotonic response and
   0.9–1.1 slope through 1 frame. Plant: clamp every recovered displacement to
   0.25 frame. It must go RED. The 1-frame reading, not the physical dose, is
   the reference for judging whether the positive control saturates.
7. **Independent decoder contract.** Compare rawpy's copied visible geometry,
   CFA pattern, black level, ISO and first-frame deterministic plane summaries
   with the Rust/rawler `strehl probe` contract and a second rawpy decode.
   Plant: admit the full padded raw buffer as the active area. It must go RED on
   the fixed 4688×7028 predicate.

The fixed external predicate is the mandatory control whose answer neither
the estimator nor its input generator produced. Synthetic image/curve arms are
supporting controls only.

## 8. Registered robustness ladders and confounds

The primary result is recomputed without changing decoded data over:

* tile side `{96, 144, 192}` plane pixels;
* prominence `{1.2, 1.5, 2.0}`;
* baseline percentile `{0, 5, 10}`;
* common integer registration versus no registration;
* four field-radius quartiles and a centre-field subset;
* the grid's real focus-step sequence `sw1/sw4/sw10`.

The fit remains log-domain on every verdict-bearing arm. A linear parabola is
reported only as a dissenting estimator because the proposal explicitly
chooses M33's log fit. If any admissible ladder changes SURVIVE /
NARROWED / KILL, the lane files **NOT ROBUST** and names the rung.

The aperture-independent premise in the dispatch belongs to lateral CA, not
C2. This lane therefore does not treat aperture independence as a required
LoCA signature. The two non-grid primaries are both f/11; the grid is f/5.6,
so an aperture-confounded disagreement is visible but cannot be decomposed
without another lane.

## 9. What would change in Rust

This lane is forbidden to edit outside its experiment and research note, so it
will not modify Rust itself. A SURVIVE result is nevertheless not allowed to
end as “more metrology”:

* `crates/strehl-core/src/optics.rs`: represent signed R/B **focus-axis**
  offsets separately from the existing spatial lateral-CA `eps` values, with
  the same gear refusal discipline;
* `crates/strehl-core/src/pyramid.rs`: stop applying one frame's green-derived
  temporal weight to R/G/B at the same focus index; accept temporally shifted,
  fractionally interpolated R/B contributions while keeping green election;
* `crates/strehl-core/src/merge.rs`: make the estimator backend's second-pass
  gather use the same per-channel focus offset;
* `crates/strehl-cli/src/merge_cmd.rs`: carry frame index/step calibration
  through orchestration and buffer the adjacent R/B contributions needed for
  a fractional offset without materialising frames.

A constant in **frame units** may not be baked from one step width. The real
`sw1/sw4/sw10` ladder decides whether the profile can store a scaled physical
offset or whether a per-stack peak calibration is required.

## 10. Reproduction

All generated artifacts go under `experiments/M-PHASE0-LCA/out/`.

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
python experiments\M-PHASE0-LCA\src\commission.py
python experiments\M-PHASE0-LCA\src\measure.py
python experiments\M-PHASE0-LCA\src\verify.py
```

