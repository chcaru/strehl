# M23 — pre-registration: per-edge response calibration of short alignment edges

**Committed before any number in `out/` was computed.** Everything below is a contract. If a
measurement contradicts it, the contract is what gets quoted, not a revised version of it.

Milestone: **M23**, research/measurement. Nothing here ships code into `crates/`.
Harness: verbatim copy of `experiments/m12-shrinkage/` (itself a verbatim copy of
`experiments/m10-deep-align/`) plus one added Rust mode, `metacal`. Neither M10's nor M12's
directory is touched.

---

## 0. The question

Deep-stack alignment lands at **6.76 plane px** held-out and the error is bounded by the *edges*,
not the solver (SYNTHESIS fact 47). The bound comes from short edges, which under-report
magnification change (fact 43). The committed plan discards spans 1–2 from the solve.

Review item **R4** proposes importing weak lensing's response calibration (metacalibration): for
each edge, plant a known scale increment `±δ` on that edge's own two frames, remeasure, form the
per-edge response `R`, and divide that edge's measured log-scale by **its own** `R`.

**Does that beat 6.76 px?**

## 0.1 Does M12 already refute this? — answered before measuring

**No, and the distinction is real.** M12 refuted a **transfer**: a scalar `k = 1/S_W(1)` fitted on
one stack's edge set and applied to a *different* stack, which failed 0 of 18 cross-scene pairs
(fact 52). R4 transfers nothing. `R` is measured on the identical two frames whose edge it
corrects, in the same run, with the same estimator and the same tile set. The two proposals differ
in the object being generalised over — M12 generalised across scenes, R4 generalises across
nothing.

**But M12's own data already bounds what R4 can achieve, and I state the bound before measuring so
it cannot be presented later as a discovery.** M12 §2.2's C4 control is *already a per-edge,
self-measured response*, just used as a diagnostic instead of a correction. On `coffee-bean` it
reads recovery **0.529** at `|g| = 1e-4` and **0.640** at `2e-4`, rising to **1.020 / 0.994 /
1.015 / 0.990** at `4e-4 / 8e-4 / 2e-3 / 4e-3`. Dividing by the most favourable of those inflates a
span-1 log-scale by at most **1/0.529 = 1.89×**, against the **3.26×** the conservation identity
says is missing. So R4 **cannot** close the conservation gap at any plant size M12 tested, unless
this milestone's two-sided estimator reads materially lower than M12's one-sided one.
(DERIVED from published M12 numbers, not a result of this milestone.)

That is not a refutation of R4. It is a pre-registered ceiling on gate (a), and gate (c) is
independent of it.

---

## 1. Definitions — fixed here, not after the fact

The estimator returns a similarity per edge with complex scale-rotation `a = (1+g) + i·rot`.

- **Measured log-scale** of edge `e = (i, j)`: `L_e = log|a_e|`.
- **Plant**: `W(δ) = Fit { g: δ, r: 0, ax: 0, ay: 0 }`, applied to the *moving* frame by
  `warp_known` (bilinear). The plant's own log-scale is `log(1+δ)`.
- **Increment**: `I_± = F_± ∘ F_0^{-1}` in the `(a, b)` algebra; `ℓ_± = log|a(I_±)|`.
- **Per-edge response (primary, two-sided)**

  ```
  R_e(δ) = (ℓ_+ − ℓ_−) / (log(1+δ) − log(1−δ))
  ```

- **One-sided response** `R_e^+ = ℓ_+ / log(1+δ)`, `R_e^- = ℓ_- / log(1−δ)`. This is M10's P7
  ratio; it is carried only as a consistency check against fact 45.
- **Corrected log-scale**: `L'_e = L_e / R_e(δ)`. Scale magnitude only. Rotation and translation
  are **not** corrected — R4 specifies scale, and correcting more would confound the gates.

### 1.1 Why two-sided

`warp_known` is bilinear, and bilinear's phase-dependent blur has variance `φ(1−φ)` in the
fractional-pixel offset `φ`. That is invariant under `φ → 1−φ`, i.e. **even** in the sign of the
plant, while the response is **odd**. So the two-sided difference cancels the resampler's own
contribution to first order where M10's one-sided ratio does not. This matters because M10's P6
`resample` arm — real content, bilinear plant, *no* defocus difference — reads **1.323** at 0.12 px
and **0.863** at 0.24 px with an IQR of `[0.656, 1.606]` and `[0.596, 1.130]`. At exactly the plant
sizes where the P7 real-pair probe reads 0.559 / 0.664, the resampler control is itself broken.
**M10's mechanism table (`out/p6-p7-mechanism.txt`) does not include the resample arm, so fact 45's
attribution to defocus is not closed against the resampler.** Null **N3** closes it here.

(ARGUED — the `φ(1−φ)` symmetry argument. N3 is the measurement that decides it.)

### 1.2 The `δ` ladder is a test of the premise, not a tuning sweep

Metacalibration assumes the measured quantity is a locally **linear** function of the true one, so
that one number `R` characterises the edge. If `R` depends materially on `δ`, that assumption is
false and no choice of `δ` rescues it.

Registered ladder: `δ ∈ {1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3}`.
**Primary `δ` = 2e-4**, registered now, chosen because its differential displacement (0.24 plane px
at ρ = 2112.93 / 1200 px lever) is the smallest plant above the estimator's 0.19 px floor and is
comparable to a real `coffee-bean` span-1 edge's own measured displacement (0.19 px).
No argmin over `δ` will be reported as an optimum (rule 13); an endpoint result is reported as
"no turnover found within the sweep".

**Registered δ-dependence criterion:** if `median R(1e-4)` and `median R(8e-4)` on `coffee-bean`
span-1 differ by more than **0.15**, the local-linearity premise is **refuted** and that is the
milestone's headline regardless of what gates (a) and (c) do.

---

## 2. The three registered gates

Each gate states its **failure direction** (rule 18) next to it.

### Gate (a) — conservation / telescoping, on `coffee-bean`

Statistic: M12's, unchanged. For window `0..W`, `T_W(1) = Σ log|a_{k,k+1}|`, `A_W = log|a_{0,W}|`,
headline **`1/S_W(1) = A_W / T_W(1)`**. `W = 48`, the window M12 published (uncorrected value
**3.260**; the orchestrator's independent recomputation **3.222**).

Corrected: replace each span-1 `log|a|` by `L'`, recompute.

- **PASS** if `|1/S'_W(1) − 1| ≤ 0.15`.
- **PARTIAL** if it moves at least halfway, i.e. `1/S'_W(1) ≤ 2.13` but outside the pass band.
- **FAIL** otherwise, including any overshoot below 0.85.

Also reported on the whole-stack chain (`0..82` against the direct `(0,82)` edge) and on every
width-48 window at every offset, because M12's verification showed a single hand-matched window is
where selection hides.

> **Failure direction.** `1/S_W(1) → 1` is manufactured by *anything* that inflates the magnitude
> of span-1 log-scales. Dividing by a noisy `R` inflates on average (`E[1/R] > 1/E[R]` for any `R`
> with variance), and a single `R` near zero blows one edge up without bound. The statistic
> **cannot** distinguish a correct per-edge correction from an undirected inflation. **Gate (a) is
> therefore inadmissible on its own** and is scored only jointly with null N1 and gate (c).

### Gate (b) — the built-in placebo, on `112MSDCF`

`112MSDCF` has essentially no shrinkage (`1/S_W(1) = 1.048`). A correction that "fixes" it is
measuring something other than the defect.

- **PASS** if `median R` over span-1 and span-2 edges at the primary `δ` lies in **[0.90, 1.10]**,
  and if applying the correction moves `1/S_W(1)` by **less than 0.10** in absolute value.
- **FAIL** otherwise.

> **Failure direction.** A probe with no statistical power reads `R ≈ 1` for a trivial reason. Gate
> (b) is admissible **only** if the same code, same day, same `δ` reads `R < 0.90` on `coffee-bean`
> — i.e. only if the positive control fires. If both read ≈ 1 the instrument, not the placebo, is
> what has been measured.

### Gate (c) — the only gate that ships anything

Held-out prediction of trustworthy long edges, M10's harness and M10's test set, unchanged:
`coffee-bean`, `cfg = m10`, test = every directly measured edge with `span ≥ 40` and `≥ 12`
surviving tiles (125 edges). No strategy ever sees a test edge.

Baseline: **6.758 px**, M10's best full-coverage row (`S4-poly6` trained on `span ≥ 32`, registered
`E*`). Recomputed here on the same scan, not quoted from the report.

- **PASS** if some full-coverage strategy trained on a set that **includes corrected spans 1–2**
  scores below **6.758 px** on the registered `E*` **and** the margin exceeds **0.40 px** (the
  observed spread among M10's runners-up, so the win is not a scan artefact).
- **FAIL** otherwise. **If gate (c) fails, R4 ships nothing**, whatever (a) and (b) say.

Training sets added for this comparison, fixed now:
`span ≥ 3` (the committed discard-1–2 policy), `all measurable` (spans 1–2 uncorrected),
`span ≥ 3 + corrected spans 1–2`, `all measurable, corrected`, and `span ≤ 2 corrected` alone.

> **Failure direction.** Scanning (train set × strategy) and reporting the minimum is a
> multiple-comparisons win. Both arms are therefore scored over the **same** strategy scan, and the
> required margin is set above the runner-up spread. The metric also cannot see errors on the short
> edges themselves — it only sees long-edge prediction — so a correction that helps short edges and
> harms long ones would read as a loss, which is the conservative direction.

---

## 3. Null controls — registered before results (rule 11, rule 17)

**Rule 17 statement of the shared path.** Gate (a) bins a corrected quantity (`L'`) against a map
(`A_W`, the long anchor) — but `L'`, `L` and `R` all come from the same estimator on the same two
frames. The mechanism that could drive both is **tile dropout and per-edge noise**: an edge with
few surviving tiles has both a noisy `L` and a noisy `R`, and `L/R` is inflated by the noise in `R`
alone. That shared path is broken by N1.

| id | control | what it destroys | what it preserves | reading that kills R4 |
|---|---|---|---|---|
| **N1** | **shuffled R** — permute `R` across edges within `(stack, cfg, span, δ)` | the per-edge correspondence, i.e. all of R4's claimed information | the exact marginal distribution of `R`, hence all inflation | N1 restores conservation as well as measured `R` |
| **N2** | **constant R** — divide every edge by the group **median** `R` | all per-edge variation | the central tendency | N2 does as well as per-edge `R`: R4 then reduces to the scalar M12 refuted |
| **N3** | **self-pair** — `R` measured on `(k, k)`: real content, zero defocus difference, identical resampler and plant | the defocus difference only | content, resampler, estimator, plant | `R ≠ 1` on N3: the response is measuring the resampler, not defocus |
| **N4** | **resampler-free field** — M10's `lock` mode `field` arm, re-read two-sided | the real content | the geometry | disagreement with M10's published 1.008 / 0.991 means the harness moved under me |

N4 is a **reuse of a prior harness, so it is a consistency check and not independent evidence**
(discipline 34). It is registered to catch harness drift, nothing more.

**Positive control (required for any null to have a scale):** `coffee-bean` span-1 at `δ = 1e-4`
must read `R < 0.9`. If it does not, no null below has a known-real signal to be read against and
the whole design is uninformative — which is itself the reportable outcome.

---

## 4. Author's predictions, registered so they can be scored

1. `R` on `coffee-bean` span-1 will be **materially δ-dependent**: low at `1e-4`, ≈1 by `8e-4`.
   That refutes the local-linearity premise and makes gate (c) fail.
2. Gate (b) **passes** — `R ≈ 1` on `112MSDCF`.
3. Gate (a) is **PARTIAL**, not PASS: `1/S'` lands near 2, not 1.
4. Gate (c) **fails**.
5. N1 (shuffled) restores conservation **nearly as well** as measured `R`, because inflation, not
   information, is doing the work.
6. N3 (self-pair) reads `R` closer to 1 two-sided than M10's one-sided resample arm did.

Any of these being wrong is a result. Predictions 1–4 being right is a **negative result**, which
per AGENTS.md is a complete milestone.

---

## 5. Cost

Registered budget: **two extra correlation evaluations per edge per δ** (three fits total, one of
which is the edge measurement that would happen anyway). Wall clock is measured and reported as
ms/fit and as the multiple of a plain edge measurement. If anything is swept for timing, rule 16
applies: alternate the sweep direction, take the per-setting minimum, quote a near-flat result as a
bound and not a value.

## 6. What will make this report wrong

- The two-sided `R` is not first-order resampler-free (N3 fires).
- The response is measured about the *measured* operating point, not the true one; if `L_meas` and
  `L_true` sit on opposite sides of a nonlinearity, `R` measured at `L_meas` is the wrong slope.
  **This is not testable within the milestone** and is recorded as a limitation, not a result.
- The correction is applied to scale only. If short edges also carry a translation bias, gate (c)
  cannot pass no matter how good `R` is.
- One deep stack. `coffee-bean` is the only 100-frame stack with a large shrinkage, so gate (a) and
  gate (c) rest on `n = 1` scene. `112MSDCF` is a placebo, not a replicate of the effect.
