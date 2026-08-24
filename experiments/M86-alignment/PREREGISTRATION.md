# M86 — pre-registration: deep-stack alignment as a shipped module

**Written and committed before any M86 accuracy number was produced.** Nothing in
this file was chosen after seeing an M86 result. Where a threshold is inherited
from another milestone it is namespaced (`M10:`, `M12:`, `M23:`, `M78:`) and the
report it comes from is named.

---

## 1. The defect, stated so it can be checked

`crates/strehl-cli/src/stack.rs:3` describes the shipped pipeline as
`decode -> calibrate -> NO alignment -> Tenengrad`. `crates/strehl-core/src/lib.rs`
declares no alignment module. **The shipped merge combines frames with no
geometric registration.**

Prior work measured the problem but never shipped an implementation:

| source | what it is | where the code lives |
|---|---|---|
| `docs/research/M3-alignment-measured.md` | the pairwise estimator | `experiments/m3-drift/` (Rust, experiment-only) |
| `docs/research/M10-deep-alignment-measured.md` | the global solve | `experiments/m10-deep-align/m10_lib.py` (**Python**, experiment-only) |
| `docs/research/M12-shrinkage-measured.md` | why calibration cannot rescue chaining | Python |
| `docs/research/M23-…` / `M78-…` | two failed short-edge repairs | Rust + Python, experiment-only |

So M86's hypothesis, registered here before measuring, is:
**the algorithm largely exists and has never been written in `crates/`.** If that
is right, the deliverable is a port plus an honest re-measurement at 299 frames,
not a new algorithm. If the port reproduces prior numbers and 299-frame stacks
behave like the 105-frame one, M86 must say so plainly rather than manufacture a
novel method.

## 2. Units, fixed here

All errors are **plane px at the worst plane corner** on the CFA-quad green
plane, exactly as `M10:` uses. One plane px is two sensor px. For the A7C II
active area 7032x4688 the plane is 3516x2344 and the corner radius is
`rho = hypot(3516,2344)/2 = 2112.85` plane px. A scale error `da` costs
`rho*|da|` px at the corner; `da = 0.01` is 21.13 plane px.

## 3. Primary metric — `E*`, held-out long-edge prediction

Inherited verbatim from `M10:` §4.1 and `experiments/m10-deep-align/m10_ruling.py`
so that M86's numbers are comparable with the corpus's:

1. Measure a set of **direct** pairwise fits. Compose nothing.
2. **Test set** = every direct edge with `span >= S_min` and `>= U_min` accepted
   tiles. Fixed per stack, so every strategy row is scored on the same edges.
3. **Training sets** are named subsets guaranteed disjoint from the test set by
   `(i,j)` key.
4. Each strategy predicts every test edge; the error is the worst plane corner.
5. **`E*` = the median over the top-span quartile of the test set**, for the
   best full-coverage strategy over a **non-tree** training graph.
6. Tree training graphs are excluded: `M10:` §1.1 — a bundle adjustment over a
   tree is chaining in disguise, so such a row has no power to separate them.
7. Partial-coverage strategies are scored but cannot set `E*`.

`S_min`/`U_min` per stack are fixed in §5 below, before measuring.

**`E*` is fit-free by construction** but it is not ground truth. It is bounded
below by the mutual consistency of the edges themselves (`M10:` §4.4), so it is
reported next to raw-edge cycle consistency, which uses no solver at all.

## 4. Registered decision rule

Inherited thresholds, `M10:` PREREGISTRATION §6, fixed before M10 had data:

| symbol | value | meaning |
|---|---|---|
| `T_solved` | **1.0 plane px** | alignment is solved |
| `T_usable` | **4.0 plane px** | usable in a shipped merge |
| `T_chain` | **12.5 plane px** | the adjacent-chain error M3 measured; anything above is no better than the thing rule 6 forbids |

Baselines to beat, namespaced:

* `M10: E* = 6.758 px` on `coffee-bean` (105 frames) — the number to reproduce
  and the bar to beat.
* `M23:` and `M78:` both registered "beat 6.758 px or ship nothing" and both
  shipped nothing (`M78: 7.266073` and `7.244330`).

### 4.1 What result means the method does NOT work

Registered before measuring. **Any one of these is a failure and will be
reported as one:**

* **F1** — `E*` on a 299-frame stack exceeds `T_chain` = 12.5 px, or coverage is
  below 100% of frames.
* **F2** — the Rust port fails gate **G0** or **G1** in §6: it does not
  reproduce the corpus's own committed numbers. Then no M86 number means
  anything and the milestone reports a broken port.
* **F3** — the planted-scale control **C2** does not recover a planted
  `a = 1.01` within the registered bar. Then the estimator is not measuring
  magnification and every other number is void.
* **F4** — the mutation control **C3** does not make a registered gate fail.
  Then the gates have no power (AGENTS.md rules 20, 39) and no PASS may be
  quoted.
* **F5** — `E*` on the 299-frame stack is *below* the drift the stack actually
  carries, i.e. the alignment error is a large fraction of the motion being
  corrected. Specifically: if `E* > 0.5 * total_corner_drift`, aligning buys
  less than half the error it removes and must not be called a fix.

### 4.2 The honest-negative outcome, registered as a first-class result

If the measured **total corner drift** of tonight's 299-frame stacks is at or
below `T_usable` = 4.0 px, then **breathing is not why these stacks look soft**,
alignment is not the defect to fix tonight, and M86 must say exactly that. This
is registered *before* the drift is measured precisely so that a small answer
cannot be quietly reframed as a win. Drift is measured as the worst-plane-corner
displacement of the frame-0 -> frame-(N-1) transform from the global solve, and
reported beside the direct long edge where one is measurable.

## 5. Test stacks, fixed before measuring

All read-only. No M86 process writes to any capture directory; inventories are
recorded before and after (AGENTS.md rule 14: `Get-ChildItem -Force`).

| id | path | frames | why it is here | `S_min` | `U_min` |
|---|---|---|---|---|---|
| `coffee-bean` | `C:\dev\macro\test\coffee-bean` | 105 | **the reproduction gate** — `M10:`'s own stack and committed edge CSV | 40 | 12 |
| `bee-3-cpl` | `D:\personal\macro\bee-3-cpl` | 299 | primary deep stack, ISO 100 | 40 | 12 |
| `bee-2-cpl` | `D:\personal\macro\bee-2-cpl` | 299 | **sibling of `bee-3`, same subject, ISO 400.** `M77:` fact 1104 measured sibling stacks disagreeing 3.31x on a constant, so one stack is never evidence | 40 | 12 |
| `flat-on-ruler-cpl` | `D:\personal\macro\flat-on-ruler-cpl` | 79 | flat ruled plane: straight lines and even graduations are a checkable invariant that needs no fit | 20 | 12 |
| `foam` | `D:\personal\macro\foam` | 100 | **adversarial** — documented as a stack that moved. A similarity model must not silently "correct" real subject motion | 24 | 12 |
| `109MSDCF` | `C:\dev\macro\test\109MSDCF` | 22 | shallow control; `M10:` reports 0.489 px median here | 12 | 40 |

`highly-angled-ruler-mm-cpl` is **excluded**: M84/M84b own it. M86 writes
nothing to `experiments/M84-ruler-metrology/` or `experiments/M84b-ruler-metrology/`.

A clean result on `109MSDCF` alone is **not** evidence of general robustness
(corpus fact M24: it is the quietest stack in the corpus).

## 6. Gates and controls, with the input that would make each FAIL

AGENTS.md rule 20 requires naming the failing input for every gate, and checking
such an input exists.

| id | what it checks | PASS bar, fixed now | an input that FAILS it |
|---|---|---|---|
| **G0** | Rust global solve reproduces `M10:`'s Python | On `M10:`'s committed `coffee-bean-edges.csv`, cfg `m10`: `E*` within **0.05 px** of 6.758, and `S3-ba-unit` median within **0.05 px** of 6.997 | any sign/gauge/weighting error in the port; a wrong Huber threshold; solving the normal equations at insufficient precision |
| **G1** | Rust estimator port reproduces `M3:`/`M10:`'s | On >= 200 shared `coffee-bean` edges, **median** corner difference from M10's committed fit <= **0.19 px** (`M10:` P1's estimator floor) and >= 95% of edges agree on `ok`/`no-fit` | a changed tile grid, margin, contrast floor, peak floor or parabolic clamp |
| **C1** | estimator floor, **no interpolator anywhere** | Band-limited field sampled at two geometries (`M10:` P6 arm). Recovered/planted scale ratio in **[0.98, 1.02]** over a planted-`g` ladder | a biased correlator; a wrong lever arm; a broken parabolic peak |
| **C2** | recovers a planted `a = 1.01` on **real frames**, plant verified by read-back | ratio in **[0.98, 1.02]**, i.e. <= 0.42 plane px of the 21.13 px planted corner motion | plant not applied; plant applied to the wrong frame; estimator blind to scale |
| **C3** | **the control that must fail.** A byte-planted mutation of a committed M86 input or constant must drive a registered gate to a **nonzero exit** | gate reports FAIL and process exits nonzero; then restore from a **copy**, set `LastWriteTime` (AGENTS.md rule 33), and re-run green | if it does not fail, F4 fires |
| **C4** | non-degeneracy | every training graph's cycle rank and `is_tree` recomputed from the data, tree rows excluded from `E*` | a span-1-only training set (this fires live in `M10:`) |
| **C5** | read-only corpus | file counts and byte totals with `-Force` identical before and after | any write into a capture directory |

**C2's plant is written to a copy inside `experiments/M86-alignment/`, never into
a capture directory.** `M23:` fact 172 is the standing warning that a resampled
plant is itself a lowpass; C2 is therefore a *recovery* control only, and no
claim about defocus bias rests on it. C1 is the interpolator-free arm.

## 7. What M86 will NOT do, registered so it cannot be quietly added later

* **No shrinkage correction.** `M12:` measured that it transfers to 0 of 18
  cross-scene pairs and makes the worst case 83.4x worse. Not attempted.
* **No re-admission of span-1/2 edges** into the solve. `M10:` rule, `M78:`
  re-tested it and shipped nothing.
* **No blur equalisation and no phase dither.** `M78:` tested both, both failed.
* **No integration into the merge.** M85 owns `merge_cmd.rs` tonight. M86 ships
  a module plus an example binary and an integration recipe, and edits
  `crates/strehl-core/src/lib.rs` only to add `pub mod align;`.
* **No claim that a metric improved "by eye".** No rendered-image comparison is
  admissible evidence in this report.

## 8. Model, registered before fitting

Primary model: a **similarity** per frame — complex `a` (scale and rotation) and
complex `b` (translation), acting on plane coordinates relative to the plane
centre, `p' = a*p + b`.

Registered questions about the model, each with its falsifier:

* **Q1 — is rotation needed?** Falsifier: if the fitted rotation over a whole
  stack is below the estimator's own rotation floor from C1, rotation is not
  measurable and must be reported as not measurable rather than as zero.
* **Q2 — is the transform smooth in frame index?** Falsifier: if a low-order
  polynomial in frame index leaves a residual **above** `T_usable`, smoothness
  is true and useless (`M10:` §5c reached exactly that verdict at 105 frames).
* **Q3 — is a single centre of expansion enough?** Falsifier: `M10:` §5c's
  registered rule — reject the single centre if its residual exceeds **3x** the
  free-translation residual.
* **Q4 — does the residual look like real breathing or like estimation noise?**
  Registered observable: the lag-1 autocorrelation of the per-frame residual in
  frame index. Smooth structure implies unmodelled physics; white residual
  implies estimator noise. **No threshold is registered** because none is
  defensible in advance; the number is reported as a diagnostic, not a verdict.

## 9. Resampling, registered before choosing

Rule 2 forbids materialising aligned frames, so the deliverable is a **gather**
sampler, not a warper. Registered comparison: **bilinear** against
**Catmull-Rom bicubic**, scored by the round-trip test that `M23:` fact 172 used
to catch its own resampler — resample a real plane by a known transform and its
exact inverse, then measure the retained high-frequency energy against the
untouched original. Registered prediction, recorded so it can be wrong:
bilinear loses materially more than Catmull-Rom. **A null is possible and would
be reported**: if both lose the same, interpolator choice is not load-bearing.

## 10. Reporting rules M86 binds itself to

* Every number labelled **MEASURED / DERIVED / ARGUED / VERIFIED**.
* Every number taken from another milestone namespaced `M10:` etc.
* Facts numbered `P1, P2, …` (AGENTS.md rule 28 corollary), never absolute.
* Failures reported in the same table as wins, not in a footnote.
* `E*` never quoted without its coverage, its training set and its cycle rank.
