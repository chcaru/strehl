import io, os
ROOT = r"C:\dev\blog\death-of-software\projects\strehl"

doc = """# V-REVIEW-geometry: does the estimator aura claim generalise beyond one subject?

**VERDICT: `lead-1-cpl` is OFF-GEOMETRY. My earlier 1.02x bounded the claim's
generality; it did not refute its mechanism. Corrected against myself. On two
subjects that do present the named geometry the effect is real in direction and
one to two orders of magnitude smaller than the claimed multiplier.**

**The exact sentence that is safe to say:**

> The estimator does put a deeper dark aura around the subject than the pyramid
> does, and the pyramid is now the default, so that complaint is addressed. The
> direction is real: the estimator's aura is deeper in all seventeen conditioned
> readings across four subjects. The size is strongly subject-dependent -- the
> estimator's excess is 294-3446 DN on `flower-bud-alone-cpl`, 334-1127 DN on
> `bee-2-cpl`, 40-205 DN on `tweezers-cpl` and 5 DN on `lead-1-cpl`. The 28.5x
> multiplier must not be quoted. Across those subjects the ratio runs 0.98x to
> 7.89x, and it moves under a change of overall level that leaves the physical
> difference bit-identical.

## 1. The geometry test, and its commissioning

The claim names a geometry: a dark subject on a bright ground. Whether a subject
presents it is measurable from the master, so I measured it rather than asserting
it. Three quantities, on luminance:

| quantity | definition | reads |
|---|---|---|
| `dark_ratio` | median far field over median subject | above 1 means the subject is darker |
| `surround` | fraction of the near band brighter than half the far field | is the subject actually encircled |
| `ground_iqr` | far-field interquartile range over its median | low means a coherent, uniform ground |

Subject delineation is Otsu on the master, opened and closed, largest connected
component. Commissioned in both directions before use:

| arm | plant | required | measured |
|---|---|---|---|
| G0 | degenerate two-valued field | recover 5.00 | 5.00 |
| G1 | dark disc on flat bright ground | score high | `dark_ratio` 5.00 |
| G2 | low-contrast subject | must not score high | `dark_ratio` 1.18 |
| G4 | bright subject on dark ground | must not read dark-on-bright | refused |
| G5 | flat field, no subject | refuse | refused |
| G6 | ground swept 20k-50k DN | ratio tracks the ground | error 0.0 percent at every step |

G6 is the denominator arm: `dark_ratio` divides by the subject level and is a
ratio to the ground, so the ground is a term the verdict divides by and it was
perturbed on its own. Ground texture was swept separately against a plant of
known amplitude, and `ground_iqr` is monotone in it while `dark_ratio` holds:

| planted ground sd | as percent of ground | `ground_iqr` | `dark_ratio` |
|---|---|---|---|
| 0 | 0 | 0.005 | 5.00 |
| 800 | 2 | 0.028 | 5.01 |
| 2000 | 5 | 0.070 | 5.01 |
| 4000 | 10 | 0.133 | 4.99 |
| 8000 | 20 | 0.261 | 5.09 |
| 14000 | 35 | 0.510 | 4.73 |

That calibrates the real readings into physical terms: `flower-bud-alone-cpl` at
0.03 has roughly a 2 percent textured ground, `lead-1-cpl` at 0.11 roughly
8-9 percent.

**Two defects in my own first attempt, both disclosed here.** The first
commissioning run refused all seven arms including the one that had to pass.
Cause: on a two-valued histogram Otsu returns the *lower* mode, and my strict
`L < cut` then excluded exactly the disc it had just found. The test is now
`L <= cut`. Re-running the corpus screen with the fix moved no real reading, so
the screen below stands. Second, my initial ground-texture plant blurred white
noise at sigma 60 without renormalising, which collapses its amplitude about
200-fold: I planted roughly 254 DN and expected it to move a statistic that
reads 0.03. The instrument was right and the plant was wrong.

## 2. Where the corpus stands

All 26 SHIP-V4 masters, same instrument: 20 measured, 6 refused for having no
coherent subject or no far field. The relevant rows:

| subject | subject percent of frame | `dark_ratio` | `ground_iqr` | geometry |
|---|---|---|---|---|
| `flower-bud-alone-cpl` | 21.1 | 4.52 | 0.03 | the claim's own subject |
| `flower-inner-edge-cpl` | 60.8 | 3.63 | 0.13 | on, incoherent ground |
| `coffee-bean` | 44.2 | 3.38 | 0.14 | on, incoherent ground |
| `109MSDCF` | 22.4 | 3.23 | 0.21 | on, incoherent ground |
| `pencil-steep-angle-cpl` | 61.8 | 2.87 | 0.09 | on |
| `bee-2-cpl` | 41.1 | 2.80 | 0.06 | on |
| `bee-3-cpl` | 39.1 | 2.80 | 0.06 | on |
| `tweezers-cpl` | 59.7 | 2.48 | 0.01 | on, most coherent ground |
| `lavendar-cpl` | 18.3 | 1.86 | 0.16 | weak |
| `leaf-2-cpl` | 34.8 | 1.63 | 0.15 | weak |
| `lead-1-cpl` | 42.9 | 1.57 | 0.11 | off |
| `couch-fibers-cpl` | 18.0 | 1.20 | 0.16 | off |

`dry-erase-marker-head-cpl` has the highest `dark_ratio` in the corpus at 5.26
but a `ground_iqr` of 0.55, roughly a 35 percent textured ground. It has no
coherent bright surround, so it is not the geometry the claim names.

## 3. `lead-1-cpl` is off-geometry

`dark_ratio` **1.57** against the reference subject's **4.52**, and a ground
roughly four times more textured, **0.11** against **0.03**. On the commissioned
scale, 1.57 sits nearer the planted negative control G2 at 1.18 than the
on-geometry regime.

**So the reading I reported earlier bounds the claim rather than refuting it.**
That is the less convenient of the two readings and it is the correct one.

## 4. Two on-geometry second subjects, and a mask defect I had to fix first

`bee-2-cpl` and `tweezers-cpl` were rendered through both merges from the same
pinned binary, `--linear-srgb`.

The fixed 20/30/40/50 percentile mask sweep used in the earlier aura work was
built on a subject occupying 21 percent of the frame. Applied to a subject
occupying 60 percent it masks half the subject, and the 40-100 px "aura" band
then lands on unmasked subject rather than on ground. The symptom was
unmissable: `tweezers-cpl` returned a depression of **16557 DN** on an image
whose overall median is **8171 DN**. A depression cannot exceed the level it is
measured against.

The mask is now anchored on each subject's own measured extent, and every
configuration carries an explicit composition floor: a configuration whose aura
band is less than 70 percent ground is **refused, not scored**. That floor
catches precisely the rows that produced the impossible number.

## 5. The aura re-measured

Partition over four subjects, eight configurations each: **17 measured, 15
refused**, summing to 32. Refusals are aura-band contamination, a denominator
below 300 DN, or too few pixels. A refusal is not a clean result.

| subject | `dark_ratio` | measured | refused | denominator DN | estimator excess DN | ratio |
|---|---|---|---|---|---|---|
| `flower-bud-alone-cpl` | 4.52 | 5 | 3 | +500 to +1000 | +294 to +3446 | 1.35-7.89 |
| `bee-2-cpl` | 2.80 | 7 | 1 | +414 to +3025 | +334 to +1127 | 1.22-2.02 |
| `tweezers-cpl` | 2.48 | 4 | 4 | +627 to +8370 | +40 to +205 | 1.01-1.13 |
| `lead-1-cpl` | 1.57 | 1 | 7 | -343 | +5.5 | 0.98 |

**The direction survives everywhere.** The estimator's aura is deeper than the
pyramid's in all seventeen conditioned readings, across every subject including
the off-geometry one. That is the part of the original claim that holds.

**The magnitude does not generalise.** Ordering the subjects by their largest
estimator excess reproduces the geometry ordering exactly, and spans nearly three
orders of magnitude from 3446 DN to 5.5 DN. Nothing here reaches 28.5x: the
largest conditioned ratio anywhere is **7.89x**, and it sits on the smallest
surviving denominator, which is the pole again.

Photometric checks, since a self-referenced statistic is only safe if the arms
share a space: level ratios 0.9883 for `bee-2-cpl`, 1.0085 for `tweezers-cpl`,
0.9831 for `flower-bud-alone-cpl`, 1.0056 for `lead-1-cpl`. All arms were hashed
and confirmed distinct before comparison.

## 6. Commissioning the aura statistic on this configuration

Not carried over from earlier work. Substrate `bee-2-cpl`, baseline excess
+777.6 DN. Every prediction was met to **0.0 DN**:

| arm | plant | required | measured |
|---|---|---|---|
| A0 | an arm against itself | excess 0, ratio 1 | +0.0 DN, 1.000 |
| A2 | depression of 100, 400, 1600 DN into the estimator aura | excess rises 1 for 1 | error 0.0 DN at every step |
| A3 | a lift of 400 and 1600 DN into the estimator aura | excess falls, goes negative when over-corrected | +377.6 then -822.4 DN |
| A4 | far field alone shifted plus or minus 200 and 800 DN | tracks 1 for 1 | error 0.0 DN at every step |
| A5 | both far fields shifted together | excess must not move | +777.6 DN unchanged |
| A6 | both arms scaled by two | a difference statistic doubles | exactly doubled |

A3 is the direction this project has twice caught instruments failing: a planted
*improvement* must not score as a defect. It does not; it drives the statistic
negative.

A4 is the denominator arm. The quantity is a difference from a far field, so the
far field is a term the verdict divides by, and it was perturbed on its own.

**A5 is the most useful row.** A common-mode level shift leaves the physical
excess bit-identical at +777.6 DN while moving the *ratio* from 1.333 to 1.179.
Two merges that differ slightly in overall level will therefore report different
ratios for identical physical behaviour. This is an independent reason, separate
from the pole, that the multiplier is not a quotable quantity.

## 7. What is still not established

The relationship between geometry strength and excess magnitude rests on four
subjects. Ordering by excess reproduces the geometry ordering, which is
consistent with `dark_ratio` driving the effect, but four points do not establish
a functional relationship and I have not separated `dark_ratio` from subject
brightness, scale or working distance. Treat it as a consistent pattern, not a
law.

No subject in this corpus presents the geometry at the reference subject's
strength. The best available are `bee-2-cpl` and `bee-3-cpl` at 2.80 against
4.52. The claim's headline subject is the corpus extreme, which is itself a
reason a single-subject multiplier was never safe. A capture presenting a small
dark subject on a clean bright ground at `dark_ratio` above 4 with `ground_iqr`
below 0.05, framed so the subject occupies well under a third of the frame,
would let this be settled properly. I did not add that to the capture list
because that file is currently being edited by another lane.

## 8. Scripts

| script | does |
|---|---|
| `experiments/V-REVIEW/vg_geom.py` | the geometry statistic and the corpus screen |
| `experiments/V-REVIEW/vg_commission.py` | geometry commissioning, both directions plus the denominator |
| `experiments/V-REVIEW/vg_commission_iqr.py` | ground-texture sweep against a plant of known amplitude |
| `experiments/V-REVIEW/vg_aura2.py` | first re-measurement, retained because it is what exposed the mask defect |
| `experiments/V-REVIEW/vg_aura3.py` | subject-matched mask, composition floor, partition |
| `experiments/V-REVIEW/vg_commission_aura.py` | aura commissioning on this configuration |
"""

p = os.path.join(ROOT, "docs", "research", "V-REVIEW-geometry.md")
with io.open(p, "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)
print("wrote", p, len(doc), "chars")
