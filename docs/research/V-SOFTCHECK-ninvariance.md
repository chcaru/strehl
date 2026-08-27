# V-SOFTCHECK: does bracket DEPTH cost the merge sharpness?

Status: Measured. Pin `9b05d0b7`, binary sha256 `44C2F2CD2E5B2894...`, the binary
named by every `SHIP-V4.tiff.ok`. Merge backend `pyramid (default)`, confirmed
from the binary's own banner on every render, not from a doc.

## Verdict

**Yes, on two of three subjects, and it is significant in the only promotable
band on the deepest capture in the corpus. It is NOT universal, and the headline
"our merge gets worse as stacks get deeper" is contradicted by the third
subject.**

`bee-1-cpl`, 299 frames, the deepest capture there is: at matched focus range and
matched exposure, **a 149-frame merge is 7.9% sharper at 0.20-0.25 cyc per
output pixel than the full 299-frame merge**, R = 1.0795, CI [1.0554, 1.1153].

This number was corrected downwards after I found a defect in my own instrument;
see *Two defects in this instrument* below. The uncorrected figure was 1.1037. The
defect had **inflated my own finding**, and correcting it moved the result against
me by 2.2 points.

`flower-bud-alone-cpl`, 205 frames, shows **no depth cost at any band**. Its curve
rises monotonically to N=205. Any unqualified claim that depth hurts is refuted by
this subject and must not be made.

## Method, and why it needs no reference frames

The originating measurement divided two masters by the same per-site max over all
63 frames. A common denominator cancels, so the depth effect is exactly a
**master-to-master** band power ratio. That removes 299 single-frame renders, the
whole registration prepass, and -- importantly -- the order statistic: there is no
max over N anywhere in this estimator, so the subsampled-reference and
winner's-curse traps cannot apply to it.

Held fixed: focus RANGE (`linspace(0, N-1, n)` rounded, so the first and last
frames are pinned into every arm and asserted on disk -- `frames[::N//n][:n]` is
never used), exposure (one explicit `--exposure` per subject, taken from the
shipped provenance, passed identically to every arm), pin, tile coordinates, band
edges, window. Only DENSITY varies.

Tiles are selected by 0.02-0.05 cyc/px energy alone, a band disjoint from every
reported band, so tile choice cannot favour an arm.

**Self-check:** the N=63 master this harness rendered for `113MSDCF` is
byte-identical to the master rendered through the ordinary shipped path,
`3c097fba746b9955`. **Determinism:** the `bee-1-cpl` N=149 arm was deleted and
re-rendered and the criterion returned the same R to four decimals. That check was
run on the pre-fix instrument and returned 1.1037 twice; it tests the RENDERER, not
the statistic, so the later fix to the statistic does not weaken it.

## The curves

Values above 1 mean the SHALLOWER stack is SHARPER. Bands are cyc per OUTPUT
pixel on the 7032x4688 shipping grid, where one output pixel is one photosite.

`bee-1-cpl`, N=299:

| N | 0.05-0.10 | 0.15-0.20 | **0.20-0.25** | 0.25-0.30 | 0.30-0.35 | 0.35-0.40 |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 0.0605 | 0.0523 | 0.1157 | 0.2199 | 0.3063 | 0.3179 |
| 32 | 0.5489 | 0.4171 | 0.4594 | 0.5424 | 0.6583 | 0.7011 |
| 64 | 0.7859 | 0.7796 | 0.7993 | 0.8804 | 0.9812 | 1.0070 |
| 100 | 0.9133 | 0.9600 | 1.0325 | 1.0801 | 1.1321 | 1.1396 |
| **149** | 0.9481 | 1.0029 | **1.0795** | **1.1531** | **1.1766** | **1.1689** |
| 200 | 0.9613 | 0.9939 | 1.0364 | 1.0823 | 1.0952 | 1.0819 |
| 299 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

The peak sits at **N=149 at every band at and above 0.15**: +7.9% at 0.20-0.25,
+15.3% at 0.25-0.30, +17.7% at 0.30-0.35. Bands at and below 0.15 never rise
significantly above 1.0 -- on this subject the coverage limb is still paying at
the coarse scales when the fine scales have already turned over.

`113MSDCF`, N=63: peak at N=16-32 above 0.25; **+15.0% at 0.30-0.35** for N=16
against the full stack. At 0.20-0.25 it is flat (+0.2%, not significant).
Re-measured after the instrument fix: every band verdict is identical, and the
only row that moved at all is N=8, whose shift flipped from `0,-1` to `0,+1`.

`flower-bud-alone-cpl`, N=205: 0.2954 at N=8 rising monotonically to 1.0000 at
N=205, at **every** band. No falling limb anywhere.

**The shape is two-limbed.** Below a subject-specific N* the bracket is still
buying focus COVERAGE and depth helps, steeply. Above N* the only thing another
frame adds is another near-tied competitor, and the merge softens. N* is roughly
16-32 for `113MSDCF`, **149** for `bee-1-cpl`, and at or beyond 205 for
`flower-bud-alone-cpl` -- which is why that subject shows no cost. It has not
reached its own N* yet. It is not immune; it is not yet oversampled.

## Mechanism: supported on one subject, competing explanations refuted

The relayed hypothesis -- `w_i = (snr_i/SNR_REF)^p` normalised over N, so the
winner's SHARE falls as N grows -- was checked against the pin before use, and its
constants are really there: `pyramid.rs` at `9b05d0b7` carries `MAX_EXPONENT: f32
= 8.0`, `exponent: 2.0`, `sharpen_per_octave: 1.4`, `SoftPower`, and
`merge_cmd.rs` carries `DEFAULT_MERGE_BACKEND: MergeBackend = MergeBackend::Pyramid`.

I did not read the merge's internal weights. I measured the output against a
ruler calibrated on the same data: explicit averages of the m frames nearest each
tile's own best frame give a dilution curve `D(m)`, validated as `D(1) = 1`
exactly and monotone from 1.0000 to 0.0131. Inverting each master onto it:

| `113MSDCF` depth | master/best at 0.30-0.35 | effective blend width |
|---:|---:|---:|
| N=8 | 0.7977 | 1.59 |
| N=16 | 0.7906 | 1.61 |
| N=32 | 0.7203 | 1.82 |
| N=63 | 0.6063 | **2.15** |

The merge behaves like a blend of more frames as the stack deepens, which is what
the hypothesis predicts. `D` is steep near m=1 -- `D(3)` is already 0.317 -- so
drifting from 1.6 to 2.15 contributors is expensive.

Two competing explanations were tested and both fail:

- **Alignment degrading with depth: REFUTED.** Held-out registration error *falls*
  as the bee deepens, 26.768 px at N=149 to 17.001 px at N=299. Alignment gets
  better while the output gets softer.
- **Contaminated frames entering the deep arm: REFUTED.** `0 refused` at every
  depth on every subject.

**The absolute held-out error on `bee-1-cpl` is 17-27 px and that is a separate
problem worth someone's attention.** It is not this one: it does not grow with N,
so it cannot produce an N-dependent effect.

## The acceptance criterion

Pre-registered in `experiments/V-SOFTCHECK/PREREG-ninvariance.md`, committed
before it was applied to anything. Delivered as
`experiments/V-SOFTCHECK/ninvariance.py` for the re-certification harness to call:
exit 0 PASS, 1 FAIL, 2 VOID, with a JSON record written per run. VOID is not a
pass.

Gate: primary band 0.20-0.25 only. FAIL when the bootstrap CI lower bound exceeds
1.0. One-sided, because depth is allowed to help.

| subject | N full vs half | R (0.20-0.25) | CI | verdict |
|---|---|---:|---|---|
| `bee-1-cpl` | 299 vs 149 | **1.0795** | [1.0554, 1.1153] | **FAIL** |
| `113MSDCF` | 63 vs 31 | 0.9623 | [0.9546, 0.9744] | PASS |
| `flower-bud-alone-cpl` | 205 vs 102 | 0.9018 | [0.8562, 0.9253] | PASS |

Partition: **3 attempted = 2 pass + 1 fail + 0 void.**

Commissioning, primary band, all four arms required: NULL 1.0 exactly, DEGRADE
0.1504, **IMPROVE 2.5486**, REFPERT 6.6509. The IMPROVE arm is the load-bearing
one -- it proves the statistic is free to reward a build rather than bounded
below.

## Two defects in this instrument, found after delivery

The tone lane reported an identity control that short-circuited to `a.copy()` and
returned exactly `1.0000` -- a control that could not have failed. I applied that
lesson to my own harness and wrote `nullhard.py`, four nulls that perturb the input
in ways the statistic must be blind to and can therefore actually fail, plus a
graded blur ladder. It found two defects in the instrument I had already delivered.

**1. My NULL arm was inert, and my teeth check was short-circuited.** The delivered
NULL was `rings(M.copy())/rings(M)`. It runs the whole statistic, so it is not
literally `a.copy()`, but the outcome is the same: it returns `1.0000` unless
numpy's FFT is nondeterministic, and it validated nothing. Worse, `gauss()` used
`r = int(3*sig)`, so any sigma below 0.33 gave **radius 0, a one-tap identity
kernel**. My first teeth check at sigma 0.3 read exactly `1.00000` because the blur
was never applied. Same failure the tone lane hit, in my own helper.
Fixed to `r = max(1, ceil(3*sig))`. The ladder is now monotone and non-trivial:
sigma 0.3 -> 1.3%, 0.5 -> 32.4%, 0.8 -> 70.4%, 1.0 -> 85.0%.

**2. `align_int()` returned the wrong sign, and it contaminated my headline.** It
returned the raw correlation peak, whose sign is opposite to the additive offset
every caller applied as `oy+sy`. Against three planted rolls:

| planted roll | `align_int` returned | ratio with `oy+sy` | ratio with `oy-sy` |
|---|---|---:|---:|
| (+7,+11) | (-7,-11) | 1.01081 | **1.00000** |
| (-5,+3) | (+5,-3) | 1.00537 | **1.00000** |
| (+13,-9) | (-13,+9) | 0.98334 | **1.00000** |

**Blast radius, bounded by the shifts the harness recorded per subject rather than
by assumption:** `113MSDCF` and `flower-bud-alone-cpl` ran at `[0,0]` on every
load-bearing arm, and negating zero is zero, so those subjects are provably
untouched -- confirmed for `113MSDCF` by re-measuring the whole curve. `bee-1-cpl`
ran at `[0,-7]`, so its headline was contaminated. Corrected, it is 1.0795
[1.0554, 1.1153], **still FAIL**. The defect had made my own finding look 2.2
points stronger than it is.

Both fixes are at a single site each and are committed with the nulls that caught
them.

## Registration is not a single number on every subject, and the criterion now says so

Chasing the translate null further turned up a third instrument problem, and it is
the most interesting of the three because it is a property of the DATA, not of my
code.

`align_int` correlates a 1024 px window. It was taking that window at the centre of
the frame, blind to content. Commissioning it per subject against planted rolls:

| subject | planted rolls recovered exactly |
|---|---|
| `bee-1-cpl` | **4/4** |
| `113MSDCF` | **4/4** |
| `flower-bud-alone-cpl` | **1/4** -- always reporting `sx=0`; the centre window lands in low-contrast bokeh |

Choosing the window by content instead of by position fixed most of that, but it
exposed something worse. On `bee-1-cpl` **both** windows recover 4/4 planted rolls
and they still disagree about the real arm shift: `+0,+7` from one, `+4,-2` from the
other. Two correctly-commissioned aligners cannot disagree about a translation. They
disagree because **the two arms are not related by a translation** -- the
displacement varies across the frame. That is the same subject whose held-out
registration error was already measured at 17-27 px.

I tried to remove the global-shift assumption with per-tile registration.
**It failed its own commissioning and is not shipped:** registering an image against
ITSELF recovered a zero shift on only 229 of 283 tiles, because un-normalised cross
correlation is biased toward high-energy regions. A component that cannot register
an image to itself does not get to register two masters, so it was deleted rather
than tuned until it looked right.

**What ships instead is an envelope.** Rather than assert one shift, the criterion
evaluates R over a neighbourhood of it and takes the verdict from the bound that is
KINDEST to the build, so it can never fail a build on the strength of my aligner's
weakness:

| subject | R point estimate | registration envelope | verdict |
|---|---:|---|---|
| `bee-1-cpl` | 1.0795 | **[1.0732, 1.0923]** | FAIL -- entirely above 1.0 |
| `113MSDCF` | 0.9623 | [0.9555, 0.9686] | PASS |
| `flower-bud-alone-cpl` | 0.9018 | [0.8784, 0.9123] | PASS |

**Every verdict is invariant across the whole envelope, and across deliberate shift
errors up to 11 px in both axes.** The `flower-bud-alone-cpl` aligner failure is
therefore real, recorded in the criterion's JSON as `aligner_err = (+1, -11)`, and
immaterial to its verdict. The translate null was also rebuilt to use the KNOWN
planted offset rather than the aligner's estimate, so that a broken aligner and a
broken statistic can no longer mask one another.

This is the third defect found in this instrument today by controls that could fail,
after an inert null and an inverted sign. None of the three changed a verdict.

## The scene/noise decomposition down the ladder is VOID

I was asked to extend the tone lane's scene/noise decomposition down my own depth
ladder, on the reasoning that if scene detail falls monotonically with N at matched
range on one subject, the mechanism is demonstrated rather than inferred.

**I could not build a noise estimator that survived commissioning, so I am not
reporting a decomposition.** Three were attempted on `bee-1-cpl` and all three were
refused, each on measured grounds, not on judgement:

| estimator | what it does | why it was refused |
|---|---|---|
| **A** flat-ROI | noise = ring power on low-contrast tiles | level mismatch **94.8%** (flats at 61059 DN, detail at 31338; shot noise scales with level), and the term **RISES 5.99x from N=8 to N=299** while correlating **0.979** with the scene term. Averaging more frames cannot manufacture noise. It is scene. |
| **B** HF-corner | noise = 0.45-0.50 ring on the *same* tiles, extrapolated flat | merge noise is **strongly non-white**: ring power falls **4.82x** across 0.30 -> 0.50 cyc/px. No out-of-band ring predicts the reporting band. |
| **C** floor bound | upper-bounds the noise floor from the 1st percentile of level-matched tiles | bound reaches **28-60%** of total power. Too large to ignore, and neither A nor B can separate it. |

Note that my originally planned gate -- refuse if `P_scene <= 0` -- **did not
catch A**. Estimator A was degenerate in a way that leaves the scene term
comfortably positive. A non-negativity check is not sufficient to commission a
decomposition; the noise term has to be tested against properties noise actually
has.

**Estimator B's failure is itself a result worth having.** Noise in a strehl master
is not white. Any decomposition anywhere on this project that estimates a noise
term in one band and applies it in another is unsound on this data, by a factor of
up to 4.8.

What survives is the un-decomposed total-power curve above, which is what the rest
of this document reports.

## The two lanes agree in sign and disagree in magnitude by 5-16x

I was asked to consider whether this lane and the tone lane converging is a
common-cause artifact. They share the shipping binary, the same masters and a
band-energy statistic, so the concern is well placed. The sharper point is that
**they do not actually converge.**

Both measure `bee-1-cpl` at N=299. The tone lane reports a scene ratio of 0.180 vs
`enfuse` and 0.060 vs `focus-stack`, i.e. a 5.6x and 16.7x deficit. The largest
depth-attributable deficit I can measure on the same subject, same binary, at
matched focus range with an identical denominator, is **1.08x at 0.20-0.25 and
1.20x at 0.30-0.35**.

| tone-lane gap | my depth effect | share of the gap explained by depth (log ratio) |
|---|---|---:|
| 5.6x vs `enfuse` | 1.08x @ 0.20-0.25 | **4.6%** |
| 5.6x vs `enfuse` | 1.20x @ 0.30-0.35 | **10.6%** |
| 16.7x vs `focus-stack` | 1.08x @ 0.20-0.25 | **2.8%** |
| 16.7x vs `focus-stack` | 1.20x @ 0.30-0.35 | **6.5%** |

**Stack depth accounts for at most about a tenth of that gap and typically a
twentieth.** This is not a contradiction -- the two measure different things, theirs
strehl against another tool and mine strehl against itself -- but it does settle the
attribution question: if the tone lane's collapse is real, **depth is not its
cause**, and a fix aimed at depth should not be expected to move 0.060 to anywhere
near 1.0. The build lane should not treat my criterion as a proxy for that number.

Whether their result is itself sound I cannot say; I did not re-derive it, and note
that any decomposition it rests on faces the non-whiteness problem above.

## What I did not establish

- The dilution mechanism is measured on **`113MSDCF` only**. On `bee-1-cpl` the
  competing mechanisms are refuted but the effective blend width was not measured;
  that needs 299 single-frame renders and was not done.
- **The confidence-dependent exponent fix is untested against this criterion.** It
  is a plausible fix for a dilution mechanism, and the criterion exists precisely
  so it does not have to be believed. If depth softening survives it, the criterion
  will say so.
- The two-limb account of N* is an interpretation that fits three subjects. It is
  not independently measured, because I did not measure focus-step size against
  depth of field.

## Disposition of `flower-bud-alone-cpl`

**Still REFUSED, and the candidate mechanism I named for it is now dead.** After
the previous run I suggested its N=205 depth might explain its anomalous softness
via this very effect. Measured: it is the one subject with **no depth cost at
all**. That explanation is withdrawn. Its mechanism remains unidentified and it
stays refused.
