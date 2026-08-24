# M92 — PRE-REGISTRATION

**Written and committed before any arm of this milestone was run.** No number in
this file was chosen after seeing a result of the experiment it governs. The one
thing already measured at the time of writing is recorded explicitly in §0 so
that it cannot be mistaken for a post-hoc discovery.

**Milestone question, in M57's own words (`M57-detail-metric-from-first-principles.md`
§0, §11 item 2, Q-b):** does the independent-noise null's per-ROI scatter — 0.343 px
per 512² ROI, where the truth is exactly 0 px — **average down across disjoint
ROIs**? M57 costed it at 3–17 ROIs in S8(b) and did not run it.

**This milestone does not propose a detail metric.** Facts 617/708 prove the
single-frequency correlation family cannot work and fact 809 records the fourth
hunt rejecting that class before measurement. `dsig` is imported unmodified from
`experiments/m57-shape-metric/src/m57lib.py` and is treated as a fixed
instrument. Any change to `m57lib` would confound this result with an
implementation difference and is forbidden to this milestone.

---

## 0. What was already measured before this file was written

Two facts were established during setup, before any arm ran, and are declared
here so they are not later presented as results of the experiment:

1. **MEASURED (EXIF, `m41lib.iso_of`, all frames of each stack):**
   `112MSDCF` = ISO 500 (79/79), `113MSDCF` = ISO 500 (63/63),
   `foam` = ISO **1000** (100/100), `109MSDCF` = ISO **160** (22/22),
   `wrapped-text-1` = ISO **100** (130/130), `wrapped-text-2` = ISO **400** (120/120).
2. **MEASURED (source read):** M57's `s5_real_nulls.py`, `s6_debias.py` and
   `s7_bias_or_variance.py` each set `ISO = 500` as a module constant and use it
   for **every** cell, so the noise injected into the `109MSDCF` and `foam` cells
   was scaled by the wrong conversion gain and the wrong read-noise branch.
   **MEASURED (`out/s6_debias.json`):** the 0.34310 px figure — M57's PR14 worst,
   the bound M82 froze, and the number this milestone was dispatched against —
   is `109MSDCF/flat`, `n1_K1 dsig[1]`, i.e. the 2× level on an ISO-160 stack run
   at ISO 500.

Consequence for this pre-registration: every arm is run at the **correct
per-stack ISO** as primary, and `109MSDCF` is additionally run at M57's ISO-500
setting as a declared comparison arm (A1f). The size of that discrepancy is a
registered secondary result, not the milestone's verdict.

---

## 1. Instrument, frozen

* `dsig` = `m57lib.dsig`, imported, unmodified, byte-identical to the committed
  M57 file. Band `[0.05, 0.2762]` cyc/px, `NBIN = 64`, `N_SECT = 16`, `n = 512`.
* Merge = `m57lib.merge_subset` (arm A: regularised winner field + noise-gated
  average), `pad = 32`, `gate = 0.50` unless an arm says otherwise.
* Split = `m57lib.splits(nf)["parity"]`.
* Focus fields = `m41lib.focus_fields(cube, g, 1.47)` with `g = ISO/436.8` for
  the stack's own EXIF ISO. `RN_E = 1.47` is m41lib's frozen value (rule 15) and
  is left alone in the operator; the M48-corrected read noise
  (`RN_E_HIGH = 1.2392`, `RN_E_LOW = 4.20`) is used only in the **noise model**
  that sets the injected sigma, exactly as M57 does.
* The only new code is the loader (one decode per frame, scattered to all ROIs,
  instead of one decode per frame per ROI) and the averaging/correlation
  harness. The loader is asserted equal to `m57lib.load_cube` on one ROI.

## 2. The null

**N1, from M57 S5.** Add independent Gaussian noise of standard deviation
`mult × sm` to each of the two half-merges, where
`sm = sqrt(noise_var_dn(median(ma), g(ISO), rn_e(ISO))) / sqrt(n_eff)` is the
merged **temporal** sigma from the calibrated model (rule 10 — never a spatial
sd). The common transfer is untouched, so the true equivalent-blur difference is
**exactly 0 px** on any scene at any level.

Primary level `mult = 2.0`, because that is the level at which M57's 0.34310 px
was measured. `mult = 1.0` and `mult = 3.0` are reported alongside.

## 3. Geometry — disjoint means disjoint, including the pad

Green-quad plane is 2344 × 3514 (`raw_image_visible` is 4688 × 7028). A 512²
quad ROI reads a 576² padded footprint.

**Disjoint grid, 24 ROIs**, origins `(x, y)` in quad coordinates:
`x ∈ {32, 608, 1184, 1760, 2336, 2912}`, `y ∈ {32, 608, 1184, 1760}`.
Stride 576 = 512 + 2 × 32, so **the padded footprints are disjoint as well as the
ROIs**. Full coordinate list is emitted to `out/`.

**Overlapping grid, 24 ROIs** (positive control):
`x ∈ {32, 160, 288, 416, 544, 672}`, `y ∈ {32, 160, 288, 416}` — stride 128,
each ROI sharing 75% of its width and height with its neighbour.

**ROI screen, fixed before any null draw.** An ROI is retained only if, on the
**noiseless** half-merge pair, `dsig(rs1, rs1_blurred_by_0.10px)` is finite. This
screen uses no null data. Screened-out ROIs and their coordinates are reported.
If a retained ROI returns `NaN` on a null draw, that ROI is `NaN` for that draw;
any (draw, subset) containing a `NaN` is dropped and the drop rate is reported.
If the drop rate exceeds 10% on any stack the arm is reported as unreadable.

## 4. Estimator and the quantity being bounded

Per ROI `i` and draw `r`, `d_{i,r}` = `dsig(...)["px"]`.

**Primary estimator:** `dbar(S, r) = mean_{i∈S} d_{i,r}` over a set `S` of `N`
distinct retained ROIs. This is M82's unit — px of equivalent blur — and it is
the coordinate in which 0.343 px and 0.1754 px are both quoted.

**Null magnitude** (truth is exactly 0, so this is an RMS about zero, not a sd
about a mean):

&nbsp;&nbsp;&nbsp;&nbsp;`Null(N) = sqrt( mean over (r, S) of dbar(S, r)² )`

with `R = 128` draws and, for each `N < 24`, 200 subsets drawn uniformly without
replacement from the retained ROIs. Uncertainty on `Null(N)` from a 2000-sample
bootstrap over draws.

**Averaging exponent** `α`: OLS slope of `−log10 Null(N)` on `log10 N` over
`N ∈ {1, 2, 3, 4, 6, 8, 12, 16, 24}` (truncated to the retained count).
`α = 0.5` is exact independence; `α = 0` is a hard floor.

**Mandatory sensitivity variant, reported whether or not it agrees:** the
slope-domain estimator `px = sign(b̄)·sqrt(|b̄|)` where `b̄ = mean_i b_i` is the
mean of the per-ROI OLS slopes. **If the primary and the variant disagree on the
verdict, the verdict is NOT ESTABLISHED and both numbers are reported.**

## 5. Bars — fixed here, before any arm

Let `E = 0.1754 px`, the largest finite central sharpness price M82 measured
(fact 1140), and `B = 0.343 px`, M57's per-ROI null bound.

* **SHIP** — *the null averages down and sharpness is measurable at N ROIs* —
  requires **all** of:
  * `α ≥ 0.40` on **every** stack, primary estimator, primary level; and
  * `Null(4) < E` on **every** stack; and
  * the placebo recovery ratio (§6) in `[0.85, 1.15]` at `N = 24` on every stack; and
  * both negative controls (§6) red.
* **NO SHIP** — *the route is dead and the floor is the result* — if **either**:
  * `Null(24) ≥ E` on any stack, or
  * `α < 0.15` on any stack.
  In that case the reported result is the measured floor `Null(24)` and the
  common-mode fraction `r̄` implying it.
* **NOT ESTABLISHED** — anything else, including any disagreement between the
  primary and the sensitivity variant. Report `N_req` = smallest `N` in the
  ladder with `Null(N) < E`, per stack, or `> 24` if none.

**Correlation.** `r̄` = mean of the off-diagonal Pearson correlations of
`d_{i,·}` against `d_{j,·}` over the `R` draws, across all retained pairs.
`r̄ ≥ 0.10` is declared **material common mode**; the implied asymptotic floor is
`Null(1)·sqrt(r̄)` and the effective ROI count is `N/(1 + (N−1)·r̄)`. Both are
reported with a bootstrap interval regardless of the value.

**Standard errors.** Every error bar in this milestone comes from **empirical
repetition**, never from the jackknife (M57 S7 PR19: the sector jackknife is
anti-conservative by a median factor of 1.90). The ratio
`sd(draws) / median(jackknife se)` is re-measured on this milestone's own
configuration and reported.

## 6. Controls — and what makes each one fail

* **RC — reproduction.** Single-ROI null at M57's own three S7 cells
  (`112MSDCF/flat` 2747,32; `112MSDCF/detail` 1671,1373; `109MSDCF/centre`
  916,1501) at `mult ∈ {1,2,3}`, at **M57's ISO-500 setting**, must reproduce
  M57 S7's `sd(draws)` within a factor of 2 in both directions. **Fails if** my
  harness has drifted from M57's; the whole milestone is then void.
* **PL — placebo.** Plant a Gaussian blur of exactly `E = 0.1754 px` on **both**
  halves of configuration 2 at every ROI, so the truth is `+0.1754 px` at every
  ROI. The averaged estimator must recover it. Recovery ratio reported at every
  `N`. **Fails if** the ratio leaves `[0.85, 1.15]` at `N = 24` — i.e. if
  averaging destroys the signal as well as the noise. A second planted level of
  `0.10 px` is run for comparability with M57's PR4.
* **PL2 — placebo at the decision point.** With the same plant, report the
  fraction of (draw, subset) pairs at each `N` for which the averaged estimate
  exceeds `Null(N)`. This is the operational statement of "can the instrument
  read M82's effect at N ROIs".
* **NC1 — common-mode injection (must go red).** One noise realisation per draw,
  added **verbatim at every ROI**. Registered expectation: `α < 0.15` and the
  SHIP criterion red. **If NC1 is not red, the instrument is not measuring what
  this milestone claims and no verdict is issued.**
* **NC2 — broken averaging (must go red).** Replace the `N` distinct ROIs with
  the **same** ROI repeated `N` times. Registered expectation: `Null(N)` exactly
  equal to `Null(1)`, `α = 0.000`, SHIP red. This control tests the averaging
  code itself, not the physics.
* **OV — overlap (positive control).** The stride-128 overlapping grid must give
  `α_overlap < α_disjoint`. **If it does not**, the instrument does not respond
  to shared noise and the disjoint result is not trustworthy; report the
  disagreement rather than the favourable arm.
* **Rule 9 — flat ROI.** `hp_sd` is recorded for every ROI before any null runs,
  the grid is reported split at its median into a low-texture and a high-texture
  half, and the low-texture half is reported **first** in every table.

## 7. Arms

| id | what | why |
| --- | --- | --- |
| A1 | N1 null, synthetic i.i.d. Gaussian, per-ROI per-draw independent, correct per-stack ISO | M57-faithful primary. **Declared limitation: the injected noise is independent across ROIs by construction, so A1 cannot exhibit injection-driven cross-ROI correlation. Its `r̄` is a control on the correlation estimator, and its between-ROI structure comes only from the real merges' own fixed content.** |
| A1f | A1 on `109MSDCF` at M57's hard-coded ISO 500 | measures §0's defect directly |
| A2 | N1 null with the injected noise taken from **real dark frames** — `(dark_k − dark_l)/√2`, green quad, cropped at each ROI's true sensor coordinates from one physical pair per draw per half, rescaled to `mult × sm` | the only arm in which a real global, row or column term can couple disjoint ROIs. **This is where `r̄` has power to be non-zero.** The difference removes the fixed pattern, which is common to both configurations in the real use case and cancels in the log ratio, and keeps the temporal structure, which does not. |
| NC1, NC2, OV, PL, PL2, RC | §6 | controls |
| G | gate contrast: config 1 = gate 0.50, config 2 = gate 0.99, both from the same frames, `dsig` per ROI, averaged | M57 P11's strategic finding, re-read with the averaged instrument. **Non-decisional for the verdict.** |

## 8. Stacks

| stack | frames used | EXIF ISO | why |
| --- | --- | --- | --- |
| `112MSDCF` | `[6:68]`, 62 | 500 | M57's own cell; ISO correct in M57 |
| `109MSDCF` | `[0:22]`, 22 | 160 | M57's own cell; different frame count; §0's ISO defect lives here |
| `wrapped-text-1` | all 130 | 100 | M82's stack — the capture the 0.1754 px price was measured on |

Three ISOs, three frame counts (22 / 62 / 130). Fact 127 stands: a result on one
stack is a result on one stack, and every headline is reported per stack.

## 9. What would make me report a negative

A floor above 0.1754 px, or `α < 0.15`, is a **first-class result** and will be
reported as the milestone's answer without hedging: it converts "we might be
able to measure sharpness" into "we cannot, by this instrument, and here is the
number". A measured `r̄ ≥ 0.10` with a floor above `E` is the strongest form of
that answer.

## 10. Things I expect to be wrong about

Recorded now so it is visible later. I expect: (a) `α` near 0.5 on the disjoint
grid in A1, because A1's injection is independent by construction; (b) `α`
materially below 0.5 in A2 if any global term exists; (c) the between-ROI
dispersion of the per-ROI mean `μ_i` to be the term that sets the floor, not the
within-draw scatter; (d) the ISO-500 defect on `109MSDCF` to inflate M57's null
by a factor between 1.3 and 2.0. If (a)–(d) come out otherwise they are reported
as wrong predictions.
