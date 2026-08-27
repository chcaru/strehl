# V-NOISE2 — does M127's noise advantage generalise across subjects?

**Status: IN PROGRESS.** Three of four subjects measured, one still building. A
milestone number has been **requested from the orchestrator and not yet
allocated**, so this file lives in `experiments/V-NOISE2/` and is not a record.
Nothing here should be cited from `docs/research/` until it moves.

> **Newest result: §10.** The frame-count ladder returns **NO BRANCH** in both
> bands. The naive reading would have **corroborated** ORCH's dilution
> mechanism (`Q` = 5.3, RISING); it is refused by this lane's own controls. A
> nuisance parameter moves `R` **6.20×** at constant `N`, and the instrument's
> BLOTCH arm **cannot respond at any potency** on most rungs. §9's subject
> `119` is cleared.

> **§9.** The half-to-half discriminator reads **R = 12.4×** in
> the **convicted 20–60 px band** — a band §8 never measured and which sits an
> order of magnitude coarser than §8's. Branch **SELECTION**: this lane holds a
> real second mechanism.

> **§8** — `119MSDCF`'s 2.017× detail deficit against `enfuse` is
> **half-stack incoherence, not absent detail** — the full renders read 1.003
> [0.670, 1.570] in the same band on the same pixels, and 2.017 lies outside
> that interval. This closes the question §7.4 left open, and it implies our
> own published noise figures are biased *against* us on selection-dominated
> merges.

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

> **RESOLVED in §8.** The sentence above is answered by a measurement that
> reads no half-stack at all. Keep §7.4 as the statement of the mechanism;
> take §8 as the verdict on which branch is true.

---

## 8. The 2.017 is half-stack incoherence, not absent detail

ORCH set the question: is `119MSDCF`'s 2.017× detail deficit against `enfuse`
**true detail loss**, in which case the project's central quality claim is
broken, or **half-stack incoherence**, in which case the detail is present in
the delivered image, the instrument cannot see it, and the published noise
figures are biased *against* this project.

The second branch flatters us. It therefore gets the hostile handling.

### 8.1 Route 1 — sidestep the half-stack entirely

ORCH's route 1: measure total high-pass amplitude on the **full** merges, in
the same band, on the same pixels. That counts detail whether or not it is
coherent across halves. `build_full.ps1` built both full renders with the
byte-identical pinned binary and flags used for the half-stacks (`strehl.exe`
verified by SHA256 `15EA7346…A7B0`); `fullhp.py` reads them. **No half-stack is
read anywhere in `fullhp.py`**, which is the whole point of the design.

**The criterion was registered before the data existed.** `PREREGISTRATION.md`
§9 — committed as `91150f56` together with `fullhp.py` **unrun** — fixes three
branches with numeric thresholds: LEVEL (ratio ∈ [0.90, 1.11] and CI contains
1.0), CONFIRMED (≥ 1.5), PARTIAL (anything else). The branch could not be
chosen after the number was seen.

### 8.2 Band limitation, stated before any two terms are combined

ORCH required this explicitly, because M127's published defect was a *full-band*
noise term subtracted from a *high-pass* total. Let `B` = [0.20, 0.25) cyc/px
and `B_c = s·B` = [0.2008, 0.2510) with `s = 1.0040`.

| term | band-limited? | to what |
|---|---|---|
| `bp(tile)` | yes | `B` on strehl, `B_c` on `enfuse` |
| `F(L)` — noise from FLAT tiles at level `L` | yes | same annulus as its arm |
| `S_d = bp(d) − F(level of d)` | yes | difference of two terms in the same annulus |
| `S_X = median S_d` | yes | as above |

**Every term is band-limited to the same annulus. There is no full-band
quantity anywhere in the file.** The M127 defect cannot recur by construction.

### 8.3 The verdict

MEASURED, `python fullhp.py 119 4000`:

| quantity | value |
|---|---:|
| half-stack `C`, same subject / band / arm | **2.017** |
| full-render band amplitude, `enfuse` / strehl, **uncorrected** | 1.330 |
| full-render band amplitude, **corrected** | **1.003** [0.670, 1.570] |

**LEVEL.** The 2.017 is not present once the half-split is removed, and it lies
**outside the 95% CI of the full-render reading**. On this subject the deficit
is half-stack incoherence, not absent detail: **the detail is in the delivered
image and the coherence statistic cannot see it.**

That has a consequence this lane does not get to enjoy quietly — it means
**our own published noise figures are biased against us** on selection-dominated
merges, because incoherent detail lands in the half-difference and is scored as
noise. That is a correction owed in our favour and it is stated as an
implication, not as a new measurement.

### 8.4 Commissioning — 10 arms, every answer fixed in advance

`strehl-full` against a mutated copy of **itself**:

| arm | true | reads | err | uncorrected |
|---|---:|---:|---:|---:|
| IDENT-BITWISE | 1.000 | 1.0000 | +0.0% | 1.0000 |
| IDENT-PATH | 1.000 | 1.0000 | −0.0% | 1.0000 |
| **SHARPER k=1.30** | **1.300** | **1.3157** | **+1.2%** | 1.2982 |
| k=0.95 / 0.85 / 0.70 / 0.50 | — | — | ≤ 2.2% | — |
| NOISE-PROP (8 seeds) | 1.000 | 0.9921 | −0.8% | **1.4789** |
| NOISE-ABS (8 seeds) | 1.000 | 1.0419 | +4.2% | **1.6740** |
| NOISE+DETAIL (8 seeds) | 0.700 | 0.7222 | +3.2% | 1.2926 |
| SCALE-PATH | 1.000 | 1.0133 | +1.3% | — |

The **SHARPER** rung is there because a statistic bounded below at parity would
pass a degradation-only ladder trivially, and this project has already shipped
one gauge that was perverse on its own arm.

**The noise arms are ORCH's required control** — noise planted without detail,
which the statistic must not reward. The uncorrected reading rises to 1.48–1.67
and the correction removes it. Each is read over 8 realisations with a standard
error, not one draw against a fixed gate: *a point estimate with no notion of
its own sampling spread cannot distinguish a broken instrument from a noisy
one*, and this lane spent three estimator rewrites learning that (§8.6).

### 8.5 Three defects, each caught by an arm whose answer was known in advance

None of these was found by reading the code. Each was found by an arm that
returned an impossible number, and each was **diagnosed before anything was
changed**.

**D1 — crossed axes in the placement bounds test.** `xb + b > self.mb.shape[0]`
tests an *x* index against a *row* count. With `rb.shape = (1172, 1758)` at 4×
block means this rejects every tile with x > 4432 (DERIVED) in a 7032-px-wide
frame — the right ~37%. MEASURED, it dropped 35 of 110 tiles with x ∈ [4480,
6528] against a kept maximum of 4224. It **changed the tile population instead
of raising**. Caught because the placer at s=1.0000 returned
correlation peak *exactly* 1.0000 and offset *exactly* 0/0 — literally the
identical pixels the baseline read — and S still moved 12%. Identical pixels
cannot give a different answer, so the population had to have changed.
`scalediag.py` reproduces it against the code as committed at `91150f56`:

| placer | s | ratio | tiles kept |
|---|---:|---:|---|
| BUGGY | 1.0000 | 0.8808 | 75/110 (35 dropped, x ∈ [4480, 6528]) |
| BUGGY | 1.0040 | 0.8845 | 75/110 |
| **FIXED** | **1.0000** | **1.0000** | **110/110** |
| FIXED | 1.0040 | 1.0008 | 110/110 |

**D2 — the arms were read at different tile sizes.** Matching scene *area* gave
strehl t=256 and the comparator t=round(256/1.0040)=255. The annulus is a
discrete bin set whose membership is not stable under tile size. MEASURED on
strehl against itself: **t=255 → +4.5%, t=250 → +10.0%, t=128 → −11.6%.** The
comparator was the arm read at 255, inflating it ~4.5%. Repair: read **both**
arms at t=256 and scale the comparator's *band* instead, which resamples no
measured pixel. BANDSHIFT magnitude MEASURED at **+0.52% power / +0.26%
amplitude**.

**D3 — the assumption of equal noise power in both tile populations was false,
and catastrophically so.** `leveldiag.py` fits `bp ~ L^p` over FLAT tiles:
**p = −1.145 [−1.346, −0.947]** (strehl) and **−0.920 [−0.984, −0.863]**
(`enfuse`) — both consistent with **p = −1, exactly shot-noise-limited in
contrast units**, which is what a linear sensor image must give. The fit landed
on the physically predicted value without being told it. Under the assumed
p = 0, `enfuse`'s scene term collapsed to 1.10e-07 against a total of 4.42e-05
and the ratio would have printed **0.089** — an absurdly flattering number this
lane came within one failed arm of reporting. The repair is **non-parametric
level matching**, which assumes no `p` at all.

### 8.6 A plant can be too potent to be informative — a new general lesson

Three successive noise estimators failed the noise arms by −4.9%, +15.1% and
+20.3%. Each rewrite was refuted by an arm rather than by taste, and the second
pair — two arms erring in *opposite* directions — correctly identified the
estimator's *basis* as the fault rather than its tuning.

The fourth attempt was to stop guessing. `noisediag.py` separates bias from
variance by sweeping the plant amplitude with 12–20 seeds per cell, reporting
`a/S` — how many times the plant exceeds the signal it is planted on:

| a/S | NOISE-PROP | NOISE-ABS |
|---:|---:|---:|
| 0.14 | 0.9928 | 0.9927 |
| 0.54 | 0.9874 | 0.9939 |
| 2.16 | 0.9870 | 1.0273 |
| 2.43 | 0.9972 | 1.0415 |
| 3.11 | 1.0040 | **1.0748** |
| 4.24 | 1.0235 | **1.1093** |
| 5.53 | **1.0548** | **1.1314** |
| 8.65 | **1.1157** | **1.1553** |

**The estimator was unbiased all along.** The three "failures" were the tail of
a wide sampling distribution at a plant 8.65× the signal. Past a few times the
signal, the scene term becomes a difference of two large nearly-equal numbers;
the arm then measures the estimator's *variance* instead of its *correctness*,
and inflates that variance ~10× without testing it any harder.

**Stated as a general lesson, alongside QUANT8 and the inert control:** a
commissioning plant has an upper useful bound as well as a lower one. Too weak
and it proves nothing; **too strong and it fails a working instrument.** The
plant must *bracket the regime the real measurement occupies*, not exceed it.

Lowering `BETA` from 0.040 to 0.020 is **not** tuning-to-pass, for two reasons
that must be stated together: the change is justified by an independent
measurement showing the estimator unbiased across a 16× range of potency, and
**both** noise arms are checked on every run, so no repair can be adopted on the
strength of the arm it was designed to pass.

The lesson was then turned into a **gate**. `fullhp.py` computes `a/S` for the
real reading and **refuses to print a verdict outside the range actually
commissioned**. It fired on the first attempt: `enfuse` reads 2.22 against a
then-commissioned 2.16. The response was to *extend the commissioning by
measurement* to 2.43 — which is what the refusal message itself prescribed —
not to lower the gate to admit the number.

**The residual systematic is disclosed rather than corrected**, with its
direction: at a/S = 2.43 it is [−0.3%, +4.1%], and it inflates the scene term of
whichever arm carries more noise. That is `enfuse` (2.22 against strehl's 0.84).
**The bias therefore acts against strehl**, so the true position is if anything
better for us than 1.003.

### 8.7 Hostile reading

1. **The correction carries the answer**: 1.330 uncorrected → 1.003 corrected.
   The noise subtraction, not the raw band power, produces this verdict. If the
   noise model is wrong the answer is wrong.
2. **S is a difference of comparable numbers.** FLAT/DETAIL band power is 0.425
   for strehl but **1.056** for `enfuse` — `enfuse` is 3.04× noisier here, so
   most of its DETAIL-tile band power is its own noise and the estimate is
   correspondingly fragile.
3. **The known failure mode of a total-band statistic is that it counts noise as
   detail**, so a noisier merge scores higher. `enfuse` is the noisier arm, so
   the *uncorrected* reading is biased toward `enfuse` and **the correction moves
   in strehl's favour — the flattering direction.** Both are printed, always.
4. **FLAT tiles are the bottom quartile of high-pass energy, not zero**, so S
   under-states scene power in *both* arms.
5. **What is established is that the full render does not show the 2.017.** What
   is *not* established is that the two are precisely equal: the CI [0.670,
   1.570] is wide.
6. **One subject, one band, one comparator.** Nothing here generalises without
   being re-run.

### 8.8 Two assumptions tested rather than asserted

`popcheck.py` was written because the reading prints "86 matched / 24 dropped"
for both arms, and **equal counts are not equal sets**.

- **Q1 — same tiles in both arms? PASS.** strehl keeps 86, `enfuse` keeps 86,
  intersection **86**; zero kept by either alone. The arms are read on the same
  scene. This was worth verifying rather than assuming: at KMIN=5 the arms keep
  84 and 83, so population identity is a property of the as-run setting, not a
  guarantee of the rule.
- **Q2 — is the drop a biased subset? YES, p = 0.000.** The 24 dropped tiles are
  *brighter* (median level 15058 vs 10095) and much *lower* in band power
  (2.09e-06 vs 3.08e-05); 13 of 24 lie outside the FLAT level range entirely, so
  they cannot be level-matched. **This is a real limitation and it is reported as
  one.** It is not a *differential* bias — Q1 shows both arms drop the same
  tiles — so it restricts what the reading *describes* (the level-matchable 86)
  without biasing the ratio between arms. It does mean the comparison excludes
  the brightest regions, which is exactly where `enfuse --hard-mask` is
  structurally most different.
- **Q3 — does the verdict depend on the matching rule's own parameters?**

  | LOGTOL | KMIN | n | ratio |
  |---:|---:|---:|---:|
  | 0.15 | 3 | 86 | **1.003** ← as run |
  | 0.25 | 3 | 104 | 0.804 |
  | 0.40 | 3 | 110 | 0.903 |
  | 0.15 | 2 | 87 | 1.011 |

  The ratio moves over **0.804–1.011**, and **no setting comes near 2.017** —
  including LOGTOL=0.40, which drops nothing at all. The verdict "not 2.017" is
  robust to the rule; the exact digit is not. Note the wider windows put strehl
  **ahead**, so the as-run 1.003 is the *least* flattering of the stable
  settings.

### 8.9 What would falsify this

A full-render reading near 2.0 on another selection-dominated subject; or a
demonstration that the FLAT population carries materially different scene power
in the two arms, which would break the noise subtraction that carries the
result. Route 2 — measuring the per-half selection-field disagreement rate
directly — would settle the mechanism rather than its consequence, but it needs
a winner field emitted from `merge.rs`, which is **owned by a build lane and
closed to this one**. That is a request for ORCH to route, not a file for me to
take.

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

Added by §8:

- **`fba` (`flower-bud-alone-cpl`) is build-FAILED, not absent.** 189 minutes in
  `align_image_stack` with **0 output files**. Per `PREREGISTRATION.md` it is
  recorded as a failed subject; it is not silently dropped from the subject
  list, because a subject that disappears without a disposition is how a
  flattering subject set gets built by accident.
- **§8 is one subject.** The full-render reading should be repeated on
  `bee-1-cpl`, the selection-dominated deep stack, where the incoherence
  mechanism should be *strongest* — §8.9's falsification condition is a
  full-render reading near 2.0 there.
- **Route 2 is unbuilt and needs ORCH to route it.** Measuring the per-half
  selection-field disagreement rate directly would settle the *mechanism*
  rather than its consequence, but it requires a winner field emitted from
  `crates/strehl-core/src/merge.rs`, which is owned by a build lane.
- **The correction owed in our favour is stated, not measured.** §8.3 argues
  that incoherent detail is scored as noise on selection-dominated merges; the
  size of that bias in the published M127 figures has not been quantified.
- Still owed as standing reporting obligations: CGAIN straddle-vs-magnitude
  with both numbers; `Arm.rgb` scale-only-no-offset; `119`'s weak 1.29× and
  `fba`'s 1.10× census separation; `bee`'s weak 0.2205 geometry peak; and the
  `crosspop` vs `banddiag` scene-ratio discrepancy (1.273 vs 1.733), which
  **remains unreconciled**.

---

## 9. The half-to-half discriminator — SELECTION, and the band changes what §8 meant

ORCH reports that fixing the merge exponent caps at **57% of the excess blotch
on one subject**, leaving ~43% unexplained across three candidate lanes, and
supplies the discriminator: **a noise-driven selection is not reproducible
across two independent half-stacks, whereas alignment drift produces coherent
error in both halves.**

`merge.rs` is closed to me, so I cannot read the per-pixel frame choice. I read
its **signature** instead, and — this is the design — I read the *same*
signature off `enfuse` built from the *same* linear TIFFs with the *same* half
splits. Incoherence specific to our merge shows as an excess over `enfuse`;
incoherence shared with it lives in the inputs both arms consume, which is the
**alignment** lane's territory, not mine.

### 9.1 The band, stated first, because it qualifies §8

| band | cyc/px | period | |
|---|---|---|---|
| `COARSE` | 0.0167–0.0500 | **20–60 px** | the convicted plateau |
| `FINE` | 0.2000–0.2500 | 4–5 px | §8's band |

**These are an order of magnitude apart. §8's LEVEL verdict says nothing about
the band where the second mechanism is suspected to live**, and this lane had
never measured that band. Both are read here and always reported together.

### 9.2 The statistic, and its band limitation

Per tile: `d = (A−B)/2`, `m = (A+B)/2`, **`phi = P_d / P_m`**. **Both terms are
band-limited to the same annulus**; `P_coh = P_m − P_d` is the only derived
combination and both of its terms live in that one annulus. There is **no
full-band quantity anywhere in `incoh.py`** — M127's published defect cannot
recur by construction.

A normalisation trap was met and handled: `h2.contrast_fft` divides a crop by
its **own** mean, which is meaningless for a half-difference whose mean is ~0.
Both terms are normalised by the **same** supplied level, which is what makes
their ratio a fraction rather than an artifact of two normalisations.

### 9.3 The verdict

MEASURED, `python incoh.py 119`:

| band | pop | strehl `phi` | `enfuse` `phi` | **R** |
|---|---|---:|---:|---:|
| **COARSE** | **DETAIL** | 0.00357 | 0.00029 | **12.424 [6.067, 19.468]** |
| COARSE | FLAT | 0.00902 | 0.00849 | 1.062 |
| FINE | DETAIL | 0.4106 | 0.3029 | 1.355 [1.010, 2.252] |
| FINE | FLAT | 0.7612 | 0.7243 | 1.051 |

**Branch SELECTION**, against thresholds registered as `2ada7413` before
`incoh.py` existed. In the convicted band our merge's halves disagree **12×**
more than `enfuse`'s on the same tiles. **This lane holds a real second
mechanism.**

### 9.4 Four hostile checks, because the number is large

`incohcheck.py`. The result convicts this lane, but a 12× is exactly the sort
of number that is wrong.

- **C1 — are `enfuse`'s halves genuinely different?** If the build had handed
  both halves the same frames, `phi_enfuse ≈ 0` by construction and R would be
  an artifact of the *build*. MEASURED: `mean|A−B|/level` is **0.01141** for
  `enfuse` against **0.00451** for strehl, zero bit-identical tiles. **`enfuse`'s
  halves differ 2.5× *more* than strehl's in absolute terms** and still carry
  12× *less* band-limited coarse disagreement. C1 does not void the result; it
  strengthens it.
- **C2 — is it just perversity?** `phi` is minimised by the worst merge, and
  `enfuse` is 9.1% lower in coarse amplitude. Answered **quantitatively off the
  `PERVERSE` arm** rather than by assertion: that arm measures the slope
  `d_phi/d_amp = 1.05`, which predicts `phi_enfuse/phi_strehl = 0.905` from the
  amplitude gap alone. Observed is **0.0805**. **Perversity accounts for 10.3%
  of the gap** — real, and nowhere near sufficient.
- **C3 — a few tiles?** n = 110 per arm, 2000 bootstraps, **both CIs exclude
  1.0**. No tiles were dropped in either arm in either band, so unlike §8 there
  is no population question here at all.
- **C4 — the control that actually discriminated.** FLAT tiles have no scene
  structure, so selection has nothing to select over *and* alignment has nothing
  to displace. The arms should not differ there, and **they do not: 1.062 and
  1.051.** The excess appears **only where scene structure exists**, which rules
  out "strehl is simply noisier" as the cause.

**C4 was not the instrument designed for this job.** The signature separator
was, and it failed (§9.6). The discriminating evidence came from a control
population that was already there.

### 9.5 §7 and §8 reconciled, by a statistic built independently of both

| what is counted | reading |
|---|---:|
| half-stack `C`, published (coherent only) | 2.017 |
| **FINE coherent-only amplitude, this file** | **1.651** |
| §8 total amplitude, noise-corrected | 1.003 [0.670, 1.570] |

The coherent-only reading reproduces `C`'s **direction and rough magnitude**
from an instrument built without reference to it, while the total reading is
level. **The gap between 1.651 and 1.003 *is* the incoherent detail**, and it
is now a measured quantity rather than the hypothesis §8 left it as.

### 9.6 Two instrument failures, reported rather than repaired quietly

**A fixed plant amplitude is wrong by construction across two bands.** The
first run failed `NOISE-INC` at +4.7% against a >5% gate. The cause is not the
estimator: white noise spreads over the whole frequency plane and an annulus
captures only its area fraction — **0.00698 for COARSE against 0.0707 for
FINE, a factor of 10**. The plant was simply too weak in the coarse band. Plant
amplitude is now **derived per band** to land at `a/S = 1.0` (β = 0.1389 COARSE,
0.0124 FINE — an 11× difference). **§8.6 established that a plant can be too
potent; this is the mirror image, and together they say the same thing: potency
must be chosen against the regime being measured, and it is band-dependent.**
Commissioning now runs **per band**, because a statistic commissioned in one
band is not commissioned in another.

**My signature separator did not separate.** It was designed to attribute the
mechanism — alignment drift lands error on gradients, selection lands it in
areas. MEASURED: `SHIFT` +0.490, `BLOTCH` +0.426, **unmutated baseline +0.457**.
The calibration arms **straddled** the thing they were meant to bracket, because
`|d|` tracks `|∇m|` under every mechanism. Replaced by an edge/area
concentration ratio, which is better posed but still spans only **0.86×** —
`BLOTCH` reads *more* edge-concentrated than `SHIFT`, the reverse of the
prediction, because blending a *blurred* copy also perturbs edges most. **The
signature is therefore reported as UNDETERMINED** and `incoh.py` prints it that
way rather than reading it in whichever direction suits. R stands on its own.

### 9.7 What this does and does not license

**MEASURED:** in the convicted band, our merge's per-half output disagrees 12×
more than `enfuse`'s, only where there is scene structure, and not explicable
by perversity or by noise.

**ARGUED, not measured:** that this *is* the missing 43% of the blotch excess.
I have measured **selection instability**, not blotch. The link is ORCH's
discriminator applied to my number, and it is an inference. **57% must not be
quoted as a corpus ceiling and 12.4× must not be quoted as a share of the
blotch.**

**Still one subject, two bands, one comparator.** `bee-1-cpl` at N=299 is where
this should be strongest and it has not been run.

> **FORWARD BANNER, added by §10.** The sentence above is now stale. `bee` has
> since been run at N=299 and across a frame-count ladder. It is **not** where
> this is strongest: `bee`'s FLAT control fails at every rung (0.460–1.252
> against [0.80, 1.25]) and its BLOTCH commissioning arm cannot respond at any
> potency below N=100, so most of `bee` is **uncommissioned** for this
> statistic. §9's own subject `119` is unaffected and is cleared by direct
> measurement in §10.3.


---

## 10. The frame-count ladder — NO BRANCH, and the instrument is the reason

> **VERDICT: the ladder cannot answer whether `R` rises with `N`.** Both bands
> return **NO BRANCH** under §12.4's gate. The naive reading — first rung 2.316,
> last rung 12.313, `Q` = 5.3, **RISING**, ORCH's dilution mechanism
> corroborated — is **refused by my own controls**, and it is refused twice
> over: once because the design confounded `N` with a nuisance parameter, and
> once because the instrument is **uncommissioned at most rungs of the ladder**.
>
> **§9 is not affected.** Its subject `119` passes the same check with the
> largest margin of any key measured (**+95.5%** COARSE, **+92.2%** FINE).

`ladder_run.py` exits **1**. `PREREGISTRATION.md` §11 was committed as
`7497c353` before `ladder_build.ps1` existed, and §12 as `81e3843c` before
`bee-L2P` or `bee-L3P` existed.

### 10.1 The design defect, which was mine

`ladder_build.ps1` defaults `-BOffset` to the stride, so the number of frames
between half-A's and half-B's focus planes **fell monotonically as `N` rose**:
9, 5, 3, 1. `R` rising across that ladder is exactly what a falling offset
alone would produce.

`bee-L1P` prices it at **constant `N` = 34**, with half-A **bit-identical**
between the two rungs (sha16 `7600B160797D4446`):

| rung | N | offset | R (COARSE/DETAIL) |
|---|---:|---:|---:|
| `bee-L1` | 34 | 9 | 2.316 |
| `bee-L1P` | 34 | 1 | **14.364** |

**6.20×, from a parameter that is not `N`** — larger than the whole L1→L4 range
of 5.32×. The mechanism is measured, not assumed: `phi_enfuse` collapses
**23.8×** (0.22286 → 0.00936) against only 3.8× in strehl. At offset 9 the two
halves are different **scenes**, and `enfuse`, which blends by local contrast,
reproduces that depth difference faithfully.

Holding the offset at 1 lowers the baseline half-disagreement at **every** `N`
where it could be tested — three for three:

| N | offset | baseline `phi` COARSE |
|---:|---:|---|
| 34 | 9 → 1 | 0.51612 → 0.13441 |
| 60 | 5 → 1 | 0.18374 → 0.14678 |
| 100 | 3 → 1 | 0.95322 → **0.05503** |

At `N` = 100 that is a **17× drop in baseline `phi`** from changing nothing but
the split, and it removes the ladder's wildest number: `R` 95.404 → 16.770.

### 10.2 The corrected ladder

Offset held at 1 frame on every rung, so only `N` varies. COARSE/DETAIL:

| rung | N | R | 95% CI | R FLAT | readable? |
|---|---:|---:|---|---:|---|
| `bee-L1P` | 34 | 14.364 | [12.081, 18.282] | 0.674 | **no** — COARSE/BLOTCH |
| `bee-L2P` | 60 | 26.883 | [18.334, 45.065] | 0.894 | **no** — COARSE/BLOTCH |
| `bee-L3P` | 100 | 16.770 | [12.021, 21.417] | 0.560 | yes |
| `bee-L4` | 299 | 12.313 | [8.638, 15.071] | 0.460 | yes |

Two of four rungs readable and the low endpoint excluded, so **NO BRANCH**.
FINE is worse: **zero** of four readable.

**A pre-registered prediction was violated and I am not rounding it away.**
§12.3 predicted the interior rungs would land between 12.3 and 14.4. `bee-L3P`
reads 16.770, 17% above that interval; **`bee-L2P` reads 26.883, 87% above
it.** The separately pre-registered falsifier — an interior rung departing
from *both* endpoints by more than 3× — was **not** crossed (1.87× and 2.18×).
So H3 is not declared insufficient, but its interval was wrong, and `R` at
constant offset is **non-monotone in `N`**.

### 10.3 The decisive finding — the instrument is uncommissioned across most of the ladder

`blotchsweep.py`. The **BLOTCH** arm plants the very mechanism `R` claims to
detect: each half blends a blurred copy under its **own** coarse random mask,
so the halves disagree over 20–60 px patches. `incoh.py` commissions it at a
**fixed** `BETA` = 0.020, while §9.6 had already established that a fixed plant
amplitude is wrong and derived it per band for the **NOISE-INC** arm. The same
defect was fixed on one arm and not the other; the ladder is the first thing
that moved the baseline far enough to expose it.

Sweeping the plant amplitude over **160×** (0.02 → 3.20) separates *too weak*
from *cannot respond*. COARSE, response at the committed amplitude, ordered by
baseline `phi`:

| key | baseline `phi` | d_phi at beta 0.02 | best over the whole sweep | |
|---|---:|---:|---:|---|
| `119` | 0.00357 | **+95.5%** | +124.2% | PASSES |
| `bee-L4` | 0.00997 | **+91.3%** | +114.3% | PASSES |
| `bee-L3P` | 0.05503 | +10.2% | +14.3% | PASSES |
| `bee-L1P` | 0.13441 | −3.3% | −1.8% | **CEILING** |
| `bee-L2P` | 0.14678 | +0.3% | +0.3% | **CEILING** |
| `bee-L2` | 0.18374 | +1.7% | +4.9% | **CEILING** |
| `bee-L1` | 0.51612 | −4.5% | −4.0% | **CEILING** |
| `bee-L3` | 0.95322 | −6.1% | −6.1% | **CEILING** |

**The failure is a ceiling, not a potency.** On five of eight COARSE cells the
plant cannot move `phi` by 5% **at any amplitude**, and on three of them it
moves `phi` the **wrong way** — planting selection disagreement makes the
statistic read *less* selection disagreement. FINE behaves the same way:
`119` +92.2% and `bee-L4` +34.5% pass, while `bee-L2`, `bee-L2P` and `bee-L3`
sit at +0.6%, +0.7% and +0.6% against baselines of 0.99.

**Within each band the response falls monotonically as the baseline `phi`
rises**, across nine keys. The gate is crossed between `phi` 0.055 and 0.134 in
COARSE and between 0.597 and 0.988 in FINE. That is a **sensitivity envelope
for §9's statistic, measured rather than assumed**: `R` is only commissioned
where the halves already agree well.

Which is fatal for *this* ladder specifically, because the ladder's whole
purpose is to walk the baseline disagreement up and down. **A statistic that is
only commissioned at one end of the axis cannot measure a trend along it.**

**Commissioning of the sweep itself.** A sweep that always found a response
would prove nothing. `bee-L4`/COARSE is the cell where the committed BLOTCH arm
**passed**; the sweep reproduces **+91.3%** there at the committed amplitude,
clearing the same gate. It is reading what the harness read, and
`blotchsweep.py` exits non-zero if it is not.

### 10.4 Two rival explanations, tested and rejected as drivers

- **H1, misregistration between halves.** The mechanism is **real**:
  `incoh.pairs` is called with `placer=None` for the half comparison, so it
  crops the same `(y, x)` from both halves and never registers A to B — a
  displacement lands straight in `d`. But it **predicts the wrong direction**
  on the controlled pair: `bee-L1P` has **twice** the A–B shift (8 px vs 4 px)
  and **3.8× lower** `phi`. Rejected as the driver, retained as a caveat.
- **H2, `phi` saturation.** Real and disqualifying **where it occurs** — it is
  why `bee-L3` COARSE (0.953) and most of FINE are excluded — but it does not
  explain the controlled pair, neither of whose COARSE arms is near 1.

### 10.5 Controls that came back clean

- **Two pins produce bit-identical decoded pixels.** `pincheck.py`:
  32,966,016 of 32,966,016 pixels identical on both strehl-A and strehl-B for
  `740e7056` against `9b05d0b7`. §9's reading and the ladder sit on one binary.
  Compared as **decoded arrays**, per ORCH; the file hashes happened to agree
  too and are reported as the weaker check.
- **strehl raster drift across rungs** never exceeds **12 px** with peak
  0.96–0.97, and is identical within each L*/L*P pair, as it must be — the two
  rungs of a pair share half-A bit-identically, so the geometry fitted on the A
  rasters is identical by construction. The fitter returned bit-identical
  results on bit-identical inputs.
- **Placer window sensitivity** is **−4.9% to +2.0%** across all seven rungs
  and both bands, so widening `incoh`'s ±32 px search is not what produced any
  number. Both windows are run and both are printed. The largest excursion is
  `bee-L2P`/FINE at −4.9%, and that rung is excluded on other grounds anyway.

### 10.6 What this licenses and what it does not

**MEASURED:** at constant `N` = 34 with half-A bit-identical, a nuisance
parameter moves `R` by 6.20×. Holding the offset lowers the baseline `phi` at
all three testable `N`. The BLOTCH arm cannot be made to respond at any
potency on five of eight COARSE cells and three of five readable FINE cells.
`119` passes both bands with the largest margins measured.

**NOT MEASURED, and specifically refused:** any statement of the form "`R`
rises with `N`" or "`R` is flat in `N`". **ORCH's dilution mechanism is neither
corroborated nor wounded by this lane.** The run that would have corroborated
it produced a number in the predicted direction, and I am discarding it because
my own controls say it is not a reading of `N`.

**What this qualifies about §9:** nothing on `119`, which is cleared by direct
measurement rather than by pointing at the earlier pass. What it adds is the
**envelope**: `R` should not be quoted on any pair whose baseline `phi` exceeds
roughly 0.05 in COARSE, and any future use of `incoh.py` on a new subject must
run the BLOTCH arm and read it before quoting `R`. §9's `bee` FLAT control
already failed at **every** rung (0.460–1.252 against a required [0.80, 1.25]),
so §9's key discriminator is **subject-specific** and does not transfer to
`bee`.

**A cheap repair exists and is not applied here.** `mut_blotch`'s amplitude
should be derived per band and per baseline exactly as `plant_beta` derives
`NOISE-INC`'s. That would fix the *amplitude*, but the sweep shows the failure
is a **ceiling**, so it would not by itself recommission the low rungs;
detecting selection disagreement against a large baseline needs a different
plant, not a bigger one. `incoh.py` is left untouched because §9 depends on it.
