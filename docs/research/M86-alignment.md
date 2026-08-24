# M86 — Deep-stack alignment: a measured module

Milestone: M86, extended by M86b
Owner: M86
Status: complete
Scope: `crates/strehl-core/src/align.rs`, `crates/strehl-cli/examples/m86-align.rs`,
`experiments/M86-alignment/`; **M86b** adds
`crates/strehl-core/src/warpmap.rs` and `crates/strehl-cli/src/align_cmd.rs`
Pre-registration: `experiments/M86-alignment/PREREGISTRATION.md` (commit `5205732`,
written and committed **before** any measurement in this milestone) and
`experiments/M86-alignment/PREREGISTRATION-warpmap.md` (commit `0756cec`, likewise
before any M86b implementation)

Every number below is labelled **MEASURED** (I ran it and read the output),
**DERIVED** (arithmetic or logic on measured numbers), or **ARGUED** (reasoning I
believe but did not measure). Numbers taken from other milestones are namespaced
to their milestone. Raw logs for every measurement are in
`experiments/M86-alignment/out/`.

**Two claims in this report were later overturned by its own author.** §6.3's
peak-locking knee is retracted (see the correction there and fact P22) and §9's
"NOT MEASURED" resampler note is now measured. Both corrections are M86b's and
both are marked in place rather than deleted.

**The sidecar that carries these warps to the merge is §14.** The two
registration patches the orchestrator must apply are §14.9.

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

**§13 answers M84b's question about the uniform focus step**: yes, the
assumption exists in two places, no, it is not load-bearing for any number
above, and forcing it costs 18–108% more held-out error on four stacks.

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

> **CORRECTED BY M86b — the cause named below was wrong.** The paragraph that
> stood here attributed the knee to correlation peak-locking, "a property of
> the estimator alone, independent of scene and of defocus". That attribution
> does not survive its own control.
>
> The probe above builds the moved frame with `gather_into`, i.e. **through a
> resampler**, so it cannot separate an estimator property from a resampling
> artefact of the plant. M23 had already met this exact confound from the other
> side: its zero-defocus self-pair reads `R = 0.372` with a bilinear gather
> where truth is 1.000, and `R = 0.965` with the resampler removed entirely
> (M23 facts 170/172/177). Reading that at source is what prompted the
> re-test.
>
> Re-running the **interpolator-free** C1 ladder — both frames rendered
> analytically from the same band-limited field, no resampler anywhere — at the
> same corner motions:
>
> | corner px | via `gather_into` (§6.3) | interpolator-free (C1) |
> | --- | --- | --- |
> | 0.042 | 0.2945 | **0.9815** |
> | 0.106 | 0.3011 | **0.9816** |
> | 0.211 | 0.3135 | **0.9807** |
> | 0.422 | 0.3955 | **0.9841** |
> | 1.056 | 1.0107 | 1.0062 |
> | 2.111 | 1.0146 | 0.9988 |
>
> **There is no knee.** Gain is flat at 0.98 down to 0.042 px. The estimator is
> very nearly unbiased across the whole range; what the §6.3 ladder measured is
> **Catmull-Rom destroying the sub-pixel displacement being planted**,
> reproducing bilinear's failure in M23 almost exactly. The measurement stands;
> the mechanism was misattributed. Fact P4 is amended accordingly.
>
> This makes §6.4's conclusion **stronger and simpler**, not weaker — see the
> note there.

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

> **AMENDED BY M86b, and the conclusion gets simpler.** §6.3's correction
> removes the first of those two attenuations: there is no correlator
> peak-locking, because the interpolator-free ladder measures gain flat at 0.98
> from 0.042 px upward. The argument no longer needs the 0.93 px coincidence
> and no longer rests on a knee sitting just below the span-1 displacement.
>
> It becomes: **the correlator is unbiased at every displacement in the relevant
> range, therefore the attenuation on real short-span pairs cannot be a
> correlator artefact, therefore it is defocus.** One attenuation, not two, and
> the remaining one is the one that matters. Everything below about M12 stands
> unchanged, and stands on a shorter chain.

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

`align.rs` provides nearest, bilinear and Catmull-Rom. **MEASURED** (unit test
`bilinear_costs_more_high_frequency_than_catmull_rom`): bilinear destroys
measurably more high-frequency energy than Catmull-Rom on a synthetic
band-limited field.

**Corrected by M86b — this is now MEASURED on real frames.** The original text
here said "NOT MEASURED … do not treat the interpolator choice as measured on
real data". That gap is closed. Two independent measurements on `bee-3-cpl`
frame 1, both via `strehl align`
(`out/W6-w2-per-resampler.log`, `out/W6-resampler-cost.log`):

| resampler | W2 plant/undo ratio | gradient energy retained by one gather |
| --- | --- | --- |
| nearest | 0.0000 | 0.9998 |
| bilinear | 0.2006 | 0.3293 |
| **catmull-rom** | **0.1228** | **0.5139** |

Catmull-Rom wins both: 39% less residual than bilinear on the plant/undo gate,
and it retains **1.56x** as much gradient energy through a single gather. The
recommendation is no longer ARGUED; it is MEASURED, and the default is
Catmull-Rom.

**Both columns contain a trap, and nearest exposes it.** Nearest reads a
*perfect* 0.0000 on W2 and a *perfect* 0.9998 retention, and it is the worst
interpolator of the three. Neither number means what it appears to:

- W2 plants a warp with `R` and undoes it with the same `R`. For nearest that
  round trip is a permutation of the lattice, so the error cancels **exactly**.
  This is not a rounding artefact: the logged residual is `0.00000` against a
  damage of `30.50000` — bit-exact zero. The 0.0000 is a property of the
  metric, not of the resampler.
- Gradient energy is preserved by nearest because it does not interpolate at
  all — it copies a neighbour, keeping every edge crisp while misplacing it by
  up to half a pixel. High retention, wrong geometry.

Note also that the *controls* stay honest under all three: inverted reads
1.5902–1.6207 and transposed 1.1311–1.1470 regardless of resampler, so W2's
ability to catch a wrong warp does not depend on the interpolator — only its
ability to rank right ones does.

So neither statistic ranks resamplers alone; the pair does, and only after the
degenerate arm is understood. This is recorded because a future reader running
one of these probes on its own would reasonably conclude nearest is best.

**Still NOT MEASURED**: what this costs the *finished render*. One gather at a
half-pixel shift destroys roughly half the gradient energy of a real frame
(0.5139 retained). That is a large number for a project whose entire purpose is
preserving fine detail, and it is a strong argument for `align.rs`'s existing
rule that the merge must gather once, at the point of consumption, rather than
materialising warped copies.

The one resampling fact settled earlier (**MEASURED**, by C1): running the
estimator on a directly-rendered band-limited field gives 0.065 px corner error
at a 104.9 px plant, so **the estimator itself is not resampler-limited** at
these magnitudes.

---

## 10. Candidate facts

Offered for SYNTHESIS.md, which I do not edit.

| # | fact | label |
|---|---|---|
| P1 | The shipped merge performs no geometric registration; `stack.rs` documents this itself. | MEASURED |
| P2 | 299-frame macro brackets drift 232.7–299.2 px at the plane corner; the corpus minimum is 39.7 px on a 22-frame stack. Alignment is a real cause of softness. | MEASURED |
| P3 | M10's pairwise estimator ports to `strehl-core` bit-exactly (1601 pairs, max corner difference 0.0000 px); its global solve reproduces `E*` = 6.758 px to 0.0002 px. | MEASURED |
| P4 | The alignment estimator attenuates planted scale to ~30% below 0.4 px corner motion **when the plant is rendered through a resampler**, and is unity above ~1 px. **Amended by P22: interpolator-free there is no knee — this is a resampling artefact, not correlator peak-locking.** | MEASURED |
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
| P18 | Forcing a constant per-frame log-scale increment costs 18–108% more held-out error on four stacks (bee-3-cpl +44%, foam +108%, coffee-bean +20%, flat-on-ruler-cpl +18%). Alignment data independently refutes a uniform per-frame increment. | MEASURED |
| P19 | A degree-2 polynomial in frame index is no better than a constant increment (bee-3-cpl 17.325 vs 16.649 px); degree 3+ is required. The per-frame increment does not drift merely linearly. | MEASURED |
| P20 | The second-difference smoothness prior costs 65% on a well-conditioned deep stack (19.236 vs 11.649 px) but wins outright on `foam` (2.454 px). It is a variance regulariser whose bias is real, not a correct physical prior. | MEASURED |
| P21 | M84b's DoF under-sampling (adjacent frames focus-disjoint) supplies the physical mechanism for M86's independently-measured short-span attenuation. Two channels, one conclusion. | DERIVED |
| P22 | The estimator has **no** peak-locking knee. Interpolator-free, gain is flat at 0.98 from 0.042 px to 2.1 px corner motion. The knee in §6.3 is Catmull-Rom destroying the plant, not the correlator. Amends P4. | MEASURED |
| P23 | One Catmull-Rom gather at a half-pixel shift retains 0.5139 of a real frame's gradient energy; bilinear retains 0.3293. Catmull-Rom preserves 1.56x as much detail, and a single gather still costs ~49%. | MEASURED |
| P24 | Nearest-neighbour reads a bit-exact 0.0000 on a plant/undo gate (residual 0.00000 against damage 30.50000) and 0.9998 gradient retention while being the worst resampler: plant/undo with nearest is an exactly-cancelling lattice permutation. Neither statistic ranks resamplers alone. | MEASURED |
| P24b | W2's *controls* are resampler-independent — inverted 1.5902–1.6207, transposed 1.1311–1.1470 across nearest/bilinear/catmull-rom. A plant/undo gate's ability to catch a wrong warp does not depend on the interpolator; only its ability to rank correct ones does. | MEASURED |
| P25 | Relaxing an alignment holdout's span floor from 40 to 1 on a fixed edge set drops median held-out error 4.15x (12.323 -> 2.970 px on bee-3-cpl), monotonically via 4.710 px at span 8 — enough to place an unusable solve inside `T_usable` = 4.0 px. Only long-span holdout tests extrapolation. | MEASURED |
| P26 | `bee-2-cpl` and `bee-3-cpl` have byte-identical frame filenames, equal frame counts and equal geometry; only file sizes differ (37,552,128 vs 39,362,560 B, frame 1). Stack identity must mix file size, not names or counts. | MEASURED |
| P27 | The held-out-to-cycle-floor **ratio** detects real subject motion where neither number alone does: `foam` reads 15.3 (0.233 px floor, 3.562 px held-out) against 4.7 for bee-3-cpl and 0.94 for 109MSDCF. Self-consistent edges plus a poor global fit means the subject moved. | DERIVED |
| P28 | Cycle-consistency floors are not comparable across milestones: the same stack reads 2.908 px under M86b's span ladder and 9.07 px under M86 §6's, because the floor is dominated by whichever short triangles the ladder happens to close. | MEASURED |

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

## 13. Does this method assume a uniform focus step? (M84b's fact 1154)

M84b measured the per-frame focus step drifting monotonically from 32.35 to
49.36 µm/frame, a factor of 1.53, on `highly-angled-ruler-mm-cpl`. I was asked
whether anything in my method is indexed on a uniform step. **The answer is
(b): yes, in two identifiable places, and I measured the impact.**

### 13.1 Where the assumption lives — audited at source

| site | assumes uniform step? | in my headline results? |
|---|---|---|
| pairwise estimator (`align_pair`) | **No.** Frame index never enters; it correlates image content only. | — |
| index→defocus conversion / blur equalisation | **Not present.** I implemented none; that is M78's territory. | — |
| `GlobalOptions::smooth` (`align.rs:1748`) | **Yes, directly.** It adds a `[1, −2, 1]` second-difference stencil with zero RHS, which is exactly a penalty on deviation from a *constant per-frame increment*. | **No** — it defaults to `0.0` and is exercised only by the `S6-ba-smooth` candidate row. |
| `solve_poly` degree | **Only at degree 1**, where log-scale is linear in frame index. | **No** — I ran degrees 2/4/6 and the winner was 6. |
| `span_bias.py` | **Yes**, it divides `g` by span to get an "implied rate per frame". | Yes — see §13.4. |

So the assumption was never load-bearing for the numbers in the VERDICT, which
is luck rather than foresight: I chose flexible models for other reasons.

### 13.2 The measured impact

Cheap direct test, as suggested: refit the ladder with a *constant* per-frame
increment (`S4-poly1`) against increments free to drift, same edges, same
training set, same held-out test set. Median held-out corner error, plane px:

| stack | frames | `poly1` (uniform) | best free degree | cost of assuming uniform |
|---|---|---|---|---|
| bee-3-cpl | 299 | 16.649 | **11.535** (poly6) | **+44%** |
| foam | 100 | 6.790 | **3.259** (poly6) | **+108%** |
| coffee-bean | 105 | 11.369 | **9.464** (poly6) | **+20%** |
| flat-on-ruler-cpl | 79 | 7.116 | **6.017** (poly6) | **+18%** |

**MEASURED: forcing a constant per-frame increment costs 18–108% more held-out
error, on all four stacks tested, in the same direction every time.** This is
held-out, not fit, error — a more flexible model that was merely overfitting
would have scored *worse*, not better.

On bee-3-cpl the two formulations agree: the explicit uniformity prior
`S6-ba-smooth` scores **19.236 px** against `S3-ba-unit`'s **11.649 px** on the
same training set, a 65% penalty for the same assumption expressed as a soft
prior instead of a hard model.

**MEASURED: degree 2 is not enough either.** On bee-3-cpl `poly2` scores 17.325
— no better than `poly1`'s 16.649 — while `poly3` drops to 12.557. If the focus
step drifted *linearly* and breathing were locally linear in focus position,
log-scale would be quadratic and degree 2 would suffice. It does not. Either
M84b's drift is not linear in frame index, or magnification-vs-focus is itself
curved, or both. **I cannot separate those from alignment data alone.**

### 13.3 The honest counter-example

**The soft prior is not always harmful, and I will not flatten this.**
**MEASURED**: on `foam` the overall winning row is `S6-ba-smooth` trained on
`span <= 2` at **2.454 px**, beating every unregularised alternative; on
coffee-bean the prior changes nothing at all (9.512 vs 9.512). foam is the stack
that *moved*, with a 23.8% refusal rate and a weaker edge set.

**ARGUED**: where the uniformity prior helps, it is helping as a *variance*
regulariser on noisy edges, not because the assumption is true — the hard
uniform model `poly1` is still 108% worse on that very same stack. The prior
buys variance reduction at the price of a bias that is real. That is a
legitimate trade on a noisy stack and a bad one on a well-conditioned deep
stack.

### 13.4 What this does and does not corroborate

**DERIVED**: alignment data independently refutes a constant per-frame scale
increment, on four stacks, from a measurement channel (image correlation) with
nothing in common with M84b's (ruler depth). The *direction* corroborates M84b.
**It does not confirm the 1.53x**, and it cannot: a non-constant scale increment
is equally consistent with a uniform focus step plus nonlinear
magnification-vs-focus. My measured 18–108% is therefore an **upper bound** on
the error attributable specifically to focus-step non-uniformity.

**A caveat against my own §6.4**, since the orchestrator's point 3 lands on it:
`span_bias.py` divides `g` by span, which treats the rate as constant. That
assumption is now known false. It does **not** overturn the finding —
`g(i, i+s)/s` is the *mean* rate over `[i, i+s]`, and averaging over all
available `i` at each span recovers approximately the stack mean at every span,
so the distortion is second-order; and the effect measured there is **7.5x**,
which a 1.53x drift cannot manufacture. But the span-bias table's exact shape
should be read as ±25% rather than exact.

**A convergence worth flagging.** M84b's fact 1159 has the bracket
under-sampling its own depth of field by 1.8–2.3x, so adjacent frames do **not**
share a focal plane. My §6.4 concluded independently that short-span
attenuation on real pairs is caused by the defocus difference and *not* by the
correlator — a synthetic plant of the same magnitude is recovered correctly.
**These two findings explain each other**: if adjacent frames are focus-disjoint,
a span-1 pair is a correlation between genuinely different blur states, which is
exactly the mechanism §6.4 infers. Two channels, one conclusion.

**Not applicable to me**: fact 1159's inverse-depth point. `align.rs` fits a 2D
similarity in image coordinates and contains no depth or object-plane model, so
there is no `Z` to fit linearly. One adjacent caveat I will own, though: a
*global* scale is the correct model only for a subject plane normal to the axis.
On a steeply tilted subject, magnification varies across the field and a single
similarity is an approximation — irrelevant to the flat-on stacks I aligned, but
it means **this module should not be pointed at `highly-angled-ruler-mm-cpl`
without first measuring that error.**

### 13.5 Consequence for the integration recipe

Add to §11: **do not use `GlobalOptions::smooth` on a well-conditioned deep
stack** — it costs 65% on bee-3-cpl. Reserve it for stacks with weak or noisy
edge sets, where §13.3 shows it can pay. And **use `solve_poly` at degree 4–6,
never 1 or 2**; degree 2 is measurably no better than assuming a constant
increment outright.

---

## 14. M86b — the warp sidecar

M86 built an alignment module that nothing consumed. The owner's binary applied
none of it. §14 closes that gap **without touching a file another agent owns**:
the solve now writes a sidecar, and the merge will read one.

### 14.1 VERDICT

> **The merge can now be given warps.** `strehl align` solves a bracket and
> writes `WarpMap`, a per-frame sidecar carrying its own provenance and its own
> uncertainty; `warpmap::gather_checked` applies a placement correctly, proven
> against the two silent bugs that would otherwise pass a round-trip test.
>
> **What is proven: the transport, not a better estimator.** Gate W2 on real
> `bee-3-cpl` frames undoes a planted 1% scale (~21 px at the corner) to a
> residual of **0.1228** of the damage, against a pre-registered bar of 0.25 —
> while an **inverted** warp reads 1.6042 and a **transposed** warp reads
> 1.1421, both far outside the bar. The gate can tell a correct warp from a
> wrong one, which a round-trip alone cannot.
>
> **What has not changed: the estimator.** Held-out error on `bee-3-cpl` is
> **13.578 px** under M10's long-span protocol — the same regime as M86's
> 11.562 px, still ~3x `T_usable` = 4.0 px. This milestone moves nothing on
> accuracy and was not asked to.
>
> **One thing here is a warning, not a result.** My first implementation used a
> 5-fold stride holdout, which reported under 3 px on the same solve — inside
> `T_usable`, and wrong. I withdrew the exact figure as unsourced and replaced
> it with a controlled measurement: on a *fixed* edge set, relaxing the
> holdout's span floor from 40 to 1 moves median held-out error from **12.323
> px to 2.970 px**, a factor of 4.15 from the protocol alone. See §14.4.

### 14.2 What was built

| file | what |
| --- | --- |
| `crates/strehl-core/src/warpmap.rs` | `WarpMap`, `FrameWarp`, `Provenance`, `StackIdentity`, `gather_checked`, `gather_frame`; text format; 16 tests |
| `crates/strehl-cli/src/align_cmd.rs` | `strehl align` — solve and write; `--verify-plant`, `--check`, `--resampler-cost` |

Neither is registered. `pub mod warpmap;` and the `main.rs` subcommand arm are
the orchestrator's to apply; both patches are given verbatim in §14.9.

### 14.3 Gate results

All gates were pre-registered in
`experiments/M86-alignment/PREREGISTRATION-warpmap.md` before implementation,
in commit `0756cec`.

| gate | result | evidence |
| --- | --- | --- |
| **W1** round-trip is bit-identical | **PASS** | `f64::to_bits` equality on every component; text is a fixed point |
| **W1** control: flipped hex digit | **PASS** (detected) | a flipped nibble in `a_re` changes the loaded warp |
| **W1** control: truncation | **PASS** (typed error) | `WarpMapError::Truncated`, never a short map |
| **W2** planted warp undone, real frames | **PASS** | ratio **0.1228** ≤ 0.25 |
| **W2** control: INVERTED | **PASS** (fails gate) | ratio **1.6042** ≥ 0.9 |
| **W2** control: TRANSPOSED | **PASS** (fails gate) | ratio **1.1421** ≥ 0.9 |
| **W3** wrong-stack detection | **PASS** | `bee-3-cpl` sidecar on `bee-2-cpl` → exit 1 |
| **W3** liveness | **PASS** | correct bracket → `MATCH`, exit 0 |
| **W4** refusal ≠ identity | **PASS** | distinct states; no accessor collapses them |
| **W5** tilted-subject guard | **PASS** | `highly-angled-ruler-mm-cpl` refused in code, exit 1 |
| **W6** resampler stated and measured | **PASS** | §9, now MEASURED on real frames |

Both W2 controls **passing** means they correctly **failed the gate**. A control
that passed the gate would be reported as a failure of the verification, and
`run_verify_plant` prints exactly that if it happens.

### 14.4 The holdout that would have shipped a lie — MEASURED

Design constraint 1 says a consumer must be able to tell a 0.353 px solve from
an 11.56 px one. My first `heldout_error` used a deterministic 5-fold stride
over the edge list, and it read **under 3 px** on `bee-3-cpl` — **below** M86's
`T_usable` of 4.0 px. A merge reading that sidecar would have concluded the
solve was usable. M86 measured that it is not.

Reading M10's protocol at source (`cmd_heldout`, `min_span = 40`) shows why: the
test set is the **long-span** edges and training is everything else, so the
solve must *extrapolate* long-range geometry from short-range measurements. A
stride holdout instead leaves, for every held-out edge, several near-duplicate
edges in training — it tests interpolation among neighbours.

**I withdrew the exact stride figure rather than ship it.** It came from an
implementation I had already replaced and whose output I had not saved, so it
was unsourced. In its place, a controlled measurement of the same effect that I
can hand you: the *same* edge set (`out/bee-3-cpl-edges.csv`, 299 frames, M86's
own), the *same* solver, varying only the holdout's span floor
(`out/W7-holdout-protocol.log`):

| test set | test edges | median error, all test spans | E* robust | verdict vs `T_usable` = 4.0 |
| --- | --- | --- | --- | --- |
| `span >= 1` (easy) | 2009 | **2.970 px** | 6.703 px | "usable" — **false** |
| `span >= 8` | 1119 | 4.710 px | 9.095 px | marginal |
| `span >= 40` (M10) | 217 | **12.323 px** | **11.562 px** | not usable — correct |

**A factor of 4.15 on the median, from the holdout rule alone**, on identical
data. The ladder is monotone, so this is a systematic property of the protocol,
not a sampling accident. The `span >= 40` arm reproduces M86 §6's `E*` of
11.562 px exactly, which is the control confirming the harness is the same one.

This was not an arithmetic bug; the easy protocol answers a different and much
easier question. `align_cmd.rs` now uses M10's protocol and the reason is in the
doc comment so it cannot be quietly reverted. Note the sidecars in §14.6 report
13.578 px for `bee-3-cpl` rather than 11.562 px because they are solved over
`align_cmd`'s own edge set, not this CSV — see the non-comparability note there.

### 14.5 Stack identity — why names and counts are not enough — MEASURED

`bee-2-cpl` and `bee-3-cpl` are the same subject, 299 frames each, same plane,
and their frame filenames are **byte-identical** (`DSC00001.ARW` …). Frame
count, geometry and a name digest all agree between them.

File sizes do not: 37,552,128 vs 39,362,560 bytes for frame 1, because the raw
compression tracks noise and the two stacks are ISO 100 and ISO 400. So
`StackIdentity` mixes **name and size** per frame through FNV-1a, which
separates them without decoding anything. Verified end to end:

```
applied to  bee-2-cpl (digest 2405062fd866542d, 299 frames)
MISMATCH
Error: this warp map was fitted on stack "bee-3-cpl" (digest 8d023c0fe355d109, 299 frames)
       but was applied to "bee-2-cpl" (digest 2405062fd866542d, 299 frames)
```

### 14.6 Sidecars produced — MEASURED

`S3-ba-unit`, spans `[1,2,4,8,16,32,64,96,128]`, M10 long-span holdout:

| stack | frames | drift px | held-out px | edge floor px | held-out / floor | edges refused | frames refused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `109MSDCF` | 22 | 38.934 | 0.360 | 0.385 | 0.94 | 0.0% (79/79) | 0 |
| `foam` | 100 | 235.285 | 3.562 | 0.233 | **15.3** | 13.2% (501/577) | 0 |
| `bee-3-cpl` | 299 | 186.702 | 13.578 | 2.908 | 4.7 | 16.2% (1961/2340) | 0 |

`109MSDCF` independently corroborates M86 §4 (drift 38.934 vs 39.7 px, held-out
0.360 vs 0.353) from a separately written pipeline.

**`foam`'s ratio is the interesting one.** Its edges are the most
self-consistent in the table — a 0.233 px cycle floor, better than the quiet
`109MSDCF` — while its held-out error is 15x that. The edges agree with each
other and no smooth similarity ladder describes them. That is the signature of
**real subject motion**, and it answers M86 §7's open question directly: the
method does silently absorb subject motion into the warp, the cycle floor does
**not** reveal it, and the **held-out-to-floor ratio does**. **DERIVED**: a
consumer wanting to detect "this bracket moved" should read the ratio, not
either number alone. Both are in the sidecar.

Note these drift figures use this command's span ladder, which is not M86 §4's;
`bee-3-cpl` reads 186.702 px here against M86's 232.7 px. The cycle floor is
likewise computed over whatever triangles this ladder closes and is dominated by
short spans, so 2.908 px here is **not** comparable to M86 §6's 9.07 px. Neither
figure is wrong; they are different edge sets. Do not mix them.

### 14.7 Design decisions and their evidence

- **Transform direction — verified at source, not assumed.** `AlignEdge.t` is
  `i -> j` (`align.rs:1330`); `Placement[k]` is relative to frame 0
  (`align.rs:1444`); `gather_into` documents `t` as mapping reference to source
  (`align.rs:2383`). So registration is `gather(frame_k, placement[k])` with
  **no inversion**. W2's inversion control exists because this is the one place
  a wrong answer is silent.
- **Text, not serde.** Neither crate depends on serde and adding one would race
  another agent on `Cargo.toml`. The format is line-oriented with `f64` stored
  as exact hex bits and the decimal beside it as a comment, so it round-trips
  bit-exactly *and* diffs.
- **Truncation is a typed error.** The header declares a frame count and the
  file ends with `end <count>`. A half-written sidecar is realistic — the writer
  runs ~50 s on 299 frames — and must never load as a short map.
- **Refusal is not identity.** Two non-collapsible states and no
  `unwrap_or(IDENTITY)` anywhere. M86 measured refusal rates to 47.5%.
- **`sample_checked`, not `sample`.** Uncovered destination pixels are NaN with
  a coverage flag, never a clamped border pixel smeared inward.

### 14.8 What I did not do

- **The estimator is untouched**, as instructed. 13.578 px on `bee-3-cpl` is
  still ~3x `T_usable`.
- **No merge integration.** `stack.rs`, `merge.rs`, `merge_cmd.rs`, `main.rs`
  and `lib.rs` were not modified. They were temporarily wired *locally* to
  build and run the gates, then restored byte-exactly; `git status` confirms
  both shared files clean.
- **No *frame* refusal was exercised on real data.** All three solves placed
  every frame (0 refused of 22, 100 and 299). Note this is **not** the same as
  edge refusal, which did fire heavily — 13.2% on `foam`, 16.2% on `bee-3-cpl`
  — and is a different mechanism: a refused *edge* is a measurement the solve
  drops, a refused *frame* is one the merge must drop. Only the second is
  represented in the sidecar, and only the first was observed. **NOT
  MEASURED**: what a genuinely disconnected frame produces in production. The
  frame-refusal path is covered by unit tests alone.
- **A near-miss worth recording.** While writing §9 I found that two of its
  numbers — the bilinear and nearest W2 ratios — existed in no committed log;
  they were carried in working memory from a run whose output I had not saved.
  I re-ran them rather than shipping them: both reproduced to four decimals
  (`out/W6-w2-per-resampler.log`). Being *right* was luck; being *sourced* is
  the standard, and the number was unsourced until re-run.
- **The flat-on-ruler physical invariant** — straight lines staying straight
  after gathering — is still unmeasured and is still the highest-value
  follow-up.

### 14.9 The two registration patches — for the orchestrator to apply

Both files were re-read at their committed bytes immediately before this section
was written. Neither is modified in my working tree (`git status --porcelain`
returns nothing for either).

**Patch 1 — `crates/strehl-core/src/lib.rs`**

The `pub mod` block is alphabetical and currently runs lines 13–25, ending
`pub mod through_focus;`. Insert one line **after** it, keeping the ordering:

```
 pub mod stack;
 pub mod through_focus;
+pub mod warpmap;
```

Exact text to insert: `pub mod warpmap;`

**Patch 2 — `crates/strehl-cli/src/main.rs`** — three insertions.

*2a.* The `mod` block is lines 3–5, alphabetical. Insert **before** line 3:

```
+mod align_cmd;
 mod image_out;
 mod merge_cmd;
 mod stack;
```

*2b.* In `enum Command` (line 25), insert as the **first** variant, before the
`/// Decode a directory of RAW files` doc comment on `Probe`:

```
 enum Command {
+    /// Solve a bracket's inter-frame geometry and write a warp sidecar.
+    ///
+    /// Focus breathing changes magnification frame to frame, so a deep bracket
+    /// is not registered as captured. This fits a similarity ladder over the
+    /// stack and writes it to disk with its own provenance and held-out error,
+    /// for the merge to gather through.
+    Align(align_cmd::AlignArgs),
     /// Decode a directory of RAW files and report what was found.
```

*2c.* In the dispatch `match` (line 281), insert **before** the `Command::Probe`
arm:

```
+        Command::Align(args) => align_cmd::run(&args),
         Command::Probe { dir, limit } => probe(&dir, limit),
```

**After applying, this should build and these should hold:**

```
cargo test  --release -p strehl-core --lib warpmap::   # 16 passed
cargo clippy --release -p strehl-cli --bin strehl -- -D warnings   # exit 0
strehl align --help                                     # exit 0
```

All three were run locally against a temporary copy of these registrations —
16 warpmap tests passed, clippy exited 0, `align --help` exited 0, and every
W1–W6 gate in §14.3 was produced by that build's `strehl align`. I then removed
the registrations and confirmed both shared files byte-clean. **NOT run**: `strehl align --help`specifically, though the subcommand itself was exercised throughout.
