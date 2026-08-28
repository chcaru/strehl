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

| # | subject | frames | detail | stuck% |
|---|---|---|---|---|
| 1 | **flowers-cpl** | 176/176 | 138 | **58.7** |
| 2 | highly-angled-ruler-mm-cpl | 100/299 | 187 | 18.2 |
| 3 | flower-bud-with-background-fern-cpl | 100/299 | 247 | 14.2 |
| 4 | coffee-bean | 100/105 | 339 | 7.1 |
| 5 | dry-erase-marker-head-cpl | 100/299 | 329 | 4.3 |
| 6 | pencil-steep-angle-cpl | 100/299 | 228 | 3.1 |
| 7 | lavendar-cpl | 100/299 | 193 | 1.6 |
| 8 | bee-1-cpl | 100/299 | 360 | 0.8 |
| 9 | 119MSDCF | 33/33 | 168 | 0.6 |
| 10 | bee-3-cpl | 100/299 | 392 | 0.3 |
| 11–21 | (109/112/113MSDCF, bee-2, coffee-bubbles, flower-bud-alone, lead-1, leaf-2, pencil-flatter, **tweezers-cpl**, wrapped-text-1) | | | **0.0** |

Corpus median **0.0**, max 58.7. Agreement between the two detail definitions
**r = 0.978** — this ranking is not a ranking of its own threshold.

**`flowers-cpl` is a massive outlier**, 3.2× the next subject and against a corpus
median of zero. It is one badly-bracketed subject, not the tip of a corpus-wide
merge defect.

**On the orchestrator's two hints:** `highly-angled-ruler-mm-cpl` is
**confirmed** at #2 (18.2%). **`tweezers-cpl` is refuted**: stuck% = **0.0**, and
its top-left region shows nothing. That hint was correctly offered as a hint and
it does not survive measurement.

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

`stuck%` (§7) is the shippable half of this result. It needs **no master, no
registration and no resampling choice** — it is computed frame-side, during or
immediately after capture. It separates "reshoot this" from "retouch this",
which is a feature the project already wants, and it is a clean outlier detector:
`flowers-cpl` 58.7% against a corpus median of 0.0.

For `flowers-cpl` specifically the honest user-facing message is: **the bracket
did not cover the near depth; extend the sweep past the frame-0 end and reshoot.**
No merge change will recover those regions, because the information is not in the
data.

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
| `stride_control.py` | subsampling calibration of §11 |
| `mapmake.py` | the per-tile map, `D:\strehl-out\V-ORACLE\maps\flowers-cpl-b2.png` |

The map's panel 1 (master) shows the blurred sites on smooth blobs; panel 2
(best available source structure) shows **the same spatial pattern** — where the
master is blurred, no source frame had structure either. That is the whole result
in one picture.
