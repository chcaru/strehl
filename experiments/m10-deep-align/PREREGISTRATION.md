# M10 — pre-registration

**Written before any solver was run.** SYNTHESIS §5 item 14: enumerate the full
outcome grid, including "everything fails", before looking at the answer.

Milestone: **M10 — deep-stack alignment**, SYNTHESIS risk 11.

---

## 0. What was already known when this was written, and what was peeked at

Known from the record:

* Alignment is a **4-parameter similarity**; affine and quadratic buy ≤6% (fact 17).
* The estimator's noise floor is **0.19 plane px**; worst known-warp scale error
  2.23e-5 = 0.047 px at the plane corner (M3 §0).
* **Chaining is dead**: composing 21 adjacent fits underestimates drift by 32%,
  **12.5 plane px / 25 sensor px** at the corner (M3 §3, fact 16).
* **A single fixed reference is dead at depth**: on the 105-frame `coffee-bean`
  stack, 3 of 104 direct-to-frame-0 fits produced no fit at all and the rest used
  a median of 18 of 96 tiles at 4.61 px tile rms (M6, risk 11).
* Scale centre ≈ **(−11, −56) plane px** from the plane centre (M3 §5).

**Disclosed peek.** Before writing this file I read M6's already-generated
`experiments/m6-residual-halo/data/coffee-bean-fits.csv` and tabulated *fit
quality against span* (median kept tiles and tile rms per span). That table was
used **only to size the edge budget** — which spans are worth measuring at all.
It contains no global solution, no cycle statistic and no held-out prediction, so
it cannot answer any hypothesis below. The M10 harness regenerates every edge
itself; nothing from M6's CSVs enters a result.

**Unit discipline.** M3's "25 px" is at **sensor** resolution; the plane figure is
**12.5 px**. M6's halo figures (19.42 / 32.39 / 89.23 px) are **plane** px. This
document reports **plane px** throughout and gives the sensor figure only where a
comparison to M3 §3 demands it. 1 plane px = 2 sensor px. Plane geometry is
3516 × 2344; the plane-corner radius is **2112.93 px**.

---

## 1. The question

Produce **globally consistent similarity transforms for all 105 frames** of
`coffee-bean`, and measure how accurate they are, without ground truth.

---

## 2. Notation and the exact objective

A similarity is a complex pair `(a, b)` acting on plane coordinates `p` taken
relative to the plane centre: `p' = a·p + b`. The harness's `Fit{g, rot, ax, ay}`
maps to `a = (1+g) + i·rot`, `b = ax + i·ay`. Composition `f1` then `f2` is
`a = a1·a2`, `b = a2·b1 + b2`.

`M(i→j) = (a_ij, b_ij)` is the **directly measured** transform taking frame `i`
coordinates to frame `j` coordinates. `G_j = (A_j, B_j)` is the **global**
transform taking frame-0 coordinates to frame `j`. Gauge: `G_0 = (1, 0)`.

Edge `(i, j)` asserts `G_j = M(i→j) ∘ G_i`, i.e.

```
A_j = a_ij · A_i           B_j = a_ij · B_i + b_ij
```

**Both are linear in the unknowns** `{A_j, B_j}`, because `a_ij` is data. So the
whole bundle adjustment is one complex linear least-squares problem, not a
nonlinear one.

**Corner error** between two similarities `T, T'` is
`max over the 4 plane corners of |T(p) − T'(p)|`, in plane px. For
`ΔA = a−a'`, `ΔB = b−b'` this is `max_corners |ΔA·p + ΔB|`.

**The objective actually minimised** is
`Σ_edges w_ij ( ρ²·|ΔA_ij|² + |ΔB_ij|² )` with `ρ = 2112.93`. Because the four
corners are symmetric about the origin (`Σp = 0`, `mean|p|² = ρ²`), this is
**exactly** the mean-square corner reprojection error over the corner set. It is
not a proxy for it.

---

## 3. Strategies under test

| id | strategy | description |
| --- | --- | --- |
| `S0-fixed` | fixed reference (status quo, rule 6) | `G_j = M(0→j)` directly. Undefined where the fit failed. |
| `S1-chain` | adjacent chain (rule 6's forbidden option) | `G_j = M(j−1→j) ∘ … ∘ M(0→1)`. |
| `S2-ladder-s` | candidate (a), keyframe ladder, stride `s ∈ {4, 8, 16, 32}` | chain over keyframes `0, s, 2s, …` using direct `M(ks→(k+1)s)`; within a segment, `G_j = M(ks→j) ∘ G_ks`. |
| `S3-ba` | candidate (b), global bundle adjustment | weighted linear LS over all measured edges, IRLS-robust. |
| `S4-poly-d` | candidate (c), parametric in stack index | `log A_j = P(j)`, complex polynomial with `P(0)=0`, degree `d ∈ {1..6}`; `B_j` then solved linearly against the same edges. |
| `S5-poly-centre-d` | candidate (c) + fixed scale centre | as `S4` plus `B_j = (1 − A_j)·c` for a single complex `c`. |
| `S6-ba-smooth-λ` | (b) + (c) | `S3` with a penalty `λ` on the second difference of `log A_j`. |
| `S7-wide` | candidate (d) | `S3`'s edge set re-measured with a 3-level pyramid and a wider fine search, to test whether no-fit pairs are a capture-range failure. |

`S3` is run on the *same* edge set as `S1` and `S2` so the comparison is a
comparison of estimators, not of data.

---

## 4. Metrics, and the identity that makes each one non-degenerate

### M1 — cycle consistency of the raw measurements (input floor)

For every triple `(i, j, k)` with all three edges measured, corner error of
`M(i→k)` against `M(j→k) ∘ M(i→j)`. Reported as a **distribution** (median, p90,
max) stratified by the spans involved. This bounds what any solver can achieve
and is computed from data alone.

### M2 — in-sample edge residual of a global solution

Corner error of `M(i→j)` against `G_j ∘ G_i⁻¹`, per edge. In-sample; reported
for completeness, not used for the ruling.

### M3 — span-stratified held-out prediction (**the headline**)

Fit using **only** edges with span ≤ `s_train`; predict every edge with span >
`s_train`; report corner error against that edge's direct measurement, as a
function of the test edge's span. `s_train ∈ {1, 2, 4, 8, 16}`.

**Non-degeneracy check, written before running.** A bundle adjustment over a
*tree* is algebraically identical to chaining along that tree: with `|E| = N−1`
the normal equations have a unique exact solution and every residual is zero. So
a design containing only span-1 edges **cannot** distinguish `S3` from `S1`, and
would have been structurally incapable of answering the question — the M6 trap.
The design therefore requires cycles: with `N = 105` and spans
`{1,2,4,8,16,32,48,64,80,96}` plus every direct-to-0 edge, `|E| ≈ 800` and the
cycle rank is `|E| − (N−1) ≈ 700`. **The harness prints the cycle rank and the
per-`s_train` cycle rank, and any `s_train` whose training graph is a tree is
reported as degenerate and excluded from the ruling.** `s_train = 1` is a tree by
construction and is included *only* to demonstrate the degeneracy explicitly.

**What this metric actually tests.** If short-span edges carry a coherent
pixel-locking bias `β` per step, a solution built from spans ≤ `s_train`
accumulates `≈ (s/s_train)·β·(something)` by the time it reaches span `s`, so the
held-out corner error must **grow with the test span**. If they do not, it must
stay flat at the direct-fit noise floor. That is a quantitative, falsifiable
split.

### M4 — leave-one-edge-out

For a fixed pseudo-random sample of 200 edges, drop that one edge, refit `S3`,
predict it. Tests local consistency, complements M3.

### M5 — bridge (cut) holdout

Drop **all** edges crossing a cut at frame `m ∈ {26, 52, 78}`; refit; predict the
dropped edges. Under `S3` the graph becomes **disconnected** and the problem is
unidentifiable — the harness must detect this and report it, not return a number.
Only `S4`/`S5` (a global model in `j`) can bridge a cut. That asymmetry is the
point: **M5 is the metric that can distinguish (b) from (c)**, because it is the
only one that (b) is structurally unable to answer.

### M6 — chain-versus-direct bias ladder (the placebo for pixel locking)

For each span `s`, compare the composition of `s` adjacent span-1 edges against
the direct span-`s` edge, in corner px, per starting frame. This measures the
pixel-locking accumulation rate on `coffee-bean` **directly**. Its positive
control is M3's own 12.5 plane px at 21 steps on `109MSDCF`, which the same code
must reproduce.

### M7 — agreement with a trusted regime (external validity)

On `109MSDCF` (22 frames) and `119MSDCF` (33 frames) the fixed reference is
known-good (60 tiles, 0.78 px rms). Report corner error of every strategy against
`S0-fixed` on those stacks. A global method that cannot reproduce the trusted
answer where one exists may not be believed where one does not.

---

## 5. Controls (project rule 11)

| id | control | what it must show |
| --- | --- | --- |
| `P1` | estimator control — M3 §0's four known warps re-run through this crate's ported aligner | worst scale error **2.23e-5**, residuals **0.194 / 0.196 / 0.190 / 0.165 px**. This is also the SYNTHESIS §5 item 15 guard: reproduce a published number before trusting a port. |
| `P2` | **solver control, purely numeric** — plant known `G_j`, synthesise edges by exact composition, add (i) Gaussian noise only, (ii) noise **plus a coherent per-step bias** mimicking pixel locking | every solver recovers the planted `G_j` in case (i); in case (ii) `S1`/`S2` must show the planted accumulation and `S3` must not. No resampling anywhere, so SYNTHESIS §5 item 11 does not apply. |
| `P3` | **null** — replace every edge measurement with a random similarity of the same magnitude | every held-out metric must blow up. A metric that looks healthy on garbage is not a metric. |
| `P4` | **semi-synthetic image control** — a 105-frame stack built from one real frame by a planted smooth similarity sequence plus a planted depth-dependent blur, so long-baseline pairs genuinely decorrelate | the whole pipeline, from ARW to global solution, recovers the planted transforms in absolute corner px. **Discloses the resampler**: the warp is bilinear, so per M6 the estimator sees a sub-pixel-phase sharpness modulation. This control is used for *recovery* only and never as evidence about defocus, exactly as M6 constrained itself. |
| `P5` | **negative control on the null's own detector** — `S3` fitted on real edges but scored against `P3`'s randomised test edges | must fail, proving M3/M4 are not passed by construction. |

`P1`, `P2`, `P3` and `P5` gate the ruling: if any fails, no number is quoted.

---

## 6. Decision rule — the FULL outcome grid

Thresholds are in **plane px of corner error**, fixed here, before running.

* `T_solved  = 1.0` px — comparable to the 0.6–1.3 px residual that M3 measured
  for a single well-conditioned pair, and ~5x the 0.19 px estimator floor.
* `T_usable  = 4.0` px — below the status quo. It is also below M6's 4.61 px
  *tile* rms, which is a different quantity and is **not** the comparison being
  made; the comparison is against `S0-fixed`'s own measured corner error under
  the same held-out protocol.
* `T_chain   = 12.5` px — M3's measured chaining error at the plane corner.

Let `E*` be the best strategy's **median M3 held-out corner error at the longest
test span with a non-degenerate training graph**, and let `slope` be the
regression of that error on test span.

| cell | condition | ruling |
| --- | --- | --- |
| **A** | `E* ≤ T_solved` **and** `slope` not significantly > 0 **and** all 105 frames have a transform **and** M7 agreement ≤ 0.5 px on both shallow stacks | **Risk 11 SOLVED.** Rewrite rule 6. |
| **B** | `T_solved < E* ≤ T_usable`, other conditions as A | **Risk 11 PARTIALLY SOLVED** — a usable strategy exists, accuracy stated, residual named. Rule 6 qualified, not deleted. |
| **C** | `E* ≤ T_usable` but `slope` significantly > 0 | **PARTIAL, with an accumulation term.** Report the slope as the new open quantity; deep stacks bounded by stack depth. |
| **D** | `E* ≤ T_usable` but some frames have no transform | **PARTIAL, coverage-limited.** Report which frames and why. |
| **E** | `T_usable < E* ≤ T_chain` | **NOT SOLVED, but better than chaining.** Report the ordering and the ceiling. |
| **F** | `E* > T_chain` | **NOT SOLVED.** Report that the global solve is no better than the option rule 6 already forbids. |
| **G** | any of `P1`,`P2`,`P3`,`P5` fails | **NO RULING.** Report the control failure and stop. |
| **H** | M3's held-out protocol is degenerate at every `s_train` (training graph always a tree) | **NO RULING from M3.** Fall back to M4 + M7 + `P4` and say so explicitly. |
| **I** | strategies are indistinguishable (all within run-to-run spread of each other) | **Report the tie.** Prefer the cheapest and say the experiment could not separate them. |
| **J** | **everything fails** — every strategy exceeds `T_chain`, or no solver converges | **Risk 11 remains fully open**, and the report says so in the first line. Enumerate exactly what was ruled out. |

### Per-hypothesis falsifiers, stated in advance

* **(a) keyframe ladder is falsified** if its M3 held-out error at the longest
  span exceeds `S3`'s by more than 2x, or if its error grows with the number of
  segments at a rate that reaches `T_usable` before 105 frames.
* **(b) bundle adjustment is falsified** if its M3 held-out error grows
  significantly with test span, or exceeds `T_usable`.
* **(c) smoothness in stack index is falsified** if **any** of:
  1. the residual of the best-degree polynomial fit to `S3`'s `log A_j` exceeds
     3x the per-frame uncertainty implied by `S3`'s own edge redundancy;
  2. `S4`/`S5`/`S6` do **not** beat `S3` on M3 held-out error at long span
     (i.e. the smoothness prior buys nothing);
  3. `S5`'s single scale centre is rejected — the residual of the
     `B_j = (1 − A_j)·c` constraint exceeds 3x the free-`B` residual.
  **Note that falsifier 2 and cell B can both hold**: smoothness may be true and
  useless. That is a real outcome and it is registered as such.
* **(d) coarse-to-fine rescue is falsified** if `S7-wide` does not convert
  no-fit pairs into fits, or converts them into fits whose M2 residual is worse
  than the edges it replaces.

### What gets reported no matter what

The per-edge CSVs, the per-frame solution CSVs for every strategy, the cycle
rank at every `s_train`, the control output, and the file counts of the
read-only capture directories before and after.

---

## 7. Threats to validity, listed before running

1. **Selection bias in long edges.** Long-span fits that succeed may be the
   easy ones. Mitigation: report `used` tile counts per edge and test whether
   held-out error correlates with `used`.
2. **The reference for M3 is itself noisy.** A direct span-64 fit uses ~13 tiles
   at ~5 px tile rms, so its own standard error is ~1–3 corner px. Mitigation:
   report the **across-edge mean** (which detects bias, and shrinks as
   1/√n_edges) separately from the **across-edge sd** (which does not). These are
   two statistics over the same set of edges — this is not a spatial-vs-temporal
   comparison (rule 10).
3. **Gauge freedom.** All errors are computed as differences of *relative*
   transforms, never of absolute ones, so the choice `G_0 = identity` cannot
   affect any number.
4. **f32 storage.** Edge parameters are written to CSV at 9 significant figures;
   `g ≈ 1e-4` at span 1, so 9 figures is ~5 orders of margin.
5. **Resampling.** No real-data claim rests on resampled imagery. `P1` and `P4`
   are recovery controls and are labelled as such.

---

## 8. Amendments (dated, pre-data)

Amendments are appended here rather than edited into the body above, so the
original registered design stays legible. Every amendment below was written
**before any solver was run on any real edge set**. The only real-data artefact
in existence at the time of writing is the control `data/coffee-bean-floor.csv`
(P1b, planted-warp recovery), which contains no pairwise stack edges.

### A1 — the keyframe ladder is reformulated as minimum-hop composition

**Registered form.** S2 was "keyframe ladder with stride s: chain frame 0 to the
nearest keyframe below the target, then fit directly within the segment."

**Problem found while implementing.** The registered edge-span set is
`{1, 2, 4, 8, 16, 32, 48, 64, 80, 96}`. A within-segment fit for stride 32
requires spans 3, 5, 6, 7, 9, ..., which are not in the set. Measuring every
span from 1 to 32 to support one strategy would multiply the edge budget by
about four and would still leave stride 48 unimplementable.

**Replacement.** `S2 = solve_hops(max_span = M)`: the transform for frame `j` is
the composition along the **minimum-hop path** from frame 0 to frame `j` in the
graph of measured edges of span at most `M`. This is a strict generalisation of
the registered ladder: for `M = 32` frame 104 is reached in four hops
(32+32+32+8), which is exactly what a stride-32 ladder would do, and every other
frame is reached in the fewest hops its available spans allow. Ties are broken
by preferring the longest available span, then the lowest intermediate index, so
the path is deterministic.

`M = 1` is the pure adjacent chain and is the S1 baseline that project rule 6
already forbids. `M = 0` is undefined and not run.

**Why this is not a weakening.** The registered ladder is one particular hop
path; minimum-hop composition is the best hop path available at that `M`. If
`S2` fails, the registered ladder would have failed at least as badly, so the
falsifier registered for (a) — "no stride reaches the usable threshold" —
becomes strictly harder to trip, not easier.

### A2 — the estimator floor sweep gains a configuration axis

**Registered form.** P1b swept the anchor margin only, at the `m10`
configuration, to choose the margin by measurement rather than by guesswork.

**Reason for amendment.** The first P1b run (360 planted warps, margins
10/32/64/96/128) showed the recovery error is nearly independent of margin but
strongly dependent on the **magnitude of the planted scale change**: median
corner error 0.14 px at |g| < 0.005 rising to about 3.7 px at |g| in
[0.035, 0.060]. That is a property of the estimator on identical content with no
defocus of any kind, so it cannot be a content-overlap effect. Two mechanisms
could produce it and the registered sweep cannot separate them:

* **capture range** — the coarse stage searches +/-`coarse_radius` decimated px
  at the coarsest factor, which at factor 8 and radius 10 is +/-80 plane px,
  while a 4.6% scale change displaces a plane corner by about 97 px; or
* **template stretch** — a rigid correlation template of side `T` matched across
  a scale difference `g` is internally stretched by `g*T` px, which for
  `T = 128` and `g = 0.046` is 5.9 px, so no single shift can align the tile.

**Amendment.** P1b is re-run over the cross product of anchor margin and three
estimator configurations: `m10` (pyramid 8/4, fine template 128), `wide`
(pyramid 32/16/8, coarse and fine radius 12 — larger capture range, same
template), and `wide64` (`wide` with a 64 px template on a denser grid — same
capture range, half the template stretch).

**Registered prediction, written before the run.** If the wide-baseline floor is
a capture-range effect, `wide` removes most of it and `wide64` adds little. If
it is a template-stretch effect, `wide` changes little and `wide64` roughly
halves the error in the largest |g| bin. If neither helps, the wide-baseline
floor is intrinsic to single-pass rigid-template similarity estimation and both
(a) and (b) must be built out of short edges only.

**Consequence for the ruling either way.** This changes no threshold and no
falsifier. It affects only which estimator configuration the edge sets are
measured with, and that choice is now made from measured recovery error rather
than assumed.
