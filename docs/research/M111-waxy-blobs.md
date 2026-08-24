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
| **H6** intermediate-response admission collapse | **CONFIRMED** | admission 285 → 1 as response rises 0.62 → 5; +12.00 DN of selection-attributable excess at seams in the elected flat population, **+97.4σ** against a translated null, with both negative controls firing *below* their nulls. |

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
* **P2 — MEASURED.** The waxy patches are selection artefacts, not regulariser artefacts. Differencing the shipped render against a gate-100000 render of the same frames, alignment, colour and exposure isolates what selection added: in the visually flat, elected (`n_eff ≤ 8`) population the luma step across election seams exceeds the off-seam step by **+12.00 DN**, ratio **1.248** against a translated-election null of **1.002 ± 0.003** (**+97.4σ**), while the same detector reads **0.765** where the merge averaged and **0.880** in textured regions — both *below* their nulls. `experiments/M111-waxy-blobs/attribution.py`.
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
* **P20 — MEASURED.** Fact 1445's election-map statistics do not transfer across stacks and must not be quoted as properties of the map. Re-measured on `dry-erase-marker-head-cpl`, 299 frames, alignment **on** with `STREHL_WARPMAP` pinned: boundary density **9.91% h / 9.03% v** against 1445's 3.33% / 3.34%, median jump **2 frames** against 1445's 1, and **44.1%** single-frame steps against 71.4%. On `lavendar-cpl` the median jump is **20 frames** and single-frame steps fall to **22.5%**. The plane grid is **3520×2344** here, not 1445's 3516×2344 — both solvers' own sidecar headers say so — and the grid follows the common crop, so a milestone that hard-codes either number will index the wrong pixels. Fact 1445's numbers should be **SCOPED** to its 12-frame `STREHL_ALIGN=0` arm.
* **P21 — MEASURED.** `STREHL_WARPMAP` structurally immunises a render against fact 1446: `merge_cmd.rs`'s `alignment_for` returns to `align_cmd::load_or_solve` — the poisoned function — only when the variable is unset. Measured with a sidecar that passes every identity check and displaces 298 of 299 frames by 2.0 plane px: with the override set, a poisoned cache leaves the render at `DB7BAAD2…`, unchanged; with it unset, the same cache moves the render to `0D41E08B…`, which is *bit-for-bit* what pointing the override at the poison directly produces. The renderer prints which path it took — `sidecar-override` versus `sidecar` — so exposure is readable from any milestone's existing logs without re-running anything.
* **P22 — MEASURED.** The `lavendar-cpl` cache entry consumed by M111's generality arm is byte-identical (`4D454CCE…`) to a forced fresh solve at the merge's own configuration, header included (`reference 149`, `S3-ba-unit`, `catmull-rom`), and the two render to the same bytes (`F12B14C4…`). Fact 1446's omitted key fields were not exercised on this bracket, so a pre-fix arm is not automatically a contaminated arm — but this can only be established per bracket, by re-solving, not assumed.

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

