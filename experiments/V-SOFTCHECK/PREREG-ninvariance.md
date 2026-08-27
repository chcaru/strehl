# Pre-registration: the N-invariance acceptance criterion

Written and committed BEFORE it is applied to any candidate build. Pin for every
baseline number: `9b05d0b7`, binary sha256 `44C2F2CD2E5B2894...`.

## The property being certified

> At matched focus RANGE and matched exposure, deepening a bracket must not make
> the merged master measurably SOFTER.

This is a one-sided property. Depth is allowed to help as much as it likes; it is
not allowed to hurt. Below the coverage-saturation point depth genuinely helps and
the criterion must not penalise that, which is why the test is one-sided.

## Construction

Two arms from one capture:

- **FULL** — every frame.
- **HALF** — `linspace(0, N-1, N//2)` rounded and de-duplicated. The first and last
  frame are pinned into the subset by construction and asserted on disk. The form
  `frames[::N//n][:n]` is forbidden: it truncates the focus range, and it has
  silently done so on this project before.

Both arms are rendered by the same binary with the SAME explicit `--exposure`.
`--auto-exposure` is forbidden here: it solves a different gain per arm and the
statistic is exactly linear in gain.

Statistic: Hann-windowed 256x256 tile FFT, radial ring band power, 300 tiles
selected by 0.02-0.05 cyc/px energy only. The selecting band is disjoint from
every reported band, so tile choice cannot favour either arm.

`R = median over tiles of ( band power of HALF master / band power of FULL master )`

with a 1500-sample bootstrap CI over tiles. Masters are registered to each other
by an INTEGER-ONLY shift; sub-pixel resampling would add blur to the measured
quantity.

## Bands

Primary gate: **0.20-0.25 cyc per OUTPUT pixel**, where 1 output pixel = 1
photosite on the 7032x4688 shipping grid. This is the only band currently
promotable on this project.

Reported but NOT gated: 0.25-0.30 (demoted). Bands above 0.30 are withdrawn and
are not grounds for failing a build.

## Decision rule, fixed in advance

| outcome | rule |
|---|---|
| **FAIL** | CI lower bound > 1.0 in the primary band -- the shallower stack is significantly sharper |
| **PASS** | CI lower bound <= 1.0 in the primary band |
| **VOID** | range assertion failed, exposure lines differ between arms, or the commissioning arms did not all pass |

`VOID` is not a pass. A run that cannot be trusted is reported as its own outcome.

## Standing baselines, measured on the current shipping pin

| subject | N | primary band 0.20-0.25 | CI | verdict today |
|---|---:|---:|---|---|
| `bee-1-cpl` | 299 vs 200 | **1.0564** | [1.0294, 1.0742] | **FAIL** |
**Amendment, recorded after measuring.** The table above used the nearest
subsets already rendered, not the exact `N//2` arms this document specifies. The
exact `N//2` arms were then rendered and the criterion evaluated on them; the
DECISION RULE above is unchanged and was not touched after seeing data. Measured
on the specified arms: `bee-1-cpl` 299 vs 149 R = 1.1037 [1.0754, 1.1376] FAIL;
`113MSDCF` 63 vs 31 R = 0.9623 [0.9546, 0.9744] PASS; `flower-bud-alone-cpl` 205
vs 102 R = 0.9018 [0.8562, 0.9253] PASS.
| `113MSDCF` | 63 vs 32 | 1.0025 | [0.9911, 1.0114] | PASS |
| `flower-bud-alone-cpl` | 205 vs 150 | 0.9717 | -- | PASS |

The originating observation, retained as the headline regression number, is
`113MSDCF` at **0.30-0.35: 63 frames is 0.114 softer than 32** of the same range.
That band is withdrawn for promotion purposes, so it is recorded as context and
is not the gate.

`bee-1-cpl` is the standing FAIL the build lane must clear. A fix that clears it
must not do so by making the HALF arm worse: the criterion is therefore paired
with an absolute check that the FULL master's band power does not fall relative
to the pinned value recorded here.

## Commissioning required before any run counts

Four arms, all of which must pass or the run is VOID:

| arm | requirement |
|---|---|
| NULL | a master against itself reads exactly 1.0000 |
| DEGRADE | a blurred HALF arm must push R DOWN |
| IMPROVE | a sharpened HALF arm must push R UP |
| REFPERT | perturbing the FULL arm must move R |

The IMPROVE arm is the one that matters most: it proves the statistic is free to
reward a build rather than being bounded below, which is how this project shipped
a metric that could never charge for the defect it existed to catch.

## What this criterion does NOT establish

It does not show the depth cost is universal. It is measured absent on
`flower-bud-alone-cpl`, whose curve rises monotonically to N=205 with no falling
limb at any band. Any claim that "the merge gets worse as stacks get deeper"
stated without qualification is contradicted by that subject and must not be made.

