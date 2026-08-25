# M120 — PRE-REGISTRATION

**Written and committed BEFORE any M120 measurement ran.** Rule 20: for every
gate below, the input that would make it FAIL is named, and such an input is
shown to exist.

Author: M120. Not self-verified (rule 12).

---

## 0. Prior work searched (rule 40)

Read in full or in the named sections before writing this file:

* `docs/research/M111-waxy-blobs.md` — **named after this artifact.** §1 prereg,
  §2 headline + retraction, §4 mechanism, §5 verdicts, §7 audit of ORCH's probe,
  §8 fix, §9 open, §10 P1–P35, §13 self-retraction, §15 soft gate.
* `docs/research/M96-election-margin.md` §Verdict, §Headlines, §0.
* `docs/research/M97s-soft-gate.md` (whole).
* `docs/research/M116-promotion.md` §5 P1–P14. **P10 is directly on point.**
* `experiments/M87-occlusion/src/04-through-focus.py`, `15-crops.py`,
  `m87lib.py` — the provenance of the three PNGs the brief names.
* `crates/strehl-core/src/merge.rs` (read only).

**What the prior work already establishes and M120 must NOT redo:**

| already settled | by | consequence for M120 |
| --- | --- | --- |
| The regulariser sets plateau *scale*, does not *create* plateaus (54.0 px at radius 0 vs 60.3 px shipped, 32× radius span) | M111 P3 | ORCH's fact-1604 limb (b) is already refuted on `marker`. M120 tests it on `bee-3`, which is a different scene class (defocused-everywhere white background). |
| A coincidence between a render feature and an election boundary is **not** evidence the election drew it — the gate-1e5 arm, where the election cannot touch the output, scores *higher* (1.686) than the shipped arm (1.239) | M111 P8 | **Item 1 of the brief, taken literally, is a test M111 already proved cannot separate R1 from its rivals.** M120 must run it (it was asked for) *and* run the control that decides whether the number means anything. |
| A mask that is a percentile of the arm under test separates the arms by construction | M111 P13/P28 | Every mask in M120 is defined from **input frames only**, never from a merged render. |
| Never divide by an sd from < ~30 samples; quote the rank floor | M111 P27 | All nulls here use ≥ 64 draws and report a rank p-value. |
| `--gate 0` shows gross polygonal tiling on `bee-3-cpl` at 1:1 and `--gate 4` does not | M116 P10 (visual only) | M120 must check *which arm the brief's three PNGs actually are* before attributing anything to the shipped merge. |

---

## 1. The provenance check that comes first

`C:\dev\strehl-out\M87-before-after\00-BEFORE-shipped-merge-tight2x.png` is
produced by `experiments/M87-occlusion/src/15-crops.py` from
`cache/bee3-leg-sel.npy`, which `04-through-focus.py` computes as

```python
best    = fields.max(axis=0)
argbest = fields.argmax(axis=0)
sel     = np.take_along_axis(lumas, argbest[None], 0)[0]
```

i.e. a **pure per-pixel argmax with no gate, no averaging, no alignment warp,
no demosaic and no colour transform**, in green luma on the binned grid, from a
Python re-implementation.

**Registered gate PC1.** Before any mechanism claim, M120 states in its first
line whether the three PNGs are the shipped merge. **FAIL input exists:** if
`ship-before-linear.tif` (the actual shipped `strehl stack` render, already on
disk at `experiments/M87-occlusion/cache/`) carries the same patchwork at the
same ROI at the same amplitude, PC1 is a non-finding and the brief's framing
stands.

---

## 2. Hypotheses

**R1 (ORCH, fact 1604).** Flat through-focus response ⇒ noise-dominated ⇒
near-random argmax ⇒ regulariser snaps it into piecewise-constant regions ⇒
polygons; frames differ in background brightness ⇒ steps.
Three separable limbs, tested separately:
* **R1a** the response is noise-dominated in the background;
* **R1b** the regulariser is what makes the field piecewise constant;
* **R1c** the steps are inter-frame background brightness differences.

**R2.** Tiling artefact of the implementation — axis-aligned edges on a fixed
pitch.

**R3.** The polygons are photographic — present in the input frames.

**R4.** The steps are photometric only; no geometric content.

**R5.** Demosaic or the output colour/tone transform.

**R6 (added by M120).** The polygons are the level sets of an argmax over a
field that is *already* smoothed at 27×27 by `focus.rs::WINDOW_RADIUS = 13`
before `merge.rs` sees it. Piecewise-constancy is then a property of
*argmax-of-a-smooth-field*, and requires no noise-domination at all. This is
R1b's rival and it is the mechanism M111 P3 measured on `marker`.

**R7 (added by M120).** The polygons are a *gate* phenomenon: at `n_eff = 1` a
pixel is one frame; the artifact's amplitude is set by how much of the ROI has
`n_eff = 1`, not by how the winner was chosen.

---

## 3. Arms, and what each shows under each hypothesis

All arms are computed on the **same ROI on the same grid**, chosen by §4.

| arm | R1a | R1b | R2 | R3 | R4 | R6 | R7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A. through-focus response peak vs its own permutation null**, per background pixel | peak ≈ null | — | — | — | — | peak ≫ null | — |
| **B. response range vs the pure-noise ceiling** (M111's 0.4777 analogue, recomputed for this ROI) | at ceiling | — | — | — | — | above ceiling | — |
| **C. recompute the field with `REGULARISER_RADIUS = 0`** from the same luma cube and re-run the argmax | — | plateaus dissolve to per-pixel speckle | unmoved | — | — | plateaus survive at ~27 px | — |
| **D. 2-D power spectrum + edge-orientation histogram of the elected-index gradient** | — | — | **peak at a pitch, edges axis-aligned** | — | — | isotropic, no pitch | — |
| **E. per-frame local HF energy of every input frame over the ROI** | — | — | — | **some frame carries the polygons** | — | — | — |
| **F. HF energy of the merge vs `max_k` HF of the inputs** (the invariant) | — | — | — | ≤ 1 if R3 | — | > 1 | > 1 |
| **G. per-polygon mean removed; residual HF inside polygons** | — | — | — | — | **residual ≈ frame noise** | — | — |
| **H. observed step across a seam vs the step predicted by the two frames' ROI-mean levels** | — | — | — | — | predicted ≈ observed | — | — |
| **I. gate ladder: `sel` (gate 0) vs `g2` (gate 2) vs shipped `--gate 4`** | — | — | unmoved | unmoved | — | — | **amplitude tracks `n_eff = 1` fraction** |

## 4. ROI definition — fixed before any render is read (rule 17)

The background ROI is defined **from the input frames alone** and never from any
merged image:

1. On the M87 luma cube (299 × 744 × 1144, `bee3-leg-luma.npy`), compute a 9×9
   local sd per frame.
2. Keep pixels whose local sd is below the 20th percentile of the *whole cube's*
   per-pixel **maximum over frames** — i.e. pixels that are smooth in **every**
   frame.
3. Take the largest axis-aligned square that fits inside that set with a 30 px
   erosion margin, restricted to the half of the box the brief's crop covers.

The mask therefore cannot be conditioned on the merge's output. **FAIL input
exists:** if no such square of side ≥ 128 exists, the invariant of item 4 is not
applicable to this stack and M120 reports that instead of a number.

## 5. Registered decision rules

1. **R3 is CONFIRMED and everything else is moot** if arm E shows any single
   input frame carrying HF energy over the ROI within 1.5× of the merge's.
   M120 stops and reports a photographic artifact.
2. **R2 is CONFIRMED** if arm D's edge-orientation histogram concentrates
   > 50% of gradient mass within ±10° of the axes **and** the power spectrum has
   a peak at a repeating pitch exceeding 3× the local background. **REFUTED** if
   orientation is within ±20% of isotropic and no pitch peak exceeds 2×.
3. **R1a is REFUTED** if the median background-pixel response peak exceeds the
   pure-noise ceiling by more than 2× (M111's registered rule 2, second clause,
   applied to this ROI), or if the paired win rate against the frame-permutation
   placebo exceeds the M96-measured null band's upper edge of 81.134%.
4. **R1b is REFUTED** if arm C leaves the plateau equivalent diameter within
   ±40% at `REGULARISER_RADIUS = 0`.
5. **R1c is REFUTED** if the observed seam step exceeds the step predicted from
   the two frames' ROI-mean levels by more than 3×, i.e. the steps are mostly
   *not* level differences.
6. **The invariant of item 4 HOLDS as a defect statement** only if arm F's ratio
   exceeds 1.0 by more than its own null band, where the null is the same ratio
   computed for a **spatially constant** frame choice (each of ≥ 20 single
   frames, and the plain mean).
   **This bound is not empirical: for constant weights, `‖H(Σ wₖ fₖ)‖ ≤ Σ wₖ‖H fₖ‖
   ≤ maxₖ ‖H fₖ‖` by the triangle inequality, so a ratio above 1 is proof the
   weights varied spatially.** Reported with its failure direction (rule 18):
   this statistic **cannot** distinguish manufactured structure from genuinely
   recovered detail, so it is admissible **only** on an ROI where every frame is
   smooth — which is precisely how §4 builds it.
7. **The metric is `Q = HF(merge) / maxₖ HF(frame k)` on a §4 ROI.** It is
   accepted only if (a) the **null** — 20+ single-frame arms and the plain mean —
   returns `Q ≤ 1.0` and (b) the **positive control** — a synthetic patchwork
   built by assigning polygons to random frames from the *same* cube — returns
   `Q` well above 1. Registered direction, written before running: **null ≤ 1.00,
   positive control ≥ 1.5.** Laplacian kurtosis is computed alongside as a rival
   metric and is reported whether or not it agrees.
8. **The soft gate is priced, not rendered.** M116 owns the render. M120's
   deliverable is a prediction with a stated number and a stated fraction of the
   frame, derived from the elected-index / margin / confusion-radius planes and
   the response cube only.

## 6. Negative controls, all mandatory

* **NC1** — the identical detector on a **textured** ROI of the same frame must
  not report the signature.
* **NC2** — every coincidence statistic carries a shift null with ≥ 64 offsets
  and a rank p-value.
* **NC3** — a **decoupled-election** control in the spirit of M111 P8: a merge
  arm whose election cannot influence the output (the plain mean), scored by the
  identical coincidence statistic. If it scores as high as the shipped arm, the
  coincidence number is retired rather than reported.
* **NC4** — a **planted patchwork** at the real DN range must be recovered by
  every statistic M120 reports; a zero reading is not self-explaining.
* **NC5** — geometry is proved, not assumed: every cross-artifact overlay states
  the measured offset and its correlation peak, and refuses if the peak is not
  unique.
* **NC6** — no file under `crates/` is edited. Proved by `git status` on that
  path at the end.

## 7. What would make M120 wrong

* If the shipped render carries the same patchwork at the same amplitude, PC1
  is void and the mechanism question is exactly as ORCH framed it.
* If a single input frame carries the polygons, R3 wins and the milestone is a
  retraction of fact 1603.
* If arm F's ratio is ≤ 1, the invariant does not hold on this stack and the
  proposal in item 4 must be withdrawn.
