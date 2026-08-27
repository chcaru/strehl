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
matched exposure, **a 149-frame merge is 10.4% sharper at 0.20-0.25 cyc per
output pixel than the full 299-frame merge**, R = 1.1037, CI [1.0754, 1.1376].

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
re-rendered and the criterion returned R = 1.1037 [1.0754, 1.1376] again, to four
decimals.

## The curves

Values above 1 mean the SHALLOWER stack is SHARPER. Bands are cyc per OUTPUT
pixel on the 7032x4688 shipping grid, where one output pixel is one photosite.

`bee-1-cpl`, N=299:

| N | 0.05-0.10 | 0.15-0.20 | **0.20-0.25** | 0.25-0.30 | 0.30-0.35 |
|---:|---:|---:|---:|---:|---:|
| 8 | 0.0659 | 0.0571 | 0.1190 | 0.2294 | 0.3123 |
| 32 | 0.5350 | 0.4070 | 0.4552 | 0.5453 | 0.6598 |
| 64 | 0.7821 | 0.7780 | 0.7993 | 0.8778 | 0.9741 |
| 100 | 0.9127 | 0.9656 | 1.0328 | 1.0759 | **1.1367** |
| 200 | 0.9518 | 0.9949 | **1.0564** | **1.1054** | 1.1118 |
| 299 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

`113MSDCF`, N=63: peak at N=16-32 above 0.25; **+15.0% at 0.30-0.35** for N=16
against the full stack. At 0.20-0.25 it is flat (+0.2%, not significant).

`flower-bud-alone-cpl`, N=205: 0.2954 at N=8 rising monotonically to 1.0000 at
N=205, at **every** band. No falling limb anywhere.

**The shape is two-limbed.** Below a subject-specific N* the bracket is still
buying focus COVERAGE and depth helps, steeply. Above N* the only thing another
frame adds is another near-tied competitor, and the merge softens. N* is roughly
16-32 for `113MSDCF`, 100-200 for `bee-1-cpl`, and at or beyond 205 for
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
| `bee-1-cpl` | 299 vs 149 | **1.1037** | [1.0754, 1.1376] | **FAIL** |
| `113MSDCF` | 63 vs 31 | 0.9623 | [0.9546, 0.9744] | PASS |
| `flower-bud-alone-cpl` | 205 vs 102 | 0.9018 | [0.8562, 0.9253] | PASS |

Partition: **3 attempted = 2 pass + 1 fail + 0 void.**

Commissioning, primary band, all four arms required: NULL 1.0 exactly, DEGRADE
0.1504, **IMPROVE 2.5486**, REFPERT 6.6509. The IMPROVE arm is the load-bearing
one -- it proves the statistic is free to reward a build rather than bounded
below.

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
