# M167 — independent adversarial detail-instrument battery

**Status: BATTERY COMMISSIONED; THREE KNOWN-DEAD INSTRUMENTS REJECTED; NO
DEPLOYABLE DETAIL INSTRUMENT ADMITTED.**

## 1. Question and result

M167 does not propose another detail statistic.  It freezes and commissions the
acceptance battery that a future candidate must survive before this program may
use it for a resolution claim.

The predicates were committed before candidate execution in `8a305128`,
`ca79eac7`, and `5fe75c14`.  The executable preregistration is
`experiments/M167-detail-battery/PREREGISTRATION.md`.

**VERIFIED.** The battery is commissioned:

- its literal all-GREEN fixture passed;
- it caught `8 / 8` one-property checker sabotages;
- its constructed optical-truth oracle passed all six mandatory arms;
- D8 per-tile FRC was rejected;
- the M137 high/low band-power gap was rejected; and
- M2 `R_box9` was rejected on signed blur, reproducing
  `0.5712148772282098x`.

The machine-readable record is
`experiments/M167-detail-battery/results.json`.  Its top-level status is
`COMMISSIONED` and every hard commissioning check is true
(`results.json:1-50,527`).

No known-good deployable instrument exists in the repository.  The positive
control is therefore a construction-truth oracle, not a candidate and not
evidence that a single-image resolution statistic is possible.

## 2. What was frozen

All candidate scores are oriented so that higher means more resolved.  A
candidate may emit a point, lower bound, upper bound, or typed refusal.  Bounds
are compared conservatively: overlap and equality do not prove direction.

| ID | arm | pre-registered pass predicate |
|---|---|---|
| **P1** | flat-ROI null | A no-scene flat must explicitly refuse as `NO_DETAIL`/`FEATURELESS`, or its entire score interval must lie below the detailed interval: `flat.upper < detail.lower`. |
| **P2** | planted improvement | A render with optical sigma `0.55 px` must lie wholly above the `1.00 px` base: `improved.lower > base.upper`. |
| **P3** | planted degradation | A render with optical sigma `1.65 px` must lie wholly below the `1.00 px` base: `degraded.upper < base.lower`. |
| **P4** | signed blur monotonicity | Scores at added post-render Gaussian sigma `[0,.5,1,1.5] px` must be strictly decreasing interval-by-interval. Equality, refusal, or any rise fails. |
| **P5** | sharpening-vs-resolution | The real optical improvement must beat base, while USM (radius `1 px`, amount `.75`) must explicitly refuse as `SHARPENING_UNSAFE` or score no higher than base. |
| **P6** | fail closed | A `NaN` image and a one-dimensional image must each produce a typed refusal/error, never a value, bound, non-finite result, or omission. |

There is no compensating aggregate: all six arms must pass.  The full result
contract, fixture construction and predicates are frozen in
`PREREGISTRATION.md:20-133`.

### Fixture construction

`fixtures.py` constructs a deterministic `1024 x 1024` latent field and renders
it to `256 x 256` through registered Gaussian optical PSFs before
area-sampling.  Optical arms reuse identical downstream noise, so the
registered optical intervention is the only change.  USM and the blur ladder
instead operate on completed images.

The flat arm contains no scene modulation.  It does contain a shared broadband
fixed pattern plus independent temporal noise, and the matched detail arm sees
the same pattern/noise.  This is deliberate: an instrument must distinguish
resolved scene information from repeatable sensor structure rather than merely
detecting repeatability.

**VERIFIED independence.** `commission.py` imports neither `fixtures.py`,
`measure.py`, nor any candidate.  It invokes `measure.py` as a child process
and adjudicates only JSON.  `measure.py` imports no checker or predicate.  All
numerical thread variables are forced to one by the parent process.

## 3. Battery commissioning

### 3.1 Checker power

**VERIFIED.** The literal accepted record passed P1-P6.  Eight targeted
sabotages were all caught: flat equality, improvement blindness, degradation
blindness, a tied blur rung, rewarded USM, numeric malformed input, generic
flat refusal, and a missing arm (`results.json:2-37`).

This does not by itself make the battery sound; the known-dead controls below
are the decisive commissioning requirement.

### 3.2 Constructed oracle

**VERIFIED PASS, P1-P6.** The oracle reads private construction labels:

- base `1.0`;
- genuine improvement `1 / .55 = 1.8181818181818181`;
- degradation `1 / 1.65 = 0.6060606060606061`;
- blur ladder
  `1.0, 0.8944271909999159, 0.7071067811865475,
  0.5547001962252291`;
- USM `1.0`, tied with base; and
- typed refusal/error for the two malformed cases.

All six gates are true (`results.json:910-1019`).  This proves the accepted set
is nonempty.  It does **not** commission an image instrument: the oracle uses
truth metadata ordinary candidates are forbidden to receive
(`results.json:501-525`).

## 4. Known-dead instruments

| instrument | M167 verdict | rejecting arm(s) | decisive observed result |
|---|---|---|---|
| D8 per-tile FRC | **REJECTED** | **P1 flat null**; also P4 blur | Detail and no-scene flat both returned `CENSORED_ABOVE`, lower bound `0.5 cyc/quad-px`; their intervals overlap completely. |
| M137 high/low band-power gap | **REJECTED** | **P1 flat null**; also P5/P6 | Flat `0.3488548829813006 dex` exceeded detail `0.3403664343410666 dex`, ratio `1.0249391472947889`, despite only `0.13314850036584688` of the coarse structure. |
| M2 `R_box9` | **REJECTED** | **P4 signed blur**; also P1/P2/P3/P5/P6 | Independent replay returned `R_box9(blurred)/R_box9(unblurred) = 0.5712148772282098`; all three M167 blur steps moved in the favourable direction. |

### 4.1 D8 per-tile FRC

M167 executes the source-hash-pinned surviving implementation at
`experiments/M-PHASE0-SPLIT2/frc.py`.  It preserves the historical classifier:
a curve above `1/7` through Nyquist is a lower bound, not a fabricated terminal
crossing.

**MEASURED.** On M167's matched flat arm, both detailed and no-scene records
were `LOWER_BOUND 0.5`; P1 therefore cannot establish
`flat.upper < detail.lower` and rejects D8
(`results.json:664-679,761-774`).  The pooled low-band FRC was
`0.9989656493074857` on detail and `0.9940552535661507` on the flat
(`results.json:278-280`).

**MEASURED.** D8 also failed signed blur.  Its crossing sequence for added
sigma `[0,.5,1,1.5]` was
`0.44807855374505606, 0.44806009012025305,
0.4481711193804649, 0.4485069054687077`; the last two steps rose rather than
fell (`results.json:689-723`).  This is the normalized common-filter
blindness recorded in the plan, now exercised by the frozen M167 predicate.

### 4.2 M137 band power

The original RAW pixels are not copied into M167 and were not reopened.
Instead, the adapter hash-pins the tracked underlying `band_ratio` source and
executes it for synthetic diagnostics, while P1 consumes the immutable,
independently verified historical kernel-gap snapshot.

**VERIFIED FROM PINNED SERIALIZED EVIDENCE, not newly re-rendered.** The adapter
reproduced the exact detail gap, flat gap, ratio and structure share above
(`results.json:148-158`).  Since the flat point is greater than the detail
point, P1 rejects it (`results.json:538-550,634-648`).  This is the same
historical `1.0249391472947889` failure, not a newly tuned surrogate.

The synthetic underlying statistic also called USM better than base
(`-1.9949655187454454 > -2.3844797126768977`) and emitted an invalid/non-refusal
on malformed inputs.  Those are retained diagnostics; the exact historical
flat failure alone is sufficient.

### 4.3 M2 `R_box9`

The adapter reimplements exactly
`population_sd(image / uniform_filter(image,9) - 1)` and pins both the M159
source and frozen result hashes.  Because lower residual was M2's favourable
direction, M167 orients its score as negative residual.

**MEASURED.** Replaying M159's complete seed-159 RNG sequence produced:

```text
unblurred R_box9 = 0.0521781532174448
blurred   R_box9 = 0.02980493738409746
blurred / unblurred = 0.5712148772282098
```

The replay equals the frozen value and is recorded at
`results.json:389-394`.  On the independent M167 blur ladder, the
higher-is-better scores rose
`-0.04995233606232108 -> -0.0445857853669207 ->
-0.03166242401262384 -> -0.021340729420569155`; every signed step is wrong.
P4 is false (`results.json:809-843,881-898`).  Thus M2 is rejected on the blur
arm as required.

## 5. Reproduction

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M167-detail-battery\commission.py --checker-only
python -B experiments\M167-detail-battery\commission.py
```

**MEASURED environment:** Python `3.12.10`, NumPy `2.4.4`, SciPy `1.17.1`,
one numerical thread, zero captures opened (`results.json`, each measurement's
`environment` object).

**VERIFIED repeatability and external contract.** Two identical full runs
produced the same `results.json` SHA-256,
`4843990388867C6F4393A39302F34FF692872BBB158BD17C0204EA16ED9F7EA0`.
Passing the serialized oracle back through `commission.py --input` exited `0`;
passing serialized M2 exited `1`.

## 6. Scope and consequences

- **VERIFIED:** this battery can accept its construction-truth oracle and
  reject all three required dead instruments.
- **VERIFIED:** working degradation/sabotage controls alone do not rescue an
  instrument.  M2 and D8 each pass some directional controls while failing an
  adversarial opposite-direction arm.
- **NOT ESTABLISHED:** that any deployable instrument can pass.  In particular,
  amendment 1's non-separability result makes a single-image high-frequency
  candidate unlikely to survive P5 without an independent reference, physical
  constraint, or explicit refusal.
- **NOT ESTABLISHED:** physical false-accept/false-refusal rates.  This battery
  is synthetic and small by design; later physical commissioning still needs
  independently registered targets, calibration and provenance.
- **ASSUMED for future candidates:** their adapter is frozen independently,
  exposes only declared observations, and does not branch on M167 arm identity.
  The checker cannot prove those provenance facts from score JSON alone.

No M164, proposal, status, owner-action, capture, or product implementation file
was modified.
