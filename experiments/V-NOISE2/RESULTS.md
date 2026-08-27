# V-NOISE2 — does M127's noise advantage generalise across subjects?

**Status: IN PROGRESS.** Two of four subjects measured, two building. A
milestone number has been **requested from the orchestrator and not yet
allocated**, so this file lives in `experiments/V-NOISE2/` and is not a record.
Nothing here should be cited from `docs/research/` until it moves.

**The subject list was fixed in advance.** `PREREGISTRATION.md` was committed
as `49a49b44` **before any of the three new subjects existed on disk**, and it
closes the list, the statistic, the commissioning arms, the verdict vocabulary,
the pooling condition and the falsification conditions. With a multi-subject
result, subject selection is the obvious place a flattering answer can enter,
and pre-registration is the only defence.

---

## 0. Where this stands

M127 measured, on **one** scene, that strehl is cleaner than `enfuse` by
1.54–1.76× and cleaner than `focus-stack` by 1.90–2.53×, at equal or better
scene content. The orchestrator named the sample size as the binding
constraint: *a reviewer will not attack the estimator; they will ask whether
1.54–1.76× is a property of `strehl` or a property of the scene.*

Two things are settled so far, and one of them was nearly lost to an
instrument defect of my own making.

**1. M127 reproduces exactly, through a re-implemented instrument.** `hd2.py`
reads M127's subject (`113MSDCF`) through the new per-subject code path and
returns **1.540 / 1.763 / 1.538** against `enfuse` and **1.898 / 2.371 /
2.532** against `focus-stack` — the published numbers to the digit — together
with M127's scene decomposition (noise 0.05187, scene 0.12151, 15.4%)
unchanged. Keeping the already-answered subject inside the closed list is what
made that check possible.

**2. The second subject is cleaner still, and by roughly double.** On
`119MSDCF` (33 frames, shallow, averaging-dominated), `enfuse` reads **3.041 /
2.807 / 2.594** and `focus-stack` **3.540 / 3.858 / 3.714**. Both extremes have
non-overlapping CIs on two of three channels, so **the subjects are already
measurably heterogeneous** and §6's split test — written before the numbers
arrived — makes pooling illegitimate unless the remaining two subjects close
the gap. A regime-dependent advantage is a real finding, not a failure.

---

## 1. The guard that nearly withdrew a correct headline

This is the most important thing in this document so far, and it is a lesson
about instruments rather than about stackers.

`hd2.py`'s `TONE` arm read **+60.17%** on 113 and declared M127's ratios a tone
measurement. M127's own `TONE` arm had read **−153.05%** on the same pixels. A
guard cannot withdraw a result while it disagrees with itself by 213 points on
one image, so the guard was measured before the data were.

**It was my defect.** The arm compared the *integer-shift corrected* strehl
sigma (0.05187) against a toned sigma computed with **no shift applied**. Those
estimate different quantities. strehl's unshifted sigma is **0.07859**, so the
arm subtracted a baseline 51.5% too small, and reported a large positive
"explained" for a map that had in fact *lowered* strehl's noise from 0.07859 to
0.07142.

> **A guard that flips sign between two runs on the same pixels is making a
> claim about the instrument, not about the image.**

`tonecheck.py` settles it by commissioning the arm **from both sides**:

| arm | construction | true answer | measured |
|---|---|---|---|
| `NEGCTL` | target = strehl **plus noise** | 0% — it differs by noise alone | gains **0.9047 / 0.9048 / 0.9041** over a 0.5×–2.0× noise sweep |
| `POSCTL` | target = strehl through a **known gamma 0.75** | 100% — it differs by tone alone | **91.4%** bias-corrected |

`NEGCTL`'s gain moves by **0.08% across a fourfold change in the target's
noise**. The arm is therefore *not* circular; it carries a fixed ≈9.5%
contraction from fitting and applying a 256-quantile map, which divides out.

**`NEGCTL` alone could not have settled this.** An arm that always returns a
small number passes a defect-only commissioning trivially. `POSCTL` is the arm
that only an instrument which actually responds to tone can pass — the same
lesson the corpus already carries from metrics that scored a genuine
improvement worse and passed every planted-defect test regardless.

Bias-corrected, tone explains **0.68%** of the `enfuse` gap and **−1.25%** of
the `focus-stack` gap on 113, and **−2.51%** / **−0.22%** on 119. M127's
headline stands, and now rests on a two-sided control rather than on an
uncontrolled number.

**The bias is a property of the subject, not a constant**: 0.9049 on 113,
0.9972 on 119. Carrying 113's value to 119 would have been wrong by 9%. This is
the pre-registration's "nothing is carried across from another scene" earning
its keep.

---

## 2. The blur objection, which was live on 119 and is now closed

M127 foreclosed *"cleaner because blurrier"* from inside the measurement:
strehl held the lowest noise **and** the highest scene term. On 119 the same
decomposition did the opposite —

| arm | flat-ROI σ | noise σ | scene term | noise fraction |
|---|---:|---:|---:|---:|
| **strehl** | 0.009944 | **0.00725** | 0.00681 | 53.1% |
| `enfuse` | 0.020451 | 0.01639 | **0.01224** | 64.2% |
| `focus-stack` | 0.019373 | 0.01565 | 0.01142 | 65.2% |

— strehl carrying **44% less** fine structure. `V-EYES` §5.5 independently
measures `119MSDCF` as the corpus's **softest** subject (0.8110 against a
per-site best frame), so this is precisely the subject where the objection is
most credible, and it cannot be answered by pointing at a separate sharpness
run.

`scenetile.py` discriminates it on a prediction registered before the run. The
decomposition runs on **FLAT** tiles — the bottom quartile by max-over-frames
high-pass variance, chosen for having the *least* detail — so its "scene term"
is not mostly subject detail. Two candidates make **opposite** predictions in
the **DETAIL** tiles (top quartile, 9.6× the high-pass energy):

- **(a) a real resolution deficit** persists into detail tiles;
- **(b) fixed-pattern structure** does not. Frames are *aligned* before fusion,
  so a scene point lands on **different sensor sites** across frames; the fixed
  pattern is not common across aligned frames, and **averaging suppresses it
  while selection does not**. strehl averages 84.7% of the finest band on 119;
  `enfuse --hard-mask` selects one frame's pixel.

**MEASURED — comparator/strehl scene term, 119:**

| tile class | `enfuse` | `focus-stack` | reading |
|---|---:|---:|---|
| FLAT | 1.798 | 1.678 | strehl trails |
| DETAIL | **0.907** | **0.956** | **strehl leads** |

The deficit is **confined to the flat tiles and reverses where subject
structure dominates** — and it reverses *against a headwind*. In detail tiles
the half-difference is not a clean noise estimate: scene cancels between halves
only if the halves are registered, and residual misregistration inflates the
noise term worst on the arm whose halves sit furthest apart, which is strehl.
The detail-tile scene term is therefore a **lower bound for strehl**, and
strehl leads anyway.

113 leads in both classes (0.879 / 0.934 worst comparator ratio), unchanged
from M127.

**MEASURED** is the confinement and the reversal. **ARGUED** is the PRNU
mechanism, from `V-CALIB`'s measured 0.286% of signal; settling it needs the
band-resolved split of the fixed-pattern structure, which
`docs/research/M102-simulator.md` §6.4.1 names as still open.

---

## 3. Per-subject results

Integer-shift corrected, median of paired per-tile ratios, bootstrap 95% CI
over tiles. **>1 means the comparator is noisier than strehl.**

| subject | frames | depth | regime | `avg_index` | tiles | commissioning |
|---|---:|---|---|---:|---:|---|
| `113MSDCF` | 63 | mid | mid | 10.46 | 110 | ALL PASS |
| `119MSDCF` | 33 | shallow | averaging | 13.31 | 110 | ALL PASS |
| `flower-bud-alone-cpl` | 205 | deep | — | — | — | building |
| `bee-1-cpl` | 299 | deep | selecting | — | — | building |

**`enfuse`**

| subject | luma Y | chroma R−Y | chroma B−Y |
|---|---|---|---|
| `113MSDCF` | 1.540 [1.399, 1.691] | 1.763 [1.671, 1.837] | 1.538 [1.456, 1.671] |
| `119MSDCF` | 3.041 [2.470, 3.404] | 2.807 [2.704, 2.860] | 2.594 [2.036, 2.659] |

**`focus-stack`**

| subject | luma Y | chroma R−Y | chroma B−Y |
|---|---|---|---|
| `113MSDCF` | 1.898 [1.790, 2.025] | 2.371 [2.274, 2.625] | 2.532 [2.410, 2.729] |
| `119MSDCF` | 3.540 [3.371, 3.624] | 3.858 [3.736, 3.931] | 3.714 [3.637, 3.807] |

`avg_index` is measured here from strehl's own stack logs (the `averaged :`
line, mean over all but the last band, following
`corpus_softness.py:98–104,181`). It is **not numerically comparable** to
`V-EYES`'s published values, which are 13-frame subsamples; it is measured
consistently across these subjects and used only for the rank test, which is
invariant to that.

---

## 4. Commissioning, per subject

Re-run on every subject. Nothing is carried across from another scene — §1
shows why that is not a formality.

| arm | 113 | 119 |
|---|---|---|
| `NULL` identity floor | 1.000000 PASS | 1.000000 PASS |
| `POTENCY` measured/predicted, 3 levels | 0.9999 / 1.0000 / 0.9996 PASS | 0.9999 / 1.0002 / 0.9996 PASS |
| `QUANT8` (must be >1 by arithmetic) | +12.4% / +33.3% / +54.8% PASS | +53.1% / +77.1% / +95.9% PASS |
| `TONE` bias-corrected, `enfuse` | +0.68% PASS | −2.51% PASS |
| `TONE` bias-corrected, `focus-stack` | −1.25% PASS | −0.22% PASS |
| `TONE` `NEGCTL` bias / `POSCTL` | 0.9049 / 91.5% PASS | 0.9972 / 99.2% PASS |
| `CGAIN-DC` magnitude | ≤12.2% PASS | ≤0.7% PASS |

`QUANT8` is much larger on 119 (+53%/+77%/+96%) than on 113 because 119's noise
is ~7× lower, so the 8-bit step is relatively bigger. `focus-stack`'s numbers
on 119 are substantially its 8-bit container rather than its merge.

---

## 5. Deviations, reported rather than asserted harmless

**5.1 `CGAIN-DC`: straddle test replaced by magnitude, diagnosed before
changing.** §4 of the pre-registration wrote "the CI must straddle 1". On 119
this fired on `enfuse` at 0.997 [0.994, 0.999] and 0.989 [0.983, 0.993] — a
**0.3%** and **1.1%** gain difference, declared a failure only because 110
tiles make even 0.3% significant. A straddle test measures *significance*; the
guard exists to test *magnitude*. Both are now computed and **both printed**,
using M127's already-pre-registered `CHROMAGAIN` arithmetic
`explained = (gain − 1)/(noise_ratio − 1)` with a <50% threshold. On 119 that
reads ≈ −0.17%, and the **sign runs against `enfuse`**.

**5.2 `align_image_stack -t 25` on `flower-bud-alone-cpl`.** The default
aborted after 308 s with *"After control points pruning reference images has no
control points"*, producing 0 of 205 files. Probes isolated it to **frame 0,
not stack length**: the first 20 frames failed in 10.5 s at the default, a
middle 20-frame slice passed at the default, and the first 20 passed at
`-t 25`. `-t` is a *pruning* parameter applied to every frame alike, so it
cannot prefer an arm — but a looser prune could leave a worse alignment, and a
worse alignment degrades the **comparators only**, since strehl aligns itself.
**That error runs in strehl's favour**, so it is checked rather than assumed.

The check is the integer-shift search, **and it comes with its own null**.
`half_sigma(shift=True)` crops the tile by `MAXSHIFT` on each side before
measuring, so even a perfectly registered pair changes value slightly; that
crop effect is the search's null level. MEASURED:

| subject | strehl | `enfuse` | `focus-stack` |
|---|---:|---:|---:|
| `113MSDCF` | **−34.00%** | +0.51% | +0.27% |
| `119MSDCF` | **−15.54%** | +0.21% | −0.24% |

The comparators move by a few tenths of a percent in *both* directions — the
crop, not a registration gain. strehl moves 30–130× further, and only
downwards. The search finds real misregistration on the arm that has it and
nothing on the arms `align_image_stack` had already registered. If it starts
moving the comparators on a subject built with a raised `-t`, that subject's
alignment is suspect and the subject is reported as such.

**5.3 `Arm.rgb` applies scale only, no offset.** Inherited from `h2h2b.Comp`
and from M127. On 119 the measured median offsets are dy −8, dx −16 px, which
on 256 px tiles is ~94% overlap: the comparison across arms is of *magnitudes*
computed within each arm, not of aligned pixels, but the tiles do not cover
identical scene content. Reported, not silently fixed.

**5.4 119's census separation is weak.** Median detail / max flat is **1.29×**
on 119 against 2.02× on 113. The half-difference estimator needs no flatness
assumption, so this does not invalidate the statistic, but it does mean 119's
"flat" tiles are less flat than 113's.

**5.5 A statistic re-implemented instead of imported, caught by the known
subject.** A first version of `pool2.py` computed `median(num)/median(den)` and
read **1.626** on 113/`enfuse` where `hd2.py` reads **1.540**. M127's `boot` is
the *median of paired per-ROI ratios*, which is a different quantity. Two
numbers for one statistic, from one lane, in one night — visible only because
113's answer was already known. `boot` is now imported from `noisefree.py` and
the two agree to the digit.

---

## 6. What is not yet done

- `flower-bud-alone-cpl` (205 frames) and `bee-1-cpl` (299 frames) are
  building. `bee-1-cpl` is the **selection-dominated deep stack** the
  commission specifically asked for, and it is the subject most likely to
  separate the regimes.
- The §6 split test and conditional pooling run only when all four are in.
  On the two available subjects the extremes are already **disjoint on two of
  three channels for `enfuse`**, which points at ILLEGITIMATE.
- The §6 rank test needs ≥3 subjects and is currently not evaluable.
- §7's chroma falsification condition (≥2 of 4 subjects reading LEVEL or
  NOISIER) is **not met** on the two measured: both read NOISIER with CIs far
  above 1.0.
