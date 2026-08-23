# M66 — pre-registration: is a fixed gate `T` an N-dependent statement?

**Committed before any result was computed.** Nothing below was written after
seeing a number from any arm. Section 1 is code reading, which the brief orders
first and which is not a measurement.

---

## 0. The question

`strehl`'s merge admits a frame at a pixel by comparing that frame's regularised
focus response against the **maximum over all N frames**. The claim under test:
because `E[max of N]` grows with N, a **fixed** tolerance `T` encodes a
*different* statistical statement at N = 30 than at N = 299, and every gate
number in this corpus was measured at one particular N.

If true, it does not break the binary. It questions the **meaning** of published
numbers — the headline `5.4778x` at `--gate 8` on N = 30, `DEFAULT_GATE = 4.0`
applied across stacks of N = 19..299, and every `n_eff` in `docs/research/`.

---

## 1. What the shipped code actually does (read, not assumed)

`crates/strehl-core/src/merge.rs`:

```rust
pub fn tolerance(&self) -> f32 {
    self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
}

pub fn admits(&self, focus: f32, best: f32) -> bool {
    best - focus <= self.tolerance()
}
```

with `FOCUS_NOISE_SD = 0.015_214` (a `const`, measured in-crate) and `best =
FocusStats::best_focus[i]`, which `absorb`/`fold` maintain as the **max over
every frame folded**.

**Three things follow from reading alone, and they are the pre-condition of the
whole milestone:**

1. `tolerance()` reads exactly three quantities: the user's `threshold`, `√2`,
   and a compile-time constant. **There is no frame count anywhere in it**, and
   no term that could carry one.
2. The response `X` it is compared in is `box_mean_8(box_mean_13(0.125·|∇L|) /
   max(σ_L, 1e-3))` — normalised per pixel by the *sensor* noise sigma
   (`focus.rs`, `noise.rs`). That normalisation is what makes one threshold
   valid across ISOs and across the frame. **It is per-pixel and per-frame; it
   contains no N.**
3. `Estimator::mean_n_eff` is the mean over **all** plane pixels of the
   per-pixel admitted count. No interior inset.

So **nothing in the shipped tolerance absorbs N.** The "already handled"
resolution is therefore *not* available on the code-reading route. It remains
available on the empirical route (§5, criterion E-ABSENT).

---

## 2. The mechanism, DERIVED

Let `X_{k,i}` be frame `k`'s regularised response at pixel `i`, `τ(T) = T·√2·σ_F`
with `σ_F = FOCUS_NOISE_SD`. Admission is `max_j X_{j,i} − X_{k,i} ≤ τ(T)`.

**Null `H0(i)`** — every frame has the same *true* response at pixel `i`, so
`X_{k,i} = μ_i + σ_F ε_k` with `ε_k` iid `N(0,1)`. (`σ_F` is *defined* as the SD
of this field under pure sensor noise, so the scale is the crate's own.)

Write `t = T√2` (the tolerance in units of `σ_F`). The admitted count is
`A_N(t) = #{k : max_j ε_j − ε_k ≤ t}` and

```
E[A_N(t)] = N · P(max_j ε_j − ε_1 ≤ t) = N · f_N(t),
f_N(t)    = ∫ φ(x) Φ(x + t)^(N−1) dx.
```

**Claim (DERIVED).** `f_N(t)` is *strictly monotone* in `N` for every finite `t`.

*Proof.* For finite `x, t`, `Φ(x+t) ∈ (0,1)`, so `Φ(x+t)^N < Φ(x+t)^(N−1)`
pointwise; `φ > 0`; integrate. ∎

Therefore the **admitted fraction under the null is a strictly monotone function
of N at fixed `T`**, and the gate's per-frame null admission rate `f_N(T√2)` is
not held fixed by holding `T` fixed. That much is a theorem about the code as
written, not a guess.

**What the theorem does *not* settle, and what I therefore refuse to predict:**

- the direction of the admitted **count** `N·f_N(t)`, which is a product of a
  rising and a falling factor;
- **the size** of the fraction change over the corpus's actual `N ∈ [19, 299]`
  at the corpus's actual gates — it could be a rounding error or a factor;
- **anything at all about real through-focus stacks**, where `H0` is false at
  most pixels (facts 263/264 put a resolved edge's peak 10²–10³ σ clear, where
  the acceptance set is set by focus contrast and not by `σ_F`). The empirical
  sign and size on real frames are open, and I am not stating an expectation.

---

## 3. Arms

The observable throughout is the pair

- **φ(N, T) = mean `n_eff` / N** — the admitted **fraction**; and
- **mean `n_eff`(N, T)** — the admitted **count**,

reported together, with `frac(n_eff = 1)`, at every gate (rule 39).

Only the frame subset varies. Operator, regulariser, noise model, tolerance
formula, pixel set and stack are held fixed within an arm.

| arm | plant | what varies | why it is here |
| --- | --- | --- | --- |
| **A — analytic null** | none; `f_N(t)` by quadrature + `10^6`-draw Monte Carlo | N, T | the mechanism in closed form, with no image, no operator, no scene |
| **B — operator null** | synthetic static burst: M62's latent (`109MSDCF/DSC00020.ARW`, 2048² RGGB crop, ISO 160) + independent sensor noise per frame, pushed through the **real** focus operator | N, T | does the analytic null survive the real 43×43-support operator, per-pixel σ normalisation, and border policy? |
| **C — real through-focus** | corpus stacks, real frames | N (by three subset modes), T | the only arm that can speak to blast radius |

**Arm C subset modes**, run at every N on every stack, because each confounds N
with something different and I cannot remove the confound:

- **prefix** — first N frames. Matches the CLI's `--limit`. Preserves focus
  step, **truncates depth range**.
- **stride** — N frames evenly spaced across the stack. Preserves depth range,
  **thins focus sampling**.
- **random** — 8 seeded random subsets of size N. Gives a *between-subset SD*,
  which is the standard error rule 39 requires beside every ratio.

**Arm C stacks and why these** (`D:\personal\macro`, read-only):

| stack | N | `n_eff/N` at gate 4.0 (M64 §2.4) | why chosen |
| --- | --- | --- | --- |
| `coffee-bean` | 105 | **0.3011 — corpus max** | most null-like real stack; most room for the mechanism |
| `foam` | 100 | **0.0136 — corpus min** | most focus-discriminating; N-matched to `coffee-bean` and 22.15x apart in `n_eff/N` |
| `bee-1` | 299 | not published | the only N that reaches the top of the corpus range |
| `109MSDCF` | 22 | 0.2267 | the most-measured stack; carries the instrument check |
| `coffee-bubbles` | 19 | 0.1857 | corpus min N |
| `119MSDCF` | 33 | 0.1431 | ISO 50 |
| `113MSDCF` | 63 | 0.1362 | ISO 500 |
| `112MSDCF` | 79 | 0.1524 | ISO 500 |

**Declared drop order if decode cost forces it** (and I will report what was
dropped): `112MSDCF`, then `113MSDCF`, then `119MSDCF`. `wrapped-text-1/2` and
`bee-2/3` are out of scope from the start. `coffee-bean`, `foam`, `bee-1`,
`109MSDCF` and `coffee-bubbles` are **not** droppable — the first three carry the
blast radius and the last two carry the controls.

**Why the static burst is arm B and not arm C, stated deliberately.** M62 §4 and
M64 §2.4 both warn that a static burst is degenerate for focus: every frame is in
focus, so a merge that stops discriminating scores exactly `√N` and is
indistinguishable there from a correct estimator. That degeneracy is a fatal trap
for a *quality* question. For **this** question it is the opposite: `H0` — every
frame equal in true focus — **is** the regime in which the winner's-curse
mechanism is defined, so the burst is the cleanest possible instrument *for the
mechanism*, and it is the only plant in which subsetting varies N and nothing
else, because its frames are exchangeable by construction. I therefore use it
for the mechanism and **refuse to use it for blast radius**. Any claim about
what this does to real stacks must come from arm C.

**Grids.** `T ∈ {0, 0.5, 1, 2, 4, 8}` — the corpus ladder, plus `DEFAULT_GATE`
and the headline's 8. `N ∈ {3, 5, 8, 12, 19, 22, 30, 33, 45, 63, 79, 100, 105,
120, 130, 200, 299}` intersected with `[3, N_max]`, plus `N_max`.

---

## 4. Controls. Every one of these can fail, and a failure stops the report.

| id | control | pass condition | what it kills if it fails |
| --- | --- | --- | --- |
| **K1** | gate 0, every arm, every N | mean `n_eff` = 1.000000 exactly | the whole instrument: gate 0 admits only the winner by construction |
| **K2** | gate 1000 (far beyond any attainable response range), every arm, every N | `n_eff/N` = 1.000000 exactly | ditto, at the other end |
| **K3** | **instrument vs the shipped binary**: my full-N mean `n_eff` at gate 4.0 on all seven of M64 §2.4's stacks | within **1%** of M64's published shipped-binary values, on all seven | my re-implementation is not the shipped rule, and arm C means nothing |
| **K4** | **loader** (M52's mandatory check): dark temporal sigma at two ISOs vs M4 §8.1 | within **1%** on all 8 plane/ISO cells | the decode is wrong and nothing downstream is printed |
| **K5** | **decimation**: 4x-decimated pixel grid vs full-frame mean `n_eff`, on `109MSDCF` and `coffee-bubbles`, all gates | within **1%** | the sweep's pixel subsampling biases the observable |
| **K6** | **power**: arm B reproduces arm A's `f_N(t)` over the same N grid | within Monte-Carlo error, and arm B must itself show `S_null ≥ 1.05` (§5) over N ∈ [19,299] at some gate on the ladder | **the instrument cannot see the effect at all**, and arm C's result — whatever it is — is uninformative rather than negative |

K6 is the one that makes a null arm-C result *mean* something. Without it, "I
measured nothing" and "there is nothing" are the same sentence.

---

## 5. Pre-registered criteria, with the outcome that says ABSENT

Let `S(stack, T) = max_N φ(N,T) / min_N φ(N,T)` over the measured N grid,
restricted to `N ≥ 19` (the corpus's real range) and to the stride mode, with
prefix and random reported beside it.

- **E-ABSENT (the refutation).** The effect is **empirically absent on the
  corpus** if, at `T = 4.0` (the shipped default), `S(stack, 4.0) ≤ 1.05` on
  **every** arm-C stack in **all three** subset modes, **while** K6 holds. I will
  report this as REFUTED and stop, and that is a complete success.
- **E-PRESENT.** The effect is present if `S(stack, 4.0) > 1.05` on any arm-C
  stack in a mode whose two sibling modes agree in direction.
- **E-CONFOUNDED.** If prefix and stride disagree in *direction* on the same
  stack, the subset confound dominates N and I will report the question as **not
  answerable by subsetting**, not as either sign.

**Materiality ladder — what it would take to move a published number:**

- **M-HEADLINE.** M62's `5.4778x` at `--gate 8`, N = 30. The claim transfers
  across the corpus iff arm A/B give `f_N(8√2) ≥ 0.999` for every `N ∈ [19,299]`.
  If any corpus N falls below, the headline is an N-specific statement and I say
  so.
- **M-DEFAULT.** `DEFAULT_GATE = 4.0` is portable in the null iff
  `max_N f_N(4√2) / min_N f_N(4√2) ≤ 1.05` over `N ∈ [19,299]`.
- **M-GUARD.** M62's Requirement G is `n_eff/N < 0.95` on a real through-focus
  stack; M64 measured a worst case of 0.3011 (`coffee-bean`), a 3.16x margin.
  The guard **fails** iff any measured `(stack, N)` at gate 4.0 reaches
  `n_eff/N ≥ 0.95`. Separately, I will report the margin `0.95 / (n_eff/N)` at
  every N, because a margin that moves with N is a finding in its own right even
  if it never crosses.

**I will report any of these as NOT MET, in these words, if they are not met. I
will not reword a criterion after seeing the number it judges.**

---

## 6. The corrected form — candidates named in advance, none to be implemented

The brief forbids building a fix. To stop me choosing a flattering one post hoc,
the candidate set is fixed here:

- **(i) status quo** — `τ = T√2·σ_F`, N-free.
- **(ii) fixed null admission rate** — `τ_N(α) = q_{1−α}(N)·σ_F` where `q` solves
  `∫φ(x)Φ(x+q)^(N−1)dx = 1−α`. Makes `T` a per-frame false-rejection rate,
  invariant in N by construction.
- **(iii) selection-offset anchor** — `τ_N = (T√2 + c_N − c_{N₀})·σ_F` with
  `c_N = E[max of N standard normals]` and a declared reference `N₀`. Keeps
  today's numbers exactly at `N = N₀`.
- **(iv) shrunk winner** — compare against `max − b_N·σ_F` rather than `max`,
  i.e. de-bias the reference instead of widening the tolerance.

I will say which the measurement selects, what it would do to the published
numbers, and **I will not write it into `crates/`.**

---

## 7. Declared in advance: what this cannot measure

- **Focus-correctness.** Every arm reads admitted *counts*. Nothing here checks
  the merge admitted the *right* frames. Unmeasured in this corpus (M64 §2.4).
- **The sharpness price.** Not measured here, and not measured anywhere in this
  corpus for this gate (`merge.rs`, `DEFAULT_GATE` doc).
- **A real static burst.** None exists in the corpus (M62 §8.1). Arm B is
  synthetic; its noise is drawn from the same model the gate normalises by.
- **Alignment.** The shipped merge does not align, so neither do I. Any true
  inter-frame shift is inside every arm equally.
- **N beyond 299**, and N between the corpus's discrete counts, on real frames.

**The circularity, named before the fact.** `σ_F = 0.015214` sets both the
tolerance *and*, in arm B, the SD of the plant's response. If `σ_F` is wrong,
arms A and B are wrong **in the same direction** and their agreement (K6) cannot
detect it. Arm B is additionally "data drawn from its own model" in exactly M62
§8's sense. Arm C is the only arm not calibrated against the thing it measures,
and it is the confounded one. That trade is the honest state of this milestone
and is not fixable inside it.

---

## 8. Reproduction

```
experiments/M66-gate-n-dependence/src/00-analytic.py     arm A + candidate fixes
experiments/M66-gate-n-dependence/src/01-loader.py       K4
experiments/M66-gate-n-dependence/src/02-fields.py       decode -> cached cubes
experiments/M66-gate-n-dependence/src/03-controls.py     K1 K2 K3 K5
experiments/M66-gate-n-dependence/src/04-burst.py        arm B + K6
experiments/M66-gate-n-dependence/src/05-sweep.py        arm C
experiments/M66-gate-n-dependence/src/06-blast.py        materiality ladder
```

Crate constants are parsed from `crates/strehl-core/src/{merge,focus,profile}.rs`
at run time and never retyped (M62's discipline). `data/` and `*.npy` are
gitignored and regenerable.
