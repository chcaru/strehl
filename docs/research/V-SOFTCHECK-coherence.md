# V-SOFTCHECK: half-stack selection coherence, and the depth prediction

Pin `9b05d0b7`, binary sha256 `44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490`,
backend `pyramid`. Every number below is at **0.20-0.25 cycles per OUTPUT pixel**
unless another band is named, on the 7032x4688 shipping grid where one output pixel
is one photosite. Pre-registered in `experiments/V-SOFTCHECK/PREREG-coherence.md`,
committed `f518b8dd` before any coherence number existed.

## Verdict

**The prediction is REFUTED as stated, and I cannot conclusively exclude the
mechanism behind it.**

A third lane predicted that if the merge over-selects on a quantity that is partly
noise, the merge's per-pixel frame choice should disagree between two independent
half-stacks **at a rate that rises with N**. Measured on three subjects, including
the deepest capture in the corpus, that rate **falls with N on every one**.

| subject | frames | depths measured | `f(N_max)/f(N_min)` | 95% CI | P1 |
|---|---:|---|---:|---|---|
| `bee-1-cpl` | 299 | 64, 128, 200, 298 | **0.5771** | [0.5378, 0.6332] | **FALL** |
| `119MSDCF` | 33 | 8, 16, 32 | **0.8408** | [0.7977, 0.8837] | **FALL** |
| `113MSDCF` | 63 | 8, 16, 32, 62 | **0.4637** | [0.4462, 0.4865] | **FALL** |

`bee-1-cpl` is the decisive case. Its halves are 149-frame merges, so it probes
depth **past this lane's own measured N\* = 149 sharpness turnover** -- the region
where the rising branch would have had to appear. It does not appear.

**3 attempted = 3 measured + 0 refused + 0 void.**

## What was measured

Two **interleaved** halves of one bracket, `A = subset[0::2]` and `B = subset[1::2]`,
each merged separately by the shipping binary at the subject's shipped exposure
passed explicitly. Both halves span the focus range; `B` starts one focus step
later, a difference that shrinks as N grows and therefore **biases against** the
rising-with-N hypothesis under test.

Per tile, per radial ring:

```
gamma = |SUM FA conj(FB)| / sqrt( SUM|FA|^2 * SUM|FB|^2 )      f = 1 - gamma
```

`f = 0` when the two halves agree, `f = 1` when they are independent. Hann-windowed
T=256 tiles, 300 of them, selected on **0.02-0.05 cyc/px energy alone** -- disjoint
from every reported band, so the selection cannot prefer tiles where either arm
happens to be sharp.

### `bee-1-cpl`, 299 frames, exposure +1.50

| N | halves | 0.05-0.10 | 0.10-0.15 | 0.15-0.20 | **0.20-0.25** | 0.25-0.30 | 0.30-0.35 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 64 | 32+32 | 0.5822 | 0.9010 | 0.9524 | **0.9695** | 0.9743 | 0.9804 |
| 128 | 64+64 | 0.1393 | 0.4373 | 0.6713 | **0.8437** | 0.9313 | 0.9608 |
| 200 | 100+100 | 0.0479 | 0.1768 | 0.3971 | **0.6095** | 0.8149 | 0.9304 |
| 298 | 149+149 | 0.0333 | 0.1169 | 0.3038 | **0.5595** | 0.7800 | 0.9068 |

### `113MSDCF`, 63 frames, exposure +2.33

| N | halves | 0.05-0.10 | 0.15-0.20 | **0.20-0.25** | 0.25-0.30 |
|---:|---|---:|---:|---:|---:|
| 8 | 4+4 | 0.4308 | 0.9469 | **0.9743** | 0.9809 |
| 16 | 8+8 | 0.0457 | 0.4724 | **0.7671** | 0.9346 |
| 32 | 16+16 | 0.0130 | 0.2152 | **0.5144** | 0.8385 |
| 62 | 31+31 | 0.0096 | 0.1702 | **0.4518** | 0.8031 |

### `119MSDCF`, 33 frames, exposure +1.53

| N | halves | 0.05-0.10 | 0.15-0.20 | **0.20-0.25** | 0.25-0.30 |
|---:|---|---:|---:|---:|---:|
| 8 | 4+4 | 0.0363 | 0.6974 | **0.9159** | 0.9672 |
| 16 | 8+8 | 0.0232 | 0.5465 | **0.8140** | 0.9220 |
| 32 | 16+16 | 0.0203 | 0.5059 | **0.7701** | 0.9020 |

## P2 is SUPPORTED, and it is the part that corroborates the other lane

Another lane measured coherent detail against `enfuse` as 1.159 on `113MSDCF` and
**2.017** on `119MSDCF`. I did not produce that ordering and had no access to it in
my construction. The mechanism predicts `f(119MSDCF) > f(113MSDCF)` at matched N:

| N | `119MSDCF` | `113MSDCF` | predicted ordering holds |
|---:|---:|---:|---|
| 8 | 0.9159 | 0.9743 | no -- **both within 0.985 independent limit, not informative** |
| 16 | **0.8140** | 0.7671 | **yes** |
| 32 | **0.7701** | 0.5144 | **yes** |

**Supported at both informative depths.** `119MSDCF` is the more incoherent subject,
independently of the instrument that produced 2.017. The N=8 row is excluded on a
pre-registered ground, not a convenient one: `NOISE_NULL` establishes the
independent limit at 0.985 and both subjects sit within 0.07 of it there.

## P3 is REFUTED, and the direction is informative

I registered that selection should move the fine band more than the coarse one. The
fall is **far larger at the coarse band**: 0.0572 at 0.05-0.10 against 0.5771 at
0.20-0.25 on bee, and 0.0222 against 0.4637 on `113MSDCF`. Coarse bands have high
SNR, so whatever incoherence they carry averages away quickly with depth. That is
the signature of an **independent-noise** term, not a selection term.

## The honest limit: my own pre-registration protected only one sign

The pre-registration argues that a RISE could not be manufactured by sensor noise.
It says nothing about the converse, and the converse is what I measured. Independent
sensor noise contributes to `f` and **falls** with N as the merge averages more
frames. **A selection term that rose more slowly than the noise term fell would not
be visible in this observable.**

So: the prediction is refuted **as stated** -- the disagreement rate does not rise
with N, on any subject, at any depth reachable including 149-frame halves. The
mechanism is **not conclusively excluded**, and I decline to claim it is. I cannot
separate the two terms because this lane has already established that noise and
scene are **not separable on this data**: merge noise is non-white, falling 4.82x
across 0.30-0.50 cyc/px, and all three of my scene/noise estimators were refused.

For the same reason the **absolute** level of `f` -- 0.45 to 0.77 at the reporting
band -- is an **upper bound** on selection incoherence, not a measurement of it.

## Do NOT adopt `f` as an acceptance criterion

This is the load-bearing warning in this document.

`f` is **trivially gameable by blurring**. Any change that moves the merge toward
averaging drives `f` toward 0 while destroying detail. A build lane optimising `f`
would be rewarded for exactly the defect this project is trying to remove.

`f` is a **diagnostic**. The acceptance criterion remains `ninvariance.py`.

## Section 3 deliverable: a statistic coherence alone cannot move

The standing requirement is that any before/after include at least one statistic
that a coherence improvement cannot move. Demonstrated, not asserted.

**Planted coherence-only "fix":** deliver `(A+B)/2` -- the average of the two
independently merged halves. This is the *maximal* coherence improvement available.
It scores `f = 0.0000` exactly and half-difference noise `= 0.0000` exactly: a
perfect score on **both** instruments the user warned are coherence-sensitive, while
adding no information whatsoever. Registration is the same per-tile sub-pixel phase
correction the statistic itself uses, so the result is not a misalignment artifact.

| band | `f` between the halves | delivered band power vs one half | closed form `(1+gamma)/2` |
|---|---:|---:|---:|
| 0.05-0.10 | 0.0350 | 0.9846 | 0.9825 |
| 0.10-0.15 | 0.1162 | 0.9390 | 0.9419 |
| 0.15-0.20 | 0.3071 | 0.8354 | 0.8464 |
| **0.20-0.25** | 0.5679 | **0.7038** | 0.7161 |
| 0.25-0.30 | 0.7851 | 0.6023 | 0.6075 |
| 0.30-0.35 | 0.9137 | 0.5354 | 0.5431 |
| 0.35-0.40 | 0.9262 | 0.5176 | 0.5369 |

**The coherence-only fix costs 29.6% of delivered band power at the reporting band**,
agreeing with the closed form `(1+gamma)/2` to 0.0123 across seven bands. The loss is
arithmetic: averaging retains the coherent part and halves the power of whatever the
arms disagree about.

**Therefore:** a statistic computed on the **delivered master** against a reference
**fixed by the input bracket** cannot be moved by coherence alone, because no
half-split appears in its definition and the merge cannot alter its denominator. It
charges the planted fix by 29.6% rather than rewarding it. That statistic is the
matched-gauge per-site ceiling ratio this lane already ships, commissioned in both
directions (planted `IMPROVE` reads 1.7086 and 2.5512, so it is free to reward).

## Five defects found in my own instrument, all by controls that could fail

1. **The statistic I pre-registered failed its own gain arm.** The half-difference
   form is not gain-free; a photometric difference lands entirely in `(A-B)/2`.
   Replaced with normalised `gamma`, gain-free exactly (`NULL_GAIN` reproduces
   `BASE` to 1.2e-07).
2. **The registration floor VOIDED the first run, correctly.** One pixel of
   misalignment alone manufactures `f = 0.486`, which **exceeded** the `f = 0.467`
   measured between the real halves.
3. **My first phase correction had the sign backwards** and doubled the shift
   (floor rose to 0.666). numpy's `ifft` puts the peak at `-s`. Corrected floor:
   1.74e-04, and a planted non-integer (0.37, -0.62) px shift reads 7.9e-05.
4. **The shift fit was overfitting.** Estimating over the full spectrum let two free
   parameters per tile buy apparent coherence out of noise -- adding *independent*
   noise drove `f` DOWN, 0.510 -> 0.482, which the additive model forbids. The fit
   is now confined to 0.02-0.05 cyc/px, disjoint from every reported band.
5. **`NULL_SHIFT_BOTH` was comparing a 116-tile median against a 120-tile median.**
   On bee that population difference alone read 6.334e-03 and VOIDED a valid run. It
   had been passing on the shallower subjects for a reason unrelated to its own
   validity. Like for like, per-tile deviation is **0.000e+00 at median, p90 and max**
   -- a prediction, not a short-circuit, since integer `np.roll` with matched tile
   origins extracts bit-identical arrays (checked with `np.array_equal`). The
   repaired gate is monotone in a planted origin mismatch and fires at >= 8 px.

Commissioning that all three subjects passed: `NOISE_NULL` 0.9811 / 0.9841 / 0.9867
against a **predicted** `1 - 1/sqrt(4604)` = 0.98526; `IMPROVE` 0.0057 / 0.0461 /
0.0021; graded `DEGRADE` monotone; `FLOOR_GATE_ratio` 2057 to 2584.

## Consequence for the convergence story

Three lanes now point at over-selection. **This one does not corroborate the
depth part of it.** The disagreement rate falls with depth on all three subjects,
so the "incoherence rises with N" leg is unsupported. What survives from my side is
the **between-subject** ordering, which is independent corroboration that
`119MSDCF` is the more incoherent subject.

This is consistent with my earlier finding that the two lanes do not converge:
depth explains only 2.8-10.6% (log ratio) of the tone lane's 5.6x-16.7x scene gap on
bee. Depth costs sharpness -- `ninvariance.py` still FAILS bee at 1.0795 -- but it is
not the explanation for the deep-subject collapse the other lanes are measuring.

## A third, unregistered line of evidence pointing the same way

`commission()` reports `BASE` over the top 120 tiles; the result tables use all 300.
Those two disagree -- 0.3971 vs 0.7854 on `119MSDCF` at N=32 -- so I checked why
rather than assume, and the answer is informative. Tiles are ranked by descending
0.02-0.05 cyc/px energy, and `f` at 0.20-0.25 rises monotonically down that rank:

| tile rank (descending contrast) | `119MSDCF` N=32 | `bee-1-cpl` N=298 |
|---|---:|---:|
| 0-60 | **0.2334** | **0.4126** |
| 60-120 | 0.6193 | 0.4947 |
| 120-180 | 0.7889 | 0.5488 |
| 180-240 | 0.8793 | 0.6444 |
| 240-300 | **0.8834** | **0.7683** |

**Incoherence is concentrated in the LOW-contrast tiles**, monotonically, on both
subjects. Selection incoherence should be worst where frames genuinely compete --
at high-contrast detail. Noise incoherence should be worst where SNR is lowest. The
gradient runs the second way, which is a third independent indication that `f` is
dominated by an independent-noise term rather than by frame choice.

This was not pre-registered and I am not treating it as a test. It is consistent
with P3 and it is the reason the `BASE`/table gap exists; both are recorded so that
neither is mistaken for a defect later.
