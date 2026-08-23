# M40 -- Verification of `SELECTION_INFLATION` (commit `253e56f`)

Status: complete. Independent verification, method = AGENTS.md rule 24 (re-choose, do not
re-compute). Author of the change under review: the orchestrator. Author of this document:
the M40 verifier. Nothing in `crates/` was modified; see §7 for why.

Every claim below is labelled **MEASURED**, **DERIVED** or **ARGUED**. Numbers without a
label are not evidence and none appear.

Scripts and raw output: `experiments/m40-verify-341/src/0{1..7}-*.py`,
`experiments/m40-verify-341/out/`.

**Provenance of the two binaries in §5.** `crates/` at `edb1c06` is byte-identical to
`crates/` at `253e56f` (`git diff --name-only 253e56f edb1c06 -- crates/` is empty), so the
release binary built from the working tree and the one built from a detached worktree at
`253e56f~1` differ in `crates/` **only** by the reviewed commit. Three further commits
(`1e4f0bf`, `694e49f`, `8e9d5e5`) landed in `crates/` after those binaries were built; they
touch M18/M21 occlusion reporting and a doc comment, and none of them reach
`predicted_sigma`, `confidence`, `do_not_trust_mask` or `upper_tail_cut`.

---

## 1. The one-paragraph verdict

**The repair does not stand.** The arithmetic reproduces exactly -- 1.0739x on the
author's ROI with the author's estimator, to four decimals (MEASURED, script 01) -- and,
as in the four prior verifications, that is precisely the wrong place to look. The defect
is the choice. `SELECTION_INFLATION = 1.074` is read off `flat_roi_stats`, which is a
ratio of two **spatial** standard deviations, and is then multiplied into
`predicted_sigma`, which is a **temporal** per-sample sigma. Those are different
quantities, and the numerator and denominator of the ratio are 53%, 51%, 90% and 86%
**scene structure** by variance on the four flat ROIs measured (MEASURED, script 06). The
denominator is one arbitrarily chosen frame -- `frames.len()/2`, position in a file list --
and holding the merge fixed while sweeping which frame sits in that denominator moves the
"constant" from 1.0245x to 1.3252x on 109MSDCF and from 1.0000x to 1.5989x on 119MSDCF
(MEASURED, script 06). Against the frames the argmax actually elects it reads 1.0289x --
1.0565x, not 1.074x. Meanwhile a pure-noise plant, which by construction has the *maximal*
winner's curse because no focus signal exists to compete with noise, caps the true
inflation at **1.0451x** in the pixel domain and **1.0307x** in the gradient domain
(MEASURED, script 03): **1.074 is larger than the most the shipped operator can produce.**
The worst defect, though, is not the value. It is that the whole thing repairs a symptom
that was never a noise symptom: on the flat ROI, the merge's modal winner (frame 9, 52.1%
of pixels) carries **1.2670x** the corrected detail of the reference frame 11 all by
itself, unmerged and unselected (MEASURED, script 04). Fact 341's "+35.47% detail on a flat
ROI where no detail can exist" is mostly the reference frame being out of focus. A noise
constant was fitted to a focus effect, and it happens to cancel it on one ROI of one stack;
on 119MSDCF's `3056,416` the same constant leaves the flat ROI reading **+31.5%** detail at
gate 0 (MEASURED, script 04).

---

## 2. Facts 428-431, ruled

| # | The claim as filed | Ruling | Author's number | Mine |
| --- | --- | --- | --- | --- |
| 428 | Pricing selection in moves corrected gate-0 detail on the flat ROI from +35.47% to 0.885x, flat-ROI noise column unchanged. | **QUALIFIED -> REFUTED as a repair** | 0.885x | 0.8854x (MEASURED, script 04) -- reproduces. But 0.9122x on the neighbouring flat ROI, 1.0347x and **1.3147x** on 119MSDCF's two flat ROIs (MEASURED, script 04). The spurious credit is removed on one ROI of one stack and survives at +31.5% on another. |
| 429 | `the_merged_estimate_is_never_noisier_than_a_single_frame` had no power to fail. | **CONFIRMED, and stronger than claimed** | -- | The test was a double tautology (DERIVED from source, §6.5). Not "blind where the invariant could be violated" -- blind everywhere, for every input, every noise model. |
| 430 | The corrected reading over-shoots to -11.5%; the ROI is low-detail, not detail-free, so the size of the over-shoot is unresolved. | **REFUTED as framed** | -11.5% | -11.46% reproduces (MEASURED, script 04). But the framing is wrong twice: the ROI is not low-detail, it is *focus-sensitive* (corrected detail runs 5.31 -> 18.66 DN across the sweep, a 3.5x span, MEASURED script 04), and on a genuinely detail-free plant the corrected value at I=1.074 reads **-11.63 DN and -9.24 DN**, i.e. negative where truth is zero (MEASURED, script 03). The over-shoot is not ROI ambiguity. The constant is roughly twice too large. |
| 431 | The `n >= 2` penalty is unmeasured, so 1.0 is used and `predicted_sigma` is a floor there. | **REFUTED** | 1.0 (unmeasured) | It is measurable and it is not 1.0. On the plant at gate 1.0: I_pix(n) = 1.0770, 1.0591, 1.0454, 1.0383, 1.0319, 1.0293, 1.0286, 1.0220 for n = 1..8 (MEASURED, script 03). Smooth decay, not a step. |

Two further defects found that facts 428-431 do not mention:

| Finding | Ruling |
| --- | --- |
| The change enumerates three consumers of `predicted_sigma`. There is a **fourth**: `merge_cmd.rs:912` prints a column headed `pred sigma gain 1/sqrt(n)` computed as `1.0/mean_n_eff().sqrt()`, never calling `predicted_sigma`. After the repair the code asserts gate-0 predicted sigma is 1.074x single-frame while the tool's own report prints 1.0000x for the same quantity. Byte-identical in both binaries (MEASURED, script 05/07). | **NEW DEFECT** |
| That same column is not a mean. `1/sqrt(mean n)` understates the merge's noise by 4.2%-5.9% at gates 0.5-2.0 relative to `mean(1/sqrt(n))` (MEASURED, script 07). It reports a *better* gain than the merge achieves. | **NEW DEFECT (pre-existing)** |

---

## 3. Choice point 1 -- the constant's value

### 3.1 What each cited number actually measures

| Fact | Value | What it is |
| --- | --- | --- |
| 19 | 1.253x | Retired **ring** operator, per-pixel argmax, spatial-sd ratio vs middle frame. Different operator. |
| 71 | 1.068x | Shipped **Tenengrad**, same spatial-sd ratio. |
| 23 / 321 | 1.075x | M2-era shipped operator, same spatial-sd ratio. |
| 320 | 1.074x | Gate 0 on 109MSDCF `2272,1344`, same spatial-sd ratio. |

All four are the **same estimator** applied to different operators/dates, and none of them
is a per-sample temporal sigma. `flat_roi_stats` (`crates/strehl-cli/src/stack.rs:653`) is
`spatial_sd(merged over ROI) / spatial_sd(middle frame over ROI)`. The shipped banner in
`report_flat_roi` says so itself. Multiplying a temporal sigma by a spatial ratio is the
comparison AGENTS.md rule 10 forbids. **DERIVED from source.**

### 3.2 The different setting I chose: structure-free temporal estimators, and a
### reference sweep

Four estimators, four arms (true / shift(37,53) / shuffle / fixed-frame), six ROIs, two
stacks (script 01). E1 is the author's. E2 and E4 are temporal: they compare the merged
value at a pixel against the same pixel's own across-frame dispersion, so scene structure
cancels.

| ROI | E1 (author's) | E1 fixed-frame arm | E2 pix | E2 changed-px | E4 grad | E4 changed-px |
| --- | --- | --- | --- | --- | --- | --- |
| 109 flat-M2 `2272,1344` | **1.0739x** | 1.0407x | 1.0191x | 1.0384x | 1.0124x | 1.0269x |
| 109 flat-M11 `2352,1408` | 1.0867x | 1.0505x | 1.0117x | 1.0239x | 1.0118x | 1.0248x |
| 109 detail-M11 `2080,1056` | 1.0001x | -- | 1.1845x | -- | 1.0184x | -- |
| 119 flat-M11 `2896,1968` | 1.0601x | 1.0137x | 1.0150x | 1.0221x | 1.0186x | 1.0241x |
| 119 flat-M11 `3056,416` | **1.2732x** | **1.2731x** | 1.0140x | 1.0244x | 1.0138x | 1.0233x |
| 119 detail-M11 `2016,1152` | 0.9841x | -- | 1.0382x | -- | 1.0337x | -- |

All MEASURED (scripts 01, 02).

Three things follow.

**(a) The author's estimator is not measuring selection.** Its **fixed-frame arm** takes
the same winner map and reads the same ROI from ONE frame -- no selection at all -- and on
119MSDCF `3056,416` that arm returns **1.2731x** against the true arm's 1.2732x. The
selection content of E1 there is 0.0001. On 109 flat-M2 the fixed-frame arm carries 1.0407
of the 1.0739. **MEASURED.** So most of the "inflation" is "a different frame simply has a
different spatial sd".

**(b) It is not a constant.** E1 spans 1.0001x to 1.2732x over six ROIs on two stacks, and
goes *below* 1 on one detail ROI. If the constant should differ per stack, the brief says,
that kills the constant. It differs per **ROI within** a stack, by 20 percentage points.

**(c) The reference is doing the work.** Script 06 holds the merge fixed and sweeps which
frame occupies the denominator:

| ROI | vs shipped middle | vs modal winner | vs winner-weighted | min..max over all N references |
| --- | --- | --- | --- | --- |
| 109 flat-M2 `2272,1344` | 1.0739x | 1.0319x | 1.0289x | 1.0245x .. 1.3252x |
| 109 flat-M11 `2352,1408` | 1.0867x | 1.0344x | 1.0395x | 1.0344x .. 1.3279x |
| 119 flat-M11 `2896,1968` | 1.0601x | 1.0458x | 1.0565x | 1.0458x .. 1.5125x |
| 119 flat-M11 `3056,416` | 1.2732x | **1.0000x** | 1.0060x | 1.0000x .. 1.5989x |

MEASURED. The rule-20 falsifier was pre-registered in the script: *a noise fact must be
roughly invariant to which frame is in the denominator, because every frame carries the
same read noise and, at these levels, nearly the same shot noise; a flat line refutes me.*
The line is not flat. It tracks the reference frame's sharpness monotonically, and against
the frames the argmax actually elects it collapses to 1.000x-1.057x.

### 3.3 The ceiling: what the operator can even produce

Script 03 builds a **pure-noise plant** at each ROI's own mean level with sigma from the
calibrated model, and pushes it through the shipped focus operator, regulariser, gate and
merge. It has no focus signal at all, so the argmax is 100% noise-driven: this is the
**maximal** winner's curse and therefore an upper bound (rule 13 -- it is a simulation, and
it is used only as a bound).

| quantity | 109-like (L=2021, ISO 160, N=22) | 119-like (L=4477, ISO 50, N=33) |
| --- | --- | --- |
| control: one frame, no selection, pixel domain | 1.0001x | -- |
| control: one frame, no selection, gradient domain | 0.99942 +/- 0.00332 | -- |
| gate 0, pixel domain (C1's quantity) | **1.0451x** | **1.0508x** |
| gate 0, gradient domain (the detail metric's quantity) | **1.03069x** | **1.03447x** |

MEASURED, 10 seeds. **1.074 exceeds the pixel-domain ceiling by 2.8 percentage points and
the gradient-domain ceiling by 4.3.** Real-data structure-free estimates (1.012-1.038) sit
*below* the bound, which is the consistency check that says the bound is doing its job.

**Ruling on choice point 1: the constant is wrong in value, wrong in units, and is not a
constant.** If a single scalar must ship, the defensible value for the detail metric is
**~1.031** (gradient domain, plant ceiling) or **~1.027** (gradient domain, real data,
changed-pixels-only), and for C1 **~1.045** / **~1.038**. Not one number: two.

---

## 4. Choice point 2 -- the n-dependence

The different setting: measure the inflation **as a function of n** instead of assuming a
step. Script 03 stratifies the plant's merge by each pixel's realised acceptance-set size.

Pixel-domain inflation at gate 1.0, 109-like configuration (MEASURED):

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I_pix(n) | 1.0770 | 1.0591 | 1.0454 | 1.0383 | 1.0319 | 1.0293 | 1.0286 | 1.0220 |

It is a **smooth decay, not a step**. At n = 8 the penalty is still 2.2%, and
`selection_inflation(8)` returns 1.0. Fact 431's "unmeasured, so 1.0" is refuted on both
halves: it is measurable with the tooling already in the repository, and 1.0 is wrong at
every n tested.

Aggregate consequence, same script. The uncorrected model under-predicts merged noise by
4.5%, 4.9%, 4.2% and 1.1% at gates 0.0, 0.5, 1.0 and 2.0 (MEASURED, `I_pix(agg)`). The
repair touches only the n = 1 stratum, which is 100%, 21.7%, 3.3% and 0.0% of pixels at
those gates. So after the repair:

| gate | share of pixels the repair reaches | model vs truth after the repair |
| --- | --- | --- |
| 0.00 | 100.0% | **over**-predicts by 2.8 pp (1.074 asserted, 1.0451 measured) |
| 0.50 | 21.7% | roughly 1.0 pp too low on aggregate |
| 1.00 | 3.3% | still **under**-predicts by ~4.1 pp -- essentially unrepaired |
| 2.00 | 0.0% | still under-predicts by 1.1 pp -- untouched |

**MEASURED + DERIVED.** The one gate where the repair bites is the gate where it
over-shoots; the gates the tool actually ships at are left as they were.

Two further consequences the step function creates and the smooth curve does not:

- **A discontinuity across half the image.** The CLI reports `n_eff = 1` for **41.66%** of
  the plane at gate 1.00 on 109MSDCF (MEASURED, script 05). The step applies a 7.4% penalty
  to those pixels and 0% to the adjacent 58.34%. There is no physical reason for a
  7.4-point jump between a pixel that admitted one frame and its neighbour that admitted
  two; the measured curve moves 1.0770 -> 1.0591, a 1.8-point step.
- **The gradient and pixel domains need different curves.** Across all four plant gates the
  ratio `(I_grad - 1)/(I_pix - 1)` reads 0.681, 0.693, 0.691, 0.685 (DERIVED from script
  03's MEASURED table) -- remarkably stable at ~0.69. The gradient domain sees roughly
  two-thirds of the pixel-domain excess. One scalar cannot serve C1 and the detail metric.

**Ruling on choice point 2: REFUTED.** `predicted_sigma` is now miscalibrated at every gate
above 0, in the same direction as before, by 1.1-4.5%.

---

## 5. Choice point 3 -- the location of the repair

The different setting: build the **pre-fix binary** (worktree at `253e56f~1`, cargo build
--release) and diff the confidence report against HEAD's binary on 109MSDCF at two gates,
`--stats --stats-placebo`, 5% tail. Raw output: `out/05-conf-109-g{0,1}-I{1000,1074}.txt`.

| channel | gate 0, I=1.000 | gate 0, I=1.074 | gate 1, I=1.000 | gate 1, I=1.074 |
| --- | --- | --- | --- | --- |
| C1 `sigma_cut` | 19.732 DN | **21.193 DN** | 19.569 DN | **21.017 DN** |
| C1 `by_sigma` | 414030 px | 414030 px | 414162 px | 414162 px |
| C2 `by_perplexity` | 412076 | 412076 | 412076 | 412076 |
| C3 `by_deficit` | 412076 | 412076 | 412076 | 412076 |
| C4 `by_flags` | 4610499 | 4610499 | 4610499 | 4610499 |
| UNION | 61.920% | 61.920% | 61.940% | 61.940% |
| UNION w/o C4' | 17.407% | 17.407% | 17.397% | 17.397% |

All MEASURED. `21.193/19.732 = 1.07400` and `21.017/19.569 = 1.07400`.

**Answer to the brief's question: no, the flag rates do not move. Not one pixel changes, at
either gate.** The reason is structural and it is a finding in its own right: C1 is
consumed only through `upper_tail_cut`, a **quantile**, so the mask is invariant to any
monotone transform of `predicted_sigma` that preserves the ordering within the tail. The
exact factor of 1.07400 at gate 1 proves the entire 5% tail is n = 1 pixels in both arms,
so scaling only the n = 1 stratum is a pure rescaling *of the tail*. **DERIVED from
MEASURED.**

The uncomfortable corollary: **the confidence vector has no power over this constant.** It
could not have detected the defect fact 341 names, and it cannot validate the repair. Any
future "C1 confirms the calibration" claim would be a tautology.

What *did* change is a **published number with no measurement behind it**: `sigma_cut` is
reported in DN and is now 7.4% higher, so M34's tabulated cuts are stale while the pixels
they select are identical.

### 5.1 The fact-281 sign question

Question 80 records that three of six reasonable `predicted_sigma` definitions flip fact
281's correlation sign; fact 292 / discipline 206 record that the split is between the
**gated** family (`/sqrt(n)`, lift 0.889 / 0.762 / 0.680) and the **ungated** family (lift
1.118 / 1.125 / 1.111), and fact 291 gives the mechanism -- C1 falls with acceptance-set
size, so its worst-5% is nearly all size-1 pixels.

The new definition is `green_luma_sigma * infl(n) / sqrt(n)`. It is in the **gated**
family, and multiplying the n = 1 stratum by 1.074 makes the worst-5% *more* size-1
dominated, not less. **ARGUED, then MEASURED**: the measurement above shows the tail is
already 100% size-1 at both gates in both arms, so the composition cannot become more
size-1 dominated -- it is saturated. The definition therefore does **not** flip the sign; it
entrenches the existing one and removes the last headroom by which C1's composition could
have moved. That is not the serious finding the brief anticipated, but it is worse in one
respect: it means the anti-correlation of fact 281 is now structurally locked in.

### 5.2 The fourth consumer

`crates/strehl-cli/src/merge_cmd.rs:912` prints

```
  gate   tol(DN-norm)     mean n_eff   n_eff=1 %   boundary %   pred sigma gain 1/sqrt(n)
```

with the value `1.0 / mean.sqrt()`. It never calls `predicted_sigma`. Both binaries print
the identical line, including **`1.0000x` at gate 0** -- the exact number fact 341 filed as
the defect. **MEASURED, script 05.** The repair did not reach the column that displays the
claim it repairs.

Separately, that column is not the mean gain. Script 07, 109MSDCF flat ROI `2272,1344`
(MEASURED):

| gate | mean n | n=1 % | `1/sqrt(mean n)` (shipped column) | `mean(1/sqrt(n))` | `mean(infl(n)/sqrt(n))` | column error |
| --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1.0000 | 100.00% | 1.0000x | 1.0000x | **1.0740x** | +0.00% |
| 0.50 | 1.2995 | 72.22% | 0.8772x | 0.9159x | 0.9693x | **-4.22%** |
| 1.00 | 1.6700 | 43.96% | 0.7738x | 0.8222x | 0.8547x | **-5.88%** |
| 2.00 | 2.4908 | 8.80% | 0.6336x | 0.6648x | 0.6714x | **-4.70%** |
| 4.00 | 4.5354 | 0.00% | 0.4696x | 0.4812x | 0.4812x | **-2.43%** |

`1/sqrt(.)` is convex, so `mean(1/sqrt(n)) >= 1/sqrt(mean n)` with equality only for
constant n (DERIVED, Jensen). The column reports a better noise gain than the merge
achieves, by up to 5.9 percentage points, and the gap is largest exactly where the tool is
meant to be calibrated.

**Ruling on choice point 3: the location is defensible for what it changes and indefensible
for what it misses.** Three consumers were enumerated; a fourth exists, it is the reporting
surface, and it is untouched and independently wrong.

---

## 6. Choice point 4 -- the -11.5% residual, against a real null

The different setting: **build a genuinely detail-free reference** rather than argue about
whether a low-detail ROI should read 1.0x. Script 03's plant is a flat plane at the ROI's
mean level with noise drawn from `strehl_core`'s calibrated model -- zero detail by
construction -- pushed through the shipped operator, regulariser, gate and merge, 10 seeds.

The retention *ratio* is undefined on a true null (0/0), so the meaningful reading is the
**absolute corrected value**, whose truth is 0 DN:

| gate | mean n | n=1 % | `corrected` at I=1.000 | `corrected` at I=1.074 |
| --- | --- | --- | --- | --- |
| 0.00 | 1.000 / 1.000 | 100% | +9.60 / +8.47 DN | **-11.63 / -9.24 DN** |
| 0.50 | 3.21 / 3.50 | 21.7 / 20.4% | 6.91 / 5.82 | -0.25 / +0.86 |
| 1.00 | 7.36 / 8.84 | 3.3 / 2.6% | 4.19 / 3.32 | 3.14 / 2.63 |
| 2.00 | 17.45 / 24.35 | 0% | 1.16 / 0.85 | 1.13 / 0.85 |
| 4.00 | 21.98 / 32.97 | 0% | 0.34 / 0.19 | 0.04 / 0.04 |

MEASURED. Truth is 0.00 in every cell. At I = 1.000 the metric credits +9.60 DN of detail
to a region that has none; at I = 1.074 it credits **-11.63 DN**, which the shipped
`max(0, .)` clamps to 0 and thereby hides. **The correction is not merely an over-shoot; it
crosses zero and lands further from truth in absolute value than the defect it replaced.**

### 6.1 And the reference was the real problem

Script 04 measures the corrected detail of **every individual frame** on the flat ROI. On
109MSDCF `2272,1344` (MEASURED, DN):

```
5.31 7.13 6.89 7.78 6.92 7.63 10.93 14.87 17.11 18.66 18.58 14.73 13.57 11.60 8.19 7.49
7.71 6.14 7.82 5.71 6.64 6.83
```

- The shipped reference, frame 11, reads **14.7270 DN** and is the **5th sharpest of 22**.
- The merge's modal winner, frame 9 (52.1% of pixels), reads **18.6595 DN = 1.2670x** the
  reference, **unmerged, unselected, with no noise story at all**.
- Retention at gate 0 with no inflation is 1.3547x. `1.3547 / 1.2670 = 1.069` (DERIVED):
  after pricing in the reference's defocus, essentially nothing is left for selection noise
  to explain, and what is left is within the plant's 1.031 gradient-domain ceiling.

So the ROI is not "low-detail". It is **focus-sensitive**: its corrected detail spans 3.5x
across the sweep. Rule 9's flat-ROI control was chosen for low *spatial contrast*, which is
a different property, and the detail metric legitimately reports a gain there. **Fact 341's
premise -- "a FLAT ROI, where no detail can exist" -- is false, and facts 428 and 430
inherit the error.**

The same measurement on all four flat ROIs (MEASURED, script 04):

| ROI | reference rank | best/middle | ret @ I=1.000 | ret @ I=1.074 | I* making ret = 1.000 |
| --- | --- | --- | --- | --- | --- |
| 109 `2272,1344` | 5 / 22 | 1.2670x | 1.3547x | 0.8854x | 1.0592x |
| 109 `2352,1408` | 4 / 22 | 1.2808x | 1.3742x | 0.9122x | 1.0626x |
| 119 `2896,1968` | 4 / 33 | 1.0544x | 1.0649x | 1.0347x | 1.1506x |
| 119 `3056,416` | **17 / 33** | 1.3430x | 1.3556x | **1.3147x** | **1.4751x** |

The constant needed to zero the flat-ROI credit ranges **1.0592x to 1.4751x**. It tracks
`best/middle`, not noise. On 119MSDCF `3056,416` the shipped 1.074 removes 4 of 35.6
percentage points and the "repaired" tool still reports +31.5% detail on a control ROI.

### 6.2 A circular inversion, reported and rejected (rule 15)

Script 06 also prints a column "with the merge's OWN implied structure -> implied noise
inflation", reading 1.0002x, 1.0006x, 0.9986x, 0.9945x. **That column is circular** and I
am reporting it only because rule 15 forbids deleting it after the fact: implied structure
is defined as `sqrt(sd_merged^2 - sigma_model_merged^2)`, so the inversion reduces
algebraically to `sigma_model(merged level) / sigma_model(reference level)`, which is ~1 by
construction. It is not evidence. The non-circular sibling column ("if structure were
IDENTICAL") gives 1.1525x, 1.1698x, 1.4946x, 2.3401x -- which is itself a demonstration
that the quantity is not a constant, since the four readings disagree by a factor of two.

**Ruling on choice point 4: 1.0x was never the right expectation, and neither is -11.5% an
over-shoot of unknown size.** Against a true null the corrected metric reads +9.60 DN
uncorrected and -11.63 DN corrected, both wrong, the second by more.

---

## 7. Choice point 5 -- was the old invariant really wrong?

The old test (`253e56f~1`, `crates/strehl-core/src/merge.rs`):

```rust
let merged = est.predicted_sigma(&noise, i, 0.0);
let single = noise.green_luma_sigma(est.green_mean(i));
assert!(merged <= single + 1e-6, ...);
assert!((merged * (n as f32).sqrt() - single).abs() < 1e-4);
```

With `black_dn = 0.0`, the pre-fix `predicted_sigma` is exactly
`noise.green_luma_sigma(green_mean(i)) / sqrt(n)` -- **the same expression as `single`,
divided by `sqrt(n)`**. Since `n >= 1` is asserted two lines above and sigma is
non-negative, `merged <= single` holds identically, for every input, every focus field,
every noise model, every threshold. The second assertion is the algebraic identity
`(single/sqrt(n)) * sqrt(n) == single` up to f32 rounding. **DERIVED from source; the
author's claim is CONFIRMED and is in fact understated.** It was not blind "in exactly the
place the invariant could be violated"; it was blind everywhere. No input could have failed
it.

### 7.1 The harder question: is n=1 a merge configuration at all?

The brief asks whether the right conclusion is "the invariant is false at n = 1" or "gate 0
should never have been reported as a merge configuration". The second reading would make
the two-branch test an entrenchment of a bad framing.

**MEASURED (script 05, whole plane, 109MSDCF):** at gate **1.00** -- a working gate, not a
diagnostic -- `n_eff = 1` for **41.66%** of the plane, with mean n_eff 1.884. On the plant,
n = 1 pixels are 21.7% at gate 0.5 and 3.3% at gate 1.0 (MEASURED, script 03).

So n = 1 is not an artefact of gate 0. It is **the modal configuration at the gate the tool
actually ships**. The two-branch framing is therefore the right one and the author's
conclusion survives here: quarantining gate 0 would leave 41.66% of pixels at the working
gate governed by an invariant that is false for them.

**Ruling on choice point 5: CONFIRMED on both halves.** This is the one part of the change
that stands. The new test's *content* is still wrong, because its n = 1 branch asserts a
constant that §3 refutes -- but its *shape* is right.

### 7.2 Why I did not edit `crates/`

The brief permits edits only with a failing test committed alongside. The two new defects
in §5.2 live in an `eprintln!` inside `report()` in `strehl-cli`, which has no seam a unit
test can reach without extracting a helper -- and extracting that helper *is* the fix, which
is the orchestrator's call, not the verifier's. `cargo test --release -p strehl-core` at
HEAD: **94 passed, 0 failed** (MEASURED). The tree is left untouched.

---

## 8. What would change my verdict

| Ruling | The input that would flip it |
| --- | --- |
| Constant is wrong in value (§3) | A structure-free temporal estimator that reads >= 1.07 on any ROI. Mine read 1.012-1.038 on four flat ROIs across two stacks, in two arms each. One such reading would mean my estimators are the biased ones. |
| Constant exceeds the operator's ceiling (§3.3) | A plant configuration in which the shipped operator produces I_pix > 1.074. The plant has *no* focus signal, so I believe it maximal -- but if fixed-pattern noise, dark current or PRNU (none of which the plant models) contributes correlated across-frame structure, the real ceiling could exceed the synthetic one. That is the single most likely way I am wrong. |
| Reference is doing the work (§3.2, §6.1) | A flat-ROI ratio that is invariant to the choice of reference frame. Sweeping the reference moved it 1.0245x-1.5989x; a spread under ~1% would refute me outright. |
| n >= 2 penalty is not 1.0 (§4) | A per-n stratification on *real* data showing I(n) -> 1.0 by n = 2. The plant says otherwise, and the plant is an upper bound, so real data could plausibly sit lower -- but it would have to sit at exactly 1.000, not merely lower. |
| Flag rates unchanged (§5) | A confidence tail deep enough for the 95th-percentile pixel to be n >= 2. At a 5% tail on 109MSDCF the tail is entirely n = 1 in both arms. A 40-50% tail would mix strata and the mask would move. **I did not measure that** (§9). |
| Metric crosses zero on a true null (§6) | A plant whose noise model differs from the merge's assumed model. Mine draws from the same `sigma_luma`, which is the fair null but also the friendly one; M39 §2.3 records a +/-2 pp sensitivity of the corrected metric to noise-model scale, and -11.63 DN is far outside that. |
| Old test was a tautology (§7) | Nothing. It is algebra, not measurement. |

---

## 9. What I could not measure

- **Whether the flag rates move at a wider confidence tail.** §5 measures only the shipped
  5% tail, where the tail is entirely n = 1 and the mask is provably invariant. A 25-50%
  tail crosses into mixed-n territory and might reorder. Two more binary runs would settle
  it; I ran out of budget.
- **The inflation on real data as a function of n.** §4's curve is the plant's. Stratifying
  a real merge by n confounds n with scene content -- pixels that admit many frames are
  pixels where the focus curve is flat, i.e. low-detail regions -- so the naive real-data
  stratification is not a measurement of selection bias and I did not report one.
- **Fixed-pattern noise.** Neither the plant nor `predicted_sigma` models PRNU, dark
  current or the orientation-dependent FPN that M16 is currently measuring. The shipped
  doc-comment already calls `predicted_sigma` a floor for this reason. If FPN is material
  the ceiling in §3.3 is not a ceiling.
- **The other three stacks.** Facts 320-322 and 71 were measured on stacks I did not open.
  Everything here is 109MSDCF and 119MSDCF.
- **Fact 19's 1.253x.** M39 §5.10 could not reproduce it and neither could I; the ring
  operator it was measured on is retired. It is cited in the shipped banner as a live
  comparison and should not be.

---

## 10. Proposed SYNTHESIS changes

Facts 440-459 are reserved for M40. Disciplines and questions are proposed **without
numbers** (§5 and §10 have collided twice). Nothing is renumbered.

### New facts

| # | Fact |
| --- | --- |
| 440 | `flat_roi_stats` is a ratio of two SPATIAL standard deviations against ONE reference frame (`frames.len()/2`); `predicted_sigma` is a TEMPORAL per-sample sigma. `SELECTION_INFLATION` multiplies the second by the first. MEASURED from source, M40 §3.1. |
| 441 | Sweeping which frame occupies the denominator of the flat-ROI ratio, merge held fixed, moves it 1.0245x-1.3252x on 109MSDCF `2272,1344` and 1.0000x-1.5989x on 119MSDCF `3056,416`. Against the frames the argmax elects it reads 1.0289x-1.0565x. MEASURED, M40 §3.2. |
| 442 | The reference frames of the four flat ROIs are 53.3%, 50.9%, 90.0% and 86.1% scene STRUCTURE by variance (spatial sd vs model sigma at the same level). The flat-ROI ratio is a ratio of two structure-dominated quantities. MEASURED, M40 §3.2. |
| 443 | The author's own estimator, applied unchanged to six ROIs on two stacks, reads 1.0001x, 1.0739x, 1.0867x, 0.9841x, 1.0601x and 1.2732x. It is not a constant. MEASURED, M40 §3.2. |
| 444 | On 119MSDCF `3056,416` the estimator's FIXED-FRAME arm -- same winner map, one frame, no selection -- reads 1.2731x against the true arm's 1.2732x. The selection content of that reading is 0.0001. MEASURED, M40 §3.2. |
| 445 | Structure-free temporal estimators (shift control, changed-pixels-only) put the per-pixel selection inflation at 1.012x-1.038x (pixel domain) and 1.012x-1.034x (gradient domain) on four flat ROIs across two stacks. MEASURED, M40 §3.2. |
| 446 | On a pure-noise plant at the ROIs' own levels -- no focus signal, hence maximal winner's curse -- the shipped operator's gate-0 inflation is 1.0451x/1.0508x (pixel) and 1.0307x/1.0345x (gradient), against controls of 1.0001x and 0.9994x. `SELECTION_INFLATION = 1.074` exceeds this upper bound. MEASURED, M40 §3.3. |
| 447 | The gradient-domain inflation is a stable fraction of the pixel-domain one: `(I_grad-1)/(I_pix-1)` = 0.681, 0.693, 0.691, 0.685 across four plant gates. C1 and the detail metric need different constants. DERIVED from MEASURED, M40 §4. |
| 448 | Plant inflation by acceptance-set size at gate 1.0: 1.0770, 1.0591, 1.0454, 1.0383, 1.0319, 1.0293, 1.0286, 1.0220 for n = 1..8. Smooth decay, not a step; `selection_inflation(n>=2) = 1.0` is wrong at every n tested. MEASURED, M40 §4. Supersedes fact 431. |
| 449 | The repair reaches only the n = 1 stratum, which is 100%, 21.7%, 3.3% and 0.0% of plant pixels at gates 0.0, 0.5, 1.0, 2.0. At gate 0 it now OVER-predicts by 2.8 pp (1.074 asserted vs 1.0451 measured); at gates 1.0 and 2.0 the model still under-predicts by 4.1 and 1.1 pp, essentially unrepaired. MEASURED, M40 §4. |
| 450 | Inflating C1 changes NO flagged pixel. `sigma_cut` moves 19.732->21.193 DN (gate 0) and 19.569->21.017 DN (gate 1), both exactly 1.07400x; `by_sigma`, `by_perplexity`, `by_deficit`, `by_flags` and both UNION figures are identical in both binaries. C1 is consumed only through a quantile, so the mask is invariant to any order-preserving transform of `predicted_sigma`. MEASURED, M40 §5. |
| 451 | The exact 1.07400x factor at gate 1 proves the whole 5% C1 tail is n = 1 pixels in both arms. The new definition is in the GATED family of question 80 and cannot flip fact 281's sign; it saturates the composition instead. MEASURED + DERIVED, M40 §5.1. |
| 452 | There is a FOURTH consumer. `merge_cmd.rs:912` prints `pred sigma gain 1/sqrt(n)` as `1.0/mean_n_eff().sqrt()`, never calling `predicted_sigma`, and still reads 1.0000x at gate 0 in both binaries -- the exact number fact 341 filed as the defect. MEASURED, M40 §5.2. |
| 453 | That column is not the mean gain. `1/sqrt(mean n)` understates `mean(1/sqrt(n))` by 4.22%, 5.88%, 4.70% and 2.43% at gates 0.5, 1.0, 2.0 and 4.0 (Jensen; equality only for constant n). It reports a better noise gain than the merge achieves. MEASURED, M40 §5.2. |
| 454 | On a genuinely detail-free plant the corrected detail metric reads +9.60/+8.47 DN at I=1.000 and **-11.63/-9.24 DN** at I=1.074, where truth is 0. The correction crosses zero and lands further from truth than the defect it replaced; the shipped `max(0,.)` hides it. MEASURED, M40 §6. |
| 455 | The flat ROI `2272,1344` is not detail-free. Per-frame corrected detail spans 5.31-18.66 DN across the 22-frame sweep (3.5x). The reference frame 11 is 5th sharpest at 14.7270 DN; the modal winner frame 9 (52.1% of pixels) reads 18.6595 DN = 1.2670x the reference, unmerged. Fact 341's premise "a flat ROI, where no detail can exist" is false. MEASURED, M40 §6.1. |
| 456 | The inflation that would zero the flat-ROI detail credit is 1.0592x, 1.0626x, 1.1506x and 1.4751x on the four flat ROIs; it tracks `best/middle` frame sharpness (1.2670, 1.2808, 1.0544, 1.3430), not noise. MEASURED, M40 §6.1. |
| 457 | With `SELECTION_INFLATION = 1.074` shipped, gate-0 flat-ROI detail retention reads 0.8854x, 0.9122x, 1.0347x and **1.3147x** on the four flat ROIs. The spurious credit is removed on one ROI of one stack and survives at +31.5% on another. MEASURED, M40 §2, §6.1. |
| 458 | `n_eff = 1` for 41.66% of the plane at gate 1.00 on 109MSDCF (mean n_eff 1.884). n = 1 is the modal configuration at a working gate, not an artefact of gate 0; the two-branch invariant is the right shape. MEASURED, M40 §7.1. |
| 459 | The retired `the_merged_estimate_is_never_noisier_than_a_single_frame` was a double tautology: with `black_dn = 0.0` both sides were the same expression divided by `sqrt(n) >= 1`, and the second assertion was the algebraic identity. No input could have failed it. DERIVED from source, M40 §7. Confirms and strengthens fact 429. |

### New disciplines (unnumbered)

- **new discipline** -- *A ratio against a single reference frame is not a measurement until
  the reference has been swept.* Any published `x/middle-frame` figure must carry the range
  it takes over all N choices of reference. On this project that range has been as wide as
  1.0000x-1.5989x for a figure published as a single number.
- **new discipline** -- *Never move a number between the spatial and temporal domains.*
  Extends rule 10. `flat_roi_stats` is spatial; `predicted_sigma` is temporal; a constant
  read off one and multiplied into the other has no defined meaning even when the arithmetic
  reproduces.
- **new discipline** -- *A "flat" control ROI must be certified detail-free by the metric
  under test, not by spatial contrast.* Report the per-frame span of the metric across the
  focus sweep beside the ROI. A 3.5x span disqualifies the ROI as a null.
- **new discipline** -- *When a constant is introduced, enumerate its consumers by grepping
  for the reported quantity, not for the function name.* M40 found a fourth consumer that
  prints the repaired quantity from a different formula and still shows the unrepaired
  value.
- **new discipline** -- *A quantile channel cannot validate the scale of its own input.*
  C1's mask is invariant to any order-preserving change to `predicted_sigma`; "the
  confidence vector is unchanged" is therefore never evidence about a calibration constant.

### New questions (unnumbered)

- **new question** -- Does the C1 mask move at a wider confidence tail (25-50%), where the
  boundary crosses into n >= 2 pixels? M40 measured only the shipped 5% tail.
- **new question** -- What is the selection inflation on **real** data as a function of n,
  given that the naive stratification confounds n with scene flatness? A matched-content
  stratification is needed.
- **new question** -- Does fixed-pattern noise (PRNU, dark current, M16's orientation FPN)
  lift the true inflation above the pure-noise plant's ceiling of 1.045? If so §3.3's bound
  is not a bound.
- **new question** -- Should `SELECTION_INFLATION` be two constants (pixel domain ~1.045
  for C1, gradient domain ~1.031 for the detail metric) or a per-n curve, or should the
  detail metric stop using a model noise term at all and use a paired difference of two
  independent merges instead?
- **new question** -- Fact 19's 1.253x cannot be reproduced by M39 or M40 and its operator
  is retired, yet it is quoted live in `report_flat_roi`'s banner. Should the banner be
  cut?

---

## 11. Recommendation

1. **Revert `SELECTION_INFLATION` to 1.0**, or replace it with the two domain-specific
   values in fact 447, and keep `predicted_sigma` honest about being a floor. Shipping
   1.074 is worse than shipping nothing, because it converts a visible over-credit into an
   invisible clamped-to-zero under-credit (fact 454).
2. **Keep the two-branch test's shape** (fact 458 supports it) and re-derive its n = 1
   constant from a structure-free estimator.
3. **Fix the fourth consumer** (facts 452, 453): route the gate-calibration column through
   `predicted_sigma` and make it a mean, not a reciprocal-root-of-a-mean.
4. **Re-open fact 341** with the correct premise: the flat ROI is focus-sensitive, and the
   +35.47% is mostly the reference frame's defocus (fact 455).
