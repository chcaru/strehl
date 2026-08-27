# V-NOISE2 — does M127's noise advantage generalise across subjects?

**Status: IN PROGRESS.** Three of four subjects measured, one still building. A
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

**The answer is that it is a property of the scene.** The noise ratio itself
generalises and grows; what does **not** generalise is the pairing M127's
verdict actually rests on.

### 0.1 The headline, and it is unflattering

M127's verdict does not rest on the noise ratio alone. It rests on the
**pairing** — strehl holding the *lowest noise* and the *highest scene content*
in the same tiles — because that, and only that, forecloses "cleaner because
blurrier" from inside the measurement rather than by appeal to a separate
sharpness run. The orchestrator put that pairing in front of everything else
and published it.

Re-read at matched bandwidth (§0.2) on every subject, over six subject-arm
pairs, it is **strictly monotone**:

| subject | arm | noise ratio (strehl cleaner ×) | scene ratio (strehl ÷ comparator) | reading |
|---|---|---:|---:|---|
| `113` | `enfuse` | 1.657 | **1.134** | strict gain |
| `113` | `fs15-coh` | 1.949 | **1.286** | strict gain |
| `119` | `enfuse` | 2.365 | 0.577 | **trade** |
| `119` | `fs15-coh` | 2.230 | 0.605 | **trade** |
| `bee` | `enfuse` | 11.929 | 0.180 | **trade** |
| `bee` | `fs15-coh` | 15.619 | 0.060 | **trade** |

**Strict gain on 2 of 6 — and both are on `113`, M127's own subject.** On the
two subjects M127 never saw, strehl is cleaner *and carries materially less
scene content in the same tiles*. The two quantities move together and the
ordering is perfect: sort by noise ratio and the scene ratio falls
monotonically, 1.13 → 1.29 → 0.61 → 0.58 → 0.18 → 0.06.

That is the signature of a **blur–noise trade**, not of a strict improvement.

MEASURED (`banddiag.py`, `C:\dev\strehl-out\V-NOISE2\banddiag.json`). What is
withdrawn is the *generalisation* of M127's pairing, not M127 itself: on `113`
the pairing survives the corrected statistic (scene 0.1224 vs enfuse 0.1080,
against M127's published 0.12151 — agreeing to 0.7%). **M127's verdict stands
on M127's subject.** The claim that it is a property of `strehl` does not.

The practical consequence for the owner-facing README: *"equal detail at
materially lower noise is a strict improvement"* is supported on
`coffee-bubbles` and **contradicted on both new subjects**. It should not be
stated as a property of the stacker until the flat-tile scene deficit is
explained.

### 0.2 The defect that had to be fixed before any of that could be read

Running the pre-registered §4 battery on `bee` returned a **6–8× noise win** —
and its scene decomposition was **degenerate on 3 of 3 arms**: the
half-difference sigma *exceeded* the flat-ROI sigma of the same tiles, which
additive independent noise cannot do. The scene term clamped to zero on every
arm and the code still printed `highest scene term: strehl` off three tied
zeros. A 6–8× "we win" from a comparison whose own internal consistency check
had failed.

The cause is in the shared statistic, and it reaches M127:

| quantity | function | filter |
|---|---|---|
| flat-ROI sigma `f` | `noisefree.sigmas` | `ch - uniform_filter(ch, HP)` — **high-pass** |
| noise sigma `n` | `halfdiff.half_sigma` | `u - v` — **full band** |

`scene = sqrt(f² − n²)` therefore subtracts a **full-band** noise term from a
**high-pass-band** total. The identity `total² = scene² + noise²` that the
subtraction assumes holds only when both terms are measured over the same band.

`banddiag.py` tests that diagnosis rather than asserting it, by re-reading the
half-difference through the *same* high-pass, with `113` and `119` as controls:

| subject | strehl | `enfuse` | `fs15-coh` | degenerate, full band → matched |
|---|---:|---:|---:|---|
| `113` | 95.9% | 98.2% | 97.4% | 0/3 → 0/3 |
| `119` | 94.5% | 98.8% | 97.6% | 0/3 → 0/3 |
| `bee` | **61.5%** | 98.6% | 87.7% | **3/3 → 0/3** |

(percentage of the full-band half-difference sigma that survives the high-pass)

On the two subjects that already decomposed cleanly, matching the bandwidth
changes nothing — **a rewrite that altered a working subject's answer would be
a rewrite, not a diagnosis.** On `bee`, **38.5% of strehl's measured "noise"
was a low-frequency half-to-half difference**, not noise, and matching the
bandwidth restores the decomposition on all three arms.

A second defect surfaced inside the first: `half_sigma` applies the
integer-shift search for strehl, which *minimises* variance, and my high-pass
variant initially did not — comparing a minimised statistic against an
unminimised one. The tell was strehl "keeping" **132.7%** of its sigma under a
high-pass, which is impossible for noise. Fixed; 132.7% → 95.9%.

**Two things are therefore settled and one is withdrawn.**

**1. M127 reproduces exactly, through a re-implemented instrument.** `hd2.py`
reads M127's subject (`113MSDCF`) through the new per-subject code path and
returns **1.540 / 1.763 / 1.538** against `enfuse` and **1.898 / 2.371 /
2.532** against `focus-stack` — the published numbers to the digit — together
with M127's scene decomposition (noise 0.05187, scene 0.12151, 15.4%)
unchanged. Keeping the already-answered subject inside the closed list is what
made that check possible.

**2. The noise ratio generalises and grows.** On `119MSDCF` (33 frames,
shallow, averaging-dominated), `enfuse` reads **3.041 / 2.807 / 2.594** and
`focus-stack` **3.540 / 3.858 / 3.714**. Both extremes have non-overlapping CIs
on two of three channels, so **the subjects are already measurably
heterogeneous** and §6's split test — written before the numbers arrived —
makes pooling illegitimate unless the remaining subject closes the gap. A
regime-dependent advantage is a real finding, not a failure.

**3. The pairing does not generalise, per §0.1, and `bee`'s ratio is
withdrawn** pending an explanation of its scene deficit. `hd2.py` now fails
commissioning on any subject whose decomposition goes degenerate, so `bee`'s
6–8× number is not reported as a result.

---

## 7. Adjudicating C against the scene term — the disagreement was a subject mismatch

*(Placed here for prominence rather than at the end of the file; it is the
lane's most recent work and it qualifies §0.)*

ORCH asked me to settle a 1.7× disagreement on `119MSDCF` between the coherence
statistic `C` (0.977, "level with `enfuse`") and my matched-bandwidth scene
ratio (0.577, "we retain 58% of its detail"), noting correctly that **I built
one of the two and may not adjudicate by arguing mine is sound.**

### 7.1 The ladder: neither instrument is broken

`ladder.py` builds companions from `119`'s real strehl half-stacks with a
**planted, known detail ratio** — `companion = lp + k·(img − lp)` with
`lp = uniform_filter(64)`, so the true amplitude ratio is exactly `k` in every
band above ~0.016 cyc/px, which is far below both readers. Both instruments are
run over the ladder, on **both** tile populations.

| rung | true k | C recovers | scene recovers |
|---|---:|---:|---:|
| IDENT-PATH | 1.000 | 1.0000 | 1.0000 |
| **SHARPER** | **1.300** | **1.2999** | **1.2993** |
| k=0.95 | 0.950 | 0.9500 | 0.9501 |
| k=0.85 | 0.850 | 0.8500 | 0.8505 |
| k=0.70 | 0.700 | 0.7000 | 0.7009 |
| k=0.50 | 0.500 | 0.5000 | 0.5016 |

(DETAIL population; FLAT is tighter still, worst error 0.0%.)

**Worst error over 6 graded rungs: C 0.0%, scene term 0.3%.** Both recover the
sharper rung, so neither is bounded below at parity — the perverse-gauge failure
mode this project has already shipped once. **Both instruments are sound as
detail measures under a coherent detail change.**

The identity rung is a prediction, not a short-circuit: the script asserts the
plant actually altered the array before believing the reading. On FLAT tiles
`k=1.0` *is* bit-identical by exact floating-point arithmetic, so potency is
carried by the `k≠1` rungs, which do change it — and the script says so rather
than silently passing.

### 7.2 The disagreement does not exist, because the two numbers are different subjects

**MEASURED.** `experiments/V-LINEAR2/cohfree.py` hardcodes its strehl inputs as
`C:\dev\strehl-out\V-H2H2\lin\113-{full,A,B}-g1.tiff`, and that directory
contains only `113-*` and `cb-*` rasters. **The 0.977 is subject `113`
(`coffee-bubbles`).** My 0.577 is subject `119`. They were never the same
subject, the same masters, or the same stack.

Measured on the **same** subject and the **same** population, the two agree far
better than 1.7×:

| subject | population | C (enfuse/strehl) | scene (enfuse/strehl) | ratio |
|---|---|---:|---:|---:|
| `113` | DETAIL | 1.159 | 0.974 | 1.19× |
| `113` | FLAT | 1.679 | 1.033 | 1.63× |
| `119` | DETAIL | **2.017** | 0.996 | 2.02× |
| `119` | FLAT | **2.420** | 1.273 | 1.90× |

(`crosspop.py`, reported as the comparator's detail amplitude relative to
strehl's, so >1 means `enfuse` holds more.)

### 7.3 The finding that matters, and it is against us

**On `119`, C — the README's own instrument — reads `enfuse` at 2.017× strehl's
detail amplitude at 0.20–0.25 cyc/px.** The published "LEVEL" was established on
`113` alone. On the second subject the README's own statistic says strehl is
behind, and the direction agrees with §0.1's scene deficit and with the other
lane's depth-dilution result.

**Caveat, stated because it bounds the claim.** My port of C reproduces the
published verdict on `113` but not the digit: 1.159 against the published
equivalent of 1.012, a 14% gap attributable to tile selection (top-`emax`
tiles versus `rois.census` detail tiles), content scale (1.0040 versus
`geomfree.py`'s 1.0050) and loader normalisation. The `119` reading of 2.017 is
far outside that gap, so **the direction and rough magnitude are robust; the
digit is not.** A digit-exact `119` number needs `cohfree.py` run on `119`
inputs by its own lane, which I have not done.

### 7.4 What each instrument actually measures

The ladder says both track a coherent detail change identically, so their
residual disagreement on real data (2.02× on `119` DETAIL) is **not** an
instrument defect. It is the one thing the plant deliberately does not contain:
the plant applies the *same* transform to both halves, so planted detail is
perfectly coherent between A and B. Real arms are not.

- **C** counts only structure **correlated between the two half-stacks**.
- **the scene term** counts total high-pass content **minus** an incoherent
  noise estimate.

They diverge exactly when an arm holds real detail that is *not* coherent across
its halves — which is what a selection-dominated merge produces when the two
halves choose different source frames, and is the same mechanism that made
`bee`'s decomposition degenerate (§0.2, 38.5% of strehl's "noise" there was a
low-frequency half-to-half difference). **That is the open question this lane
leaves**, and it is stated rather than resolved.

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

## 2. The blur objection on 119 — SUPERSEDED, see §0.1 and §7

> **This section's title and conclusion are withdrawn.** It was written when
> `119` was the only subject showing a scene deficit and the deficit looked
> closable. It is not closed. §0.1 measures the same deficit on `bee` (scene
> ratio 0.180 and 0.060) and shows the pairing M127 rests on holds on **2 of 6**
> subject-arm pairs, both on `113`. §7.3 then measures `enfuse` at **2.017×**
> strehl's detail amplitude on `119` using **C, the README's own instrument**.
> The numbers below are retained and reproducible; the reading "now closed" is
> not. **The blur objection is LIVE on `119`.**

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
