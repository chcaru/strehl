**VERDICT: Candidate 2 DOES NOT CLEAR blocker (a).**

Candidate 2 really does resolve both synthetic optical arms in the correct
direction. That result survives my choice audit. It still does not furnish the
program with an admissible comparative-detail instrument: the optical plant
supplies the target intervention, the existing captures cannot instantiate the
registered target task, the no-target control emits an unqualified numeric
reading, and the frozen M55 contract rejects it at B0 before most batteries can
lawfully run.

## Rule-40 prior-art search

**MEASURED.** I ran, before the M131 measurements:

```powershell
python experiments\ORCH-drift-check\prior_art.py detail metric detectability hotelling sharpness
```

It exited `0`. The complete output is
`experiments/M131-cand2-ruling/prior-art.txt`.

The headline reports it surfaced were:

1. `M46-detail-metric-measured.md`
2. `M99-photometric.md`
3. `M39-verify-detail-metric.md`
4. `M55-acceptance-spec.md`
5. `M55-sigpow-verification.md`
6. `M57-detail-metric-from-first-principles.md`
7. `BUILD-SHARPMETRIC.md`
8. `M93-election-gate.md`
9. `M98-gate-adjudication.md`
10. `M95-merge-vs-frame-sharpness.md`

It additionally named `ORCH-veiling.md`, `M87-occlusion.md`,
`M116-promotion.md`, `M41-r3-kill-measured.md`, `BUILD-TRIAGE.md`, and
`BUILD-SHARP.md`.

I read the required `M-CAND2.md`, `M55-sigpow-verification.md`,
`M55-acceptance-spec.md`, `M46-detail-metric-measured.md`,
`M57-detail-metric-from-first-principles.md`, `M92-null-averaging.md`, and
`M95-merge-vs-frame-sharpness.md`. There is no
`docs/research/M95-sharpness.md`; the last file is the actual M95 report
surfaced by rule 40.

The controlling prior-art lesson is not that Candidate 2 belongs to the dead
`C/(C+U)` family. It does not. The controlling lesson is that a statistic must
own a lawful target, a null, a failure direction, and a natural-data execution
contract before an optical sign on a supplied plant can become an instrument
(`docs/research/M55-sigpow-verification.md`;
`docs/research/M57-detail-metric-from-first-principles.md`;
`docs/research/M92-null-averaging.md`).

## Killer 1 — synthetic, signal-linear optical arms

**VERDICT: THE SYNTHETIC RESULT IS VALID, BUT IT DOES NOT TRANSFER. THIS
KILLER BLOCKS CLEARANCE.**

### The published numbers are real

**MEASURED.** I hash-checked the stored held-out score arrays and re-scored
them under settings that do not merely repeat the published summary
(`experiments/M131-cand2-ruling/synthetic-choice-audit.json`):

| Arm | Frozen native ratio | Four task ratios | Block-jackknife 95% interval |
|---|---:|---|---|
| Blur | `0.2779204536` | `0.1942, 0.3505, 0.3074, 0.2873` | `[0.2357, 0.3198]` |
| Improvement | `2.4627494970` | `2.4184, 2.6240, 2.5125, 2.2647` | `[2.1392, 2.7856]` |

Display-referred values give the same dispositions. All four balanced macro
subsets retain the sign:

- blur: `0.2536` to `0.3027`;
- improvement: `2.3948` to `2.5337`.

Arithmetic mean, median, minimum, maximum, even/odd macros, first/second
macro halves, native/display mappings, and leave-one-acquisition-block-out
scoring all agree. An exact-copy plant and an improvement deliberately
mislabelled as blur are both rejected by the direction checker. The optical
effect is not an arithmetic accident.

### The null exposes a choice point, but not enough to explain the arms

**MEASURED.** Eight independent same-optics, same-task noise realisations
compared to the historical baseline gave a ratio
`0.946779 +/- 0.016498 SE`, range `[0.887946, 0.997830]`. All eight falling
below one shows that privileging one baseline realisation is itself a nuisance
choice.

**MEASURED, POST-RESULT DIAGNOSTIC.** Pairing those eight independent null
realisations without the historical baseline gave geometric mean `1.045040`,
log-ratio SE `0.025780`, and 95% interval `[0.993548, 1.099201]`, which includes
unity (`experiments/M131-cand2-ruling/null-rechoice.json`). This pairing was
chosen after seeing the baseline shift and is disclosed as such. It changes no
gate. Either null treatment is far from explaining ratios `0.278` and `2.463`.

### Why the plant tends to produce the registered answer

**MEASURED.** In `cand2.py`, the optical sigma is applied only to the injected,
band-limited target. The natural background nuisance is left unfiltered, and
fresh arm-specific noise is drawn after the target filter
(`experiments/M-CAND2/src/cand2.py:256-335,338-435`).

**DERIVED.** Candidate 2 estimates

```text
d'^2 = d' K^-1 d
```

from a zero-target covariance `K` and a target derivative `d`. In the optical
plant, the intervention deliberately changes `d` while leaving the nuisance
construction and expected noise covariance substantially fixed. A stronger
target transfer therefore has a built-in route to larger detectability; a
weaker target transfer has a built-in route to smaller detectability.

That is a legitimate commissioning plant for this narrow supplied task. It is
not a model of the full physical intervention:

- real optics filter all scene structure, not only the investigator's target;
- photon variance is signal-dependent and is drawn after the optical image;
- a natural scene does not supply known symmetric target labels;
- focus density changes contributor selection, registration, and covariance,
  not only one additive target template.

The inputs that make the result differ are already demonstrated. Setting the
target to zero produces the flat-null behavior reported below. Applying one
invertible linear operator to the complete realised observation produces
Candidate 2's exact congruence equality, as its USM arm showed. The optical
fixture is between those cases because it filters only the supplied target.

**Rule-18 failure direction.** This plant can flatter optical sensitivity in
the expected direction: it changes the labelled signal while withholding
several covariance changes that occur in a real capture. Finite arm-specific
noise can move a ratio either way, as the same-optics null shows.

**RULING.** The synthetic optical signs are commissioned for the synthetic
forward model only. A real-photon task is necessary, not confirmatory.

## Killer 2 — can Hotelling \(d'^2\) license comparative detail?

**VERDICT: YES IN A NARROW TASK-BASED EXPERIMENT; NO FOR CANDIDATE 2 ON THE
AVAILABLE NATURAL RENDERS. THIS IS THE DECISIVE KILLER.**

### What the statistic can lawfully say

**ARGUED.** For each system under comparison, a Hotelling observer may be
given the same externally defined physical task:

```text
zero-target observations -> K
separate +theta/-theta observations -> d and midpoint
held-out +theta/-theta observations -> tested d'^2
```

Comparing the resulting `d'^2` values can then license:

> Under this registered target, band, capture regime, and output support,
> system A provides higher target detectability than system B.

That is a valid comparative-detail statement for the task. It is not a generic
natural-image sharpness scalar, a resolution cutoff, or proof of more
information for arbitrary scene structure. Candidate 2 itself refused an NEQ
interpretation because stationarity was not established
(`experiments/M-CAND2/PREREGISTRATION.md`).

### Why dense and sparse cannot be used as the classes

**DERIVED.** `tilted-sw4` and `tilted-sw10` are the two acquisition systems.
Each system would separately need the same `+theta/-theta` task. If dense and
sparse are instead called the two classes, the derivative is the
cross-capture difference and

```text
d'^2(dense, sparse) = d'^2(sparse, dense).
```

It measures distinguishability, not which system preserved more detail.

**MEASURED.** An executable class-swap test returned exactly
`0.26719151383825196` in both directions, with zero floating-point difference
for every task
(`experiments/M131-cand2-ruling/m55-audit.json`). Exposure, tone, IBIS,
registration, scale, fixed pattern, focus coverage, or real detail can all
make the captures distinguishable. The square has no direction with which to
separate them.

Defining labels from the dense output would let the candidate define its own
truth. Digitally injecting Candidate 2's old templates into the completed
renders would only repeat the synthetic supplied-target experiment; it would
not show that natural detail survived the acquisition or merger.

### The registered streams do not exist in the current session

**MEASURED.** Candidate 2's executable input is an `ObservationSet` containing
independent covariance, derivative-plus, derivative-minus, test-plus, and
test-minus arrays. It uses four tasks, `p=256`, five held-out acquisition
blocks, 96 sites per block, and 384 covariance sites per fold
(`experiments/M-CAND2/src/cand2.py:73-97,338-435,550-641`).

The calibration-slide session supplies:

- one 182-frame dense sweep of one natural target state;
- one 92-frame sparse sweep of that state;
- no physical symmetric target alternatives within either sweep;
- no matched zero-target population for either tilted acquisition;
- no separate derivative and held-out target acquisitions; and
- one acquisition per density, not five independent acquisition blocks.

The three flat stacks are no-target/noise controls, not the missing target
alternatives. They also have different exposure-dependent noise distributions
and cannot be pooled into Candidate 2's covariance.

No traceable slide design committed with these captures supplies the missing
paired motifs. Even if it did, this exact estimator would still need separate
zero-target, derivative, test, and acquisition-block roles. Spatial patches
from one sweep cannot be renamed as independent acquisition blocks.

### Candidate 2 is also already closed on mandatory tone arms

**MEASURED.** Potent gamma-3 and logistic arms moved the display-referred
statistic to `R=0.502893` and `R=0.486741`, respectively. The frozen downstream
gate records `candidate_status: DEAD`, `eligible: false`
(`experiments/M-CAND2/out/amendment-gamma3.json`;
`experiments/M-CAND2/out/amendment-logistic.json`;
`experiments/M-CAND2/out/amendment-downstream-gate.json`).

Those transforms did not create a false win; they nearly halved the reading.
That is still fatal to a comparative instrument whose tone contract is not
identical across outputs. The scorecard requires a replacement to refuse
gamma and logistic challenges, not merely rank the optical plant correctly
(`docs/proposals/2026-09-sota-scorecard.md:563-577`). An external PCHIP
linearisation would define a successor and require a new freeze and complete
commissioning; it cannot retroactively rescue Candidate 2.

**Rule-18 failure direction.** With dense/sparse as classes, any stable
cross-capture difference fools `d'^2` upward, and class swapping cannot reveal
the error. With a lawful task, a target or covariance mismatch between systems
can move the comparative ratio in either direction.

**RULING.** Hotelling task detectability is not intrinsically disqualified.
Candidate 2 is disqualified for the program's present use because no lawful
natural-render task is available and creating one changes the experiment.

## Killer 3 — confirmation-pair confounds

**VERDICT: THE PAIR CANNOT CONFIRM CANDIDATE 2. THE TAIL DOES NOT EXPLAIN A
FALSE DENSE WIN ON THE MEASURED GRID; COVERAGE AND IBIS/GEOMETRY STILL FAIL.**

### Metadata facts independently reproduced

**MEASURED.** ExifTool and forced directory enumeration reproduced all three
focus histograms exactly
(`experiments/M131-cand2-ruling/capture-metadata-audit.json`):

```text
tilted-sw4                 182: 57 x76, 58 x80, 59 x26
tilted-sw10                 92: 57 x38, 58 x40, 59 x14
very-tilted-all-axis-sw10  197: 56 x10, 57 x40, 58 x40,
                                59 x41, 60 x40, 61 x26
```

The sw4/sw10 bucket ratios are exactly `2.000`, `2.000`, and `1.857143`.
All six high-resolution-slide stacks report image stabilisation on.

I did not infer physical converter identity from metadata. `LensModel` and
maker-note `LensType3` both format as Sony protocol identity on every frame;
the physical Viltrox identity remains owner testimony. I also did not use
`ReleaseMode`: ExifTool formats every frame as `Exposure Bracketing`, while the
owner-confirmed operation was focus bracketing.

### Image-derived coverage, not encoder bins

**MEASURED.** I decoded only `raw_image_visible`, copied both sampled green
planes inside each LibRaw context, and used a fixed non-overlapping 8-by-8 grid.
Two independently chosen focus coordinates were evaluated: normalized
Tenengrad and normalized Laplacian variance. They locate through-focus maxima;
they are not used as detail scores
(`experiments/M131-cand2-ruling/focus-coverage-audit.json`).

The stacks are strongly density matched in image space:

| Coordinate | sw4 index from sw10 slope | Peak-rank correlation | Mapping residual |
|---|---:|---:|---:|
| Tenengrad | `1.99778` | `0.999666` | `0.908` sw4 frames RMS |
| Laplacian | `2.00014` | `0.997707` | `2.372` sw4 frames RMS |

That is much stronger evidence than equal EXIF endpoints.

It is not a 64-peak pass. At prominence thresholds `1.02`, `1.05`, and `1.10`,
only **63 of 64** sites have an interior peak in both metrics and both stacks.
The same edge site is the problem: its curve reaches the opening boundary.
The exact 64-site claim therefore fails rather than being rounded up.

**Rule-18 failure direction.** Tenengrad and Laplacian can be raised by noise
or edge contrast. Here they are used only to locate a maximum under matched
ISO/exposure and must agree; they do not license a detail comparison.

### The unmatched tail

**MEASURED.** Neither focus coordinate placed any of the 64 grid maxima in the
last 26 sw4 frames or last 14 sw10 frames. Thus the `26/14` mismatch has no
observed route to manufacture a dense advantage on this grid.

**DERIVED.** Relative to exact two-for-one sampling, the dense arm is short two
tail frames (`26` rather than `28`). If a lawful target peak occupied that
tail, the direct bias would be against the dense arm: it would omit dense
samples. If the two physical endpoints differ rather than merely their
sampling counts, the sign becomes indeterminate. Because Candidate 2 has no
lawful target sites here, I do not generalise the grid result to an unobserved
task.

### IBIS and cross-capture geometry

**MEASURED.** Adjacent-frame phase correlation found image-motion increments
of:

- sw4: `4.052` raw pixels RMS; detrended residual `0.589` raw pixels RMS;
- sw10: `4.201` raw pixels RMS; detrended residual `0.571` raw pixels RMS.

The cumulative horizontal spans were approximately `700` and `340` raw
pixels. Those spans include focus breathing and other smooth camera/lens
motion; the residual is not a unique estimate of IBIS. The result establishes
that the two sweeps have separate motion histories, not which mechanism made
each displacement.

Existing image-derived production maps already fail the stronger input-only
gate:

- full sw4 `k=0.9676287512`;
- endpoint-preserving 92-frame sw4 subset `k=0.9676287512`;
- independent sw10 `k=0.9652763795`;
- subset-versus-independent difference `0.00235237`, above the registered
  `0.0010` limit;
- held-out map errors `8.6621 px` and `12.0952 px`, both above the product's
  `4 px` usability threshold
  (`docs/research/cover-default.md:590-599`).

Fitting a local warp from scored detail would leak the outcome. The
within-capture full-sw4 versus frozen 92-frame subset is the cleaner density
diagnostic because it shares one motion trajectory, but it still lacks the
physical target streams and fails the strict 64-site coverage gate. The
cross-capture sw4/sw10 comparison adds an inseparable IBIS/geometry
intervention.

**Rule-18 failure direction.** Independent geometry can raise or lower
detectability. Residual misregistration usually reduces a matched task, while
stable capture-specific structure can increase class distinguishability.
There is no one-sided correction.

**RULING.** The pair is useful development evidence for focus-density and
geometry work. It is not a Candidate 2 confirmation arm and cannot clear
blocker `(a)`.

## Flat-ROI control

**VERDICT: FAIL.**

This was M131's first measurement, run before any M131 RAW decode
(`experiments/M131-cand2-ruling/flat-control.json`).

The input had spatially constant per-channel backgrounds, Candidate 2's frozen
five blocks, 96 sites per block, `p=256`, four nominal tasks, independent
covariance/derivative/test noise streams, and **target amplitude exactly
zero**.

Across 16 independent repetitions:

| Quantity | Result |
|---|---:|
| Status | `NUMERIC` in `16/16` |
| Mean null \(d'^2\) | `0.0030320 +/- 0.0005553 SE` |
| Range | `[0.0010202, 0.0092096]` |
| Accuracy | `0.499382 +/- 0.001414 SE` |

The near-chance accuracy correctly says there is no target. The squared
finite-sample mean separation nevertheless produces a strictly positive
`d'^2`, and Candidate 2 emits it without a `NO_TARGET` status or an absolute
null calibration. Forming ratios from the 16 null values gives 240 ordered
ratios spanning **`0.1108` to `9.0270`**. A flat arm can therefore appear nine
times “better” solely from a near-zero denominator.

The test had power. Restoring the registered target amplitude `0.0045` gave
mean `d'^2=32.6748 +/- 1.8618 SE`, range `[29.4409, 38.0079]`; every power
reading exceeded every null reading. A planted checker mutation that accepted
finite numeric zero-target results was caught.

**Rule-18 failure direction.** Squaring a finite-sample class separation biases
the no-target reading upward. Ratios between two such readings can fail in
either direction according to which near-zero estimate becomes the
denominator.

Candidate 2 could be extended with a frozen absolute null, power test, and
typed refusal. That extension is not present in the candidate under ruling.

## Candidate 2 against the M55 acceptance battery

**VERDICT: REJECTED AT B0; B4/B5-STYLE NULL DISCIPLINE ALSO FAILS; THE OTHER
BATTERIES CANNOT BE INSTANTIATED WITHOUT A SUCCESSOR.**

I applied the executable M55 B0 declaration checker directly to Candidate 2
as shipped, not to an adapter
(`experiments/M131-cand2-ruling/m55-audit.json`).

Candidate 2 has no `value(a,b,ctx)` entry point. Its public computation is
`crossfit(ObservationSet, arm, macro_limit)`. B0 reported all ten required
fields missing:

```text
name, version, consumes_calibration, uses_ground_truth,
declared_range, no_claim_floor, decision_threshold,
failure_direction, nuisances, property_tests
```

The battery disposition is:

| Battery | M131 disposition | Reason |
|---|---|---|
| B0 declaration | **FAIL** | No M55 candidate contract or executable pairwise property test |
| B1 true-resolution monotonicity | **NOT INSTANTIABLE** | M55 supplies a natural half-merge pair; Candidate 2 needs five labelled observation streams per system |
| B2 homogeneity/swap | **NOT INSTANTIABLE** | No `value(a,b)`; dense/sparse class swapping leaves \(d'^2\) exactly unchanged |
| B3 nuisance leverage | **NOT INSTANTIABLE** | No lawful natural-output reading to perturb |
| B4 specificity/sensitivity | **FAIL, ANALOGOUS EXECUTION** | The zero-target plant emitted `NUMERIC` in 16/16 |
| B5 sign/range/denominator | **FAIL** | No declared status/range and the no-target ratio denominator is not bounded away from zero |
| B6 held-out real data | **NOT INSTANTIABLE** | Held-out cells do not supply Candidate 2 target/covariance/derivative/test populations |
| B7 stability | **NOT INSTANTIABLE** | A repetition sweep first needs a lawful reading; null ratios already span 0.11–9.03 |
| B8 calibration sensitivity | **NOT INSTANTIABLE** | No M55 calibration declaration; perturbing the supplied synthetic constants audits the plant |
| B9 roll-null | **NOT INSTANTIABLE** | The roll-null calls `value(a,b)`; Candidate 2 has no registered equivalent |

I did not relax M55 to admit the candidate. Adding the missing task, pairwise
value, thresholds, statuses, nuisance registry, and property tests would be
the design of a new instrument.

**MEASURED.** This is not a battery that rejects everything. M55's committed
calibration has `PR27` passability met and `PR28` power met; all three known-bad
references are killed. I reran two no-corpus property suites: B6 coverage and
wrong-answer checks passed `7/7`, and the constant-\(|z|\) normative-wrapper
suite passed `7/7`. The planted pass fixtures remained passable.

M55 requires every battery to pass. An exact B0 failure plus failed no-target
specificity/denominator discipline is already decisive. “Not instantiable”
does not count as a pass; it means the present candidate has not become the
detail instrument that blocker `(a)` requires.

### Execution integrity

**MEASURED.** The capture trees were enumerated with
`Get-ChildItem -Force -Recurse -File` before and after all RAW reads:

| Root | Files | ARWs | Bytes | Before/after |
|---|---:|---:|---:|---|
| `D:\personal\macro` | `10,724` | `10,509` | `487,169,829,957` | identical |
| `D:\personal\macro\requests` | `3,918` | `3,908` | `149,982,011,502` | identical |

M131 wrote only beneath `experiments/M131-cand2-ruling/` and this report. No
file under `crates/` was touched.

## What I did not establish

- I did **not** run Candidate 2 on the natural tilted outputs. There is no
  lawful target/stream mapping, so producing a number would have answered the
  wrong question.
- I did **not** establish that Hotelling observers are generally unusable.
  With externally specified physical alternatives and complete acquisition
  roles, one can support a narrow task-detectability comparison.
- I did **not** establish that the unmatched tail is irrelevant to every
  possible task. I established only that neither of two image-derived focus
  coordinates placed a maximum there on the fixed 64-site grid.
- I did **not** isolate IBIS displacement from focus breathing, smooth camera
  drift, or phase-correlation error. I established that IBIS was on, the two
  motion histories differ, and the existing input-only geometry gate fails.
- I did **not** commission a PCHIP-linearised, truth-referenced, or
  physical-target successor. Each would be a new candidate requiring a new
  pre-results freeze, complete battery, independent audit, and explicit
  scorecard admission.
- I did **not** establish a no-new-capture route to blocker `(a)`. The existing
  stacks can commission input and geometry diagnostics, but they do not
  contain the physical target roles required by frozen Candidate 2.

The actionable ruling is therefore final: stop treating Candidate 2's
synthetic optical success as a route to blocker `(a)`. Preserve its
full-covariance congruence result as prior art for a successor; Candidate 2
itself is closed.
