# M103 — the alignment solve recovers half the drift

Status: complete. The defect is found, fixed, and measured end to end on the
owner's stack. The fix ships in `crates/strehl-core/src/align.rs`.

**Every claim below is labelled MEASURED, DERIVED or ARGUED.** Every number can be
re-run from committed scripts; §14 gives the commands in order.

---

## 1. Summary

**MEASURED.** The shipped solve recovers **52.4%** of the true log-scale drift on
`bee-3-cpl`. The corrected solve recovers **105.4%**. On the absolute end-to-end
check the residual misregistration falls from **150.3 plane px to 2.9 plane px**,
which is **50.1% → 99.0%** of the drift removed — a **52x** reduction.

**The cause is not blur asymmetry, and it is not a stray factor of two.** It is a
compound of two things, both of which had to be fixed together:

1. **Coarse-stage capture starvation** (the dominant term). The plane is
   3516x2344, the tile-centre lever reaches 1891 px, and at the true scale the
   corner displacement is ~270 plane px. `AlignConfig::deep()` searches ±80 plane
   px. Long edges are refused outright, the surviving tiles are the low-lever
   central ones — the ones carrying least scale information — and the censoring is
   self-confirming because tiles survive only where the already-wrong seed
   predicts them.
2. **Peak-locking in the sub-pixel refinement.** `ncc_tile` rounds the seed to an
   integer, so the *only* sub-pixel information in the estimator is a 3-point
   parabola, and on real pairs that parabola piles its answers onto integers. The
   radial displacement ramp that *is* the scale signal is destroyed at short
   baselines.

**The second one explains a rule the corpus has held for a long time without a
mechanism.** AGENTS rule 6 records that "short-baseline edges under-report
magnification change", that the effect "lives below ~0.5 px of differential
displacement", that its magnitude "is a property of the scene, not of the optics",
and that **"no measurable property of the edge sets predicts it"**. M103 measures
one that does: the concentration of the per-tile displacement fractional parts,
which tracks published shrinkage across six stacks at Spearman **rho = -0.886**
(§10).

**A second, independent defect was found in the deciding instrument itself** and
had to be repaired before the fix could be scored honestly (§6). M97's
`signtest.py` **cannot report a residual above 1.0**. A correctly solved sidecar
lands slightly above 1.0. Uncorrected, it scores the fix at a flattering and false
"0.1 plane px, 100.0% removed".

---

## 2. What shipped

`crates/strehl-core/src/align.rs`, additive only. No public signature changed and
no existing default moved (B6, §8).

| addition | what it does |
|---|---|
| `AlignConfig::fine_iters` | re-seed the fit and refit until the plane corner moves < `FINE_CONVERGE_PX`. Defaults to `1` (today's behaviour). |
| `AlignConfig::warp_tiles` | correlate the moving tile on the reference tile's **warped** lattice instead of an axis-aligned box. Defaults to `false`. |
| `sample_bilinear_strict` | refuses outside the plane instead of clamping. |
| `ncc_tile_warped` | builds a `(tile + 2*radius)^2` patch along the warped lattice, then searches inside it. |
| `fit_stage_iterated` | drives the re-seeding; a failing pass leaves the previous fit standing. |
| `AlignConfig::iterated()` / `iterated_wide()` | `deep()` / `wide()` plus `fine_iters 8` and `warp_tiles true`. |

`AlignConfig::iterated_wide()` is the configuration that produced every headline
number.

**Why `sample_bilinear_strict` rather than the existing `sample_bilinear`:** the
existing one clamps at the plane edge, which fabricates plausible samples exactly
at the corners where the whole mechanism lives. Clamping would have hidden the
defect inside the fix.

**This is not a fitted shrinkage correction and rule 6's prohibition does not
apply.** Nothing is fitted, nothing is transferred between scenes, and there is no
free parameter tuned on `bee-3-cpl`. The change is to how each pair is *measured*,
and the same code with the same constants is a 0.47% no-op on `112MSDCF` (§8, B4).

---

## 3. Corrections to the commission (AGENTS rule 43)

Recorded in `PREREG.md` **before** any treatment ran, and repeated here because
they change what future milestones should believe.

- **Candidate fix 1, "per-edge metacalibration", is M23's R4 and it is already
  dead.** Facts 170, 171, 175, 176, 177, 178. Its local-linearity premise is
  refuted on the very edges it would correct (`R` = 0.5264 at delta=1e-4 against
  0.9928 at delta=8e-4), and a *shuffled* `R` reproduces 93.3% of its effect.
- **Candidate fix 2, "blur equalisation", is M78's R5 and it is already dead.**
  Facts 1097, 1098, 1099. The commission states that "as far as the corpus knows
  this has never been applied to focus-stack registration". **That is false.**
- **The commission's leading hypothesis rests on a withdrawn attribution.**
  Fact 45's 0.56 recovery ratio has had its causal reading withdrawn by M23 at
  fact 174: the mechanism was the plant's own bilinear resampler, not blur
  asymmetry. A zero-defocus self-pair on the same harness reads 0.372 — *further*
  from unity than the real defocus pair.

**M103 independently corroborates fact 174 from the opposite direction** (§5.3):
resampling a plant *suppresses* peak-locking, so a resampled plant reads a
response of 1.00 while the real pairs it is standing in for read 0.16. Any plant
built with a resampler is blind to this mechanism.

**Neither candidate was pre-registered as a primary arm, and neither was
implemented.** What genuinely reopened the question is that both R4 and R5 were
scored on **held-out pairwise error**, which M97 proved is structurally blind to a
global multiplicative gain error.

---

## 4. Trivial explanations, ruled out with the number that rules each out

The commission required these be killed first. **All MEASURED.**

| candidate | ruled out by |
|---|---|
| an exact factor of 2 | per-span recovery is a **ramp**, 0.138 at span 1, 0.847 at span 16, 0.260 at span 128. A `/2` is flat at 0.5. |
| mid-stack reference quoted end-to-end | the sidecar's own ends are 1.050368 / 0.968875; ratio 0.922414 **is** the end-to-end span. Reference 0 and reference 149 give identical spans (both emitted, §14). |
| log vs linear confusion | ln gives 0.080761/0.154154 = **0.524**; linear gives 0.077586/0.142860 = **0.543**. 3.6% apart. Both are ~half; neither is the cause. |
| averaged where summed | the solve is a global LSQ over 1961 edges with `cycle_rank 1663`. Not a chain. Long-span-only solves are *worse* (0.943), so short edges are not diluting long ones. |
| plane px vs sensor px | `\|a\|` is dimensionless. The independent truth ladder uses a DOWN=4 green sub-lattice — a different pixel convention entirely — and agrees to five decimals. |
| half-step in the pyramid, `/2` in the centre of mass | `parabola` is the standard 3-point vertex formula. A half-step bug gives a constant offset, not a ramp. |
| MAD outlier cut | swept `outlier_mads` 3 -> 6 -> 100: span-1 chain moves only 0.163 -> 0.193 -> 0.229. Contributes ~40% relative, is not the cause. |

**The solver itself is exonerated by exact reproduction.** MEASURED: the probe
re-solving the shipped edge set returns `|a_0| = 1.050368`, `|a_298| = 0.968875`
against M97's quoted 1.0504 / 0.9689 — six-digit agreement. The solve is a
faithful least-squares fit to edges that are themselves wrong.

---

## 5. The mechanism

### 5.1 Ground truth

**MEASURED, three independent implementations.** A feature at radius `r` in frame
0 of `bee-3-cpl` sits at **0.857140 r** in frame 298 (ln = -0.154154). M97
measured 0.85714; the orchestrator measured 0.85715 with no strehl code at all;
M103's `src/truth.py` reproduces 0.85714 on a DOWN=4 green sub-lattice; and
`signtest.py`'s own RAW arm reads 0.85714 (0.85719 under the repaired two-sided
search). Four routes, five decimals.

### 5.2 Capture starvation

**MEASURED.** `deep()` uses `coarse_factors [8]` and `coarse_radius 10` — a total
capture of **±80 plane px** — against a corner displacement of ~270 plane px. A
`fine_tile` of 128 under a 14.3% scale mismatch is stretched **18.3 px across its
own width**, which a pure-translation NCC cannot undo; widening the window makes
it worse, which is why run `B` (`wide`) over-shoots to 1.27 at span 256 while
`deep` under-shoots to 0.11.

Consequences, all MEASURED from `data/A-deep-edges.csv`:

- `Border` refusals dominate at every span >= 8 — **68.7 of 96 tiles at span 16**.
- `used` collapses to the `min_tiles = 8` floor by span 64.
- The direct `(0,298)` edge is **refused outright** (`TooFewTiles { correlated: 6 }`).
  **The shipped solve has no long-baseline anchor at all.**
- Planting the true scale 0.857 on a real frame is refused with
  `CoarseStageFailed { level: 0 }` — an independent confirmation of the range limit.

### 5.3 Peak-locking

`ncc_tile` (~L757) does `let (bx, by) = (px.round() as i32, py.round() as i32);`.
The unwarped path rounds the seed to an integer, so the only sub-pixel information
in the estimator comes from the 3-point parabola — and that parabola is locked.

**MEASURED.** Fractional parts of per-tile displacements; uniform would give a
mean |frac| of 0.25:

| pair | mean \|frac\| | histogram (10 bins over ±0.5) | rms | fitted g vs truth |
|---|---|---|---|---|
| REAL (0,1) | **0.0761** | `1 0 7 18 67 66 12 3 4 2` | 1.358 px | -1.38e-4 vs -5.1e-4 |
| PLANT 0.9995 | **0.1827** | `20 0 14 14 48 48 14 14 0 20` | 0.116 px | -5.03e-4 vs -5.0e-4 |
| REAL (0,8) | **0.0476** | `0 1 0 2 28 41 5 0 1 0` | 0.898 px | -2.5e-5 vs -2.6e-3 |

Lever-binned radial displacement is a clean monotone ramp on the plant
(-0.122, -0.381, -0.669, -0.935) and **pure noise on real pairs**
(-0.389, +0.221, -0.507, -0.065).

This explains the whole recovery ramp: at span 1 the scale signal is entirely
sub-pixel and is destroyed; by span 32 the signal is much larger than the locking
error and recovery reaches 0.80-0.92; past span 64 censoring and decorrelation take
over again.

### 5.4 The self-criticism that matters most

**My own positive control has a discipline-615 blind spot, and I am reporting it
rather than burying it.**

**MEASURED.** On *planted* scales the **shipped, untreated** estimator responds
**1.00** across 5e-4 to 0.10, with both resamplers agreeing and the zero-plant
exact. Taken alone that says there is no estimator bias at all — and it is
consistent with the brief's blur-asymmetry hypothesis being wrong, which it is.

But it is also **wrong as a test of this estimator**, because the plant resamples,
and **resampling smooths the correlation peak and suppresses peak-locking**. The
plant perturbs the mechanism it is measuring through. That is precisely the
failure discipline 615 exists to name, and it is why a 1.00 planted response
coexists with a 0.16 real-pair recovery in the same codebase on the same day.

It is also, independently, the same failure M23 found at fact 174. **Two
milestones have now been misled by a resampled plant on this exact question.**

---

## 6. The deciding instrument is one-sided, and that had to be fixed first

**This is a second defect, in M97's `signtest.py`, found while running B3.**

`best_scale` trials a candidate scale `s` by forming `zoom(b_raw, 1.0/s)`, and
`zoom(img, t)` is `gather(img, 1/t)`. So the trial image is `gather(b_raw, s)`, and
**every trial with `s > 1` calls `gather` with `a > 1`**. `gather` samples with
`mode="constant", cval=nan` and `prep` turns those NaNs into zeros, so for `a > 1`
the lattice runs off the input and the trial is scored with a black rim eating into
the frame. Its NCC is depressed by construction and the argmax can never land there.

M97's own control already reports this branch as broken —
`GATHER ROUND-TRIP a=1.08 -> 118.1 plane px FAIL` against `a=0.92 -> 7.3 px OK` —
but the connection to `best_scale`'s own trials was never drawn, and **both of its
plant controls (0.940, 0.860) sit below 1.0**, so nothing in the suite ever
exercised the failing side. This matters here and nowhere else in the corpus,
because only a *correctly* solved sidecar lands above 1.0.

**MEASURED, `src/residual.py control`** — known scales, planted as a pair
`gather(img, min(1,s))` against `gather(img, min(1,1/s))` so that both gather
arguments stay <= 1 and both sides are resampled equally:

| planted | two-sided search | err | M97 `best_scale` | err |
|---|---|---|---|---|
| 0.800 | 0.79999 | -0.00001 | 0.79999 | -0.00001 |
| 0.860 | 0.86001 | +0.00001 | 0.86002 | +0.00002 |
| 0.940 | 0.93996 | -0.00004 | 0.94003 | +0.00003 |
| 1.000 | 0.99998 | -0.00002 | 0.99997 | -0.00003 |
| **1.020** | 1.02002 | +0.00002 | **1.00681** | **-0.01319** |
| **1.060** | 1.05999 | -0.00001 | **1.01383** | **-0.04617** |
| **1.120** | 1.12001 | +0.00001 | **1.02094** | **-0.09906** |
| **1.200** | 1.19996 | -0.00004 | **0.99997** | **-0.20003** (full clip) |

Worst two-sided error over the whole range: **0.00004 (0.1 plane px)**. Worst M97
error above 1.005: **0.20003 (422.3 plane px)**.

Two further consequences, both MEASURED:

- **M97's headline baseline number is sound.** Below 1.0 the two searches agree to
  0.1 plane px, and the baseline residual is 0.9288. The 150.2 px / 50.2% figure
  stands, and the repaired instrument independently reproduces it at 150.3 px /
  50.1%.
- **`signtest.py`'s own reported plant errors are mostly the plant, not the
  estimator.** Its plants are built as `zoom(g0, 0.860)` = `gather(g0, 1.163)`, on
  the broken branch. It reports -0.00142 at 0.860; a clean plant of the same scale
  reads **+0.00001**.

**The clip is not hypothetical, it fired on this milestone's own data.** Sweeping
M97's `gain` hook on the baseline sidecar, the one-sided search returns *bit
identical* residuals of 0.99997 / 0.1 px at gain 2.000 **and** gain 2.200 — two
materially different sidecars — and identical to the SELF arm.

Everything geometric in `src/residual.py` is imported from `signtest.py`
unmodified, so the repaired instrument cannot drift from the original.
**`signtest.py` itself was not edited; it belongs to M97.** §15 routes the patch.

---

## 7. Attribution: which part of the fix does the work

**MEASURED**, all on the *shipped* span ladder so that configuration is the only
variable. Truth is ln -0.154154.

| arm | end-to-end ln | recovery |
|---|---|---|
| `deep` (shipped) | -0.080761 | 0.524 |
| `+ warp_tiles` | -0.086035 | 0.558 |
| `+ fine_iters` | -0.090473 | 0.587 |
| `+ both` | -0.097431 | 0.632 |
| `wide` (capture only) | -0.140605 | **0.912** |
| `iterated_wide` | -0.123811 | 0.803 |

**The dominant lever is coarse capture range, not warping or iteration.** Warping
and iteration each add 3-6 points on `deep`; going `wide` adds 39.

With the extended span ladder (`1,2,4,8,16,32,64,96,128,192,256,298` plus a
frame-0 anchor fan at stride 8 — which is what rule 6 already prescribes):

| arm | end-to-end ln | scale | recovery |
|---|---|---|---|
| `deep` | -0.071834 | 0.930685 | 0.466 |
| `wide` | -0.171987 | 0.841990 | 1.116 |
| **`iterated_wide`** | **-0.162541** | **0.849981** | **1.054** |

`iterated_wide` is preferred over plain `wide` because it is closer to unity
(1.054 against 1.116), not because it recovers more.

**DERIVED.** Corner misregistration at rho = 2113 px: shipped 7.6% -> ~138 plane
px; corrected 0.83% -> ~15 plane px.

---

## 8. Pre-registered bars: outcomes

Scored against `PREREG.md` exactly as written. **No bar was moved.** One failed.

### B1 — conservation identity. PARTIAL (diagnostic only, never a gate).

MEASURED, telescoping chain recovery:

| span | shipped | corrected |
|---|---|---|
| 1 | 0.163 | 0.285 |
| 4 | 0.312 | 0.406 |
| 16 | 0.697 | 0.230 |
| 96 | — (censored) | 0.891 |
| 128 | — (censored) | 1.019 |

Long spans now telescope essentially correctly (1.019 at span 128) where the
shipped config could not form the chain at all. **Span 1 does not reach unity —
0.285 against a required 1.0 — so B1 is not met at short spans.** Reported as
registered: diagnostic, never a gate (fact 1098). The fix does not repair span-1
edges; it stops the solve depending on them.

### B2a — self-pair placebo. PASS.

MEASURED: `|a| = 1` to **2.1e-5** with warping and iteration on, against a bar of
1e-4. `used` did not fall.

### B2b — the uncensored span. **FAIL, as written.**

Registered bar: "the treatment must move the span-1 mean `ln|a|` by **< 20%** of
its own value." MEASURED: span-1 recovery moves 0.138 -> 0.286, a **107% move**.

**I am not redefining this bar.** It failed. The reason is that I wrote it while
hypothesis 1 (capture starvation) was the only one on the table, and its stated
rationale is explicitly capture-range reasoning: *"at span 1 the shipped estimator
already keeps 85.9/96 tiles ... there is nothing for a capture-range treatment to
uncensor."* That reasoning is still correct. But the treatment I ended up shipping
is **not** capture-range-only — it also fixes peak-locking, which is precisely a
span-1 defect, so it moves span 1 by design. **B2b tested a hypothesis I
subsequently refined, and it was mis-specified by me.**

The substantive requirement B2b was standing in for — *the correction must be a
measured no-op where there is nothing to correct* — is carried by **B2a**
(self-pair, 2.1e-5) and, load-bearingly, by **B4** below. A reader should treat B4
as the placebo of record.

### B3 — THE DECIDING BAR. PASS.

Registered: PASS if >= 80% of drift removed. MEASURED on `bee-3-cpl`:

| | span | residual | plane px | drift removed |
|---|---|---|---|---|
| shipped | 0.922414 | 0.92880 | **150.3** | **50.1%** |
| **M103** | 0.849981 | 1.00138 | **2.9** | **99.0%** |

Both measured with the repaired two-sided instrument, in the reference-0 gauge so
that both placements sit on the branch M97's round-trip control passes. The
shipped figure reproduces M97's own 150.2 px / 50.2%.

Under M97's **unmodified** `signtest.py` the fix scores 0.1 plane px / 100.0%.
**That number is an artefact of the clip in §6 and should not be quoted.** The
honest figure is 2.9 plane px / 99.0%.

**Dose-response, the positive control for this bar.** MEASURED, sweeping the gain
hook and finding where each sidecar's residual is actually minimised:

| gain | shipped residual (px) | | gain | M103 residual (px) |
|---|---|---|---|---|
| 1.000 | 150.3 | | 0.850 | 27.3 |
| 1.400 | 79.4 | | 0.900 | 14.5 |
| 1.700 | 27.5 | | 0.950 | 3.5 |
| 1.908 | 3.3 | | **0.980** | **1.4** |
| 2.000 | 1.5 | | 1.000 | 2.9 |
| 2.200 | 31.1 | | 1.050 | 17.6 |
| 2.500 | 85.0 | | 1.200 | 71.5 |

Clean V-shaped minima on both arms. **The shipped solve needs its log-scale
multiplied by ~1.97 — it recovers 50.8%. The corrected solve needs 0.98 — it is
within 2% of optimal.** This is the "recovers half" defect measured as a curve
rather than a point, and it is independent of the truth ladder.

### B4 — must not break the good case. PASS.

Registered: on `112MSDCF` the treatment must stay within **±10%**. `112MSDCF` is
the corpus's canonical null — rule 6 records `1/S_W(1)` = 1.05, "essentially none",
and 78 chained adjacent edges recovering 99.0% of the direct long edge.

MEASURED: ln-span **-0.038359** (shipped) -> **-0.038538** (corrected). A **0.47%**
move. DERIVED: 0.38 plane px of corner effect.

**The same code, same constants, is a 0.47% no-op on the stack with no defect and
doubles the span on the stack with one.** This is the load-bearing placebo.

### B5 — positive control. PASS, with a stated blind spot.

MEASURED: zero-plant exact; planted scales recovered at 1.00 from 5e-4 to 0.10;
both resamplers agree. **See §5.4 — this control cannot see peak-locking, because
its plant suppresses it.** It is reported as passing and as insufficient.

### B6 — the shipped default path must not move. PASS.

MEASURED: edge dumps bit-identical across **2520 real pairs** between the
pre-change build and the post-change build on the untreated path. Only the
configuration-echo comment line differs. Every new field defaults to current
behaviour.

**`cargo test -p strehl-core --release`: 238 passed, 0 failed.**

---

## 9. The photograph

The stated point of the milestone. Rendered twice through `strehl stack`, same
bracket, same `--gate 2 --srgb --demosaic`, 299 frames, registration the only
variable, injected with `STREHL_WARPMAP` so nothing was written beside the capture.

Both renders reported **identical coverage (0.9974)**, so both show the same field
at the same pixels and the comparison is not confounded by field of view.

**A falsifiable prediction, registered before the measurement.** Residual
misregistration under a scale error is `|s-1| * rho` — proportional to distance
from centre. So a registration improvement **must** be near-zero at the centre and
largest at the corners. A uniform improvement would refute the attribution.

MEASURED — acutance (mean squared gradient normalised by mean intensity squared)
over 486 textured 256x256 tiles:

| r / r_max | tiles | shipped | M103 | ratio |
|---|---|---|---|---|
| 0.0 - 0.2 | 35 | 0.00282 | 0.00261 | **0.924x** |
| 0.2 - 0.4 | 101 | 0.00299 | 0.00283 | 0.944x |
| 0.4 - 0.6 | 163 | 0.00165 | 0.00178 | 1.081x |
| 0.6 - 0.8 | 135 | 0.00064 | 0.00072 | 1.130x |
| 0.8 - 1.0 | 52 | 0.00025 | 0.00034 | **1.370x** |
| whole frame | 486 | 0.00074 | 0.00077 | 1.043x |

**Monotone in radius, +37% at the edge of the frame. The prediction holds.**

**I looked at the images.** At large radius the bee's leg bristles are individually
resolved and countable in the corrected render and smeared into a mass in the
shipped one; a second leg that is entirely blurred out in the shipped render is
sharp in the corrected one. Crops are written to
`C:\dev\strehl-out\M103\img\crops\` as before/after pairs.

**The centre is 7.6% *worse*, and I am not hiding it.** MEASURED, and DERIVED
cause: with reference frame 0, frame 298 is gathered at `a = 0.850` and so is
**magnified 1.176x** into the output. A mid-stack reference splits that
magnification. This is a resampling cost of the gauge, not of the registration.

**But the gauge is now a real decision, and reference 0 wins.** MEASURED coverage:

| reference | shipped solve | M103 solve |
|---|---|---|
| 149 (production today) | 0.9315 (6.9% of width dropped) | **0.8561 (14.4% dropped)** |
| 0 | 0.9974 | **0.9974 (0.3% dropped)** |

DERIVED: coverage is set by `max |a_k|`, and a reference at the end of the sweep
makes every `a_k <= 1` so every frame maps inward. **With the corrected, larger
span, a mid-stack reference costs 14.4% of the frame; reference 0 costs 0.3%.**
Routed to the orchestrator in §15.

---

## 10. Peak-locking predicts the shrinkage rule 6 says nothing predicts

**MEASURED.** Mean |frac| of per-tile displacements on the (0,1) pair of each
stack, shipped `deep` config, against `1/S_W(1)` as published in rule 6:

| stack | 1/S_W(1) | source | mean \|frac\| |
|---|---|---|---|
| bee-3-cpl | 6.13 | M103 (1/0.163) | **0.0761** |
| coffee-bean | 3.26 | rule 6 | 0.1414 |
| 119MSDCF | 2.20 | rule 6 | 0.1100 |
| 109MSDCF | 1.32 | rule 6 | 0.2054 |
| 112MSDCF | 1.05 | rule 6 | 0.1912 |
| 113MSDCF | 1.03 | rule 6 | 0.2168 |

**Spearman rho = -0.886 over n = 6.** Uniform would be 0.2500; every stack is below
it, so some locking is always present and what varies is how much.

Two independent measurements — the shrinkage figures come from earlier milestones
under a different protocol — so this is a test and not a restatement. It also
explains rule 6's own puzzle that "two stacks matched to 0.3% in per-frame
displacement still differ 3.11x in shrinkage": peak-locking severity depends on how
sharply peaked the correlation surface is, which is a property of scene texture,
not of displacement.

**ARGUED, and offered as a candidate only.** n = 6 with one pair per stack is thin,
and the two rank inversions are between stacks whose shrinkage differs little
(3.26 against 2.20; 1.32 against 1.05). A proper test needs several pairs per stack
and a pre-registered threshold.

---

## 11. Candidate facts (AGENTS rule 28 — numbered P1.., to be folded by content)

- **P1 (MEASURED).** The shipped alignment solve recovers 52.4% of the true
  log-scale drift on `bee-3-cpl` (solved ln -0.080761 against truth -0.154154).
- **P2 (MEASURED).** `AlignConfig::iterated_wide()` with a span ladder carrying
  long spans and a frame-0 anchor fan recovers 105.4% (ln -0.162541).
- **P3 (MEASURED).** Absolute end-to-end residual on `bee-3-cpl` falls from 150.3
  plane px (50.1% of drift removed) to 2.9 plane px (99.0%).
- **P4 (MEASURED).** The dominant term is coarse capture range, not sub-pixel
  refinement: `wide` alone takes recovery 0.524 -> 0.912 on the shipped ladder,
  while warping and iteration together take it only to 0.632.
- **P5 (MEASURED).** Under `deep()` the direct `(0,298)` edge on `bee-3-cpl` is
  refused (`TooFewTiles { correlated: 6 }`); the shipped solve has no long-baseline
  anchor.
- **P6 (MEASURED).** Per-tile NCC displacements on real pairs pile onto integers:
  mean |frac| 0.0761 on `bee-3-cpl` (0,1) against 0.25 for uniform, and the
  lever-binned radial ramp that encodes scale is absent.
- **P7 (MEASURED).** Resampling a plant suppresses peak-locking, so a resampled
  plant reports estimator response 1.00 on a pair where the real-pair recovery is
  0.16. Independently corroborates fact 174 and satisfies discipline 615's warning.
- **P8 (MEASURED).** `signtest.py`'s `best_scale` cannot report a residual above
  1.0: its trials call `gather` with `a > 1`, the branch its own round-trip control
  fails. Planted 1.200 reads 0.99997, an error of 422 plane px. Below 1.0 it is
  correct to 0.1 plane px, so M97's 150.2 px baseline stands.
- **P9 (MEASURED).** `signtest.py`'s own plant controls are built on that broken
  branch; its reported -0.00142 error at planted 0.860 is the plant, not the
  estimator. A clean two-sided plant reads +0.00001.
- **P10 (MEASURED).** On `112MSDCF` (rule 6: `1/S_W(1)` = 1.05) the M103 correction
  moves the end-to-end ln-span by 0.47%, a measured no-op.
- **P11 (MEASURED).** Correcting the solve improves rendered acutance monotonically
  in radius on `bee-3-cpl`: 0.924x at the centre, 1.370x in the outer bin, 1.043x
  whole-frame.
- **P12 (MEASURED).** Merge coverage is set by `max |a_k|`. With the corrected span,
  reference 149 costs 14.4% of frame width against 0.3% for reference 0.
- **P13 (ARGUED, candidate).** Mean |frac| of per-tile displacements tracks
  published per-stack shrinkage at Spearman rho = -0.886 over six stacks — a
  measurable property of the edge sets that predicts shrinkage, which rule 6
  currently records as non-existent.
- **P14 (MEASURED).** `DEFAULT_SPANS` = `[1,2,4,8,16,32,64,96,128]` includes spans
  1 and 2 in direct violation of rule 6's "discard spans 1-2 from the solve", and
  contains no frame-0 anchor fan although rule 6 prescribes one. Those are exactly
  the peak-locked edges.

---

## 12. Rule 22 walk

Rule 22 requires naming the rules I could have violated rather than affirming them.

- **Rule 4 (never a raw argmax).** The NCC integer search *is* an argmax, and its
  bias is the subject of §5.3 rather than something I assumed away.
- **Rule 6 (never chain; discard spans 1-2).** My solve composes nothing — global
  LSQ, `cycle_rank 2056`, checked. The reference frame is a **gauge** for
  expressing solved placements, not a chaining anchor; §9's reference-0
  recommendation is about resampling and coverage, not about relying on a single
  reference for the fit. I did **not** discard spans 1-2, because they were the
  evidence for the mechanism; the shipped ladder recommendation in §15 does.
- **Rule 6 (do not fit a shrinkage correction).** §2 states why this is not one:
  no fitted parameter, no cross-scene transfer, and a 0.47% no-op on `112MSDCF`.
- **Rule 9 (controls).** Every arm carries a placebo and a positive control. B2b
  failed and is reported as failed.
- **Rule 10 (do not compare unlike quantities).** The acutance comparison is
  normalised by mean intensity, and I checked coverage was identical before
  comparing per-pixel; where it was not (reference 149) I did not quote the
  comparison.
- **Rule 20 (named failing inputs).** Pre-registered in `PREREG.md` §2; B3's named
  failing input (run `A`'s own sidecar at 50.2%) is on disk and was measured.
- **Rule 28 (facts by content, not number).** Candidates are P-numbered, unfolded.
- **Rule 41 (milestone allocation).** **M103 is not in the AGENTS.md ledger.** It
  was never allocated at dispatch. Routed in §15.
- **Rule 43 (false assertions of absence).** §3.

---

## 13. What I did not test, and what would change my mind

- **The over-shoot at spans 192-298** (1.25-1.33 on only 10-15 surviving tiles) is
  unexplained and may be false peaks. The trustworthy band is spans 96-128.
- **`iterated_wide` costs 1096 s against 55 s for `deep`** on 2520 pairs — a 20x
  slowdown, unoptimised. Not addressed.
- **I did not replace the sub-pixel estimator.** Gaussian/log-parabola fitting,
  correlation-surface upsampling, or symmetric pre-blur all attack peak-locking
  directly and none were tried, because `iterated_wide` already reaches 1.054.
  Note that symmetric pre-blur is M78's R5 arriving for an entirely different
  reason than the commission gave.
- **§10 is n = 6 with one pair per stack.** Several pairs per stack, pre-registered,
  would settle it.
- **What would change my mind about the mechanism:** a stack with heavy integer
  piling and *no* shrinkage, or a demonstration that widening capture alone
  (without touching sub-pixel behaviour) recovers 100% — which would make
  peak-locking irrelevant rather than contributory. `wide` reaching 1.116 on the
  extended ladder is uncomfortably close to that and deserves a direct test.
- **The measured residual is better than the sidecar's own span arithmetic
  predicts** (1.00138 against 1.00848 predicted; and the dose minimum sits at 1.97
  where scale arithmetic predicts 1.908). ~0.7-3% is unexplained. It is in the
  favourable direction and both figures are <= 3 px against a 150 px baseline, but
  it is not understood.

---

## 14. Reproducing every number

```powershell
$env:PATH="$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR="C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m103-probe"
$env:PYTHONIOENCODING='utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\M103-halfdrift
cargo build --release --manifest-path probe\Cargo.toml
$P = "..\..\.cargo-target-m103-probe\release\m103probe.exe"
$D = "D:\personal\macro\bee-3-cpl"

# ground truth, three controls inside (SELF, PLANT, and the RAW ladder)
python src\truth.py                                    # -> data\truth-ladder.json

# edge dumps: shipped config and the fix  (55 s and 1096 s)
& $P measure --dir $D --config deep --spans 1,2,4,8,16,32,64,96,128,192,256,298 `
     --anchor-from 0 --anchor-stride 8 --out data\A-deep-edges.csv
& $P measure --dir $D --config iterated-wide --spans 1,2,4,8,16,32,64,96,128,192,256,298 `
     --anchor-from 0 --anchor-stride 8 --out data\IWW-edges.csv

# per-span recovery and the B1 telescoping chain
python src\score.py data\A-deep-edges.csv data\truth-ladder.json
python src\score.py data\IWW-edges.csv    data\truth-ladder.json

# sidecars (temp-then-rename; caches under C:\dev\strehl-out\M103 only)
& $P solve --edges data\A-deep-edges.csv --only-spans 1,2,4,8,16,32,64,96,128 `
     --reference 0 --digest-dir $D --label shipped-baseline `
     --warpmap C:\dev\strehl-out\M103\wm-baseline-r0.txt
& $P solve --edges data\IWW-edges.csv --reference 0 --digest-dir $D `
     --label iterated-wide --warpmap C:\dev\strehl-out\M103\wm-iww-r0.txt

# §6: the instrument control -- MUST be run before believing any B3 number
python src\residual.py control data\B3-instrument-control.json

# B3, the deciding bar
python src\residual.py sidecar C:\dev\strehl-out\M103\wm-baseline-r0.txt data\B3-ts-baseline.json 298
python src\residual.py sidecar C:\dev\strehl-out\M103\wm-iww-r0.txt      data\B3-ts-iww.json      298

# B3's dose-response positive control
python src\dose.py C:\dev\strehl-out\M103\wm-baseline-r0.txt data\B3-dose2-baseline.json 298 1.0 1.4 1.7 1.8 1.908 2.0 2.2 2.5
python src\dose.py C:\dev\strehl-out\M103\wm-iww-r0.txt      data\B3-dose2-iww.json      298 0.85 0.90 0.95 0.98 1.00 1.05 1.10 1.20

# B4, the placebo of record
& $P measure --dir "D:\personal\macro\112MSDCF" --config deep --spans 1,2,4,8,16,32,64 `
     --anchor-from 0 --anchor-stride 4 --out data\B4-112-deep.csv
& $P measure --dir "D:\personal\macro\112MSDCF" --config iterated-wide --spans 1,2,4,8,16,32,64 `
     --anchor-from 0 --anchor-stride 4 --out data\B4-112-iww.csv
& $P solve --edges data\B4-112-deep.csv --reference 0
& $P solve --edges data\B4-112-iww.csv  --reference 0

# §5.3 peak-locking, and §10 across the corpus
& $P tiles --dir $D --i 0 --j 1 --config deep --out data\T-real-0-1.csv
python src\tiles.py data\T-real-0-1.csv
python src\corpus.py

# §9 the photograph  (~4 min per render)
$env:CARGO_TARGET_DIR="C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m103"
cargo build --release -p strehl-cli
$env:STREHL_WARPMAP="C:\dev\strehl-out\M103\wm-baseline-r0.txt"
..\..\.cargo-target-m103\release\strehl.exe stack $D --gate 2 --srgb --demosaic `
     -o C:\dev\strehl-out\M103\img\bee3-baseline.tiff
$env:STREHL_WARPMAP="C:\dev\strehl-out\M103\wm-iww-r0.txt"
..\..\.cargo-target-m103\release\strehl.exe stack $D --gate 2 --srgb --demosaic `
     -o C:\dev\strehl-out\M103\img\bee3-m103.tiff
python src\photo.py C:\dev\strehl-out\M103\img\bee3-baseline.tiff `
     C:\dev\strehl-out\M103\img\bee3-m103.tiff C:\dev\strehl-out\M103\img\crops data\photo.json
```

`D:\personal\macro` is read-only and nothing here writes to it. Sidecars are
written to a temp path and renamed, per M97's torn-read observation.

---

## 15. Routed to the orchestrator

All of these are outside M103's ownership. Verbatim, for the orchestrator to apply
or refuse.

**15.1 — Rule 41: M103 was never allocated.** There is no M103 row in the AGENTS.md
ledger. Suggested row:

> `M103` — the alignment solve recovers half the drift. Found the cause (coarse
> capture starvation plus peak-locking in the sub-pixel NCC), fixed it in
> `align.rs` (`AlignConfig::iterated_wide`), and measured end-to-end residual on
> `bee-3-cpl` falling 150.3 -> 2.9 plane px (50.1% -> 99.0% of drift removed).
> Also found that `signtest.py` cannot measure a residual above 1.0.
> `docs/research/M103-halfdrift.md`.

**15.2 — Rule 43 correction to the M103 commission.** The dispatch asserted of blur
equalisation that "as far as the corpus knows this has never been applied to
focus-stack registration". It is M78's R5 (facts 1097-1099). Per-edge
metacalibration is M23's R4 (facts 170-178). Fact 45's causal reading is withdrawn
by fact 174. See §3.

**15.3 — `align_cmd.rs` (M97 owns; M103 must not edit).** Two changes, together
worth 0.524 -> 1.054 MEASURED:

> `DEFAULT_SPANS` is `[1, 2, 4, 8, 16, 32, 64, 96, 128]`. Rule 6 says "**Discard
> spans 1-2 from the solve**" and prescribes "a span ladder ... **plus every
> frame-0 pair**". The shipped ladder does neither. Suggested:
> `[4, 8, 16, 32, 64, 96, 128, 192, 256]` plus a frame-0 anchor fan at stride 8.
> Separately, the default config should become `AlignConfig::iterated_wide()`;
> `deep()`'s own doc comment already warns that its margin "must track stack
> depth", and `bee-3-cpl` carries 301.6 px of corner drift against a margin of 96.

**15.4 — `align_cmd.rs` / merge reference choice.** MEASURED in §9: coverage is set
by `max |a_k|`, so with the corrected span a mid-stack reference costs **14.4%** of
frame width where reference 0 costs **0.3%**. Recommend placing the reference at the
end of the focus sweep so every `a_k <= 1`. Note the trade: reference 0 magnifies
the far frame 1.176x and costs ~7.6% of centre acutance.

**15.5 — `experiments/M97-warped-merge/src/signtest.py` (M97 owns).** The patch is
implemented and controlled in `experiments/M103-halfdrift/src/residual.py`; M97
should lift `trial_pair`/`best_scale_2s` or adopt the file. Minimal change:

> ```python
> def trial_pair(a_raw, b_raw, s):
>     if s <= 1.0:
>         return a_raw, gather(b_raw, complex(s, 0.0), 0j, 1.0)
>     return gather(a_raw, complex(1.0 / s, 0.0), 0j, 1.0), b_raw
> ```
>
> and rebuild the two PLANT arms as
> `gather(img, min(1,s))` against `gather(img, min(1,1/s))` so both gather
> arguments stay <= 1. Without this the instrument silently clips every residual
> above 1.0 and cannot score a correct sidecar. **M97's published baseline of
> 150.2 px / 50.2% is unaffected and reproduces at 150.3 px / 50.1%.**

**15.6 — SYNTHESIS candidate facts.** P1-P14 in §11.

**15.7 — a rule 6 amendment, if P13 survives independent checking.** Rule 6
currently states "no measurable property of the edge sets predicts it". §10
measures one at Spearman rho = -0.886 over six stacks. Suggested replacement for
that clause only:

> Before: `and no measurable property of the edge sets predicts it.`
>
> After: `and no property of the *optics* predicts it; M103 measures one property
> of the edge sets that does, the concentration of per-tile displacement
> fractional parts (Spearman rho = -0.886, n = 6, one pair per stack -- a
> candidate, not a settled law).`
