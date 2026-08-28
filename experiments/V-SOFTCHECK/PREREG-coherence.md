# PRE-REGISTRATION: half-stack selection coherence

Written and committed BEFORE any coherence number exists. Pin `9b05d0b7`, binary
sha256 `44C2F2CD2E5B2894...`, backend `pyramid`.

## The claim being tested

A third lane proposes that the shipping merge over-selects on a quantity that is
partly noise, and offers a falsifiable consequence: **a selection driven by noise
cannot be reproduced across two independent halves of the same stack.** If so, the
merge's per-pixel frame choice should disagree between two independent half-stacks
at a rate above what the scene justifies, and that rate should RISE with N.

I cannot read the merge's internal choice map without editing `pyramid.rs`, which
the build lane owns. I can measure its observable consequence: how much of the
delivered detail is COMMON to two independently-merged halves of the same bracket.

## Construction

For total depth N, take `subset = linspace(0, NF-1, N)` rounded, then
`A = subset[0::2]`, `B = subset[1::2]`. The halves are INTERLEAVED, so both span
the focus range rather than each taking one end. Each is merged separately by the
shipping binary at the subject's shipped exposure, passed explicitly.

`B` begins one focus step later than `A`, so their ranges differ by `1/N` of the
sweep. That difference SHRINKS as N grows, so it inflates disagreement at small N
and therefore biases against the hypothesis under test. It is conservative here.

## The statistic, band-limited end to end

Per tile, per radial ring `b`, on the shipping output grid where one output pixel
is one photosite:

```
P_sum = ring power of (A+B)/2          P_dif = ring power of (A-B)/2
P_coh = P_sum - P_dif                  P_inc = 2 * P_dif
incoherent fraction  f = P_inc / (P_coh + P_inc)
```

For `A = S + eA`, `B = S + eB` with independent zero-mean errors this gives
`P_coh -> PS` and `f -> 0` for identical arms, `f -> 1` for wholly independent
arms. Every term is the same ring of the same Hann-windowed T=256 tile FFT. No
term is full-band. Tiles are chosen on 0.02-0.05 cyc/px energy alone, disjoint
from every reported band.

**Degeneracy gate.** `P_coh < 0` means the half-difference exceeds the half-sum,
which the additive model forbids. Any arm-band in that state is reported VOID and
no fraction is printed for it. This is the failure the tone lane hit by mixing a
band-limited term with a full-band one, and it is gated rather than assumed away.

## Predictions, registered before measurement

**P1, within subject.** If selection is noise-driven, `f` at 0.20-0.25 cyc/px
RISES with N. If selection is determined by the scene, `f` FALLS with N, because
each half samples focus more finely and both converge on the same right answer.
**The two hypotheses predict OPPOSITE SIGNS**, which is why this discriminates
where a magnitude alone would not.

Decision rule: bootstrap the ratio `f(N_max) / f(N_min)` over tiles.
RISE if the CI lower bound exceeds 1.0. FALL if the CI upper bound is below 1.0.
INCONCLUSIVE otherwise. I commit to reporting INCONCLUSIVE as a result.

**P2, between subjects.** Another lane measured coherent detail against `enfuse`
at 0.20-0.25 as 1.159 on `113MSDCF` and 2.017 on `119MSDCF`. I did not produce
that ordering. If incoherent selection is what that instrument is missing, then at
matched N, `f(119MSDCF) > f(113MSDCF)`. If `119MSDCF` is not the more incoherent
subject, the proposed mechanism does not explain their result and I will say so.

**P3, band shape.** Selection matters less at coarse scales, where all frames
agree. The rise in `f` at 0.20-0.25 should exceed the rise at 0.05-0.10. A rise
that is uniform across all bands points at something global, not at selection.

## Why a rise cannot be explained by the competing causes

- **Sensor noise.** Independent noise in the two halves does contribute to `f`,
  but it does not RISE with N. If anything it falls: this lane already measured the
  merge's effective blend width rising from 1.59 to 2.15 with depth, and more
  blending means less per-pixel noise. A rise in `f` therefore cannot be noise.
- **Alignment drift.** Both halves are aligned against the same reference, so
  drift produces the same error in both. That is COHERENT error. It moves `P_coh`,
  not `P_inc`, and cannot manufacture a rise in `f`.
- **Registration between the two arms** does inflate `P_dif`. Controlled below.

## Commissioning, required before any number is reported

| arm | what it does | required |
|---|---|---|
| `NULL_OFFSET` | add DC to both halves | `f` unchanged |
| `NULL_GAIN` | scale one half by 1.3 | `f` unchanged; the statistic must be gain-free |
| `NULL_SHIFT_BOTH` | shift both halves equally | `f` unchanged |
| `NOISE_NULL` | two independent random fields | `f` = 1.0 within tolerance. A PREDICTED value, not a round number taken on trust |
| `DEGRADE` | add independent noise to each half | `f` rises, monotone in noise amplitude |
| `IMPROVE` | replace B with A plus a small independent perturbation | `f` FALLS toward 0. The load-bearing arm: it proves the statistic is free to reward a merge and is not bounded below |

`IDENTITY` (A against itself) is computed but explicitly NOT relied on: it returns
0 by construction and could not fail. It is reported as a saturation check only.

**Registration floor control.** Take one master, shift it by 1 px, and measure the
apparent `f` between it and its own shifted copy. That is the incoherence
attributable purely to misregistration, measured in the SAME band as the result. If
the measured `f` is not at least twice this floor, the run is VOID for that band. A
band-limited statistic gets a band-limited control.

## What would falsify the mechanism

- `f` flat or falling with N at 0.20-0.25 on both subjects.
- `f(119MSDCF) <= f(113MSDCF)` at matched N.
- `f` rising uniformly across all bands including 0.05-0.10.

Any of these and I report that the half-stack incoherence mechanism is not
supported by this measurement, whatever the other lanes have found.

## Standing caveat I am required to carry

If detail is incoherent rather than absent, it is still PRESENT in the delivered
image. A high `f` therefore does NOT by itself establish that the image is worse.
It establishes that the choice is not reproducible. Any before/after built on this
number must include a statistic that coherence alone cannot move.

---

# AMENDMENT, written after the numbers existed

Recorded here rather than by editing the text above, so the registered form and the
delivered form can be compared. Everything above this line is as committed in
`f518b8dd`, before any coherence number existed.

## 1. The statistic I registered FAILED its own commissioning. It was replaced.

The half-difference form `f = 2*P_dif / (P_coh + 2*P_dif)` registered above is
**not gain-free**, and my own `NULL_GAIN` arm caught it: a photometric difference
between the arms lands entirely in `(A-B)/2`, so scaling one half by 1.3 moved `f`.
That is the exact defect the pre-registration demanded the arm exist to find, and it
found it in my own registered design.

Delivered form, adopted before any subject was measured:

```
gamma = |SUM FA conj(FB)| / sqrt( SUM|FA|^2 * SUM|FB|^2 )        f = 1 - gamma
```

Gain-free **exactly** — a scalar on either arm cancels in numerator and denominator.
`NULL_GAIN` now reproduces `BASE` to 1.2e-07 on `bee-1-cpl`. `P_coh` is retained
only as the degeneracy diagnostic, because `gamma` cannot express `P_coh < 0`.

## 2. The registration-floor control VOIDED the first run, correctly.

One pixel of misalignment alone manufactures `f = 0.486` at 0.20-0.25, which
**exceeded the `f = 0.467` measured between the real halves.** Uncorrected, this
instrument cannot distinguish incoherent frame choice from one pixel of shift.
Sub-pixel correction was added as a pure phase ramp, never resampling.

My first phase correction had the **sign backwards** and doubled the shift rather
than removing it: the floor rose to 0.666. numpy's `ifft` puts the phase-correlation
peak at `-s`. Corrected, the 1 px floor is 1.74e-04 and a planted NON-integer shift
of (0.37, -0.62) px reads 7.9e-05. `FLOOR_GATE_ratio` on `bee-1-cpl` is 2584.

## 3. A fourth defect, found by the `DEGRADE` ladder.

Fitting the shift over the full spectrum let two free parameters per tile buy
apparent coherence out of noise: adding **independent** noise to both arms drove `f`
DOWN, 0.510 -> 0.482, which the additive model forbids. Shift estimation is now
confined to 0.02-0.05 cyc/px, disjoint from every reported band. The ladder is
monotone on all three subjects.

## 4. A fifth defect, found by `bee-1-cpl` and fixed in the instrument.

`NULL_SHIFT_BOTH` compared its own median against `BASE`, but the arm drops the
tiles too near the top-left edge. It was comparing a **116-tile median against a
120-tile median**. On bee that population difference alone read 6.334e-03 and VOIDED
a valid run. Comparing like with like, per-tile `|shifted - base|` is **0.000e+00 at
the median, the p90 and the max.**

That exact zero is a **prediction, not a short-circuit**: `np.roll` by integer
(7,11) with tile origins offset by the same (7,11) extracts bit-identical arrays,
verified with `np.array_equal`. The repaired gate was then commissioned against a
graded planted mismatch and is monotone in it, firing at >= 8 px:

| origin mismatch | 0 px | 1 px | 2 px | 4 px | 8 px | 16 px |
|---|---:|---:|---:|---:|---:|---:|
| deviation | 0.0 | 1.8e-04 | 8.8e-04 | 2.5e-03 | **5.9e-03** | **8.2e-03** |

On the two shallower subjects the unrepaired arm happened to fall under tolerance.
It was passing for a reason unrelated to its own validity.

## 5. Outcome against the registered predictions

| | registered | measured | |
|---|---|---|---|
| **P1** within subject | RISE if noise-driven | **FALL on all three**, incl. the deepest capture in the corpus | **REFUTED** |
| **P2** between subjects | `f(119) > f(113)` at matched N | holds at both informative depths | **SUPPORTED** |
| **P3** band shape | fall/rise larger at 0.20-0.25 than 0.05-0.10 | fall is far larger at 0.05-0.10 | **REFUTED** |

`P1` was refuted in the registered direction on `119MSDCF` (N<=32) and `113MSDCF`
(N<=62) before `bee-1-cpl` was rendered, and `bee-1-cpl` then refuted it at halves of
149 frames each -- past this lane's own measured N* = 149 sharpness turnover, which
is where the rising branch would have had to appear.

## 6. The one-sided protection in section "Why a rise cannot be explained"

That section argues a RISE could not be manufactured by noise. It is silent on the
converse, and the converse is what I measured. Independent sensor noise contributes
to `f` and **falls** with N as the merge averages more frames. A selection term that
rose more slowly than the noise term fell would not be visible in this observable.

So the registered prediction is refuted **as stated** -- the disagreement rate does
not rise with N -- but the mechanism is **not conclusively excluded**. I cannot
separate the two terms, because this lane already established that noise and scene
are not separable on this data: the merge noise is non-white, falling 4.82x across
0.30-0.50 cyc/px, and all three of my scene/noise estimators were refused.
