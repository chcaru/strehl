# M103 — the alignment solve recovers half the drift

Status: complete. The defect is found, fixed, and measured end to end on the
owner's stack. The fix ships in `crates/strehl-core/src/align.rs`.

**Revised after first publication.** §9 previously claimed the photograph got
visibly sharper (+37% acutance at the frame edge). **That claim is retracted**;
the corrected §9 shows it was carried by five tiles of fifty-two and does not
survive an orientation-based instrument. The solve results in §1-§8 are
unaffected — they are measured in plane px on the sidecar and depend on no
render.

**Every claim below is labelled MEASURED, DERIVED or ARGUED.** Every number can be
re-run from committed scripts; §14 gives the commands in order.

---

## 1. Summary

> **RETRACTED IN PART — read §16 before acting on anything below.** The
> end-to-end numbers in this summary are correct and reproduce. What is withdrawn
> is their *meaning*. §16 measures that end-to-end residual and **per-frame
> placement** — what the merge actually consumes — are nearly independent: the
> same fix moves the first 150.3 → 2.9 px and the second 36.4 → 37.5 px. The fix
> should **not** be adopted as a default (§15.3 is withdrawn), and the acceptance
> bar used by M86, M97, M97b and this milestone scores one frame pair out of 299.

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

**The photograph did not measurably get sharper, and an earlier revision of this
report wrongly claimed it did.** §9 is a retraction. Two instruments now say so:
the orchestrator's orientation-based `anisotropy.py`, run paired, returns a null
in which every confidence interval overlaps and the centre moves more than the
edge; and the median of my own acutance statistic reads **0.9898** at the frame
edge where its mean read **1.3697**, because five tiles of fifty-two carried
73.6% of that bin. The residual reaches the render as ~1 px, not 150, because the
frames that win a pixel are clustered in index. **What the fix buys is correct
geometry — features landing where they belong — not visible sharpness.** The
owner's softness complaint is dominated by something else (M95's 8.2 MP of
information in a 33 MP file is the orchestrator's current candidate).

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

## 9. The photograph — RETRACTION, and what actually happened

> **This section previously claimed "+37% acutance at the edge of the frame" and
> "the prediction holds". I am retracting both.** The claim was published in an
> earlier revision of this report and in my checkpoint summary. It does not
> survive the checks below. The measurement was real and reproduces exactly; my
> reading of it was wrong. The solve results in sections 5-8 are untouched by
> this — they are measured in plane px on the sidecar and do not depend on any
> render.

### 9.1 Why this was re-examined

The orchestrator built an independent instrument,
`experiments/ORCH-drift-check/anisotropy.py`, and measured something my acutance
statistic could not: a residual *scale* error displaces every feature along its
own radius, so it leaves an **orientation** signature — high-frequency power
suppressed along the radial direction relative to the tangential — that is zero
at the centre and grows outward. Diffraction, defocus, demosaic and a soft
subject share neither property.

Their finding, which reframes this milestone: **the residual reaches the render
as roughly 1 px, not 150.** The frames that win a given pixel are clustered in
index, so the merge averages over the displacement spread *within the
competitive set*, not over the stack's total drift. ARGUED, and I accept it: a
150 plane px end-to-end drift does not arrive at the output as 150 px of blur.

### 9.2 The instrument passes its controls on my render

MEASURED. Re-verified on my own `bee3-baseline.tiff` rather than trusted from
the orchestrator's subject (`logs/aniso-controls-baseline.log`):

| control | result |
|---|---|
| SENSITIVITY — 10 px plant must lower A_outer | **PASS** (0.4734 -> 0.0116) |
| DOSE ORDER — monotone with dose | **PASS** (0.4734 / 0.3269 / 0.0629 / 0.0116) |
| SPECIFICITY — isotropic blur must NOT move it | **PASS** (-0.0077) |
| BUILT-IN NULL — A(centre) ~ 1 untreated | **PASS** (0.9607) |
| GEOMETRY — at 1 px outer bites harder than centre | **PASS** |

So the instrument is sensitive, specific, and correctly geometric *on this exact
render*. Any null it returns here is informative rather than blind.

### 9.3 Run paired, it returns a null

`src/aniso_pair.py` imports the orchestrator's `measure()` unmodified and adds
pairing via its own `tile_keys` argument. This matters: the instrument's
docstring is emphatic that the tile selection must not depend on the treatment,
`controls()` obeys that, but the multi-file path in `__main__` does not — it
re-derives a 35th-percentile texture threshold per file. My fix adds
high-frequency power at large radius, which is exactly the condition under which
an unpaired selection drifts.

MEASURED (`data/aniso-pair.json`), usable annuli only (angular clustering
<= 0.30, the orchestrator's own threshold):

| r | clustering | A shipped | A M103 | delta | 95% CIs |
|---|---|---|---|---|---|
| 0.05 | 0.019 | 0.9416 | 0.9796 | +0.0380 | overlap |
| 0.15 | 0.022 | 0.9799 | 1.0175 | +0.0375 | overlap |
| 0.25 | 0.013 | 1.1050 | 1.1303 | +0.0253 | overlap |
| 0.35 | 0.052 | 0.8820 | 0.8373 | **-0.0447** | overlap |
| 0.45 | 0.081 | 0.6450 | 0.6634 | +0.0184 | overlap |
| 0.55 | 0.221 | 0.5279 | 0.5591 | +0.0312 | overlap |

**Every confidence interval overlaps. One annulus moves backwards.** And the
deltas are the same size as the method's own sensitivity to arbitrary choices:
re-pinning the tile set on the other arm moves them by up to **0.0298**, and the
stock unpaired path disagrees by up to **0.0161**.

**It also fails the discriminating half of the orchestrator's pre-registered P3**
("A(r) rises toward 1 at large r and is UNCHANGED at r=0"). A(centre) moves
**+0.0380**, *more* than any outer annulus, at a radius where the geometry
forbids a scale-induced change. Whatever moved this metric is not the radial
registration.

Placebo: before vs before on the same tiles, max |dA| = **0.00e+00**, PASS.

Inverting the planted dose curve to px gives **0.00 px before and 0.00 px after**
at every usable radius — the shipped render's radial residual was already below
this instrument's detection floor at the radii where the subject is angularly
clean.

### 9.4 The +37% was five tiles

The acutance number reproduces exactly, so the two measurements genuinely
disagree and one had to be wrong. MEASURED (`src/acutance_dist.py`,
`data/acutance-dist.json`) — the same per-tile quantity photo.py averaged, but
with its distribution shown:

| r / r_max | n | mean (published) | **median** | trimmed 80% | top-5 share |
|---|---|---|---|---|---|
| 0.0 - 0.2 | 35 | 0.9239 | 0.9174 | 0.9100 | 39.6% |
| 0.2 - 0.4 | 101 | 0.9445 | 0.9367 | 0.9600 | 23.5% |
| 0.4 - 0.6 | 163 | 1.0810 | 1.0391 | 1.2112 | 15.5% |
| 0.6 - 0.8 | 135 | 1.1304 | 1.3501 | 3.3359 | 39.7% |
| 0.8 - 1.0 | 52 | **1.3697** | **0.9898** | 1.0626 | **73.6%** |

**At the frame edge the median tile reads 0.9898 — no change — while the mean
reads 1.3697, because five tiles of fifty-two carry 73.6% of the bin.** The
`0.6-0.8` bin is equally unstable (trimmed mean 3.34). Acutance carries a `1/m^2`
normalisation, so a tile's leverage grows without bound as it darkens, and outer
tiles on this subject are an order of magnitude darker than central ones.

The median is not merely an insensitive statistic. POSITIVE CONTROL: against a
copy sharpened 3% at *all* radii, the median moves at every radius
(1.0226 / 1.0237 / 1.0221 / 1.0270 / 1.0356) and tracks the mean. A broad, real
change moves it. On the real pair, at the edge, it does not.
PLACEBO: before vs before, max |mean_ratio - 1| = 0.00e+00, PASS.

A separate decomposition (`src/acutance_check.py`) confirms raw gradient energy
at the edge rises only **1.061x**, and refutes my first guess that brightness
normalisation was the culprit: a planted 5% dimming reads `acut_ratio` exactly
**1.0000**, because `1/m^2` correctly cancels a multiplicative level change.

### 9.5 And the crops I looked at were selected by the tail

`photo.py` places its visual crops on "the most textured tiles the *baseline*
has" at large radius. Those are precisely the tiles that dominate the mean. So
when I reported that bristles were "individually resolved and countable", I was
looking at an unrepresentative sample chosen by the same statistic the tail
controls. **The visual impression was real for those crops and does not
generalise to the frame.** I withdraw the sentence.

This is the fourth incident this week of a metric and an eye agreeing while both
were pointed at a selected sample; it belongs with disciplines 611, 615, 616 and
620.

### 9.6 What the fix does and does not buy

MEASURED, and stated without inflation:

- It does **not** measurably sharpen this photograph. Two independent
  instruments — one orientation-based and confound-resistant, one the median of
  my own acutance — both return no significant change at any radius.
- The centre is genuinely **~8% worse**, and that part *is* broad: median 0.9174
  agrees with mean 0.9239. DERIVED cause: with reference frame 0, frame 298 is
  gathered at `a = 0.850` and so is magnified 1.176x into the output, against
  1.084x under the shipped solve. This is a resampling cost of the gauge, not of
  the registration, and section 9.7 removes it.
- It **does** put the geometry right: 150.3 -> 2.9 plane px of residual
  misregistration (section 8, B3). Features land where they belong. That caps
  final-render accuracy no matter how sharp the pixels are, and it is a
  precondition for the resolution work rather than a substitute for it.

ARGUED: the softness the owner is complaining about is dominated by something
else. The orchestrator's current candidate is M95's finding that the default
output carries 8.2 MP of information in a 33 MP file. Nothing in this milestone
should be read as addressing that.

### 9.7 The crop side effect, quantified — and it is avoidable

The orchestrator asked for this explicitly: a solve that applies the *full* drift
instead of half spans a wider range of scales, and the merge shrinks the field of
view until every frame covers every output pixel, so a correct solve should
demand a **larger** crop. It does, and the size of the cost depends entirely on
the reference frame.

MEASURED — coverage as reported by `strehl stack` itself
(`logs/img-*.log`), four renders, same bracket:

| reference | shipped solve | M103 solve | extra cost of the fix |
|---|---|---|---|
| 149 (production today) | 0.9315 (6.9% of width dropped) | **0.8561 (14.4% dropped)** | **+7.5 points** |
| 0 | 0.9974 (0.3% dropped) | **0.9974 (0.3% dropped)** | **none** |

DERIVED: coverage is set by `max_k |a_k|`. A reference at the **end** of the
sweep makes every `a_k <= 1`, so every frame maps inward and nothing is clipped;
a **mid-stack** reference forces `|a_k| > 1` on one whole half of the stack, and
the crop is `1 / max |a_k|`, which the corrected larger span makes worse.

**So the side effect is real, it is worth 7.5% of frame width at the reference
production uses today, and moving the reference to frame 0 removes it entirely.**

This also matters more than it looks, because the dropped field is **upsampled
back to the output dimensions** — the renderer says so in the same line. At
reference 149 the corrected solve therefore delivers 14.4% less real resolution
stretched over the same 33 MP file. ARGUED: that pushes in exactly the wrong
direction for M95's finding that the output already carries 8.2 MP of
information in a 33 MP container, so shipping this fix on a mid-stack reference
would make that defect measurably worse. Reference 0 costs 0.3% and is the
recommendation. Routed to the orchestrator in §15.

**Both photograph renders in 9.3-9.5 used reference 0 and reported identical
coverage (0.9974),** so the null result above is not an artefact of one arm
seeing a different field.

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
- **P11 (MEASURED, RETRACTED AND REPLACED).** An earlier revision claimed the fix
  improves rendered acutance monotonically in radius (0.924x centre, 1.370x outer).
  **The outer figure is a tail artifact.** On the same tiles the *median* per-tile
  ratio in the outer bin is 0.9898 — no change — while five tiles of fifty-two
  carry 73.6% of the bin, because acutance's `1/m^2` normalisation gives dark
  tiles unbounded leverage and outer tiles on this subject are an order of
  magnitude darker. The centre figure (0.9239 mean, 0.9174 median) *is* broad and
  real, and is a resampling cost of the reference-0 gauge.
- **P12 (MEASURED).** Merge coverage is set by `max |a_k|`. With the corrected span,
  reference 149 costs 14.4% of frame width against 0.3% for reference 0. The
  dropped field is upsampled back to full output dimensions, so at reference 149
  the corrected solve delivers 14.4% less real resolution in the same 33 MP file —
  ARGUED: directly counterproductive for M95's 8.2 MP-in-33 MP finding.
- **P13 (ARGUED, candidate).** Mean |frac| of per-tile displacements tracks
  published per-stack shrinkage at Spearman rho = -0.886 over six stacks — a
  measurable property of the edge sets that predicts shrinkage, which rule 6
  currently records as non-existent.
- **P14 (MEASURED).** `DEFAULT_SPANS` = `[1,2,4,8,16,32,64,96,128]` includes spans
  1 and 2 in direct violation of rule 6's "discard spans 1-2 from the solve", and
  contains no frame-0 anchor fan although rule 6 prescribes one. Those are exactly
  the peak-locked edges.
- **P15 (MEASURED).** Correcting the solve from 50.1% to 99.0% of drift removed
  produces **no detectable change in rendered radial anisotropy** on `bee-3-cpl`
  at `--gate 2`. Every annulus confidence interval overlaps; the largest delta
  (+0.0380) is at r=0.05, where the geometry forbids a scale-induced change; and
  the deltas are smaller than the measurement's own sensitivity to tile-set choice
  (0.0298). This is consistent with the orchestrator's finding that the residual
  reaches the render as ~1 px rather than 150 px.
- **P16 (MEASURED).** `anisotropy.py`'s `controls()` correctly pins the tile set on
  the untreated frame, but its multi-file `__main__` path calls `measure()` with
  `tile_keys=None` per file, re-deriving a texture threshold inside each arm — the
  exact failure its own docstring documents. On a before/after pair of two
  different solves this shifts reported deltas by up to 0.0161, comparable to the
  effects being reported.
- **P17 (MEASURED).** A visual "before/after" check placed on max-texture tiles is
  not a random sample: `photo.py` selects outer crops by baseline texture, which
  are the same tiles that dominate the `1/m^2`-weighted mean. Looking at those
  crops confirmed an improvement whose median across the bin is 0.9898. Belongs
  with disciplines 611, 615, 616, 620.

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
- **I did not render a gate-0 pair.** The orchestrator's P2 reasoning implies the
  registration residual should smear *less* at gate 0, where a single frame is
  elected per pixel and misregistration displaces rather than averages. A gate-0
  before/after would test whether the small, non-significant anisotropy deltas in
  §9.3 are smear-related at all. I judged it low value once every gate-2 CI
  already overlapped — two nulls do not compound into evidence — but it is the
  obvious next check if anyone wants to push on §9.
- **I did not measure whether correct geometry improves anything downstream.**
  §9.6 argues that features landing in the right place caps final-render accuracy
  regardless of pixel sharpness. That is ARGUED, not measured. The test would be
  whether a resolution fix (M95's) yields *more* once the geometry is right than
  it does on the shipped solve — an interaction, and neither milestone can measure
  it alone.
- **What would change my mind about §9's null:** an instrument that detects
  sub-pixel misregistration without relying on orientation, or a subject with
  clean angular statistics out to r>0.6 where `bee-3-cpl` is contaminated
  (clustering 0.42-0.62). The null is currently established only over r <= 0.55.

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

# §9.2-9.5 the retraction  (~6 min total)
# The orchestrator's instrument, verified on MY render first. Run it from a
# directory of mine: it writes anisotropy-controls.json / anisotropy.json
# relative to the CWD and must not overwrite the orchestrator's copies.
mkdir aniso -Force; cd aniso
python ..\..\ORCH-drift-check\anisotropy.py --controls C:\dev\strehl-out\M103\img\bee3-baseline.tiff
cd ..
copy aniso\anisotropy-controls.json data\aniso-controls-baseline.json

# Paired before/after. Imports the orchestrator's measure() unmodified and adds
# the pairing its own tile_keys argument exists for.
python src\aniso_pair.py C:\dev\strehl-out\M103\img\bee3-baseline.tiff `
     C:\dev\strehl-out\M103\img\bee3-m103.tiff `
     aniso\anisotropy-controls.json data\aniso-pair.json

# Why the +37% was wrong. acutance_check splits the statistic into sharpness and
# brightness factors; acutance_dist shows the distribution behind the bin mean.
python src\acutance_check.py C:\dev\strehl-out\M103\img\bee3-baseline.tiff `
     C:\dev\strehl-out\M103\img\bee3-m103.tiff data\acutance-check.json
python src\acutance_dist.py C:\dev\strehl-out\M103\img\bee3-baseline.tiff `
     C:\dev\strehl-out\M103\img\bee3-m103.tiff data\acutance-dist.json
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

**15.3 — `align_cmd.rs` (M97 owns; M103 must not edit). WITHDRAWN by §16.6 —
DO NOT APPLY.** Left in place because it was published and routed. Measured
afterwards: discarding spans 1-2 takes max per-frame placement error from 139.7
px to **628.1 px**; the prescribed frame-0 anchor fan is a 1.3 px no-op against a
0.8 px placebo; and `iterated_wide()` does not improve per-frame placement. The
original text follows, refuted.

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

**15.8 — URGENT, a live recurrence: solve caches are being written into the
READ-ONLY corpus right now.** MEASURED, 2026-08-24 08:20. M97 reported this
hazard tonight and asked that it not recur. It is recurring, from some process
other than M103.

At 08:20 I enumerated `D:\personal\macro\*\warpmap.txt` and found **eleven**
sidecars written within the previous six hours, one of them five minutes old:

```
bee-2-cpl            03:12:36        flowers-cpl          04:35:56
lavendar-cpl         04:34:44        leaf-2-cpl           04:36:51
flower-bud-alone-cpl 04:37:48        tweezers-cpl         04:38:35
coffee-bean          04:39:05        lead-1-cpl           04:55:28
flat-on-ruler-cpl    04:56:07        foam                 04:57:46
bee-3-cpl            08:15:27  <-- five minutes before this was written
```

**They are not mine.** Every M103 sidecar is 299-frame, reference 0 or 149, and
carries an `M103-` strategy string; all of mine live under
`C:\dev\strehl-out\M103\`, and every render I ran went through `STREHL_WARPMAP`,
which by construction writes nothing. The `bee-3-cpl` file currently on disk
reads:

```
frames 60
reference 30
strategy S3-ba-unit
```

a 60-frame subset under a bundle-adjust strategy — not a shape M103 ever
produced.

Three consequences for the orchestrator, in order of urgency:

1. **`D:\personal\macro` is stated READ-ONLY and is being written.** Whichever
   milestone is running `stack`/`align` without `STREHL_WARPMAP` is triggering
   the beside-the-capture cache write in the paths I may not edit
   (`align_cmd.rs` / `lib.rs`). The durable fix is to default that cache
   somewhere under `C:\dev\strehl-out\` and require an explicit opt-in to write
   beside a capture.
2. **`bee-3-cpl/warpmap.txt` no longer describes the owner's full stack.** It is
   a 60-frame, reference-30 solve sitting at the path a 299-frame consumer will
   read. Anything that trusts it without checking `frames` is reading a
   different stack than it thinks. Note the digest guard does **not** catch this:
   `stack-digest` covers name plus file sizes, not the frame subset.
3. **The torn-read hazard is live, not historical.** M97 saw a half-written
   read; with writes landing every few minutes across eleven stacks, any agent
   reading these paths now can catch one mid-rewrite. Until the write path is
   changed, readers should copy to a private path first — and writers should
   write-temp-then-rename, as M103's probe emitter does.

I have not touched these files, and I am not able to fix the write path from
inside my ownership boundary.

**15.9 — `experiments/ORCH-drift-check/anisotropy.py` (the orchestrator owns).**
Two notes, in order of importance. The instrument itself is sound: it passed all
five of its controls unmodified on my render (§9.2), and its verdict on my fix is
the one this report now carries.

1. **The multi-file `__main__` path does not pair its tile selection**, though
   `controls()` does and the module docstring is emphatic about why it must:

   > "The selection must not be allowed to depend on the treatment."

   `__main__` calls `measure(y, os.path.basename(p))` per file with
   `tile_keys=None`, so each file re-derives its own `MIN_POWER_Q` threshold. For
   a gate ladder — one solve, several gates — this is minor. For a before/after
   comparison of two *different solves* it is the documented failure mode, and I
   MEASURED it shifting deltas by up to **0.0161**, which is the same size as the
   effects being reported. Suggested minimal change:

   > ```python
   > results, keys0 = [], None
   > for p in args:
   >     y = load_luma(p)
   >     m = measure(y, os.path.basename(p), keys0)
   >     if keys0 is None:
   >         keys0 = set(m["keys"])   # pin on the FIRST file, reuse for the rest
   >     results.append({k: v for k, v in m.items() if k != "keys"})
   > ```

   `src/aniso_pair.py` in this milestone does exactly this by importing your
   `measure()` rather than reimplementing it, and additionally reports the
   unpaired numbers alongside so the two are always comparable.

2. **A caution worth folding into the docstring.** `aniso_px.py` correctly warns
   that the outer annuli are subject-contaminated on `bee-3-cpl` (clustering
   0.42-0.62). I confirm that independently: at r=0.75 my paired run reports a
   delta of **-0.1681**, larger than any usable annulus and in the opposite
   direction, purely from subject texture. The `CLUST_MAX = 0.30` rule is doing
   real work and should probably live in `anisotropy.py` itself rather than only
   in the downstream script, so that a future caller of `measure()` cannot
   accidentally quote an r>0.6 annulus.

**15.10 — a discipline candidate.** A visual before/after check whose crops are
selected by maximum texture is not a random sample of the frame; it is a sample
of the tail that dominates whatever texture-weighted statistic chose it. In this
milestone that produced a confident, wrong "I looked at the images and the
bristles are resolved" against a bin whose median was 0.9898. Suggested wording:

> **When a metric and the eye agree, check what selected the tiles the eye was
> shown.** If the crops were chosen by the same statistic being reported, the
> agreement is circular. Choose crops at random within the annulus, or at fixed
> coordinates, and report the median tile alongside the mean.


## 16. Second arm — the bar was wrong, and my own fix does not survive it

**This section retracts §15.3's recommendation and, with it, the operational
value of §8's B3 pass.** The code in `align.rs` is unchanged and was never on the
default path (B6), so nothing has to be reverted; what has to be withdrawn is the
advice to adopt it.

The orchestrator dispatched a second arm with a direct instruction — *"Ship the
gain correction. That is the deliverable. Not a further characterisation of the
shortfall"* — on the strength of M97b's arm ladder, and with one precondition:
test whether the real breathing track is curved before multiplying by 1/0.543,
because M102 planted a *linear* track and recovered 96.96% of it, which may be
circular. I tested the precondition. It fired, and then it kept firing.

### 16.1 The precondition fired: the track is curved (C1)

**MEASURED** (`src/curvature.py`, against `data/truth-dense.json`, a 39-rung RAW
ladder with no strehl code in its measurement path). The true breathing track
departs from its own straight chord by **46.1 plane px at j=200**, against a
pre-registered threshold of 10 px. The rate accelerates monotonically:
0.00030/frame over j=0–96, 0.00051 over 96–192, 0.00072 over 192–298. NCC holds
at 0.9696–0.9970 across the curved region, so this is not a confidence collapse,
and the truth instrument's own controls pass (SELF 1.00000; planted cases within
0.0016).

The orchestrator's hypothesis is confirmed: **M102's synthetic plant is linear
and the real track is not, so its 96.96% recovery does not transfer to real
captures.** Reported as the orchestrator asked, having been ARGUED by them and
now MEASURED here.

### 16.2 The finding that actually matters: end-to-end and per-frame are nearly independent

Every bar this project has used on the solve is **end-to-end** — frame 0 against
frame 298. M97's `signtest.py`, M86's span, M97b's "drift removed" column, and my
own B3 are all one number out of 299.

But the merge does not gather frames end to end. It gathers each frame at its own
`a_k`. So I scored the tracks **per frame**, on all 39 rungs of the independent
ladder, in the gauge the merge actually uses — `bee-3-cpl/warpmap.txt` says
`reference 149`, so the operative gauge is mid-stack, and rung 144 is the nearest
measured one (`src/gauge.py`, `src/placement.py`).

| solve | end-to-end residual | per-frame placement, mean |
|---|---:|---:|
| `deep()`, as shipped | 150.3 px | **36.4 px** |
| `iterated_wide()`, M103's fix | 2.9 px | **37.5 px** |

**MEASURED. A fifty-fold improvement in the headline number bought nothing where
it counts.** That is the whole of §9's null, explained: the render did not change
because the placements the render depends on did not change.

`gauge.py`'s controls: placebo (truth against truth) 0.000e+00 px; positive
control (a planted constant offset of +0.02 ln) reads 42.3 px against a closed
form of 42.3 px gauged at frame 0 and 2.9e-14 px gauged at 144, which is the
script's own claim demonstrated on a case with a known answer; sanity check that
the gauge-invariant spread is identical across gauges to 2.3e-13 px.

Gauge matters enormously here and it is not a technicality. Gauged at **frame 0**
my fix reads 98.2 px against the shipped solve's 39.4 px — two and a half times
worse. Gauged at **144** the two are level. The difference is a single constant
offset between frame 0 and the other 298 frames, which costs one frame in 299
when the merge references mid-stack and costs all 298 when it references frame 0.
Anyone quoting a placement number must say which gauge it is in. §15.4's
recommendation to move the reference to the end of the sweep now carries this
extra cost and should be re-priced before it is taken.

### 16.3 What I got wrong about my own fix, and how it was caught

I found the offset first and reached for a mechanism: `iterated_wide` was run with
a frame-0 anchor fan (`--anchor-from 0 --anchor-stride 8`), frame 0 is a terminal
node with no counterbalancing edges, and §6 of this report had already flagged the
long spans as over-shooting at 1.25–1.33 on 10–15 surviving tiles. Endpoint
leverage. It was a good story and the sidecar looked like its smoking gun: the
solve puts **22.1% of the entire 298-frame drift into the single step from frame 0
to frame 1**, −34.0e−3 against a mean increment of −0.517e−3, which is physically
impossible for a focus stack.

**The story is wrong.** `src/edgeset.py` re-solves the *same committed edge
measurements* through the real solver with controlled edge sets, so any difference
is attributable to the edge set alone. Dropping the anchor fan moves mean
placement error from 98.2 px to 99.5 px — a 1.3 px move against a placebo (drop a
deterministic 1% of non-frame-0 edges) of 0.8 px. **The fan is not the cause.**
The wiring control passes exactly: the unfiltered re-solve reproduces the
published `wm-iww-r0.txt` to 0.000e+00.

What *is* a cause, partly, is the over-shooting long spans: dropping spans
192/256/298 takes 98.2 px to 61.3 px, and dropping fan and long spans together
reaches 49.2 px (gauge 0). None of it survives re-gauging — at rung 144 every
variant lands between 36.3 and 37.5 px, indistinguishable from the shipped 36.4.

I am recording the refuted hypothesis rather than deleting it because it was
about to be published as a mechanism.

### 16.4 The instruction was right in direction and wrong in magnitude (S1)

**MEASURED** (`src/gaingauge.py`), per-frame placement error on the shipped solve,
gauge 144:

| gain applied to the shipped solve | mean placement error |
|---|---:|
| 1.000 (untouched) | 36.4 px |
| **1.842** (the 1/0.543 the orchestrator specified) | **25.6 px** |
| 1.459 (the per-frame optimum) | **22.5 px** |

**The gain correction is real and worth 30–38% of per-frame placement error.** The
orchestrator's instruction is vindicated on the axis that matters, which no
previous measurement had checked. The endpoint-derived 1.842 overshoots the
per-frame optimum of 1.459, because the shipped solve's shortfall is worst exactly
at the endpoint where that gain was fitted, so it over-corrects the interior — but
it still captures most of the available win.

Controls: placebo (gain 1.000) reproduces `gauge.py`'s 36.4 px; positive control
(a synthetic track built as truth×0.543) is nulled to 0.017 px by a sweep that
finds 1.8420 against a closed form of 1.8416; **negative control** (a pure shape
error, the track pulled half-way to its own straight chord, which preserves both
endpoints) is *not* nulled — 8.1 px in, 8.0 px out at a best gain of 1.007. That
last one is the discriminating control and it is what separates "a gain does not
help here" from "this instrument cannot see a gain helping".

**But it cannot ship as a constant, and that is measured, not argued.** M97
measured 54.3% recovery on `bee-3-cpl`; M97b measured 33.3% on
`dry-erase-marker-head-cpl`. Those imply gains of 1.84 and 3.00 — a 63% spread
across the only two stacks the corpus has measured. Shipping 1.84 leaves
`dry-erase` a third under-corrected; shipping 3.00 over-corrects `bee-3-cpl` by
63%. This is rule 6's "do not fit a shrinkage correction" and fact 52's refuted
cross-scene transfer, arriving from a new direction.

### 16.5 Per-span is not the answer either (and my negative control had to be fixed)

If the attenuation were a function of baseline, the correction would be per-span
and could be self-measured. **MEASURED** (`src/perspan.py`) — the shipped
estimator's response, fitted as the slope of measured log-scale on true
log-scale, is not monotone in span and never reaches 1.0:

| span | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 96 | 128 | 192 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r(s) | 0.130 | 0.184 | 0.232 | 0.334 | 0.545 | **0.659** | 0.516 | 0.420 | 0.238 | 0.102 |

An inverted U. Short baselines lose to peak-locking (§5.3), long ones to capture
starvation (§5.2), and the best span still recovers only 66%. Applying 1/r(s) per
span and re-solving:

| arm | mean | max | rms |
|---|---:|---:|---:|
| shipped, untouched | 36.4 | 139.7 | 54.1 |
| shipped + best scalar gain | **22.5** | — | — |
| shipped + per-span 1/r(s) | 31.6 | 105.5 | 38.4 |
| negative control, groups mixed | 46.9 | 354.1 | 74.7 |

**One scalar beats the per-span correction.** Over-correcting a span whose
response is 0.130 means multiplying it by 7.7, and the global least squares pays
for the injected noise. The span structure is real — the negative control, which
keeps the same number of groups but fills each with a mixture of baselines, is
*worse* than doing nothing — but exploiting it naively costs more than it earns.

**A control that could not fail, caught.** The first version of that negative
control permuted the span *labels*. That is a bijection on the grouping: the
groups are identical and only renamed, so it returned a byte-identical result by
construction. It was caught because it matched the treatment arm to four
significant figures. The fix assigns each edge a pseudo-random group from its
endpoints, preserving the degrees of freedom while destroying the span structure.
Recorded per the house rule about nulls passing while the instrument is blind:
this one would have passed while being incapable of failing.

### 16.6 Rule 6's span advice is measurably harmful on this stack

**MEASURED** (`edgeset.py`). Rule 6 says "discard spans 1–2 from the solve", and
§15.3 of this report recommended exactly that. Doing it takes max per-frame
placement error from 139.7 px to **628.1 px**; adding the prescribed frame-0
anchor fan on top does not help (551.7 px), and dropping spans 1–2 together with
the fan and the over-shooting long spans leaves the graph unable to place every
frame at all. Short edges are badly attenuated *and* load-bearing for local
connectivity. **§15.3 is withdrawn.**

### 16.7 What I am not shipping, and why

Nothing new goes into `align.rs` beyond a measured warning on
`iterated_wide()`'s docstring, because:

- the fix I already landed does not improve per-frame placement (37.5 vs 36.4 px)
  and it *blocks* the gain correction, which reads 70.0 px when the 1.84 gain is
  applied to it because it has already absorbed the endpoint shortfall;
- the gain correction that does work is a scene-fitted scalar, which rule 6 bans
  and which the corpus's own two measurements (1.84 and 3.00) show is not
  transferable;
- and the self-measured route that would make it shippable is not built. The
  probe's existing `plant` command synthesises a moving frame from a *single real
  frame*, so it carries no defocus difference and measures a response of ~1 by
  construction — it is B2's placebo, not the correction. A response measured on
  the **actual pair**, by planting ±δ on frame k of the real (j,k) edge and
  re-measuring, is the missing instrument. It is the brief's candidate fix 1,
  restricted to the form fact 52 does not refute, and §16.4 now prices it: it has
  up to 38% of per-frame placement error to recover on `bee-3-cpl`.

I may not verify my own work, and I am not going to hand over an unverified
second fix on the same night the first one failed its real bar.

### 16.8 Candidate facts

- **P18 (MEASURED).** `bee-3-cpl`'s breathing track departs from linear by 46.1
  plane px at j=200, with a monotonically accelerating rate (0.00030 → 0.00072 per
  frame). The track is curved, not a straight ramp.
- **P19 (DERIVED, from P18).** M102's 96.96% recovery of planted drift was
  measured against a *linear* plant and does not transfer to real captures. Its
  own §6–§7 flagged the missing capture; P18 supplies it.
- **P20 (MEASURED).** End-to-end alignment residual and per-frame placement error
  are nearly independent. `iterated_wide` moves the first 150.3 → 2.9 px and the
  second 36.4 → 37.5 px on the same stack, same solve, same ladder.
- **P21 (DERIVED, from P20).** Every published acceptance bar on the strehl solve
  — M97's `signtest.py`, M86's span, M97b's "drift removed", and M103's own B3 —
  scores one frame pair out of 299 and is blind to where the other 297 land. This
  is discipline 621's warning about relative scores, one level up: an *absolute*
  score can still be absolutely the wrong quantity.
- **P22 (MEASURED).** A per-frame placement number is meaningless without its
  gauge. `iterated_wide` reads 98.2 px gauged at frame 0 and 37.5 px gauged at
  rung 144, a difference of one constant offset.
- **P23 (MEASURED).** A scalar gain on the shipped solve is worth 36.4 → 25.6 px
  of per-frame placement error at the orchestrator's 1.842, and 22.5 px at the
  per-frame optimum of 1.459. The gain correction works; the endpoint-fitted value
  overshoots.
- **P24 (MEASURED).** The required gain is stack-dependent: 1.84 on `bee-3-cpl`
  (M97's 54.3%) against 3.00 on `dry-erase-marker-head-cpl` (M97b's 33.3%). No
  single constant serves both.
- **P25 (MEASURED).** The shipped estimator's per-span response on `bee-3-cpl` is
  an inverted U — 0.130 at span 1, peaking at 0.659 at span 32, falling to 0.102
  at span 192 — and never reaches 1.0 at any baseline.
- **P26 (MEASURED).** Correcting per span is *worse* than one scalar (31.6 px vs
  22.5 px), although the span structure is real (a matched-degrees-of-freedom
  control with mixed baselines reads 46.9 px, worse than the untouched 36.4 px).
- **P27 (MEASURED).** Discarding spans 1–2, as rule 6 directs and as §15.3 of this
  report recommended, takes max per-frame placement error from 139.7 px to 628.1
  px on `bee-3-cpl`; combined with the other prescribed changes the graph cannot
  place every frame.
- **P28 (MEASURED, negative).** The frame-0 anchor fan is not the cause of
  `iterated_wide`'s frame-0 offset: removing all 29 fan edges moves mean placement
  error by 1.3 px against a 0.8 px placebo.

### 16.9 Reproducing this section

```powershell
$env:PYTHONIOENCODING='utf-8'
cd experiments\M103-halfdrift

# C1/C2 -- is the track curved, and is the shortfall uniform?
python src\curvature.py                    # data\curvature.json

# per-frame placement, and the ceiling on any scalar gain
python src\placement.py data\truth-dense.json `
    C:\dev\strehl-out\M103\wm-baseline-r0.txt `
    C:\dev\strehl-out\M103\wm-iww-r0.txt data\placement.json

# which edges cause the frame-0 offset  (re-solves, ~2 min)
python src\edgeset.py data\IWW-edges.csv data\truth-dense.json data\edgeset.json

# the gauge question -- run AFTER edgeset.py, it reads its sidecars
python src\gauge.py data\truth-dense.json data\edgeset.json data\gauge.json

# the shipping decision
python src\gaingauge.py data\truth-dense.json data\gaingauge.json

# scalar versus per-span  (re-solves, ~2 min)
python src\perspan.py data\A-deep-edges.csv data\truth-dense.json data\perspan.json
```

Every script prints its own controls before its result and exits non-zero if they
fail. Sidecars and filtered edge sets are written under `C:\dev\strehl-out\M103\`
only, temp-then-rename, per M97's torn-read hazard; nothing is written beside the
captures.

### 16.10 Routed to the orchestrator (additions to §15)

**16.10a — §15.1's ledger row is now wrong.** Replace with:

> `M103` — the alignment solve recovers half the drift. Found the cause (coarse
> capture starvation plus peak-locking in the sub-pixel NCC) and closed it in
> `align.rs`, taking end-to-end residual on `bee-3-cpl` from 150.3 to 2.9 plane
> px. Then measured that end-to-end residual and **per-frame placement** are
> nearly independent (36.4 → 37.5 px for the same fix), which retracts the fix's
> operational value, explains three separate render nulls, and invalidates the
> acceptance bar used by M86, M97, M97b and M103 alike. Priced the scalar gain
> correction on the axis that matters — 36.4 → 25.6 px at 1.842 — and measured
> that it cannot ship as a constant (1.84 on `bee-3-cpl`, 3.00 on
> `dry-erase-marker-head-cpl`). Also found `signtest.py` cannot measure a residual
> above 1.0. Then cleared the blob gate: the waxy blobs M97b attributed to the
> gain correction are **already in the shipped render** (1:1, no resampling), and
> in the region judged disqualifying the shipped arm measures 21% *more*
> piecewise-flat than the corrected one. `docs/research/M103-halfdrift.md`.

**16.10b — §15.3 is WITHDRAWN.** Do not apply it. Measured in §16.6: discarding
spans 1–2 takes max per-frame placement error to 628.1 px, the frame-0 anchor fan
is a 1.3 px no-op against a 0.8 px placebo, and `iterated_wide()` should not
become the default.

**16.10c — for M97b.** M97b's GAINED arm is, as far as this report can tell,
endpoint-gauged: "89.5% drift removed" is a frame-0-against-frame-N number. §16.2
measures that such a number is nearly independent of per-frame placement. That
does **not** refute M97b's 19–32% sharpness win, which was measured on a render
with a seam control that ran against the result — and §16.4 independently supports
a real gain being available. But the two should be reconciled: M97b's GAINED track
should be scored per frame against a dense ladder on `dry-erase-marker-head-cpl`,
in the gauge that stack's merge uses. If it reads level with ALIGNED there, the
sharpness win has a different cause than placement and needs one.

**16.10d — for M102.** §16.1 confirms the circularity M102 flagged in its own §7.
The real track on `bee-3-cpl` is curved by 46.1 plane px from its chord. A linear
plant against a linear model measures arithmetic. Suggest M102's simulator take
the measured track shape from `experiments/M103-halfdrift/data/truth-dense.json`.

**16.10e — a discipline candidate.** Suggested wording:

> **Score the solve where the merge reads it.** A registration solve is consumed
> per frame, so an end-to-end residual between the two extreme frames is one
> sample out of N and can be driven to zero while every interior placement stays
> exactly as wrong as it was. Before accepting any alignment bar, state the frame
> set it scores and the gauge it scores in — a whole-graph offset is free in one
> gauge and costs every frame in another.

**16.10f — a second discipline candidate, from §16.5.** Suggested wording:

> **A control that relabels is not a control.** Permuting the labels of a
> grouping is a bijection: the groups are unchanged and the "shuffled" arm
> reproduces the treatment arm exactly, by construction. If a negative control
> returns the treatment result to several significant figures, suspect that it
> cannot fail before concluding the effect is spurious.

---

## 17. The waxy blobs — the shipping gate

The orchestrator opened M97b's side-by-side themselves, judged the waxy blobs in
the bright low-texture region **disqualifying as shipped**, and added a gate: the
gain correction must not ship until the blobs are either diagnosed and fixed, or
shown to be an artefact of M97b's viewer. They offered three mechanisms —
(1) election mottle where the focus statistic has no signal, (2) coverage running
out as the corrected warp pushes further, (3) M97b's Lanczos downsample, applied
to the corrected side only — and ordered hypothesis 3 killed first because it is
one command.

The answer turns out to be none of the three, and it is a better answer than any
of them: **the blobs are already in the render that ships today.**

### 17.1 Hypothesis 3 is dead (MEASURED)

`src/blobs.py` crops the same scene region from the corrected TIF twice: once at
1:1 with no resampling of any kind, and once through M97b's exact viewer path
(474 px crop, Lanczos to 420 px). It carries a SELF control — the PNG it writes is
compared byte-for-byte against the pixels it read — and a positive control that
measures what Lanczos ringing on a known smooth ramp is actually worth.

- The blobs are **plainly present in the 1:1 crop with zero resampling**: a smooth
  grey lobe with a hard, curved, *closed* boundary. A separable 1-D kernel cannot
  synthesise a closed curved boundary that was not already in the data.
- Lanczos 474→420 on a synthetic smooth ramp produces **0.288 DN** of banding out
  of 255 — roughly one part in 900, and around two orders of magnitude below the
  step across a blob edge.

The viewer is exonerated. The artefact is in the pixels.

### 17.2 The blobs are in the SHIPPED render too (MEASURED)

This is the finding that decides the gate, and it needed no instrument at all —
only opening the other file, which is the step that had not been taken.

`src/crop2.py` takes a matched pair of 1:1 crops, one from each arm, over the
bright low-texture area at the bottom of M97b's lower-right panel. The corrected
arm's origin is refined by NCC search rather than assumed, because the predicted
mapping is exact at the frame centre and drifts with radius — which is not
incidental, it is this milestone's own defect showing up in my crop arithmetic.
The lock is reported so a bad one is visible, in the manner of M97b's honest
0.2253.

- Target region locks at **NCC 0.8242**, mean 165.2 vs 155.3 DN, sd 38.1 vs 37.9.
  A genuinely matched pair.
- Opened at 1:1: **the shipped render carries the same class of artefact** —
  smooth grey lobes with hard closed boundaries, and hard-edged tonal contours
  through the bright region.

The orchestrator's reading of the shipped side as "duller but *natural*" is, on
the evidence of the file itself, mistaken. So is M97b's §8 description of the
blobs as an artefact "that the shipped render does not have". Both were made by
comparing two panels; neither was made by interrogating the shipped panel alone.

### 17.3 The controlled measurement says the shipped arm is the waxier one

`src/waxy.py`, scoped to the NCC-0.8242 pair. The statistic is **not** smoothness
— an out-of-focus background is smooth and looks right. It is *piecewise*-flatness:

```
flatness = median over structured px of  sigma(31 px) / (sigma(5 px) + 0.5)
```

This carries a physical guarantee the earlier attempts lacked. Defocus, diffraction
and demosaic are all low-pass: they attenuate the 5 px and 31 px windows together,
so the ratio stays bounded. Only piecewise-constant content drives sigma(5) to the
quantisation floor while sigma(31) stays high, because only a step has energy at
large scale and none at small. The election can produce one; no optical process can.

Controls, all three passing:

| control | reads | verdict |
|---|---|---|
| PLACEBO shipped vs itself | `+0.000000` | PASS |
| POSITIVE hard-edged constant patch, 10.1% of crop | `+0.2004` | PASS |
| NEGATIVE **natural** blurred patch, same area, feathered | `−0.0021` | PASS |
| separation piecewise-flat / optically-soft | **97.4×** | — |

The negative control is the one that matters and the one my three earlier
detectors did not have. Without it, an instrument that fires on both waxiness and
softness would convict the gain correction merely for changing what is in frame.

**Whole matched crop** — shipped `3.6053`, corrected `3.2118`. But this readout is
confounded: `sigma(5)` differs between arms (0.977 vs 1.155 whole-crop), and the
corrected arm is genuinely sharper in the textured fibres (M97b, MEASURED), which
raises `sigma(5)` and mechanically depresses the ratio for a reason unrelated to
waxiness. Median and p90 move in opposite directions (`7.4837` → `7.5435`), which
is the signature of exactly that split.

**Restricted to the bright low-texture subset**, where the artefact lives and
where there is little fine texture to sharpen — positive control `+0.5476`,
natural control `+0.0006`, separation **959.5×**:

| arm | flatness | sigma(5) | sigma(31) | px |
|---|---:|---:|---:|---:|
| shipped | **3.7324** | 1.876 | 8.422 | 50 927 |
| corrected | **3.0837** | 1.895 | 7.326 | 46 148 |

`sigma(5)` is now matched to within 1% — the sharpness confound is gone — and the
whole difference sits in `sigma(31)`. **The shipped render is 21% more
piecewise-flat than the corrected one in the region judged disqualifying**, a gap
larger in magnitude than the positive control's own move.

### 17.4 I do not get to keep both readings

Twenty minutes before running `waxy.py` I looked at the same matched pair and
wrote that the lobes were "larger and harder-edged in the corrected arm". The
controlled statistic says the opposite, with a working positive control, a
working natural-smooth negative control, and a matched `sigma(5)`. **I withdraw
the eye-read.** It was made on two crops of unequal pixel size (640 vs 722 for the
same scene extent), where the larger one presents every feature 12.8% bigger, and
that alone will make lobes look larger. The measurement stands and the impression
does not.

I record this because it is the same error, in the same direction, that produced
the gate: a side-by-side invites you to attribute to the *treatment* whatever you
notice in the *treated panel*, when the honest question is what the control panel
looks like when examined on its own terms.

### 17.5 What this says about mechanisms 1 and 2

**Hypothesis 2 (coverage) is not supported.** ARGUED. Coverage failure is a
boundary phenomenon by geometry — `gather_checked` writes `NaN` where a frame does
not reach, and that region is an annulus at the frame edge. The blob examined here
sits well interior, and the artefact appears in the *shipped* arm, whose warp is
the shorter of the two and therefore has the more generous coverage. A mechanism
that predicts "worse when you warp further" cannot explain "worse in the arm that
warps less".

**Hypothesis 1 (election mottle) survives and is the natural reading.** DERIVED.
The election is a property of the merge, not of the solve. Fact 73 records that
the box mean of the gradient magnitude is blind on monotone content, so in a
bright low-texture region the focus statistic is choosing between frames on noise.
Adjacent cells then elect frames at different depths, and the seam between two
differently-defocused frames is a step — piecewise-flat, hard-bounded, exactly
what §17.3 measures and what §17.1 shows at 1:1. On that account the gain
correction does not *create* the blobs; it perturbs the warp, so it changes *which*
frame wins in every low-signal cell, and the blobs **move**. In a side-by-side,
relocated blobs read as new ones, because the eye is offered no view of the
control panel by itself.

I have not proved hypothesis 1. Proving it wants an elected-frame-index debug map
out of the merge, and `merge_cmd.rs` is contended — see §17.8.

### 17.6 Four instrument-control failures, recorded because they were caught

Three whole-frame waxiness detectors failed before `waxy.py` passed. Every one was
caught by its own positive control, and every one failed for a *plant* reason
rather than a statistic reason:

1. `blobs.py` — `to8()` right-shifted by 8 on data that was already `uint8`,
   producing black frames. The tell was `smooth_frac = 1.0000` on all three panels.
2. `waxmap.py` — the positive plant was `median + 40` in a *dark* region and never
   crossed the brightness threshold; 3% of planted area recovered. Then a per-cell
   edge test that only fired on a blob's perimeter, and block-*mean* gradient
   pooling that diluted a 140 DN step across 16 px of a 256 px cell to ~8.75 DN.
   Once passing, its whole-frame verdict still disagreed with what is plainly
   visible at 1:1, so **its numbers are not quoted here.**
3. `waxsweep.py` — planted a bright fill at a fixed 175 DN on a subject whose p95
   brightness cut is **253 DN**. The planted pixels never entered the bright set;
   the control read exactly `+0.000000`.
4. `waxy.py` — the first bright-subset positive control filled at the *local
   median*, below the p75 cut, and read `−0.0033`. Fixed by filling at p85.

Failures 3 and 4 are the same mistake twice: **a plant specified in absolute units
against a distribution I had not looked at.** The general form is worth stating.

> **A plant must be specified against the distribution it is planted into.** Choosing
> a level, a size or a contrast from intuition rather than from the data risks
> planting outside the selector the instrument uses, which returns a clean null
> that is indistinguishable from a null result. Take plant parameters from
> percentiles of the actual array, and print the selector's thresholds next to
> the plant's value so a mismatch is visible in the log.

Failure 2 also generalises, and it is why the whole-frame route was abandoned:

> **An absolute threshold tuned against an intuition is not calibrated.** If a
> detector passes its controls but disagrees with direct observation at a location
> you can point to, the controls have established sensitivity to the *plant*, not
> to the artefact. Scope the measurement to a region where the artefact is known
> to be visible before trusting a whole-frame aggregate.

### 17.7 Candidate facts

- **P29** (MEASURED) The waxy blobs M97b reported in the gain-corrected render are
  present in the **shipped** render as well, at 1:1 with no resampling, on
  `dry-erase-marker-head-cpl`. They are not created by the gain correction.
- **P30** (MEASURED) In a matched crop locked at NCC 0.8242 over the bright
  low-texture region, restricted to that region and with `sigma(5)` matched to
  within 1%, the shipped render measures `flatness` 3.7324 against the corrected
  render's 3.0837 — the **shipped** arm is 21% more piecewise-flat.
- **P31** (MEASURED) Lanczos 474→420, the resample in M97b's viewer, produces
  0.288 DN of banding out of 255 on a smooth ramp. It cannot account for the
  artefact, and hypothesis 3 is refuted.
- **P32** (DERIVED) `sigma(31)/sigma(5)` separates piecewise-flat content from
  optically-soft content by 97.4× on real render data, because every optical
  degradation is low-pass and attenuates both windows together while a step
  populates only the large one. A useful primitive for any future "is this an
  artefact or is it just out of focus" question.
- **P33** (ARGUED) A side-by-side systematically over-attributes to the treatment:
  an artefact present in both arms but *relocated* by the treatment is read as new,
  because the control panel is never examined on its own terms. Two independent
  readers (M97b §8, and the orchestrator) and this milestone's own first eye-read
  all made this error on the same image.
- **P34** (MEASURED, cheap) The two arms' crops of the same scene extent differ in
  pixel size by 1.1278×. Comparing them without placing both on a common scene grid
  makes every feature in the corrected arm look 12.8% larger, which is enough on
  its own to make lobes read as "bigger".

### 17.8 Routed to the orchestrator

**17.8a — the gate is answered, and the answer is not one of the three.** The
blobs are neither the viewer (§17.1, refuted) nor a consequence of warping further
(§17.5, unsupported). They are already in production. The correct statement to the
owner is not "the gain correction melts highlights" but "the merge's election
mottles bright low-texture regions, today, in the render he already has, and the
gain correction moves the mottle without measurably worsening it — by the one
controlled measurement available, it slightly improves it."

**17.8b — this removes the blob objection to shipping, but §16 still stands
against shipping.** I am not reversing §16.7. The gain correction should not ship
as a constant, for the reason measured there and unchanged by this section: 1.842
on `bee-3-cpl` against 3.00 on `dry-erase-marker-head-cpl`, and per-frame
placement that a scalar cannot fix. The blob gate was a second, independent
objection; it is the one I can now clear. **Clearing it does not clear the first.**

**17.8c — a patch I cannot write, for whoever owns `merge_cmd.rs`.** Hypothesis 1
is testable in one run with a debug output that writes the *elected frame index*
per pixel as a 16-bit image, alongside the merge. The prediction is specific and
falsifiable: inside a blob the index map is piecewise constant with the same
boundaries as the visible lobe, and the index difference across that boundary is
large; in the textured fibres it is fine-grained and locally continuous. M96's
disconnected-competitive-set statistic (25.247% on `bee-3-cpl`) is the aggregate
form of the same measurement and could be reported per region. If the index map
does not show lobe-shaped plateaus, hypothesis 1 dies too and the artefact wants a
new explanation.

**17.8d — for M97b.** §8's statement that the blobs are an artefact "that the
shipped render does not have" is refuted by P29. M97b's §8 is otherwise the model
this section tried to follow — it built a viewer, caught two defects in it before
believing its output, and volunteered an inconvenient artefact. The correction is
to the comparison, not to the honesty.

### 17.9 Reproducing this section

**Provenance of the two inputs.** Both TIFs were rendered by **M97b**, not by this
milestone, on `dry-erase-marker-head-cpl` at **`--gate 2`** (recorded in M97b's
report), at 07:21:25 and 07:24:23 on 2026-08-24 — both **after** the `885e9f7`
alignment watershed of 03:15:23, so both describe an *aligned* merge. The gate is
non-default (`DEFAULT_GATE = 4.0`), but it is the **same** for both arms, so the
comparison is internally matched. Recorded here in full because "we used the
default" is not a record and defaults move.

```powershell
$env:PYTHONIOENCODING='utf-8'
cd experiments\M103-halfdrift

# hypothesis 3: 1:1 versus M97b's exact Lanczos path, plus the ramp control
python src\blobs.py C:\dev\strehl-out\M97-before-after\marker-TODAY-shipped.tif `
                    C:\dev\strehl-out\M97-before-after\marker-POSSIBLE-gaincorrected.tif `
                    C:\dev\strehl-out\M103\blobs

# the matched pair, NCC-locked, no resampling of either arm  (~5 min, 190 MB TIFs)
python src\crop2.py C:\dev\strehl-out\M97-before-after\marker-TODAY-shipped.tif `
                    C:\dev\strehl-out\M97-before-after\marker-POSSIBLE-gaincorrected.tif `
                    C:\dev\strehl-out\M103\blobs

# the decision: piecewise-flatness with a natural-smooth negative control
python src\waxy.py C:\dev\strehl-out\M103\blobs\target-brightlowtexture_SHIP_640px.png `
                   C:\dev\strehl-out\M103\blobs\target-brightlowtexture_CORR_722px.png `
                   data\waxy.json
```

`waxy.py` exits non-zero if any control fails. The two failed detectors
(`waxmap.py`, `waxsweep.py`) are committed unrepaired, with their failure modes in
their docstrings, because §17.6 is worth more to the corpus than a tidy directory.

**The one thing a verifier should do that no script does:** open
`C:\dev\strehl-out\M103\blobs\target-brightlowtexture_SHIP_640px.png` — the
*shipped* crop — at 1:1 and look at the left third. If the hard-bounded grey lobe
is not there, P29 is wrong and everything in §17.2 onward falls.

---

## 18. Is `e(j)` smooth or jittery? — jittery, by ~110×

The orchestrator asked for one number rather than a fix, because fact 1393
measured `n_eff = 1` wherever there is detail: a detailed output pixel takes
exactly **one** frame, so a placement error there cannot blur it, only displace
it. What then matters is not the magnitude of `e(j)` but `|de/dj|` — the
disagreement between frames that neighbouring pixels elect.

**This is the only number in this milestone that needs no gauge.** §16.2
established that per-frame placement is meaningless without one, the same track
reading 98.2 px at frame 0 and 37.5 px at rung 144. A whole-graph constant offset
cancels in a first difference and twice over in a second, so everything below is
gauge-invariant. That is a property of the question, not a virtue of the
instrument.

**Added after the ownership change**, needing no `align.rs`: §18.6 extends the
same statistic to the **election lag** the mechanism actually runs on, and finds
the disagreement **nearly flat in lag** — 0.4829 px at lag 1 rising only to
0.7191 px at lag 8, against 2.83× for a random walk. The jitter is bounded and
high-frequency, not accumulating. §18.7 records that the lag sweep's first
control could not fail and how it was replaced.

### 18.1 Two routes, because one of them needs no truth data

**R1**, as asked: `de(j) = ds(j) − dt(j)`. The truth ladder exists at 39 of 299
rungs, so `dt` comes from a smooth fit — a modelling choice, reported at three
polynomial orders with its residual.

**R2**: the second difference of the solve alone, `s(j+1) − 2s(j) + s(j−1)`.
Truth-free, fit-free, parameter-free, and available at 297 interior frames rather
than 39. **R2 is the trustworthy one**; R1 is reported because it was what was
asked and because agreement between them is worth more than either alone.

**Why curvature cannot contaminate R2 — DERIVED, and then measured.** C1 measured
the real track departing its own chord by 46.1 plane px at `j = 200`. For a
smooth arc, a departure `d` over `N` frames implies a second difference near
`8d/N² = 8 × 46.1 / 200² =` **0.0092 px**. Control C below plants exactly that
curvature and measures **0.0044 px median, 0.0060 max** — inside the derived
ceiling. Two orders of magnitude of headroom, established rather than assumed.

### 18.2 Controls

| control | expectation | measured | verdict |
|---|---|---|---|
| **A placebo** — a purely linear track | exactly 0 | `0.0000` | PASS |
| **C specificity** — smooth track, **real** breathing curvature | ≪ jitter | `0.0044` med, `0.0060` max | PASS |
| **B positive** — planted ±0.5 px alternating | `4A = 2.00 px` | `2.0000 px`, **100.0%** | PASS |

Control C is the one that matters, and it is the analogue of the natural-smooth
plant that finally made `waxy.py` honest. Without it, an instrument that reports
curvature as jitter would answer this question backwards, and confidently — on a
track that C1 has already measured to be strongly curved.

### 18.3 The answer

**R2 — the shipped solve, truth-free, gauge-free** (plane px at corner radius):

| set | median | p90 | p99 | max | ≥0.5 px | ≥1 px |
|---|---:|---:|---:|---:|---:|---:|
| **all frames** | **0.4829** | **1.0772** | 2.1533 | 9.7069 | 47.8% | **13.8%** |
| near reference (\|j−149\| ≤ 50) | 0.4464 | 0.9873 | 1.6542 | 1.7045 | 39.6% | 9.9% |
| far from reference (> 100) | 0.6259 | 1.1971 | 2.8392 | **9.7069** | 65.6% | 19.8% |

**R1 — first difference of the error**, insensitive to fit order:

| truth fit | median | p90 | p99 | max | ≥1 px |
|---|---:|---:|---:|---:|---:|
| degree 3 (resid 2.46 px) | 0.5560 | 1.5405 | 2.2494 | 8.9838 | 27.9% |
| degree 4 (resid 1.92 px) | 0.5624 | 1.4945 | 2.1825 | 8.7791 | 27.9% |
| degree 6 (resid 2.07 px) | 0.5669 | 1.4990 | 2.0635 | 8.1075 | 28.2% |

**MEASURED: the track is jittery.** Against the orchestrator's stated threshold —
smooth means an increment much below 1 px, jittery means at or above it — the
median sits at 0.48–0.57 px, the p90 exceeds 1 px on both routes, and between
**13.8% (R2) and 28% (R1)** of adjacent frame pairs disagree by a plane pixel or
more. The median is **~110× control C's 0.0044 px**, which is what a genuinely
smooth track with this stack's real curvature reads.

**The most useful framing, DERIVED.** The mean frame-to-frame breathing increment
on this stack is `−0.517e−3` in ln, which is `0.517e−3 × 2112.9 =` **1.09 plane px
per frame**. The median jitter of 0.4829 px is therefore **44.2% of the true
inter-frame step**. Adjacent frames' relative placement is uncertain by nearly
half of the actual motion between them.

**It is worse where the spans are starved.** Far from the reference the median
rises 0.4464 → 0.6259 px and the maximum rises 1.70 → 9.71 px, a 5.7× worsening
of the worst case. §16.5's inverted-U response predicts exactly this: the long
baselines that carry the far frames are the ones whose response collapses to
0.102.

### 18.4 What this means, and what it does not

**DERIVED, and it follows directly from fact 1393.** At `n_eff = 1` a detailed
pixel cannot be blurred by a placement error. But two *adjacent* detailed pixels
electing frames `j` and `j+1` inherit those frames' placements, and those differ
by a median 0.48 px and by ≥1 px one time in seven. The output is then a mosaic
of individually sharp patches drawn from inconsistently placed sources. The
signature is **local geometric incoherence** — edges that step, features that
shear across an election boundary — and not softness.

**ARGUED.** This is a candidate mechanism for the waxy blobs of §17, and it
explains a detail §17 could not: the blobs have *hard, closed boundaries*. An
election boundary between two frames whose placements disagree by ≥1 px is a
step, and §17.3 measured the artefact as piecewise-flat rather than merely soft,
with a 97.4× separation from optical softness. Two independent measurements now
point at the election boundary.

**What this does NOT establish.** It does not show the jitter is visible; §17's
instrument and the orchestrator's `anisotropy.py` both work on renders and could
test that, and neither has been pointed at this. It does not show the jitter is
larger than the resampler's own contribution. And it does not identify a cause —
peak-locking in the sub-pixel NCC is the obvious suspect given §16.5, but that is
a hypothesis and this section did not test it.

**No corrective was built,** per instruction. Nothing new enters the solver.

### 18.5 Candidate facts

- **P35** (MEASURED) On `bee-3-cpl`, the shipped solve's frame-to-frame placement
  increment has median **0.4829 plane px**, p90 **1.0772 px**, max **9.7069 px**,
  with **13.8%** of adjacent pairs disagreeing by ≥1 px. Truth-free, fit-free and
  gauge-invariant (second difference of the solved track).
- **P36** (MEASURED) The same statistic on a synthetic track carrying this stack's
  *real* breathing curvature reads **0.0044 px** — so the measured jitter is
  ~110× what curvature alone can produce, and curvature is not being mistaken for
  jitter.
- **P37** (DERIVED) The mean true inter-frame step is 1.09 plane px, so the median
  jitter is **44.2% of the actual motion between adjacent frames**.
- **P38** (MEASURED) Jitter is worse far from the reference: median 0.4464 →
  0.6259 px and max 1.7045 → 9.7069 px comparing `|j−149| ≤ 50` against `> 100`,
  consistent with §16.5's collapse of long-baseline response to 0.102.
- **P39** (DERIVED) A smooth arc departing its chord by `d` over `N` frames has a
  second difference near `8d/N²`. With C1's 46.1 px at `j=200` this bounds
  curvature's contribution at 0.0092 px, which is what makes a truth-free jitter
  measurement trustworthy on a curved track.

### 18.6 Election lag — pricing fact 1411's actual mechanism

Fact 1411 argues that at `n_eff = 1` a placement error cannot blur a detailed
pixel, only displace it, so the predicted signature is local geometric
incoherence where **adjacent pixels elect different frames**. The severity of
that mechanism is not set by the lag-1 increment §18.3 reports. It is set by the
disagreement between the frames adjacent pixels actually elect — and M96
measured a **25.247% disconnected competitive set** on this stack, so elections
jump and the operative lag is not always 1.

The same truth-free second difference, taken at spacing `L`, prices it:

| lag `L` | median px | p90 px | max px | ≥1 px | curvature ceiling | ratio |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.4829 | 1.0772 | 9.7069 | 13.8% | 0.0092 | 52.5× |
| 2 | 0.4635 | 1.2061 | 4.8287 | 16.3% | 0.0368 | 12.6× |
| 4 | 0.5635 | 1.3982 | 8.8555 | 27.1% | 0.1472 | 3.8× |
| 8 | 0.7191 | 2.2032 | 18.0753 | 37.1% | 0.5888 | 1.2× |
| 16 | 1.6506 | 3.4737 | 11.7409 | 72.7% | 2.3552 | 0.7× |
| 32 | 4.4863 | 8.3860 | 11.0251 | 83.0% | 9.4208 | 0.5× |
| 64 | 11.6812 | 25.2607 | 27.3123 | 93.0% | 37.6832 | 0.3× |

`L = 1` reproduces §18.3's 0.4829 exactly, which is the internal consistency
check that the lag generalisation is the same statistic.

**The ceiling column is what makes this readable, and it is what kills the
bottom half of the table.** A smooth arc's second difference at spacing `L`
grows as `f''·L²`, so P39's 0.0092 px bound scales to 0.59 px at `L = 8` and
37.7 px at `L = 64`. Beyond `L ≈ 8` the statistic can no longer separate genuine
disagreement from the breathing curve the stack really has, and the rows below
that line are quoted only to show where the method dies. **Do not read the
`L = 32` and `L = 64` rows as measurements of jitter.** They are dominated by
real, correct geometry.

Within the trustworthy band the result is the interesting one:

> **Disagreement is nearly flat in lag.** Median rises only 1.49× from `L = 1`
> to `L = 8` (0.4829 → 0.7191 px), against **2.83×** for a random walk and
> **8×** for a linear drift — and a bounded part of even that 1.49× is the
> curvature ceiling, which reaches 0.59 px by `L = 8`.

So the jitter is a **bounded, high-frequency disturbance, not an accumulating
one**. Two pixels electing frames anywhere from 1 to 8 apart inherit placements
disagreeing by ~0.5–0.7 px at the median and 1.1–2.2 px at p90. That is the
number fact 1411's mechanism runs on, and it does not get worse with election
distance in the range where elections plausibly land.

### 18.7 A control that could not fail, caught and replaced

The first version of this lag sweep detrended `e(j)` with a degree-4 polynomial
fit and used, as its control, a "smooth track" **built from that same fit**. It
read exactly `0.0000` at every one of eight lags. That is not a passing control;
it is a polynomial subtracted from itself, and it is the identical failure to
`perspan.py`'s bijection from §16 — the second time this milestone has built a
control whose output was determined by construction.

Replacing the control track with a genuinely different smooth curve (degree 8
through the same rungs, detrended by degree 4) made it **fail informatively**:
trend-model choice alone contributed up to **0.7675 px at `L = 1`** and
**7.4709 px at `L = 64`** — comparable to the signal being claimed. That is a
real defect in the polynomial route, and it is why §18.6 above is computed
truth-free and fit-free instead, in the manner of §18.3's R2.

**The headline numbers of §18.3 were never exposed to this**, because R2 uses no
truth data and no fit at all. The contamination was confined to the route that
did, and the fix was to stop using that route rather than to improve its fit.

The generalisable form, and it now has two instances in one milestone:

> **A control built out of the same object as the treatment cannot fail.**
> Before trusting a control that reads clean, ask what it would take to make it
> read dirty. If no answer exists, it is decoration. `0.0000` at eight
> consecutive lags should have been read as an alarm, not a pass.

**A third instance, found by mutation rather than by inspection.** The replaced
lag control above was computed at line 229 while the exit code was decided at
line 172 from `a_ok and b_ok and c_ok`. So `lag_ok` was printed, and stored in
the JSON, and **could not change the exit status**. This is a nastier variant
than the other two, because the verdict it prints is entirely real — the failure
is only in whether anything is listening.

It was caught by asking a question this milestone had not asked of its own
harness: *have I ever seen this gate print a failure?* The answer was no. The
measurement:

| arm | exit | expected |
| --- | --- | --- |
| real run, current | 0 | 0 |
| lag threshold forced impossible, current | 1 | 1 |
| control A tolerance forced impossible, current | 1 | 1 |
| lag threshold forced impossible, **committed `ec50e0c`** | **0** | 1 |

The last row is the counterfactual: the shipped-at-`ec50e0c` script prints
`-> lag readout FAIL at L=1` and exits **0**. The gate was decoration, and the
proof is a measurement rather than a reading of the source.

**No number in §18.6 changes.** The lag control passed on its merits, with 52.5×
headroom; what was broken was only the wiring that would have stopped the run had
it not. But an unfired gate is an unverified gate, which is the whole content of
§18.7.

> **A pass/fail gate you have never seen fail is not a gate, it is a print
> statement.** Mutate the threshold until it fails, once, and watch the exit
> code move. Three of this milestone's controls were dead in three different
> ways — two tautological, one disconnected — and all three read `PASS`
> throughout.

The mutants are kept at `C:\dev\strehl-out\M103\ctl\` so the four rows above can
be re-run without reconstructing them.

### 18.8 Candidate facts from the lag sweep

- **P40** (MEASURED) Placement disagreement on `bee-3-cpl` is nearly flat in
  election lag over the band where the statistic is valid: median 0.4829 px at
  `L = 1` rising only to 0.7191 px at `L = 8` (1.49×), against 2.83× for a random
  walk. The jitter is bounded and high-frequency, not accumulating.
- **P41** (DERIVED) The curvature ceiling scales as `f''·L²`, reaching 0.5888 px
  at `L = 8` and 37.68 px at `L = 64`, so a truth-free lag sweep on this stack is
  informative only to `L ≈ 8`. Longer-lag disagreement cannot be separated from
  real breathing without truth data denser than the 39-rung ladder.
- **P42** (MEASURED) Detrending against a fitted truth model is not safe for this
  question: swapping a degree-8 fit for a degree-4 one moves the apparent
  disagreement by up to 0.7675 px at `L = 1` and 7.4709 px at `L = 64`, which is
  the same order as the effect. §18.3's headline avoids this by using no fit.
- **P43** (MEASURED) `jitter.py` at `ec50e0c` computed its lag control after the
  line that decided its exit status, so the control printed `FAIL` and the
  process still exited **0**. Verified by mutation against the committed blob,
  not by inspection. No §18 number changes; the control passed on its merits with
  52.5× headroom. Three of this milestone's controls were dead in three distinct
  ways — two tautological, one disconnected — and all read `PASS` throughout.

### 18.9 Reproducing this section

```powershell
$env:PYTHONIOENCODING='utf-8'
cd experiments\M103-halfdrift
python src\jitter.py data\truth-dense.json `
                     C:\dev\strehl-out\M103\wm-baseline-r149.txt `
                     data\jitter.json
```

Runs in seconds and exits non-zero if any of the three controls fails. The solve
is the shipped `deep()` configuration gauged at reference 149; the gauge is
recorded for provenance only, since §18 is gauge-invariant by construction. The
lag sweep of §18.6 prints its curvature ceiling beside every row so the lag at
which the statistic stops being valid is visible in the output rather than only
in this prose.


