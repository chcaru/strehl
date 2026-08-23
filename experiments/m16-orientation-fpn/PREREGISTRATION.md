# M16 — pre-registration

**Question:** SYNTHESIS §10 open question 20. *Why does edge orientation set the
direction the merge regulariser moves the focus-window optimum — and is it a
defect that biases every window number the project has produced?*

**Written and committed before any M16 result was computed.** Nothing in this
file is conditioned on an M16 measurement. The only numbers quoted here are
already published: SYNTHESIS fact 83, M15 §6, M13's ladder and thresholds.

Labels used throughout the milestone: `MEASURED` (a number this milestone
produced), `VERIFIED` (produced twice through disjoint paths), `DERIVED`
(follows from a stated rule applied to measured numbers), `ARGUED` (a mechanism
I believe and have not isolated), `UNVERIFIED` (a belief flagged so nobody
quotes it as fact).

---

## 1. The effect under test

Fact 83 / M15 §6. Between merge-regulariser width `g = 1` and `g = 17`, over the
30 occluding-edge cells with a depth step:

| geometry | cells | median shift of `w*` | narrower | wider | same |
| --- | ---: | ---: | ---: | ---: | ---: |
| `horizontal` | 10 | **−2.5** | **10** | 0 | 0 |
| `vertical` | 10 | +1.5 | 2 | 6 | 2 |
| `bar` | 10 | +1.0 | 2 | 6 | 2 |
| ALL | 30 | 0.0 | 14 | 12 | 4 |

Both the Sobel pair and the box window are 90°-symmetric, so this should not
happen.

**A structural fact about the harness that the question's framing hides, and
that this design is built around.** `EdgeGeometry::Bar` is a bar in **x**:
`signed_distance = |x − at| − half_width`. Its two boundaries are therefore
**vertical lines**. So the three geometries are not three orientations — they
are **two vertical-boundary geometries and one horizontal-boundary geometry**,
and the split in fact 83 is exactly boundary orientation. That is consistent
with the orchestrator's correction on fold ("`horizontal` is the outlier"), and
it means the primary contrast is `horizontal` against `vertical ∪ bar` pooled,
not a three-way comparison.

## 2. Hypotheses

- **H1 — texture anisotropy.** The two corpus stacks' green-luma content has
  directional structure, so a horizontal boundary and a vertical boundary meet
  different texture. Harmless; a corpus artefact; nothing to fix.
- **H2 — a defect in the evaluation geometry** that `E_excess` uses, shared by
  M13 and M15. `E_excess = mean_band(e_merged) − mean_band(e_oracle)` over
  `|d| ≤ 24`. On a 384×256 ROI that band is a 49×256 strip for a vertical edge
  and a 384×49 strip for a horizontal one — different shape *and* 1.5× different
  pixel count. Two sub-forms, tested separately:
  - **H2a — band shape.** The scored band itself is not 90°-symmetric.
  - **H2b — plant aspect.** The *layers* are not 90°-symmetric either: a
    vertical edge leaves 192 px of each layer, a horizontal edge 128 px, while
    the widest window in the ladder is 81 px across and the widest defocus blur
    is 41 px. A wide window therefore occupies a larger fraction of the
    available layer at a horizontal edge.
- **H3 — row/column fixed-pattern noise (the external reviewer's mechanism, and
  the primary hypothesis).** Sobel-x and Sobel-y see row banding
  asymmetrically: a row-constant pattern has **exactly zero** `gx` and all of
  its energy in `gy`. The real texture tiles are single decoded frames and carry
  the sensor's FPN. If row banding is large enough to move the focus field, it
  moves it anisotropically, and horizontal boundaries — whose own step is also
  pure `gy` — are the ones it interferes with.
- **H4 — none of the above / the effect is not resolved.** Ten cells per
  geometry with a discrete argmin is a coarse instrument. This is a live
  outcome and is registered as such.

More than one may be true. None may be true.

## 3. Design

### 3.0 Harness

M13's harness, **reused not reimplemented**: `edge.rs` (the layered-occlusion
render, the profile, `E_excess`), `measures.rs` (Sobel/Tenengrad and the box
window), `planted.rs` (the blur, the RNG, `synthetic_texture`) and `tile.rs`
(the green-luma extraction) are included from
`experiments/m13-window-depth/src/` **by path, unmodified and uncopied**.
`experiments/m13-window-depth/**` is not written by this milestone.

M16 adds a driver (`experiments/m16-orientation-fpn/src/main.rs`) that
re-implements only the sweep loop of M13's `edge_mode`, plus the knobs below.
That re-implementation is the risk, and **Gate 2 exists to price it**.

### 3.1 Treatment knobs

| knob | values | what it does |
| --- | --- | --- |
| `--texture` | `real` \| `synth` | real decoded green-luma tiles, or an isotropic 1/f synthetic field |
| `--destripe` | `none` \| `mean` \| `hp` \| `oracle` | applied **per frame, to the focus operator's input only** |
| `--fpn-sd`, `--fpn-axis` | DN, `row`/`col`/`both` | plants a known row and/or column offset pattern into the base texture |
| `--transpose` | flag | transposes both textures before rendering |
| `--score-region W,H` | | crops the scored region, centred, inside the ROI |

**`destripe = mean`** is the fix the reviewer proposed:
`F'[y,x] = F[y,x] − (r[y] − m) − (c[x] − m)`, with `r` the row means, `c` the
column means and `m` the frame mean. Level-preserving by construction
(`mean(F') = m`), which matters because the operator's `Norm::Pointwise`
divides by `σ(luma)`.

**`destripe = hp`** subtracts only the *high-frequency* part of those profiles
(`r − blur_σ(r)`, σ = 4 px), which preserves low-frequency scene content.

**`destripe = oracle`** subtracts the exactly-known planted pattern. Only
meaningful with `--fpn-sd`; it is the arm with **no** content-destruction
confound at all.

**Crucially, the destripe is applied to the focus operator's input and nowhere
else.** The merged output is still `frames[sel[p]][p]` from the *undestriped*
frames, and `ideal`, `oracle` and `single_sigma` are untouched. So the treatment
changes **only which frame is elected**, and `E_excess` is measured on the same
physical quantity in every arm. This is deliberate: it removes "you changed the
metric" as an explanation of any movement.

### 3.2 Arms

All arms: 24-window ladder `w ∈ {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,
18,20,23,26,33,40}`, regulariser widths `{1,3,5,9,13,17,25,33,49}`, steps
`{0,2,4,8,16,32}`, shapes `{vertical, horizontal, bar}`, seeds
`{20260823, 771117, 4242424, 13371337, 90210}`, both stacks `109MSDCF` and
`119MSDCF`, `frames 41`, `sigma0 0.8`, `alpha 0.35`, `noise-scale 1`. Identical
to M15's sweep, so the ladder, margin and therefore the *scene* are identical.

| id | texture | ROI | transpose | destripe | planted FPN | tests |
| --- | --- | --- | --- | --- | --- | --- |
| `A0` control-rect | real | 384×256 | no | none | none | Gate 2 |
| `A1` destripe-mean | real | 384×256 | no | mean | none | **H3, decisive** |
| `A2` destripe-hp | real | 384×256 | no | hp | none | H3, content-preserving |
| `A3` synth-rect | synth | 384×256 | no | none | none | **H1 + H3 jointly** |
| `A4k` synth-rowfpn | synth | 384×256 | no | none | row, k× | **H3 positive control** |
| `A5k` synth-rowfpn-fixed | synth | 384×256 | no | mean | row, k× | H3 fix confirmation |
| `A6` control-square | real | 256×256 | no | none | none | **H2a + H2b** |
| `A7` synth-square | synth | 256×256 | no | none | none | H2 on isotropic texture |
| `A8` square-transposed | real | 256×256 | **yes** | none | none | **scene vs machinery** |
| `A9` destripe-mean-square | real | 256×256 | no | mean | none | H3 on symmetric geometry |
| `A10` crop-score | real | 384×256 | no | none | none, `--score-region 256,256` | H2a alone |

`k ∈ {1, 8, 64}` where `1×` is the row-FPN amplitude **measured in the real
texture tiles** by this milestone's `fpnscan` mode. The ladder is expressed as a
multiple so that no threshold in this file depends on a number I have not yet
measured.

**A8 is the key experiment.** On a square ROI the machinery is 90°-symmetric by
construction: identical tile, identical band pixel count, congruent band shapes.
Transposing the textures rotates the *scene* (its anisotropy, its FPN
orientation, and which half of each tile each layer gets) while leaving the
machinery alone. Therefore:

- if `shift(A8, vertical) ≈ shift(A6, horizontal)` and
  `shift(A8, horizontal) ≈ shift(A6, vertical)` — the asymmetry rotates with the
  scene, and the machinery is innocent (H2 dead);
- if `A8 ≈ A6` cell for cell — the asymmetry is bolted to the axes, i.e. to the
  machinery (H2 alive).

A8's `bar` is a bar with **horizontal** boundaries — the "h-bar" geometry the
harness does not otherwise have. If it tracks `horizontal`, boundary
orientation, not "bar-ness", is the grouping variable.

### 3.3 Statistics

For an arm, at each regulariser width `g`, over cells `(stack, geometry, step)`
with `step > 0` (30 cells, 10 per geometry):

- `E_g(cell, w)` = mean of `excess_dn` over the 5 seeds. **This is M15's
  `cell_values` recipe and it is what fact 83 is computed from.**
- `w*(cell, g) = argmin_w E_g(cell, w)`, ties to the **smallest** `w`
  (M15's convention: `min()` over an insertion-ordered dict whose windows are
  inserted in ascending order).
- `shift(cell) = w*(cell, 17) − w*(cell, 1)`.
- `med(geom)` = median `shift` over that geometry's 10 cells.
- `narrow(geom)` = #cells with `shift < 0`; `wide(geom)` = #cells with
  `shift > 0`.

**Primary statistic — the orientation asymmetry**

```
A = med(horizontal) − med(vertical ∪ bar)        (20 pooled cells on the right)
U = narrow(horizontal) / 10                       (unanimity of the outlier)
```

M15's published values give `A_ref = −2.5 − med(vertical ∪ bar)` and
`U_ref = 1.00`. `med(vertical ∪ bar)` is not published as a pooled figure; Gate
1 recovers it, and every threshold below is expressed as a **fraction of
`A_ctrl`**, the value M16's own control arm A0 produces, so no threshold depends
on a number recovered after this file was written.

**Secondary statistic — continuous, because a discrete argmin over 10 cells is
coarse.** For each cell, normalise the regret curve at each `g` onto `[0, 1]`
over the fixed ladder, `r_g(w) = (E_g(w) − min E_g) / (max E_g − min E_g)`, and
take the **narrow-preference change**

```
S(cell) = sum over ladder w of  sign(w − 13) * ( r_17(w) − r_1(w) )
```

`S > 0` means the regulariser penalises wide windows more than narrow ones, i.e.
the optimum is pushed narrower. Report `median S` per geometry and
`A_S = medS(horizontal) − medS(vertical ∪ bar)`. This uses every ladder point
rather than one argmin and cannot be moved by a single tie.

### 3.4 Noise floor (discipline 31)

Argmin jitter is estimated by **leave-one-seed-out**: recompute `w*`, `shift`,
`med`, `A` and `A_S` on each of the 5 four-seed subsets and report the spread.
**A difference in `A` smaller than the leave-one-out spread is reported as "not
resolved", never as an effect.** The same rule applies to `A_S`.

Every reported argmin carries M13's `interior` / `ENDPOINT` label, and every
`interior` label is published next to the separation between the argmin and its
better neighbour, in DN (discipline 25 and 31).

### 3.5 Controls

**Null controls — things that must NOT move.**

1. **N1 — no-op treatment.** `--destripe none` must reproduce A0 exactly. Byte
   identity of the CSV. *(A consistency check, not evidence — discipline 20.)*
2. **N2 — zero-amplitude plant.** `--fpn-sd 0` must be byte-identical to no
   `--fpn-sd` flag at all.
3. **N3 — the zero-step stratum.** The 6 `step = 0` cells carry an intensity
   edge, two textures and the full compositing arithmetic but **no depth
   discontinuity** (fact 62: the objective does not turn over there). Their `A`
   must be small and their argmins must be endpoints or plateaus. If the
   zero-step stratum shows the same orientation asymmetry as the decision
   stratum, the effect is not about occlusion at all and the milestone's framing
   is wrong.
4. **N4 — square-ROI machinery symmetry.** On a square ROI with a *synthetic*
   isotropic texture and no FPN (`A7`), the machinery has no remaining
   orientation-dependent term at all. `A(A7)` should be at the noise floor. If
   it is not, something in the machinery is asymmetric that none of H1–H3 names,
   and that becomes the finding.

**Positive controls — things that MUST move.**

1. **P1 — the H3 mechanism must be expressible.** Planting row FPN into the
   isotropic synthetic texture (`A4k`) at some amplitude in `{1, 8, 64}×` must
   move `A` away from `A(A3)` by more than the noise floor, in the direction
   that makes `horizontal` the outlier. **If no amplitude in the ladder moves
   it, then the plant cannot express H3's failure mode and the H3 arms carry no
   information** — that is project rule 13 / discipline 24, and it will be
   reported as "not measured", not as "H3 refuted".
2. **P2 — the fix must undo the plant.** `A5k` (planted FPN + `destripe mean`)
   must return `A` to within the noise floor of `A(A3)` at whatever amplitude P1
   fires. This proves the treatment removes what it claims to remove.
3. **P3 — signal not destroyed.** For every destriped arm, the absolute
   `E_excess` level at `w13` and the aggregate argmin over all 30 cells must
   stay within **20%** and **±3 windows** respectively of the matching
   undestriped arm. A treatment that flattens the objective has not tested
   anything. Reported as a table, per arm.
4. **P4 — the metric is alive.** `E_excess` must still order the ladder: the
   aggregate mean-regret argmin over the 30 cells must remain `interior` in
   every arm. An arm whose aggregate argmin runs to an endpoint is reported as
   "no turnover found within the sweep" (discipline 25) and excluded from the
   `A` comparison.

**Instrument checks.**

5. **G1 — reproduce fact 83.** From M15's committed
   `experiments/m15-regulariser-window/data/edge-{109,119}MSDCF.csv`, with code
   written for M16, recover: `horizontal` 10/10 narrower, median −2.5;
   `vertical` 6/10 wider, median +1.5; `bar` 6/10 wider, median +1.0; ALL median
   0.0. **All twelve numbers must match exactly. If they do not, STOP.**
6. **G2 — the M16 driver reproduces M15's harness.** Arm A0, run with M15's
   exact ladder, widths, seeds, steps, shapes and ROIs, must reproduce M15's
   committed `edge-*.csv` values for every shared column on every shared row.
   Tolerance: **exact string equality** of the formatted numeric fields.
   Byte-identity of the whole file is not required (M16's CSV carries extra
   provenance columns). **If G2 fails, every M16 arm is measuring a different
   experiment from M15 and the milestone reports that instead.**
7. **G3 — the synthetic texture is faithfully re-seeded.** M16 needs two
   *independent* synthetic fields, and `planted::synthetic_texture` has a
   hard-coded seed. M16's `synthetic_texture_seeded` must return a bit-identical
   field to `planted::synthetic_texture` when given that hard-coded seed,
   asserted in a unit test.
8. **G4 — read-only corpus.** `C:\dev\macro`, `D:\macro-dark-frames` and
   `D:\personal\macro` audited with `Get-ChildItem -Force` before and after,
   plus M13's own `audit` mode, both bracketing the whole run.

### 3.6 Plant characterisation, measured before the arms

`fpnscan` mode, reported as descriptive plant properties, not as tests:

- row-mean and column-mean **high-passed** profiles of each real texture tile,
  and their sd in DN — the amplitude H3 has to work with;
- the same for a matched-ISO master bias built from `D:\macro-dark-frames`
  (≥ `(σ_t/σ_FPN)² = 7` frames, M4 §6's rule) — how much of it is sensor rather
  than scene, and whether a dark-derived profile transfers to a lit frame at
  all;
- the realised gradient anisotropy `mean(gx²) / mean(gy²)` of each real tile and
  of the synthetic field — the direct measurement of H1, and the isotropy check
  the synthetic control needs.

## 4. Decision rules

Fixed here, applied mechanically, reported whatever they say. `A_ctrl` is arm
A0's value; `φ` is the leave-one-seed-out noise floor for `A`.

**H3 (primary).**

- **SUPPORTED** iff P1 fires at some amplitude **and** A1 gives
  `|A| ≤ 0.5·|A_ctrl|` **and** `U ≤ 0.7` **and** P3 passes for A1.
- **REFUTED** iff P1 fires at some amplitude **and** A1 gives
  `|A| ≥ 0.75·|A_ctrl|` **and** `U ≥ 0.9`.
- **NOT MEASURED** if P1 does not fire at any amplitude, whatever A1 says.
- Anything else: **UNRESOLVED**, reported with the numbers.

**H1.**

- **REFUTED** iff A3 (isotropic synthetic, no FPN) reproduces the asymmetry:
  `|A| ≥ 0.5·|A_ctrl|`, same sign, and `U ≥ 0.8`.
- **SUPPORTED** iff `|A(A3)| ≤ 0.25·|A_ctrl|` **and** A8's transpose test shows
  the asymmetry rotating with the scene (§3.2).
- Anything else: **UNRESOLVED**.

**H2.**

- **SUPPORTED** iff either (a) `|A(A6)| ≤ 0.5·|A_ctrl|` — squaring the geometry
  removes it — or (b) the transpose test shows `A8 ≈ A6` cell-for-cell rather
  than rotating, with the per-cell median absolute difference below `φ`.
- **REFUTED** iff `|A(A6)| ≥ 0.75·|A_ctrl|` **and** the transpose test shows the
  asymmetry rotating with the scene.
- H2a vs H2b is separated by A10 (band cropped square, plant still rectangular):
  if A10 behaves like A6, the **band shape** carried it; if A10 behaves like A0,
  the **plant aspect** did.

**The headline consequence.**

- If any hypothesis implicating the shared machinery (H2) or a removable sensor
  defect (H3) is SUPPORTED, re-derive M13's window argmin with the correction in
  place: mean regret over the 30 step > 0 cells, at `g = 1` (M13's condition) and
  `g = 17` (the shipped condition).
- **`WINDOW_RADIUS = 13` is declared to change only if** the corrected argmin
  lies outside M13's published basin `w11–w15` **and** the corrected mean regret
  at `w13` exceeds the corrected minimum by more than **0.87 DN** — M15's
  already-registered primary threshold, reused deliberately so this milestone
  cannot pick a friendlier one.
- Otherwise the report states `WINDOW_RADIUS = 13` survives, with the measured
  penalty.

## 5. Predictions, recorded so they can be falsified

Registered before any arm ran. Ranked, with reasons.

1. **H3 will be REFUTED on the real corpus** (60%). The real texture tiles are
   lit photographs of a macro subject; scene gradients there are of order
   10²–10³ DN/px, while M4 measures the whole per-pixel offset FPN at
   **0.377 DN** at base ISO and never decomposes it into row and column terms at
   all — SYNTHESIS §5 item 9 and M5 §3.1 assert "M4's row/column FPN" as an
   *argued* root cause of a dark-frame artefact, not as a measured amplitude in
   a lit frame. Three orders of magnitude is a large gap to close.
2. **H2b (plant aspect) will be SUPPORTED** (50%). It is the largest unforced
   asymmetry in the design: 192 px of layer against 128 px, with an 81 px window
   and a 41 px blur. It also already shows in M15's published levels — median
   `w*(1)` is 9.0 on `horizontal` against 17.0 on `vertical` — i.e. the
   horizontal geometry prefers a much narrower window *before* any regulariser
   is applied, which an aspect-ratio effect predicts and a pure FPN effect does
   not obviously predict.
3. **H1 will be REFUTED** (55%) — the asymmetry will survive on isotropic
   synthetic texture.
4. **P1 will fire only at 8× or 64×**, not at 1× (65%).
5. **`WINDOW_RADIUS = 13` will survive** (80%), because fact 83's shifts cancel
   in aggregate and M15 already priced w13's regret at 0.050 DN at `g = 17`.
6. **The A0 ↔ M15 reproduction (G2) will pass exactly** (85%).

If prediction 1 is right, the deliverable is a clean refutation of the
reviewer's mechanism plus a measured replacement, which is worth more than a
confirmation.

## 6. What this milestone cannot do

- It cannot measure PRNU (multiplicative, signal-proportional). Blocked on the
  flats in `captures-needed.md` §4. If the sensor's fixed pattern in a *lit*
  frame is mostly PRNU rather than DSNU, the dark-derived arm under-reads it and
  the `destripe mean` arm still removes whatever row-structured part exists.
- It cannot separate texture *anisotropy* from texture *inhomogeneity* on the
  real corpus with two subjects. Both are H1 for the purposes of the ruling.
- It cannot say whether the asymmetry matters on **real** occluding edges. Every
  edge here is planted, because that is the only way `ideal` and `oracle` exist.
- It measures only `E_excess`. `W_bleed`, `mis_*` and `dmae_far` are recorded
  but are expected to carry a *separate* orientation defect, noted here before
  measurement so it is on the record as predicted rather than discovered:
  `edge_mode` derives `baseline_lo = max(roi.width/2 − 32, 32)`,
  `baseline_hi = roi.width/2 − 4` and `max_d = roi.width` from `roi.width`
  **regardless of which axis the signed distance runs along**. On a 384×256 ROI
  a vertical edge has `|d| ≤ 192` and a well-populated baseline band
  `[160, 188]`; a horizontal edge has `|d| ≤ 128`, so that band is **empty**,
  `dmae_far` falls back to `0.0`, and `equivalent_width`'s baseline is
  `median(∅)`. **`E_excess` reads neither `baseline_lo/hi` nor `max_d`** — it is
  `mean(e_merged) − mean(e_oracle)` over `|d| ≤ 24` only (`edge.rs::summarise`,
  verified by reading) — which is exactly why it is the primary statistic and
  why this defect, if real, cannot be the explanation of fact 83. Scope of the
  defect is the bleed/mis/`dmae_far` columns. It is reported, not fixed:
  `experiments/m13-window-depth/**` is not writable by this milestone.

---

*Committed before any M16 measurement. Amendments, if any, are appended below
with a timestamp and a reason, never edited in place.*
