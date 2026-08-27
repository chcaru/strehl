# RETRACTION: the clip-to-zero defect is NOT fixed at HEAD

In commit `c6f21874` I reported that ORCH's clip-to-zero defect "is fixed at
HEAD" and recommended they re-render `clean6` because "the flip you halted may
not need to be halted."

**That was wrong, and the way it was wrong is the exact failure ORCH had just
warned me about.**

I measured the defect with an **exact-zero** statistic only. ORCH's defect has
three columns, and I checked the smallest one. A repair that lifted the crushed
region off the zero rail without fixing what drives it there reads 0.0000% on an
exact-zero instrument while leaving the region intact. That is what happened.
It lifted the region 750 DN and left 71% of the crushed pixels crushed.

I wrote the sentence describing this failure mode at the top of the message in
which I discovered it, as a reason to check. It was not a hypothetical.

## The measurement that corrects it

`crushcensus.py`, ORCH's paired third column (`ctrl - arm > 2000 DN`), null and
pin controls in the same run. Reference is ORCH's own `clean6` ctrl.

| arm | crush px | crush % | ctrl med | arm med | exact0% | luma<500% |
|---|---:|---:|---:|---:|---:|---:|
| null (ctrl vs itself) | 0 | 0.000% | - | - | 0.000% | 0.002% |
| **PIN gate 4** (ORCH's arm) | **721,189** | **2.185%** | **3920.7** | **878.0** | **0.371%** | **1.310%** |
| **HEAD gate 4** | **510,415** | **1.547%** | 4074.5 | **1628.7** | 0.000% | 0.000% |
| HEAD gate 2 | 509,749 | 1.545% | 4073.9 | 1627.8 | 0.000% | 0.000% |

The pin row reproduces ORCH's figures to the digit — 721,189 px, 2.185%,
3920.7 DN, 878.0 DN — so the instrument is commissioned as potent, and the null
row is exactly 0.0 in every cell, so it is commissioned as quiet.

Geometry, which is the part that settles it:

| arm | bbox | centroid |
|---|---|---|
| PIN gate 4 | y 744..4687, x 1668..5104 | y 3169 x 3678 |
| HEAD gate 4 | y 744..4687, x 1668..5104 | y 3114 x 3569 |

**The bounding box is identical to the pixel.** The region did not move, shrink
at its edges, or break up. It is the same contiguous failure, 29% smaller in
population and lifted off the rail.

## What the two unpaired rails were actually measuring

At HEAD, `exact0` is 0.000% and `luma<500` is 0.000% — the latter *below* the
ctrl's own 0.002%. Both of ORCH's unpaired columns are genuinely clean at HEAD.
They are simply not sensitive to a region sitting at 1628 DN instead of 4074 DN.
Nothing about those two numbers was wrong; they were answering a question whose
answer no longer discriminated.

## One thing this does establish

HEAD gate 4 and HEAD gate 2 differ by 666 pixels out of ~510,000 — **0.13%**.
The fallback fraction changes enormously between those two gates on this subject
(level 0 goes from a minority to 49.1%), and the crush does not move.

**So the crush is gate-independent, which rules out ORCH's candidate 3** (the
sub-gate fallback interacting with the base band). Whatever this is, it is not
the fallback, and it is not anything else the gate controls.

## Where it points instead

`blend-render.rs:136` carries a comment I wrote earlier in this project:

> "Reproduces the mid-tone clip: without the hull clamp the reconstruction may
> emit values no input frame supports, which on real stacks crushes dark pixels
> to exact zero."

So `Hull::InputRange` was already the partial repair, and it is already the
default. That reframes ORCH's candidate 2 rather than eliminating it: the
reconstruction *is* emitting values no input frame supports, the hull clamp is
catching them at `min_k`, and `min_k` is still far below what the estimator
produces. The clamp converts an impossible value into a merely wrong one.

If that is right, the crushed pixels should sit *at* the hull floor, and
`--unclamped` should be dramatically worse in the same bbox.

## It is right, and the result is stronger than predicted

| arm | crush px | crush % | ctrl med | arm med | exact0% | luma<500% | p0.01 | p99.99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **PIN gate 4** | **721,189** | **2.185%** | 3920.7 | **878.0** | 0.371% | 1.310% | -8454.8 | 4863.2 |
| **HEAD `--unclamped`** | **721,189** | **2.185%** | 3920.7 | **878.0** | 0.371% | 1.310% | -8454.8 | 4863.2 |
| HEAD (default hull) | 510,415 | 1.547% | 4074.5 | 1628.7 | 0.000% | 0.000% | -8002.7 | 3813.9 |
| HEAD `--per-level` | 485,177 | 1.470% | 4084.8 | 1677.6 | 0.000% | 0.000% | -7990.6 | 3785.2 |

`--unclamped` at HEAD does not merely resemble the pin. It reproduces it in
**every cell of the table**, including all five percentiles to the decimal, and
the identical bbox and centroid. The two renders are statistically
indistinguishable.

Two things follow immediately:

1. **ORCH's `clean6` blend arm is an unclamped render.** The "something between
   the pin and HEAD that repaired it" is `Hull::InputRange` becoming the
   default. There is no mystery commit to find.
2. **The hull clamp is saturated across the crushed region.** Removing it
   restores the defect exactly, so the crushed pixels sit *at* `min_k`: the
   reconstruction is trying to go below every input frame and the clamp is
   catching it. The clamp converts an arithmetically impossible value into a
   merely wrong one. It is a floor, not a fix, and `--per-level` (485,177) is
   the same floor at a different height.

So the defect is not "the output is clipped". It is **"the reconstruction is
wrong over a contiguous 500,000-pixel region, and the clip is the symptom by
which it announces itself."** That is a much better-posed problem, and it is
squarely inside `pyramid.rs`.

## The mechanism this implicates

A per-level winner-take-all selection chooses the max-|L| frame **independently
at every level**. The Laplacian coefficients of a *single* frame at different
levels are not independent — they are different-scale views of the same edge and
they carry a consistent sign structure. Selecting level 0 from frame 12, level 1
from frame 80 and level 2 from frame 31 sums three coefficients that never
coexisted in any observation, and the sum need not lie within the hull of the
inputs.

The error is largest where the coefficient magnitudes are largest, which on this
subject is the dark subject against bright ground — exactly the region ORCH
bounded. It is also gate-independent, which matches, and it survives every
fallback arm, which also matches.

If this is the mechanism, the crush should track **selection sharpness**: near
zero when weights are uniform (a plain average, in hull by construction) and
worst under `--hard-max`. That ladder is the discriminator.

## The ladder confirms it

All three `--unclamped`, so the hull floor cannot mask the ordering.

| selection | crush px | crush % | ctrl med | **arm med** | **exact0%** | luma<500% |
|---|---:|---:|---:|---:|---:|---:|
| `--exponent 0` (uniform) | 371,584 | 1.126% | 17766.9 | **13167.9** | **0.000%** | 0.000% |
| default exponent | 721,189 | 2.185% | 3920.7 | **878.0** | **0.371%** | 1.310% |
| `--hard-max` | 1,008,530 | 3.056% | 3836.4 | **396.8** | **1.612%** | 3.966% |

Monotone in every column that matters. Sharpening the selection nearly triples
the crushed population, drops the region's median from 13168 DN to 397 DN, and
takes the exact-zero rail from nothing to 1.6% of the frame.

**One caveat, stated because the top-line number invites a wrong reading.** The
`ctrl - arm > 2000 DN` threshold flags *any* darkening, not only crushing, so
`--exponent 0` still shows 371,584 pixels. Those are not crushed: their ctrl
median is 17766.9 DN and their arm median is 13167.9 DN, with **zero** exact
zeros. That is a broad tone difference on bright pixels — expected, since
uniform weights are a plain average with no focus selection at all — and it is a
different phenomenon wearing the same threshold.

The columns that separate the two cases are `arm med` and `exact0%`, and they
are unambiguous: uniform weighting has no crush, and crush severity rises
monotonically with selection sharpness. Printing the rails beside the centre is
what made that legible, which was ORCH's instruction and it was the right one.

## Conclusion

The defect is cross-scale selection incoherence in the Laplacian merge. It is:

- **gate-independent** (510,415 vs 509,749 across gates 2 and 4)
- **fallback-independent** (survives every fallback arm measured)
- **monotone in selection sharpness** (371,584 -> 721,189 -> 1,008,530)
- **masked, not fixed, by the hull clamp** (`--unclamped` reproduces the pin exactly)

That combination is not consistent with any of the three mechanisms ORCH
proposed as stated, and it is consistent with per-level independent selection
summing coefficients that never coexisted in a single observation.


## Correction to the record

My recommendation in `c6f21874` — "re-render `clean6` at HEAD before any further
work on this, the flip you halted may not need to be halted" — is withdrawn.
**The halt is correct. Do not flip the default.**
