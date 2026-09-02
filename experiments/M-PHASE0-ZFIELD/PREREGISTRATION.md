# M-PHASE0-ZFIELD — preregistration

Status: REGISTERED. Written before any statistic in §5 was computed.

Gates: **A5** (depth surface as a solved field), `docs/proposals/2026-08-sota-path.md`
lines 579–676. This lane does not gate C10 or C12.

---

## 1. The question, in the proposal's words

A5's cheap phase-0 gate, quoted verbatim from line 672:

> Cheap phase-0 gate first: **M-PHASE0-ZFIELD**, a corpus-only census of ẑ curvature,
> σ_z, and coherence from existing estimator statistics — if σ_z is so large at corpus
> step sizes that the surface never beats the per-pixel estimate outside already-easy
> regions, kill it for one sprint's cost.

Two further lines of A5 are load-bearing for the bar and are quoted here so the lane
cannot drift from them:

> for a parabola peak under response noise σ_r, σ_z ∝ σ_r / (curvature × step²), so
> confidence is curvature over noise, and it goes to zero exactly where the ground is
> flat and election currently chases noise. (line 600)

> Admission in pass two becomes the union of two rules: A1's energy margin, **or
> |z_i − z(x,y)| ≤ DOF/2 in frame-index units** (DOF from the measured optics: ≈1.3–1.5
> frames at the recommended step, 3–6 at corpus density — M27, SYNTHESIS §1). (line 613)

## 2. Why those three census items are the right three

They are not a list of nice-to-haves. They are exactly the three inputs to the decision,
and they compose:

The surface's *only* job in pass two is to answer `|z_i − z(x,y)| ≤ DOF/2`. That
decision is meaningful only when the surface's own uncertainty is small compared to the
half-width it is being compared against. So the operating question is where
`σ_z ≤ DOF/2` holds.

- **Curvature** sets σ_z through `σ_z ∝ σ_r / curvature`. It is the denominator.
- **σ_z** is the quantity the bar is stated in.
- **Coherence** sets how much a *surface* can improve on a *per-pixel* estimate: pooling
  `N_eff` genuinely-independent, genuinely-same-depth neighbours buys at most
  `σ_z / √N_eff`. With no coherence there is no surface, only a smoother.

This yields a three-way partition of every pixel, which is this lane's primary product:

| Stratum | Definition | Meaning for A5 |
| --- | --- | --- |
| **EASY** | σ_z(per-pixel) ≤ DOF/2 | Per-pixel already decides admission. The surface cannot add value here — this is the "already-easy region" the kill text excludes. |
| **WINNABLE** | σ_z(per-pixel) > DOF/2 ≥ σ_z(surface) | The band A5 exists to serve. **This is the number the lane is being run to measure.** |
| **LOST** | σ_z(surface) > DOF/2 | Neither estimator can decide. A5's own text says this degenerates safely to A1, so it is not a defect — but it is not a win either. |

**Registered decision rule.** The kill text says the surface must *sometimes beat* the
per-pixel estimate outside already-easy regions. WINNABLE is precisely that set. So:

- **KILL** if the WINNABLE fraction is < 2% of valid pixels, median across the eight
  stacks, at native step.
- **SURVIVE** if it is ≥ 10%.
- **INCONCLUSIVE — escalate to a decode-bearing lane** if it lands in [2%, 10%), or if
  any control in §6 fails.

The 2% / 10% bar is registered now, before measurement, and is chosen as follows: A5's
claimed wins are the flat-mid-ground plateau class and the veil class, which in the
corpus census (STATUS, plateau work) occupy of order 10–30% of frame area on affected
stacks. A mechanism that can reach under 2% of pixels cannot be responsible for a defect
class of that size. 10% is the point at which it plausibly can. The gap between them is
declared inconclusive rather than resolved by taste.

**DOF/2 is evaluated at both ends of the proposal's own range** — DOF/2 ∈ {0.65, 0.75}
frames (recommended step) and {1.5, 3.0} frames (corpus density). The verdict is
reported at all four and is only called ROBUST if it agrees at all four. This is the
QUINCUNX λ-robustness discipline, applied on the first pass rather than retrofitted.

## 3. Substrate, and its four stated limits

Primary: the eight per-pixel through-focus response cubes at
`experiments/M66-gate-n-dependence/data/*-d4.npy`, float32 `[frame, y, x]`, all
`(N, 586, 879)` with N ∈ {19, 22, 33, 63, 79, 100, 105, 299}. Verified present, correct
dtype and finite on 2026-08 by this lane.

Supporting: `experiments/M69-focus-noise-sd/out/80-corpus-rho.json` (per-stack noise
calibration ρ, an independent cross-check on §4's σ_r), and M69's own two σ_r estimators
in `src/50-a5-structure.py` (`structure_intercept`, `sg_sigma`).

**Limit 1 — the operator is not the shipping operator.** M66's response is, from
`src/02-fields.py:99–103`, `box_27(|sobel(luma)|) / green_luma_sigma(luma, iso)` then
`box_17(·)`. The shipping estimator's fine field is 5×5. This lane therefore measures a
*more heavily regularised* response than production.

**Limit 2 — the cubes are unaligned.** They are in fixed sensor coordinates. Any real
inter-frame shift appears as apparent depth structure.

**Limit 3 — physical step size is unknown per stack.** Camera focus-step settings were
searched for and NOT FOUND. All σ_z and DOF figures are therefore in **frame-index
units**, which is exactly the unit A5's admission rule is written in, so no conversion
is required for the bar. Physical µm are out of scope for this lane.

**Limit 4 — no metric truth on these eight stacks.** M84b's ruler truth
(`depth-truth-highly-angled-ruler-mm-cpl.npz`, 12.8% valid, median σ 8.28 µm) is on a
stack with no M66 cube. It is therefore **not** used as truth here, and the lane does
not claim metric accuracy.

## 4. σ_r must be measured, not assumed

The M66 response is divided by a per-pixel luma noise sd, so it is a *gradient SNR*, not
a unit-variance quantity. Its noise sd is **not 1** and is not otherwise recorded.

This lane measures σ_r per pixel from the cube itself, with an estimator chosen to be
independent of both of M69's:

    σ_r = MAD_k( r[k-2] − 4r[k-1] + 6r[k] − 4r[k+1] + r[k+2] ) / (0.6745 · √70)

The 5-point kernel annihilates any local cubic, so a smooth focus curve contributes
nothing to leading order; MAD across k makes the peak's real structure a minority
outlier. Frame-to-frame noise is independent (separate exposures), so the √70 is exact
under iid noise. Requires N ≥ 5; all eight stacks qualify.

**Registered cross-check (C3).** This estimator is compared against M69's
`structure_intercept` and `sg_sigma` on the same cubes. Registered tolerance: the three
medians must agree within a factor of 1.5. Disagreement beyond that halts the lane.

**σ_z, derived here rather than cited.** For a 3-point parabola through
`(k−1, y_l), (k, y_c), (k+1, y_r)` the peak offset is `x* = (y_l − y_r) / (2D)` with
`D = y_l + y_r − 2y_c` (negative at a maximum, `D = 2a`). Evaluated at the symmetric
point, `∂x*/∂y_l = 1/(2D)`, `∂x*/∂y_r = −1/(2D)`, `∂x*/∂y_c = 0`, giving

    σ_z = σ_r / (|D| · √2)

in frame-index units. This is A5's `σ_r / (curvature × step²)` with the step already
absorbed into the index-unit curvature.

## 5. What will be computed

- **Z1 — curvature census.** Distribution of `|D|` per stack; fraction with `D ≥ 0`
  (no interior maximum, ẑ undefined); fraction below the noise floor `|D| < 2σ_r`.
- **Z2 — σ_z census.** Per-pixel σ_z; median and quantiles per stack; the EASY /
  WINNABLE / LOST partition at all four DOF/2 values.
- **Z3 — coherence census.** (a) The **noise correlation length** of the response field,
  measured from the spatial autocorrelation of the 5-point residual, which sets the true
  `N_eff` of a pooling window. (b) The spatial autocorrelation of ẑ itself. (c) The
  fraction of ẑ variance in a window attributable to a coherent gradient versus
  salt-and-pepper.
- **Z4 — step ladder.** Every statistic recomputed on cubes decimated along the frame
  axis by 2 and 3, giving a controlled step ladder with subject and optics held fixed.
  Registered prediction: σ_z falls with coarser steps in *index* units (curvature per
  index rises), while DOF/2 in index units falls faster, so the WINNABLE fraction should
  **shrink**. Registered before measurement.

`σ_z(surface)` is computed as `σ_z(per-pixel) / √N_eff` with `N_eff` **deflated by the
measured noise correlation length from Z3(a)**, never the nominal window area.

## 6. Bias directions, declared before measuring (house rule 18)

| # | Bias | Direction | Handling |
| --- | --- | --- | --- |
| B1 | M66's 27×27 + 17×17 regularisation smooths the response spatially | **Favours A5** — inflates apparent ẑ coherence and pooling gain | A SURVIVE verdict from this substrate is weak and must be labelled as such in the note. A KILL verdict is strong, because it kills despite a favourable substrate. |
| B2 | σ_z ∝ 1/\|D\| is a ratio with a noisy denominator; heavy-tailed, mean biased up | **Against A5** | Report medians and quantiles only. Never a mean σ_z. |
| B3 | `N_eff = window area` assumes independent neighbour noise, which box regularisation destroys | **Favours A5**, potentially by a large factor | Z3(a) measures the correlation length and deflates `N_eff`. Registered as the single most likely way this lane could wrongly let A5 live. |
| B4 | Unaligned cubes (limit 2) inject shift as apparent depth structure | **Favours A5** — adds spurious large-scale coherence | Z3(b) reports coherence at multiple scales so a global ramp is separable from local smoothness. |
| B5 | argmax-based `k` is biased toward noise spikes where curvature is low | **Against A5** in the low-curvature stratum | Report the stratum's size, not just its σ_z. |

Three of five biases favour A5. **The substrate is therefore charitable to A5 by
construction, and the lane is written to make a kill hard rather than easy.**

## 7. Controls, registered

- **C1 — planted-σ recovery.** Add known Gaussian noise of sd `s` to a Savitzky-Golay
  smoothing of a real cube; require §4's estimator to recover `s` within 10% over
  `s ∈ {0.5, 1, 2} × ` the measured σ_r. (M69's `k3` discipline, independently written.)
- **C2 — planted-ẑ recovery.** Synthesise a cube whose peak location is a known smooth
  ramp plus a known step; require ẑ to recover the ramp within the predicted σ_z, and
  require the measured σ_z to match the empirical scatter within 20%. **This is the
  positive control: it proves the σ_z scale is real and not merely self-consistent.**
- **C3 — σ_r cross-check** against M69's two estimators, factor-1.5 tolerance (§4).
- **C4 — null.** On a synthetic cube of pure noise with no focus structure, require the
  WINNABLE fraction to be < 2% (i.e. the instrument must return KILL when there is
  nothing to find).
- **C5 — inverted conclusion.** On a synthetic cube with very high curvature and low
  noise everywhere, require WINNABLE ≈ 0 *via EASY saturation*, not via LOST. This
  distinguishes "no room to improve" from "cannot estimate", which the headline number
  alone conflates.
- **C6 — N_eff deflation fires.** Require the measured noise correlation length on real
  M66 cubes to be > 1 px, confirming B3 is a real effect and the deflation is not a
  no-op. A deflation factor of exactly 1.0 would mean the control never fired.

## 8. What would falsify this lane's own verdict

- If C3 fails, σ_r is wrong and every σ_z is wrong by a common factor; the partition
  moves and the verdict is void.
- If C2's σ_z does not match empirical scatter, the Gaussian first-order propagation in
  §4 is inadequate at these SNRs and the lane must move to a Monte-Carlo σ_z.
- If Z3(a) finds a correlation length comparable to the pooling window, `N_eff → 1`, the
  surface reduces to a smoother, and A5's central claim fails on this substrate
  regardless of the WINNABLE fraction.
- A SURVIVE verdict does **not** license A5. Per B1/B3/B4 it licenses only the next,
  decode-bearing lane on the shipping 5×5 operator with aligned frames.

## 9. Reproduction

    python experiments/M-PHASE0-ZFIELD/src/z1_census.py
    python experiments/M-PHASE0-ZFIELD/src/z2_controls.py
    python experiments/M-PHASE0-ZFIELD/src/check_note.py
    python experiments/M-PHASE0-ZFIELD/src/commission_note.py

Outputs land in `experiments/M-PHASE0-ZFIELD/out/`. No file under `D:\personal\macro` is
written. No RAW is decoded.

---

## Amendment 1 — the analytic σ_z is unusable, and the controls proved it

Registered 2026-08, after running §7's controls and **before** computing any census
statistic in §5. All four numbers below come from `out/z2-controls.json`, run 1.

### A1.1 The §4 derivation was evaluated at a special point and applied generally

§4 derived `σ_z = σ_r / (|D| · √2)` "at the symmetric point", where `y_l = y_r` and the
sub-frame offset `x*` is zero. That step is correct but the result was then applied to
every pixel. Carrying the general offset through:

    ∂x*/∂y_l = (D − n)/(2D²),  ∂x*/∂y_r = −(D + n)/(2D²),  ∂x*/∂y_c = n/D²

with `n = y_l − y_r = 2D·x*`, giving

    σ_z = σ_r · √(1 + 12 x*²) / (|D| · √2)

Since `x*` is near-uniform on [−0.5, 0.5], the omitted factor averages `√2` and reaches
`2` at an interval edge. **This is a disclosed error in the preregistration**, not a
finding.

### A1.2 Even corrected, first-order propagation is inadequate — §8's escape hatch fires

Measured against a planted-ẑ truth (C2, 96 noise realisations, known ramp + 2-frame
step):

| σ_z estimator | predicted | empirical sd | ratio |
| --- | --- | --- | --- |
| §4 as registered | 0.1454 | 0.2634 | **0.552** |
| §4 with the A1.1 correction | 0.1965 | 0.2634 | **0.746** |
| per-pixel parametric bootstrap | 0.3000 | 0.2634 | **1.139** |

Both analytic forms are **optimistic**, which is the dangerous direction: they would
have inflated EASY and shrunk LOST. The residual after A1.1 is the discrete
argmax flip, which no smooth first-order propagation can represent.

§8 registered the response: *"If C2's σ_z does not match empirical scatter, the Gaussian
first-order propagation in §4 is inadequate at these SNRs and the lane must move to a
Monte-Carlo σ_z."* It does not match, so the lane moves.

**The replacement.** Per-pixel parametric bootstrap: Savitzky-Golay (window 9, order 3)
the measured curve along the frame axis to get a working truth, add fresh Gaussian noise
at the pixel's own measured σ_r, re-run the full argmax-plus-parabola estimator, and take
the sd of ẑ over 64 realisations. It uses the **real measured curve shape** at each
pixel rather than a parabolic idealisation, and it inherits every discreteness the real
estimator has because it runs the real estimator.

Its 1.139 ratio errs **conservative**. Per §6 that is a bias against A5, so it cannot
manufacture a survive verdict.

### A1.3 The peak-reality gate is no longer needed, because the bootstrap subsumes it

C4 was registered to check that a pure-noise cube is not called placeable. Under the §4
analytic σ_z it failed catastrophically:

| cube | analytic median σ_z | analytic EASY | bootstrap median σ_z | bootstrap fraction ≤ DOF/2 |
| --- | --- | --- | --- | --- |
| pure noise, n = 22 | 0.1907 frames | **90.2%** | 5.85 frames | **0.2%** |
| pure noise, n = 105 | 0.1416 frames | **97.9%** | 29.67 frames | **0.0%** |

The analytic form conditions on the argmax, and an argmax over pure noise *is* a spike,
so it reports high curvature and therefore high confidence. The bootstrap has no such
blind spot: it lets the argmax wander, sees it wander across the whole stack, and
reports σ_z of order the stack length.

A separate `|D|/σ_r` gate was considered and is **not** adopted: the null's own
`|D|/σ_r` is 3.66 at n = 22 and 4.97 at n = 105, so any fixed threshold is N-dependent
and would need its own calibration. The bootstrap needs none.

### A1.4 C3 becomes a truth test rather than an agreement test

As registered, C3 compared this lane's σ_r against M69's two estimators and demanded
agreement within 1.5×. Measured on `113MSDCF-d4`: this lane 0.0179, M69 `sg_sigma`
0.0426 (2.4×), M69 `structure_intercept` 0.0810 (4.5×). The registered test fails.

The three estimators average the residual over different frame spans — 5 frames here, 11
for the Savitzky-Golay arm, 12 for the structure function's τ ≤ 6 — so on a cube whose
focus curve has real structure at those scales they *must* disagree, and the widest span
must read highest. That is the observed ordering.

Agreement was therefore the wrong test. **C3 is replaced by C3′: run all three
estimators on a cube with planted noise of known sd, and require this lane's estimator to
recover it within 10%.** The two M69 estimators are reported alongside, without a
pass/fail bar, because they are being used outside the frame-span regime they were
written for. This is a change of instrument, not a relaxation: C3′ is strictly harder for
this lane's estimator than C3 was, because it must hit a truth rather than match a peer.

### A1.5 Bias B3 is confirmed, and it is the dominant term

C6 measured the response noise correlation length on `113MSDCF-d4`: 1/e at **7 px in x
and 14 px in y**, giving `n_eff(9×9) = 1.58` against a nominal 81 — a deflation of
**51×**. The pooling gain a 9×9 surface can buy is therefore `√1.58 = 1.26×`, not `9×`.

§6 named B3 as "the single most likely way this lane could wrongly let A5 live". It is
real and it is large. No further amendment follows from this; the registered deflation
handles it. The x/y asymmetry is noted and not explained.

### A1.6 What does not change

The §2 partition, the 2% / 10% verdict bar, the four DOF/2 values, the eight stacks, and
every bias direction in §6 stand exactly as registered. Only the σ_z *estimator* and the
σ_r *control* change, and both changes move the lane against A5.
