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
