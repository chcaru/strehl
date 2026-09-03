# M-PHASE0-XSPEC — C10's complex through-focus phase channel

**Lane:** `experiments/M-PHASE0-XSPEC/`

**Status:** complete; **NOT ROBUST**

**Preregistration:** commit `efdc6829`  
**Commissioned estimator:** commits `db43d7e4`, `e78f1b46`

## Finding

<!-- claim:verdict -->
**C10 is NOT ROBUST at this phase-0 gate. This is not a KILL.** The nominal
64-point result is negative for every proposed read, but the preregistered
population and grid-ladder conditions forbid promoting that result to a
conclusion about C10:

* `bee-1-cpl` supplied only **132 eligible strong-texture tiles**, below the
  preregistered minimum of 160;
* the held-out phase-floor check fails on the 48-point grid: only
  **71.43%** of warm-light records are within a factor of two of prediction,
  below the 80% bar.

All three programmed grid verdicts are `NOT ROBUST`. The result is therefore a
failed measurement gate, not evidence that the phase channel works and not a
licensed conclusion that it does not.

<!-- claim:headline -->
The one preregistered statistic governing reads 2/3 is the smaller stackwise
lower 95% bound for observed odd phase over its external floor. On the primary
grid it is **`0.66732`**. The weaker stack's point estimate is
**`R = 0.70852`**, tile-cluster-bootstrap **95% CI
`[0.66732, 0.76315]`**, against the required point `>= 2.0` and lower bound
`>= 1.5`.

That number is plainly below the bar, but it cannot carry a KILL because the
same stack misses the tile-population minimum and an alternate floor fails
commissioning.

## What C10 actually asserts

C10 is **not** the inter-colour or “borrow green detail for red/blue” proposal.
The authoritative section is
`docs/proposals/2026-08-sota-path.md`, “C10. NEW — the phase channel.”
It proposes registration-aligned **complex cross-spectra through focus** and
four reads:

1. linear phase ramps for sub-pixel registration near the `0.1 sensor-px` bar;
2. odd-in-defocus phase for the sign of defocus;
3. field-resolved phase-diversity retrieval of the pupil/aberration state;
4. phase coherence as a refusal guard against contrast inversion.

Its phase-0 gate calls for about 200 strong-texture tiles on two stacks, each
read across `+/-5` frames around an elected focus peak. If odd phase is below
the floor, reads 2 and 3 die together and C10 can retain only reads 1 and 4.

## Corpus search before measurement

The commissioned `experiments/ORCH-drift-check/prior_art.py` search established:

* `M70-through-focus-spectrum.md` measured modulus only and explicitly names
  aligned complex cross-spectra its highest-value unmeasured follow-up. Its
  saved products do not contain complex coefficients.
* `M-PHASE0-PHASE/PREREGISTRATION.md` records a retracted C1 KILL and final
  `NOT ROBUST`, including generator/checker cancellation, a sign defect, and a
  capped positive control. None of its truth labels was reused.
* `M-PHASE0-RHO.md` supplies the green-quincunx geometry, but its scalar moved
  **30.49x** across its frequency-grid ladder. XSPEC therefore fixes an exact
  grid and repeats the complete decision on two alternates.
* `M-PHASE0-QUINCUNX.md` establishes high-band energy at four of five
  apertures, but answers C12 rather than C10.
* `M78-blur-equalised-edges.md` shows that an interpolated half-shift can mimic
  a phase result by low-pass filtering. The primary XSPEC tiles are never
  resampled.

No commissioned corpus result already answers C10.

## Data and fixed conventions

The two outcome stacks were fixed before decoding:

| stack | frames | setting | selected / eligible / candidates |
| --- | ---: | --- | ---: |
| `D:\personal\macro\bee-1-cpl` | 299 | ISO 100, f/5.6 | 132 / 132 / 252 |
| `D:\personal\macro\wrapped-text-1` | 130 | ISO 100, f/5.6 | 200 / 244 / 252 |

The external floor used the 64 ISO-100 frames in
`12-bee-iso-var-no-bracket-32-repeat-diff-light`: 32 bright-light frames set
the overlap multiplier and 32 warm-light frames were held out.

Analysis is on undemosaiced green-quincunx patches. For GQ DFT coordinates
`fu,fv`, full-sensor coordinates are
`fx=(fu-fv)/2`, `fy=(fu+fv)/2`, with legal support
`abs(fx)+abs(fy)<=0.5`. The primary Welch grid is 64 and the fixed ladder is
64/48/32. Every grid uses a symmetric Hann window, 50% overlap, no padding,
and no resampling. Bands in cycles per sensor pixel are:

* registration `[0.02,0.12)`;
* odd phase `[0.06,0.22)`;
* inversion `[0.06,0.12)`, `[0.12,0.18)`, `[0.18,0.26)`.

The exact election, Fourier, boundary, coherence, bootstrap, and verdict rules
are in `experiments/M-PHASE0-XSPEC/PREREGISTRATION.md`.

## Commissioning

<!-- claim:commission -->
The final instrument is **GREEN: 8/8 controls pass and 9/9 planted defects go
RED**. `out/commission.json` is the machine-readable record.

The cancellation-immune absolute control periodically permutes untouched
samples from a real RAW crop and checks against the external shift theorem. It
recovers the fixed `(3,1)` sensor-pixel displacement with
**`2.22e-16 px` error**. It does not generate its input through the estimator.
Other load-bearing readings are:

* independent sub-pixel spatial shift: phase error **`0.007624 px`**;
* independent odd transfer: **`0.122524 rad`**; the magnitude-only plant falls
  to **`0.006723 rad`**;
* translated even blur after derotation: **`0.007325 rad`**; omitting
  derotation reads **`0.099681 rad`**;
* full inversion: **`rho=-1`** in every band; clipping or taking magnitude
  makes it non-negative;
* independent Gaussian floor holdout: observed/predicted **`0.987975x`**;
  halving the floor reads **`1.975949x`**;
* rawpy's `4688x7028` visible crop agrees at the origin with the shipping
  rawler probe's `4688x7032` active area; pretending the widths are equal is
  caught.

Plants cover shift sign, sensor-axis swap, GQ/sensor unit conversion,
frequency scale times two, omitted phase-ramp removal, magnitude-only spectra,
negative-correlation clipping, a halved floor, and the rawpy/rawler width
mistake. Every plant both landed and made its intended control fail.

## Real-capture results

### External phase floor

`q` is fitted only on bright repeats. The table evaluates untouched warm
repeats. “Central 95%” is the 2.5th--97.5th percentile of accepted record
ratios, not uncertainty on the median.

| grid | `q` | bright / warm accepted | warm median | central 95% | within factor 2 | literal prereg bar |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 64 | 4.18401 | 96 / 96 | 1.02323 | 0.29799--1.29339 | 83.33% | PASS |
| 48 | 2.64883 | 61 / 49 | 1.28214 | 0.47462--2.30419 | 71.43% | **FAIL** |
| 32 | 2.11806 | 32 / 19 | 0.89549 | 0.57862--3.27341 | 94.74% | PASS |

There is one implementation disclosure. `src/measure.py` also requires at
least 60 accepted bright and 60 accepted warm records, a conservative count
condition not stated in the preregistered floor paragraph. It changes the
programmed grid-32 floor field from literal PASS to FAIL. An independent
reclassification with that extra condition removed still leaves grid 32
`NOT ROBUST` because 132 tiles is below 160, and grid 48 still fails the
explicit 80% bar. It changes neither a per-grid verdict nor the lane verdict.

### Reads 2/3: odd phase

`R` is median observed phase RMS divided by its calibrated floor. Confidence
intervals use 10,000 tile-cluster bootstrap draws and keep all offsets of a
tile together.

| grid | stack | records / tiles | `R` | 95% CI | excess RMS rad | pass |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 64 | bee | 654 / 132 | 0.70852 | 0.66732--0.76315 | 0.00000 | no |
| 64 | text | 1000 / 200 | 0.80518 | 0.75459--0.85004 | 0.00000 | no |
| 48 | bee | 514 / 132 | 1.00718 | 0.92654--1.07186 | 0.02389 | no |
| 48 | text | 939 / 200 | 1.35174 | 1.22614--1.46848 | 0.19016 | no |
| 32 | bee | 236 / 132 | 1.17400 | 1.06181--1.31473 | 0.03963 | no |
| 32 | text | 535 / 200 | 1.31224 | 1.15427--1.53774 | 0.06117 | no |

No stack reaches the point bar of 2.0 on any grid. The increasing apparent
excess as the grid is coarsened is exactly why a grid-free phase scalar is not
filed. Positive excess is not attributed to a pupil: local deformation and
scene evolution can also create it.

### Read 1: phase-ramp registration

Precision is half the checkerboard-Welch split disagreement. It is a
repeatability statistic, not absolute registration accuracy.

| grid | stack | phase px, 95% CI | spatial px, 95% CI | phase/spatial, 95% CI | pass |
| ---: | --- | --- | --- | --- | --- |
| 64 | bee | 0.20053, 0.16952--0.22893 | 0.07253, 0.06304--0.08739 | 2.7647, 2.2934--3.2559 | no |
| 64 | text | 0.07203, 0.06644--0.07953 | 0.04244, 0.03577--0.05048 | 1.6974, 1.4451--2.0000 | no |
| 48 | bee | 0.17806, 0.16073--0.19917 | 0.07347, 0.06311--0.08508 | 2.4237, 2.0232--2.8677 | no |
| 48 | text | 0.07068, 0.06528--0.07655 | 0.03693, 0.03099--0.04247 | 1.9140, 1.6654--2.2585 | no |
| 32 | bee | 0.12536, 0.11331--0.13736 | 0.06388, 0.05589--0.07213 | 1.9625, 1.6670--2.2784 | no |
| 32 | text | 0.06060, 0.05548--0.06676 | 0.02117, 0.01910--0.02350 | 2.8621, 2.5556--3.2190 | no |

The text stack clears the absolute 0.1-px bound, but the phase estimator is
less repeatable than the independent spatial solver on every grid. Read 1
therefore fails its conjunction on both stacks.

### Read 4: contrast-inversion guard

The low-band occlusion mask never reads the inversion statistic; the placebo is
its fixed toroidal shift by `(+3 rows,+5 columns)`.

| grid | occlusion inverted / eligible | placebo inverted / eligible | risk ratio, 95% CI | pass |
| ---: | ---: | ---: | ---: | --- |
| 64 | 42 / 142 | 42 / 135 | 0.9507, 0.8506--1.0609 | no |
| 48 | 56 / 142 | 54 / 135 | 0.9859, 0.8991--1.0864 | no |
| 32 | 5 / 142 | 9 / 135 | 0.5282, 0.1898--0.8380 | no |

Grid 64's occlusion fraction is 29.58%, Wilson 95%
`[22.69%,37.54%]`, but the placebo is 31.11%. The apparent inversions are not
enriched at occlusions, so they do not license an admission guard.

## Robustness and independent verification

The programmed verdict is `NOT ROBUST` on 64, 48, and 32. The nominal read
classification would be KILL on each grid if all commissioning and population
preconditions were waived, but the preregistration expressly forbids that
promotion.

A separate read-only verifier recomputed every gate from
`calibration.json`, both detailed record files, and `inventory.json` rather
than accepting `summary.json`. It matched all reported point estimates,
bootstrap intervals, registration ratios, inversion counts, and programmed
verdicts to machine precision. It also:

* confirmed that no XSPEC source changed between the frozen estimator commit
  `e78f1b46` and measurement tree `5c2d416c`;
* confirmed the literal grid-32 floor correction above does not change its
  verdict;
* checked the sign, axis, unit, grid, split-half, odd-phase, floor,
  correlation, and clustering formulas against the preregistration.

`inventory.json` records `source_tree_unchanged=true` across all 493 outcome
frames plus the repeat directory. The measurement recorded repository HEAD
`5c2d416c`, because concurrent work committed two unrelated VEIL2 changes
after the XSPEC freeze; the path-specific diff is empty.

The independent verifier did not re-decode the RAW corpus and did not
independently re-hash every RAW file. It verified the saved record layer and
the source path from which that layer was produced.

## Bias and remaining limits

The declared researcher bias was **toward SURVIVE**. Selecting the strongest
modulus tiles, residual deformation, and scene evolution can all inflate odd
phase in that direction. Conversely, repeat motion or illumination drift can
inflate `q` and favour KILL; the fitted ramp can absorb a real linear odd term;
and the fixed placebo can land on real boundaries.

Only one Sony ILCE-7CM2, lens/teleconverter configuration, and two f/5.6
subjects were tested. The phase-ramp result measures split precision rather
than truth accuracy. No Zernike pupil was retrieved, no physical cause was
assigned to the residual phase, and no claim is made outside the fixed
green-quincunx bands.

## What changes in Rust

<!-- claim:rust-consequence -->
**Nothing changes in Rust as a result of this verdict.** In particular:

* no complex observer is added beside
  `crates/strehl-core/src/through_focus.rs`;
* no observer is wired into `crates/strehl-cli/src/merge_cmd.rs`;
* no phase-sign admission hook is added to the shipping
  `crates/strehl-core/src/pyramid.rs` fold.

This is not because the nominal numbers favour C10. They do not. It is because
the lane missed its own minimum population and alternate-grid floor gate, so
neither implementation nor a permanent KILL is licensed. A retry must first
choose two stacks with at least 160 eligible tiles and externally commission
the floor on every fixed grid; only then may the surviving read justify one of
those source changes.

## Reproduction and artifacts

From the repository root, with Python 3.12.10, NumPy 2.4.4, SciPy 1.17.1, and
rawpy 0.27.0:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
python experiments\M-PHASE0-XSPEC\src\commission.py
python experiments\M-PHASE0-XSPEC\src\measure.py
```

The result-bearing artifacts and SHA-256 digests are:

| artifact | SHA-256 |
| --- | --- |
| `out/commission.json` | `6e64c224b406106f2cc03508c77bfa73115f5099ae0a40ab9ab0ae0a4127038f` |
| `out/calibration.json` | `585eea46fceb518e99bb18e2d69a485d784cbf9b79a1f796b711975eabc1c719` |
| `out/inventory.json` | `d6a48e8e43192f24bce543260a567355e76909b9f1446f5fab397d662b5b3a3f` |
| `out/records-bee-1-cpl.json` | `e98d4fb38d75bd97746fb19633e4fad71029d515b6a2272a2124902d8867db58` |
| `out/records-wrapped-text-1.json` | `988b5931ff30d416dc333d8154bec154557f77515ba83a3a8c0760a2c3e3af51` |
| `out/summary.json` | `5ff86789daa2b86afbdb03f842212ead6030dbaa78209df2a5370addba6b2bee` |

The ignored `focus-scan-*.npz` files are decode caches, not additional result
authorities. All filed numbers are present in the JSON artifacts above and are
generated by the committed code in the experiment directory.
