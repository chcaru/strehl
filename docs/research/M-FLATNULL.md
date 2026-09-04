# M-FLATNULL — real flat-target commissioning of M8-O

**Final verdict: the registered noise-rise failure was not observed, but M8-O
is not commissioned as a general comparative invention/detail axis.** It is
sensitive to a downstream unsharp mask, yet it reads materially nonzero on
every flat-target arm. On the clean 6-second arm, 97.827% of inset violations
are a representation false positive: the output is encoded at 65535 while the
entire independently reconstructed normalized source hull lies above
`1+tolerance`. The census is literally detecting an outside-hull value, but
the cause is output clamping rather than invented detail.

The result is development evidence, not a scorecard result. No holdout was
opened.

## Registered questions and blindness

Predicates were frozen at `736915d9` before any new target output:

1. the 6-second flat null is material at inset M8-O `>=0.0100%`, or at least
   64 distinct pixels with at least 16 DN excess;
2. noise sensitivity requires a strict `6 s < 2.5 s < 1 s` matched-N=60
   ordering, at least `0.0100` percentage-point and `1.25x` clean-to-noisy
   effects, at least 40/64 increasing blocks, and a non-reversing full-N arm;
3. the fixed USM must be potent, then raise inset M8-O by at least `0.0100`
   percentage points and `1.25x` in at least 40/64 blocks.

This was not blind. The allowed `M8-COMPARATIVE.md` read exposed the prior
aggregate result, and mandatory prior-art review then exposed all three prior
per-exposure results in `M8-overshoot.md` and its committed `results.json`.
The full-N arms are therefore frozen replications. The primary exact-zero M8-O
bar predates this lane; the matched-N and downstream-USM treatments are new.

## Provenance and configuration

| item | frozen value |
|---|---|
| production source | `c88733098ffb512468a830dceb700d831dbc5c7f`, tree `076811d2` |
| M8 tool source | `76b3d9cc8b5185735d6c19d4339ce74d29e333e2`, tree `229de542` |
| instrumented binary | `strehl 0.0.0 (c88733098ffb)`, SHA-256 `7EEA0CF3...6C81273` |
| checker / injector / hook | raw-blob SHA-256 `3E6048C2...251780`, `37B7FCF6...FDFA80`, `D6DB609A...2E0D` |
| build isolation | `git -c core.autocrlf=false archive`; private source/tool snapshots and Cargo targets |
| merge | `--merge pyramid --cover scale --resampler catmull-rom` |
| environment | `STREHL_DEFECT=off`; `STREHL_PYRAMID_WORKERS=1`; `RAYON_NUM_THREADS=8` |
| output | linear u16 RGB TIFF, `3516x2344x3` |

`STREHL_WARPMAP` named an isolated sidecar for each arm. Full-N commands
omitted `--limit`; matched arms passed `--limit 60` to both `align` and
`stack`. All other defaults are fixed by the production commit.

| arm | N | cover scale | output SHA-256 prefix |
|---|---:|---:|---|
| clean full, 6 s | 65 | 0.9859 | `7884DD2B809361CE8` |
| middle full, 2.5 s | 61 | 0.9870 | `D7A1A1046BB3F6C1` |
| noisy full, 1 s | 60 | 0.9862 | `1B559A76D7ADC332` |
| clean matched | 60 | 0.9866 | `9F2E782A84494DF7` |
| middle matched | 60 | 0.9870 | `9724EDA9097771C4` |
| noisy matched | 60 | 0.9862 | `1B559A76D7ADC332` |

The full-N percentages and TIFF hashes reproduce the earlier M8 run exactly.
The 60-frame noisy command is, as expected, byte-identical with and without
the explicit limit.

## Commissioning

The unchanged independent checker passed all known-answer controls:

* fractional Catmull hard step: `28/252`, 14 per sign;
* exact-copy null: `0/252`, zero copy error;
* convex bilinear null: `0/300`;
* explicit `lo/hi +/-32*tau`: exactly two, one per sign;
* independence audit: no Strehl import.

The separate USM implementation also passed before target use. Amount zero was
exact, a constant remained exact, and a `0.25/0.75` hard step changed
`6,144/196,608 = 3.125%` of samples with both signs and `9,847 DN` maximum
displacement.

The preparation gate caught two harness faults before a target render: Windows
archive line-ending conversion made an artifact hash disagree, and the
synthetic zero-inset slice was empty. A third pre-render failure caught use of
PowerShell's automatic `$input` variable. Each correction was committed before
target output. The clean evidence then completed before its marker hit a
PowerShell reflection error; the committed recovery path required every
expected evidence file and preserved rather than reran those bytes.

## P1 — clean flat null: `NULL-MATERIAL`

| region | violations / denominator | percent | lower / upper | spread |
|---|---:|---:|---:|---:|
| full output | `961,398 / 24,724,512` | **3.888441%** | `958,272 / 3,126` | — |
| 256-pixel inset | `715,477 / 16,509,984` | **4.333602%** | `713,620 / 1,857` | 64/64 blocks |

This is neither numerical dust nor the separately owned crop-boundary defect.
The run used `--cover scale`; the inset rate is higher than the full-frame
rate, and only 25.58% of violations lie outside the inset although that border
contains 33.22% of output samples.

The prior `-1.049185276` anomaly reproduces exactly. Its worst inset row is
`(x=388,y=901,channel=R)`: encoded output `1.0`, reconstructed source hull
`[2.049185276, 2.304976463]`, tolerance `9.734e-6`. The output cannot encode
that hull. The current M8-O definition therefore reports serialization's
high-rail clamp as a lower-hull violation.

A post-result descriptive cross-tab, explicitly excluded from every predicate,
finds:

* `699,932 / 715,477 = 97.827%` inset violations have
  `direction=lower`, `encoded=65535`, and `lo > 1+tolerance`;
* all three channels participate (`219,654 / 228,050 / 252,228`);
* excluding those rows leaves `15,545 / 16,509,984 = 0.094155%`,
  still material and present in all 64 blocks.

That exclusion is not a repaired M8 result. It only identifies the dominant
mechanism. The residual remains unattributed between pyramid behavior,
Catmull-Rom excursions, and other stages.

The lower-exposure arms have no output-rail samples but remain materially
nonzero in the inset: `0.060236%` at 2.5 s and `0.030963%` at 1 s, both across
64/64 blocks. Thus the exact-zero flat null fails even where the newly
identified clamp mechanism is absent.

## P2 — noise ladder: `NOISE-TREND-NOT-OBSERVED`

| exposure | full-N M8-O | matched-N=60 M8-O |
|---|---:|---:|
| clean, 6 s | **4.333602%** | **4.460053%** |
| middle, 2.5 s | **0.060236%** | **0.059903%** |
| noisy, 1 s | **0.030963%** | **0.030963%** |

These are the preregistered 256-pixel-inset rates. Every noise-falsification
condition fails in both ladders:

* ordering runs in the opposite direction;
* noisy minus clean is `-4.302639` points full-N and `-4.429090` points at
  matched N;
* noisy/clean is `0.007145x` and `0.006942x`;
* `0/64` blocks have a higher noisy than clean rate.

Equalizing frame count does not change the conclusion. This experiment does
**not** show M8-O rewarding photon noise in the registered direction. It does
show a much larger exposure/output-range confound: the clean arm's high-rail
clamp dominates the census. These three stacks therefore cannot license a
general claim of noise invariance.

## P3 — downstream USM: `SENSITIVITY-PASS`

The fixed plant was per-channel linear
`I + 1.0 * (I - Gaussian(sigma=1.0 px))`, reflect boundary, clipped to
`[0,1]`, then round-to-nearest u16.

On the clean full-N output it changed `15,166,031 / 16,509,984 = 91.859756%`
of inset samples: 7,010,566 positive and 8,155,465 negative, with
`+22,430/-20,246 DN` extrema. Newly clipped fractions were 0.345827% high and
0.000206% low, both inside the frozen 1% potency ceiling.

| reading | full output | 256-pixel inset |
|---|---:|---:|
| baseline | 3.888441% | 4.333602% |
| USM amount 1 | 11.603157% | 12.301308% |

Inset response was `+7.967706` percentage points, `2.838587x`, with increases
in 64/64 blocks. Maximum upper excess rose from `0.003703290` to `0.244272217`.
The amount-zero TIFF was byte-identical to baseline and reproduced both the
counts and violation-manifest hash. The instrument can fire; sensitivity is
not its failure.

## Licensed conclusion

M8-O's literal outside-hull census is working, but a nonzero result does not
uniquely establish invented detail:

1. final u16 clamping can itself put an encoded value outside an unclipped
   normalized source hull;
2. the rail-free flat arms are also nonzero, while this configuration includes
   a non-convex Catmull-Rom gather and a pyramid merge;
3. the strong USM response proves sensitivity, not specificity.

**Do not use current M8-O as the surviving general comparative detail axis.**
A rail-aware hull, pre-clamp output census, or frozen rail exclusion would be a
new statistic, not a reinterpretation of this one; it requires a new
preregistration and full commissioning. This lane made none of those changes.

## Integrity, load, and artifacts

Before/after manifests content-hashed every file under all three read-only
capture directories: 65, 61, and 60 files; 2,783,895,552,
2,470,408,192, and 2,307,440,640 bytes. They were identical from
`2026-09-04T04:25:34Z` through `2026-09-04T05:27:31Z`. Every arm had the
expected four sites per frame, zero coordinate-validity mismatches, no
unconsumed blocks, and complete output bracketing.

The host was deliberately shared with other lanes. Census results are
deterministic; machine load was not used to accept or reject them. No timing or
throughput result is reported.

The compact evidence record is
`experiments/M-FLATNULL/results.json`, SHA-256
`D4569AB56D646661E6205BF1BD44C272E329A36BB841E2108BE898EF5B0CFF2D`.
Raw states, manifests, logs, private snapshots, binaries, maps, and TIFFs remain
under ignored `experiments/M-FLATNULL/out/`.
