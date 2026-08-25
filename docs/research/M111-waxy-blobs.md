# M111 — the waxy blobs: what the merge synthesises where the frames carry nothing

**Status: REPORTED. §1 is the pre-registration, written and committed at `34b3983`
before any M111 measurement; §2 onward was written after.**
Author: M111. Not self-verified — see AGENTS.md rule 12.

Dispatched to find the mechanism behind the defect the owner can see, and to
prove it with controls. The defect and its first instrument are SYNTHESIS fact
**1444** (ORCH, `experiments/ORCH-drift-check/blob_probe.py`).

*Note on that citation:* §1 cited 1444 before it was folded — SYNTHESIS ran to
1441 when the pre-registration was committed. It has since been folded and the
number resolves. I flag this rather than leave it silent, because a citation
that happens to resolve later is not the same thing as one that resolved when it
was written.

Prior work searched before writing this (rule 40): `M54-clip-mask-measured.md`,
`M65-election-gate-measured.md`, `M77-gate-sweep.md`, `M81-estimation-merge.md`,
`M82-normalised-gate.md`, `M87-occlusion.md`, `M93-election-gate.md`,
`M96-election-margin.md`, `M97-warped-merge.md`, `M110-track-jitter.md`, plus
SYNTHESIS facts 19, 84, 86, 212, 242, 683, 1036, 1103–1107, 1128, 1438, 1444.
No committed report asks *why* the merge produces flat hard-edged patches; M110
is the nearest and asks about alignment jitter at election boundaries.

---

## 1. Pre-registration

### 1.1 What is being tested

**H1 — the regulariser manufactures plateaus.** Pass one elects a winner from a
`REGULARISER_RADIUS = 8` (17×17) box-filtered focus field. Where the focus
response is pure noise, a box filter over an argmax produces flat plateaus of a
single winning frame separated by hard polygonal boundaries.

**H2 — the gate is not firing where it should.** Fact 19's noise-gated mean is
supposed to average when no frame is better than the others. In a textureless
region no frame *is* better, so the gate should be averaging and there should be
no patchwork.

**H3 (named now so it cannot be claimed post hoc) — the admission cliff.** The
inverse of H2: the gate averages *many* frames inside the patch and few outside
it, so the patch is the mean of a large set of differently-defocused frames — an
image that appears in no single input — bounded by the contour where `n_eff`
collapses.

**H4 (named now) — censored highlights.** `Estimator::value` reports the pin
where the winner's own sample is at `CONTAINER_MAX_DN`, so a "winner censored /
winner not censored" contour is a hard step in the output by construction, and
its interior is flat by construction.

**H5 (named now) — downstream of the merge.** Demosaic, colour matrix, exposure,
or the per-frame alignment warp. Predicted signature: blob boundaries
uncorrelated with every pass-one and pass-two state plane, and unmoved by
`REGULARISER_RADIUS`.

### 1.2 Arms, and what each shows under each hypothesis

Instrument: a dump of pass one's `best_index` (the winner frame index) and
`best_focus` (the winner's regularised response value), and pass two's `n_eff`
(frames averaged), all on the 3520×2344 plane grid — half the 7040×4688 output
grid in each axis. `best_index` already ships as `STREHL_DUMP_ELECTION`; the
other two are added by this milestone and are proved non-perturbing by hash.

| arm | H1 true | H2 true | H3 true | H4 true | all false |
| --- | --- | --- | --- | --- | --- |
| **A. `n_eff` inside blob interiors** vs the whole-image mean (81.851 at gate 4.0 on `marker`) | not diagnostic on its own | **≈ 1**, far below the image mean | **≫ image mean**, approaching N = 299 | ≈ 1 (a censored winner is reported alone) | no relation to the mask |
| **B. `best_focus` inside blob interiors**, against the pure-noise floor (a single frame's regularised response has mean ≈ 0.433 and SD `FOCUS_NOISE_SD` = 0.015214, so the max over 299 frames sits at ≈ 0.478) | **≈ 0.48**: H1's own premise is that the response there is noise | ≈ 0.48 (same premise) | may be anywhere | high (a clipped patch's edge is the steepest thing in frame; fact 683's seek limb) | may be anywhere |
| **C. coincidence of blob boundary with `best_index` discontinuity**, against the same statistic on a translated mask (rule 17) | **high, and collapses under translation** | not required | not required | not required | at the translated-mask level |
| **D. coincidence of blob boundary with an `n_eff` step** | not required | high | **high** | high | at the translated-mask level |
| **E. `REGULARISER_RADIUS` sweep** — 0, 2, 4, 8, 16, 32, at gate 4.0 and again at a gate re-solved to hold mean `n_eff` fixed | **blob linear scale ∝ radius; at radius 0 the patch dissolves into per-pixel speckle** | unmoved | unmoved (or moves only through the gate) | unmoved | unmoved |
| **F. clip census inside the blob mask** — fraction of blob pixels whose winner sample is at `CONTAINER_MAX_DN` | ≈ 0 | ≈ 0 | ≈ 0 | **large** | ≈ 0 |

### 1.3 Registered decision rules, written before the numbers

1. **H1 is CONFIRMED** only if arm E moves the blobs' linear scale monotonically
   with the radius *and* arm C's coincidence survives its translated-mask
   control. Arm C alone is correlational and is not sufficient.
2. **H1 is REFUTED** if arm E leaves the blobs' scale unchanged within ±20%
   across a 16× span of radius, or if arm B shows the winner response inside the
   blobs to be more than 2× the pure-noise ceiling of 0.478 — because then the
   election there is driven by signal, not by noise, and H1's premise is false
   whatever the plateaus look like.
3. **H2 is CONFIRMED** if median `n_eff` inside blob interiors is ≤ 2 while the
   region carries no signal by arm B.
4. **H2 is REFUTED** if median `n_eff` inside blob interiors exceeds the
   whole-image mean. In that case H3 is the live reading and must be tested on
   arm D, not asserted.
5. **Every arm is reported with its control.** A coincidence statistic without
   its translated-mask null is not reported as a number (rule 39).
6. **The mask is defined from the output image only** — brightness and local
   flatness of the rendered RGB — and never from any merge-state plane, so that
   the axis being binned and the bins do not share a path (rule 17).

### 1.4 Negative controls, all mandatory

* **NC1 — textured ROI.** The identical blob detector over a high-texture region
  of the same render must not report the blob signature.
* **NC2 — single-frame control.** The identical detector over the LibRaw
  single-frame render must not report it.
* **NC3 — synthetic blob, real DN range.** A flat pale patch with a hard edge is
  planted into a copy of the render and pushed through the identical detector,
  which must find it. A zero-detection is not self-explaining (discipline 722,
  fact 1440).
* **NC4 — non-perturbation by hash.** The render with the state dump on and off
  must be byte-identical, SHA256 (rule 26).
* **NC5 — translated mask.** Every coincidence statistic is repeated with the
  blob mask translated far enough to destroy per-pixel correspondence while
  preserving its spatial statistics.
* **NC6 — planted mutation.** Any assertion added to the codebase is proved to
  have power by sabotaging the value it asserts on, requiring the *exact*
  expected nonzero exit code (rule 47's addendum: `-ne 0` is satisfied by the
  corruption itself under both PowerShell editions).

### 1.5 Audit of the instrument this milestone inherits

ORCH asked, in as many words, to be told if its own probe is wrong. Three
properties of `blob_probe.py` are checked **before** anything is built on it,
and are reported whatever they say:

* **A1 registration.** The probe reads the same `(x, y)` in a strehl render and
  in a LibRaw single-frame decode, having cropped both to the common top-left
  rectangle. That is only valid if the two arms are registered.
* **A2 tone.** A gradient-energy ratio between two arms is not commensurable if
  the arms' transfer curves differ in slope where the mask is drawn.
* **A3 composition of the headline ratio.** `0.094` versus `0.761` is a ratio of
  ratios. It must be decomposed into its numerator and denominator before it is
  attributed to the merge, because "the merge sharpened the surroundings" and
  "the merge flattened the interior" are different claims with different fixes.

---

## 2. Headline

> ### ⚠ RETRACTION — read §13 before quoting anything in this section
>
> **The `+97.4σ` in this section and in §4.2 is withdrawn, and so is the
> election-seam mechanism it was offered as proof of.** Two defects, both mine,
> both found by my own follow-up audit and neither by a verifier:
>
> 1. **The σ is arithmetic, not evidence.** `attribution.py` estimates the null
>    standard deviation from **three** translations and divides by it. Re-running
>    the *identical* mask with 64 translations gives a null sd of 0.021 instead of
>    0.003 and the same effect reads **+11.6σ**, not +97.4σ.
> 2. **The effect itself does not survive an independent mask.** The `flat` mask
>    was a percentile of the arm under test. Taking it from the single-frame
>    control instead — the only mask that cannot be conditioned on the outcome —
>    the whole-plane statistic is **0.839 against a 0.911 ± 0.101 null, −0.7σ,
>    p = 0.63**, and at ORCH's own `blobB` it is **1.123, +1.9σ**, marginal at
>    best. This is exactly the circularity I charged fact 1444 with in §7.2. I
>    made the same error one section later and did not see it.
>
> **What survives is in §13.3 and it is smaller and differently shaped than what
> this section claims.** The gate's absolute-tolerance collapse (the table below)
> is a direct reading of the code's behaviour and stands; the claim that it
> prints *at election seams* does not. **H1, H2 and H7 remain refuted** — their
> refutations are direct arm-to-arm comparisons that never used the broken null.

**The waxy patches are single elected frames. The merge stops averaging and
starts electing wherever the winner's focus response rises out of the noise
floor, because the gate's tolerance is an absolute constant in response units
while the response itself is a contrast-scaled quantity spanning 0.43 to 84 on
this stack. Visually flat regions that nonetheless carry weak defocused
structure fall in that collapse band, get rendered from one frame per plateau,
and the plateau seams print into the image.**

The collapse, measured on the shipped render, gate 4.0, `marker`:

| winner response `best_focus` | % of plane | mean `n_eff` | median `n_eff` |
| --- | --- | --- | --- |
| 0.60 – 0.65 | 18.55 | 275.5 | 285 |
| 0.65 – 0.70 | 2.13 | 112.3 | 119 |
| 0.80 – 1.00 | 5.39 | 43.3 | 29 |
| 1.00 – 1.50 | 6.96 | 22.5 | 17 |
| 2.00 – 3.00 | 4.29 | 7.7 | 5 |
| 3.00 – 5.00 | 9.17 | 3.0 | 2 |
| 5.00 – 10.00 | 12.41 | 1.6 | 1 |
| above 20 | 15.18 | 1.1 | 1 |

Admission falls **285 → 1** while the response rises **8×**. The gate's
tolerance is fixed at `4.0 · √2 · FOCUS_NOISE_SD` = **0.086063** response units:
14% of a response of 0.62, and 1.7% of a response of 5.

Neither hypothesis I was handed survives, and the reason each fails is the
useful part.

* **H1 — REFUTED.** The regulariser sets the plateaus' *scale* and does not
  create them. At `REGULARISER_RADIUS = 0` — the box removed entirely — the
  plateaus are still **54.0 px** across against **60.3 px** shipped, and the
  artifact's amplitude is **1.213** against a null of 1.005 ± 0.030, statistically
  indistinguishable from the shipped 1.239. H1's stated premise is separately
  false: **0.00%** of either of ORCH's blob ROIs has a winner response below the
  pure-noise ceiling of 0.4777, with medians of 4.305 and 2.961 — 9.0× and 6.2×
  the ceiling. The election in there is driven by signal, not by noise.
  **Fact 84's −35% is not implicated. The regulariser is not the culprit.**
* **H2 — REFUTED as a diagnosis; its symptom is real.** The gate fires, and
  fires hardest exactly where H2 said it would not: median `n_eff` is **285** in
  the weakest-response band and **151** across the whole visually flat
  population. What H2 got right is that the merge is not averaging inside the
  patches (median `n_eff` **2.0** in both of ORCH's ROIs). What it got wrong is
  the reason. It is not that no frame is better; frames there differ by
  **2.4×** the gate's own tolerance from one another, so the gate is behaving
  exactly as specified. The specification is what is wrong.

The third mechanism is the one above, and it is proved by an arm neither
hypothesis called for: rendering the same stack, the same frames, the same
alignment, the same colour and the same exposure with the gate opened to admit
everything, and differencing.

---

## 3. What reproduced, and what that buys

`experiments/M111-waxy-blobs/render_baseline.ps1`, built from a `git archive` of
`a7bd05a` into a private `CARGO_TARGET_DIR`, renders

```
strehl stack D:\personal\macro\dry-erase-marker-head-cpl --srgb --exposure=-0.24 --gate 4
```

to SHA-256 `DB7BAAD2FDC5BF74309B132D0DDEB1A681609037312E76923C2B22703BA1DDDC`,
198 022 898 bytes — **byte-identical to ORCH's
`marker-HEAD-8f46f04.tif`**, which was rendered at a different commit by a
different agent. The merge core is unchanged between `8f46f04` and `a7bd05a`
(`merge.rs`, `focus.rs`, `through_focus.rs`, `plane.rs`, `noise.rs` all diff
empty), so every state plane below describes exactly the pixels ORCH measured
rather than an approximation of them.

`STREHL_WARPMAP` was pinned to a private copy of the solve (rule 45); without
that pin six live agents share one warpmap cache and the render is not
reproducible.

**NC4 passed twice.** Dump-off and dump-on renders are byte-identical in the
pinned scratch build *and* in the live tree
(`experiments/M111-waxy-blobs/nc4_live_nonperturbation.ps1`), where the live
tree also happens to still produce `DB7BAAD2…` despite other agents' uncommitted
`align.rs` and `robust.rs` work.

### 3.1 The instrument

`crates/strehl-cli/src/merge_cmd/dump.rs` — new, additive, env-gated on
`STREHL_DUMP_MERGE_STATE`. It writes three NPY planes on the 3520×2344 plane
grid (output coordinates halved, one focus decision per CFA quad):

| plane | dtype | what |
| --- | --- | --- |
| `best_index.npy` | `u16` | pass one's elected frame index. Already available as `STREHL_DUMP_ELECTION` (fact 1445, `b27904a`); duplicated here so all three planes come from one switch. |
| `best_focus.npy` | `f32` | the winner's **regularised response value**. This is the plane that decides whether an election was made on signal or on noise, and nothing before this milestone could see it. |
| `n_eff_gate*.npy` | `u16` | pass two's per-pixel admitted-frame count, per gate. Fact 1141 says a whole-image mean cannot locate anything; this is the same quantity that can. |

`STREHL_DUMP_ELECTION` **already existed** at HEAD (M97's
`write_election_map`), contrary to the brief's uncertainty. The two new planes
did not.

---

## 4. The mechanism, measured

### 4.1 The pooled test is null, and that is the first useful result

Defining "flat" from the rendered luma alone — 9×9 local sd below 300 DN,
**40.18%** of the plane — and asking whether luma steps concentrate on election
boundaries there gives **1.061** against a translated-election null of
**0.999 ± 0.071**. That is 0.87σ: **nothing**.

A report that pooled the flat population would have concluded there is no
defect. The flat population is two populations:

| population | fraction of flat | median `n_eff` | median `best_focus` |
| --- | --- | --- | --- |
| flat, `n_eff ≥ 64` | 85% | 151 (mean 155) | 0.62 |
| flat, `n_eff ≤ 8` | **14.77%** | ≤ 8 by construction | 4.3 |

and the defect lives entirely in the second.

### 4.2 The unconfounded attribution

> **⚠ The table in this subsection is retracted. See §13.** The null it quotes
> is a three-sample standard deviation, and its `flat` mask is a percentile of
> the arm under test. Both are corrected in §13; the corrected numbers do not
> support the conclusion stated here.

The coincidence statistic on its own is **confounded, and my own arm caught it.**
At `--gate 100000` every output pixel is the plain mean of all 299 frames, so
the election has no influence on the output whatsoever — and election boundaries
*still* score **1.686** against a 1.048 null there. Election boundaries sit
where frames' focus responses cross, which is genuinely correlated with scene
structure. **"The blob edge coincides with an election boundary" is not evidence
that the election drew it,** and this report would have been wrong if it had
stopped at that number.

The test that is not confounded is the difference image

```
D = luma(gate 4) − luma(gate 100000)
```

Same frames, same alignment, same colour pipeline, same pinned exposure; the
arms differ only in how many frames the gate admitted. `D` is therefore exactly
what **selection** added.

| population | on-seam DN | off-seam DN | excess | ratio | translated null | σ |
| --- | --- | --- | --- | --- | --- | --- |
| **flat, `n_eff ≤ 8`** | 60.38 | 48.38 | **+12.00** | **1.248** | 1.002 ± 0.003 | **+97.4** |
| flat, `n_eff ≥ 64` | 5.03 | 6.57 | −1.55 | 0.765 | 1.012 ± 0.050 | −5.0 |
| textured (NC1) | 565.19 | 641.99 | −76.79 | 0.880 | 0.963 ± 0.035 | −2.4 |

The same detector on the shipped image itself, not the difference: **1.239**
against 1.005 ± 0.006 (+37.5σ), with both controls again *below* their nulls
(0.897 and 0.887).

**Selection adds 12 DN of extra step exactly at plateau seams, in regions that
are otherwise flat, and adds nothing at seams where it averaged and nothing at
seams in textured regions.**

Energy accounting in the same three populations: median `|D|` is **1458 DN**
where the merge elected, **58.5 DN** where it averaged, **3144 DN** in texture.
Selection is doing almost nothing where it averages and a great deal where it
elects — which is the design — and the price is paid where there is no detail
to buy.

### 4.3 Why the plateaus are 54 px wide when the regulariser is off

`crates/strehl-core/src/focus.rs` line 83: `WINDOW_RADIUS = 13`, a **27×27 box
mean of the Sobel magnitude over sigma** (M13). The focus field the merge takes
an argmax over is *already* smoothed at 27 px before `merge.rs` applies its
further 17×17. That is why radius 0 is not per-pixel speckle. The merge
regulariser contributes **60.3 / 54.0 = 1.12×** of the plateau diameter at its
shipped radius.

| `REGULARISER_RADIUS` | plateau equiv. diameter (own mask) | (fixed r8 mask) | seam density | artifact ratio | null | whole-image mean `n_eff` |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 54.0 | 57.4 | 0.1789 | 1.213 | 1.005 ± 0.030 | 60.9 |
| 2 | 54.0 | 56.9 | 0.1284 | 1.224 | 0.993 ± 0.022 | 63.5 |
| 4 | 55.6 | 57.6 | 0.1160 | 1.238 | 0.998 ± 0.014 | 66.2 |
| **8 (shipped)** | **60.3** | **60.3** | **0.0984** | **1.239** | 1.005 ± 0.006 | 70.7 |
| 16 | 71.7 | 66.6 | 0.0838 | 1.287 | 1.004 ± 0.010 | 75.3 |
| 32 | 86.7 | 69.7 | 0.0598 | 1.203 | 1.009 ± 0.011 | 76.6 |

A **32× change of radius moves the plateau scale 1.6× and the artifact's
amplitude not at all.** All six renders have distinct SHA-256s, so the override
was live in every arm.

### 4.4 The dose-response on the axis that does move it

`experiments/M111-waxy-blobs/sweep_gate.ps1`, shipping regulariser throughout,
masks held fixed at the gate-4 definition:

| `--gate` | mean `n_eff` | flat pixels that elect | plateau interior sd | artifact ratio | null |
| --- | --- | --- | --- | --- | --- |
| 0.25 | 6.2 | **97.30%** | 174.2 | 1.264 | 1.012 ± 0.002 |
| 1 | 9.0 | 50.63% | 166.1 | 1.190 | 1.011 ± 0.005 |
| **4 (shipped)** | **81.9** | **14.77%** | 153.5 | 1.239 | 1.005 ± 0.006 |
| 16 | 114.1 | 5.76% | 167.8 | 1.392 | 0.998 ± 0.019 |
| 64 | 152.8 | 1.67% | 107.9 | 1.985 | 0.982 ± 0.027 |
| 100000 | 299.0 | **0.00%** | 74.2 | — | — |

The vulnerable population is what collapses: **97.3% → 0%** of flat pixels are
rendered by election as the gate opens. Looked at directly
(`C:\dev\strehl-out\M111\_ARMS-blobB.png`, six panels: r0, r8, r32, g0.25, g4,
g1e5) the lobes are present and hard-edged at r0, present at r8, larger and
smoother at r32, **worst and most angular at gate 0.25, and completely absent at
gate 100000.**

**And gate 100000 is not the fix.** That arm is a defocused mush: the marker
texture is gone entirely, and plateau-interior sd falls from 153.5 to 74.2
because everything fell. Opening the gate removes the artifact by removing the
photograph.

### 4.5 The seam is a near-tie, and that is what makes a fix possible

`experiments/M111-waxy-blobs/seam_continuity.py`. Across election seams:

| population | median `\|Δ best_focus\|` on seam | off seam | as a fraction of the gate-4 tolerance |
| --- | --- | --- | --- |
| flat, `n_eff ≤ 8` | 0.04023 | 0.01708 | **0.467×** |
| flat, `n_eff ≥ 64` | 0.00089 | 0.00091 | 0.010× |
| textured | 0.18823 | 0.22640 | **2.187×** |

Where the artifact is, the two competing frames are within **half the gate's own
tolerance** of each other and the merge nonetheless picks one and discards the
other. Where there is real texture, the winner is **2.2 tolerances** ahead and
deserves to win. That 4.7× separation is the handle a fix can grip. 46% of seams
in the flat population jump **ten frames or more** in winner index while the
response moves by less than half a tolerance.

---

## 5. Verdicts

| hypothesis | verdict | the number |
| --- | --- | --- |
| **H1** regulariser manufactures plateaus | **REFUTED** | plateau diameter 54.0 px at radius 0 vs 60.3 px shipped; artifact ratio 1.213 vs 1.239 across a 32× radius span. Premise separately false: 0.00% of either blob ROI below the 0.4777 noise ceiling, medians 4.305 / 2.961. Registered rule 2, second clause. |
| **H2** the gate is not firing where it should | **REFUTED as a diagnosis** | median `n_eff` 285 in the weakest-response band, 151 across the whole flat population. The gate fires hardest exactly where H2 said it does not. Its symptom half is confirmed: median `n_eff` 2.0 inside both of ORCH's ROIs. Registered rule 3's second clause fails — the region carries signal. |
| **H3** admission cliff, blobs are means of many frames | **REFUTED (mine)** | `n_eff` inside the blobs is **low**, not high: median 2.0 against a whole-image mean of 81.9. |
| **H4** censored highlights | **REFUTED (mine)** | **0.000%** of either blob at or near the 16-bit ceiling in either arm (`audit_probe.py` A3). |
| **H5** downstream of the merge | **REFUTED (mine)** | the artifact is removed completely by a merge-only change (`--gate`) with demosaic, colour, exposure and the alignment warp bit-for-bit identical. |
| **H6** intermediate-response admission collapse | **PARTLY CONFIRMED — see §13** | The admission collapse itself is confirmed and mask-free: 285 → 1 as response rises 0.62 → 5. The seam-attribution that was offered as proof it *causes the visible defect* is **retracted** — the +97.4σ divided by a three-sample null sd and its mask came from the arm under test. Corrected: **+0.5σ, p = 0.65** on the single-frame-control mask. |
| **H7** heterogeneous-PSF averaging (ORCH) | **REFUTED** | 3 of 4 predictions fail, including its own nominated discriminator. Plateaus in blobs are *smaller* (33.2 px) than the plane average (92.5 px); `n_eff` inside blobs is median **2.0**, not high; tightening the gate makes the artifact **worse** (97.30% of flat pixels elect at gate 0.25). Only P2 survives (seams jump median 3 frames, 17.9% ≥ 10). Shares H2's refuted premise. §14. |

> **What remains proved about the defect after §13:** in regions the single-frame
> control says are textureless, the shipped render carries **6.1×** that frame's
> local variation (466.1 DN vs 75.9 DN), measured with no render-derived mask.
> That is real and it is the user's complaint. **What mechanism produces it is
> not settled** — it is not the regulariser (H1), not a silent gate (H2), not
> PSF-heterogeneous averaging (H7), and not, on the corrected numbers, a step
> printed at election seams (H6's second half).

---

## 6. The controls, and what each could have killed

| control | result | what it would have killed |
| --- | --- | --- |
| **NC1** identical detector on textured regions | ratio **0.880**, −2.4σ (below null) | if it fired here, the detector measures "edges", not "invented edges". |
| **NC2** single-frame LibRaw control | superseded by a stronger arm — see §7 | the cross-arm control is unregistered and tone-confounded; the gate-100000 arm is the same comparison with those confounds structurally absent. |
| **NC3** synthetic patchwork at the real DN range | planted 0 / 2 / 4 / 8 / 16 DN recovered as **0.000 / 2.033 / 3.626 / 7.268 / 15.593** DN of excess | a detector that cannot see a planted signal cannot be trusted reporting one; and the amp-0 arm returning exactly 0.000 shows it invents nothing. |
| **NC4** dump on vs off, SHA-256 | identical, in both the pinned build and the live tree | if the dump moved bytes, every plane would describe a different image than the one measured. |
| **NC5** translated election map | every headline has one; nulls 0.98–1.05 with sd 0.003–0.05 | if the null matched the real number, the statistic measures the index map's spatial statistics rather than its registration to the image. |
| **NC6** planted mutation | sabotage → exit **exactly 101**, correct test named; restore → exit **exactly 0**, 3/3 pass | a green suite is a claim about the instrument, and this is the claim being falsified. **It also found a real defect in my own test** — see below. |
| **gate-100000 arm** | election boundaries score 1.686 vs 1.048 null with the election disconnected from output | this one **did** kill something: it killed the coincidence statistic as evidence. |
| **NC7** cache contamination (fact 1446) | §12: marker A2 green with A1 and A3 both red; lavendar's cached sidecar is byte-identical to a fresh solve | if the warp cache had served either arm a foreign registration, every delta in this report would be a cache artefact. |
| **generality arm** (`lavendar`) | ratio 0.922, −4.5σ | see §8.3. |

**NC6 found a defect in my own instrument.** The first version of
`a_length_mismatch_is_refused_rather_than_written` asserted `!path.exists()`
after a refusal, using a relative path. The sabotage created that file, the
restore then failed with exit 101, and the "restored" tree was red for a reason
that had nothing to do with the restore. A test a sabotage can leave broken is a
test that cannot be trusted to have been green for the right reason. It is now
`check_len`, pure, with no filesystem in the assertion, and the red/green cycle
is clean. This is discipline 722's shape applied to a test rather than a
detector.

---

## 7. The audit of ORCH's probe — asked for, and it does not survive intact

ORCH asked to be told directly if the probe was wrong. It is wrong in two of its
three claims, and right in the one that matters most.

### 7.1 The 10.6× headline is mostly the stacker working

`0.094` versus `0.761` decomposes as

| | inside blob | outside blob |
| --- | --- | --- |
| control | 119.17 | 156.67 |
| merged | 79.29 | 839.17 |
| merged / control | **0.67×** | **5.36×** |

The blob interior is 0.67× the control's — modest flattening, entirely
consistent with averaging noise down. The *surroundings* are **5.36× sharper**.
Most of the ratio-of-ratios is **the merge sharpening the textured part of the
frame relative to a defocused single frame**, which is the stacker doing its
job. "The merge is flattening the interior 10.6× beyond the optics" is not what
the number says.

### 7.2 The boundary-hardness number is mask-circular

The mask is `merged ≥ percentile(merged, 75)` — defined on the arm under test
(rule 17). Re-scoring the identical statistic with the mask taken instead from
the gate-100000 arm, so the mask and the arm no longer share a path, moves the
shipped arm's boundary p90 at blobB from **1384.04 to 115.42**. A 12× change
from changing only the mask's source. The number is not measuring the merge.

### 7.3 `blobA` is not a defect at all

| arm | inside | outside | ratio | boundary p90 |
| --- | --- | --- | --- | --- |
| single frame | 197.71 | 134.63 | 1.468 | 237.00 |
| **gate 4 (shipped)** | 295.02 | 199.73 | **1.477** | 737.38 |
| gate 0.25 | 297.52 | 203.22 | 1.464 | 664.09 |
| gate 100000 | 52.62 | 30.04 | 1.752 | 66.67 |

The interior ratio is **1.477 shipped against 1.468 in the control** — ORCH
flagged this themselves. The merge state explains the rest: the whole ROI elects
frames **178–220**, 28 distinct winners out of 299, `n_eff` mean 1.77. That is a
genuine in-focus bright object with a real edge, and the "6.1× harder boundary"
is a focus stacker sharpening a real edge relative to a defocused frame. **Any
fix aimed at blobA would be a regression.**

### 7.4 What survives, and it is the important part

**The eye was right.** There are pale, internally featureless patches bounded by
hard scalloped edges that appear in no input frame. Run ORCH's own statistic
across the selection arms at blobB, mask held fixed, everything else identical:

| arm | inside | outside | ratio | **boundary p90** |
| --- | --- | --- | --- | --- |
| gate 100000 (no selection) | 23.21 | 64.88 | 0.358 | **83.98** |
| **gate 4 (shipped)** | 79.29 | 839.17 | 0.094 | **1384.04** |
| gate 0.25 (near-argmax) | 167.32 | 865.13 | 0.193 | **1556.72** |

Boundary hardness normalised by each arm's own outside gradient energy —
1.294 → **1.649** → 1.800 — is monotone in how hard the merge selects. ORCH
found a real defect with a flawed instrument. Both halves of that sentence
belong in the record.

---

## 8. Recommended fix

> **⚠ Superseded by §13.4.** This section was motivated by the seam-attribution
> retracted in §13. With that evidence withdrawn, **§8.2's soft admission weight
> is unmotivated as well as unbuilt, and should not be implemented on this
> report.** §8.1 ("what not to do") stands — it is argued from the radius and
> gate sweeps, which are unaffected. §8.3 stands.

### 8.1 What not to do

* **Do not open the gate.** §4.4 measures the cost: the photograph goes.
* **Do not rescale the gate by a texture-qualified noise estimate.** That is
  M81's refuted unit hypothesis (`M81-estimation-merge.md`): correction made the
  sibling span **worse**, 3.25× → 3.63×, and the corrected gate beat the shipped
  one on **0/5** stacks. M111 does not revisit it and its result does not depend
  on it.
* **Do not touch `REGULARISER_RADIUS`.** It is exonerated, fact 84 stands, and
  `FOCUS_NOISE_SD` is defined against it.

### 8.2 What to do — a soft admission weight (ARGUED, not measured)

Replace pass two's boolean admit/reject with a weight that decays smoothly in
the response margin, e.g.

```
w_f = exp( −½ · ((best − focus_f) / tol)² ),   tol = threshold · √2 · FOCUS_NOISE_SD
```

and accumulate `Σ w_f · sample_f / Σ w_f`.

The argument is the §4.5 measurement and nothing else. At a seam the two
competing frames are within **0.467 tolerances** of each other, so a weight with
scale `tol` gives them near-equal weight and the seam is blended out of
existence. In texture the winner is **2.187 tolerances** ahead, so it keeps
essentially all the weight and sharpness is preserved. The current rule cannot
distinguish those two cases because a step function has no gradient to
distinguish them with.

**Why this is cheaper than the alternatives:**

* the tolerance keeps its unit, so **`FOCUS_NOISE_SD` (fact 500) survives
  unchanged** — this is the property M81's route did not have;
* memory and pass structure are unchanged; the cost is one `exp` and one
  multiply-add per frame-pixel in pass two, against the existing compare-and-add;
* it is a strict generalisation — the boolean gate is the limit of a box kernel.

**What it breaks, explicitly:**

| breaks | why |
| --- | --- |
| every row of `crates/strehl-cli/tests/byte-freezes.tsv` covering `stack`/`merge` | pass two's output changes on every pixel where `n_eff > 1`. |
| `DEFAULT_GATE = 4.0` | a Gaussian of scale `tol` admits more effective weight than a box of half-width `tol`; the constant must be re-solved for the new shape. It is a re-solve of an existing constant, not a new uncalibrated one. |
| fact 19's **0.534×** | measured for the boolean gate. The soft gate needs its own number; it does not inherit this one. |
| facts 1036, 1103–1107, 1128, and M77's `n_eff/N` spans | these describe the boolean gate's behaviour. They should be **scoped** to it rather than retracted. |
| fact 84's −35% | **not affected.** The regulariser is untouched. |

**Cost estimate:** the change in `merge.rs` is small — `Gate::admits` becomes
`Gate::weight`, `Estimator::fold_inner` accumulates weighted sums, `n_eff`
becomes `(Σw)² / Σw²` which is its actual definition anyway. Re-solving
`DEFAULT_GATE` is the expensive part and is a ladder, not a research question.
I estimate the implementation at well under a day and the constant at one sweep.
**I have not implemented or measured it. It is ARGUED.**

### 8.3 A second, free recommendation

Ship the merge-state dump (this milestone does). Before it, "is the gate firing
here?" was unanswerable, and both hypotheses in the brief were guesses about a
quantity nobody could see. `n_eff` per pixel is the plane that turns this class
of question into a measurement.

---

## 9. What I could not settle

1. **Generality is UNRESOLVED, and it may be a real limit rather than a gap.**
   On `lavendar` the same detector reads **0.922**, −4.5σ — *below* its null.
   The mechanism predicts this: `lavendar` has **2.78%** of its plane in the
   vulnerable flat-and-intermediate-response population against `marker`'s
   **18.18%**, and only **1.11%** of its plane elects in flat regions against
   `marker`'s 5.93%. So a stack with no vulnerable population shows no defect,
   which is the mechanism's own prediction confirmed on a stack it was not
   derived from. **But I cannot fully separate that from a sensitivity failure:**
   an in-situ plant of 16 DN moves `lavendar` by only **+2.8σ** against
   `marker`'s +9.4σ. The reading is consistent with absence and I am not
   entitled to call it absence. Two more stacks would settle it.
2. **The runner-up margin is not dumped.** §4.5 uses `best_focus` continuity
   across seams as a proxy for "the two frames are tied". The direct quantity —
   the second-best response at each pixel — is not in `FocusStats` and adding it
   costs another full plane. The proxy is sound (a seam is where two responses
   cross, so continuity of the max *is* near-tie) but it is a proxy and is
   labelled one.
3. **The soft gate is unmeasured.** §8.2 is an argument from two numbers, not a
   measurement of a built thing. It should be built and priced before anyone
   believes the sharpness claim.
4. **I have not priced the artifact perceptually.** +12.00 DN of excess step in
   a region whose off-seam step is 48 DN is a 25% relative effect and it is
   visible in `_ARMS-blobB.png`, but "how much of the owner's complaint is this
   versus softness versus the half-drift alignment defect" is not a question my
   arms can answer.
5. **`n_eff ≤ 8` is a stated threshold, not a derived one.** The results are
   reported at one operating point. The gate sweep varies the population
   continuously and behaves monotonically, which is the best evidence I have that
   the threshold is not load-bearing, but I did not sweep it directly.

---

## 10. Candidate facts and disciplines

Numbered `P1…` per rule 28; ORCH assigns corpus numbers.

**Facts**

* **P1 — MEASURED.** The merge's gate tolerance is an absolute constant in focus-response units (`threshold · √2 · FOCUS_NOISE_SD` = 0.086063 at the shipped gate 4.0) while the response itself is contrast-scaled. On `dry-erase-marker-head-cpl`, admission collapses from mean `n_eff` **275.5** in the 0.60–0.65 response band to **1.6** above 5.0 and **1.1** above 20, i.e. the merge is an averager where the response is at the noise floor and a pure selector everywhere else. `experiments/M111-waxy-blobs/mechanism.py`.
* **P2 — RETRACTED, see P24.** ~~The waxy patches are selection artefacts, not regulariser artefacts...~~ The published version divided by a three-sample null sd and used a mask taken from the arm under test. Both defects are corrected in §13; the effect does not survive either correction. **Do not fold P2.**
* **P3 — MEASURED.** `REGULARISER_RADIUS` sets the plateaus' scale and does not create them. Sweeping 0 → 32 moves the plateau equivalent diameter **54.0 → 86.7 px** and the seam density 0.1789 → 0.0598, while the artifact amplitude is flat at **1.213 / 1.239 / 1.203**. At radius 0 — the box removed — the plateaus are still 54.0 px across, because `focus.rs`'s `WINDOW_RADIUS = 13` already smooths the field over 27×27 before the argmax. The merge regulariser contributes **1.12×** of the plateau diameter at its shipped radius. Fact 84 is not implicated.
* **P4 — MEASURED.** In the elected flat population the winner's response is continuous across the seams it draws: median `|Δ best_focus|` on seam is **0.04023**, **0.467×** the gate's own admission tolerance, while in textured regions it is **0.18823** = **2.187×** tolerance. The merge discards a frame that is within half a tolerance of the winner and paints a hard edge where it changes its mind. `experiments/M111-waxy-blobs/seam_continuity.py`.
* **P5 — MEASURED.** Opening the gate removes the defect and the photograph together. At `--gate 100000` the flat population that elects falls **14.77% → 0.00%** and the artifact vanishes, but plateau-interior sd falls **153.5 → 74.2** and the subject's texture is gone. At `--gate 0.25`, **97.30%** of flat pixels elect and the seams are at their hardest (1.264).
* **P6 — MEASURED.** Fact 1444's `blobA` is not a defect. Its interior gradient ratio is **1.477** in the shipped render against **1.468** in the single-frame control, and the merge elects frames 178–220 there — 28 distinct winners of 299, `n_eff` mean 1.77. It is a real in-focus edge that the stacker correctly sharpened. Fact 1444 should be **SCOPED to `blobB`**.
* **P7 — MEASURED.** Fact 1444's headline 0.094-vs-0.761 decomposes into interior **0.67×** and exterior **5.36×**: most of the ratio-of-ratios is the merge sharpening the surroundings, which is the stacker working, not the merge flattening the interior. Its boundary-hardness number is mask-circular — the mask is the arm under test's own bright quartile, and taking the mask from an independent arm moves the shipped arm's boundary p90 from **1384.04 to 115.42**. Fact 1444's defect is real and independently confirmed here at 97σ; its two numbers are not the evidence for it.
* **P8 — MEASURED.** A coincidence between an image feature and an election boundary is not evidence that the election drew it. At `--gate 100000` the election has zero influence on the output and election boundaries still score **1.686** against a 1.048 null, because seams sit where responses cross and that is correlated with scene structure. This bears directly on **fact 1445's** second column, which argues that a joint statistic between the render and the election map is immune to fact 1438's single-frame control "because a single frame has no election map at all". That is true and insufficient: the gate-100000 arm *has* an election map, is not a single frame, and is decoupled from the output, and it still produces the coincidence — at **1.686, higher than the shipped arm's 1.239**. Fact 1445's shipped instrument and its 23.2× structure factor stand; the immunity claim needs the extra clause. **A blob/election coincidence test is therefore not a valid cheap refutation of H1:** H1 and the confirmed mechanism both predict coincidence, and the arm with no mechanism at all produces the most of it, so the test cannot separate them in either direction.
* **P9 — MEASURED.** Pooling the visually flat population hides the defect completely: the whole flat population (40.18% of the plane, 9×9 local sd < 300 DN) scores **1.061** against a 0.999 ± 0.071 null. It is two populations — 85% averaging at median `n_eff` 151, 14.77% electing — and only the second carries the artifact.
* **P10 — MEASURED.** `STREHL_DUMP_MERGE_STATE` is byte-inert: dump-on and dump-off renders are SHA-256 identical in both a pinned `a7bd05a` build and the live tree, and the pinned build reproduces ORCH's `marker-HEAD-8f46f04.tif` exactly at `DB7BAAD2FDC5BF74309B132D0DDEB1A681609037312E76923C2B22703BA1DDDC`.
* **P11 — MEASURED.** The defect is stack-dependent in the way the mechanism predicts. `marker` has **18.18%** of its plane both visually flat and in the 0.7–5.0 response band; `lavendar` has **2.78%**, and `lavendar`'s detector reads 0.922 (−4.5σ). An in-situ 16 DN plant moves `lavendar` by only +2.8σ against `marker`'s +9.4σ, so this is consistent with absence but does not establish it.
* **P12 — ARGUED.** A soft admission weight `exp(−½((best − focus)/tol)²)` would blend seams where the frames are tied and preserve the winner where it is genuinely ahead, using the 4.7× separation P4 measures. It keeps `FOCUS_NOISE_SD`'s unit — which M81's texture-qualified correction did not — at the cost of re-solving `DEFAULT_GATE` for the new kernel shape and re-measuring fact 19's 0.534×. Unbuilt and unpriced.
* **P18 — MEASURED.** `HEAD` did not compile between `e4796e5` and `fc4cbf6`. `e4796e5` ("M97o: drop refused frames instead of aborting the render") committed another agent's `merge_cmd.rs` **together with three uncommitted edits of mine that were live in the shared tree**, including `pub(crate) mod dump;` and two call sites, while `dump.rs` itself was untracked and therefore did not go with them. `git cat-file -e HEAD:crates/strehl-cli/src/merge_cmd/dump.rs` exits **128**; a `git archive HEAD` build fails on the missing module and succeeds at **exit 0** with `dump.rs` committed. **A path-scoped commit is path-scoped, not authorship-scoped** — naming a file you did not fully write commits whatever is in it. Repaired at `fc4cbf6`. A second, independent breakage is live in the tree right now: an uncommitted `main.rs` references `n_eff_map` on `Command::Stack` and `MergeOptions`, which do not have it; that one is not at HEAD and is not mine.

**Disciplines**

* **P13.** When a defect is defined by a mask and the mask is a percentile of the arm under test, the statistic separates the arms by construction. Re-score with the mask taken from a third arm before attributing anything. Fact 1444's boundary number moved 12× under this check.
* **P14.** A coincidence between an artefact and an internal state plane needs an arm in which that state plane **cannot** affect the output. Translating or shuffling the plane is not enough — those destroy correspondence but not the state plane's own correlation with the scene, and "no unstacked frame has this plane" is not a substitute either (fact 1445). M111's gate-100000 arm killed its own headline coincidence statistic; the difference image replaced it.
* **P15.** Before pooling a population defined by an image property, check whether the merge treated it as one population. M111's flat population is 85% averaged and 15% elected and the pooled test is null at 0.87σ while the split test is 97σ.
* **P16.** A planted-mutation control tests the restore as well as the sabotage. M111's sabotage left a file on disk that its own assertion depended on, so the restored tree was red for a reason unrelated to the restore. Assert the exact expected code on **both** legs and make the assertion independent of filesystem residue.
* **P17.** An env-var debug export that would move output bytes belongs in a patch beside the experiment, not in the repository. M111's `STREHL_M111_REG_RADIUS` earned its result and shipped as `experiments/M111-waxy-blobs/reg_radius.patch`; the byte-inert state dump shipped as code.
* **P19.** In a shared tree, commit a new module and its `mod` line in the **same** commit, and check `git log -S '<the mod line>'` before assuming your edit is still uncommitted. M111's `mod dump;` was swept into another milestone's path-scoped commit and left HEAD un-buildable for six commits, which no agent noticed because everyone was building a working tree that still had the file.
* **P23.** A cache-contamination control needs a **red** arm on the vulnerable code path, not merely a green one on the arm under test. M111's NC7 green (poisoned cache, override set, bytes unmoved) is worth nothing on its own; it is worth something because the same poisoned cache moved the bytes when the override was removed, and moved them to the exact hash the poison produces when read directly. **Ask "which code path did my render actually take" before asking "is my number contaminated"** — the renderer prints it, and on this fleet it split one milestone's arms into an immune 15 and an exposed 2.
* **P27.** **Never divide by a standard deviation estimated from fewer than about thirty samples, and prefer a rank p-value that cannot be inflated at all.** M111 reported +97.4σ from a null of **three** translations; the same mask at 64 translations reads +11.6σ. The failure is silent because a small-n sd is biased *downward*, so the defect always flatters the result and never warns you. Report the null's sample size next to every σ, and quote the rank floor — 64 translations cannot license anything below p = 1/65.
* **P28.** **P13 is not a rule for other people's instruments.** M111 charged fact 1444 with mask circularity in §7.2 and committed the identical defect in §4.2 of the same report, five sections apart, without noticing. A mask-circularity check belongs in the harness that computes the statistic — score every masked statistic under at least one mask drawn from an arm that cannot have been affected by the treatment — not in a reviewer's attention.
* **P29.** **When an independent mask kills an effect, partition before concluding either way.** The independent mask can be larger and dilute a real effect, or the original mask can be conditioning on the outcome, and the pooled comparison cannot tell them apart. Split into (original ∧ independent), (original only), (independent only). If every firing cell contains the original condition and the independent-only cell is null, it is circularity. M111's independent-only cell read **0.954, −0.2σ** against an original-only **1.169, +8.1σ**, which is the answer.
* **P30.** **Match the population fraction, not the threshold, when swapping a mask between arms of different contrast.** M111's absolute `local_sd < 300 DN` selects 39.9% of the shipped arm and 81.5% of the softer mean arm, so the mask swap silently swapped the population size too and its result could not have been read either way. Take the same percentile of each arm; then the only thing that varies is which arm decides.
* **P31.** **A median connected component is not a plateau size.** Counting components equally lets one-pixel islands dominate: on M111's map the median-component figure reads 3.7 px inside `blobB` while the area-weighted equivalent diameter — the plateau the average *pixel* sits in — reads 33.2 px, a 9× difference that reverses which regions look coarse. Weight by area whenever the question is "what does a pixel experience".
* **P20 — MEASURED.** Fact 1445's election-map statistics do not transfer across stacks and must not be quoted as properties of the map. Re-measured on `dry-erase-marker-head-cpl`, 299 frames, alignment **on** with `STREHL_WARPMAP` pinned: boundary density **9.91% h / 9.03% v** against 1445's 3.33% / 3.34%, median jump **2 frames** against 1445's 1, and **44.1%** single-frame steps against 71.4%. On `lavendar-cpl` the median jump is **20 frames** and single-frame steps fall to **22.5%**. The plane grid is **3520×2344** here, not 1445's 3516×2344 — both solvers' own sidecar headers say so — and the grid follows the common crop, so a milestone that hard-codes either number will index the wrong pixels. Fact 1445's numbers should be **SCOPED** to its 12-frame `STREHL_ALIGN=0` arm.
* **P21 — MEASURED.** `STREHL_WARPMAP` structurally immunises a render against fact 1446: `merge_cmd.rs`'s `alignment_for` returns to `align_cmd::load_or_solve` — the poisoned function — only when the variable is unset. Measured with a sidecar that passes every identity check and displaces 298 of 299 frames by 2.0 plane px: with the override set, a poisoned cache leaves the render at `DB7BAAD2…`, unchanged; with it unset, the same cache moves the render to `0D41E08B…`, which is *bit-for-bit* what pointing the override at the poison directly produces. The renderer prints which path it took — `sidecar-override` versus `sidecar` — so exposure is readable from any milestone's existing logs without re-running anything.
* **P22 — MEASURED.** The `lavendar-cpl` cache entry consumed by M111's generality arm is byte-identical (`4D454CCE…`) to a forced fresh solve at the merge's own configuration, header included (`reference 149`, `S3-ba-unit`, `catmull-rom`), and the two render to the same bytes (`F12B14C4…`). Fact 1446's omitted key fields were not exercised on this bracket, so a pre-fix arm is not automatically a contaminated arm — but this can only be established per bracket, by re-solving, not assumed.
* **P24 — MEASURED. This retracts P2 and supersedes it.** M111's own +97.4σ is an artefact of its instrument, found by M111 in self-audit. Two independent defects: the null standard deviation was estimated from **three** translations (re-running the identical mask with 64 gives null sd 0.021 against 0.003, and the same effect reads **+11.6σ**); and the `flat` mask was a percentile of the arm under test. With the flat population held at the same 40% of the plane but chosen by an arm that cannot be conditioned on the outcome, the low-`n_eff` statistic falls to **0.904 (+1.2σ, rank p = 0.31)** on the gate-100000 mean arm and **0.989 (+0.5σ, p = 0.65)** on the single-frame control. Partitioning shows why: flat-in-render ∧ flat-in-control scores 1.428 (+10.4σ) and flat-in-control ∧ *not* flat-in-render scores **0.954 (−0.2σ)** — every cell that fires contains the render-flatness condition. **The claim that the visible defect is a luma step printed at election seams is withdrawn.** `experiments/M111-waxy-blobs/recheck.py`, `decompose.py`.
* **P25 — MEASURED. This is what survives of M111's headline.** With "the subject has no texture here" defined on the **single-frame control alone** (flattest 40%, 9×9 local sd ≤ 99.9 DN) and never on the render, the shipped render carries **6.1×** the local variation of that single frame in those regions (466.1 DN against 75.9 DN; the gate-100000 mean arm reads 62.6). A single frame is the noisiest thing available, so this is not explained by having averaged fewer frames. But the same seam detector on the same control-defined mask is **null** — whole plane 0.839 against a 0.911 ± 0.101 null (−0.7σ, p = 0.63), `blobB` interior 1.123 (+1.9σ, p = 0.046, one positive cell in five tests). **The excess structure is real and mask-independent; its attribution to election seams is not.** `experiments/M111-waxy-blobs/blob_interior.py`.
* **P26 — MEASURED.** ORCH's H7 (smooth regions admit the whole bracket, and averaging heterogeneous PSFs is an extra blur) is refuted on three of its four predictions, including the one it nominated as its discriminator. **P1** — blob plateaus are *smaller* than typical, not larger: `blobB` **33.2 px** area-weighted equivalent diameter against a control-chosen matched no-blob region's **30.0 px** and a whole-plane **92.5 px**, and `blobA`, which is not a defect, has the largest cells at 42.1 px. **P3** — `n_eff` inside the blobs is **median 2.0** and **mean 1.77**, against a plane mean of 81.9; it is low, not high. **P4** — tightening the gate makes the artifact monotonically *worse*, not better, with flat pixels electing 97.30% at gate 0.25 against 14.77% at the shipped 4.0. **P2 survives**: `blobB` seams jump a median of 3 frames with 17.9% jumping ≥ 10, against the matched control's 1 and 7.5%. H7 also shares H2's premise, which §2 measured false — winner response medians 4.305 and 2.961 against a 0.4777 noise ceiling. `experiments/M111-waxy-blobs/h7_orch.py`.
* **P32 — MEASURED.** The soft admission gate is built, opt-in and byte-inert. `crates/strehl-core/src/softgate.rs` implements `w = exp(−½((best − focus)/tol)²)` with `tolerance()` **bit-identical** to `Gate::tolerance()` (`threshold · √2 · FOCUS_NOISE_SD`, asserted across nine thresholds), `n_eff` as the **Kish** estimator `(Σw)²/Σw²` — the exact generalisation, since it returns the integer count on 0/1 weights — and a tail truncated at `WEIGHT_FLOOR = 1/65536`, i.e. `√(32 ln 2) = 4.7096` tolerances, derived rather than chosen. **18 tests green; a 5-mutation negative control catches 5/5** at exit exactly 101 with a SHA-256-verified byte-exact restore. **NC8:** the tree with the module and the tree with `softgate.rs` deleted and its `mod` line removed both render `DB7BAAD2…`, which is also M111's `a7bd05a` reference and ORCH's `marker-HEAD-8f46f04.tif`; `git grep softgate` outside the module returns only the `mod` line. The default path is byte-identical because nothing calls it, so **no byte-freeze breaks, no `DEFAULT_GATE` re-solve is forced, and fact 19's 0.534× keeps its scope.**
* **P33 — MEASURED. The fix's own falsifiable prediction holds.** With masks taken from the **single-frame control alone** (flattest 40% / sharpest 10% by 9×9 local sd, never from a render), the soft/boolean `n_eff` ratio is **1.59–2.14** in the flat-and-elected population — the seams — and **1.07–1.29** in texture. **The intervals are disjoint**, and both populations have boolean `n_eff` = 1.0, so the separation is entirely in the numerator and not an artefact of a differing denominator. Where the boolean gate already averages ≥ 64 frames the ratio is 0.77–1.37, i.e. the soft weight changes least where the merge was already doing the right thing. `experiments/M111-waxy-blobs/softgate_prediction.py`.
* **P34 — MEASURED.** A boolean `n_eff` map at gate *g* **is the per-pixel response-gap CDF** sampled at *g*, so a gate ladder evaluates **any** monotone kernel by Stieltjes summation with rigorous two-sided bounds — lower edge for the upper bound, upper edge for the lower — and **no new instrument is needed** to price a proposed weighting before building it. Validated against a known truth: a top-hat at one gate-4 tolerance reconstructs the gate-4 map with `max |diff| = 0` on the lower bound, and its upper-bound slack is **exactly** the gate-4→gate-5 count (`max |diff| = 0`, up to 296 frames). This prices `--photometric`-style proposals against existing dumps for the cost of a ladder.
* **P35 — MEASURED.** `through_focus.rs` already ships a posterior over frame-of-best-focus on the **identical calibrated temperature** as the merge gate — `temperature() = √2 · FOCUS_NOISE_SD` (line 313), with a doc comment stating the commensurability with `Gate::tolerance` deliberately — but on a **different kernel**: `through_focus.rs:371-373` computes `exp(−gap/T)`, **exponential**, while M111's `softgate.rs` computes `exp(−gap²/2T²)`, **Gaussian**. The codebase therefore now weights one z-axis three ways at one temperature: **top-hat** (`merge.rs`, shipping, decides bytes), **exponential** (`through_focus.rs`, diagnostic, `--stats` only), **Gaussian** (`softgate.rs`, opt-in, unreachable). The Gaussian is what a normal gap of sd `T` implies, which is what `FOCUS_NOISE_SD` was calibrated to describe; the exponential is heavier-tailed and admits far frames more readily — the direction that made `--gate 1e5` destroy the photograph. **That is an argument, not a measurement: both should be priced against the same ladder (P34) before either is integrated.**

* **P41 — MEASURED. Fact 1490 reproduces, and it is sharper than the advisory that relayed it.** On **pwsh 7.6.5**, reading `$LASTEXITCODE` after a pipeline truncated by `Select-Object -First` returns the *previous* command's code. Primed with `exit 0`, a truncated command whose true code is 7 reads **0** (false green); primed with `exit 5`, a truncated command whose true code is 0 reads **5** (false red). **Two refinements.** (a) **The stale value is retained verbatim, not coerced to 1** — the advisory's "reads 1" is an artefact of having primed with 1, so no particular value is the signature of a stale read and a gate cannot detect corruption by testing for one. (b) **`Select-Object -Last` is safe and `-First` is not**: `-Last` cannot emit until the stream ends, so the process is reaped and the same case reads the correct **7**. The mechanism is early termination, and the practical split is `-First` versus `-Last`. M111's own gates capture the code on the line immediately after the call and were additionally re-run under deliberate failure priming — `cargo check --workspace --all-targets` and the 18-test suite both read **0** while primed to **3**, so both reads were live and no number moved.
* **P42 — MEASURED.** M111's seven committed files carry **0** control characters under check S7 (fact 1489), and that null was only accepted after the instrument was shown to be live: planting a single `0x08` in place of `` `n `` inside `` `n_eff` `` — the exact defect fact 1488 describes — made an independent byte scan report 1 and made `corpus_lint` fail with S7 naming the byte, the column and the remedy. S15 was written with the single-quoted `@'…'@` form. **A clean S7 result on prose full of `` `n_eff` ``, `` `best_focus` `` and `` `experiments/…` `` is only evidence if the checker has been fired at least once on that same text.**
* **P44 — MEASURED. The short-circuiting variants of the cmdlets the fleet table cleared are safe, and the mechanism is visible in the wall-clock.** The narrowed fleet rule (facts 1507/1508) clears `Select-String` unqualified, but `-Quiet` and `-List` are the variants a pass/fail gate reaches for first and both are documented as stopping at the first match — so an unqualified clearance could have granted an unsafe shape. Measured on pwsh 7.6.5 under adversarial priming in **both** directions (prime 0 / true 7, and prime 5 / true 0), against a native command emitting 20 000 lines: `Select-Object -First 1` reads **0** and **5** — stale in both directions — while `-Last 1`, `Select-String`, `Select-String -Quiet`, `Select-String -List`, `Where-Object`, `ForEach-Object`, `Out-String -Stream` and the bare no-pipeline form all read the true code in both. **The table stands as ORCH wrote it, and extends to `-Quiet` and `-List`.** The decisive evidence is not the exit code but the **wall-clock**: every safe shape takes ~550 ms (the full emit), `-First 1` takes **16–30 ms** — a ~35× gap that dates the read to before the producer finished. cmd.exe also emits *“The process tried to write to a nonexistent pipe”* on the `-First` arms only, which is the early termination announcing itself. This confirms **early termination, not truncation**, is the trigger.
* **P45 — MEASURED. M111 writes nothing to `D:\`, by intent and not merely by present state.** Under the widened rule (`D:\` read-only in its entirety, discipline 771) the honest check is not “is there a scratch directory today” but “could any script of mine ever create one”. All **13** `D:\` references across M111's scripts are the *input* stack (`D:\personal\macro\dry-erase-marker-head-cpl` and `…\lavendar-cpl`), every one a read; all **8** `$root` definitions resolve to `C:\dev\strehl-out\M111`, and every `--out` argument is built from `$root` or a literal `C:\dev\strehl-out\M111\…`. `D:\` top level carries `m106-scratch` and `strehl-scratch-m98`, **neither mine**. Nothing to report and nothing to delete.
* **P46 — MEASURED (at source). ORCH's blur hypothesis for the halo correction is refuted twice over by measurements that already exist.** (a) `P24`/`P104`: a Catmull-Rom gather that destroys **~49% of gradient energy** moves the halo metric by **+0.6%** — ISO is a median *level* profile against distance, not a sharpness proxy. (b) `P57`/`P59`, Blur-Matched Fidelity: a Gaussian blur bisected until its COARSE-band suppression matches the correction's **exactly** needs **sigma = 5.108 px** and retains only **20.46%** of the FINE band, where the correction retains **90.58%** — **BMF = 4.428**. Read from `experiments/M87-occlusion/data/56-bmf.json`, not from the prose: `blur_coarse` 0.9145749511849404 against `coarse` 0.9145749511806655, matched to **4e-12**, so the race is properly run. **The correction is not blur.**
* **P47 — MEASURED (at source). The 87.9% / 84.6% headline is from a different pipeline than the one the owner would see.** M87 §16.9 states it plainly: everything in §6 and §16.1–§16.8 was measured on **ROI crops of an unaligned, gate-0 merge**. The shipped binary renders the **full frame, aligned, at gate 2**, and there the same correction scores **−72.9%** (ISO 0.06406 → 0.01734). Quoting 87.9% for the shipped path overstates it by **15 points** and attributes it to a render nobody has made.
* **P48 — MEASURED (at source). M87's own conclusion is *do not enable this*, and the later withdrawal explicitly preserved that conclusion.** §16.9 is titled *“why I am telling you not to enable it”* and records, by looking at the owner's own photograph: the hair fringe is *“replaced by a smooth, milky, scalloped band … larger, softer and more conspicuous than the halo it replaced. **It looks worse.**”* The §23.3 banner withdraws only the *mechanism* (“blur-grade destruction”) and states **the conclusion — do not enable this by default — stands**. M87's closing line: *“A default-on version of this would have been visible to the owner as damage in the morning.”*
* **P49 — MEASURED (at source). Registered bar V3 FAILS: the correction removes fine structure harder than it removes the veil.** FINE **0.905812** against COARSE **0.914575** — 9.42% of the fine band gone against 8.54% of the coarse band. `56-bmf.json` `bars` reads `V1 true, V2 true, V3 false, V4 true`, verified as JSON rather than transcribed. The defect is **selectivity**, and it is measured on the real full frame, which is the only place §16.9's miss could have been caught.
* **P50 — MEASURED (at source). The confound is silhouette-keying, not blur, and the ground-truth file states it more strongly than the prose does.** On the plant, `moved_frac` is **1.000 at every delta** on the **non-occluding** control against **0.394** on the real occluding scene — the treatment is **2.5× more aggressive on a scene containing no occlusion at all**. M87 §16.2: *“It keys on **silhouettes**, not on **occlusions**, and it cannot tell them apart.”*
* **P51 — MEASURED (at source). The non-occluding control's ISO dose-response is NON-MONOTONE, which reframes its one ‘good’ rung.** From `22-plant-truth.json`, ISO change against F0 at d10 / d20 / d40 is **−186.6% / −142.0% / +63.9%** — the treatment makes a region with almost no halo **2.9× worse** at low dose before ‘improving’ it at high dose — while band RMSE rises **monotonically** +215.9% / +354.4% / **+558.4%**. A mechanism that removes halo cannot do that. The d40 ‘−63.9% halo’ is the tail of a band rewritten into flatness, and the RMSE ladder is the honest reading of the same three arms. **This is the dose ladder ORCH asked for; it already exists, on ground truth, and it is pathological.**
* **P52 — MEASURED (at source). ISO cannot certify a reconstruction, by its author's registered bar.** Of four deliberately broken unmixings, ISO noticed **one**. The swapped-layer variant is wrong against truth by **six orders of magnitude** (RMSE **33117** against 0.0171) and ISO reads **0.00676** against the correct 0.00648 — indistinguishable. M87's governing rule, stated as binding on everything downstream: *“no halo-removal arm may be certified on ISO alone.”*
* **P56 — MEASURED. M111 is not exposed to the PIL 16-bit RGB hazard: **zero** `Image.open(` calls across all 33 files in the lane.** Every TIFF read in M111 is `tifffile.imread`; PIL is imported by exactly three scripts (`final_figs.py`, `gate_arms.py`, `state_panel.py`) and used only as `Image.fromarray`, `Image.new` and resampling constants — the **write** path, producing PNG contact sheets for human eyes, which is the harmless category. Audited by counting `Image.open(` call sites rather than by grepping for `PIL`, because a case-insensitive search for `PIL` matches the substring in *com***pil***ing* and returns a false hit from a code comment.
* **P57 — MEASURED. Had M111 used PIL, the headline defect would have been **understated by 8.7%**, and the bias points toward the null.** Recomputing the `blobB` statistic through both readers with every other line identical: the merged-against-control **boundary hardness** contrast falls from **6.105×** (tifffile) to **5.573×** (PIL), −8.7%; `blobA` falls **3.111× → 2.875×**, −7.6%. The mechanism is unequal, not uniform: the *small* quantity moves far more than the large one — the control's soft boundary p90 shifts **+10.5%** where the merged render's hard boundary shifts **+0.8%** — so the ratio between them compresses. Level counts confirm the loss: **62152 → 256** distinct levels on the merged file (**243×**) and 49028 → 245 on the control. The interior-flatness ratio is nearly immune (−0.0%, +3.0%), so the exposure is **statistic-dependent and not predictable from the file alone**.
* **P59 — MEASURED, pre-registered at commit `40da965` before the data existed. “A ratio of two arms on the same data” does not by itself confer protection against a narrowed reader; **the arms' magnitude disparity does.** 1547 tiles, 256 px, merged-over-control gradient p90 through `tifffile` against PIL, every other line identical. Median |shift| by disparity `D = max/min`: **0.68 % / 0.90 % / 3.79 % / 6.15 % / 6.71 % / 7.58 % / 8.04 %** across `D` bins [1.00,1.25) → [8,∞), **monotone in every step, in both mean and median**, Spearman rho **+0.530**. The two ends reproduce the two measurements that appeared to conflict: ORCH's **−1.0 %** sits at the comparable-arms end (0.68 %, n=58) and M111's **−8.7 %** at the disparate end (8.04 %), and M111's own statistic has **D = 6.105**. **A two-arm ratio can *be* a small-over-large ratio, so the two triage questions are not independent and the protective one can clear a statistic the hazardous one condemns.**
* **P60 — MEASURED. My diagnosis of my own failed gate was wrong, and I had registered it as falsifiable, so it was caught.** Run 1's gate failed (low-`D` mean 2.92 % against a < 2 % bar) and I attributed it to a heavy tail defeating the mean. I registered that account as gate **(c)** — *the lowest bin's mean will still exceed 2 %* — and it **FAILED**: at n=58 the lowest bin's mean is **1.89 %**, under the bar. The tail is real (mean exceeds median in **all seven** bins, 64.52 % against 8.04 % in the top one) but it is **not what sank run 1**. The real cause is the gate's own **bin boundary**: it averaged `D` < 1.5, and by `D` = 1.5 the arms already differ by half and the shift has climbed to 3.40 %. **My ‘low disparity’ band was too wide to mean what it said**, so the gate failed on threshold placement, not on statistic choice or sample size. With the strict lowest bin, mean and median **agree**, and the original mean-based gate would have passed.

**Disciplines**

* **P36.** **A bound that overlaps is not a refutation — it is an unresolved instrument, and a verdict with two outcomes cannot tell you which you have.** M111's first `n_eff` ladder sampled nothing between z = 1 and z = 4, exactly where the Gaussian falls 0.607 → 0.0003, so one bin spanned a factor of 1800 in weight and bounded nothing: seam 0.96–4.87 against texture 1.00–2.59. The verdict code called that **FAILED** and would have killed a live fix on a null detection from a blind probe. Give any bounded statistic **three** verdicts — separated, separated the other way, and *overlapping* — and when refining, check that the new interval **nests inside** the old one, which is the only cheap proof that refinement did not change the estimand.
* **P37.** **Never index a ladder, a sweep or an arm list by position.** M111's `boolean = maps[2]` was correct for a six-rung ladder where position 2 was gate 4.0; inserting two rungs silently moved it to the gate-2 map, with no error, no shape change and no failed assertion, corrupting both the ratio's denominator and the population definition that ratio described. Look the arm up **by its value**, and hard-error if it is not present exactly once.
* **P38.** **When a prediction is computed in one language and the fix ships in another, pin the shared function at the exact points the prediction used.** M111's `n_eff` interval was integrated in Python over fourteen ladder edges while the kernel ships in Rust; nothing structural keeps them in step. The cross-language test agrees to seven significant figures and is load-bearing — the wrong-kernel-width mutation trips it — and if it ever fails the published interval is **stale, not approximate**.
* **P39.** **In a working tree shared with other agents, a negative control's post-restore green leg can be turned red by somebody else's in-flight edit, and the control will report its own restore as failed.** M111's control restored `softgate.rs` byte-exactly — SHA-256 verified — and then read the suite red because another milestone's uncommitted work had stopped `strehl-core` compiling on `outlier::Discriminator::Shift`. Separate the two: assert the restore by **hash**, decide restore-failure by whether the breakage **names the file under test**, and give the environment case a **distinct exit code** so a harness fault can never be read as a measured hole. Verify the real answer in a `git archive HEAD` extraction with only the file under test overlaid — M111's 18/18 was confirmed that way while the live tree would not build.
* **P40.** **A control's assertion can be wrong in the direction of being too strong, and the fix is to pin the discrepancy exactly rather than loosen the check.** M111's top-hat ground truth demanded that *both* Stieltjes bounds reconstruct the gate-4 map and failed at 296 frames. The lower bound was exact; the upper bound legitimately over-counts one bin, because a top-hat is discontinuous on a ladder edge and is the loosest possible case for edge-evaluated bounds. Asserting `upper − lower == the gate-4→gate-5 count` exactly is strictly stronger than the assertion that failed, and it passes.
* **P43.** **Anchor a text edit on a complete line, never on a sentence prefix.** A prefix anchor that ends mid-sentence silently absorbs the remainder of the line into the replacement, and the damage reads as plausible prose rather than as a syntax error. M111 did this **three times in one session** on its own report: twice grafting an existing fact's tail onto a newly inserted bullet (P26 onto P40, P36 onto P42), and once deleting four words by replacing a prefix with a shorter prefix. None of the three produced an error, a failed match, or a `corpus_lint` violation — only reading the joined line aloud found them. This is the same failure as a mutation anchor that does not land, and it takes the same remedy: **match a full line, assert the anchor is unique, and assert the remainder begins where you expect.** M111's repair script caught its own wrong split point that way, on the assertion rather than on review.
* **P53.** **Before designing a control for a suspected confound, search the source for whether it has already been tested — the answer may be a registered prediction the author made in your direction and then falsified against themselves.** ORCH asked M111 to transfer the CA blur confound to the halo claim and to build the blur-matched arm. That arm already existed (`56-bmf.py`), was better designed than the one specified — it matches the blur on **achieved suppression** by bisection rather than on a guessed magnitude — and M87 had **pre-registered the prediction that its own correction would prove no better than a blur (BMF ≤ 1.05)**, then measured **4.43** and recorded the refutation of its own hypothesis. Building it again would have re-derived a dead hypothesis and left the four live defects (P47–P51) untouched. This is ORCH's own discipline 811 run forwards: **an estimator is not the only thing that can be correctly reporting an input you have not read.**
* **P54.** **A control arm must match the treatment on its REALIZED intervention, not on its nominal parameter — a parameter-matched arm that mostly misses under-treats, and therefore flatters the treatment.** ORCH proposed *forbidding the far frames instead of the near ones* as a blur-matched null, on the grounds of *“same number of frames excluded”*. It is not: the treatment forbids `|k − k_F| < 40`, a **79**-frame band of 299, so forbidding the complement excludes **220** — **2.8× as many**. Worse, the mechanism is that near-silhouette background pixels **inherit the foreground's election**, so the near band is aimed precisely at the frames those pixels actually elect; a band placed anywhere else mostly misses, changes few elections, and pays little of the incidental cost it was built to reproduce. **Same bias structure as the tangential placebo (disciplines 815–816), and it points the same way — toward vindicating the treatment.**
* **P55.** **A guard that checks a report against constants written into the guard has not touched the source; plant in BOTH directions or the source-reading arm stays untested.** `halo_claim_guard.py` reads each number from M87's JSON and pins it to its own fact row. Seven planted report defects — last-digit edits, a flipped bar verdict, an off-by-one count — were **all caught, and all by the literal-presence arm**, which short-circuits before the numeric comparison. **7/7 green, and the only arm that actually opens the source file had never once fired.** It took three further plants into a *copy* of the source JSON to show that arm was live. The literal arm alone would have passed unchanged if M87's data were replaced wholesale. **A multi-arm check reports the disjunction, so an arm that never fires is indistinguishable from an arm that cannot.**
* **P58.** **A reader that silently narrows bit depth biases results toward the null, because quantisation noise inflates small quantities proportionally far more than large ones and therefore compresses every large-over-small ratio toward 1.** This is the direction that manufactures a **false clean null**, which is the hardest error to notice — nobody re-examines an arm that came back showing no effect. Measured here at +10.5% on the small term against +0.8% on the large one in the same statistic. **So the triage question is not “was my input 16-bit” but “does my statistic divide a small quantity by a large one”**: M111's interior-flatness ratio survived 8-bit truncation almost exactly while its boundary-hardness contrast — computed from the *same pixels, in the same script* — lost 8.7%. Per ORCH's notice, the one-line prophylactic is to assert the dtype immediately after loading.
* **P61.** **“Protected by cancellation” is a property of the two arms' magnitude ratio, not of the statistic being a ratio of two arms.** Quantisation adds a roughly constant *absolute* floor to both arms, so it is a comparable *fraction* of each — and therefore cancels — only when the arms are comparable in size. Measured: protection is near-total at `D` < 1.25 (**0.68 %**) and gone by `D` > 8 (**8.04 %**), monotone throughout (P59). **State the triage rule as a question about the ratio of the terms, not about the form of the expression**, or it will clear exactly the statistics that a strong-against-weak contrast is made of — which is most defect-detection statistics, since a defect is usually the large term and the clean baseline the small one.
* **P62.** **When a pre-registered gate fails, register your *explanation* of the failure as its own falsifiable prediction before re-running — otherwise the re-run's design silently encodes the diagnosis you have not tested.** Switching from mean to median after seeing run 1 would have produced the answer I wanted with no evidence that my reason was right. Registering the diagnosis as gate (c) cost one line and **refuted it** (P60): the tail existed but the bin boundary was the actual fault. **A failed gate tells you the gate failed; it does not tell you why, and the why is what you carry into the next design.**

---

## 11. Reproduction

Everything is in `experiments/M111-waxy-blobs/`, run in this order:

| script | what |
| --- | --- |
| `audit_probe.py` | the inherited probe's registration, tone and clipping audit (§1.5) |
| `render_baseline.ps1` | reproduces ORCH's bytes; NC4 in the pinned build |
| `state_panel.py` | the merge's state at ORCH's two ROIs, with contact sheets |
| `quantify.py` | the pooled test and its null (§4.1) |
| `sweep_radius.ps1` + `mechanism.py` | arm E, the H1 causal test (§4.3), and the admission curve (§2) |
| `sweep_gate.ps1` + `gate_arms.py` | arm F, the dose-response (§4.4), and NC3 |
| `attribution.py` | the difference-image attribution (§4.2), marker and lavendar |
| `arms_lavendar.ps1` + `final_figs.py` | the generality arm and the census (§9.1) |
| `seam_continuity.py` | the fix's premise (§4.5) |
| `orch_probe_arms.py` | ORCH's statistic across selection arms (§7) |
| `nc4_live_nonperturbation.ps1` | NC4 in the tree being committed |
| `nc6_planted_mutation.ps1` | NC6, exact exit codes 101 then 0 |
| `cache_control.ps1` + `make_poison.py` | NC7 on `marker`, four arms (§12) |
| `cache_control_lavendar.ps1` | NC7 on `lavendar`, forced fresh solve (§12) |
| `reg_radius.patch` | arm E's deliberately unshipped override |
| `recheck.py` | the self-audit's 64-translation null and matched-population masks (§13.1, §13.2) |
| `decompose.py` | the circularity-versus-dilution partition (§13.2) |
| `blob_interior.py` | what survives with no render-derived mask (§13.3) |
| `h7_orch.py` | ORCH's H7, predictions P1-P4 (§14) |
| `softgate_negctl.py` | the module's 5-mutation control, 5/5 (§15.1) |
| `nc8_byte_inert.ps1` | NC8, the two-arm byte-identity proof that the module is opt-in (§15.2) |
| `refine_ladder.ps1` | the eight extra gate rungs the `n_eff` bound needed (§15.3) |
| `softgate_prediction.py` | the `n_eff` prediction and **both** its negative arms (§15.3, §15.4). Run `test`, `control-tophat` and `control-swap`; all three must pass. |

Heavy artifacts are under `C:\dev\strehl-out\M111\` and are not in Git.
Figures worth looking at: `_STATE-blobB-row2.png`, `_ARMS-blobB.png`,
`_M111-headline.png`.

---

## 12. NC7 — the cache-contamination control (fact 1446)

Fact 1446: `StackIdentity` keys the frame set but **not `reference` and not
`resampler`**, so an identical command line can be served bytes solved under a
different configuration depending on what ran earlier in the tree.

**This milestone is squarely in the window.** M97's fix landed at `69f7b4c`,
**13:41**. Every M111 measurement arm rendered between **13:12 and 13:32**, on
the pre-fix binary. The fix does not exonerate anything here and the question
had to be answered by measurement.

### 12.1 The split, read off the renderer's own logs

`merge_cmd.rs`'s `alignment_for` returns early to
`align_cmd::load_or_solve` — the function fact 1446 poisons — **only when
`STREHL_WARPMAP` is unset**. The provenance string in the log distinguishes the
two paths exactly:

| arms | log line | path taken |
| --- | --- | --- |
| all 15 `marker` arms | `alignment: ON (sidecar-override), reference frame 149` | pinned file; `load_or_solve` never called |
| both `lavendar` arms | `alignment: ON (sidecar), reference frame 149` | **the cache path — exposed** |

So the arm carrying the 97σ finding took a different code path from the arm that
was exposed. Both were tested anyway, because a log line is a transcript claim
and ORCH's instruction was to run the control rather than argue from it.

### 12.2 `marker` — four arms, two of which had to be red

ORCH's literal prescription (`align --reference <other frame>` between arms) is
not run: `strehl align` writes sidecars and `D:\personal\macro` is strictly
read-only, the same objection M109 recorded. The substitute reproduces fact
1446's *effect* exactly — a sidecar that passes every identity check strehl
makes (same stack name, digest, frame count, plane) and places 298 of 299 frames
2.0 plane px elsewhere, which is precisely what a foreign-`reference` cache entry
is. `make_poison.py` hard-errors if it rewrites zero frames.

| arm | `STREHL_WARPMAP` | `STREHL_CACHE_DIR` | SHA-256 | provenance |
| --- | --- | --- | --- | --- |
| **A0 baseline** | pinned | empty | `DB7BAAD2…` | `sidecar-override ref=149` |
| **A1 red** | **poison** | empty | `0D41E08B…` | `sidecar-override ref=149` |
| **A2 green** | pinned | **poisoned** | `DB7BAAD2…` | `sidecar-override ref=149` |
| **A3 exposure** | **unset** | **poisoned** | `0D41E08B…` | `sidecar ref=149` |

* **A0** reproduces the reported render, so the control is scoring the real thing.
* **A1** moves the bytes, so the substitution is live — without this, A2's green
  would mean nothing (discipline 722).
* **A3** moves the bytes *to exactly A1's hash*. The poisoned cache entry was
  found, read, and produced bit-for-bit what pointing the override at the same
  file produces. This is the arm that proves the poison was reachable on the
  vulnerable path at the filename the pre-fix key computes.
* **A2** is unmoved with the same poisoned cache sitting there.

**`STREHL_WARPMAP` wins over the cache, and a cache poisoned by fact 1446's
exact mechanism cannot move M111's marker bytes.** The pinned sidecar is also
SHA-256 identical (`1864A370…`) to the cache entry it was copied from, so even
the counterfactual arm that *did* consult the cache would have got the same
warps.

### 12.3 `lavendar` — the exposed arm, tested by forced re-solve

| arm | `STREHL_CACHE_DIR` | provenance | render SHA-256 | seconds |
| --- | --- | --- | --- | --- |
| **L0 cached** | real cache | `ON (sidecar)` | `F12B14C4…` | 110 |
| **L1 fresh** | empty | **`ON (solved)`** | `F12B14C4…` | 169 |

L1 genuinely re-solved — the log says so and it cost 59 s more — and the sidecar
it wrote is **byte-identical** to the entry L0 consumed (`4D454CCE…`), header and
all: `reference 149`, `strategy S3-ba-unit`, `resampler catmull-rom`. The renders
match. The cached entry *is* a fresh solve at the configuration the merge asks
for, so the omitted key fields were never exercised.

Liveness for this arm is inherited from A3, which showed that a poisoned entry
**on this exact code path** changes the output hash. The match is a measurement,
not a silence.

### 12.4 Verdict

**NC7 PASSES on both stacks. No M111 number is contaminated, and the control
could have fired: two of its four arms are red by construction and both fired.**
Neither read-only corpus directory gained a non-`.ARW` file.

One incidental corroboration: both solvers' own headers report
`plane 3520x2344`, independently confirming P20's grid finding against fact
1445's 3516×2344.

---

**Not self-verified.** Rule 12. The claims that most need an independent eye are
§4.2's difference-image attribution — because it is the only arm that carries
the finding — and §8.2, which is an argument and is labelled one.



---

## 13. Self-audit — the headline was overstated, and here is the corrected number

I set out to audit ORCH's probe (§7) and charged fact 1444 with mask
circularity. Reviewing my own `attribution.py` afterwards, I found the same
defect in it, plus a second one that is worse. This section supersedes §2 and
§4.2. `experiments/M111-waxy-blobs/recheck.py`,
`experiments/M111-waxy-blobs/decompose.py`,
`experiments/M111-waxy-blobs/blob_interior.py`.

### 13.1 Defect one — a standard deviation from three samples

`attribution.py` line 45:

```python
SHIFTS = [(137, 211), (-263, 89), (451, -337)]
```

Three translations, then `np.std(..., ddof=1)` over the three resulting ratios,
then divide. The sd came out at **0.0025**, and 0.246/0.0025 is 97. **The
sigma measured the sample size of my null, not the strength of my effect.**
Re-running the byte-identical mask and statistic with **64** translations:

| null size | null mean | null sd | reported significance |
| --- | --- | --- | --- |
| 3 (as published) | 1.002 | **0.003** | **+97.4σ** |
| 64 (corrected) | 1.011 | **0.021** | **+11.6σ** |

A 64-sample null also admits a **rank** p-value — how many nulls are at least as
extreme — which cannot be inflated by an underestimated sd. It bottoms out at
1/65 = **0.015**, and that is the strongest claim 64 translations can license.
Every "σ" in this report that came from `attribution.py` should be read as "at
most p = 0.015, effect size as tabulated".

### 13.2 Defect two — the mask is the arm under test

`attribution.py` line 118: `flat = (local_sd(y4) < FLAT_SD) & inner`, where `y4`
is the gate-4 arm. Re-scoring with the flat population held at the same **40%**
of the plane but chosen by each of three arms in turn:

| `flat` defined on | low (`n_eff ≤ 8`) ratio | null | σ | rank p |
| --- | --- | --- | --- | --- |
| **gate 4 — the arm under test** | **1.257** | 1.011 ± 0.021 | +11.6 | 0.015 |
| gate 1e5 mean — no selection | **0.904** | 0.836 ± 0.058 | **+1.2** | **0.31** |
| single frame — ORCH's control | **0.989** | 0.935 ± 0.098 | **+0.5** | **0.65** |

**The effect requires the mask to come from the arm under test.** Note the
population fraction is matched across all three rows, so this is not a
sample-size artefact — `attribution.py`'s absolute 300 DN threshold would have
selected 39.9% of the gate-4 arm and 81.5% of the softer mean arm, which is a
second, independent reason its mask swap could not have been read.

Partitioning the low-`n_eff` population settles whether that is circularity or
dilution:

| partition | n | ratio | null | σ |
| --- | --- | --- | --- | --- |
| flat in render **and** in control | 119 817 | 1.428 | 1.006 ± 0.041 | +10.4 |
| flat in render, **not** in control | 221 782 | 1.169 | 1.010 ± 0.019 | +8.1 |
| flat in control, **not** in render | 652 951 | 0.954 | 0.966 ± 0.050 | **−0.2** |

Every cell that fires contains the condition *flat in the render*; the one cell
that omits it is null. That is the signature of conditioning on the outcome, and
the mechanism is not subtle: restricting to pixels the render made flat
suppresses the off-seam denominator harder than the on-seam numerator, so the
ratio rises whether or not selection drew the seam.

### 13.3 What survives, measured with no render-derived mask at all

Define "the subject has no texture here" on the **single-frame control alone**
(flattest 40%, 9x9 local sd <= 99.9 DN) and never on the render. Then:

| region | control sd | mean-arm sd | gate-4 sd | gate-4 / control |
| --- | --- | --- | --- | --- |
| whole plane, control-smooth | 75.9 | 62.6 | **466.1** | **6.1x** |
| whole plane, control-textured | 497.7 | 174.4 | 1814.5 | 3.6x |
| `blobB` interior | 88.5 | 167.1 | 511.5 | 5.8x |
| `blobA` interior | 90.6 | 71.7 | 611.8 | 6.8x |
| matched no-blob interior | 89.9 | 374.0 | 3103.1 | 34.5x |

**In regions the single frame says are textureless, the shipped render carries
6.1x the local variation of that single frame.** A single frame is the noisiest
thing available — one exposure, one noise realisation — so this cannot be
explained by having averaged fewer frames. This is ORCH's "inventing structure
that is in no input frame", measured with no circular mask. It is the one part
of the headline that is clean.

**But it is not localised to the blobs, and it is not at election seams.** The
same seam detector, on the same control-defined masks:

| population | n | ratio | null | σ | rank p |
| --- | --- | --- | --- | --- | --- |
| whole plane, control-smooth | 3 017 727 | 0.839 | 0.911 ± 0.101 | −0.7 | 0.63 |
| `blobB` interior | 11 955 | 1.123 | 0.983 ± 0.072 | **+1.9** | 0.046 |
| `blobA` interior | 2 603 | 0.825 | 0.978 ± 0.266 | −0.6 | 0.56 |
| matched no-blob interior | 8 850 | 0.945 | 1.010 ± 0.139 | −0.5 | 0.60 |
| control-smooth but rough in render | 301 773 | 1.002 | 0.985 ± 0.019 | +0.9 | 0.32 |

`blobB`'s +1.9σ is the only positive cell and it would not survive correction
for the five tests in the table. **The proposition "the visible defect is the
luma step printed at election seams" is not supported once the mask is honest.**

### 13.4 What that leaves standing, and what it does not

**Stands** — none of these used the null or a render-derived mask:

* The admission collapse in §2 (mean `n_eff` 275.5 -> 1.6 as response goes
  0.6 -> 5). It is a direct reading of `n_eff` against `best_focus` from the
  state dump.
* **6.1x excess local variation** in control-smooth regions (§13.3).
* **H1 refuted** — the radius sweep is an arm-to-arm comparison of plateau
  diameters (54.0 px at radius 0 vs 60.3 shipped) and of amplitudes that are
  indistinguishable from one another (1.213 / 1.239 / 1.203) across a 32x range.
* **H2 refuted** — median `n_eff` 285 in the weakest band, 151 across flat.
* **P6** — `blobA` is not a defect (1.477 shipped vs 1.468 control, ORCH's own
  statistic).
* **§12 NC7** — hash comparisons, no statistics at all.

**Falls:** P2 as written, the +97.4σ, the +37.5σ variant on the shipped image,
and the claim in §2 that the plateau seams "print into the image" as the visible
defect. §8.2's proposed soft gate was motivated by that claim and is now
**unmotivated as well as unbuilt** — it should not be implemented on this
report's evidence.

**Unsettled and honestly so:** what does produce the 6.1x excess variation, if
not seams. It is spatially broad rather than seam-localised, which points at
per-frame noise and PSF differences being carried through selection rather than
at the plateau boundaries themselves — but that is a hypothesis, not a
measurement, and M111 did not test it.

---

## 14. H7 (ORCH's PSF-heterogeneity hypothesis) — REFUTED on three of its four predictions

H7: in smooth regions all frames score near-zero focus, so the gate admits the
whole bracket, and averaging frames with different PSFs is an extra blur.
`experiments/M111-waxy-blobs/h7_orch.py`. The matched no-blob region was chosen
from the **single-frame control alone**, by relative distance in (mean luma,
mean |grad|), before any map was read, as ORCH required; it landed at plane
(424, 1984), luma 33 988.8 against `blobB`'s 34 145.5 and |grad| 1238.2 against
1233.5.

**H7 shares H2's premise, and §2 already measured that premise false.** Inside
both ROIs the winner's response medians are **4.305** and **2.961** against a
pure-noise ceiling of **0.4777** — 9.0x and 6.2x the ceiling. The frames there
are *not* all scoring near-zero, so the gate is not admitting the bracket for
the reason H7 gives.

| prediction | H7 predicts | measured | verdict |
| --- | --- | --- | --- |
| **P1** cells markedly larger in blobs | larger | `blobB` **33.2 px**, matched control **30.0 px** (1.11x), whole plane **92.5 px** | **REFUTED** |
| **P2** blob seams jump many frames | many | `blobB` median **3**, **17.9%** jump >= 10 frames, only **29.8%** single-frame; control median **1**, 7.5%, 68.4% | **SURVIVES** |
| **P3** `n_eff` high inside blobs | high | `blobB` median **2.0**, `blobA` mean **1.77**, plane mean 81.9 | **REFUTED** |
| **P4** tightening the gate shrinks blobs | shrink | tightening makes it **worse**: gate 0.25 -> **97.30%** of flat pixels elect, amplitude 1.264, visually the hardest arm | **REFUTED, wrong sign** |

P1 is refuted twice over: the blobs' plateaus are *smaller* than the plane
average, and `blobA` — which §7.3 shows is **not** a defect — has the **largest**
cells of the three at 42.1 px. Cell size does not track the defect.

P4 is H7's own nominated discriminator ("no change is a kill"). It is worse than
no change: the artifact grows monotonically as the gate tightens, across
0.25 -> 1 -> 4 -> 16 -> 64 with flat pixels electing 97.30% -> 50.63% -> 14.77%
-> 5.76% -> 1.67% -> 0.00%.

**Two corrections to the brief that dispatched H7.** (a) P3 was described as
blocked on an `--n-eff-map` from M97. It is not — per-pixel `n_eff` shipped in
this milestone's own `dump.rs` at `fc4cbf6`, and the P3 row above is measured
from it. (b) The plane grid is **3520x2344** for this bracket, not fact 1445's
3516x2344; see P20.

P2 surviving is worth keeping. It says blob seams are genuinely large index
jumps, which is a real property of the map — but P1, P3 and P4 between them say
that property is not what the eye is reacting to.

---

## 15. The soft admission gate — built, opt-in, byte-inert, and its prediction tested

Commissioned after S8.2 and S13. This section is the deliverable: a module, a
falsifiable prediction tested before any image was rendered, an exact
integration specification I did **not** apply, and one finding I did not expect.

### 15.1 What was built

`crates/strehl-core/src/softgate.rs`, new, owned by nobody else, plus the one
`pub mod softgate;` line in `lib.rs`. Both went in a **single** commit, because
S10's P19 says a new module is two artefacts and committing only the tracked
one leaves `HEAD` un-buildable.

The weight is

```
w(focus, best) = exp( -0.5 * ((best - focus) / tolerance)^2 )
```

with `tolerance()` **bit-identical** to `Gate::tolerance()` —
`threshold * SQRT_2 * FOCUS_NOISE_SD`, asserted equal across nine thresholds by
`the_tolerance_is_bit_identical_to_the_boolean_gates`. That identity is the
constraint M81's rejected route broke, and it is the reason a soft weight can be
dropped in without re-deriving `FOCUS_NOISE_SD`'s meaning.

Three details are not cosmetic:

* **`n_eff` is Kish, `(sum w)^2 / sum w^2`, not `sum w`.** These agree on 0/1
  weights, so every test I had written passed under either. I found the hole by
  asking what the boolean estimator would have to reduce to, not by running a
  mutation — and then planted the mutation to prove the test now holds it.
* **The tail is truncated where a frame can no longer move a `u16`**, at
  `WEIGHT_FLOOR = 1/65536`, giving `cutoff_tolerances() = sqrt(32 ln 2) =
  4.7096`. Derived, not a magic number.
* **A frame scoring *above* the winner is not penalised.** The Gaussian is
  symmetric and would otherwise down-weight a better frame; `weight` returns 1.0
  for a non-positive gap, matching `admits`. NaN earns 0.0, also matching.

**Tests: 18, all green.** **Negative control: 5 planted mutations, 5/5 caught**,
each at exit exactly 101, restore verified byte-exact by SHA-256
(`F6E238AC8EBD5A27...`), post-restore suite green.

### 15.2 It is opt-in, and that is measured, not asserted

**NC8.** Arm S is the tree with the module present; arm N deletes `softgate.rs`
and removes the `mod` line. Both render
`DB7BAAD2FDC5BF74309B132D0DDEB1A681609037312E76923C2B22703BA1DDDC` — which is
also this milestone's original `a7bd05a` reference hash and ORCH's
`marker-HEAD-8f46f04.tif`. `git grep softgate` outside the module returns only
the `mod` line, so the code is statically unreachable from any render path. The
default is byte-identical because nothing calls it yet.

That is the whole point of the shape ORCH asked for: no `stack`/`merge`
byte-freeze breaks, no `DEFAULT_GATE` re-solve is forced, and fact 19's 0.534x
keeps its meaning, because the boolean gate is still the default.

### 15.3 The `n_eff` prediction — HELD, and the instrument was shown to be live

ORCH asked for a falsifiable pre-render prediction: a soft weight should raise
`n_eff` **at seams** without raising it **in texture**.

**No new instrument was needed.** The boolean `n_eff` map at gate `g` counts the
frames whose response gap is within `g` tolerances of the winner — so it *is*
the per-pixel gap CDF sampled at `g`. A gate ladder therefore yields any
kernel-weighted sum by Stieltjes summation, and because the Gaussian is monotone
decreasing, evaluating each bin at its lower edge is a rigorous **upper** bound
and at its upper edge a rigorous **lower** bound.

Masks are taken from the **single-frame control only** — flattest 40% and
sharpest 10% by 9x9 local sd — never from any render, per S13's P28 and
discipline 752.

| population | boolean `n_eff` | soft `n_eff` bounds | ratio |
| --- | --- | --- | --- |
| flat, and the merge **elected** (the seams) | 1.0 | 1.59 - 2.14 | **1.59 - 2.14** |
| flat, and the merge already averaged >= 64 | 284.0 | 217.63 - 388.97 | 0.77 - 1.37 |
| **textured** | 1.0 | 1.07 - 1.29 | **1.07 - 1.29** |
| whole inner plane | 2.0 | 2.49 - 4.04 | 1.25 - 2.02 |

**The seam and texture intervals are disjoint: 1.59 > 1.29.** Both populations
have boolean `n_eff` = 1.0, so the separation is entirely in the numerator and
cannot be an artefact of a differing denominator. The prediction **HELD**.

**First run said the opposite, and it was my instrument.** A six-rung ladder
sampled nothing between z = 1 and z = 4 — exactly where the Gaussian falls from
0.607 to 0.0003 — and one bin spanning a factor of 1800 in weight bounded
nothing: seam 0.96 - 4.87 against texture 1.00 - 2.59, overlapping. My verdict
code called that **FAILED**. It was not a refutation, it was an unresolvable
instrument, and reporting it would have killed a live fix on a null detection
from a blind probe. Eight more rungs (gates 2, 3, 5, 6, 8, 10, 12, 14) resolved
it, and the refined intervals **nest inside** the coarse ones — the check that
refining the ladder did not change the estimand. The verdict logic now has three
outcomes, not two, and names overlap as the ladder's resolution.

**A second defect in the same script, found the same way.** `boolean = maps[2]`
was a *positional* index, correct for the six-rung ladder where position 2 was
gate 4.0. Inserting gates 2 and 3 silently moved it to the **gate-2** map, with
no error and no shape change, corrupting both the ratio's denominator and the
seam population's own definition. It is looked up by gate **value** now, with a
hard error if the ladder does not contain gate 4.0 exactly once.

### 15.4 The controls that could have killed 15.3

Two arms, both required to pass, both wired into the same script so they cannot
drift from what they test.

**`control-tophat` — discipline 751 exactly.** Replace the Gaussian with the
boolean gate's own top-hat and leave the masks, the bins, the Kish estimator and
the verdict logic standing. The mechanism under test is the kernel's *shape*, so
this disables it and nothing else. Result: ratio **1.00 - 1.00** in texture,
**1.00 - 2.00** at seams, verdict **UNRESOLVED**, and soft `n_eff` exceeds
boolean on **0.00%** of the plane against 20.98% for the Gaussian. The
separation is caused by the kernel and not by the bookkeeping.

This arm also carries a **known ground truth**, which is the only reason to
trust the Stieltjes arithmetic at all: a top-hat at one gate-4 tolerance *is*
the gate-4 map, so the lower bound must reconstruct it exactly. It does —
`max |diff| = 0` — and the upper bound's excess is **exactly** the gate-4 to
gate-5 count, `max |diff| = 0`, up to 296 frames. The bin counts are right.

My first version of that assertion demanded **both** bounds reconstruct exactly
and failed at 296. The assertion was wrong, not the measurement: the top-hat is
discontinuous on a ladder edge, which is the loosest possible case for
edge-evaluated bounds. I pinned the slack exactly rather than loosening the
check.

**`control-swap` — the verdict logic is wired to the populations it names.**
Exchange the flat and textured masks and the verdict must invert. It does:
**REFUTED (disjoint, wrong order)**. So the script can report a refutation; a
HELD is not the only thing it can say.

### 15.5 The prediction was computed in Python and the fix ships in Rust

Nothing structural keeps those two in step, and the field numbers above are
worthless if they drift. `the_kernel_agrees_with_the_python_that_computed_the_field_prediction`
pins the Rust kernel at the **fifteen exact ladder edges the prediction
integrated over**. The two independent implementations agree to seven
significant figures at the tightest rung — Rust `0.000_015_261_641`, Python
`0.000_015_262` at z = 4.7096, which sits just *below* the cutoff 4.709_640 and
is therefore tapered, not truncated. The mutation control confirms the test is
load-bearing: M1 (wrong kernel width) trips it.

If that test ever fails, the published interval in 15.3 is **stale**, not
approximate.

### 15.6 The integration point — specified, NOT applied

`merge.rs` is M97's lane and I have not touched it; `git status` confirms it and
`merge_cmd.rs` are clean of me. This is the hand-off.

All line numbers are `Estimator::fold_inner`, `crates/strehl-core/src/merge.rs`.

| # | line | current | replacement |
| --- | --- | --- | --- |
| 1 | 746 | `let admitted = winner \|\| self.gate.admits(regularised[i], self.best_focus[i]);` | `let w = self.soft.weight(regularised[i], self.best_focus[i]);`<br>`let w = if winner { w.max(1.0) } else { w };`<br>`let admitted = w > 0.0;` |
| 2 | 765 | `self.sum[s][i] += v as f32;` | `self.sum[s][i] += w * v as f32;` |
| 3 | 782 | `self.luma_sum[i] += luma;` | `self.luma_sum[i] += f64::from(w) * luma;` |
| 4 | 785 | `self.n[i] += 1;` | `self.wsum[i] += w;  self.wsq[i] += w * w;` |
| 5 | 824-826 (`absorb`) | `self.n[i] += other.n[i];` | `self.wsum[i] += other.wsum[i];  self.wsq[i] += other.wsq[i];` |
| 6 | 932 | `self.sum[s][i] / n as f32` | `self.sum[s][i] / self.wsum[i]` |
| 7 | 536 (`n_eff`) | returns `&self.n` | `self.wsum[i] * self.wsum[i] / self.wsq[i]` |

Two new `Vec<f32>` fields, `wsum` and `wsq`, sized like `n`, allocated where `n`
is and reduced in `absorb` alongside it. `self.soft: SoftGate` is constructed
from the same threshold the `Gate` is.

Four things a reviewer should check, because they are where this breaks:

* **The winner must be pinned to weight 1.0** (row 1). Its gap is zero so the
  Gaussian already returns 1.0, but `max` makes the invariant explicit rather
  than dependent on `best_focus[i]` being exactly the winner's response.
* **Row 3 is easy to miss.** `disagreement()` at line 882 divides
  `luma_sum` by `n`; if `luma_sum` becomes weighted and its divisor does not,
  the noise diagnostic silently changes meaning. Either weight both or leave
  both alone.
* **`n_eff()` returns `&[u16]` today.** Row 7 changes its type, which is a
  ripple beyond `merge.rs`. The cheap alternative is a second accessor and
  leaving `n_eff` as the boolean count.
* **This is gated on the flag, and the boolean path must remain the default**,
  or every byte-freeze in the corpus breaks at once.

### 15.7 Is it a posterior? Yes — and the codebase already has one

ORCH asked whether the construction is naturally a posterior over
frame-of-best-focus. It is: `posterior()` normalises the weights to sum to one,
`entropy()` reads 0 when one frame wins and `ln n` when all tie, and the
threshold acts as a **temperature** — all three are tests.

**But the more useful answer is that I built the third kernel over the same
axis, and I did not know it until after the module was written.**
`through_focus.rs` already ships a posterior on the **identical temperature
scale**. Its `temperature()` at line 313 is `SQRT_2 * FOCUS_NOISE_SD` — the same
expression as my `tolerance()` at threshold 1 — and its own doc comment says it
matches `Gate::tolerance` at threshold 1 "so the soft posterior and the hard
gate are on one scale by construction". It has `posterior_perplexity()`,
explicitly commensurable with `Estimator::n_eff`.

The kernels differ. `through_focus.rs:371-373` computes `u = (regularised -
anchor) / t; e = u.exp()` — that is **`exp(-gap/T)`, exponential**. Mine is
**`exp(-0.5 (gap/T)^2)`, Gaussian**. So the merge now has three weightings of
one z-axis at one calibrated temperature:

| kernel | where | status |
| --- | --- | --- |
| top-hat | `merge.rs` `Gate::admits` | **shipping**, decides output bytes |
| exponential `exp(-gap/T)` | `through_focus.rs` fold | diagnostic only, built under `--stats` |
| Gaussian `exp(-gap^2/2T^2)` | `softgate.rs` | new, opt-in, unreachable |

**I am not claiming the Gaussian is the right one.** A Gaussian is what you get
if the response gap is normal with sd `T`, which is exactly what
`FOCUS_NOISE_SD` was calibrated to describe, so it is the choice the existing
noise model implies. The exponential is heavier-tailed and admits far-off frames
more readily — the direction that made `--gate 1e5` destroy the photograph. That
is an argument, not a measurement, and **whoever integrates this should price
both against the same ladder before choosing.** The machinery in 15.3 evaluates
any monotone kernel with a one-line change.

This is adjacent to the pattern fact 1442 records. The instrument was not
duplicated — the export I needed existed and I checked before writing code — but
the *concept* was, twice, by two milestones, in one file neither had read. The
scale being identical by explicit design and the kernels differing silently is
the part worth folding.

### 15.8 The boundary of the design space, measured

Both alternatives are dead ends and both were measured, not argued:

* **Opening the gate removes the defect and the photograph together.** At
  `--gate 100000` flat pixels electing falls 14.77% -> 0.00%, and
  plateau-interior sd falls **153.5 -> 74.2**. S4.4.
* **Rescaling the tolerance by local response is M81's route and it failed 0/5
  stacks.** It did not preserve `FOCUS_NOISE_SD`'s unit. The soft gate does, by
  construction and by test.
* **Tightening the gate makes it monotonically worse**, not better — 97.30% of
  flat pixels elect at gate 0.25. S14 P4.

The soft weight is the only direction left that does not move the default.

### 15.9 What I did not do

* I did not edit `merge.rs`, `merge_cmd.rs`, or any file another agent owns.
* I did not move `DEFAULT_GATE`, re-solve it, or restate fact 19.
* I did not render an image with the soft gate on — it is unreachable by
  construction, which is what makes 15.2 provable. **The prediction in 15.3 is
  therefore a prediction, not a result**, and the first render through the soft
  path is the arm that can still falsify it.
* I did not verify any of this myself beyond the controls stated. `softgate.rs`
  is written to be verifiable independently: 18 tests, a 5/5 mutation control,
  and a three-arm field script with two negative arms.

---

## 16. Fleet-correction audit — neither correction moves a number in this report

Two corrections arrived after S15 was committed at `2ae2944`. Both were applied
as an audit rather than assumed to be inapplicable, and the audit is recorded
here because "it did not affect me" is a claim that needs evidence like any
other.

### 16.1 Backtick-eating here-strings (fact 1488, check S7) — CLEAN, and the check was proven live first

S15 was appended with a here-string, and it is dense with exactly the
identifiers at risk: `` `n_eff` ``, `` `best_focus` ``, `` `absorb` ``,
`` `tolerance` ``, `` `experiments/…` ``, `` `regularised` ``. In a
double-quoted `@"…"@` every one of those loses its backtick **and its first
letter**.

An independent byte scan of all seven files this milestone committed found
**0 control characters**. That is a null result from an instrument nobody had
shown to be live, so it was not accepted on its own: planting a single `0x08`
in place of `` `n `` inside `` `n_eff` `` — the exact defect — made my scanner
report **1** and made `corpus_lint` **FAIL with S7** naming the byte, the
column and the correct remedy. Both instruments fire; the 0 therefore means
something. The single-quoted `@'…'@` form was used throughout.

### 16.2 `$LASTEXITCODE` after a truncated pipeline (fact 1490) — reproduced, and it is sharper than the advisory

The correction was relayed with an explicit disclosure that it had not been
independently reproduced. It reproduces. On **pwsh 7.6.5**:

| primed with | command's true code | truncated by `Select-Object -First 1` | untruncated |
| --- | --- | --- | --- |
| `exit 0` | 7 | **0** — false GREEN | 7 |
| `exit 5` | 0 | **5** — false RED | 0 |
| `exit 0` | 7 | `-Last 1` reads **7** — correct | 7 |

**Two refinements the advisory does not state.**

* **The stale value is retained verbatim, not coerced to 1.** Priming with
  `exit 5` yields a read of **5**, not 1. The advisory's "reads 1" is an
  artefact of having primed with 1. So **no specific value can be treated as
  the signature of a stale read** — a gate that expects to distinguish
  corruption by seeing 1 will miss every other case, and any *plausible* code
  is suspect, which is the advisory's own central point taken to its
  conclusion.
* **`Select-Object -Last` is safe; `-First` is not.** `-Last` cannot emit
  until the stream ends, so the process is reaped and the code is live;
  `-First` short-circuits. The advisory says "truncation itself", which is the
  right mechanism, but the practical `-First`/`-Last` split is what an author
  needs, and both appear in this milestone's scripts.

**Audit of this milestone's own gates.** Every script here already captures
`$LASTEXITCODE` on the line immediately after the native call, into a
variable, before any filtering — `nc8_byte_inert.ps1:69`,
`refine_ladder.ps1:53`, `nc4_live_nonperturbation.ps1:24/41/47`,
`nc6_planted_mutation.ps1:35/47`, `render_baseline.ps1:60/71`,
`sweep_gate.ps1:35`, `sweep_radius.ps1:50`, `arms_lavendar.ps1:33/46`. The two
`Select-Object -First` uses operate on already-captured variables **after** the
read. `softgate_negctl.py` and `softgate_prediction.py` gate on Python's
`subprocess.returncode`, which has none of this behaviour.

Structural cleanliness is still only an argument, so **both gates this
milestone reported were re-run under deliberate failure priming**, where a
stale read shows as a false RED:

| gate | primed to | read | live? |
| --- | --- | --- | --- |
| `cargo check --workspace --all-targets` @ `2ae2944` | 3 | **0** | yes |
| `cargo test -p strehl-core --lib softgate::` | 3 | **0**, 18/18 | yes |

**No number in this report moves.**


## 17. Second fleet-correction audit — the narrowed exit-code rule, and the widened `D:\` rule

ORCH narrowed the truncated-pipeline order from *“re-run any gate”* to *“re-check only gates whose pipeline contained `Select-Object -First`”*, and widened the read-only constraint from two named trees to the whole of `D:\`. Neither moves a number in this report. Both were nonetheless audited rather than asserted, and the exit-code audit produced a small measured extension to the fleet table.

**The narrowed rule, applied.** Under the old broad order this milestone would have re-run its gates; under the narrow one it does not have to, and the reason is checkable rather than asserted. Every native call in M111's scripts is **bare** — no pipeline element at all — with `$LASTEXITCODE` captured on the immediately following line (`nc8_byte_inert.ps1:58-59` and `:68-69`, `refine_ladder.ps1:51-52`). Two `Select-Object -First` uses exist and **neither is a gate**: `nc8_byte_inert.ps1:75` filters the **already-captured variable** `$log` *after* the code was read at `:69` and contains no process at all, and `refine_ladder.ps1:60` truncates `Get-ChildItem`, a **cmdlet**, whose exit code is never consulted. The `-Last 20` / `-Last 15` uses are inside the failure branch, i.e. downstream of the read, and `-Last` is safe anyway. **Zero M111 gates match the unsafe shape.** Independently of this structural argument, both reported gates were already re-run under deliberate failure priming in §16 and read live.

**The extension.** ORCH's table clears `Select-String` unqualified. `-Quiet` and `-List` short-circuit by documentation and are the natural choice for a gate, so an unqualified clearance risked granting an unsafe shape — a false clear in the dangerous direction. Measured: **both are safe** (P44). The concern was reasonable and is refuted; the table closes rather than opens. The harness carries a **positive control** — it exits 3 and declares itself dead unless `-First 1` reproduces as UNSAFE — because a run in which every shape looks safe is far more likely to be a dead instrument than a refutation of facts 1507/1508.

**On being told my own measurement.** ORCH relayed fact 1508 (*the stale value is retained verbatim, so no observed exit code is evidence the read was live*) as M111's and M113's. I note it is load-bearing **against my own audit**: the structural argument above would be worth much less if a plausible-looking code could clear a gate, and §16's priming re-runs exist precisely because it cannot.

**The widened `D:\` rule, applied.** Audited by intent, not by present state — see P45. Nothing of M111's writes to `D:\`; the two scratch trees there belong to other milestones and are untouched.


## 18. The halo claim: ORCH's blur hypothesis is dead, and four better reasons to hold the campaign

**Assignment.** Audit M87's halo metric and design the controls for a campaign ORCH had queued as *“the thing he will actually see”*, on the hypothesis that the CA confound transfers: a treatment whose incidental blur acts on exactly the quantity being scored. Analysis only, read-only with respect to `crates/`.

**Verdict, in order of what it changes.**

1. **The blur hypothesis is refuted, twice, by measurements that already exist (P46).** It is not a near miss. A transformation destroying ~49% of gradient energy moves ISO **+0.6%**, and at *exactly* matched coarse suppression a Gaussian blur keeps 20.5% of the fine band against the correction's 90.6%. **Do not spend M116 on this arm.**
2. **But the campaign should still be held, for four reasons that are better evidenced than the hypothesis it was built on.** The headline is from the wrong pipeline (P47, 87.9% → **72.9%** on the shipped path); its author says **do not enable it** and the withdrawal preserved that conclusion (P48); registered bar V3 **fails** (P49); and the treatment fires *harder* on a scene with no occlusion than on the real one (P50), with a **non-monotone** ISO dose-response on that control against a monotonically rising error (P51).
3. **The confound is real but it is not blur — it is silhouette-keying.** The correction cannot distinguish *thin bright structure attached to the subject* from *background veiled by the subject*, because both are thin bright structure adjacent to a silhouette. That is a matting problem, and M87 says so.

**On the controls ORCH asked me to design.** Two of the four questions are already answered at source and re-running them would cost the campaign its time for nothing (P53). The proposed negative-dose arm is **unsound as specified** and biased toward vindicating the treatment (P54). Question 4 — *is d40 below the blur threshold or just the visible one?* — is answered and the answer is **neither**: at the strongest-correction site on the shipped full frame the FINE band falls to **0.9058**, i.e. **9.4% of fine structure destroyed**, and M87's own summary of the ladder is that *“none of these three is good; d40 is the least-bad point on a ladder every rung of which raises error against truth.”*

**The one arm I would actually commission,** because it is the only gap I found and it is nearly free: BMF matched the blur on the **COARSE DoG band ratio**, while the 49%-gradient arm was scored on **ISO**. Both halves of ORCH's literal question are covered, but by different arms and different statistics. **Scoring ISO on the already-computed coarse-matched blur** (`sigma = 5.108 px`, `56-bmf.py`) closes it in one line and yields the number in the exact form ORCH asked for. I did not run it — M116 owns render invocations and this needs none of mine.

**What I did not do, and why.** I did not re-measure fine-structure retention with the DoG instrument from §17. M87's FINE/COARSE bands are ratios against an untouched reference **on identical content**, which is strictly better than an absolute high-frequency energy statistic here — `P104` records that an absolute proxy rated visible polygonal patchwork **2.73× sharper** than the correct render. Re-running mine would have duplicated a better instrument with a worse one.

**Provenance.** Every number above was read from `experiments/M87-occlusion/data/56-bmf.json` and `22-plant-truth.json` as JSON, not transcribed from the prose, because this source self-retracts often — §16.9 carries a partial-withdrawal banner and P52, P80 and J1 are withdrawn elsewhere in the same file. I checked that the BMF result is **not** itself superseded: §§24.5, 25.9 and 28.7 all cite it as standing, and §25.9 makes it **binding on the successor** — *“it goes in paired with `BMF`, never alone”*.

**The instrument, and what it caught.** Because this audit is entirely transcription — every number is someone else's measurement — the failure mode is misquotation, so the numbers in §18 are machine-checked against their sources by `experiments/M111-waxy-blobs/halo_claim_guard.py` (23 checks, each pinned to its own fact row so a duplicate elsewhere cannot satisfy it), with `halo_claim_guard_negctl.py` as its negative control (**7/7** planted report defects and **3/3** planted source defects caught, restore verified). **It caught its owner on the first run**: I had written the control's d20 ISO change as −141.9% where 141.95215 rounds to **−142.0%** — truncation, not rounding. A small error, in a section whose whole claim is that the numbers in circulation are not the numbers at source. Discipline **P55** records the more interesting failure the control exposed in the guard itself.

**Reproduce:** `python experiments/M111-waxy-blobs/halo_claim_guard.py` (expect `GREEN 23/23`) and `python experiments/M111-waxy-blobs/halo_claim_guard_negctl.py` (expect `GREEN 7/7 report defects, 3/3 source defects`). The negative control writes only to `%TEMP%` and `C:\dev\strehl-out\M111-halo-control\negctl-data`, and restores the report from a `%TEMP%` copy rather than from Git.


## 19. The PIL 16-bit RGB hazard: not exposed, and what the exposure would have cost

**ORCH's fleet notice.** `PIL.Image.open()` on a **16-bit RGB** TIFF silently returns `uint8` — no warning, no exception — while 16-bit **greyscale** round-trips perfectly through `I;16`, which is almost certainly why it survived: anyone who sanity-checked the reader on a single-channel file saw it work.

**M111 is clean (P56)**, and not by luck — every TIFF read in the lane already went through `tifffile`. The two files carrying M111's headline numbers are `uint16` at source and were read as `uint16`, and re-running the probe reproduces the reported values exactly: `blobB` merged interior ratio **0.094**, control **0.761**, boundary p90 merged **1384.04**, control **226.69**.

**But “I didn't use PIL” is an argument, not a measurement**, and ORCH's notice specifically warned against reasoning that 8 bits would have been enough. So the exposure was measured rather than dismissed (P57): the defect would still have been detected, but **understated by 8.7%**, and — the part worth keeping — **the bias runs toward the null in every arm tested** (P58). The interior-flatness ratio was almost immune while the boundary-hardness contrast was not, from the *same pixels in the same script*, so exposure cannot be triaged from the file alone; it depends on the shape of the statistic.

**Reproduce:** `python experiments/M111-waxy-blobs/pil16_exposure_audit.py` — reads only from `C:\dev\strehl-out\`, writes only `C:\dev\strehl-out\M111-pil-audit\pil16_exposure_audit.json`.


## 20. Two-arm ratios are not protected by being two-arm ratios

**Trigger.** ORCH's corrected PIL notice offered two triage questions — *is my statistic absolute?* and *does it divide a small quantity by a large one?* — and, separately, the reassurance that *a ratio of two arms on the same data is largely protected by cancellation*, measured at **−1.0 %**. M111's boundary-hardness statistic **is** a ratio of two arms on the same data and it moved **−8.7 %** (§19). Both numbers cannot be a general property of two-arm ratios.

**Resolution: they are both right, at different disparities (P59).** The protective rule as stated has a **false-clear**, and it clears the statistics that matter most — a defect-detection contrast is a strong term over a weak one almost by definition, so it is a two-arm ratio *and* a small-over-large ratio at the same time. ORCH's two triage questions are not independent.

**Process note, because it is the more useful half.** Run 1 failed its own pre-registered gate. Rather than switch statistic and re-run — which would have delivered the answer I wanted with no evidence — I wrote down *why I thought it failed* as gate (c), committed the whole registration at `40da965` **before run 2 existed**, and run 2 **refuted my diagnosis** (P60). The disparity result survived; my account of my own error did not.

**Reproduce:** `python experiments/M111-waxy-blobs/twoarm_cancellation.py` (`M111_STRIDE=128 M111_TAG=run2` for the registered run). Writes only to `C:\dev\strehl-out\M111-pil-audit\`.
