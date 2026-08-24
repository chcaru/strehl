# M111 — the waxy blobs: what the merge synthesises where the frames carry nothing

**Status: PRE-REGISTRATION (written and committed before any M111 measurement).**
Author: M111. Not self-verified — see AGENTS.md rule 12.

Dispatched to find the mechanism behind the defect the owner can see, and to
prove it with controls. The defect and its first instrument are SYNTHESIS fact
1444 (ORCH, `experiments/ORCH-drift-check/blob_probe.py`).

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

*Sections 2 onward are written after the measurements and are not part of this
pre-registration.*
