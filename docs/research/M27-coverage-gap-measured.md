# M27 — Is a focus-bracket coverage gap detectable from the stack alone?

> **NOT INDEPENDENTLY VERIFIED.** Measured by the orchestrator. Rule 12 binds
> its author exactly as it binds any milestone author.

Review item **R19** — *"close the reshoot loop"* — calls §1's fourth product idea
(separate *retouch-this* from *reshoot-this*) **"the most differentiating sentence
in the plan"**, and notes it has no design. Before designing anything, this
milestone asks the prior question: **can the pipeline tell, from the stack alone,
that the bracket did not cover the subject?**

The experiment has **ground truth by construction**. Remove frames from a real
bracket, and the pixels whose best frame was among those removed have provably
lost their focus coverage. Nothing is planted, nothing is simulated.

Instrument: `coffee-bean` (105 frames, ISO 50, f/8), every 2nd frame → **53
frames**, green sublattice, centred 1500×1500 crop, Sobel magnitude box-filtered
at `R = 2`.

## 1. MEASURED — yes, a hole in the bracket is blindly detectable

Two detectors that use **only the reduced stack** (no full-stack reference, so
both are deployable at inference time):

- **`curv`** = `(2·f[k] − f[k−1] − f[k+1]) / (f[k] − f_min)` — peak sharpness.
- **`|δ|`** = magnitude of the parabola vertex offset from the argmax sample, in
  `[0, 0.5]` — how far off-centre the peak sits.

Positive group = pixels whose full-stack argmax lies inside the removed block.
Control = a **fixed** band of pixels (`k ∈ [26,34)`, 6,937 px) that no tested gap
touches, identical in every row. Null = the same number of frames removed from
the far end of the stack, where no pixel in either group peaks — this isolates
*"frames were removed"* from *"**your** frames were removed"*.

| gap (frames) | pos n | curv ratio | curv null | **curv excess** | \|δ\| ratio | \|δ\| null | **\|δ\| excess** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 63,942 | 1.879 | 1.428 | **+0.452** | 0.668 | 0.832 | **−0.164** |
| 2 | 143,672 | 2.463 | 1.404 | **+1.059** | 0.380 | 0.864 | **−0.484** |
| 4 | 376,467 | 2.672 | 1.416 | **+1.256** | 0.486 | 0.847 | **−0.361** |
| 6 | 584,778 | 2.805 | 1.412 | **+1.393** | 0.564 | 0.865 | **−0.301** |
| 8 | 776,356 | 2.757 | 1.426 | **+1.331** | 0.629 | 0.862 | **−0.234** |
| 12 | 859,400 | 2.408 | 1.421 | **+0.987** | 0.765 | 0.867 | **−0.102** |

**The null is stable at 1.40–1.43 (curv) and 0.83–0.87 (|δ|) across every row**,
so the depth-band confound — gap-band pixels naturally have sharper peaks than
the far control band — is constant and the excess is the signal. Both detectors
fire from a **single missing frame**.

## 2. MEASURED — but the gap disguises itself as a *better* peak

Read the direction of those numbers. A coverage gap makes the through-focus curve
**sharper** (curvature ratio up to 2.81 against a control of ~0.40 absolute) and
**better centred** (|δ| falls from 0.23 to 0.088 — closer to a perfectly
sample-aligned peak).

I had predicted the opposite for both, and the reasoning was wrong in an
instructive way. I expected the true peak to fall *between* retained samples,
driving `|δ| → 0.5`. What actually happens is that when the frames around the
true peak are removed, the surviving frames on either side sit at **roughly equal
focus distance** from it — so the sampled curve is close to symmetric, and δ goes
to **zero**. The gap does not look like a badly sampled peak. It looks like a
textbook one.

**This is the third independent instance of the same pattern in this project:**

| # | Situation | Metric reads | Information present |
|---|---|---|---|
| fact 73 | untextured monotone edge | focus magnitude **high** (37.04 vs 45.13 for sharp texture) | **zero** |
| fact 203 | pixel clipped in every frame | peak contrast **1.0000, its maximum** | **zero** |
| **M27** | **best frame missing from the bracket** | **peak sharper, better centred** | **absent** |

Three different failure modes, three different metrics, all failing in the same
direction: **confident where there is nothing to be confident about.** That is
not a coincidence about any one metric; it is what happens when a statistic is
computed over a neighbourhood that contains no evidence — degenerate inputs make
clean-looking outputs. Proposed as discipline 120.

## 3. MEASURED — uniform under-sampling, and it needs no optics model

§1's experiment removes a contiguous block: a **hole**. The commoner real failure
is different — focus steps that are **uniformly** too coarse. Then every pixel is
equally affected and there is no internal control by construction, so §1's
comparative method cannot work at all.

I expected this to be the wall, and predicted the reshoot advisor would need the
optical model to supply a *predicted* peak width. **That is refuted.** Decimating
the whole stack moves the detectors' **absolute** values monotonically:

| decimation | frames | median `curv` | median \|δ\| | median `nwide` |
|---:|---:|---:|---:|---:|
| ×1 | 53 | 0.561 | 0.2005 | **3.00** |
| ×2 | 27 | 1.128 | 0.1163 | **2.00** |
| ×3 | 18 | 1.391 | 0.0773 | **1.00** |
| ×4 | 14 | 1.535 | 0.0522 | **1.00** |
| ×6 | 9 | 1.668 | 0.0371 | **1.00** |

`nwide` = the number of retained frames within 50% of the peak height. **It has
an absolute, reference-free interpretation**: `nwide = 1` means the peak is
resolved by a single sample and its true location is unrecoverable. No optics
model, no reference stack, no calibration is required to read that.

**Confound closed (rule 17).** `nwide` divides by `(peak − min)`, and decimation
estimates `min` from fewer samples — which would raise `min`, raise the
half-height threshold and shrink `nwide` **with no change in peak width at all**,
reproducing the whole trend spuriously. Holding the threshold at the **full-stack**
minimum gives an identical column (3.00 / 2.00 / 1.00 / 1.00 / 1.00), and the
median minimum itself drifts only 1.000 → 1.195. The trend is real.

## 4. The deployable criterion, and a verdict on real capture practice

Fraction of reliable pixels whose peak is resolved by **one sample or fewer**,
using the confound-free threshold:

| frames | pixels under-resolved |
|---:|---:|
| 53 | **0.01%** |
| 27 | **37.46%** |
| 18 | 59.91% |
| 14 | 69.06% |
| 9 | 75.76% |

This is the reshoot signal: per-pixel, absolute, blind, and directly phrasable as
the recipe R19 asks for — *"38% of the subject is resolved by a single frame;
halve the focus step."*

**MEASURED verdict on the owner's own capture:** at 53 frames only **0.01%** of
the subject is under-resolved, so `coffee-bean`'s **105-frame bracket is roughly
2–4× denser than it needed to be** at f/8. The bracket is not too coarse; it is
comfortably too fine.

**DERIVED, and contingent — the two capture findings cancel.** M20 argues for
opening from marked f/11 to f/5.6 to buy 9.6× contrast at 4-px detail, at the
cost of ~2× the frames for the same depth. M27 measures ~2–4× surplus sampling
density at f/8. **So the aperture change M20 wants is roughly free in frame
count** — the frames are already being spent. This is DERIVED, not measured: it
chains M27's f/8 measurement to a depth-of-field scaling from the optics model
that **M20's verifier is currently checking for circularity**. If that gate is
tautological, this inherits the problem.

## 5. What I got wrong

1. **Predicted `|δ| → 0.5` at a gap; measured `|δ| → 0`** (§2). The mechanism is
   that surviving frames flank the true peak at near-equal distance, so the curve
   reads symmetric. This is the finding, not a footnote — it is why the gap is
   dangerous.
2. **Predicted uniform under-sampling would need the optical model; it does not**
   (§3). `nwide` is absolute.
3. **My first detector was an oracle.** Step 1 scored `f_reduced / f_full`, which
   divides by a full-stack peak that does not exist at inference time. It gave a
   beautiful monotone table (peak loss 16% / 26% / 49% / 62% / 73% for gaps of
   1/2/4/6/8) that measures **effect size**, not detectability. Retained as an
   effect-size result only; it is not a detector and must never be cited as one.
4. **My first control drifted.** Defining the control relative to the gap made it
   a different population as the band widened — its own `nwide` went 3 → 14.
   Fixed by defining one control band once.

## 6. What was NOT measured

- **One stack, one crop, one operator, one radius.** `coffee-bean` only, a
  centred 1500×1500 crop of the green sublattice, Sobel at `R = 2`. Fact 152
  says radius matters a great deal for through-focus structure.
- **Frames are not aligned.** Breathing moves pixels across the crop; this
  inflates all curves somewhat and is not corrected.
- **A "hole" is not the field failure mode.** §1 simulates a bracket with a block
  missing (skipped frames, corrupt files). Real under-coverage is §3's uniform
  case, and §1's comparative detectors cannot address it.
- **The reliability filter is an oracle** — "reliable" pixels are selected using
  the *full* stack. That is an analysis choice to make "true argmax" meaningful
  (the rule-17 guard against noisy pixels being assigned a random truth and then
  flagged for noise reasons); it is **not** part of the detector, and a shipped
  version needs a blind reliability criterion.
- **No genuinely under-sampled real stack was tested.** Every number here comes
  from decimating a well-sampled one, which assumes decimation is equivalent to
  having shot coarsely. It is equivalent optically but not photometrically —
  a real coarse bracket would have different breathing and drift per step.
- The `nwide ≤ 1` threshold is asserted from the sampling argument, not tuned or
  validated against a reconstruction-quality outcome.

## 7. Proposed record

Facts **210–213**, discipline **120–121**, question **40**. Reconciled by the
orchestrator at fold time, not here.

## 8. Reproducing

```
experiments/m27-coverage-gap/src/
  00-build-volume.py     dense focus volume from coffee-bean (105 -> 53 frames)
  01-first-look.py       the oracle detector -- effect size only, NOT a detector
  02-blind-detector.py   blind nwide detector, per-width matched nulls
  03-fixed-control.py    fixed control band + continuous blind detectors (the result)
  04-uniform.py          uniform decimation: is under-sampling visible absolutely?
  05-confound.py         closes the min-estimation confound in 04
```
