# V-REVIEW-dust: adjudicating BUILD-DEFECT against V-H2H2

**VERDICT: THE SHIPPING DEFAULT DOES NOT NEED A DUST CORRECTOR ON.** There is a
real mote on the sensor. It does not reach the delivered product at a level this
corpus can detect, the map that would drive the correction is too deep by
roughly a factor of two, and the guard that would catch that is unverified.
Correcting costs real risk to buy a benefit nobody has measured.

**The dust is real.** A depression sits at quad `(3419, 2316)`, photosite
`(6838, 4632)`, roughly 80 by 100 photosites across. Both lanes were partly
right: BUILD-DEFECT found a real feature at a real place, V-H2H2 was correct
that it does not reproduce in the delivered masters, and the two lanes were
measuring **different places**.

## 1. The coordinates: the lanes were measuring different places

| interpretation | quad x | quad y | rampA | rampB |
|---|---|---|---|---|
| BUILD-DEFECT `(3434,2305)` read as QUADS | 3434 | 2305 | +2.89% | +2.89% |
| BUILD-DEFECT `(3434,2305)` read as PHOTOSITES | 1717 | 1152 | +0.06% | +0.05% |
| V-H2H2 cite `(7008,4450)` read as photosites | 3504 | 2225 | +1.30% | +1.27% |
| V-H2H2 filename `6776_4322` read as photosites | 3388 | 2161 | +0.90% | +0.91% |
| my own detection, independent | 3440 | 2282 | +3.05% | +3.01% |
| corner control, nobody claims a mote | 3400 | 2300 | +0.41% | +0.42% |

Measured with `experiments/V-REVIEW/vd_quad.py`.

`(3434,2305)` is in **quads**. Read as quads it lands on a real feature; read as
photosites it lands on nothing. Photosite equivalent `(6868, 4610)`.

Both V-H2H2 coordinates are **off the feature**, by 106 and 155 quads. A grid
scan finds scattered dips of 0.82-1.13% all over the frame, including 0.88% in
the *opposite* corner, so their readings of +1.30% and +0.90% are at the
statistic's own background level. I do **not** claim they are the mote's skirt;
the fine map shows the mote decayed to 0.0-0.2% well before either of them.

## 2. What BUILD-DEFECT calls unexplained is not an error

That lane records a 25-quad offset between its flat-derived location and its map
coordinate, and calls it unexplained. **The feature is bigger than the offset.**
Quadratic-detrended, 5-quad blocks, per cent, both ramps agreeing:

| quad y | 3412 | 3422 | 3432 | 3442 | 3452 |
|---|---|---|---|---|---|
| 2282 | 0.04 | -0.03 | -1.37 | -2.40 | -0.12 |
| 2292 | 0.01 | -1.08 | -3.11 | -3.12 | -1.26 |
| 2302 | -0.13 | -3.13 | -3.03 | -3.00 | -1.80 |
| 2312 | -1.48 | -3.23 | -2.99 | -3.02 | -0.74 |
| 2322 | -1.26 | -2.95 | -2.88 | -1.26 | -0.07 |

A flat-bottomed blob about 35 by 45 quads at a 1.5% contour. The flat-derived
centroid `(3440,2281)` and the map coordinate `(3434,2305)` are **both inside
it**, 24.7 quads apart. Two estimators picking different points on a
flat-bottomed feature will differ by tens of quads and neither is wrong.

## 3. Amplitude: my own first answer was measured with the wrong window

This is the correction that matters most, and it cuts against my earlier draft.

`vd_quad.py` and `vd_fine.py` fit their reference annulus at radius greater than
14 quads. **The mote is 35 to 45 quads across, so that annulus sits partly
inside the feature** and the quadratic absorbs the thing being measured.
Commissioned with a plant the width of the real mote
(`experiments/V-REVIEW/vd_wide.py`):

| configuration | plant 2% | plant 5% | plant 8% | plant 13.3% | under-read |
|---|---|---|---|---|---|
| narrow win45 core8 fit>14 | 0.83% | 2.08% | 3.36% | 5.75% | 2.4x |
| medium win90 core15 fit>40 | 1.66% | 4.14% | 6.63% | 11.01% | 1.21x |
| wide win140 core25 fit>70 | 1.37% | 3.39% | 5.42% | 8.98% | 1.47x |
| wider win200 core25 fit>110 | 1.37% | 3.39% | 5.42% | 8.98% | 1.48x |

The narrow configuration under-reads a mote-width feature by a factor near 2.4,
consistently across every planted amplitude. Reading the real mote with each,
using a median core rather than a minimum core:

| configuration | rampA | rampB | clean-site sd | calibrated |
|---|---|---|---|---|
| narrow | 1.92% | 1.91% | 0.27 pts | 4.6% |
| medium | 2.48% | 2.48% | 0.10 pts | 3.0% |
| wide | 2.14% | 2.12% | 0.13 pts | 3.1% |
| wider | 2.03% | 1.99% | 0.10 pts | 3.0% |

**Calibrated depth is 3.0 to 4.6 per cent**, three of four configurations
agreeing at 3.0 to 3.1. I quote the family, not a member of it. My earlier
single value of 3.45 per cent was the maximum of a family measured with a
minimum-of-core statistic that is biased deep, in a window too small for the
feature. Two errors that partly cancelled.

Against that, the map's 8.24 per cent is too deep by **1.8x to 2.7x**. That is a
smaller margin than the 2.4x I first wrote, and it is better supported.

The corpus figure of 13.28 per cent is a **master-domain** reading on
`highly-angled-ruler-mm-cpl`. On that same subject a control site reads
**39.92%**, three times deeper than the dust site. A 13 per cent dip at a
nominated site in that master is not remarkable.

## 4. Is it on the sensor or on the filter?

This matters more than amplitude: a corrector keyed to fixed sensor coordinates
is only right if the feature is fixed in sensor coordinates.

**I have to retract an assumption of my own here.** `vd_flat.py` states in its
docstring that its two halves are "one with CPL one without". That is a
declaration, never a measurement; the split is `int(name[3:8]) < 300`, a
filename number. Measured:

| ramp | frames | aperture | ISO | shutters | clock |
|---|---|---|---|---|---|
| rampA | 38 | f/5.6 | 100 | 1/20, 1/13 | 16:43:25 to 16:44:09 |
| rampB | 40 | f/5.6 | 100 | 1/30, 1/20 | 16:47:58 to 16:48:44 |

Same aperture, same ISO, overlapping shutters, four minutes apart. A polariser
costs one and a half to two stops and would be unmistakable here. **These are
one optical configuration split by filename.** So "reproduces across two
independent ramps" is a sound reproducibility check and **not** an independent
optical check, and my earlier report leaned on it as though it were both.

The labelled pair settles the direction instead. Stacking raw frames from the
corpus at fixed sensor coordinates, where subject detail varies between subjects
but dust does not (`experiments/V-REVIEW/vd_raw.py`):

| group | subjects | mote | control mean | control sd | significance |
|---|---|---|---|---|---|
| CPL | 17 | -1.577% | -0.190% | 0.280 pts | -4.95 sd |
| non-CPL | 9 | -1.858% | -0.764% | 2.373 pts | -0.46 sd |

The mote is present at essentially the same depth **with and without the
polariser** (0.28 pts apart, far inside the non-CPL spread). The non-CPL arm
lacks the power to stand alone, but its point estimate agrees. **The feature is
not on the CPL.**

The direct with-CPL against without-CPL focus sweeps **refused**: their control
sites scatter across 7.8 points while a planted 3 per cent dip moves the
statistic only 1.84 points. An arm that cannot see what it hunts is not evidence
in either direction, and I am not counting it as any.

## 5. Does it survive into the delivered product? No

Fixed-location residual stacking across the corpus
(`experiments/V-REVIEW/vd_stack.py`). Commissioned first: a **1.0 per cent**
fixed dip is recovered at **-6.46 sd**, 3 per cent at **-16.30 sd**, 0.5 per
cent below floor. Registration jitter priced separately
(`experiments/V-REVIEW/vd_jitter.py`): a 3 per cent dip survives 20 px of
jitter at -8.41 sd.

| site | centre dip | noise sd | significance |
|---|---|---|---|
| dust | -1.604% | 0.524% | -3.06 sd |
| control mean | -1.563% | - | none |

Indistinguishable. A control site reads deeper (-3.186%) and another reads more
significant (-3.63 sd) than the dust site does. Across 24 usable subjects the
dust site was the deepest of its site group in a single subject, where chance
gives about four. **The dust site is quieter than the controls.**

Why a 3 per cent sensor feature does not appear in the masters is **not
established**. Alignment smearing is consistent with it and unproven.

## 6. Which arms had the power to decide

| arm | power against a 3% mote | counts as evidence? |
|---|---|---|
| V-H2H2 whole-frame reduced, floor 27.85% | none | no |
| V-H2H2 cross-median, floors 38.95% and 21.11% | none | no |
| V-H2H2 1:1 at its stated coordinate | yes, master domain | yes, and correct |
| BUILD-DEFECT flat location | yes | yes, correct place |
| BUILD-DEFECT corner depth | biased by its reference | no |
| this lane, flats, calibrated window | yes | yes |
| this lane, raw stack CPL arm | yes | yes |
| this lane, raw stack non-CPL arm | no, sd 2.37 pts | no |
| this lane, focus-sweep ratio | no, scatter 7.8 pts | no |
| this lane, master residual stack | yes, floor 1.0% | yes |

## 7. Partition

Arms built for this adjudication: **6 measured, 2 refused by regime, 1 failed**,
summing to 9. The failure was a ring-profile arm that crashed on an out-of-range
slice: the mote sits 28 quads from the bottom frame edge, so a 160-quad ring
does not fit. That edge proximity is itself the mechanism behind every
annulus-style reference over-reading here.

## 8. Errors of mine, disclosed

- My first detector failed its own null arm with 55 detections on a dust-free
  field, all at frame borders.
- Every reference I built before the quadratic one over-read in the corner,
  because I commissioned them on a flat synthetic background, the one background
  that cannot expose a gradient-following failure. An iso-radial arm read 7.51
  to 8.88 per cent at a corner control with no mote, bracketing the very figure
  I was disputing.
- My residual stacker v1 produced a standard deviation of 1.7e9 per cent by
  dividing by near-black patches; v2 adds a level floor.
- **The wrong-sign arm on my load-bearing statistic was planted on the mote
  itself**, so it could not fail. Repaired in `experiments/V-REVIEW/vd_cpl.py`
  and re-run at clean sites: a planted bright spot now reads -3.01% and -2.72%,
  correctly refusing to call brightness a depression.
- I reported 3.45 per cent as a depth when it was the maximum of a family, taken
  with a biased statistic in an undersized window. Corrected in section 3.
- I repeated `vd_flat.py`'s unmeasured CPL claim. Corrected in section 4.

## 9. The product decision

**Leave the corrector off.**

- Nothing at or above 1 per cent reaches the delivered masters, against a floor
  commissioned at exactly 1 per cent.
- The dust site is quieter than its controls across the corpus.
- The map's amplitude is too deep by 1.8x to 2.7x, and that lane's own
  manufacture arm prices an unguarded map at +8.64% to +16.44% injected.
- I did **not** verify that lane's self-validation guard on the real corpus, and
  I am not making the recommendation depend on it: an unmeasured condition is
  not a gate, so the recommendation stands on the measured benefit alone, which
  is below detectability.

If it is ever switched on, it must correct at quad `(3419, 2316)`, photosite
`(6838, 4632)`, over roughly 80 by 100 photosites, taking amplitude from the
frames and never from the map.

## 10. Scripts

| script | does |
|---|---|
| `experiments/V-REVIEW/vd_flat.py` | builds the two master flats |
| `experiments/V-REVIEW/vd_detect.py` | detector and both null arms |
| `experiments/V-REVIEW/vd_quad.py` | local quadratic detrend |
| `experiments/V-REVIEW/vd_wide.py` | window-size calibration, the amplitude answer |
| `experiments/V-REVIEW/vd_cpl.py` | ramp audit and repaired wrong-sign arm |
| `experiments/V-REVIEW/vd_raw.py` | raw-domain stack split by polariser |
| `experiments/V-REVIEW/vd_coords.py` | the disputed coordinates |
| `experiments/V-REVIEW/vd_fine.py` | the fine map and per-subject masters |
| `experiments/V-REVIEW/vd_stack.py` | master residual stacking and its floor |
| `experiments/V-REVIEW/vd_jitter.py` | registration-jitter confound |
| `experiments/V-REVIEW/vd_station.py` | search-based stationarity, negative |
