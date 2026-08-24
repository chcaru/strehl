# M66 — the gate's tolerance is an N-dependent statement

**Verdict: the concern is CONFIRMED, and it is a function of the gate. At the
project's headline gate `T = 8` the effect is nil (`f_N(8√2) ≥ 0.99999` at every
`N` in [19, 299]) and the `5.4778x` result stands unqualified. At the shipped
default `T = 4.0` it is small but real — `1.0048x` in the iid null, `1.0577x`
through the real operator, `1.05x`–`4.01x` on real through-focus stacks. At the
tight gates `T = 0.5`–`2.0`, the ones every cross-stack diagnostic in this corpus
uses, a fixed `T` moves the admitted fraction by `1.68x`–`8.89x` across the
corpus's own N range. The shipped binary is not wrong. A class of published
*comparisons* is contaminated: M64's published **22.15x** cross-stack spread in
`n_eff/N` at gate 4.0 is reproduced here at 22.187x and falls to **6.210x** once
N is equalised — roughly 72% of it was frame count, not scene.**

Pre-registered at **`6e75b90`**, before any number in this report existed.
Every criterion is reported below as MET or NOT MET in the words it was written
in. Two of my six controls came back **NOT MET** and are reported as such, not
reworded. **No Rust was written. No file under `crates/` was modified.** The
corrected tolerance is named in section 8 and was deliberately **not built**.

Facts numbered locally from 1.

---

## 0. Prior work read before measuring (rule 40)

The search was `Select-String` over `docs/research/*.md` and `experiments/**` for
`DEFAULT_GATE`, `n_eff`, `--gate`, `gate`, `tolerance`. It returns 62 files in
`docs/research/` alone; `gate` is a common word here. The files I actually
**read**, and what I took from each:

| File | What I took, and did not re-derive |
|---|---|
| `docs/research/M64-estimator-default.md` | §1.1a — the adaptive `n_eff`-targeting gate is **refuted**; `foam` needs gate 21.9934 to reach `n_eff = 3`, off the 0.5–4.0 ladder, driving a 31.1 SD tolerance. §2.4 — the seven-stack corpus guard table at gate 4.0, which is my control K3's target. I did not re-open the adaptive-gate question. |
| `docs/research/M62-sqrt-n.md` (+ pre-reg `b94649c`) | §1 the burst's degeneracy; §3 the plant, ROI and constants; §6.2 the `5.4778x` / `0.7690x` separation and the gate ladder; §7 the negative controls; Requirement G (`n_eff/N < 0.95`), measured spread 0.014–0.301 against 1.000 on the burst. I reused M62's plant specification for arm B rather than inventing one. |
| `docs/research/M52-gate-cluster-verified.md` | The gate-transfer fact cluster and its Python harness. Its harness hardcodes `RN_HIGH = 1.47`, now stale against `profile.rs` (`read_noise_e_high: 1.2392`); I parse every constant from the crate at run time instead. |
| `docs/research/M65-election-gate-measured.md` | Read for overlap; it is a different gate question and I did not touch it. |
| `docs/research/M60c-speckle-citation-and-the-gate.md`, `M49-unapplied-findings.md`, `M38-merge-on-real-frames-measured.md`, `M57-detail-metric-from-first-principles.md`, `M4-fpn-measured.md` §8.1 | Background. M4 §8.1's dark temporal sigma is my loader control K4. |
| `crates/strehl-core/src/merge.rs`, `focus.rs`, `noise.rs`, `plane.rs`, `profile.rs` | The object under study, read rather than described. |

**Nothing in the corpus had measured this.** The nearest prior statement is the
doc comment on `DEFAULT_GATE` in `merge.rs`, written by M64, which already says
*"A fixed `threshold` is therefore an N-dependent statement."* M64 asserted the
mechanism and explicitly declined to measure it. This milestone measures it.

---

## 1. What the shipped code actually does — read, not assumed

**Fact 1 (MEASURED, source read).** The whole of the gate is four lines in
`crates/strehl-core/src/merge.rs`:

```rust
pub const FOCUS_NOISE_SD: f32 = 0.015_214;      // line 185
pub const DEFAULT_GATE: f32 = 4.0;              // line 297

pub fn tolerance(&self) -> f32 {                // line 310
    self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
}
pub fn admits(&self, focus: f32, best: f32) -> bool {   // line 319
    best - focus <= self.tolerance()
}
```

`best` is the maximum of the regularised focus response **over every folded
frame**. So the admission rule is exactly

```
admit frame k at pixel p  <=>  max_j X_j(p) - X_k(p) <= T * sqrt(2) * sigma_F
```

**Fact 2 (MEASURED).** `tolerance()` contains no `N` and no term that could carry
one. It is a product of a user scalar, `√2`, and a compile-time constant. The
response normalisation upstream (per-pixel sensor sigma, in `focus.rs`) is also
N-free — it divides by a per-pixel noise estimate that does not depend on how
many frames were loaded. **The "already handled, and here is why" resolution is
therefore not available on the code-reading route.** Nothing absorbs N.

**Fact 3 (MEASURED).** `mean_n_eff` is the mean over **all** plane pixels with no
interior inset, so the reported `n_eff` includes the border. My instrument
reproduces that choice exactly (control K3).

---

## 2. The mechanism, DERIVED

**Fact 4 (DERIVED).** Under the null in which every frame has the same true
focus at a pixel — the model the tolerance is written for, since `σ_F` is a
*noise* SD — write `X_k = mu + sigma_F * eps_k` with `eps_k` iid `N(0,1)`. Put
`t = T√2` in units of `sigma_F`. The expected number of admitted frames is

```
E[A_N(t)] = N * f_N(t),    f_N(t) = INTEGRAL phi(x) * Phi(x + t)^(N-1) dx
```

because frame `k` is admitted iff `eps_k + t >= eps_j` for all `j != k`, and the
`N-1` others are independent given `eps_k`.

**Fact 5 (DERIVED — the proof).** `f_N(t)` is **strictly decreasing in N** for
every finite `t`. For finite `x` and `t`, `Phi(x + t)` lies strictly in `(0, 1)`,
so `Phi(x+t)^N < Phi(x+t)^(N-1)` pointwise; `phi(x) > 0`; integrating a strict
pointwise inequality against a strictly positive weight preserves it. ∎

So the *fraction* admitted falls with N at fixed `T`, without exception, for any
gate short of infinite. The concern's mechanism is real as stated. What remains
is entirely a question of **size**.

**Fact 6 (DERIVED).** `f_N(0) = 1/N` exactly, so `N * f_N(0) = 1` for every N:
gate 0 admits exactly the winner. This is the exact anchor I used as a quadrature
control, and it is also what control K1 tests on real data.

---

## 3. Arm A — the analytic null

Adaptive Gauss quadrature in log-space, cross-checked at `t = 0` against the
exact `1/N` (worst absolute error **6.7e-16** across the whole grid) and against
a 2,000,000-draw Monte Carlo (agreement inside its standard error at every cell).

**Fact 7 (DERIVED).** Admitted fraction `f_N(T√2)` under the iid null:

| N | T=0.5 | T=1.0 | T=2.0 | T=4.0 | T=8.0 |
|---:|---:|---:|---:|---:|---:|
| 19 | 0.162758 | 0.362576 | 0.814091 | 0.999483 | 1.000000 |
| 22 | 0.146742 | 0.338953 | 0.798685 | 0.999405 | 1.000000 |
| 33 | 0.109712 | 0.279510 | 0.753778 | 0.999132 | 1.000000 |
| 63 | 0.068199 | 0.201854 | 0.676870 | 0.998461 | 1.000000 |
| 79 | 0.057573 | 0.179271 | 0.648977 | 0.998136 | 1.000000 |
| 100 | 0.048191 | 0.158053 | 0.619658 | 0.997734 | 1.000000 |
| 105 | 0.046441 | 0.153941 | 0.613571 | 0.997642 | 1.000000 |
| 120 | 0.041956 | 0.143152 | 0.596902 | 0.997374 | 1.000000 |
| 130 | 0.039470 | 0.137005 | 0.586912 | 0.997200 | 1.000000 |
| 299 | 0.020729 | 0.085551 | 0.484605 | 0.994722 | 1.000000 |
| **span over [19, 299]** | **7.85x** | **4.24x** | **1.68x** | **1.0048x** | **1.0000x** |

**Fact 8 (DERIVED).** `c_N = E[max of N standard normals]`, the quantity the
tolerance is implicitly racing: 19 → 1.84448, 22 → 1.90969, 30 → 2.04276,
33 → 2.08241, 63 → 2.33778, 79 → 2.42215, 100 → 2.50759, 105 → 2.52498,
120 → 2.57209, 130 → 2.59998, 200 → 2.74604, 299 → 2.87670. Over the corpus's
range `c_N` grows by **1.032 sigma_F**, against a gate-4 tolerance of
`4√2 = 5.657 sigma_F` — an **18%** erosion of the tolerance's headroom, which is
exactly why the effect is tiny at T=4 and enormous at T=0.5.

**This is the single sentence that resolves the shape of the answer.** The gate
is a race between a fixed tolerance `T√2` and a reference that drifts by `c_N`.
When `T√2 >> c_N - c_19` the drift is invisible; when `T√2` is comparable to it,
the drift *is* the gate.

---

## 4. Arm B — the real operator on a synthetic static burst

The pure null, run through the shipped algorithm rather than through my algebra.
Plant per M62 §3: `D:\personal\macro\109MSDCF\DSC00020.ARW`, 2048² RGGB crop at
`(y=1024, x=4096)`, ISO 160, N = 299 synthetic frames, two seeds. Model pooled sd
**18.7002 DN** against empirical first frames 18.6772–18.7036 DN.

**Fact 9 (MEASURED).** The regularised response's own temporal SD on this plant
is **not** `FOCUS_NOISE_SD`. Mean 0.018446, median 0.018739, p05 0.014232,
p95 0.021563, against the crate constant 0.015214 — a ratio
**rho = 1.2124** (seed 0), **1.2122** (seed 1). The distribution across pixels
spans **0.94x to 1.42x** of the crate constant.

**Fact 10 (MEASURED, control K7).** rho is a property of *scene content*, not of
my pipeline. Three latents through the identical code:

| latent | response SD mean | rho = mean / 0.015214 |
|---|---:|---:|
| FLAT (constant DN) | 0.015242 | **1.0018** |
| SMOOTH (low-pass of the real crop) | 0.016263 | 1.0690 |
| REAL (the crop) | 0.018137 | 1.1921 |

**K7 PASS** — criterion was `|rho - 1| <= 0.05` on FLAT; measured 1.0018. So
`FOCUS_NOISE_SD` is correctly calibrated **on a flat field** and runs about
**19–21% low on real texture**. The effective tolerance a user gets at gate `T`
on textured content is `T√2 / rho`, i.e. gate 4.0 buys **4.67 sigma**, not 5.66.
This is an *orthogonal* finding to N-dependence and is flagged again in §8.

**Fact 11 (MEASURED).** Admitted fraction (= `n_eff/N`), stride subsets, seed 0:

| N | T=0.5 | T=1.0 | T=2.0 | T=4.0 | T=8.0 |
|---:|---:|---:|---:|---:|---:|
| 19 | 0.139013 | 0.288120 | 0.679550 | 0.989429 | 0.999998 |
| 33 | 0.092269 | 0.215728 | 0.600548 | 0.984072 | 1.000000 |
| 63 | 0.054959 | 0.146711 | 0.504535 | 0.973307 | 0.999998 |
| 105 | 0.036175 | 0.106590 | 0.433282 | 0.963034 | 0.999998 |
| 299 | 0.015635 | 0.056161 | 0.313817 | 0.935481 | 0.999994 |
| **span over [19, 299]** | **8.89x** | **5.13x** | **2.17x** | **1.0577x** | **1.0000x** |

Seed 1 reproduces every cell to within 0.006 absolute.

**Fact 12 (MEASURED, control K6 PASS).** Arm B declines *faster* than arm A, and
rho explains most of it. Comparing arm B against `f_N(T√2)` and against
`f_N(T√2 / rho)`:

| N | T | arm B | arm A raw | arm A /rho | B − A raw | B − A /rho |
|---:|---:|---:|---:|---:|---:|---:|
| 19 | 0.5 | 0.139013 | 0.162758 | 0.138858 | −0.023745 | **+0.000155** |
| 299 | 0.5 | 0.015635 | 0.020729 | 0.015889 | −0.005094 | **−0.000253** |
| 19 | 1.0 | 0.288120 | 0.362576 | 0.289602 | −0.074456 | −0.001482 |
| 299 | 1.0 | 0.056161 | 0.085551 | 0.056556 | −0.029390 | −0.000395 |
| 105 | 2.0 | 0.433282 | 0.613571 | 0.447943 | −0.180289 | −0.014661 |
| 299 | 4.0 | 0.935481 | 0.994722 | 0.958435 | −0.059240 | −0.022953 |

A single scalar `rho` reconciles the real operator to the algebra to better than
**0.3% of the fraction** at `T <= 1.0`, but leaves up to **2.3 points** at
`T = 4.0, N = 299`. **ARGUED:** no single scalar can close that residual, because
a T=4 gate is probing the *tail* of the max, and the per-pixel response SD is
heterogeneous (p05 0.0142, p95 0.0216) — the tail is set by the upper end of that
distribution, not its mean. I did not measure a per-pixel-sigma version of arm A
that would test this.

K6 required arm B to show a span `>= 1.05` somewhere on the ladder, or the
instrument has no power to detect what arm A predicts. Best span **8.8909x**.
**K6 PASS.**

---

## 5. Arm C — real through-focus stacks, N varied three ways

Eight stacks decoded to regularised focus cubes (720 ARW frames), N varied by
**prefix** (first K frames — truncates the depth range), **stride** (evenly
spaced — preserves the depth range, coarsens the sampling), and **random**
(8 draws per cell). The pre-registered primary mode is **stride**; prefix and
random are reported beside it.

**Choice of stack, justified.** M62 §1 establishes that a static burst is
degenerate for focus — every frame is in focus, so `n_eff/N` → 1 and the merge
stops discriminating. That degeneracy is exactly why the burst is the **right**
instrument for arm B (it *is* the null the tolerance is written for, and it is
the only way to observe the pure winner's-curse mechanism uncontaminated) and
exactly why it is the **wrong** instrument for arm C (it cannot show what the
effect does to a real stack, where `best` also rises because denser depth
sampling resolves the focus peak better). I ran both, deliberately, and I do not
mix their conclusions.

**Fact 13 (MEASURED).** Span of `n_eff/N` over `N >= 19`, sign of the change from
lowest to highest N (all signs are negative — the fraction falls as N rises — in
every stack, every mode, every gate):

| stack | N range | mode | T=0.5 | T=1.0 | T=2.0 | T=4.0 | T=8.0 |
|---|---|---|---:|---:|---:|---:|---:|
| 109MSDCF | 19..22 | prefix | 1.1577 | 1.1578 | 1.1574 | 1.1517 | 1.1149 |
| 109MSDCF | 19..22 | **stride** | 1.1410 | 1.1225 | 1.0870 | **1.0469** | 1.0090 |
| 109MSDCF | 19..22 | random | 1.1249 | 1.0982 | 1.0625 | 1.0302 | 1.0265 |
| 119MSDCF | 19..33 | **stride** | 1.5204 | 1.3658 | 1.1854 | **1.0720** | 1.0399 |
| 113MSDCF | 19..63 | **stride** | 2.7428 | 2.2347 | 1.5608 | **1.2048** | 1.1017 |
| 112MSDCF | 19..79 | **stride** | 3.2637 | 2.5422 | 1.6555 | **1.2171** | 1.1074 |
| foam | 19..100 | **stride** | 5.0686 | 4.8849 | 4.5529 | **4.0122** | 3.2687 |
| coffee-bean | 19..105 | **stride** | 4.3607 | 3.1201 | 1.7375 | **1.1229** | 1.0882 |
| bee-1 | 19..299 | **stride** | 9.6211 | 5.6078 | 2.3283 | **1.2176** | 1.1369 |
| coffee-bubbles | 19..19 | — | — | — | — | — | — |

Prefix spans are far larger (foam 22.24x at T=4, 112MSDCF 4.63x) because prefix
also truncates depth range; that is the confound the three modes exist to expose,
and stride/random bracket the honest number.

**Fact 14 (MEASURED, rule 39 — `n_eff` beside every gate, stride mode):**

| stack | N | T=0 | T=0.5 | T=1.0 | T=2.0 | T=4.0 | T=8.0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 109MSDCF | 19 | 1.0000 | 1.3924 | 1.8265 | 2.7130 | 4.5085 | 9.1247 |
| 109MSDCF | 22 | 1.0000 | 1.4130 | 1.8840 | 2.8900 | 4.9865 | 10.4713 |
| coffee-bubbles | 19 | 1.0000 | 1.2381 | 1.5041 | 2.1097 | 3.5297 | 6.4737 |
| 119MSDCF | 33 | 1.0000 | 1.3990 | 1.8553 | 2.8472 | 4.7238 | 8.1902 |
| 113MSDCF | 63 | 1.0000 | 1.4317 | 2.1936 | 4.7617 | 8.5902 | 12.2127 |
| 112MSDCF | 79 | 1.0000 | 1.5502 | 2.5610 | 6.1921 | 12.0499 | 17.5463 |
| foam | 100 | 1.0000 | 1.0428 | 1.0867 | 1.1762 | 1.3583 | 1.7266 |
| coffee-bean | 105 | 1.0000 | 1.8701 | 4.0732 | 14.3884 | 31.6436 | 34.2174 |
| **bee-1** | **299** | 1.0000 | 2.2941 | 5.8595 | 26.1182 | **70.2012** | 85.5176 |
| bee-1 | 105 | 1.0000 | 1.8502 | 3.8713 | 12.6485 | 25.8280 | 30.5833 |
| bee-1 | 19 | 1.0000 | 1.4025 | 2.0880 | 3.8642 | 5.4318 | 6.1780 |

**`bee-1` is new to this corpus.** At its own N = 299 and the shipped gate 4.0 it
gives mean `n_eff` **70.2012**, `n_eff/N` **0.23479**. M64's §2.4 table stops at
seven stacks and does not contain it.

**Fact 15 (MEASURED, the standard error).** Between-subset SD over 8 random draws
at gate 4.0, worst `SD/mean` over every `(stack, N)` with `N >= 19`:
**0.00377** (109MSDCF at N=19; foam 0.00316, 119MSDCF 0.00316, bee-1 0.00294).
Over the whole grid including `N = 3` it reaches 0.09150 (coffee-bubbles, N=3),
which is why I restrict the criteria to `N >= 19` as pre-registered. **Every span
in fact 13 exceeds the N ≥ 19 SE by two to three orders of magnitude.**
Subset-draw noise cannot produce them.

---

## 6. Controls — including the two that failed

Reported first, and in the words they were written in.

**K1 — NOT MET as pre-registered.** Gate 0 must give mean `n_eff` exactly
1.000000. Measured 1.000000 to 1.0000058 across the grid; 17 of 40 cells exceed
1.0. Worst excess **5.824e-06**. **Diagnosis (post-hoc, K1′):** `admits` uses
`<=`, and the crate's own unit test asserts `gate.admits(1.0, 1.0)`. Exact `f32`
ties between two frames' responses are admitted **by design**. Counting ties
directly: 0–3 tied pixels out of 515,094, which accounts for the excess exactly.
The criterion is not met; the instrument is not wrong; the criterion was written
without accounting for a documented `<=`.

**K2 — NOT MET as pre-registered.** Gate 1000 was pre-registered as "far beyond
the attainable range" and so must give `n_eff/N = 1.000000`. It does not. Gate
1000 is a tolerance of 21.51 response units, and the **measured maximum
frame-to-frame response gap** reaches: 109MSDCF 11.96, 112MSDCF 12.73,
113MSDCF 17.28, 119MSDCF 25.82, coffee-bubbles 40.60, coffee-bean 67.61,
foam 73.48, **bee-1 120.37**. Measured `n_eff/N` at gate 1000: coffee-bean
**0.845746**, foam 0.966800, bee-1 0.988388. My premise was simply false.
**K2′ (post-hoc)** repeats at gate 1e5 (tolerance 2151) and returns 1.000000 on
all eight stacks. **K2′ PASS.**

That the response range reaches 120 units on `bee-1` is itself worth recording:
the gate ladder in use (0.5–8.0, i.e. tolerances 0.011–0.172 response units)
occupies a vanishing fraction of the attainable range.

**K3 — PASS.** My Python instrument against M64 §2.4's *shipped-binary* mean
`n_eff` at gate 4.0, all seven stacks M64 measured:

| stack | mine | M64 | ratio |
|---|---:|---:|---:|
| foam | 1.3583 | 1.3590 | 0.9995 |
| 113MSDCF | 8.5902 | 8.5810 | 1.0011 |
| 119MSDCF | 4.7238 | 4.7230 | 1.0002 |
| 112MSDCF | 12.0499 | 12.0370 | 1.0011 |
| coffee-bubbles | 3.5297 | 3.5290 | 1.0002 |
| 109MSDCF | 4.9865 | 4.9870 | 0.9999 |
| coffee-bean | 31.6436 | 31.6140 | 1.0009 |

Maximum deviation **0.11%**. The instrument is the shipped rule.

**K4 — PASS.** My raw loader reproduces M4 §8.1's dark-frame temporal sigma to
**0.01%**.

**K5 — PASS.** 4x decimation against full resolution, every gate, two stacks:
maximum deviation **0.041%** (109MSDCF gate 8.0, ratio 1.00023). Decimation does
not move the statistic.

**K6 — PASS** (fact 12). **K7 — PASS** (fact 10, post-hoc).

---

## 7. The pre-registered criteria, decided

### E-criteria

Pre-registration §5: E-ABSENT required `S(stack, 4.0) <= 1.05` on **every**
arm-C stack in **all three** modes.

**Fact 16 (MEASURED). Corpus verdict at `T = 4.0`: E-PRESENT.** Seven of eight
stacks exceed 1.05 at gate 4.0 in a mode whose sibling modes agree in direction;
all three modes agree in direction (negative) on every stack and every gate, so
**E-CONFOUNDED does not trigger**. `109MSDCF`'s primary (stride) span is
**1.0469**, below 1.05 — but its prefix span is 1.1517 with sibling agreement, so
it is E-PRESENT by the letter of the rule; its N range is only 19..22, so it has
almost no lever to pull.

**`coffee-bubbles` is UNDETERMINED, not E-PRESENT.** Its `N_max` is 19, the floor
of the restricted range, so it contributes exactly one point and has no span.
My `06-blast.py` classifier binned a `NaN` span into E-PRESENT; that is a script
artifact and I am correcting it here rather than letting it stand. The corpus
verdict does not rest on it.

### Materiality ladder

**Fact 17. M-HEADLINE — MET.** Criterion: `f_N(8√2) >= 0.999` for every
`N ∈ [19, 299]`. Arm A gives **1.00000000** at every corpus N. Arm B's minimum
admitted fraction at `T = 8` over the same range is **0.99999443**. **M62's
`5.4778x` at `--gate 8` on N = 30 is not an N-specific statement.** At gate 8 the
tolerance is `11.31 sigma_F` against a `c_N` drift of `1.03 sigma_F`; the gate
admits essentially every frame at every N in the corpus range, which is precisely
the degeneracy M62 identified and *wanted* for the acceptance test. **The
project's headline survives this milestone intact.**

**Fact 18. M-DEFAULT — arm A MET, arm B NOT MET.** Criterion: span `<= 1.05` over
`N ∈ [19, 299]`. Arm A (iid null) **1.0048 — MET**. Arm B (real operator, real
texture, still the pure null) **1.0577 — NOT MET**, by 0.7 percentage points of
the threshold. The difference between the two is `rho`: the effective tolerance
is `4√2 / 1.2124 = 4.666 sigma`, not 5.657.

So `DEFAULT_GATE = 4.0` is portable in the model and marginally non-portable in
reality. On real through-focus stacks the stride spans run **1.0469 to 4.0122**,
but that number mixes two mechanisms and is not attributable to this one (§9).

**Fact 19. M-GUARD — NOT MET.** Criterion as written: *"The guard fails iff any
measured `(stack, N)` at gate 4.0 reaches `n_eff/N >= 0.95`."* It does.
`112MSDCF` prefix at N=3 gives **0.99850**; `bee-1` prefix at N=3 gives 0.96740;
`113MSDCF` prefix at N=5 gives 0.95300. **NOT MET.**

I will not reword it. I will say what it means. Those three cells are all
**prefix subsets at N ≤ 5** — three consecutive frames of a through-focus stack
sit at nearly the same depth, so they *are* a static burst, and M62's Requirement
G correctly reports them as focus-degenerate. Restricted to the corpus's real
range:

**Fact 20 (MEASURED). Requirement G margin, `N >= 19`, gate 4.0:**

| stack | worst `n_eff/N` (N ≥ 19, any mode) | margin | at own N (stride) | margin |
|---|---:|---:|---:|---:|
| bee-1 | **0.84972** | **1.12x** | 0.23479 | 4.05x |
| 112MSDCF | 0.70590 | 1.35x | 0.15253 | 6.23x |
| coffee-bean | 0.54279 | 1.75x | 0.30137 | 3.15x |
| 113MSDCF | 0.49386 | 1.92x | 0.13635 | 6.97x |
| foam | 0.30207 | 3.15x | 0.01358 | 69.94x |
| 109MSDCF | 0.26105 | 3.64x | 0.22666 | 4.19x |
| 119MSDCF | 0.23863 | 3.98x | 0.14314 | 6.64x |
| coffee-bubbles | 0.18577 | 5.11x | 0.18577 | 5.11x |

**The guard holds everywhere at `N >= 19`, but its margin is a function of N.**
M64 reported a worst case of 0.3011 and a 3.16x margin. On the same corpus at the
corpus's own smallest N, the worst is **0.84972 — a 1.12x margin**, on `bee-1`,
a stack M64 did not measure. That is not a failure; it is a guard whose stated
safety factor is 2.8x smaller than published once N is allowed to vary. Nothing
in the guard's statement mentions N.

---

## 8. The blast radius, and the corrected tolerance (named, NOT built)

**Fact 21 (MEASURED) — the contaminated class, and the specific published number
it hits.** The material damage is not to any single shipped image. It is to
**cross-stack comparison at a fixed gate**. Comparing the same eight stacks at
each one's own N versus all of them at a common N = 19 (stride, so the depth
range is preserved in both):

| gate | spread of `n_eff/N` across stacks at own N | at common N = 19 | how much of it was N |
|---:|---:|---:|---:|
| 1.0 | **7.881x** | 2.280x | 3.46x |
| 2.0 | **11.651x** | 4.446x | 2.62x |
| 4.0 | **22.187x** | 6.210x | 3.57x |

**M64 published exactly this number.** M64 §2.4 records *"`n_eff/N` spans 22.15x
at a fixed gate — 0.0136 on `foam` to 0.3011 on `coffee-bean`"* and repeats it in
its fold. I reproduce it independently at **22.187x** (foam 0.01358,
coffee-bean 0.30137 — agreement to 0.2%, a K3-grade match). **At a common
N = 19 the same eight stacks span 6.210x.** So roughly **72% of that headline
spread is frame count, not scene**, and `foam` — the stack the spread's low end
rests on — is the single most N-sensitive stack in the corpus.

Per stack, the ratio `n_eff/N(own N) / n_eff/N(N=19)` at gate 4.0: 109MSDCF
0.955, coffee-bubbles 1.000, 119MSDCF 0.933, 113MSDCF 0.830, 112MSDCF 0.822,
coffee-bean 0.891, bee-1 0.821, **foam 0.249**.

**Any statement of the form "stack A admits X times more than stack B at gate G"
in this corpus is part scene and part frame count, and the two were never
separated.** M52-class gate-transfer numbers and M64 §2.4's guard table are all
tabulated at each stack's own N. They are correct as descriptions of those stacks
**as shipped** — nothing in them is wrong about what the binary does — but they
are not clean scene comparisons and were not recorded as N-conditional.

**Fact 22 (DERIVED) — what the corrected tolerance would be.** The measurement
selects **candidate (ii), fixed null admission rate**, from the set fixed in
pre-registration §6:

```
tau_N(alpha) = q_{1-alpha}(N) * sigma_F,   where  INTEGRAL phi(x) Phi(x+q)^(N-1) dx = 1 - alpha
```

It is invariant in N **by construction** under the null the tolerance is written
for, which is the property fact 5 proves the status quo cannot have. Candidate
(iii) (selection-offset anchor, `tau_N = (T√2 + c_N − c_{N0}) sigma_F`) is
numerically almost identical and is easier to explain; candidate (iv) (shrink the
winner) moves the same quantity but changes the *estimate*, not just the
admission set, and is a larger behavioural change than this evidence justifies.

Priced against a declared anchor `N0 = 30` (M62's burst), the equivalent gate at
each corpus N:

| N | (ii) `T_equiv` at `T=4` | (ii)/T | (iii) `T_equiv` | (iii)/T | fixed-`T` null rate |
|---:|---:|---:|---:|---:|---:|
| 19 | 3.8929 | 0.9732 | 3.8598 | 0.9649 | 0.999483 |
| 33 | 4.0217 | 1.0054 | 4.0280 | 1.0070 | 0.999132 |
| 63 | 4.1636 | 1.0409 | 4.2086 | 1.0522 | 0.998461 |
| 105 | 4.2704 | 1.0676 | 4.3410 | 1.0852 | 0.997642 |
| 130 | 4.3139 | 1.0785 | 4.3940 | 1.0985 | 0.997200 |
| 299 | 4.4774 | 1.1194 | 4.5897 | 1.1474 | 0.994722 |

At `T = 2` the correction is much larger (0.930x at N=19 to **1.289x** at
N=299). **The correction a user would notice is at the tight gates, not at the
default.**

**Fact 23 (ARGUED) — a fifth candidate, found post hoc and flagged as such.**
K7 (fact 10) shows `FOCUS_NOISE_SD` is a flat-field constant running **19–21%
low on real texture**, with per-pixel spread 0.94x–1.42x. Candidate (ii) would
equalise the *modelled* null admission rate across N while leaving that scale
error untouched. A per-pixel measured response SD would fix a larger error than
the one this milestone was chartered to find. **It was not in my pre-registered
candidate set, I am naming it post hoc, and it is not mine to rule on.**

**None of this was implemented. `crates/` is untouched.** `git show --name-only`
on this milestone's commits contains no path under `crates/`. Because no Rust
changed, `cargo fmt` / `clippy` / `test` / `doc` were not run and are not
required; there is no Rust diff for them to check.

---

## 9. What I did not measure, and where this is circular

**Not measured (measurable, I did not do it):**

1. **Whether the admitted set is *right*.** Every number here is about how many
   frames are admitted, never about whether the admitted ones are the in-focus
   ones. A gate could be perfectly N-invariant and admit the wrong frames.
2. **The price in output quality.** No sharpness, noise or detail metric was
   computed on any merged image. I did not run M62's acceptance battery.
3. **A real static burst.** Arm B's burst is synthesised from one real frame plus
   the calibrated sensor model. M62's own burst exists; I did not re-run it.
4. **N > 299 and N < 3.** The corpus ends at 299.
5. **Alignment.** The merge does not align (confirmed: no register/align path in
   `merge_cmd.rs`), so neither does my instrument. If alignment is ever added,
   every number here is about the pre-alignment operator.
6. **Colour planes other than the one the plane loader returns**, and the border
   region is included exactly as `mean_n_eff` includes it.
7. **A per-pixel-sigma version of arm A**, which is what fact 12's residual asks
   for.

**Not measurable by this design (a real distinction, not an excuse):**

8. **Arm C cannot separate the two mechanisms that both raise `best` with N.**
   One is the winner's curse in *noise* — the thing a `sigma_F`-denominated
   tolerance is meant to handle, and the only thing arms A and B contain. The
   other is that denser depth sampling *genuinely finds a sharper frame*, raising
   the true maximum focus. Subsetting a fixed capture cannot hold the second
   constant while varying the first, because varying N **is** varying the depth
   sampling. Arm C's within-stack decline at gate 4.0 (coffee-bean 1.1229 over
   19→105) is about **4x** arm B's pure-noise prediction over the same span
   (0.98943 → 0.96303 = 1.0274). The remainder is real optics, not a defect.
   Separating them needs a capture in which N varies at fixed depth sampling —
   i.e. repeated frames per depth — which this corpus does not contain.
   **Therefore: arm C establishes the *direction and the corpus-wide presence*;
   arms A and B establish the *size attributable to the mechanism under study*.
   Arm C's spans must not be read as the size of the noise effect.**

**Circular with its own calibration (declared in pre-registration §7):**
`FOCUS_NOISE_SD` sets both the tolerance (numerator) and, in arm B, the scale of
the synthetic plant's response (denominator). If that constant is wrong, arms A
and B are wrong **in the same direction** and K6 could not detect it. K7 partly
breaks this — it measures the response SD *empirically* against the constant and
finds a 19% discrepancy on real content — but K7's own plant is built with the
same sensor model, so the sensor model itself remains unaudited by this
milestone. M4, M48 and M61 are the authorities there, not me.

---

## 10. Reproduction

```
$env:PYTHONIOENCODING='utf-8'
cd projects\strehl\experiments\M66-gate-n-dependence
python src\00-analytic.py      # arm A         -> out/00-analytic.json
python src\01-loader.py        # K4            -> out/01-loader.json
python src\02-fields.py        # decode cubes  -> data/*.npy  (~2.8 GB, gitignored)
python src\03-controls.py      # K1 K1' K2 K2' K3 K5
python src\04-burst.py         # arm B         -> out/04-burst.json
python src\05-sweep.py         # arm C         -> out/05-sweep.json
python src\07-response-sd.py   # K7            -> out/07-response-sd.json
python src\06-blast.py         # criteria      -> out/06-blast.json
python src\08-guard.py         # guard + rule 39 tables
```

All constants (`FOCUS_NOISE_SD`, gain, read noise, black/white levels) are parsed
from `crates/` at run time rather than transcribed, so the instrument cannot
drift from the crate silently. Nothing writes to `D:\personal\macro`,
`D:\macro-dark-frames` or `C:\dev\macro`.

---

## 11. Summary for the orchestrator

- The mechanism is **real and proved** (fact 5), and **nothing in the shipped
  `tolerance()` absorbs N** (fact 2).
- **The headline is safe.** `--gate 8` is N-invariant to 5 decimal places across
  [19, 299]. M-HEADLINE **MET**.
- **The default is marginal.** M-DEFAULT **MET** in the iid null (1.0048),
  **NOT MET** through the real operator (1.0577).
- **The guard's criterion as written is NOT MET** (0.99850 at `112MSDCF` N=3
  prefix), holds everywhere at `N >= 19`, but its published 3.16x margin becomes
  **1.12x** on `bee-1` at N=19.
- **The real damage is to comparisons, not to any shipped output.** M64's
  published **22.15x** cross-stack spread in `n_eff/N` at gate 4.0 is reproduced
  here at **22.187x**, and falls to **6.210x** when N is equalised —
  **~72% of it was frame count, not scene.**
- **Tight-gate numbers are the contaminated ones**: a fixed `T` between 0.5 and
  2.0 moves the admitted fraction **1.68x–8.89x** across the corpus's N range.
- The corrected form is **candidate (ii)**, priced in fact 22, and **was not
  built**.
- K7 found something bigger and orthogonal: **`FOCUS_NOISE_SD` is a flat-field
  constant and runs 19–21% low on real texture.** Flagged post hoc; not mine to
  rule on.
- New corpus number: **`bee-1`, N = 299, gate 4.0, mean `n_eff` 70.2012,
  `n_eff/N` 0.23479.**
