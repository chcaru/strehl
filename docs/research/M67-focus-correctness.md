# M67 — Does the shipped merge admit the frames that are actually in focus?

**Status:** MEASURED, on a simulator. **NOT MEASURED on real captures, and the
report says why and names what would change it.**

---

## Headline

On a calibrated simulated stack whose per-pixel correct frame is known **from
scene geometry** rather than from any focus operator, the shipped estimating
merge at its shipped default gate admits the truly-best frame at
**99.955 % ± 0.023 % of interior pixels** (3 seeds, K = 25, `n_eff` = 6.84).
A blind admission set of **identical per-pixel size** hits **27.44 %**; matched
for size *and* contiguous shape it hits **32.36 %**. The margin is **+0.725**,
which is **3.1 × 10³ times the across-seed standard deviation**. The metric
therefore has power, and the answer is not an artefact of set size.

**Three things must be read next to that number or it is misleading.**

1. **It is an idealised-PSF upper bound, produced by a suite that M25 proved is
   blind to the PSF.** The forward model hands a contrast operator a symmetric,
   monotone through-focus response *by construction*; M25 §6.2 measured that
   `coffee-bean`'s real through-focus curve "is asymmetric and falls faster than
   any simulated one", and M25's Gate 2 NC-B removed diffraction **entirely**
   and passed every gate. This was named in the pre-registration before any run.
2. **`H` alone is not a sufficient statistic, and three of ten swept cells prove
   it.** In the low-SNR and steep-spectrum cells the gate admits 24.5–24.9 of 25
   frames; `H` reads 0.99968–1.00000 and so does the random null — the metric
   has **no power** there and it is reported as no power, not as success. Those
   are exactly the cells M62's shipped guard G (`n_eff/N ≥ 0.95`) already FAILs
   — and, as §5 shows, they are a regime the real corpus never enters.
3. **Admission is not concentration.** In those same degenerate cells the
   admitted set's centre is up to **8.34 frames** away from the truth while
   `H = 1.000`. A merge that admits everything hits every truth and estimates
   nothing.

**The finding with the most consequence for the project's thesis** is the
separation between the two objects M65 warned are not interchangeable:

| object | hits the exactly-correct frame |
| --- | --- |
| `ArgmaxBaseline`'s elected winner (raw field) | **35.71 %** |
| the estimating merge's elected winner (regularised field) | **39.70 %** |
| the estimating merge's **admitted set** | **99.96 %** |

**The merge's own argmax is wrong about the exact frame index six times in
ten — and the gate catches the right frame anyway.** That is the estimator
thesis, measured for the first time in this project rather than argued.

**The price is measured too, in the same units.** The selector's single chosen
frame sits **0.848 frames** from true focus on average; the estimator's
admitted set averages frames sitting **1.733 frames** out — `D(A)/D(E) = 0.4895`.
The merge buys near-certain inclusion of the right frame by averaging in frames
roughly twice as defocused. **No direction was registered for this contrast and
none is claimed now**; it is the price list the owner's ruling (fact 848) asked
for, expressed on the focus axis.

---

## 1. Prior art searched and read (rule 40)

Searched `docs/research/` for `oracle`, `ground truth`, `ground-truth`,
`correct`, `depth`, `truly best`, `which frames`, `right frames`.

**Matched `oracle|ground[- ]truth` (36 files, all listed, per the brief):**
`B-algorithms-sota.md`, `E-plugin-architecture.md`, `F-camera-lens-optics.md`,
`G-edof-deconvolution.md`, `M3-alignment-measured.md`,
`M9-support-coupling-measured.md`, `M10-deep-alignment-measured.md`,
`M12-shrinkage-measured.md`, `M13-window-depth-measured.md`,
`M15-regulariser-window-measured.md`, `M16-orientation-fpn-measured.md`,
`M18-merge-implemented.md`, `M20-deconvolution-ceiling-measured.md`,
`M20-VERIFICATION.md`, `M21-occlusion-bimodality-measured.md`,
`M25-simulator-measured.md`, `M27-coverage-gap-measured.md`,
`M29-static-defects-measured.md`, `M31-VERIFICATION.md`,
`M32-posterior-confidence-measured.md`, `M33-subframe-offset-measured.md`,
`M34-confidence-vector-measured.md`, `M35-fit-generality-measured.md`,
`M36-VERIFICATION.md`, `M41-r3-kill-measured.md`, `M46-detail-metric-measured.md`,
`M48-read-noise-measured.md`, `M55-sigpow-verification.md`,
`M57-detail-metric-from-first-principles.md`, `M58b-fold-fidelity-audit.md`,
`M60-robustness-mask-at-merge-time.md`, `M61-ptc-high-iso-measured.md`,
`M63-bimodality.md`, `M64-estimator-default.md`,
`M65-election-gate-measured.md`, `SYNTHESIS.md`, `OWNER-QUESTIONS.md`.

**Matched `truly.best|correct frame|which frames|right frames` (9 files):**
`M25-simulator-measured.md`, `M32-posterior-confidence-measured.md`,
`M55-sigpow-verification.md`, `M57-detail-metric-from-first-principles.md`,
`M60-robustness-mask-at-merge-time.md`, `M62-ruling-M64.md`,
`M64-estimator-default.md`, `SYNTHESIS.md`, `OWNER-QUESTIONS.md`.

**Read in full or in the relevant sections, before anything was run:**

| file | what it settled, so that M67 did not re-derive it |
| --- | --- |
| `M25-simulator-measured.md` | §1 forward model, §2 fitted-vs-tested split, §4.3 Gate 1a/1c, §4.4 Gate 2 negative controls, §6 failure axes, §10 reproduce. **This is the only oracle the project owns.** Its §4.3 says ground truth was "used for the first time in this project" there. |
| `M64-estimator-default.md` | `Command::Stack` is the estimating merge and is the default; `DEFAULT_GATE = 4.0`; `Command::ArgmaxBaseline` is the retained pure selector. M64 states its own acceptance guard reads self-reported `n_eff`. |
| `M65-election-gate-measured.md` | 56.70 % of pixels elect a different winner while the acceptance set moves 0.44 %; the winner map and the admitted set are different objects. Its §9 is the model for §7 below. Its §3 control discipline and §5.1 post-hoc-probe-and-refusal are the template. |
| `M62-sqrt-n.md`, `M62-ruling-M64.md` | the √N acceptance battery and **guard G, `n_eff/N < 0.95`**. M62-ruling-M64 states the hole this milestone closes in terms: guard G "establishes that the merge still *discriminates between frames* on real data — `n_eff/N` between 0.014 and 0.30 across seven stacks against 1.000 on the burst from the same binary — and **establishes nothing about whether the frames it admits are the right ones**." §5 below shows guard G and this milestone's power failures coincide exactly. |
| `M13-window-depth-measured.md` | §2.4 "NULL 1 (ground truth)" — the project's existing pattern of feeding a metric the true frame map and requiring exactly 0. M67's mirrored-truth control (§4) is the inverse of it. Its occluding-edge cells were **not** used; see §8. |
| `M15-regulariser-window-measured.md` | the oracle-referenced `E_excess` and why an oracle is needed to see through a metric collapse. |
| `M32-posterior-confidence-measured.md` | §4: "The uncertain quantity is not *which frame is best* — that is nearly certain… It is **which frames are equivalent**." §6 below puts a number on that and partly contradicts it at exact-index granularity. |
| `M21-occlusion-bimodality-measured.md` | "No ground truth. 'Depth step' is inferred from the argmax field, not known." — the circularity M67 was told to avoid, already named. |
| `M12-shrinkage-measured.md` | the project's usage of "oracle" as an in-sample upper bound, not an accuracy claim. |
| `docs/captures-needed.md` §8, §9 | the tilted planar target request; corpus locations. §8 amended by this milestone. |
| `SYNTHESIS.md` facts 834, 847, 848, 870 | fact **834** is load-bearing for §8: `wrapped-text-*` is a real near-ground-truth depth target and **nothing has used it**. |

**Nothing in the corpus already answers this question.** M13 and M15 use an
oracle to score a *window* choice and a *reconstruction error*, not admission.
M20 uses "oracle depth" to bound a deconvolution. M32 argues about frame
certainty from peak σ and explicitly declines to measure it. No file scores
which frames the merge admits against an external truth.

---

## 2. What was measured, and against what

**The pre-registration is `experiments/M67-focus-correctness/PREREGISTRATION.md`,
committed at `53663ff` before any correctness, admission or hit-rate number
existed.** Where it and this report disagree, it is the record.

### 2.1 The oracle

`experiments/m25-simulator/src/strehl_sim/render.py::ground_truth` composites
each layer's focus map under **unblurred, geometric** alpha, integrates over the
pixel aperture, and returns `best_frame = argmin_k |visible_focus − focus_plane_k|`
together with the continuous `visible_focus`.

**Fact 1 (DERIVED).** That truth is a function of scene geometry and the frame
focus planes only. It never evaluates Tenengrad, the 27×27 support window
(`WINDOW_RADIUS = 13`), the 17×17 regulariser (`REGULARISER_RADIUS = 8`), the
noise model or the gate. **The operator under test cannot influence the answer
it is scored against.** This is the specific circularity the brief warned about,
and it is absent.

Truth is emitted at sensor resolution; the harness takes the 2×2 block mean of
`visible_focus` to obtain plane-resolution truth, because a green-plane pixel
owns the quad at `(2px, 2py)`.

### 2.2 The instrument

`crates/strehl-cli/examples/m67-focus-correctness.rs` — **additive**. It does not
modify `crates/strehl-core/src/merge.rs`, which another agent is certifying. It
implements `QuadSource` over rendered `u16` planes and drives the **shipped**
`FocusField::compute` → `regularise` → `FocusStats` → `Gate::admits` →
`Estimator` path, mirroring `merge_cmd.rs`'s two passes and the shipped
admission rule verbatim:

```rust
let winner = self.best_index[i] == frame_index;
let admitted = winner || self.gate.admits(regularised[i], self.best_focus[i]);
if !admitted { continue; }
```
> `crates/strehl-core/src/merge.rs`, pass two.

Scored over the **interior only**, margin `SUPPORT_RADIUS + REGULARISER_RADIUS
= 14 + 8 = 22` plane px, because a pixel nearer the border has a
replicate-clamped response. Headline cell: 512 × 512 plane, **219 024 interior
pixels**, truth `k*` spanning **2 … 22** of 0 … 24.

### 2.3 The arms

| arm | admitted set at pixel `i` |
| --- | --- |
| **`E(T)`** | the shipped estimating merge, `T ∈ {0.5, 1.0, 2.0, 4.0}`; `4.0` is `DEFAULT_GATE` |
| **`A`** | `Command::ArgmaxBaseline` — one frame, elected on the **unregularised** field, because `crates/strehl-cli/src/stack.rs` calls `field.compute(...)` and never `regularise` |
| **`Su(T)`** | null: `n_eff(T)[i]` indices drawn uniformly without replacement, **per pixel** |
| **`Sb(T)`** | null: a contiguous run of `n_eff(T)[i]` frames at uniform random start — matched in size **and shape** |

Both nulls are matched to `E(T)`'s **own per-pixel `n_eff`**, not to its mean,
and both are checked against a closed-form hit probability computed
independently (`n/K` for `Su`; contiguous-run overlap count over `K−n+1` for
`Sb`). Sampled and closed-form agree to ≤ 0.002 everywhere, e.g. seed 1 at gate
4: `H(Su) = 0.276965` sampled vs `0.275012` closed form.

### 2.4 The plants

21 renders, `strehl_sim` unmodified, all at ISO 160 (the one ISO where the
simulator's and the crate's read-noise constants cannot disagree), supersample
2, `breathing.total_scale_change = 0.0` (the merge assumes registered frames;
warping the plant would score the aligner), `channels = "green"` (inert — no
merged pixel value is scored).

Radiometry fitted from the real `D:\personal\macro\109MSDCF` ROI
`(2272, 1344, 256, 256)` — read-only, the same ROI M25 Gate 1a used: base
5515.4 e⁻, contrast 56.2 e⁻ sd, β 1.651. **That fit was disclosed in the
pre-registration** because it predates it. It is M25 §4.3 attempt 1's
noise-saturated 1.4 %-contrast regime, so subject contrast is **swept** ×{1, 4,
16} rather than fitted.

**Headline cell (fixed in the pre-registration, before any run):** `tilt`, side
1024 → plane 512 × 512, K = 25, `coc = 1.0` px/frame, contrast ×4, β 1.651,
span 24 frames, **three seeds**. Achieved in-focus band SNR (structure sd /
model noise sd) **2.35**.

---

## 3. Controls first — no arm ratio is believed until these are reported

**Fact 2 (MEASURED).** **C0 — the harness counts what the shipped `Estimator`
counts.** On every plant, at gate 4.0 over the whole plane, the harness's mean
`n_eff` equals `Estimator::mean_n_eff()` to printed `f64` precision. Headline
seed 1: `6.729324341` vs `6.729324341`. **PASS.** Without this, nothing below
is scoring the shipped merge.

**Fact 3 (MEASURED).** **C1 — the metric has power against a matched-`n_eff`
random admission set. MET on the headline cell.**
`|H(E(4.0)) − H(Su(4.0))| = |0.99955 − 0.27441| = 0.72514`, against a bar of
0.10; and against `10 ×` the across-seed SD of `H(E(4.0))`, which is
`10 × 2.339 × 10⁻⁴ = 0.00234`. The margin is **311 × that bar** and
**3.1 × 10³ × the SD itself**.

**Fact 4 (MEASURED).** **C2 — the metric separates the pure selector from the
estimating merge. MET, on all three statistics.**
`H(E) − H(A) = +0.64244`, `D(E) − D(A) = +0.88470` frames,
`M(E) − M(A) = −0.81429` frames, each against `10 ×` its own across-seed SD
(0.00234, 0.18615, 0.00234 respectively).

**Fact 5 (MEASURED).** **C3 — the plant carries a solvable signal. MET.**
`H(A) − 1/K = 0.35712 − 0.04000 = +0.31712`, against `10 × SD(H(A)) = 0.10235`.
A plant carrying no focus information at all would put `A` at `1/K`.

**Fact 6 (MEASURED).** **The instrument's own negative control fires.** This
control is **not** in the pre-registration; it was added before the sweep was
scored and is reported as an addition. Mirroring the truth map in the ramp axis
makes the truth anti-correlated with reality on a monotone plant. On headline
seed 1 it takes:

| statistic | true truth | mirrored truth |
| --- | --- | --- |
| `H(E(4.0))` | 0.99986 | **0.17458** |
| `H(A)` | 0.34278 | **0.03271** (`1/K` = 0.04) |
| `H(E) − H(Su)` | **+0.72289** | **−0.10091** |
| `E` winner == `k*` | 0.37341 | 0.03358 |

The margin against the null goes **negative**. A metric that is not reading the
truth would not have moved. This is the inverse of M13's NULL 1: M13 fed the
metric the true frame map and required exactly 0; M67 feeds it a false one and
requires collapse.

---

## 4. The primary result

Headline cell, three seeds, across-seed means; `H` is the fraction of interior
pixels whose admitted set contains the truly-best frame `k*`.

```
gate   n_eff     H(E)    H(Su)    H(Sb)    D(E)   D(Sb)    M(E)      rho     dev
 0.5   1.652  0.57738  0.06617  0.06924  0.7854  7.4755  0.4636  1.00000  0.4081
 1.0   2.446  0.74538  0.09779  0.10536  0.8662  7.3404  0.2662  1.00000  0.3247
 2.0   4.090  0.94117  0.16356  0.18513  1.1305  7.0692  0.0591  1.00000  0.2920
 4.0   6.843  0.99955  0.27441  0.32364  1.7329  6.7167  0.0004  1.00000  0.6110
```
> `experiments/M67-focus-correctness/out/AGGREGATE.txt`. `D` is mean admitted-set
> defocus in frames; `M` is mean miss distance in frames; `rho` is Spearman
> between column index and that column's mean admitted index; `dev` is the max
> column deviation from truth in frames. `A` scores `H = 0.35712`,
> `D = 0.8482`, `M = 0.8147`, `n_eff = 1` at every gate by construction.

### 4.1 D1 — the headline decision

**Fact 7 (MEASURED).** `H(E(4.0)) = 0.99955`, sd `0.00023` over three seeds
(0.999858, 0.999290, 0.999510). The pre-registered rule was: below 0.50,
conclude the merge does not admit the truly in-focus frame at a majority of
pixels; at or above, conclude that it does, at that rate, on this plant.
**`H ≥ 0.50`. On this plant, at the shipped default gate, the merge admits the
truly-best frame at 99.955 % of interior pixels.** Mean miss distance
`M(E(4.0)) = 0.0004` frames.

### 4.2 D2 — the margin. **MET.**

**Fact 8 (MEASURED).** Against the harder, shape-matched null:
`H(E) − H(Sb) = 0.99955 − 0.32364 = +0.67591` (bar ≥ 0.10) **and**
`D(Sb)/D(E) = 6.7167 / 1.7329 = 3.876` (bar ≥ 1.10). Both clauses MET, so the
claim "the merge's admitted set beats a matched blind guess" stands. Against the
size-matched-only null, `D(Su)/D(E) = 7.5909 / 1.7329 = 4.380`.

### 4.3 D3 — the structural prediction. **MET.**

**Fact 9 (MEASURED).** The plant's depth is monotone in `x` by construction, so
a merge admitting frames for the right reason must produce an admitted-set
centre monotone in `x` and tracking the truth. Measured at gate 4.0 on the
headline cell: Spearman `ρ_col = 1.00000` (bar `|ρ| ≥ 0.95`) and max column
deviation **0.611 frames** (bar ≤ 1.0). Both MET. `ρ_col = 1.00000` at every
rung of the ladder.

**This is the simulator's stand-in for the brief's option 2** — a planar subject
at a known tilt, whose in-focus frame index must vary smoothly and monotonically
across the field. §8 reports what happens to it on a real capture: nothing, yet.

### 4.4 D4 — selector versus estimator. Reported with no direction.

**Fact 10 (MEASURED).** Gated by C2, which is MET.

| contrast | value |
| --- | --- |
| `H(E) − H(A)` | **+0.64244** |
| `M(E) − M(A)` | **−0.81429** frames |
| `D(E) − D(A)` | **+0.88470** frames, i.e. `D(A)/D(E) = 0.4895` |

The estimator is far more likely to have the right frame *somewhere in the set*
and its worst-case distance to the right frame is 0.81 frames smaller — but the
**average frame it actually averages** is twice as far from focus as the single
frame the selector picks. The pre-registration recorded no expected sign for any
of these and predicted no value, precisely because a selector can only hit or
miss while an estimator can hit while averaging poor frames. Both halves
happened.

### 4.5 D5 — gate dependence, on the rungs fixed in advance

**Fact 11 (MEASURED).** `H(E)` rises 0.577 → 0.745 → 0.941 → 0.99955 across
gates 0.5 → 1 → 2 → 4 while `n_eff` rises 1.65 → 2.45 → 4.09 → 6.84 and `D(E)`
rises 0.785 → 0.866 → 1.131 → 1.733 frames. **The shipped default is the only
rung of the four at which the correct frame is nearly always admitted**, and it
is also the rung with the most defocused average admission. The two nulls rise
in step with `n_eff` (0.066 → 0.274 for `Su`), which is what a size-driven
statistic must do and is why the margin, not `H`, carries the claim.

Note the non-monotone `dev`: the max column deviation falls 0.408 → 0.325 →
0.292 and then **rises to 0.611** at gate 4. Widening the gate past 2.0 buys the
last 6 % of `H` by admitting frames that pull the set's centre away from the
truth at the ends of the ramp, where the admitted interval is clipped by the
ends of the stack. That is a one-sided-truncation effect and it is the mechanism
by which `H` and `dev` come apart — see §5.

---

## 5. Where the metric has NO POWER, and it is exactly where M64 already says FAIL

The sweep is reported at every cell, not only where `H` is largest, as
pre-registered.

```
cell                                           n_eff/K  M64  H(E)-H(Su)  C1abs  H(A)-1/K   C3  devmax   D3*
tilt-s1024-coc10-c4-b1650-span24                0.2737   ok    +0.72514    yes  +0.31712  yes   0.611  yes
flat-s512-coc10-c4-b1650-span0                  0.2713   ok    +0.72620    yes  +0.28527  yes   0.302   n/a
tilt-s512-coc10-c1-b1650-span24                 0.9840 FAIL    +0.01577     NO  +0.09689  yes   8.246   NO
tilt-s512-coc10-c16-b1650-span24                0.1279   ok    +0.87107    yes  +0.53428  yes   0.233  yes
tilt-s512-coc10-c4-b1650-span24                 0.2813   ok    +0.71972    yes  +0.27739  yes   0.305  yes
tilt-s512-coc10-c4-b1650-span8                  0.2761   ok    +0.72275    yes  +0.34422  yes   0.281  yes
tilt-s512-coc10-c4-b3454-span24                 0.9979 FAIL    +0.00169     NO  +0.03618  yes   8.338   NO
tilt-s512-coc30-c1-b1650-span24                 0.9786 FAIL    +0.02195     NO  +0.21583  yes   8.250   NO
tilt-s512-coc30-c16-b1650-span24                0.0558   ok    +0.94409    yes  +0.88329  yes   0.221  yes
tilt-s512-coc30-c4-b1650-span24                 0.1172   ok    +0.88099    yes  +0.70824  yes   0.245  yes
```
> `D3*` is a **post-hoc** extension of D3 to the sweep; D3 as pre-registered is
> scored only on the headline cell. On `flat` the truth is constant, so a
> Spearman against column index is undefined and D3 does not apply — it is
> reported `n/a`, not FAIL. `M64` is the column for **M62's guard G**,
> `n_eff/N ≥ 0.95`, as run in M62-ruling-M64 and M64 PR3.

**Fact 12 (MEASURED).** **C1 is NOT MET on three of ten cells**, and the
pre-registered consequence is honoured: **on those three cells the metric has no
power and no correctness claim is made about them.** `H(E(4.0))` reads
0.99968, 0.99960 and 1.00000 on them — and `H(Su(4.0))` reads 0.98390, 0.99791
and 0.97805. **The blind guess is as good as the merge, because the merge is
admitting 97.9–99.8 % of the stack.** Reporting those `H` values as accuracy
would be the exact failure this milestone exists to prevent.

**Fact 13 (MEASURED).** The three no-power cells are **precisely** the three
cells where M62's shipped guard G fails: `n_eff/N` = 0.9840, 0.9979, 0.9786, all
≥ 0.95, and no other cell exceeds 0.28. **The project's existing acceptance
battery already refuses to certify exactly the regime in which this milestone's
instrument is blind.** These are the two lowest-SNR cells (0.53 and 0.50) and
the steep-spectrum cell (β 3.454, `coffee-bean`'s low-band slope).

**Fact 14a (DERIVED).** **The blind regime is one the real corpus never
enters.** M64's PR3 measured `n_eff/N` on all seven corpus stacks: worst
**0.3011**, `109MSDCF` **0.2267**, `foam` **0.0136**; M62-ruling-M64 states the
range as **0.014 to 0.30**. Every no-power cell here sits at 0.978–0.998, more
than three times the corpus maximum. **On the `n_eff` axis, the powered result
covers the regime real captures occupy and the blind cells are outside it.**
This is an argument about set size only. It does **not** transfer the result to
real captures, because the optical circularity of §7.2 is untouched by it.

**Fact 14 (MEASURED).** In those cells the admitted set's centre deviates from
the truth by up to **8.34 frames** (8.246, 8.338, 8.250) while `H ≈ 1`, and
`ρ_col` falls to 0.900, 0.690 and 0.731. **`H` and the structural check come
apart, and they come apart in the honest direction:** `H` says the right frame
is in the set, `dev` says the set is centred a third of the stack away from it.
**`H` must never be quoted without `n_eff/N` beside it.** That is a property of
the observable, not of the merge, and it was not anticipated in the
pre-registration.

**Fact 15 (MEASURED).** Where the metric does have power, the answer is stable
across every axis swept. On the **six powered `tilt` cells**, `H(E(4.0))` spans
**0.99917–1.00000**, covering defocus rate `coc ∈ {1.0, 3.0}` px/frame, subject
contrast ×{4, 16}, depth span {24, 8} frames and plane {256², 512²}. The
seventh powered cell is `flat` — a fronto-parallel plant where every pixel's
correct frame is the same one — and it gives **0.99828** against a null at
**0.27207**.

---

## 6. Election versus admission: which object is being scored

M65 measured that the winner index map and the acceptance set are different
objects — 56.70 % of pixels elect a different winner while the acceptance set
moves 0.44 %. **`H` scores the admitted set.** The winner is reported here
separately and is not the headline.

**Fact 16 (MEASURED).** On the headline cell, across three seeds:

| statistic | value |
| --- | --- |
| `E` winner == `k*` (regularised field) | **0.39699**, mean \|win − k*\| **0.7175** frames |
| `A` winner == `k*` (raw field) | **0.35712**, mean \|win − k*\| **0.8147** frames |
| `E` admitted set contains `k*` | **0.99955** |

The regulariser buys **+3.99 points** of exact-index election accuracy and
**0.097 frames** of mean winner error over the raw field. The gate buys
**+60.26 points** over the regularised election. **Almost all of the merge's
focus correctness lives in the gate, not in the election.**

**Fact 17 (MEASURED).** `ArgmaxBaseline`'s miss-distance CDF on the headline
cell: exact **0.35712**, within ±1 frame **0.84292**, ±2 **0.98561**, ±3
**0.99962**. `E(4.0)`'s admitted set reaches **1.00000** by ±1 on all three
seeds.

**Fact 18 (ARGUED).** This sharpens M32 §4 and partly contradicts its phrasing.
M32 wrote that "the uncertain quantity is not *which frame is best* — that is
nearly certain", reasoning from 10²–10³ σ peak separations. At **±1–2 frame**
granularity that is right: `A` is within ±2 frames 98.6 % of the time. At
**exact index** granularity it is wrong on this plant: `A` is right 35.7 % of
the time. The reconciliation is M32's own explanation — the true peak lies
*between* frames, so the argmax of a noisy discrete sample lands one rung off
most of the time. **What is nearly certain is the neighbourhood, not the
index**, and that is precisely why a gate that admits a neighbourhood
outperforms an election that must name one.

---

## 7. The circularity, named, and what is downstream of it

### 7.1 What is NOT circular

The truth map, the depth ramp, the frame ordering and the defocus rate are
inputs to the render and outputs of nothing the merge computes (Fact 1). `Su`
and `Sb` never read the focus field. The `A`-vs-`E` contrast is between two
shipped code paths scored by one external ruler. The mirrored-truth control
(Fact 6) demonstrates empirically that the ruler is being read.

### 7.2 The circularity I could not remove

**Fact 19 (ARGUED, registered in advance).** The forward model blurs each depth
band with `defocus(|F−k|·coc) ⊛ diffraction(N_eff, λ)`. That PSF is **symmetric
in `k` about `F` and monotone in `|F−k|`**, so a contrast-based focus operator
is handed a monotone unimodal through-focus response **by construction**. Real
optics are not that: M25 §6.2 measured `coffee-bean`'s real through-focus curve
as "asymmetric and falls faster than any simulated one", and M25 §6.3 lists
spherical aberration, coma, astigmatism, field curvature, longitudinal chromatic
aberration and PRNU as **not modelled at all**.

**The consequence was registered before any run and is honoured now: every
accuracy number in this report is an UPPER BOUND on real-capture accuracy, and
every failure number is a LOWER BOUND on real-capture failure.** The 99.955 %
is the ceiling, not the estimate.

**Fact 20 (ARGUED, registered in advance).** M25's own validation suite is blind
to the component this milestone's observable depends on. Gate 2's NC-B removed
diffraction **entirely** — a 4.52× amplitude change over 0.30–0.48 cyc/px — and
**passed every gate**. M25's headline says in terms: do not use it to score
deconvolution, PSF estimation or EDoF. `H` is not a deconvolution score, but it
is squarely downstream of the PSF and is **not in M25's validated set**.
Everything in §4 inherits an unvalidated optical component.

**Fact 21 (ARGUED).** The noise model is shared. The plant is exposed through
the simulator's `g = max(ISO,100)/436.8`, `RN = 4.20 e⁻` chain; the focus
operator normalises by `profile.rs`'s `ILCE-7CM2` model, which is the same
model. **The operator is noise-matched to the plant by construction.** A real
sensor's PRNU — unmodelled, and M25 §6.1's "leading suspect for the floor
deficit" — would break that match. Both sides are pinned at ISO 160, where the
simulator's `read_noise_e_high = 1.47` and the crate's `1.2392` cannot disagree
because neither is used below ISO 400.

**What is downstream of the circularity:** Facts 7, 8, 9, 10, 11, 15, 16, 17 —
every number produced on a plant. Facts 2–6 (the controls), 12–14 (the power
failures) and 22–24 (§8) are not, because they are statements about the
instrument and about what exists, not about the merge's optical performance.

---

## 8. Not measured versus not measurable, on real captures

**Fact 22 (MEASURED).** **Per-pixel focus correctness is NOT measurable on the
existing corpus.** No stack in `D:\personal\macro` has a per-pixel depth or
in-focus-index truth, and none can acquire one after the fact. The
pre-registration said this milestone would claim nothing about real captures and
it claims nothing.

**Fact 23 (DERIVED).** **The brief's option 3 — self-consistency under frame
subsetting — is vacuous against this merge, and provably so.** The shipped
pass-two loop is

```rust
if !admitted { continue; }
```

so a frame outside the admitted set contributes **exactly zero** to the pixel.
Removing it from the stack is therefore a **bit-exact no-op**, not a small
effect. Removing an admitted frame changes the pixel by an algebraically known
amount determined by `n_eff` and the frame's value, which contains no
information about whether that frame was the correct one. **Leave-one-out can
measure a soft-weighted merge; it cannot measure a hard-gated one.** This is
worth recording because the test sounds reasonable until the gate is read.

**Fact 24 (MEASURED).** **A real-capture *structural* test does exist today, it
is stronger than anything else available, and it has never been run.**
SYNTHESIS fact 834: `wrapped-text-1` (130 frames, ISO 100) and `wrapped-text-2`
(120 frames, ISO 400) are text on a supplement bottle — **known, smooth, convex
curvature** with high-contrast glyphs over the whole surface — and "nothing has
used it". A cylinder gives a strong falsifiable prediction that needs no oracle:
the in-focus frame index must be **smooth and unimodal across the bottle's
circumference and constant along its axis**, with no interior extremum other
than the single ridge nearest the camera.

**Three reasons this milestone did not run it, all of which are limitations and
not defences.**

1. **The pre-registration excluded real captures** (§7, "Nothing about real
   captures"). Running it now, after seeing the simulator result, would be a
   post-hoc arm with no bar fixed in advance. M65's §5.1 is the precedent for
   how such a probe must be labelled, and the labelling would consume most of
   its value.
2. **It cannot measure accuracy, only falsify.** The field being tested for
   smoothness is the operator's own output, so a *pass* is self-consistency with
   an assumed geometry, not correctness. Only a *failure* would be informative.
3. **Its premise is itself unverified.** Fact 834's "known, smooth, convex
   curvature" is a description, not a measurement; nobody has fitted the bottle.
   Fact 847 records that this project has already been burned once by inferring
   subject geometry from filenames.

**What would make per-pixel correctness measurable on real frames:** the tilted
planar target of `docs/captures-needed.md` §8, already requested and still owed.
A plane's true depth map is known in closed form up to three parameters that can
be fitted **from the data itself**, so the per-pixel in-focus index becomes
computable without an oracle — which is exactly what `H` needs and exactly what
no stack in the corpus provides. §8 of that file has been amended with M67's
specific use. **The owner also still owes flat fields** (`captures-needed.md`
§4), and fact 835 records that those must now be shot both with and without the
polariser.

---

## 9. What I refused to conclude

* **Any accuracy claim on the three degenerate cells.** C1 is NOT MET there and
  the registered consequence — no correctness claim — is honoured. `H = 1.000`
  in a cell where the null also scores 0.998 is not a result.
* **Anything about real captures.** No `H`, no margin, no structural number on
  any stack in the corpus. Fact 24 names an available structural test and
  declines to run it under a pre-registration that excluded it.
* **Anything about image quality.** `H`, `D` and `M` are properties of the
  admitted *set*. No sharpness, SSIM, edge-error or detail number was produced,
  and the D4 contrast is **not** a quality comparison — a set with lower `D` is
  not thereby a better image, because averaging trades defocus against noise and
  this milestone measured only one of those two axes.
* **Any direction for D4.** None was registered and the measured signs go
  opposite ways on `H` and `D`, which is the outcome the pre-registration said
  it declined to guess.
* **Anything about occlusion.** M25's Gate 1c FAILs — the veiling signature has
  the wrong sign, 0.23× against a real 4.38× — so M13's ready-made occluding-edge
  cells were **excluded by M25's own verdict**. An admission statistic at a
  simulated depth discontinuity would be measuring the plant.
* **That 99.955 % is what the merge does on a camera.** Facts 19–21 make it a
  ceiling produced by an idealised, unvalidated PSF and a noise model shared
  with the operator.

---

## 10. Verification

* **C0 identity**, every plant, `f64`-exact against `Estimator::mean_n_eff()`.
* **Closed-form nulls** computed independently of the sampled ones; agreement
  ≤ 0.002 at every gate and cell.
* **Mirrored-truth control** collapses `H(E)` 0.99986 → 0.17458 and drives the
  margin negative (Fact 6).
* **`merge.rs` untouched.** The instrument is `crates/strehl-cli/examples/`.
  Verified by the commit's own file list.
* **Corpus read-only.** The only access to `D:\personal\macro` was one ROI read
  in `00-timing-probe.py` and `10-render-plants.py` for the radiometric fit.
* `cargo fmt` clean, `cargo clippy --release -p strehl-cli --example
  m67-focus-correctness` clean.

**Two instrument defects found and fixed before scoring**, recorded because they
would each have produced a silently wrong table: `Tee-Object` under Windows
PowerShell 5.1 writes **UTF-16LE**, which a UTF-8 reader parses as zero SUMMARY
lines (loud, caught); and the SUMMARY line carries `plant=` **twice** — the run
name and the meta block's scene kind — so a naive parser collapsed 10 cells into
2 and would have averaged unrelated cells together (quiet, caught by an
assertion that exactly one headline cell exists).

---

## 11. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl

# ~75 min single-threaded; --stride/--offset splits it across workers
python -u experiments\M67-focus-correctness\src\10-render-plants.py

cargo build --release -p strehl-cli --example m67-focus-correctness
powershell -File experiments\M67-focus-correctness\src\15-run-instrument.ps1
python -u experiments\M67-focus-correctness\src\20-aggregate.py

# the instrument's negative control, on its own
.\target\release\examples\m67-focus-correctness.exe `
    experiments\M67-focus-correctness\plants\tilt-s1024-coc10-c4-b1650-span24-seed1 `
    --truth-mirror
```

Plants (`*.frames.u16`, `*.truth.f32`) are gitignored; `plants/*.meta.txt`,
`out/*.log` and `out/AGGREGATE.txt` are committed.

---

## 12. Facts, for the fold

| # | fact | label |
| --- | --- | --- |
| 7 | **The shipped estimating merge admits the truly-best frame at 99.955 % ± 0.023 % of interior pixels** on a simulated tilted plane with `n_eff` = 6.84 of 25, where truth is computed from scene geometry and never from the focus operator. | MEASURED |
| 3 | The metric has power: the margin over a per-pixel-size-matched random admission set is **+0.725**, **3.1 × 10³ ×** the across-seed SD. | MEASURED |
| 8 | Against a null matched for size **and contiguous shape**: margin **+0.676**, and the null's admitted set is **3.88 ×** as defocused. | MEASURED |
| 16 | **The merge's own argmax names the exactly-correct frame only 39.70 % of the time; the gate raises that to 99.955 %.** The selector `ArgmaxBaseline` scores 35.71 %. Almost all focus correctness lives in the gate, not the election. | MEASURED |
| 10 | The price: `D(A)/D(E) = 0.4895`. The selector's chosen frame sits **0.848** frames from focus; the estimator's admitted set averages frames **1.733** frames out. No direction was registered and none is claimed. | MEASURED |
| 12 | **`H` has no power in 3 of 10 cells** — the gate admits 97.9–99.8 % of the stack there and the blind null scores 0.978–0.998. No correctness claim is made on them. | MEASURED |
| 13 | Those three cells are **exactly** the cells M62's guard G (`n_eff/N ≥ 0.95`) already FAILs (0.9786, 0.9840, 0.9979; no other cell exceeds 0.28). | MEASURED |
| 14a | **The blind regime is outside the real corpus.** M64 PR3 measured `n_eff/N` on all seven corpus stacks at 0.014–0.3011; every no-power cell here is 0.978–0.998. On the set-size axis the powered result covers the real operating regime. It transfers nothing optical. | DERIVED |
| 14 | In those cells the admitted set's centre is up to **8.34 frames** from the truth while `H = 1.000`. **`H` must never be quoted without `n_eff/N`.** | MEASURED |
| 17 | `ArgmaxBaseline`'s miss CDF: exact **35.7 %**, ±1 **84.3 %**, ±2 **98.6 %**. M32's "which frame is best is nearly certain" holds at ±2 frames and fails at exact index. | MEASURED |
| 19 | **Every accuracy number here is an upper bound and every failure number a lower bound**, because the forward model's PSF is symmetric and monotone in `|F−k|` by construction while real through-focus curves are measured asymmetric (M25 §6.2). Registered before any run. | ARGUED |
| 20 | The observable is downstream of the PSF, and **M25's suite is blind to the PSF** — Gate 2 NC-B removed diffraction entirely and passed everything. This result sits outside M25's validated set. | ARGUED |
| 23 | **Leave-one-out frame subsetting is vacuous against a hard-gated merge**: `if !admitted { continue; }` makes removing a non-admitted frame a bit-exact no-op. | DERIVED |
| 24 | **`wrapped-text-1/-2` supports a real-capture structural falsification test that has never been run** — a bottle's curvature forces the in-focus index field to be smooth, unimodal circumferentially and constant axially. It can falsify but not measure accuracy, and its premise (fact 834's geometry) is itself unverified. | MEASURED |
| 22 | **Per-pixel focus correctness is not measurable on the existing corpus.** The capture that would change that is `captures-needed.md` §8's tilted planar target, requested and still owed. | MEASURED |

---

## 13. Hand-off

**The one-line answer to the question the brief asked.** Yes, by a wide and
measurable margin — **on an idealised plant, at the shipped default gate, and
only where the gate is not already degenerate.** The margin over a matched blind
guess is +0.725 with the metric's power demonstrated at 3.1 × 10³ σ and its
negative control firing hard. The same instrument shows the margin vanishing
wherever `n_eff/N ≥ 0.95`, which is where the project's own acceptance battery
already refuses to certify.

**What is now known that was not.** M64 and M65 both said the project had
measured how many frames the merge averages and never whether they were the
right ones. That gap is closed on a simulator and it is closed in the direction
the thesis predicted, with the mechanism localised: **the gate, not the
election, is what makes the merge correct.** The election is wrong six times in
ten about the exact index.

**What is still open, in priority order.**

1. **The tilted planar target** (`captures-needed.md` §8). It is the only thing
   that converts `H` from a simulated number into a measured one. Cheap, owed,
   and now has a second milestone depending on it.
2. **Run the `wrapped-text` structural falsification** (Fact 24) as its own
   pre-registered milestone, with the bottle's geometry fitted first so the
   premise is measured rather than asserted. It cannot produce an accuracy
   number, and that must be in its pre-registration, not discovered later.
3. **`H` is not safe to ship as a diagnostic on its own** (Fact 14). Any future
   use of it must carry `n_eff/N` and the matched-null margin beside it, or it
   will certify a merge that admits everything.
4. **The PSF remains the project's largest unvalidated component.** M25 §6.2's
   asymmetric real through-focus curve is the measurement that would let this
   milestone's ceiling be converted into an estimate. Until then, 99.955 % is a
   ceiling and this report says so in its first paragraph.
