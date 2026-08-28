# V-SOFTCHECK: the half-stack discriminator does not implicate selection

**Lane:** V-SOFTCHECK (independent verification).
**Pin:** SHIP-V4 `9b05d0b7`, binary sha256 `44C2F2CD2E5B2894...`, verified by hash before every render.
**Band:** 0.20-0.25 cyc per OUTPUT pixel on the 7032x4688 grid (`PRIMARY`) unless stated.
**Renders:** interleaved half-stack pairs, `--srgb --exposure` passed explicitly and
identically to both arms (`bee-1-cpl` +1.50, `119MSDCF` +1.53, `113MSDCF` +2.33).
`--auto-exposure` is forbidden here: the statistic is gain-free only if the arms match.

## Summary

The orchestrator proposed a single number to discriminate three hypotheses:

> the merge's per-pixel frame choice disagreeing between two independent half-stacks
> at a rate above what the scene justifies is evidence for selection; agreement
> alongside lost detail is evidence for alignment or for depth dilution.

I own that number. **As specified it cannot discriminate**, and after building an
instrument that can, **the answer does not implicate selection on either subject I
could measure.** On the deepest subject the entire contrast-proportional signal is
accounted for by residual misregistration between the two arms.

| subject | N | incoherence `f` at 0.20-0.25 | shape | residual within-tile warp | warp explains |
|---|---:|---:|---|---:|---:|
| `119MSDCF` | 32 | 0.8810 (anchor decile) | noise-shaped | 0.161 px | **3.7%** |
| `bee-1-cpl` | 298 | 0.8671 (anchor decile) | contrast-proportional | 1.354 px | **87.3%** |
| `113MSDCF` | 62 | 0.7807 | REFUSED, flat calibration | not measured | not measured |

**3 attempted = 2 measured + 1 refused + 0 failed.**

## 1. Why the raw discriminator cannot discriminate

`f = 1 - gamma` between the two half merges is dominated by a term that has nothing
to do with frame choice. Measured on `119MSDCF`, sorting tiles by scene contrast in
0.02-0.05 cyc/px (a band disjoint from every reported band, so the stratifier cannot
be the thing measured):

    top-contrast decile   f = 0.2334
    bottom decile         f = 0.8834

`f` rises monotonically as contrast falls. That gradient is the signature of an
independent additive term, and **on this data it is larger than the effect being
discriminated.** A lane reading raw `f` would report a noise floor as selection
disagreement. Three separate instruments confirmed the gradient before I accepted it.

The first separator I built assumed a noise-immune high-contrast decile and bounded
selection there. It **failed its own commissioning**: white noise at 0.05 sigma reads
`0.5785` in the TOP decile. There is no noise-immune decile. `hselrun.py` is retained
as the artifact of that refutation rather than deleted.

## 2. The instrument that works, and the gate that reversed its answer

Statistic: `fall = f(anchor contrast decile) / f(top decile)`, a ratio on the same
image, so common amplitude cancels. Additive noise falls steeply with contrast;
content-proportional incoherence stays flat. Calibrated by planting a blob-mask
frame-choice model at mix lambda and bisecting a white-noise amplitude until the
anchor decile matches the real pair, so every rung carries the same incoherence and
differs only in how much of it is content-proportional. lambda = 0 and lambda = 1 are
both reachable: the instrument is free to answer either way.

Two plants were discarded before this one. A pure blur is **not** a valid model of
frame choice, because gamma is normalised and a smooth MTF difference barely moves
it. My first structured plant was **circular** -- it injected a fraction of the real
A-B difference, the very thing under test.

**A saturation gate changed the answer.** `NOISE_NULL` puts the independent limit at
`1 - 1/sqrt(4604) = 0.98526`. `bee-1-cpl`'s bottom decile sits at 0.9822, which is
saturated: every plant matches it trivially and the match then over-drives the plant.
The signature was visible from outside -- all five rungs converged on the bisection's
*first* midpoint, amp 0.1500. Re-anchoring on the first decile below 0.90 moved bee
from a content-proportional share of **0.00 to 0.85**. The gate is the result.

| subject | N | anchor | real fall | pure-noise rung | content-proportional share |
|---|---:|---:|---:|---:|---:|
| `119MSDCF` | 32 | decile 0, f=0.8810 | 4.554 | 3.309 | **0.00** |
| `113MSDCF` | 62 | decile 1, f=0.7807 | 2.039 | 1.321 | REFUSED (spread 1.106 < 1.30) |
| `bee-1-cpl` | 298 | decile 3, f=0.8671 | 2.016 | 3.583 | **0.85** |

## 3. The 0.85 is not selection

The fall ratio separates content-proportional incoherence from noise. **It does not
separate frame choice from misregistration**, because both are proportional to scene
content: a shifted edge and a defocused edge both differ from the reference by
something scaling with the local gradient. `pair_stats` removes each tile's own
constant shift exactly, as a phase ramp. Within-tile warp survives.

`hwarp.py` measured the residual per-tile shift field between the two arms, after the
global integer shift:

| subject | median | p90 | max | field spread | median vs 8-neighbour mean |
|---|---:|---:|---:|---:|---:|
| `119MSDCF` N=32 | 0.823 px | 1.27 | 1.82 | 0.351 | **0.161 px** |
| `bee-1-cpl` N=298 | 8.885 px | 34.6 | 97.2 | 14.523 | **1.354 px** |

bee's field is large and **smooth**: neighbour deviation is 0.093 of the field's own
spread. A smooth field is a real warp; a scattered one would be per-tile fitting
noise. The within-tile component -- what pair_stats cannot remove -- is 8.4x larger on
bee than on 119, and bee is the subject that read 0.85.

### The calibrated warp arm was refused

I tried to put warp on the same amplitude-matched ladder. It **failed commissioning
twice**, and the second failure is a property of the statistic, not of my plant:

    d=0 px  f = -0.0000     d=2 px  f = 0.8522
    d=1 px  f =  0.3875     d=3 px  f = 0.7840   <-- DOWN
                            d=4 px  f = 0.9240

`f` is not monotone in displacement and cannot be: coherence in a band centred on
0.225 cyc/px is set by a phase `2*pi*f*s` that **wraps**, so decorrelation oscillates
with shift instead of growing with it. A bisection assumes monotonicity and would
have converged on whichever root it met first. **No shift plant is bisectable on a
band-limited coherence statistic.** I did not tune the plant until it passed.

### The test that needs no calibration

Plant exactly the warp that was *measured*, on a clean pair, and read how much of the
observed incoherence it produces. No bisection, no matching, no monotonicity
requirement. Commissioned in both directions: `d=0` is an exact no-op giving
`f = -0.000000` on bit-identical arms; `d>0` is asserted to change the array;
`f` rises 0 -> 0.1024 -> 0.1910 -> 0.3875 over the m=1 rungs and falls monotonically
back, so the plant is free to improve the image as well as degrade it.

| subject | measured warp | 1x | 2x | 4x | verdict |
|---|---:|---:|---:|---:|---|
| `119MSDCF` N=32 | 0.161 px | 0.0323 = **3.7%** | 0.1211 = 13.7% | 0.2518 = 28.6% | WARP INSUFFICIENT |
| `bee-1-cpl` N=298 | 1.354 px | 0.7566 = **87.3%** | 0.8885 = 102.5% | 0.8900 = 102.6% | WARP SUFFICIENT |

**On `bee-1-cpl` the residual misregistration between the two arms is, on its own,
sufficient to produce the observed incoherence.** I therefore withdraw the 0.85 as a
selection number. On `119MSDCF` warp accounts for 3.7% and the shape is noise, so it
is not selection either.

**I have no positive evidence for the frame-selection mechanism on either subject.**

## 4. What could still make me wrong

- **The plant over-states warp per pixel, in three ways**, all favouring the warp
  hypothesis: it varies at 64 px against a 256 px measurement tile and a field
  measured at 256 px spacing; each displaced block leaves a hard boundary
  discontinuity real warp would not have; and its random directions leave the
  tile-mean shift near zero so almost all of the displacement survives as the
  within-tile component. **87.3% is an upper bound on warp's contribution, not a
  point estimate.** The safe claim is sufficiency, not attribution.
- **The plant saturates just above the observed value** (102.5% at 2x, 102.6% at 4x).
  Bee's real `f` sits essentially at that ceiling, so the test cannot distinguish
  "warp exactly explains it" from "warp plus anything else, all saturating".
- **Selection can masquerade as warp.** If the two halves choose frames far apart in
  the bracket at the same site, focus breathing renders that as a local displacement.
  The halves are **interleaved** (`sub[0::2]`, `sub[1::2]`, both spanning the full
  range, first and last indices asserted on disk), so adjacent-frame breathing is
  small -- but a noise-driven winner could still pair frame 40 against frame 220.
  **The smoothness is the discriminator:** a noise-driven per-pixel choice produces a
  field that is incoherent between neighbouring tiles, and bee's field is smooth at
  0.093 of its own spread. That is an alignment signature, not a selection one.
- `113MSDCF` is **unbounded and refused**. No share is claimed for it.

## 5. The border audit -- the mean-only failure shape

The tone lane warned of a self-test that asserted only the mean of a field whose
defect was at the borders. I checked my own harness for that shape:

| subject | border tiles | interior tiles | median over all | border warp | interior warp |
|---|---:|---:|---:|---:|---:|
| `119MSDCF` | 42: f=0.8770 | 400: f=0.8398 | 0.8497 | 1.207 px | 0.781 px |
| `bee-1-cpl` | 68: f=0.8846 | 400: f=0.7089 | 0.7675 | 12.217 px | 8.208 px |

The field is **not** uniform: on bee the borders read 0.176 higher than the interior
and carry 49% more residual shift. A statistic asserted only on the median would
report a number no tile actually holds. Every share above is anchored on contrast
deciles rather than on a global median, so the gradient is measured rather than
averaged away, but the border excess is stated here so nobody quotes a single `f`.

## 6. Standing warnings this lane has already reproduced

- **`f` must never become an acceptance criterion.** I planted the maximal
  coherence-only "fix" `(A+B)/2`: it scores `f = 0` and half-difference noise `= 0`
  exactly, while costing **29.6%** of delivered band power, matching the closed form
  `(1+gamma)/2` to 0.0123 across seven bands. This is the orchestrator's "on blotch
  alone the worst arm wins", reproduced independently before it was relayed. Any
  before/after must carry a statistic that coherence alone cannot move.
- **Total incoherence falls with N** (`f(N_max)/f(N_min)`: bee 0.5771, `113MSDCF`
  0.4637, `119MSDCF` 0.8408 -- P1 = FALL on all three). The orchestrator's prediction
  that disagreement should *rise* with N is **refuted as stated**. My
  pre-registration protected only the RISE sign, so a selection term rising more
  slowly than the noise term falls would be invisible; absolute `f` is an upper bound.

## Files

`hcoh.py` (core, committed `a675e215`), `hsel.py`, `hshape.py`, `hselrun.py`
(the separator that failed commissioning, retained), `hmixrun.py`, `hwarp.py`,
`hwarpmix.py` (the refused calibrated warp arm, retained), `warpbudget.py`.
Machine-readable: `C:\dev\strehl-out\V-SOFTCHECK\hcoh\{hmix,warpbudget}.json`.
