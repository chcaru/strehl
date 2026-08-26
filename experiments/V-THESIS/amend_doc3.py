import pathlib

p = pathlib.Path("docs/research/V-THESIS.md")
doc = p.read_text(encoding="utf8")

add = """

## Addendum 3 -- the alignment confound, measured with the control nobody ran

The orchestrator made the alignment confound the top priority: `argmax-baseline`
does not align, both merge paths do, and if the matched sites are not genuinely
matched across that rescale the comparison measures registration error rather
than detail -- which would *wash out* a real merge advantage and manufacture the
reported null.

### The gap: their whole-chain control switched the confound off

All three of BUILD-THESIS's chain controls carry, in their own run log:

```
field of view scaled to 1.0000 (control: both arms share one grid)
```

`experiments/BUILD-THESIS/build_controls.py` writes that line, and it is true.
The control that proves the chain can recover a planted blur was run with the
arms on ONE grid. The confound that threatens the headline is a 2-7% rescale,
and no control ever exercised it. The plant was never shown able to express the
failure it was meant to catch.

### Building the missing control

`experiments/V-THESIS/build_scaled_ctrl.py` and `build_ruler_ctrl.py` construct
synthetic subjects where the scale AND the blur are both known:

    argmax_syn = warp(gauss_exact(merge, sigma), scale s about the centre)

Blur before the resample, so `sigma` is a scene blur in merge pixels. Two
geometries: leaf-2's 0.9342 (6.6% -- the size of the miss the orchestrator
flagged on `EST-leaf-2-cpl`) and flat-on-ruler's 0.9707 (2.9%).

`python experiments/BUILD-THESIS/measure.py VCTRL-...` then
`python experiments/BUILD-THESIS/blureq.py ...` -- their code, unmodified.
Their `measure-mean.json` was copied to `$env:TEMP` first and restored after.

### What their chain does when the truth is exactly zero

| control | truth | S1_norm | S2_f50 | S3_acf | signs |
|---|---:|---:|---:|---:|---|
| their CTRL-identity (one grid) | 0.000 | +0.000 | +0.000 | +0.000 | agree |
| their CTRL-blur0.8 (one grid) | 0.800 | +0.800 | +0.800 | +0.800 | agree |
| their CTRL-blur1.5 (one grid) | 1.500 | +1.498 | +1.500 | +1.500 | agree |
| V VCTRL-s-blur0.0 (6.6% rescale) | 0.000 | **+0.310** | **-0.460** | **-0.434** | DISAGREE |
| V VCTRL-s-blur0.4 (6.6% rescale) | 0.400 | +0.483 | **-0.325** | +0.322 | DISAGREE |
| V VCTRL-s-blur0.8 (6.6% rescale) | 0.800 | +0.745 | +0.599 | +0.622 | agree |

On one grid the chain is flawless. Across a realistic rescale, with **no blur
planted at all**, it reports 0.31-0.46 px of equivalent blur and its three
statistics disagree in sign -- the same size and the same signature as the
entire published headline. And a genuine **+0.4 px merge advantage** is reported
by `S2_f50` as a **0.325 px argmax advantage**: the sign is inverted, on 4 of 6
tiles.

Their published six subjects also disagree in sign on 5 of 6. That disagreement
was visible in their own output and is the tell.

The decisive comparison: their real-subject readings span S1 [-0.475,+0.491],
S2 [-0.438,+0.257], S3 [-2.062,+0.470]. The **0.0 px** control lands inside that
range on 2 of 3 statistics; the **+0.4 px** control lands inside on **all
three**. Their data cannot discriminate "no difference" from "a real 0.4 px
merge advantage".

### My instrument, held to the same test

| control | truth | V reads | error |
|---|---:|---:|---:|
| VCTRL-r-blur0.0 (2.9% rescale) | +0.000 | **-0.007** | -0.007 |
| VCTRL-r-blur0.4 (2.9% rescale) | +0.400 | **+0.400** | -0.000 |
| VCTRL-s-blur0.0 (6.6% rescale) | +0.000 | **+0.054** | +0.054 |
| VCTRL-s-blur0.4 (6.6% rescale) | +0.400 | **+0.404** | +0.004 |
| VCTRL-s-blur0.8 (6.6% rescale) | +0.800 | **+0.802** | +0.002 |

A real merge advantage planted across the exact rescale in question is
recovered to within 0.004 px. **The null I report is not a washout.**

Deliberately corrupting the scale (`floor_budget.py`) confirms it: a full 6.6%
miss -- twice the largest plausible error, since my anchor fit and warp-correlate
sweep agree with their ECC to within 0.5-2% on all six -- moves my reading by at
most 0.15 px and never flips a sign.

| subject | fitted | -6.6% | -3.3% | correct | +3.3% | +6.6% |
|---|---:|---:|---:|---:|---:|---:|
| bee-3-cpl | 0.93554 | +0.331 | +0.294 | +0.255 | +0.203 | +0.102 |
| leaf-2-cpl | 0.95399 | -0.248 | -0.230 | -0.218 | -0.174 | -0.079 |
| flat-on-ruler-cpl | 0.97073 | -0.300 | -0.370 | -0.385 | -0.397 | -0.441 |

Their ECC also recovered the planted scale exactly on all five controls
(0.9342 and 0.9707, matching truth). It did not latch wrong on the headline arms.

## Addendum 4 -- the "0.5 px is also the noise gap" equivalence is incomplete

Their own `limits.json` noise-null table, n=12 rows:

| statistic | median abs px | max abs px |
|---|---:|---:|
| S1_norm | 0.367 | 0.492 |
| S2_f50 | 0.255 | 1.503 |
| S3_acf | 0.241 | 1.320 |
| all | **0.261** | **1.503** |

"0.5 px" is roughly the *maximum* of S1, not the typical value (0.261). But the
substantive point is that the floor has at least three terms and their yardstick
counted one:

| term | size | counted? |
|---|---|---|
| noise gap | 0.261 px median | yes |
| scipy kernel truncation | 0.155-0.184 px | no -- V `floor_exact.py` |
| **arm rescale** | **0.310-0.460 px** | **no -- V `VCTRL-*-blur0.0`** |

The largest single measured term is the one their commissioning switched off.
The sentence "0.5 px is also what the instrument reports for the noise gap
alone" is therefore not a coincidence and not a noise floor; it is a floor built
mostly of registration and truncation, with noise second.

## Addendum 5 -- `flat-on-ruler-cpl` (finding #2) is right for the wrong reason

Their published row: **-0.475 / -0.438 / -0.377**, offered as "selection wins
outright, ~0.4 px, all three statistics agreeing".

Their chain on that subject's OWN geometry with **zero blur planted**
(`VCTRL-r-blur0.0`): **-0.320 / -0.361 / -0.354**, all six tiles each, all three
agreeing.

The tri-statistic agreement that was offered as corroboration is what the chain
does when the answer is zero. It is a shared systematic, not independent
confirmation. Bias-subtracting leaves -0.155 / -0.077 / -0.023: their own data,
corrected, says the subject is a tie.

The direction nevertheless survives on independent evidence. My instrument reads
**-0.007 px** on that same zero-truth geometry and **-0.329 px [-0.362,-0.176],
sign p=0.011** on the real subject. Selection *is* finer there. Their number,
their magnitude and their stated grounds are not evidence for it.

## Addendum 6 -- the invented-structure statistic fails both commissioning tests

First, a retraction of my own: `experiments/V-THESIS/kurt_attack.py` derived the
flat mask separately on each arm, so it compared different sets of pixels. Its
numbers are withdrawn. `labelcheck.py:101` uses one mask from the mean of both
panels; `kurt_attack2.py` and `kurt_levels.py` follow that rule.

**K5' blur plant, mask fixed on the mean of both panels:**

| planted blur | k(sharp) | k(blurred) | ratio |
|---:|---:|---:|---:|
| 0.0 | 3.180 | 3.180 | 1.000x |
| 0.5 | 3.180 | 4.109 | **1.292x** |
| 1.0 | 3.001 | 5.084 | **1.694x** |
| 4.0 | 3.184 | 7.365 | **2.313x** |

**Gradient kurtosis in flat regions RISES on blur.** BUILD-THESIS disqualified
two of its own candidates for rising 1.39x, 5.1x and 12.6x on a blur plant. By
the project's own standard this statistic fails the same test.

**K2' noise null:** 1.302x at 5% added noise, 1.198x at 15%, 0.862x at 30% --
non-monotone, and up to 1.30x on noise alone.

The confounds are the same size as the effect (1.09-2.26x observed).

**K6' mask-fraction sweep, camera-linear, geometry-matched:**

| subject | README | 0.10 | 0.20 | 0.35 | 0.50 | 0.70 |
|---|---:|---:|---:|---:|---:|---:|
| bee-3-cpl | 2.79 | **0.90** | 1.73 | 2.26 | 1.93 | 1.71 |
| bee-1-cpl | 1.89 | 1.65 | 2.34 | 1.82 | 1.34 | 1.04 |
| leaf-2-cpl | 1.57 | 1.30 | 1.43 | 1.58 | 1.65 | 0.74 |
| flowers-cpl | 1.98 | 0.97 | 1.24 | 1.65 | 1.93 | 2.44 |
| tweezers-cpl | 1.17 | 0.67 | 1.03 | **1.86** | 0.99 | 1.06 |
| flat-on-ruler-cpl | 1.01 | 1.11 | 1.12 | 1.09 | 1.07 | 0.98 |

The per-subject **ordering is not robust**. `frac` was never varied and is
load-bearing: at 0.10 the README's top subject reads 0.90, below unity. Three
implementations of "the same" statistic give bee-3 = 2.79 (README, via 8-bit
gamma PNGs), 3.58 (my `vinvent2.py`) and 2.26 (here). The magnitude is not
stable enough to quote per subject.

What IS robust: absolute levels against the pure-noise (Rayleigh) reference of
3.245.

| subject | k(merge) | k(argmax) | ratio |
|---|---:|---:|---:|
| bee-3-cpl | 5.947 | 13.420 | 2.26 |
| bee-1-cpl | 9.325 | 16.926 | 1.82 |
| leaf-2-cpl | 3.601 | 5.683 | 1.58 |
| flowers-cpl | 4.605 | 7.582 | 1.65 |
| tweezers-cpl | 15.627 | 29.136 | 1.86 |
| flat-on-ruler-cpl | 5.338 | 5.811 | 1.09 |

Both arms sit far above pure noise, so this is structure and not the noise gap;
argmax carries the heavier tail on 6 of 6 at frac 0.35 and on 5-6 of 6 across
frac 0.20-0.50. `flat-on-ruler-cpl` is the exception at every fraction tested
and in every implementation.

Two caveats on that exception. `tweezers-cpl` moves 1.17 -> 1.86 camera-linear,
which breaks the README's "near-planar target, so selection is well-posed"
narrative -- tweezers has the *highest* absolute gradient kurtosis of any
subject. And on `flat-on-ruler-cpl` the merge is 0.33 px softer (measured
above); K5' says 0.5 px of blur inflates kurtosis about 1.29x, which is enough
to suppress a ratio of ~1.3 to the observed 1.09. The exception may be the
softness confound rather than an absence of invented structure.
"""

p.write_text((doc.rstrip() + add).replace("\r\n", "\n"), encoding="utf8", newline="")
print(f"wrote {p}, {p.stat().st_size} bytes")
