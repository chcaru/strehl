# V-ORACLE — is the blur in `flowers-cpl` a capture gap or a merge defect?

**Verdict: (a) CAPTURE GAP. Not our bug.**

At every one of the six inspected crop sites — including all three that read as
smooth defocus blur by eye — **no source frame carries more resolvable structure
than the merge delivers.** The merge is not throwing away information it had. The
information was never captured: at the blurred sites the through-focus curve is at
its maximum on the *first* frame of the bracket and decays monotonically from
there. The sweep started already past best focus for those regions.

This is a clean negative. The product response is not to fix the merge, it is to
*detect and report* the gap — and §7 gives a statistic that does exactly that,
needs no master, and needs no registration.

---

## 1. The question, and why it needed measuring rather than arguing

The orchestrator cut six 1:1 crops from the delivered master
`flowers-cpl.tiff`; three were sharp to the pollen grain, three were smooth
blur. Two readings are possible and they have opposite consequences:

- **(a) capture gap** — no frame was sharp there; the bracket did not cover that
  depth. A feature request, not a defect.
- **(b) merge defect** — a sharp frame existed and the merge discarded it. The
  most damaging bug in the product.

I re-cut my own crops first (the orchestrator explicitly warned against trusting
their read, having been wrong once that night on a downscaled preview). The
defect is real at 1:1: sites 0/2/4 sharp, sites 1/3/5 smooth defocus. So the
observation stands; only its *cause* was open.

## 2. The statistic, and why it is band-agnostic and noise-immune

For band `b`, frame `k`, tile `t`:

```
contrast(b,t) = max_k Var(b,k,t)  -  quantile_0.25_k Var(b,k,t)
```

Every frame in a stack is one sensor at one ISO at very nearly one level, so the
noise power `kappa_b · sigma^2` is **common to all frames at a given tile** and
cancels identically in the difference. No noise model is fitted and none can be
mis-fitted.

This discharges two of the project's standing rules directly:

- *"Do not gate any sharpness claim on a fixed frequency band."* The statistic is
  band-agnostic by construction: a band that is pure noise on this subject gives a
  flat through-focus curve, hence contrast ≈ 0, and simply contributes nothing. I
  report all five bands everywhere rather than selecting one. (See §8 — headlining a
  single band would have given me the *wrong verdict*.)
- *"Raw band power counts noise as sharpness."* I reproduce this hazard
  independently: at band 2, `kappa_2 = 0.014011 × (45 DN)^2 = 28 DN^2` of pure
  grain, against a band-2 signal of only 29–155 DN^2 in the blurred tiles. Raw
  band power would have said "frame beats merge" there for no reason but grain.

Grid: 18×27 = 486 tiles of 128 green px (= 256 master px). Bands from
`SIGMAS = [0.0, 0.8, 1.6, 3.2, 6.4, 12.8]` (5 DoG bands).

## 2.1 Which band, and is this subject qualified there?

Required by ORCH correction #5: no sharpness claim may be quoted without naming
the band and the subject's qualification at it.

**`flowers-cpl` does not appear in `V-LINEAR-BANDS.md`. It has never been
band-qualified** - the same status that cost `coffee-bubbles` its licence in that
correction. So I cannot lean on qualification and must argue from frequency
instead.

Band frequencies measured from the actual band operator (`bandfreq.py`: white
noise in, radially averaged output power = the band's squared transfer function),
not from the DoG algebra:

| band | peak (cyc/green-px) | half-power span | cyc/raw-px | used by the verdict |
|---|---|---|---|---|
| b0 | 0.498 | 0.303-0.498 | 0.249 | **no - excluded** |
| b1 | 0.186 | 0.123-0.283 | 0.093 | yes, but see below |
| b2 | 0.107 | 0.061-0.143 | 0.054 | **yes** |
| b3 | 0.049 | 0.033-0.072 | 0.024 | **yes** |
| b4 | 0.029 | 0.018-0.033 | 0.015 | no |

V-ORACLE works on the green sub-lattice (1 green px = 2 raw px = 2 master px).
V-LINEAR works with no demosaic. **I have not confirmed which grid its cyc/px
refers to**, and it changes the comparison by 2x, so the claim below is required
to hold under *both* readings.

The available argument is one of margin, not qualification: **a band whose entire
half-power span lies below 0.17 cyc/px - the lowest signal/noise boundary
V-LINEAR observed anywhere in the corpus - cannot be grain on any subject in that
corpus, qualified or not.**

- **b2 and b3 clear this under both grid readings** (top edges 0.143 and 0.072
  against a 0.17 floor). These are the bands that carry the verdict.
- **b1 does not.** Its half-power span reaches 0.283 cyc/green-px, above 0.17
  under the less favourable reading. Following ORCH's own precedent I treat b1's
  licence as **withdrawn pending measurement, not refuted**.
- **b0 was excluded from the rule before this check, not because of it** - it
  peaks at Nyquist and is the band V-LINEAR found to be noise or mixed on 5 of 9
  subjects.

**The verdict survives without b1.** Re-running the rule on bands 2 and 3 only
(`verdict.py flowers-cpl --bands 2,3`) returns the identical conclusion at all
six sites, in the same classes:

```
bands 1,2,3 (published):  T G G G T T
bands 2,3   (b1 dropped): T G G G T T      <- identical
```

The Stage B medians that carry §5.4 are b2 = 0.675 and b3 = 0.870, both in
licensed bands and both below 1. The 25x fine-band deficit of §5.3 is a b2
number. **No load-bearing number in this report depends on b1.**

## 3. Commissioning the instrument, and the detection floor

`commission_tfc.py` commissions **the statistic that actually ships in this
lane**, not a demoted variant. Four tests, **4 PASS / 0 FAIL**:

| test | result |
|---|---|
| T1 NULL — plant nothing, require silence | max abs delta = **0.000e+00** |
| T2 DEFECT — plant a known blur, require detection | floor **σ = 0.75 green px = 1.5 master px** |
| T3 IMPROVEMENT — plant a *sharpening*, require it scores better | 51.01 → 63.69 (**1.25×**) |
| T4 LOCALITY — require silence outside the planted tile | worst relative change **0.0000** |

T3 matters because a statistic bounded below would score a defect as "better" and
pass every degradation test trivially. It is not bounded below, so T2's fall is a
real detection.

**T2 ladder (retained contrast):** σ=0.125→1.000, 0.25→1.000, 0.5→0.914,
**0.75→0.799 DETECTED**, 1.0→0.677, 1.5→0.456, 2.0→0.294, 3.0→0.125. Outcomes
partition as 5 DETECTED + 3 not-detected + 0 PLANT-NOOP = 8 of 8 rungs; nothing
is skipped and read as passed.

**The plant is physical.** A naive `gaussian_filter` attenuates noise along with
signal; real defocus blurs the *scene* while sensor noise stays white and
full-amplitude. `physical_defocus()` blurs and then adds back white noise of
variance `sigma^2 · (1 - sum k^2)`. Noise variance is measured as
**Var(G1-G2)/2** — the two green sites see nearly the same scene with independent
noise, so this isolates noise without counting fine detail as noise. My first
attempt (high-pass of one plane) gave 226 DN^2 against the correct 302.9 DN^2,
because it injected signal as noise.

**Power relative to the defect under investigation.** The observed sharp-vs-blurred
separation is ~25× in band-2 contrast. The floor is 1.5 master px, and σ=3.0 green
px still registers on the ladder. The instrument had ample power to find a merge
defect had one existed; it did not fail to find one for want of sensitivity.

### 3.1 Commissioning the DECISION RULE, not just the statistic

Added after the ORCH broadcast on V-NEVERWORSE's report verifier, which tested
for the *presence* of the string "refuted" and stayed green through 712 checks
while that section's conclusion was flipped to "confirmed". A presence test
cannot detect a reversed conclusion.

I had the same class of hole, one level up. `commission_tfc.py` proves the
sharpness *number* moves correctly under a planted blur. It says nothing about
the (a)/(b) *rule* that turns that number into the conclusion this lane
published. **A rule structurally incapable of emitting (b) would have printed (a)
on every input, agreed with the prior and with `BUILD-TRIAGE.md`, and passed
every test I had.**

`commission_verdict.py` closes it by feeding the real `verdict.py` inputs whose
correct conclusion is known in advance - mutations that flip the CONCLUSION, not
ones that perturb a number:

| test | mutation | required conclusion | result |
|---|---|---|---|
| T1 NULL | none | all 6 sites (a) | **PASS** `aaaaaa` |
| T2 DEFECT | merge arm degraded 4x | all 6 sites (b) | **PASS** `bbbbbb` |
| T3 BOUNDARY | one tile driven to ratio 1.24, then 1.26 | (a) then (b) | **PASS** flips at the published 1.25x |
| T4 LOCALITY | one tile only, 8x | only that site changes | **PASS** `[0]` |
| T5 PEAK-CENTRED | focus peak moved to mid-bracket | no site may read capture-gap | **PASS** `TTTTTT` |
| T6 PEAK-AT-EDGE | focus peak moved to frame 0 | every site must read capture-gap | **PASS** `GGGGGG` |
| T7 SPECIFICITY | both arms scaled x3 (no information) | conclusion must not move | **PASS** `TGGGTT` |
| T8 DELETION | one site removed from the output | harness must refuse it | **PASS** refused 5/6 |
| CHANNEL | a deliberately false expectation | must report FAIL | **LIVE** |

**8 PASS + 0 FAIL, and the pass/fail channel is verified LIVE.** Every mutation asserts it actually landed before the rule is
run; a mutation that silently fails to apply produces a green that means nothing.

T2 is the one that matters: the rule *does* emit (b) on all six sites, including
the three that read blurred, when a merge defect genuinely exists. The published
(a) is therefore a property of the data and not of the rule.

## 4. The confound that had to die first: does tile *t* mean the same thing in every frame?

Stage A compares frames at a *fixed* tile index. If the stack drifts, that
comparison silently compares different scene patches — and it fails in the
direction of **inventing a merge defect**, so it is an adverse control for my
verdict, not a friendly one.

`correspond.py`, all 176 frames: frame-to-frame drift **median 0.00, p90 0.00
green px**; identity control exactly 0.00; only **1.37%** of tiles exceed a
quarter tile. The bracket is on a rail. Stage A's cross-frame comparison is sound.

## 5. The forcing evidence

### 5.1 The through-focus curves — the decisive number

Argmax alone cannot distinguish "peak captured inside the bracket" from "curve
already falling at frame 0". So `curves.py` prints the curves and an end-slope
discriminator `rise` = the fraction of the peak that has decayed by the nearer
bracket end. `rise ≈ 0` means the sweep ended while the tile was still at its
sharpest.

At all three blurred tiles, **in every signal band**, the curve is maximal at
frame 0 and decreases monotonically: `rise = 0.00`. Contrast the sharp tile
r12c01, which peaks at frame 7 with a clear rise-then-fall (b1: 131 → 1144 → 46)
and `rise` 0.90–0.96.

### 5.2 The verdict table (full 176-frame bracket)

| site | eye | tile | b1 ratio | b2 ratio | b3 ratio | b1 rise | b2 rise | verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | SHARP | r12c01 | 1.099 | 0.925 | 0.924 | 0.90 | 0.76 | (a) |
| 1 | BLURRED | r05c02 | 1.211 | 0.975 | 0.929 | 0.00 | 0.00 | **(a) capture gap** |
| 2 | SHARP | r06c05 | 0.868 | 0.743 | 0.741 | 0.00 | 0.00 | (a) |
| 3 | BLURRED | r09c02 | 0.288 | 0.399 | 0.900 | 0.04 | 0.00 | **(a) capture gap** |
| 4 | SHARP | r06c08 | 0.383 | 0.458 | 0.751 | 1.02 | 1.00 | (a) |
| 5 | BLURRED | r16c10 | 0.841 | 0.675 | 0.664 | 0.41 | 0.22 | (a) merge not beaten |

`ratio` = best source frame / merge, both noise-corrected. **All six sites are
(a).** The tile chosen inside each crop is the *best* one, which is adverse to a
capture-gap verdict.

### 5.3 Fine-band amplitude: the blurred regions never had fine detail to lose

Band-2 contrast — sharp sites **1382 / 451 / 308** versus blurred sites
**55 / 155 / 29**: a ~25× deficit. Band 1 — sharp 1128 / 201 / 120 versus blurred
17 / 50 / 99. The blurred regions do carry large *coarse*-band contrast (b3 up to
1218), which is the signature of a big soft defocus blob moving through focus.
That is exactly "smooth defocus-like blur" and it is not resolved detail.

### 5.4 The merge is essentially never beaten

Stage B, best-source / merge at detail tiles, noise-corrected, full 176 frames:

| band | median ratio | src > merge |
|---|---|---|
| b1 | 0.696 | 26.5% |
| b2 | 0.675 | 20.4% |
| b3 | 0.870 | 20.4% |

All medians are **below 1**. Stable across both resampling conventions (b2:
point 0.675 vs box 0.682, <1%). Full-depth numbers move <1% from the 100-frame
run, as the stride control predicted.

Of the 7 tiles at b2 where a source beats the merge by >1.25× under **both**
samplings, **5 are on the frame border** (row 0 / column 0, where the master's
crop and the frame's active area do not cover the same scene). Only **2 interior
tiles out of 486** lose at all, by ≤1.31×. Against a 25× sharp-vs-blurred deficit,
recovering them would be sub-visible.

**Whole-frame partition, 486 tiles** (band 2): 7 detail tiles lose by >1.25× |
42 detail tiles where the merge is not beaten | 0 detail-but-unmeasurable | 437
below detail threshold | **TOTAL 486 = 486.** Every tile lands in a counted
outcome; nothing is skipped and read as a pass.

### 5.45 The merge arm carries strehl's lateral-CA defect, and it flattered me

ORCH has since shown that the visible magenta is strehl's own lateral-CA
correction: it moves red from -2.009 px inward past zero to +0.672 px outward
while blue stays outward, so R and B pile up on the same side of every edge, on
12 of 14 coherent subjects.

**This lands on me because my merge arm is Rec.709 luma, not green** -
`0.2126 R + 0.7152 G + 0.0722 B`, so **28.5% of it is R and B**. A spurious
colour fringe is extra edge structure; extra edge structure inflates the merge
arm; an inflated merge arm drives the source/merge ratio **down**, toward
verdict **(a)** - the verdict I published. Unlike the selection premium (§5.5),
whose sign was adverse to my conclusion, **this one biases in my favour**, so it
had to be measured.

The control re-runs Stage B with the master's **green channel alone**. Green is
the reference channel that lateral-CA correction moves R and B *relative to*, so
the green-only arm does not carry the fringe. Frames are unchanged, so the arms
still differ only in the plane under test.

| band | merge arm = Rec.709 luma (published) | merge arm = green only |
|---|---|---|
| b1 point | 0.696 | **0.824** |
| b2 point | 0.675 | **0.768** |
| b3 point | 0.870 | 0.869 |
| b2 box | 0.682 | 0.660 |

**The effect is real: removing R and B raises the b1/b2 point ratios by 14-18%.
My published medians were flattered by a genuine product defect.** They are not
invalidated - every median remains **below 1** under both channel choices, so no
source frame beats the merge at the median detail tile either way.

**One site does move, and it is the one that matters.** Under the green-only arm,
site 1 (BLURRED, r05c02) flips to **(b) MERGE DEFECT at 1.32x - in band 1 only**.
Its licensed-band ratios are b2 = **0.999** and b3 = **0.946**. Restricted to the
licensed bands 2 and 3, all six sites return **(a)** under both channel
choices, identical to the published table.

So the honest statement is narrower than the one I first published:

- **The verdict (a) holds** on licensed bands under both channel choices.
- **The margin at site 1 is thinner than I represented.** At b2 the green-only
  source and merge are within 0.1% of each other - a tie, not a defeat. I
  previously reported that site at 0.975 and did not flag it as marginal.
- The one reading that would call site 1 a merge defect depends on **band 1,
  whose licence is withdrawn** (§2.1), and on the **green-only** arm. Neither
  alone is sufficient and I am not claiming a defect on that basis. It is the
  single tile in this study most worth re-measuring once band 1 is qualified.

### 5.5 The selection premium is inside my own instrument

ORCH facts 1843-1845: the max-of-N order statistic on a noisy measure
manufactures noise power, 24.82x at N=19 and 240.70x at N=79. My source arm
contains `max_k Var(b,k,t)`, so this applies to **my** instrument. Common-mode
cancellation removes the noise term's *mean*; it does not remove the upward bias
of taking a maximum. Two consequences, measured (`premium_control.py`), not
assumed:

**On the ratio, the premium is adverse to my own conclusion.** The source arm is
a max over N frames; the merge arm is one image with no max. So the premium
inflates the source arm *only*, drives the ratio *up*, and biases the rule toward
**(b)**. Measured inflation, N=176 versus N=88 on the same scene: median
**1.032**, p90 1.092, max 1.220 at detail tiles. The published verdict is (a),
reached *despite* a bias pushing the other way, and the bias is small enough
(3%) that it cannot account for ratios of 0.675.

**On the corpus ranking, it was not safe, and my own gate caught it.** This is
where I had a real problem: see §7 and refuted prediction 6. The `rise < 0.10`
criterion fires on **38.0%** of `flowers-cpl`'s no-detail tiles and up to 53.5%
elsewhere - not from the premium as such but from a sweep-wide trend. The fix is
`excess = stuck% - flat%`, each subject against its own null.

One process note worth propagating: my first version of this control tested raw
*argmax-at-boundary*, which is **not** the criterion the ranking ships
(`rise < 0.10`). It gave a comfortable 3.2x separation where the shipped
criterion gives 1.5x. Testing a proxy for the shipped statistic is the same
error as testing a report for the presence of a word instead of the claim it
certifies - it just looks more like real measurement.

## 6. Mechanism

Deliverable 3 asked, *if* (b): which frame should have won, which won instead. It
is (a), so the question is void — there is no frame that should have won. The
mechanism of the visible blur is that **best focus for those regions lies outside
the captured bracket, off the frame-0 end.** The curves do not turn over inside
the sweep, so the depth was never covered.

## 7. Deliverable 4a — corpus ranking on the capture-gap signature

`stuck%` = detail tiles whose through-focus curve is still at its maximum on a
boundary frame. **Frame-side only: no master, no registration, no resampling
choice enters it**, so no such choice can move the ranking.

**Corrected 2026-08-27 after the ORCH selection-premium broadcast. The table
below supersedes the raw-`stuck%` ordering I first published; §8.6 records what
was wrong with it.**

The confound that had to be removed: the criterion *also* fires on tiles with no
detail at all - on some subjects for more than half of them - because a
whole-frame trend across the sweep (illumination or level drift) can make the
boundary frame the maximum with no focus signal involved. `flat%` measures that
per subject; **`excess = stuck% - flat%`** is the drift-controlled statistic and
is the ranking. The confound is per-subject, so no global threshold could have
removed it.

| # | subject | frames | detail | stuck% | flat% | **excess** |
|---|---|---|---|---|---|---|
| 1 | **flowers-cpl** | 176/176 | 138 | 58.7 | 38.0 | **+20.7** |
| 2 | bee-1-cpl | 100/299 | 360 | 0.8 | 0.0 | +0.8 |
| 3-6 | 112MSDCF, 113MSDCF, coffee-bubbles, wrapped-text-1 | | | 0.0 | 0.0 | 0.0 |
| 9 | coffee-bean | 100/105 | 339 | 7.1 | 9.7 | -2.6 |
| 13 | bee-3-cpl | 100/299 | 392 | 0.3 | 25.9 | -25.7 |
| 14 | highly-angled-ruler-mm-cpl | 100/299 | 187 | 18.2 | 44.4 | **-26.2** |
| 15 | flower-bud-with-background-fern-cpl | 100/299 | 247 | 14.2 | 41.1 | -26.9 |
| 17 | tweezers-cpl | 100/100 | 291 | 0.0 | 30.4 | -30.4 |
| 21 | dry-erase-marker-head-cpl | 100/299 | 329 | 4.3 | 53.5 | -49.3 |

Corpus excess: median **-12.2**, max **+20.7**. **Subjects with excess > 5
points: 1 of 21.** Detail-definition agreement r = 0.978.

**`flowers-cpl` is the only subject in the corpus with a capture-gap signature at
all** - 26x the next value, and the only positive one of any size. It is one
badly-bracketed subject, not the tip of a corpus-wide defect. The drift control
*strengthens* the conclusion: from "a large outlier" to "the sole instance".

**On the orchestrator's two hints:** `tweezers-cpl` is **refuted** on both the
raw statistic (stuck% = 0.0) and the controlled one (excess -30.4).
`highly-angled-ruler-mm-cpl` I first **confirmed at #2 on raw stuck% (18.2), and
that confirmation is now withdrawn**: its no-detail tiles fire at 44.4%, so its
detail tiles are *less* stuck than its own null (excess -26.2). Its apparent rank
was its own sweep-wide trend, not a capture gap. Both hints were correctly
offered as hints; neither survives measurement.
**Outcome partition over all 26 delivered masters:** RANKED 21 | TOO-LITTLE-DETAIL
3 (`couch-fibers-cpl`, `flat-on-ruler-cpl`, `foam`) | UNREGISTERED 2
(`flower-inner-edge-cpl`, `wrapped-text-2`) | **TOTAL 26 = 26.**

### 7b. The merge-defect ranking, and why it must not be read as one

The companion ranking by `lose%` is reported in the tool but **carries a warning
that fires automatically**: agreement between the two detail definitions is only
**r = 0.557**, so 4b is partly a ranking of its own threshold and must not be read
as an ordering of merge quality. Its top entry is `coffee-bean` (20.35%), whose
median ratio is 1.10 — i.e. marginal, not a visible defect. `flowers-cpl` sits 7th
there. **4a is the ranking to use.** The one follow-up I would offer is a look at
`coffee-bean`, on the explicit understanding that 4b is weak evidence.

## 8. Predictions of mine that were refuted

1. **My leading hypothesis was (b), and a band-2 headline supported it.** The
   three blurred sites sit at the 90.9th–95.9th percentile of through-focus
   contrast on band 2. Had I headlined a single band I would have reported a merge
   defect. The full five-band ladder reversed it: at fine bands the blurred sites
   are 5–70× *poorer*. Coarse-band through-focus contrast is produced by a defocus
   *blob* moving through focus and does not imply resolved detail. This is the
   single strongest vindication of the project's "do not gate on a fixed band"
   rule that I produced.
2. **Stage B's pre-registered failure direction is violated at bands 3–4.** I
   registered that the uncorrected (grain-inflated) ratio must exceed the
   noise-corrected one. At b3 (0.859 < 0.870) and b4 (1.000 < 1.005) it does not,
   because there noise is negligible and the correction is dominated by the
   merge-side floor subtraction, which shrinks the denominator. **The claim holds
   only in bands 0–2.** Reported, not silently narrowed after the fact.
3. **My provisional detection floor was optimistic by 3×** — 0.5 master px from
   the unfaithful plant, 1.5 master px from the physical one.
4. **My first corpus ranking was partly a ranking of its own threshold**
   (r = 0.122), and `couch-fibers-cpl` ranked #1 on n = 2 tiles. My own gates
   caught both, which is why 4a now leads with the registration-free statistic.
5. **My own `rank.py` reported a worst-case ratio of 4.5e14.** The
   measurable-signal guard filtered the lose *count* but not the reported worst
   and median, so a tile excluded as a division artefact still supplied the
   headline. Fixed; `dry-erase-marker-head-cpl` 4.5e14 → 14.25,
   `flowers-cpl` 27.01 → 4.94. None of the §5 verdict numbers depend on it.
6. **I confirmed the orchestrator's `highly-angled-ruler-mm-cpl` hint, and I was
   wrong to.** Prompted by the ORCH selection-premium broadcast I built the
   no-detail null I should have built first. The ranking criterion fires on
   tiles with *no detail at all* on most subjects - 44.4% of them on the ruler,
   53.5% on `dry-erase-marker-head-cpl`. Against its own null the ruler's 18.2%
   is **negative** (excess -26.2): its detail tiles are *less* stuck than its
   structureless ones. **The confirmation is withdrawn.** My published ranking
   rows 2-10 were substantially measuring each subject's own sweep-wide trend.
   The corrected result is *stronger*, not weaker - `flowers-cpl` goes from a
   3.2x outlier to the **only** subject in the corpus carrying the signature -
   but I published the uncontrolled version first and it named a subject that
   does not have the defect. The `tweezers-cpl` refutation survives the control.
7. **I commissioned the statistic but never the decision rule.** Also prompted by
   the broadcast. `commission_tfc.py` proves the *number* moves correctly; it
   says nothing about whether the (a)/(b) *rule* sitting on top of it can emit
   (b) at all. A rule structurally stuck on (a) would have agreed with the prior,
   agreed with `BUILD-TRIAGE.md`, and passed every test I had. The gap is now
   closed and the rule passes 4/4 - but it was open when I published the verdict,
    and nothing I had run would have caught it.
8. **My commissioning harness had the V-LINEAR defect, and I only found it
   because ORCH's postscript told me to look.** `commission_verdict.py` v1
   parsed each printed verdict down to the letter `(a)` or `(b)`. But the rule
   reaches **three** conclusions, not two: `(b)` merge defect, `(a)` capture gap,
   and `(a)` merge-not-beaten-because-focus-was-captured. The letter parser
   collapsed the two `(a)` classes into one symbol - and **the distinction it
   erased is the actual product claim, reshoot-this versus retouch-this.**
   Measured, not supposed: the T5 arm changes the conclusion class at **3 of 6
   sites while changing the letter at 0 of 6**, so v1 would have reported a
   fully reversed focus verdict as UNCHANGED, with every number in this document
   still correct. Fixed by parsing the conclusion class and adding T5/T6; the
   harness now catches 6 of 6 arms. This is the same shape as V-NEVERWORSE's 712
   green checks and V-LINEAR's 88/88, and I had it too.
9. **My merge arm was contaminated by a product defect that flattered my own
   result, and I did not notice for three rounds.** The arm is Rec.709 luma, so
   28.5% of it is R and B - the two channels strehl's lateral-CA correction
   piles onto the same side of every edge. The spurious fringe inflates the
   merge arm and pushes the ratio toward (a). Measured (§5.45): removing R and B
   raises the b1/b2 ratios by 14-18%, and site 1 flips to (b) at 1.32x in band 1.
   The verdict survives on licensed bands, but **the margin at site 1 is a tie
   (b2 = 0.999), not the comfortable 0.975 I published**, and I should have
   noticed that a luma arm imports every chroma defect in the product into a
   measurement that did not need chroma at all. Using green alone from the start
   would have cost nothing.
10. **Three of my arms were sensitivity-only.** T2-T6 all plant something and
   require a reaction; none established that the rule stays put when handed a
   change carrying no information, and none tested that a *deleted* finding is
   refused rather than silently passed. T7/T8 close both. Separately, every
   "PASS" I had reported was uncertified until the pass/fail channel itself was
   commissioned - an inert plant and a dead instrument print the same green.

## 9. Defects I found in my own instrument before trusting it

- **G1×G2 covariance sign inversion near Nyquist** — would have manufactured
  verdict (a) for the wrong reason. Estimator demoted.
- **PTC estimator** gave a physically impossible negative read-noise intercept and
  a 162× per-band gain spread. Deprecated in favour of the common-mode
  cancellation in §2, which fits no noise model at all.
- **Unfaithful blur plant** (§3), corrected to a physical one.

The reasoning for each demotion is kept in comments in `ora.py` as the audit
trail.

## 10. Unexpected finding, flagged not diagnosed

Translation-only registration of master→frames failed across most of the corpus
with weak (peak 2.6–3.6) and **mutually inconsistent** residuals — point sampling
wanting (26, 99) where box wanted (37, -124) on the same subject. Inconsistency of
that kind means a missing degree of freedom. Adding a scale search fixed it:

| subject | scale | peak |
|---|---|---|
| flowers-cpl | 0.990 | 13.5 |
| bee-1-cpl | 0.930 | 25.4 |
| couch-fibers-cpl | 0.891 | 24.8 |

**The delivered master differs from its own source frames in scene scale by up to
11%, subject-dependent.** Any fixed-grid merge-vs-frame comparison that ignores
this is comparing different scene patches — a trap for any future lane doing this
kind of work. Whether the cause is focus breathing, an aligner `fit_to_cover`
artefact, or a render-canvas difference is **not** determined here. Flagged as an
observation, not a diagnosis.

## 11. How the arms differ only in the variable under test

The variable under test is *which image plane* is scored. Both arms are pushed
through **one call to `ora.tile_stats(g1, g2, ts)` on full-size planes** — same
band decomposition, same tile grid, same noise handling, same code. The master
supplies both green sub-lattices exactly as a raw frame does, so there is no
"master path" and "frame path" to diverge. Verified additionally by direct
comparison: Stage B's stored source arm `src_sig` equals Stage A's `contrast` to
**1.0000 at p10, median and p90 across all 486 tiles** in every band checked.

Two resampling conventions (point and box) are carried end-to-end and reported
separately throughout; a tile only counts as losing if it loses under **both**,
because a result that depends on the resampling choice is a measurement of the
choice.

Per the project rule, comparisons are on **pixels, never file hashes** — TIFF
`ImageDescription` carries tool parameters, so identical pixels can hash
differently.

**Subsampling control.** The corpus survey uses 100 frames per subject. Calibrated,
not assumed: stride 1 → 1.0000 exactly (identity control); stride 2 → worst tile
0.9093; stride 3 → 0.8680; stride 4 → 0.8229; stride 8 → 0.4945. The directional
risk was stated in advance — under-sampling misses sharp frames, under-reports the
*source* arm, and drifts every subject toward verdict (a), i.e. toward agreement
with the prior. `flowers-cpl`, the subject the verdict rests on, is therefore run
at the **full 176 frames**; its numbers move <1% from the subsampled run.

## 12. Reconciliation with prior art

`BUILD-TRIAGE.md` classified `flowers-cpl` as CAPTURE-LIMITED and refuted
`flowers-cpl`, `highly-angled-ruler-mm-cpl` and `tweezers-cpl` as merge failures —
the same three subjects in this brief. **I reach the same verdict by a genuinely
independent route**: through-focus common-mode cancellation over a dense 486-tile
grid, versus their grain decomposition at four hand-picked sites. I also localise
it further: the deficit is at the **frame-0 end** and the curve is **monotone
decreasing**, which is a stronger statement than "peak at a bracket end".

Two known results were deliberately *not* re-derived, per the brief: the
**selection premium** (max-of-N order statistic, 24.8× at N=19, 240.7× at N=79)
and the refuted `fit_to_cover` upsample (270× too small). Neither explains this
defect: the premium is a grain/softness effect, whereas the blurred regions here
have *large coarse-band and near-zero fine-band* contrast, and their curves never
turn over inside the bracket. Nothing I measured revives either explanation.

## 13. Product implication

`excess = stuck% - flat%` (§7) is the shippable half of this result. It needs
**no master, no registration and no resampling choice** - it is computed frame
side, during or immediately after capture. It separates "reshoot this" from
"retouch this", which is a feature the project already wants.

**Ship the drift-controlled form, not raw `stuck%`.** Raw `stuck%` fires on
tiles with no detail at all - 53.5% of them on `dry-erase-marker-head-cpl` - so a
product built on it would tell users to reshoot subjects that are correctly
bracketed. Each subject must be scored against its own no-detail rate. On the
controlled statistic the corpus separates cleanly: **1 subject of 21 above +5
points, `flowers-cpl` at +20.7, corpus median -12.2.**

For `flowers-cpl` specifically the honest user-facing message is: **the bracket
did not cover the near depth; extend the sweep past the frame-0 end and
reshoot.** No merge change will recover those regions, because the information is
not in the data.

---

### Files

All code in `experiments/V-ORACLE/`; all heavy output under
`D:\strehl-out\V-ORACLE\` (never on C:), with full-resolution intermediates
deleted once reduced to numbers.

| file | role |
|---|---|
| `ora.py` | core library; bands, tile stats, the shipped `through_focus_contrast`; demotion audit trail in comments |
| `commission_tfc.py` | commissions the shipped statistic; `physical_defocus()` is the function that mattered |
| `correspond.py` | the drift control of §4 |
| `curves.py` | **the decisive evidence** — through-focus curves + `rise` |
| `stageA.py` / `stageB.py` | frame-side cube; master-vs-source with similarity registration |
| `verdict.py`, `losers.py`, `sites.py` | deliverables 1–3 |
| `survey.py`, `surveyB.py`, `rank.py` | deliverable 4 |
| `commission_verdict.py` | commissions the (a)/(b) DECISION RULE with conclusion-flipping mutations |
| `bandfreq.py` | measures where each band sits in cyc/px (§2.1) |
| `premium_control.py` | selection-premium and no-detail-null controls; produced the §7 correction |
| `stride_control.py` | subsampling calibration of §11 |
| `mapmake.py` | the per-tile map, `D:\strehl-out\V-ORACLE\maps\flowers-cpl-b2.png` |

The map's panel 1 (master) shows the blurred sites on smooth blobs; panel 2
(best available source structure) shows **the same spatial pattern** — where the
master is blurred, no source frame had structure either. That is the whole result
in one picture.
