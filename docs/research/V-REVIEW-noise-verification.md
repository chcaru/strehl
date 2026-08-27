# V-REVIEW: independent verification of the noise head-to-head

Adjudicating `docs/research/M127-noise-head-to-head.md`, the claim the project's
state-of-the-art case now rests on. Written under this project's rule that an
author never verifies their own work. No module of the original was imported;
the estimator was re-implemented from the written method in
`experiments/V-NOISE/PREREGISTRATION.md` and re-derived on the same images.

Every number below is labelled MEASURED, DERIVED or ARGUED.

## 1. Verdict

**The noise claim is CONFIRMED. The argument offered in its support is not.**

The measured half of M127 survives independent re-implementation without
qualification. All six of its shift-corrected ratios fall inside 95% intervals
computed by code that shares no line with it. strehl is quieter than `enfuse`
and than `focus-stack` in luma and in both chroma channels, and the direction is
bounded away from parity in every channel.

The *reasoning* M127 attaches to that result in its section 5 does not survive.
The "lowest noise and highest scene content in the same tiles" pairing is not
two findings. It is one measurement and an algebraic rearrangement of it, and
the ordering it reports reverses under a gauge choice M127 leaves open.

Partition of the five items assigned, summing to five:

| item | outcome |
|---|---|
| 1. re-derive the estimate independently | **confirmed**, within 2.0% on two arms and 5.0% on the third |
| 2. attack the pairing | **refuted**, the scene column is an identity |
| 3. check the survivor for cancellation | **no cancellation**, but a blind spot confirmed |
| 4. commission on my own arm and image | **passed** after I corrected my own prediction |
| 5. check comparator fairness | **fair**, with one mis-applied correction found |

## 2. Item 1, independent re-derivation

Implemented from the method, not the code: per tile, per channel, normalised by
that tile's own mean luma, on linear Rec.709 opponent channels.

    flat-ROI   sigma = std(x - uniform_filter(x, 9)) / mean_luma
    half-diff  sigma = sqrt(0.5 * var(A - B)) / mean_luma

The tile census was read as data only. MEASURED, medians over 110 flat tiles:

| arm | M127 raw luma | mine | agreement |
|---|---:|---:|---:|
| strehl | 0.07859 | 0.08017 | 1.020 |
| `enfuse` | 0.08394 | 0.08570 | 1.021 |
| `focus-stack` | 0.09953 | 0.10141 | 1.019 |

Three independent implementations of a normalised standard deviation landing
within 2.1% of each other is a confirmation. The residual is accounted for by
`enfuse` writing **RGBA**, where the fourth plane is 1.0 everywhere: a loader
that averages over the last axis reads 0.26051 instead of 0.01401, an 18.6x
corruption. My loader drops it. So does theirs.

## 3. Item 4, commissioning, including a defect of my own

The pre-registration fixes NULL at 1.000 +/- 0.005 and POTENCY within 10%.
MEASURED on the arm and image actually used, not carried across from
`coffee-bubbles`:

| control | measured | predicted | error | outcome |
|---|---:|---:|---:|---|
| NULL, image against itself | 0.00000000 | 0 | exact | pass |
| POTENCY 0.5x | 0.08476 | 0.08469 | 0.08% | pass |
| POTENCY 2.0x | 0.13914 | 0.13830 | 0.61% | pass |
| POTENCY 4.0x | 0.24251 | 0.23955 | 1.24% | pass |

**My first potency run failed at 2.0x with 21.78% error, and the defect was
mine.** I predicted `sqrt(s0^2 + sadd^2)`. Noise planted into one half of a
half-difference contributes only half its variance, so the target is
`sqrt(s0^2 + 0.5*sadd^2)`. DERIVED, and confirmed by three levels agreeing to
within 1.24% once corrected.

The instructive part is the 0.5x arm. Against the wrong formula it read 5.01%
error and **passed**, because the missing factor is small when the plant is
small. A single-level commissioning would have certified a wrong prediction.
Two levels were pre-registered and the second level is what caught it.

## 4. Item 5, is the comparison fair

MEASURED. Both comparators load from one shared 63-frame aligned tree,
`C:\dev\strehl-out\V-LINEAR2\aligned`, named directly in
`logs/coh-fs15-A.log`. Range fairness, with the arithmetic corrected as noted in
section 7:

| arm | dtype | planes | max | of range | mean |
|---|---|---:|---:|---:|---:|
| strehl | uint16 | 3 | 65535 | 100.0% | 0.0252 |
| `enfuse` | uint16 | 4 | 65535 | 100.0% | 0.0270 |
| `focus-stack` | uint8 | 3 | 255 | 100.0% | 0.0266 |

No arm is clipped, floored or exposure-penalised; the three means agree within
7%. `focus-stack` emits 8-bit because the tool emits 8-bit, which is why a
quantisation penalty has to be removed before its ratios read as an algorithm
comparison. The 8-to-8-bit identity control passes exactly in all three
channels, so my requantiser adds nothing of its own.

**But M127 does not apply the penalty it measured.** MEASURED, by dividing its
own published columns:

| channel | penalty M127 states | factor M127's table actually divides by |
|---|---:|---:|
| luma | 1.124 | 1.093 |
| R-Y | 1.333 | 1.090 |
| B-Y | 1.548 | 1.131 |

My own requantisation measures 1.167, 1.390 and 1.596, close to what M127
*states*. On chroma its correction is applied at roughly a quarter of the
measured size. Applying the measured penalty to my raw ratios gives 1.088,
1.623 and 1.627 against M127's published 1.161, 2.028 and 2.237. **The error
runs in strehl's favour and the published chroma advantage over `focus-stack`
is overstated by about 0.4 to 0.6x.** The direction of the finding is unchanged;
its size is not.

## 5. Item 2, the pairing, refuted

M127 section 5 argues strehl cannot merely be blurrier because it reads lowest
noise **and** highest scene content, calling the scene column a different
statistic. MEASURED, by recomputing `sqrt(flat^2 - noise^2)` from its own two
published columns:

| arm | scene as published | `sqrt(flat^2 - noise^2)` |
|---|---:|---:|
| strehl | 0.12151 | 0.12151 |
| `enfuse` | 0.10682 | 0.10681 |
| `focus-stack` | 0.09247 | 0.09247 |

The scene column is an algebraic rearrangement of the other two to five
significant figures. At a fixed total it is a strictly decreasing function of
the noise term, so "lowest noise" and "highest scene" are **one finding stated
twice**. It cannot corroborate itself.

A second separation with different failure modes, holding the total fixed and
varying only how the noise term is gauged. MEASURED:

| treatment | strehl | `enfuse` | `focus-stack` | highest |
|---|---:|---:|---:|---|
| raw noise | 0.11522 | 0.11272 | 0.12024 | `focus-stack` |
| shift-corrected noise | 0.12979 | 0.11272 | 0.12024 | strehl |
| corrected, depth-scaled | 0.13509 | 0.12798 | 0.14000 | `focus-stack` |

strehl reads highest under one treatment of three. The third assumes noise falls
as one over root N between the 31-frame half the noise term is measured on and
the 63-frame full stack the total is measured on; M127 section 6 states that
scaling is unmeasured, so this row is a sensitivity test rather than a result.
That is the point: **an unmeasured choice moves the conclusion.**

**This does not damage the noise claim.** The ratios in section 6 are direct and
carry no scene term. It removes one of the two legs section 5 stands on. The
other leg, the level sharpness result of 0.977 with interval 0.810 to 1.181 in
`docs/research/V-LINEAR2.md`, is an independent measurement of detail and is
untouched by this. **The anti-blur defence should rest on that leg alone.**

## 6. Item 3, cancellation, and one gauge question resolved

M127 withdrew its pre-registered primary after it read two arms differing 19% in
noise as 0.13585008 against 0.13585464. I looked for the same disease in the
survivor and did not find it: the half-difference has no numerator and
denominator that can cancel, and the potency series above shows it tracking a
known plant across an 8x range to within 1.24%.

It does have a **blind spot**, which M127 states as a virtue. MEASURED, by
planting a fixed deterministic pattern identically into both halves and into the
full stack:

| term | before | after | change |
|---|---:|---:|---:|
| half-diff noise | 0.08017 | 0.08017 | 0.00% |
| flat-ROI total | 0.14018 | 0.22119 | +57.79% |
| derived scene | 0.11500 | 0.20615 | +79.26% |

A reproducible artifact is invisible to the noise term and lands **entirely** in
the derived scene term, where nothing distinguishes it from detail. This is the
mechanism behind section 5's refutation: a high scene term is equally consistent
with "it stamps something into every frame".

**One criticism I formed and then withdrew on measurement.** M127's section 2
table pairs strehl's shift-corrected figure with the comparators' raw ones, and
I recorded that as cross-gauge. It is asymmetric, but MEASURED it is not unfair:
the median best integer offset is 1.41 px for strehl and **0.00 px for both
comparators**, and correcting them moves their numbers by +0.0%. The mechanism
is in the logs: both comparators draw their halves from one pre-aligned raster,
while strehl aligns internally on each run, so only strehl's halves sit on
different rasters. That offset is an artifact of the half-split design and does
not exist in the shipping product, which aligns all 63 frames once. The
corrected figure is the right one to quote. **The defect that remains is
presentational**: section 2 does not tell the reader one column is corrected,
and the fact that makes this harmless is not stated there.

The shift search got its own control, an arm that cannot contain a real offset:
two independent noise fields, where the same 49-candidate search moved the
statistic by **-0.43%**. MEASURED. The search is not fitting noise.

## 7. Two defects in my own instrument, disclosed

Both were caught by me, both are corrected above, and neither changes a reported
number. They are recorded because this project treats an undisclosed self-error
as worse than a wrong result.

**A label asserting a statistic the code did not compute.** `vn_scene.py`
printed the header `BOOTSTRAP ... 2000 resamples` over a column headed
`[95% CI]`, above a body that built a five-element throwaway list and printed
the point value. No interval existed. This is the same defect class as a control
named in prose and implemented as a filename parse: the part everyone reads
described something the predicate did not do. The intervals in section 8 are
computed.

**An overflowed percentage presented as a measurement.** `vn_boot.py` computed
`100 * a.max() / full` on a numpy uint16 scalar. `100 * 65535` wraps, and the
line reported a full-range image as "1.0% of range". The conclusion I drew from
it was correct and the number supporting it was not, which makes it an argued
conclusion wearing a measured number's clothes. Recomputed in float in section 4.

## 8. The interval that decides it

MEASURED. Ratio of medians, comparator over strehl, 2000 tile resamples,
percentile interval, both arms shift-corrected on one gauge:

| comparator | channel | mine | 95% interval | M127 | inside |
|---|---|---:|---|---:|---|
| `enfuse` | luma | 1.618 | 1.510 to 1.708 | 1.540 | yes |
| `enfuse` | R-Y | 1.813 | 1.716 to 1.967 | 1.763 | yes |
| `enfuse` | B-Y | 1.606 | 1.527 to 1.703 | 1.538 | yes |
| `focus-stack` | luma | 1.915 | 1.811 to 2.003 | 1.898 | yes |
| `focus-stack` | R-Y | 2.408 | 2.314 to 2.596 | 2.371 | yes |
| `focus-stack` | B-Y | 2.586 | 2.475 to 2.758 | 2.532 | yes |

Every published value lands inside an interval from an independent
implementation, and every interval is bounded away from parity on the low side.

**What ORCH may say.** That strehl is measurably quieter than both open-source
comparators at equal detail, by roughly 1.5 to 1.8x against `enfuse` in all
three channels. **What ORCH should stop saying.** That strehl shows more scene
content as well; that is the same measurement counted twice. And the
`focus-stack` chroma figures should be restated at about 1.6x rather than 2.0 to
2.2x once the penalty M127 measured is applied at the size it was measured.

## 9. What is not verified

- The comparison is a **shadow-noise** comparison. The 110 tiles are the dark
  quartile, median tile mean luma 0.01304 linear. MEASURED. Nothing here
  measures midtone or highlight noise, and M127 says so.
- One subject, one stack. Six ratios from 110 tiles of one image are not a
  corpus result.
- All statistics here are purely spatial. **No frequency transform is taken**,
  so the formally withdrawn statistic above 0.30 cyc/px does not apply to any
  number in this document.
- I did not verify that the aligned tree is byte-identical to what strehl itself
  consumed, and it is not: strehl reads the linear frames and aligns internally,
  while the comparators read a Hugin-resampled copy at 7029 px against strehl's
  7032 px. That resampling correlates noise, which would flatter the
  comparators on this statistic rather than penalise them, so it does not
  threaten the direction of the result. Its size is unmeasured.

## 10. Scripts

All under `experiments/V-REVIEW/`, none importing anything from
`experiments/V-NOISE/`.

| script | what it does |
|---|---|
| `vn_probe.py` | shapes, dtypes, ranges, census contents; found the RGBA plane |
| `vn_half.py` | the independent re-derivation of the estimator |
| `vn_comm.py` | commissioning, quantisation penalty, alpha control |
| `vn_shift.py` | corrected potency, selection-bias null, one-gauge ratios |
| `vn_scene.py` | the three attacks on the pairing |
| `vn_boot.py` | bootstrap intervals |
| `vn_fair.py` | comparator input and range fairness |
