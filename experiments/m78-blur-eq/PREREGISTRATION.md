# M78 — pre-registration: blur-equalised and phase-shifted short alignment edges

**ARGUED — contract.** This file is committed before either M78 treatment is run on a real pair,
a self-pair, or a synthetic field. Results may falsify it; thresholds will not be revised after a
result is visible.

**ARGUED — scope.** M78 is a research measurement. It changes nothing under `crates/`, and the two
arms below remain separately attributable: Arm A never phase-shifts a frame, Arm B never applies
blur equalisation or reads a focus label, and no combined A+B arm will be scored.

## 0. Fixed inheritance and validity gate

**MEASURED (inherited).** `SYNTHESIS.md` §4 fact 43 records that `coffee-bean` span-1 edges recover
only `1/3.260` of the width-48 anchor's log-scale change. Fact 47 records that the deep solve is
bounded by its pairwise measurements. Fact 177 records the fixed held-out baseline as **6.758
plane px** and reports that R4 did not improve it. Those are inherited observations, not M78
measurements.

**MEASURED (M78, before this contract).** The unmodified M23 run completed from a forced Rust
rebuild. Its measurement CSVs reproduced with no Git diff, `m23_conserve.py` printed both G0
checks as PASS, and `m23_heldout.py:evaluate` printed **6.758 px**. Timing-bearing text files were
not byte-identical because wall time changed; they are not treated as scientific outputs.

**ARGUED — harness.** The Rust files and solver library in this directory were copied from
`experiments/m23-metacal/` as present at M23's folded revision
`833377601334ad1ab7a02677dd2ad288999d5690`. M23 itself is a copy of M12/M10 plus its `metacal`
mode. M78 will add modes rather than rewrite the estimator.

**MEASURED (inherited input).** Fixed inputs:

| input | SHA-256 | role |
|---|---|---|
| `data/m10-coffee-bean-edges.csv` | `E242A64A6367FBE2C1A52D679D85CAA40BD091529E2FCE0D477EDB94FAC801A6` | untouched long-edge test set and raw baseline |
| `data/m12-stack-112-edges.csv` | `045995EFA2CFF6804D0391274EB51E2919432BBC869F1983C853E9F036D943FF` | Arm B placebo stack |
| M6 `data/coffee-bean-focus.csv` | `C5533D43654CC84E7CD4FA95ACFE87F72236B81D6C585484811017DC2D6FF8D4` | fixed Arm A tile-focus labels; copied byte-for-byte into M78 before use |

**ARGUED — invalidation rule.** Before either outcome is read, the inherited edge CSV hashes must
match this table, the M6 focus CSV copy must match its source, and the untreated held-out path must
reproduce **6.758 within 0.01 px**. A failure invalidates the measurement rather than counting
against either treatment.

**ARGUED — read-only rule.** Every command reads the real captures only from
`C:\dev\macro\test\coffee-bean` and `D:\personal\macro\112MSDCF`. A
`Get-ChildItem -Recurse -File -Force` count and byte sum is taken immediately before and after the
real-data run; any within-run difference invalidates the run.

## 1. Shared held-out acceptance gate

**ARGUED — statistic.** `E*` is M10/M23's statistic: for the fixed 125 directly measured test
edges with span at least 40 and at least 12 surviving tiles, take the median corner error over the
top span quartile. The test set is identical in every arm and contains no span-1 or span-2 edge.
`m10_measure.py:train_sets`, `strategies`, and `score` remain unmodified.

**ARGUED — admissible rows.** A candidate row must (1) use the registered primary treatment, (2)
train on a set that actually contains treated span-1 or span-2 edges, (3) cover all 105 frames, and
(4) have positive cycle rank. A tree is chaining in disguise and is excluded. The global row
trained on `span >= 32` has no power to differ and is not evidence for either arm.

**ARGUED — ship gate required by the M78 brief.** An arm passes the acceptance gate only if its
best admissible `E*` is **strictly below 6.758 px**. Equality fails. The same table will also print
M23's stronger historical margin, **`E* <= 6.358 px`** (reported as 6.36 there), but that second
line does not replace the brief's strict beat-baseline gate.

**ARGUED — failure direction.** Larger `E*` is worse. Scanning strategies can manufacture a small
win, so every arm is compared over the same scan, the winning train-set/strategy is named, and the
paired untreated value for that exact row is printed. A sub-0.40 px win is explicitly reported as
inside M23's runner-up margin even if it clears the brief's strict gate.

## 2. Arm A — R5 blur equalisation

### 2.1 Hypothesis and exact treatment

**ARGUED — hypothesis A.** A short pair's two tile images carry different defocus PSFs. If that
degradation mismatch contributes to the span-dependent scale loss, cross-convolving each side by
the other side's estimated PSF should move the span-1 conservation statistic toward 1 and may let
the repaired short edges beat the held-out baseline.

**ARGUED — focus label.** For each of M10's 12×8 fine-grid tile IDs, `w_t` is the sub-frame
parabolic winner of M6's registered `ring` profile, computed exactly as
`m6_lib.py:winner_index`. M6 used the same 12×8 ordering at a 56 px margin while M10 uses 96 px.
M78 matches by tile ID; the at-most-40 px anchor displacement is a declared model error, not a
parameter to tune after the result.

**DERIVED — primary blur rate.** The fixed capture-policy geometry uses a 2 sensor-pixel CoC with
1.5× overlap: `2 / 1.5 = 4/3` sensor-pixel diameter per focus step, or `2/3` green-plane-pixel
diameter. Matching the per-axis second moment of a uniform disc gives Gaussian
`q = diameter/4 = 1/6 = 0.1666667` plane px of sigma per frame. This is a model-derived primary
value, not a fit to `coffee-bean`.

**ARGUED — filter.** For pair `(i,j)` and tile `t`, define
`sigma_i = q*|i-w_t|` and `sigma_j = q*|j-w_t|`. The reference tile is convolved by a circular
Gaussian of sigma `sigma_j`; the moving search patch is convolved by sigma `sigma_i`. Under the
Gaussian model both then carry total sigma `sqrt(sigma_i^2 + sigma_j^2)`. Kernels are
unit-normalised and truncated at `ceil(3*sigma)`. No sigma cap is used at the primary rate:
`w_t in [0,104]` implies sigma at most 17.34 px and radius at most 53 px, inside M10's 96 px
margin after the 6 px fine search.

**ARGUED — estimator boundary.** The unfiltered M10 coarse pyramid supplies only the capture-range
seed. R5 changes the final 128×128 fine correlations, from which the reported similarity is fit.
The baseline and every non-R5 arm keep the inherited `align_with` path byte-identical.

**ARGUED — non-tuning ladder.** The blur-rate ladder is
`q in {1/12, 1/6, 1/3, 2/3}` plane px/frame, an 8× range. The primary outcome uses only `q=1/6`.
Other rates test sensitivity and may not be selected because they score better.

### 2.2 Arm A controls and falsifiers

| ID | exact control/statistic | numeric criterion | consequence |
|---|---|---|---|
| **A-C0 self-pair** | **ARGUED.** For every other adjacent index, use frame `i` on both sides but apply the two cross-filters that the real `(i,i+1)` pair would receive. True geometry is identity while real content and the R5 lowpass remain. Score corner error from identity. | median `<= 0.05 px` and p95 `<= 0.19 px` at `q=1/6` | Either excess kills Arm A regardless of real-pair movement. |
| **A-C1 interpolator-free field** | **ARGUED.** Render one continuous band-limited field directly as point samples at known scales, with analytic native Gaussian sigmas 0.5 and 1.5 px. No geometric interpolator appears. Apply the same discrete cross-filter before the inherited estimator. Define `Q(g)=log|a_measured|/log(1+g)` over `g={1e-4,2e-4,4e-4,8e-4}`, 12 independent fields. | At every `g`, treated median `Q in [0.90,1.10]`; `max_g median(Q)-min_g median(Q) <= 0.15`. | Accuracy or non-flatness failure kills Arm A. This is the mandatory 8× probe-amplitude check. |
| **A-C1p equal-blur placebo** | **ARGUED.** Repeat A-C1 with both native sigmas 1.0 px. | Same accuracy and flatness bands as A-C1. | Failure attributes the reading to the added filter rather than blur mismatch and kills Arm A. |
| **A-P positive mechanism probe** | **ARGUED.** The untreated A-C1 field is the plant that can express the proposed failure. | `\|median Q(1e-4)-1\| >= 0.10` | If it does not fire, R5's blur-asymmetry mechanism is not demonstrated. A real-data movement may still be reported but not attributed to that mechanism. |

**ARGUED — control failure direction.** `Q` can be fooled toward unity by a large probe, exactly
M23 fact 170's failure. That is why the smallest probe is the positive-mechanism reading and
flatness over the full 8× ladder is mandatory before any `Q` is relied on.

### 2.3 Arm A real-data statistics and decision

**ARGUED — A-S1 conservation.** For the fixed window 0..48,
`C_A(q) = log|a_0,48| / sum_{k=0}^{47} log|a^A_k,k+1|`. Untreated `C_0=3.2604` is recomputed,
not inserted. A direction-independent effect is `|C_A-C_0| >= 0.15`. A repair additionally
requires `|C_A-1| <= |C_0-1|-0.15` and no overshoot below 0.85. Values on all width-48 windows and
the local span-2/two-span-1 telescoping median are reported but do not replace the fixed-window
statistic.

**ARGUED — A-S2 held-out.** Replace only the inherited span-1 and span-2 rows by measurements at
`q=1/6`, then apply §1's fixed gate. No long test edge is filtered.

**ARGUED — Arm A ships only if all are true:** A-C0, A-C1, and A-C1p pass; A-S1 is a repair in the
registered direction; and A-S2 is strictly below 6.758 px. Passing advances R5 as an implementation
candidate; M78 itself still ships no production code. Any failed clause means **Arm A ships
nothing**.

## 3. Arm B — half-pixel phase probe

### 3.1 Hypothesis and exact treatment

**ARGUED — hypothesis B.** If sub-pixel sampling phase contributes to fact 43's span dependence,
moving a short edge to a known half-pixel operating phase and removing the known transform
analytically should change `1/S_48(1)`. A movement toward 1 would identify phase dither or an
upsampled peak—not response calibration—as the repair class.

**ARGUED — primary plant.** The moving plane is shifted once by `(ax,ay)=(+4.5,-3.5)` plane px
using M23's bilinear `warp_known`; the inherited estimator measures the shifted pair; the exact
inverse translation is then composed with the measured similarity before the edge row is written.
The integer terms leave the near-zero locking zone and both fractional phases are exactly 0.5.
The 96 px margin keeps all fine anchors away from image boundaries.

**ARGUED — registered controls.** The mirror replicate is `(-4.5,+3.5)`. The no-interpolator
placebo is an exact integer point-copy by `(+4,-3)`, analytically removed. No offset is selected
after results.

### 3.2 Arm B controls and falsifiers

| ID | exact control/statistic | numeric criterion | consequence |
|---|---|---|---|
| **B-C0 self-pair** | **ARGUED.** Shift every other real frame by the primary offset, align it to the unshifted copy of itself, and remove the shift. True result is identity. | median corner error `<=0.05 px`, p95 `<=0.19 px` | Failure kills Arm B. |
| **B-C1 integer placebo** | **ARGUED.** Re-measure all `coffee-bean` span-1 edges after the exact integer point-copy and analytic removal. | `\|C_integer-C_0\| <= 0.05` | Failure means composition/search operating point, not half-pixel phase, moved the result; Arm B dies. |
| **B-C2 112MSDCF placebo** | **ARGUED.** Apply the primary half shift to span-1 edges of the stack whose inherited `1/S_48(1)` is 1.0482 (M23 §7 gate b). | `\|C_112,half-C_112,raw\| < 0.10` | Failure means the plant moves a stack with no shrinkage to repair; Arm B dies. |
| **B-C3 interpolator-free field** | **ARGUED.** Render the shifted moving field directly at the composed transform as continuous point samples, then analytically remove the shift. No bilinear interpolator appears. Use the same `g={1e-4,2e-4,4e-4,8e-4}` and `Q(g)` as A-C1. | median `Q in [0.90,1.10]` at each probe and range across medians `<=0.15` | Failure kills reliance on a phase effect; this is the 8× response-amplitude check. |

**ARGUED — B-S1 phase effect.** Primary `C_half` must differ from `C_0` by at least **0.15** and
the mirror shift must move it in the same direction. A repair must move closer to 1 by at least
0.15 without crossing below 0.85. A movement away from 1 is an effect but a failed repair.

**ARGUED — mechanism attribution.** If the bilinear half-shift moves the real/self statistics but
the exact-render field and integer placebo do not, the effect belongs to the interpolator's
lowpass, not sampling phase. If the exact-render field also moves while its `Q` remains flat, it
belongs to the estimator's sampling phase. This attribution is reported before any held-out claim.

**ARGUED — B-S2 held-out.** Replace only inherited span-1 and span-2 rows by primary-offset rows,
then apply §1's gate. Arm B never consumes an Arm A row.

**ARGUED — Arm B ships only if all are true:** B-C0 through B-C3 pass; B-S1 is a same-direction
repair in both half-shift replicates; and B-S2 is strictly below 6.758 px. Passing advances a phase
dither/upsampled-peak follow-up; M78 itself still ships no production code. Any failed clause means
**Arm B ships nothing**.

## 4. Registered predictions

1. **ARGUED.** A-C0 will pass because cross-convolution uses centred kernels, but A-P will not
   fire: symmetric blur mismatch will flatten a peak without creating coherent scale shrinkage.
2. **ARGUED.** Arm A may change tile survival and conservation through added lowpass, but will not
   beat 6.758 px once its controls are honoured.
3. **ARGUED.** The bilinear Arm B plant will move a small-scale recovery statistic while the
   integer and exact-render arms stay near their known answers, attributing any effect to the
   interpolator rather than unplanted sampling phase.
4. **ARGUED.** Arm B will not move `C_0` toward 1 by the registered 0.15 in both mirror directions
   and will not beat 6.758 px.

**ARGUED — interpretation.** Wrong predictions are results. A negative verdict on both arms is a
complete M78 outcome.
