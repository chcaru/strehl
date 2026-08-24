# M86 — Deep-stack alignment: a measured module

Milestone: M86
Owner: M86
Status: complete
Scope: `crates/strehl-core/src/align.rs`, `crates/strehl-cli/examples/m86-align.rs`,
`experiments/M86-alignment/`
Pre-registration: `experiments/M86-alignment/PREREGISTRATION.md` (commit `5205732`,
written and committed **before** any measurement in this milestone)

Every number below is labelled **MEASURED** (I ran it and read the output),
**DERIVED** (arithmetic or logic on measured numbers), or **ARGUED** (reasoning I
believe but did not measure). Numbers taken from other milestones are namespaced
to their milestone. Raw logs for every measurement are in
`experiments/M86-alignment/out/`.

---

## VERDICT

**Deep-stack alignment is NOT solved. It is usable, it is essential, and it is
now implemented and tested in `strehl-core`.**

1. **The defect is real.** **MEASURED**: the shipped pipeline performs no
   geometric registration of any kind. `crates/strehl-cli/src/stack.rs:3`
   documents its own pipeline as `decode -> calibrate -> NO alignment ->
   Tenengrad`, and a search for any transform, warp or similarity across
   `crates/*/src/*.rs` at HEAD returns only comments stating that alignment is
   absent.

2. **The honest-negative branch is refuted, decisively.** My pre-registration
   (§4.2) committed in advance to reporting "breathing is below threshold and
   alignment is not why the images look soft" if total corner drift came in
   under `T_usable` = 4.0 px. **MEASURED**: it does not, on any stack. The
   *smallest* drift in the corpus is **39.7 px** (109MSDCF, only 22 frames), and
   tonight's 299-frame stacks read **232.7 px** (bee-3-cpl) and **299.2 px**
   (bee-2-cpl) of corner motion. Frame 0 is roughly 10–12% smaller than frame
   298. **Alignment is a real and large cause of the softness the project owner
   saw.**

3. **What the module achieves.** **MEASURED** on bee-3-cpl (299 frames): a
   global solve reduces 232.7 px of raw drift to **`E*` = 11.56 px held-out**
   error — a ~20x reduction — against pre-registered thresholds
   `T_solved` = 1.0 px, `T_usable` = 4.0 px, `T_chain` = 12.5 px. That is
   *worse* than `T_usable` and only just better than the chain-it-and-hope
   bar. On shallower or easier stacks it is much better: **0.353 px**
   (109MSDCF), **1.838 px** (foam, 100 frames), **4.761 px**
   (flat-on-ruler-cpl, 79 frames).

4. **The bottleneck is the pairwise estimator, not the solver.** **MEASURED**:
   on bee-3-cpl the raw edge set's own cycle-consistency floor is 9.07 px, and
   the solve lands at 11.56 px. No solver can beat the floor its edges allow.
   **MEASURED** at G0: my solver reproduces M10's published protocol result to
   0.0002 px, so the solving half is not where the error lives.

5. **Cost.** **MEASURED**, 299-frame stack, 32 threads: 6.3 s decode + 48.8 s
   pairwise measurement + <1 s global solve = **~55 s**, at 9.18 GiB peak for
   299 green planes.

6. **A prior result needed integrating, and I did that rather than rebuild it.**
   M10's pairwise estimator existed in Rust only under
   `experiments/m10-deep-align/src/align.rs`; its global solve existed **only in
   Python** (`m10_lib.py`). Neither had ever been in `crates/`. This milestone
   ports both into `strehl-core` and proves the port faithful (G1 is
   **bit-exact** against M10's committed fits).

7. **Two new mechanisms found, both bearing directly on M12's refuted
   shrinkage.** See §6. Short answer: there are **two distinct attenuations**,
   neither of them a transferable scalar, which is why M12's scalar correction
   could not transfer and never could have.

**I have not integrated this into the merge**, per my instructions. §11 is the
recipe for whoever does. The module is committed, declared and live at HEAD.

---

## 1. What I verified at source before building anything

I was told the brief was "a pointer, not evidence". Every load-bearing prior
claim was re-read at its source. What changed as a result:

| Claim I was handed | Source read | Outcome |
|---|---|---|
| M10 reports ~6.76 px held-out | `docs/research/M10-deep-alignment-measured.md` (654 lines) | **Confirmed**, 6.758 px, but the *definition* matters enormously — see below |
| M12 shrinkage was refuted | `docs/research/M12-shrinkage-measured.md` | **Confirmed**, and I can now say *why* (§6.4) |
| Alignment is absent from the merge | `crates/strehl-cli/src/stack.rs`, grep of `crates/` | **Confirmed** |
| Prior work might already be sufficient | `experiments/m10-deep-align/` | **Partly true and load-bearing**: the estimator existed in Rust *outside* `crates/`; the global solve existed only in Python |

**M10's `E*`, verified verbatim at source** (this is the definition I adopted,
and it is not what a one-line summary conveys): error is in **plane pixels at
the worst plane corner**, on the CFA-quad green plane, where 1 plane px = 2
sensor px. The test set is every **direct** edge with `span >= S_min` and at
least `U_min` accepted tiles. Training sets are named subsets disjoint from the
test set by `(i,j)`. `E*` is the **median over the top-span quartile** of
held-out corner errors (`spans >= percentile(spans, 75)`, numpy linear
interpolation), reported for the best **full-coverage, non-tree** strategy row.

I flag one thing the compressed rendering loses: **`E*` is measured against
edges produced by the same estimator being tested.** It is therefore an upper
bound that is itself inflated by the test edges' own error. §6 shows that error
is not small.

---

## 2. What I built

`crates/strehl-core/src/align.rs` — ~2380 lines, 23 unit tests, std-only and
single-threaded (`strehl-core` depends only on `thiserror` + `anyhow`; there is
no rayon there, and keeping the module serial means a "per-pair cost" is a real
per-pair cost). Parallelism lives in the CLI example, which has rayon.

- **Similarity algebra.** `T(p) = a·p + b` on plane coordinates relative to the
  plane centre, `a = (1+g) + i·rot`, `b = ax + i·ay`. Compose, exact invert,
  relative, corner error and its parts. All in `f64`.
- **Pairwise estimator.** Gaussian pyramid, tile grid, NCC with parabolic
  sub-pixel peak refinement, robust similarity fit per stage, coarse-to-fine.
  Returns `Result<_, AlignFailure>` so a refusal is a typed, loud event rather
  than a silent `None`.
- **Global solve.** Edge constraints are linear in the unknowns, so the whole
  bundle is **one complex linear least-squares problem**, gauge-fixed at
  `A_0 = 1, B_0 = 0`. The normal-equation system is **exactly block-diagonal**
  (A-rows touch only A unknowns, B-rows only B), so it splits into two
  independent `(n-1)`-unknown complex systems solved by Hermitian Cholesky with
  two steps of iterative refinement; the blocks couple only through the IRLS
  Huber weights. **DERIVED** from the algebra, **MEASURED** by G0 agreement.
- **Polynomial solve** (`solve_poly`): log-scale as a low-order polynomial in
  frame index, which is the "exploit smoothness" idea from the brief.
- **Diagnostics.** `predict`, `edge_errors`, `cycle_consistency`, `total_drift`,
  `graph_stats`.
- **Resampling.** Bilinear and Catmull-Rom, plus `Resampler::support()` and
  `Resampler::sample_checked()` which returns `None` where the kernel support
  leaves the plane instead of silently clamping.

`crates/strehl-cli/examples/m86-align.rs` — ~1800 lines, subcommands
`solve-csv`, `edges`, `heldout`, `drift`, `compare`, `field`, `plant`. House
style follows `examples/m67-focus-correctness.rs`.

---

## 3. Port fidelity — is this actually M10's algorithm?

Two gates, both pre-registered with a named failing input.

**G0 — global solve vs M10's committed CSV. MEASURED: PASS.**
Running my Rust solver over M10's own `data/coffee-bean-edges.csv` and my
re-implementation of its full 136-row strategy protocol:

| quantity | M10 published | M86 Rust | Δ |
|---|---|---|---|
| `E*` (winner) | 6.758 px | 6.758 px | **0.0002 px** |
| `S3-ba-unit` | 6.997 | 6.997 | exact |
| `S3-ba-invvar` | 24.011 | 24.011 | exact |
| `S1-hops1` | 40.342 | 40.342 | exact |
| winner row | `S4-poly6` on `span >= 32` | same | — |

Whole protocol: **110 ms** for 136 candidate rows. **MEASURED.**

**G1 — pairwise estimator vs M10's committed fits. MEASURED: PASS, bit-exact.**
1601 shared pairs; 100% agreement on fitted-vs-refused (1461 fitted / 140
refused, exactly M10's counts); median, p90 **and max** corner difference
**0.0000 px**.

**The gate is live, not vacuous.** **MEASURED**: the same comparison run against
a deliberately different configuration (`wide64`) reports median 2.911 px and
exits 1. A gate that cannot fail is not a gate.

### Disclosed deviations from M10

1. Transforms in `f64`, not `f32` (**DERIVED** effect ≈ 1.3e-5 px). NCC
   correlation is kept in `f32` with identical summation order — that is why G1
   is bit-exact.
2. Normal equations + Cholesky + refinement, not SVD `lstsq`. My Cholesky
   **refuses** rank-deficient systems. This is deliberate: M10 §8 item 8 found
   `lstsq` silently returning ~1e16 minimum-norm garbage *while reporting full
   coverage*.
3. `cycle_consistency` subsamples by deterministic stride, not numpy PCG64.
4. `align_pair`/`fit_stage` return `Result<_, AlignFailure>`, not `Option`.
5. `strehl-core::plane::green_luma` clamps negatives to zero; M10's
   `green_plane` did not. **MEASURED**: G1 is bit-exact anyway, so on this
   corpus it had no effect.

---

## 4. The headline measurement: how much do these stacks actually move?

**MEASURED.** Total corner drift is the corner displacement between the solved
transforms of the first and last frame, in plane px.

| stack | frames | total drift px | cycle floor px | `E*` px | non-monotonic steps | roughness med px | refusal rate |
|---|---|---|---|---|---|---|---|
| 109MSDCF | 22 | 39.7 | 0.42 | **0.353** | 0/21 | 0.106 | 0.0% |
| flat-on-ruler-cpl | 79 | 108.8 | 3.37 | **4.761** | 0/78 | 0.103 | 0.7% |
| foam | 100 | 224.5 | 1.64 | **1.838** | 0/99 | 0.148 | 23.8% |
| coffee-bean | 105 | — | ~13 (M10's) | **6.758** | — | — | 8.7% |
| bee-2-cpl | 299 | 299.2 | 3.71 | **5.501** | 10/298 | 0.456 | 47.5% |
| bee-3-cpl | 299 | 232.7 | 9.07 | **11.562** | 36/298 | 0.506 | 20.1% |

Two things to read off this table, and one trap.

**It is real breathing, not estimation noise.** **MEASURED**: the recovered
log-scale track is smooth and near-monotonic — median `|d²g|·ρ` = 0.51 px on
bee-3-cpl with 88% of steps monotonic, and flat-on-ruler-cpl and foam are 100%
monotonic. A noisy estimator does not produce a monotone track over 299 frames.

**The trap: `E*` is NOT comparable across stacks with different survivor sets.**
bee-3-cpl is the *cleaner* stack (ISO 100 vs bee-2-cpl's ISO 400) and yet has a
*worse* `E*` (11.56 vs 5.50) and a worse cycle floor (9.07 vs 3.71). **DERIVED**
cause, and it is measured: bee-3-cpl successfully fitted many long-span edges
(46 fits at span 128) where bee-2-cpl fitted **zero** (it decorrelates and has 0
fits at span >= 80). Long-span edges are exactly where inconsistency lives, so
the stack that measures more of them scores worse. **Comparing `E*` between
stacks without comparing their span distributions is meaningless.** I believe
this is a generic hazard for any held-out alignment metric and it is worth
carrying forward.

### Uncertainty

**MEASURED**: bee-2-cpl and bee-3-cpl are the *same subject* at ISO 400 and ISO
100, 299 frames each, and their drift reads **299.2 px vs 232.7 px — a 29%
disagreement on a quantity that ought to be identical.** This echoes M77's fact
1104. I therefore quote **systematic uncertainty on drift magnitude of about
±30%**, and I do not believe any single-stack drift figure to better than that.

---

## 5. Held-out accuracy, and why chaining is not an option

**MEASURED** (bee-3-cpl, my `heldout` subcommand, M10's protocol):

| strategy | held-out `E*` px |
|---|---|
| `S1-hops1` (chain adjacent frames) | 32.9 |
| `S3-ba-unit` (global, unit weights) | 11.56 |
| `S4-poly4/6` (global, polynomial log-scale) | ~11.6 |

**Chaining is catastrophically worse than a global solve** — a factor of ~2.8
here, and M10 measured the same qualitative result on coffee-bean (`S1-hops1`
40.342 vs winner 6.758). §6.4 explains why the gap is *even larger* than simple
error accumulation would predict.

---

## 6. The estimator's actual response — the novel part

This is where the milestone found things the corpus did not already know. All
four probes plant a **known synthetic warp on real frames** and check recovery,
which is the pre-registered "control that can fail".

### 6.1 C1 — interpolator-free field test. MEASURED: PASS.

Rendering a band-limited field directly at the warped coordinates (so no
resampling error is involved at all) and recovering the transform: worst
`|gain - 1|` = **0.0012**, corner error **0.065 px at a 104.9 px plant**.

**MEASURED capture-range limit**: a 192 px plant is **refused** with
`CoarseStageFailed{level: 0}`. This is load-bearing — see §7.

### 6.2 C2 — defocus asymmetry. MEASURED: PASS.

The pre-registered control: plant a scale on frame `j`, estimate against frame
`i` at a controlled defocus gap `|i-j|`, aggregate over 4 base frames × 4 plant
scales. Gain = measured increment / `(1/s - 1)`, using the **exact** inverse.

| defocus gap | n | median gain | MAD | min | max |
|---|---|---|---|---|---|
| 0 | 16 | 0.9997 | 0.0041 | 0.9915 | 1.0059 |
| 1 | 16 | 1.0064 | 0.0034 | 0.9923 | 1.0312 |
| 2 | 16 | 1.0028 | 0.0070 | 0.9712 | 1.0194 |
| 4 | 16 | 1.0049 | 0.0414 | 0.9481 | 1.1031 |
| 8 | 16 | 0.9875 | 0.0836 | 0.4583 | 1.1100 |
| 16 | 15 | 1.0264 | 0.1184 | 0.2260 | 2.3312 |
| 32 | 13 | 0.8904 | 0.4970 | -0.9366 | 1.9502 |

Gate C2 (gap 0): worst `|gain - 1|` = **0.0085** against the registered bar of
0.02. **PASS.**

**The result: for a displacement in the estimator's working range, defocus
asymmetry inflates VARIANCE, not measurably BIAS.** The median stays within 3%
of unity out to gap 16 while the MAD grows 30-fold, 0.004 → 0.118. **Honest
caveat**: n = 16 with only 4 independent base frames, so the median's standard
error is roughly MAD/sqrt(4) ≈ 0.06 at gap 16. I can say the multiplicative
bias is **bounded below ~6% at gap 16**; I cannot say it is zero.

### 6.3 The peak-locking knee — MEASURED, and new

C2 above plants *large* scales (4–21 px of corner motion). I then asked what
happens at the displacement sizes real adjacent frames actually present. Same
probe, **zero defocus gap** (so nothing but the synthetic warp differs), sweeping
plant size:

| plant `s-1` | corner motion px | n | median gain | MAD |
|---|---|---|---|---|
| 2.00e-5 | 0.042 | 4 | **0.2945** | 0.034 |
| 5.00e-5 | 0.106 | 4 | **0.3011** | 0.026 |
| 1.00e-4 | 0.211 | 4 | **0.3135** | 0.016 |
| 2.00e-4 | 0.422 | 4 | **0.3955** | 0.017 |
| 5.00e-4 | 1.056 | 4 | 1.0107 | 0.003 |
| 1.00e-3 | 2.111 | 4 | 1.0146 | 0.005 |
| 2.00e-3 | 4.217 | 4 | 0.9922 | 0.0005 |
| 5.00e-3 | 10.512 | 4 | 1.0039 | 0.0004 |
| 1.00e-2 | 20.919 | 4 | 0.9989 | 0.0002 |

**MEASURED: below ~0.4 px of corner motion the estimator recovers only ~30% of
the true scale; above ~1 px it is unity to within 1.5%. The knee is sharp,
between 0.42 px and 1.06 px.** The MAD is tiny (0.0002–0.034) and four
independent base frames agree, so this is a **reproducible systematic
attenuation, not noise** — and it occurs with **no defocus difference at all**.
This is classic correlation peak-locking: parabolic sub-pixel refinement biases
small displacements toward zero.

I did not find this documented anywhere in the corpus. It is a property of the
estimator alone, independent of scene and of defocus.

### 6.4 Span bias on real pairs — and the resolution of M12

**MEASURED** (`span_bias.py` on bee-3-cpl's 3587 edges): the per-frame
log-scale rate implied by *direct* pairwise fits is strongly span-dependent.

| span | implied rate /frame | implied total corner px |
|---|---|---|
| 1 | -5.914e-05 | -37.2 |
| 4 | -1.404e-04 | -88.4 |
| 16 | -4.083e-04 | -257.1 |
| 32 | -4.414e-04 | **-277.9** (peak) |
| 64 | -3.301e-04 | -207.8 |
| 128 | -1.222e-04 | -77.0 |

**Span-1 pairs read the breathing rate 7.5x too low.** This *is* M12's shrinkage,
live and quantified on a 299-frame stack.

Now combine with §6.3, and note carefully that **peak-locking does not explain
it**. **DERIVED**: if the plateau rate 4.41e-4/frame is the truth, a span-1 pair
carries 0.93 px of true corner motion — a size at which §6.3 measures the
estimator's gain as ~1.0, not 0.13. So:

> **DERIVED, and I regard this as the milestone's most useful inference:** there
> are **two separate attenuations**. One is peak-locking, which is a property of
> the correlator and bites below ~0.4 px. The other bites on *real* short-span
> pairs at ~0.9 px, where the correlator is provably accurate on a synthetic
> plant of the same size — so **that one is caused by the defocus difference
> between the frames**, not by the correlator's sub-pixel behaviour.

This is why M12 failed and why it was always going to. A scalar shrinkage
correction fitted on one scene bakes in that scene's particular mix of
displacement magnitudes, span distribution and defocus step. Change the scene
and every one of those changes. **The attenuation is not a constant of the
instrument, so no scalar can transfer it.** That is a stronger statement than
"it didn't transfer", and it is supported by two independent measurements.

**Which end of the span range should be believed?** The long end, and this is
measured rather than assumed: §6.3 proves the estimator is accurate to **0.4% at
10–21 px** of corner motion. A span-32 edge carries ~14 px — squarely inside the
proven-accurate regime. A span-1 edge carries ~0.9 px and is confounded. The
short edges also cannot reproduce the long ones: **DERIVED**, chaining 32
span-1 edges gives 1.9e-3 of log-scale where a single direct span-32 edge gives
1.4e-2, a 7x internal inconsistency in the edge set. That inconsistency, not
mere error accumulation, is why `S1-hops1` is so bad (§5).

**Consequence for the global solve. MEASURED/DERIVED**: unit-weighted global
solve gives 232.7 px, while the least-biased span band (16–48) implies
**258–278 px**. The global solve is being dragged ~12–16% low by short-span
edges. §11 turns this into a concrete recommendation.

### 6.5 C3 — the control that must fail. MEASURED: PASS.

Pre-registered requirement: plant a known regression and confirm the gate
catches it. I changed `AlignConfig::deep()`'s `margin` from 96 to 64, rebuilt,
and re-ran G1: median corner difference **0.9157 px, FAIL, exit 1**. Restored
from a **backup copy** (never `git checkout --`, per this project's history),
verified byte-identical by SHA256 (`EEA5260E…0DDEA`), `git status` clean, reset
`LastWriteTime`, rebuilt, re-ran G1: **PASS, exit 0**.

**A finding worth carrying: more tiles is not better.** **MEASURED**: the
margin 96→64 plant *increased* fitted pairs from 1461 to 1512 while making the
fits 0.92 px worse. More accepted tiles with worse fits is a false-confidence
signature, and it is the same pattern M10 found with `wide64`.

---

## 7. Failure modes — where this breaks

Reported because the brief asked for them, not because they are comfortable.

1. **Frame 0 and frame 298 cannot be registered directly, at all.**
   **MEASURED**: capture range fails at a 192 px plant (§6.1) and these stacks
   drift 232–299 px. Any deep-stack alignment **must** route through the edge
   graph; a direct first-to-last fit is outside the estimator's reach. This is
   not a tuning issue, it is a structural constraint on the design.
2. **Refusal rate rises steeply with span and with ISO.** **MEASURED**:
   bee-2-cpl (ISO 400) refuses **47.5%** of pairs and produces **zero** fits at
   span >= 80, versus bee-3-cpl (ISO 100, same subject) at 20.1%. Noise
   decorrelates long spans first. On a noisy stack the long edges that carry the
   scale signal are precisely the ones you lose.
3. **`E*` is not portable between stacks** (§4). It depends on which edges
   survived.
4. **`E*` is an upper bound of unknown tightness**, because the held-out edges
   are themselves products of the biased estimator (§1, §6.4).
5. **Real subject motion is silently absorbed.** foam is documented in this
   corpus as a stack that moved. **MEASURED**: foam breathes ~3x faster per
   frame than bee (7.1% over 80 frames vs 2.2%), is 100% monotonic, and returns
   the *best* deep `E*` in the corpus at 1.838 px — while its **maximum**
   held-out error is 86.2 px. **ARGUED**, and I think it is important:
   **axial subject motion is geometrically indistinguishable from focus
   breathing**, and lateral motion is absorbed into the translation term. A
   similarity aligner therefore *does* silently "correct" real subject motion.
   For stacking that is desirable. But it means **the recovered scale track must
   not be read as a measurement of the lens's breathing** — which is directly
   relevant to M84's ruler metrology, and I flag it to them rather than acting
   on it.
6. **Plane geometry is not constant across the corpus.** **MEASURED**: most
   stacks are 3516×2344 (ρ = 2112.85) but `flat-on-ruler-cpl` is **3520×2344**
   (ρ = 2114.5). Take it from the decoder's `active` region; never hard-code.
   (Rule 7, vindicated the hard way.)

---

## 8. Cost

**MEASURED**, bee-3-cpl, 299 frames, 32 threads:

| phase | cost |
|---|---|
| decode | 21–33 ms/frame wall → **6.3 s** |
| pairwise measurement | 13.6 ms/pair wall (≈435 ms/pair core-time) × 3587 pairs → **48.8 s** |
| global solve | 0.1–0.6 s |
| **total** | **~55 s** |
| peak memory | 9.18 GiB (299 green planes) |

A note that corrects a possible misreading of M10: my measured 13.6 ms/pair is
*exactly* M10's published figure, and my core-time measurement shows that number
is **throughput on 32 threads, not single-core cost**. Anyone budgeting from
M10's figure on fewer cores will be wrong by ~32x.

---

## 9. Resampling

`align.rs` provides bilinear and Catmull-Rom. **MEASURED** (unit test
`bilinear_costs_more_high_frequency_than_catmull_rom`): bilinear destroys
measurably more high-frequency energy than Catmull-Rom on a synthetic
band-limited field.

**NOT MEASURED**: I did not run a retained-HF-energy comparison on real frames.
The pre-registration §9 called for this and I did not get to it. **Do not treat
the interpolator choice as measured on real data.** Recommendation on the
strength of the unit test and standard practice only (**ARGUED**): Catmull-Rom.

The one resampling fact I *do* consider settled (**MEASURED**, by C1): running
the estimator on a directly-rendered band-limited field gives 0.065 px corner
error at a 104.9 px plant, so **the estimator itself is not resampler-limited**
at these magnitudes.

---

## 10. Candidate facts

Offered for SYNTHESIS.md, which I do not edit.

| # | fact | label |
|---|---|---|
| P1 | The shipped merge performs no geometric registration; `stack.rs` documents this itself. | MEASURED |
| P2 | 299-frame macro brackets drift 232.7–299.2 px at the plane corner; the corpus minimum is 39.7 px on a 22-frame stack. Alignment is a real cause of softness. | MEASURED |
| P3 | M10's pairwise estimator ports to `strehl-core` bit-exactly (1601 pairs, max corner difference 0.0000 px); its global solve reproduces `E*` = 6.758 px to 0.0002 px. | MEASURED |
| P4 | The alignment estimator attenuates planted scale to ~30% below 0.4 px corner motion and is unity above ~1 px, with zero defocus difference. Peak-locking knee at 0.42–1.06 px. | MEASURED |
| P5 | At displacements above ~4 px, defocus gap up to 16 frames inflates estimator variance 30-fold (MAD 0.004→0.118) with multiplicative bias bounded below ~6%. | MEASURED |
| P6 | Direct pairwise fits imply a breathing rate that varies 7.5x with span, peaking at span 16–48; span-1 pairs read 7.5x low. | MEASURED |
| P7 | Short-span attenuation on real pairs is NOT peak-locking — a synthetic plant of the same magnitude is recovered correctly — so it is caused by the defocus difference. This is why M12's scalar shrinkage correction could not transfer. | DERIVED |
| P8 | Unit-weighted global solve underestimates drift by 12–16% versus the least-biased span band (232.7 px vs 258–278 px). | DERIVED |
| P9 | Held-out `E*` is not comparable across stacks with different edge-survivor sets; a cleaner stack can score worse by fitting more long-span edges. | MEASURED |
| P10 | Global solve beats chaining by ~2.8x on a 299-frame stack (11.56 vs 32.9 px) because the edge set is internally inconsistent by 7x at short span. | MEASURED |
| P11 | The pairwise estimator's capture range fails at a 192 px plant, so first-to-last registration of a deep bracket is impossible directly and must route through the edge graph. | MEASURED |
| P12 | Same subject at ISO 100 vs ISO 400 yields 29% disagreement in measured drift; systematic uncertainty on drift is ~±30%. | MEASURED |
| P13 | Refusal rate is 47.5% at ISO 400 vs 20.1% at ISO 100 on the same subject, with zero fits beyond span 80 at ISO 400. | MEASURED |
| P14 | Reducing the tile margin increased accepted pairs 1461→1512 while worsening fits by 0.92 px — more tiles is a false-confidence signal. | MEASURED |
| P15 | Axial subject motion is geometrically indistinguishable from focus breathing; a similarity aligner silently corrects it, so a recovered scale track is not a measurement of lens breathing. | ARGUED |
| P16 | Plane geometry varies across the corpus: `flat-on-ruler-cpl` is 3520×2344 where most stacks are 3516×2344. | MEASURED |
| P17 | Alignment costs ~55 s for a 299-frame stack on 32 threads (6.3 s decode, 48.8 s measure, <1 s solve) at 9.18 GiB. M10's 13.6 ms/pair is 32-thread throughput, not single-core cost. | MEASURED |

---

## 11. Integration recipe

For whoever wires this into the merge. **M85 owns `merge_cmd.rs`; I did not
touch it.** `align.rs` is committed and green, and is currently inert to cargo
because its `pub mod align;` declaration is not yet committed (§12).

1. **The module is already declared.** `pub mod align;` is committed in
   `crates/strehl-core/src/lib.rs` (landed via M85's `e59f1b0`, which carried my
   line alongside its own). Nothing to do — `strehl_core::align` is live.
2. **Solve globally. Never chain.** Use `solve_global` with
   `Weighting::Unit`, or `solve_poly` with degree 4–6. **MEASURED**: chaining
   costs 2.8x (§5).
3. **Prefer edges in the span 16–48 plateau.** **DERIVED** from §6.4: short-span
   edges are attenuated ~7.5x and drag the solve 12–16% low. Build the edge set
   from that band plus enough shorter edges to keep the graph connected, or
   down-weight by span. This is the single highest-value change available and it
   is not what M10 did.
4. **Do not attempt direct first-to-last registration.** **MEASURED** (§6.1,
   §7.1): it is outside capture range on every 299-frame stack here.
5. **Use `Resampler::sample_checked`, not `sample`.** `sample` clamps at the
   border, which silently fabricates edge data; `sample_checked` returns `None`
   where the kernel support leaves the plane so the caller can drop the sample.
   **MEASURED**: my identity-gather unit test asserts the interior is exact
   *and* that the clamped border is not the identity — the clamping is real.
6. **Gather at consumption; never materialise warped frames** (rule 2).
   `gather_into` is the entry point. Note the sign convention, which cost me two
   failed runs: `gather_into(p, t, ...)` fills output pixel `q` from source
   `t(q)`, so **the warped frame is the source warped by `t⁻¹`**. Likewise
   `BandLimited::render(geom, t)` samples at `t(p)`. Use the **exact** inverse,
   not the linearisation: at `s = 1.02` the difference between `-(s-1)` and
   `1/s - 1` is **0.83 plane px**, larger than many of the effects here.
7. **Set `margin` ≈ measured drift + 16**, and do **not** reduce it to gain
   tiles (§6.5).
8. **Expect ~11.6 px residual on a 299-frame stack, not sub-pixel.** Budget for
   it. If the merge needs sub-pixel registration, the pairwise estimator must
   improve first (§4.4) — M23's metacalibration and M78's blur-equalised edges
   are the obvious next attacks, and §6.4 now gives them a sharper target: the
   defocus-induced attenuation at ~1 px displacement.

---

## 12. What I did not do, and one blocked step

- **I did not integrate into the merge**, per instruction.
- **The module is committed and declared.** `align.rs` landed as `938c0d1`.
  Its `pub mod align;` declaration sat uncommitted in my working tree for most
  of the milestone, because that file's diff also carried **another agent's**
  in-flight `pub mod color;` / `pub mod demosaic;` lines and committing it would
  have committed their work-in-progress. I left it alone and re-checked at
  commit time, as instructed: **M85 has since committed `lib.rs` with all three
  lines**, so `strehl_core::align` is live at HEAD with no action outstanding.
  Recording the near-miss because the resolution was luck, not design: had M85
  landed first and I second, one of us would have clobbered the other.
- **I did not check the flat-on-ruler physical invariant.** The brief correctly
  identifies straight lines staying straight and graduations staying evenly
  spaced as a strong checkable invariant, and I agree it is the best available
  independent arbiter of §6.4's "which span should be believed". It needs
  ruling-line detection which I did not have time to build. flat-on-ruler-cpl's
  *alignment statistics* are measured (§4); its *physical* invariant is not.
  **This is the highest-value follow-up.**
- **I did not run the resampler comparison on real frames** (§9).
- **I did not write to `experiments/M84-ruler-metrology/`** and did not
  duplicate M84's work. §7.5 is a finding they should have.
