# M167 detail-instrument acceptance battery — preregistration

Status: **FROZEN BEFORE M167 EXECUTES ANY CANDIDATE**

## 1. Question and authority

M167 builds the judge, not a fourth detail statistic.  A candidate resolution
instrument is admissible only if an independently generated result record passes
every mandatory arm below.  Passing this synthetic battery is necessary, not
sufficient, for a physical resolution claim.

The checker never imports the fixture generator or candidate code.  It receives
only serialized result records from a child process.  Candidate adapters never
import the checker or its predicates.

The battery is commissioned before it may judge a new candidate:

1. one literal constructed oracle must pass every arm;
2. one-property checker sabotages must make every arm RED; and
3. all three already-dead instruments must be rejected.

If any dead instrument passes, or the oracle fails, the battery disposition is
`NOT_COMMISSIONED` and it may not issue a candidate verdict.

## 2. Candidate result contract

Every ordinary arm record is one of:

```json
{"status": "VALUE", "score": 1.25}
{"status": "LOWER_BOUND", "score": 0.50}
{"status": "UPPER_BOUND", "score": 0.10}
{"status": "REFUSED", "code": "NO_DETAIL", "reason": "..."}
{"status": "ERROR", "code": "INVALID_SHAPE", "reason": "..."}
{"status": "INVALID", "reason": "non-finite candidate output"}
```

`score` is always oriented **higher means more resolved**.  `VALUE` denotes the
closed point interval `[score, score]`; `LOWER_BOUND` denotes
`[score,+infinity)`; `UPPER_BOUND` denotes `(-infinity,score]`.  A non-finite
numeric return is `INVALID`, not a refusal.  Missing records are failures.

An external candidate supplies the same JSON object emitted by `measure.py`.
Its adapter and score orientation must be frozen and source-hashed before the
checker is run.  Candidate code is not allowed to read construction truth,
arm names, or checker predicates.  M167's built-in constructed oracle is the
only exception and is permanently ineligible as an instrument.

## 3. Independent deterministic fixtures

All ordinary candidates receive only their declared observations:

- `single_image`: one completed image;
- `repeat_pair`: two completed independent-noise observations of one scene; or
- a future explicitly preregistered reference-bearing mode.

The constructed oracle receives hidden construction labels and is not an
ordinary candidate.

The fixed fixture construction is:

- array side: `256` output pixels;
- oversampling: `4`, hence a `1024 x 1024` latent field;
- latent seed `167001`: NumPy `default_rng().standard_normal`, Gaussian-filtered
  at sigma `1.0` high-resolution pixel with `mode="reflect", truncate=6`,
  normalized to zero mean/unit population standard deviation, then mapped to
  `0.5 + 0.12*x`;
- render: Gaussian filter the high-resolution latent at
  `4 * sigma_optical` pixels with the same mode/truncation, then area-average
  each non-overlapping `4 x 4` block;
- base optical sigma `1.00` output px;
- genuinely improved optical sigma `0.55` output px;
- optically degraded sigma `1.65` output px;
- downstream noise seeds `167003` and `167004`, independent Gaussian
  `sigma=0.003`, reused across optical arms so only the registered optical
  intervention changes;
- post-render blur ladder: additional Gaussian sigma
  `[0.00, 0.50, 1.00, 1.50]` output px, applied to each completed base
  observation;
- USM: completed base image plus `0.75 * (base - Gaussian(base,1.00))`,
  same Gaussian convention, deliberately unclipped.

The flat-null fixture has no scene modulation by construction.  It is the
constant `0.5` plus the same independent downstream noise and a shared
broadband fixed pattern in both observations.  The fixed pattern uses seed
`167002`, is normalized to zero mean/unit population standard deviation, and
has sigma `0.04`.  The matched detail observation carries the same fixed
pattern and downstream noise.  This deliberately tests whether repeatable
sensor structure is mistaken for resolved scene detail.

Two fail-closed cases are supplied separately: a valid-size observation with
one `NaN`, and a one-dimensional row in place of an image.

## 4. Frozen mandatory predicates

Comparisons use the candidate's emitted intervals.  Equality never proves a
directional claim.

| ID | Arm | Frozen pass predicate |
|---|---|---|
| `P1` | Flat-ROI null | The detailed record is numeric/bounded, and the flat is either explicitly `REFUSED` with code `NO_DETAIL` or `FEATURELESS`, or its entire interval is below the detail interval: `flat.upper < detail.lower`. A generic refusal, lower bound, overlap, equality, or flat win fails. |
| `P2` | Planted improvement | Both records are numeric/bounded and `improved.lower > base.upper`. The improved render is more resolved by its registered smaller pre-sampling optical sigma, not by judgement. |
| `P3` | Planted degradation | Both records are numeric/bounded and `degraded.upper < base.lower`. |
| `P4` | Signed blur monotonicity | All four blur-ladder records are numeric/bounded and every adjacent pair obeys `next.upper < previous.lower` as added blur increases. Equality, refusal, or a rise fails. |
| `P5` | Sharpening-vs-resolution | The true-improvement record obeys `improved.lower > base.upper`, and USM either explicitly refuses with code `SHARPENING_UNSAFE` or obeys `usm.upper <= base.lower`. USM may tie or worsen; it may not be called improved resolution. |
| `P6` | Fail closed | Both non-finite and wrong-shape cases return `REFUSED` or `ERROR`. `VALUE`, either bound, `INVALID`, omission, or process success without a typed record fails. A whole candidate subprocess error is represented as `ERROR` for that isolated case and is acceptable. |

The candidate disposition is `ACCEPTED_BY_SYNTHETIC_BATTERY` only when all
`P1` through `P6` pass.  No compensation or averaging across arms is allowed.

## 5. Checker power

Before candidate adjudication, a literal all-GREEN fixture must pass.  The
checker then applies at least these one-property sabotages, each of which must
make the named predicate RED:

1. flat score equal to detail (`P1`);
2. improvement equal to base (`P2`);
3. degradation equal to base (`P3`);
4. one blur rung equal to its predecessor (`P4`);
5. USM above base (`P5`);
6. malformed input returning a number (`P6`);
7. a generic flat refusal substituted for `NO_DETAIL` (`P1`); and
8. one mandatory arm omitted.

## 6. Constructed-oracle nonempty-set control

The oracle reports the registered optical truth `1 / sigma_optical`, refuses
the no-scene flat as `NO_DETAIL`, treats post-render USM as unchanged optical
truth, uses
`1 / sqrt(1.00^2 + sigma_added^2)` for the blur ladder, and refuses both
malformed cases.  It must pass `P1` through `P6`.

This is not a candidate metric: it reads private construction labels that an
ordinary adapter is forbidden to receive.  It proves only that the conjunction
of predicates has a nonempty accepted set.

No known-good deployable resolution instrument is available as a positive
control.  M167 will say so rather than relabel the oracle.

## 7. Known-dead commissioning controls

The primary rejecting arm is selected in this fixed priority order:
`P1`, `P2`, `P3`, `P4`, `P5`, `P6`.  All failed arms are retained.

### D8 per-tile FRC

The adapter executes the surviving historical implementation
`experiments/M-PHASE0-SPLIT2/frc.py`, SHA-256
`C0408661BDDF15554BB8EC0F3D10C972D88CB632AF226C2E6944466855898288`.
`MEASURED` is a point value, `CENSORED_ABOVE` is a lower bound,
`CENSORED_BELOW` is an upper bound, and `INSUFFICIENT` is a refusal.
The shared-pattern flat is expected to prevent `P1` from establishing that
detail outranks flat; common post-render filtering may also defeat `P4`.
D8 must be rejected on at least one arm.

The historical common-mode control (`0.972099` in
`docs/research/M-PHASE0-SPLIT.md`) is corroborating provenance, not a threshold
tuned from this run.

### M137 high/low band-power gap

The adapter executes the tracked underlying `band_ratio` implementation in
`experiments/M95-coverage/src/m95cov.py`, SHA-256
`4AAE9064AD89C7846492C00EA1FC60A1965CEC3A6AB7550BF84634C9E021EC1D`,
for synthetic diagnostics.  Its decisive flat arm is the immutable historical
measurement snapshot:

- detail gap `0.3403664343410666` dex;
- flat gap `0.3488548829813006` dex;
- flat/detail ratio `1.0249391472947889`; and
- flat/detail coarse-structure share `0.13314850036584688`.

These values are bound to tracked
`experiments/M135-detail-instrument/AMENDMENT-4.md`, SHA-256
`79E257EA22103C2D0C17E84A518249BA69F61457301190BC07EBFB43CAEDB5EB`,
and `docs/research/M135-detail-instrument.md`, SHA-256
`9BA4CA24C9DAB0656A2DD6F8CC3F9F3AF6225D291BE21180F2D733627D8689AA`.
The original RAW is not copied into M167.  The adapter must reproduce the
snapshot arithmetic exactly and be rejected by `P1`.

### M2 `R_box9`

The adapter faithfully reimplements
`population_sd(image / uniform_filter(image,9) - 1)` from
`experiments/M159-noise-clause/measure.py`, SHA-256
`6109FAFFF52F3C287DE2DEACC57B76843215D72CA4AD155E3BBB92BC4F057DA9`.
Because lower residual was the instrument's favourable direction, its
higher-is-better battery score is the negative residual.

It also replays M159's seed-159, 384-square specificity construction, including
the preceding 128 commissioning trials that advance the RNG.  The reconstructed
`R_box9(blurred) / R_box9(unblurred)` must be within `1e-9` of the frozen
`0.5712148772282098` in
`experiments/M159-noise-clause/results.json`, SHA-256
`5EBA810719313ECD85116E268965FE699C43E0EA32BC4D43B6354FDE8DD30389`.
M2 must be rejected, and `P4` must be one of its failed arms.

## 8. Disposition and reporting

The battery itself is commissioned only if:

- the checker passes its all-GREEN fixture and catches every sabotage;
- the constructed oracle passes all six predicates;
- D8, M137 band power, and M2 are each rejected;
- D8 is rejected by `P1`;
- M137 is rejected by `P1`; and
- M2 is rejected by `P4` with its reconstructed blur ratio reported.

Any deviation is a battery failure, not permission to weaken a predicate.
M167 opens no RAW/capture and makes no claim that a sound single-image detail
instrument exists.

## 9. Pre-execution implementation bindings

This section was added and committed before the first candidate execution.  It
closes adapter choices that the sections above did not spell out:

- D8 uses one centered `256 x 256` tile, the historical `1/7` threshold,
  minimum ring population and three-adjacent-ring classifier exactly as loaded
  from the pinned `frc.py`.  No last-bin fallback is enabled.
- The M137 synthetic diagnostics call the pinned `band_ratio(image, 1.0)`;
  only the exact historical detail/flat gap snapshot determines its `P1`
  verdict.
- M2 scores each ordinary single-image arm as
  `-population_sd(image / uniform_filter(image,9) - 1)`.  No epsilon, clipping,
  finite-value replacement, or denominator repair is permitted.
- A candidate's two malformed cases are isolated calls.  Exceptions become
  typed `ERROR` records; a returned non-finite scalar becomes `INVALID`.
- The child measurement process emits JSON on stdout.  The checker invokes it
  once per built-in candidate with numerical thread environment variables set
  to one, then adjudicates only that serialized JSON.
