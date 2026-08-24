# M90 — PRNU in the noise model: the correction, and what it breaks

## 1. Verdict

**Flip the default in two pieces, not one.** The κ term and the gain correction have
completely different blast radii and must not be shipped together.

**κ alone is free.** Adding `+ (κ·S)²` at `Estimator::predicted_sigma` moved **zero
selection decisions** — 0.0000% of frames, on six real stacks spanning ISO 50–1000 and
22–60 frames, in every signal octave (§5.2). It is a pure *reporting* change. Fact 1063's
ruling — that the term belongs at `predicted_sigma` and nowhere else — is not merely
argued in this milestone, it is **measured in the output**.

**The gain correction is not free.** It moves `n_eff` by 0.38%–14.72% across the six
stacks, but moves the merge's election winner on only **0.0006%–0.0073% of pixels**. So
the *published images* survive a flip; the *published confidences* do not.

**The defect is substantially larger than fact 1064 records.** Single-frame residual is
**−11.45% at S = 8000** (1064 says −12.8%, close) but continues to **−16.90% at
S = 13230 DN**, the top of the measured range. Worse, the *merged* over-confidence is far
larger than the single-frame figure, because `predicted_sigma` divides by `√n_eff` while
PRNU does not average down: on the coffee-bean stack the bright octave (58.69% of the
frame) is over-confident by **+285.71%**, not 12.8%.

**And the term that dominates that number is unmeasured.** `rho_warp` — the inter-frame
correlation of the fixed pattern after warping — is a **30.8× lever** on the merged σ at
`n_eff` = 44, and the project has never measured it (§5.4, P7). **This is now the highest-value
measurement available.** Deliverable A ships default-off and byte-identical (§7), so
nothing has to be decided tonight.

> **AMENDED BY ROUND 2 — read §R2 before reusing anything in this paragraph.** `rho_warp`
> is now **measured** (§R2.1). It is not a constant but a decaying function of frame
> separation, and **round 1's `rho_warp` = 1 is retracted**: it overstates merged PRNU σ by
> **3.3×**. The +285.71% in the paragraph above is quoted at `rho` = 1; the measured value
> is **+19.04%**. The 30.8× lever survives as a *bound*, but the realised lever is **4.4×**.

**One corpus number is contradicted.** Fact 1065 says the shipped profile gain is 2.16%
high. My independent measurement says **3.42%** high (§2.2). This milestone's measurement
disagrees with M71's by 3.6× M71's own quoted 1σ and **the disagreement is not resolved**
(failed bar PR-5a, §8.2).

---

## 2. The four residual curves

### 2.1 The non-circularity problem, and how it was solved

Arm (iv) — "gain fixed and κ added" — is *true by construction* if it is scored against
M71's own constants, because those constants were fitted to make it true. Any residual
curve built that way measures nothing.

So M90 measured `g` and `κ` **independently**, from raw ARW, with an estimator that shares
no code and no intermediate with M71:

- **`g` from a temporal photon-transfer curve.** For each matched exposure pair, the
  variance of the *difference* of two frames at the same illumination cancels the fixed
  pattern exactly (it is common to both frames), leaving `2·(g·S + read²)`. Regressing
  `v_single` on `S` gives `g` as the slope. **This estimator is structurally blind to κ**
  — verified in §8.4, where a 10× change in planted κ moves the recovered `g` by 0.01%.
- **`κ` from the high-pass residual of the mean of the pair**, with the temporal term
  subtracted using the `g` just measured.
- **Both scored against `v_single`**, the measured temporal variance, never against a model.

360 ARW flats, 58 exposure groups, 86 usable signal levels, 257–13230 DN.

### 2.2 The independent constants (MEASURED)

| quantity | M90 | M71 | delta |
| --- | --- | --- | --- |
| `g` green, ISO 100 (DN/e⁻) | **0.221113 ± 0.000142** | 0.224103 | **−1.33%** |
| `g` vs shipped 0.228938 | **−3.42%** | −2.16% | contradicts fact 1065 |
| `κ` per-level mean (n = 76) | **0.3096% ± 0.0146%** | 0.3096% ± 0.0159% | **0.00%** |
| `κ` S²-weighted fit | 0.2911% | — | −6.0% |

**κ replicates to four significant figures** against a from-scratch estimator on a
different flat selection. That is the strongest single result in this milestone: fact
1062 is confirmed, not merely re-quoted.

**`g` does not replicate.** −1.33% is 3.6× M71's quoted 1σ. Both measurements agree the
shipped gain is too high; they disagree on whether it is 2.16% or 3.42% too high. This is
a **failed bar**, reported in §8.2, not smoothed over.

### 2.3 The curves

Residual is `σ_model / σ_measured − 1`, per green photosite (G1), against the measured
temporal σ from §2.1. Negative = **over-confident** (model claims less noise than exists).

| S (DN) | σ_meas | (i) shipped | (ii) gain-only | (iii) prnu-only | (iv) both |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 257 | 7.495 | +3.15% | +2.07% | +3.70% | +2.62% |
| 326 | 8.472 | +2.63% | +1.55% | +3.32% | +2.25% |
| 772 | 13.259 | +0.51% | −0.55% | +2.12% | +1.07% |
| 856 | 13.984 | +0.34% | −0.72% | +2.12% | +1.07% |
| 956 | 14.838 | **−0.09%** | −1.14% | +1.88% | +0.85% |
| 1009 | 15.301 | −0.47% | −1.52% | +1.60% | +0.57% |
| 1363 | 17.932 | −1.36% | −2.40% | +1.41% | +0.39% |
| 2190 | 23.061 | −2.82% | −3.85% | +1.53% | +0.55% |
| 2671 | 25.738 | −3.85% | −4.87% | +1.37% | +0.41% |
| 4364 | 33.799 | −6.44% | −7.43% | +1.74% | +0.83% |
| 5344 | 38.041 | −8.02% | −9.00% | +1.74% | +0.86% |
| 6957 | 44.526 | −10.35% | −11.30% | +1.87% | +1.03% |
| 8058 | 48.513 | **−11.45%** | −12.39% | +2.40% | +1.59% |
| 11148 | 59.425 | −14.97% | −15.87% | +2.97% | +2.23% |
| 12472 | 63.731 | −16.14% | −17.03% | +3.46% | +2.74% |
| 13230 | 66.239 | **−16.90%** | −17.78% | +3.58% | +2.88% |

Scores over all 86 levels:

| arm | RMS | worst | median |
| --- | ---: | ---: | ---: |
| (i) shipped | 8.22% | 17.10% | −3.45% |
| (ii) gain-only | **8.89%** | **17.98%** | −4.48% |
| (iii) prnu-only | 2.28% | 3.91% | +1.93% |
| (iv) both | **1.46%** | **2.88%** | +0.97% |

**Arm (iv) wins on every score — RMS, worst case and median.** The brief warned this might
not hold; it does.

**Arm (ii) is worse than shipping nothing.** Fixing only the gain makes the model *worse*
on RMS, on worst case and on median. The brief's warning that "fixing only one of the two
makes the model worse over part of its range" is confirmed, and it is stronger than that:
gain-only is worse over **the whole measured range**, because the gain error and the κ
omission push σ in the *same* direction above ≈770 DN and the gain fix removes the only
thing holding the residual up.

**A partial correction is therefore not safe in general, but κ-only is.** Arm (iii) is a
uniform improvement (RMS 2.28% vs 8.22%) and its residual is **positive everywhere** — it
never makes the model over-confident at any measured level. That is the M68 criterion
M71 §8.3 invoked, and κ-only satisfies it.

### 2.4 Two different crossovers, and they are different objects

Fact 1064's 504 DN is the point where *shipped* and *corrected* **models** cross — where
the 2.16%-high gain and the absent κ cancel each other. M90 reproduces it at
**≈460–520 DN**, confirming 1064's arithmetic.

But the crossover that matters operationally is where the shipped model crosses
**reality** — where the residual changes sign. That is at **≈945 DN**, measured
(the sign flips between 856 DN at +0.34% and 956 DN at −0.09%). This is a **new object**
not previously in the corpus, and it is the number a reader wants: *below ~945 DN the
shipped model is conservative, above it the model is over-confident.*

The two differ because the gain error is 3.42% not 2.16% (§2.2), which moves the
model-vs-reality crossing up.

### 2.5 A correction to M71 §8.3

M71 §8.3 quotes the κ-inflation of *luma* σ at a given signal, but compares it against a
**per-photosite** signal level. The luma-domain inflation at luma value `L` equals the
photosite-domain inflation at `S = L`, not at `S = 2L` — the demosaic averages the two
green sites, which halves the *variance* of the temporal part but leaves the fixed-pattern
part correlated. The consequence: **M71's 1009 DN reads as 504 DN in the photosite domain
where `PlaneNoise` operates.** Encoded as the test
`the_luma_inflation_equals_the_photosite_inflation_at_the_same_dn` in `noise.rs`.

This is a bookkeeping correction to a boundary number, not to κ.

### 2.6 M71 §8.1's per-plane table is not internally inconsistent

M71 §8.1 tabulates R 0.3102%, green 0.3096%, B 0.2528% and states B is "0.823× green".
But 0.2528 / 0.3096 = 0.8165, not 0.823. Reading M71's **primary JSON** rather than its
prose resolves this:

- the green headline 0.3096% comes from `05-kappa.json`, a matched-pair split-half estimator;
- R and B come from `10-rb.json`, a **different** estimator whose own green figure is
  0.3072% (G1 0.30525%, G2 0.30916%);
- within `10-rb.json`, B / green = **0.82303** ✓.

So the ratio is right and the table is right; it juxtaposes two estimators that disagree
about green by **0.78%**. That 0.78% is a real, unremarked estimator-dependence in κ and
it is comparable to M71's own quoted uncertainty. Recorded as P12.

---

## 3. Does adding κ double-count what M70 already absorbed? — **No**

Fact 1102 says κ accounts for 25.12% of M70's unruled flat-residual floor, leaving 74.88%
unruled. If M70's absorbed portion were live in a shipped code path as a level-dependent
multiplicative variance term, adding κ would double-count that 25.12%.

**Pre-registered decision rule (PR-10, registered before looking):** double counting
occurs **iff** a shipped code path carries a level-dependent multiplicative variance term.

**Measured answer: it does not.**

- `PlaneNoise::variance` is exactly `g·S + (RN_e·g)²`. No multiplicative term.
- The strings `e_flat`, `flat_residual` and the constant `1.83` appear **zero times**
  under `crates/*/src/`.
- `flat_ratio::frame_flat` is a *frame-admission diagnostic*. It never feeds `variance`.

M70's empirical floor lives in a report, not in the pipeline. **The correction is the full
size it looks.**

**The converse hazard is live and should be recorded.** If a future milestone adds an
`e_flat`-style empirical floor term to the shipped model *and* κ is by then defaulted on,
that combination **would** double-count 25.12%. This is a constraint on a future
milestone, not on this one.

---

## 4. Fixed pattern vs temporal: which consumers should see κ

PRNU is a **fixed pattern**. At a given photosite it is the same multiplicative error in
every frame. That has a sharp consequence: **it does not contribute to between-frame
variance at all, and it does not average down across frames.** Those are opposite
behaviours, and the noise model's three consumers want opposite things.

| consumer | what its σ predicts | how the fixed pattern enters | κ? |
| --- | --- | --- | --- |
| `focus.rs::normalise_by_luma_sigma` | within-frame gradient noise floor | `FOCUS_NOISE_SD` was **calibrated** against today's σ | **NO** |
| `Estimator::disagreement` | between-frame sample variance | contributes **exactly zero** | **NO** |
| `Estimator::predicted_sigma` | across-frame average's residual error | is the **floor** the average converges to | **YES** |

The reasoning, in order:

1. **`disagreement` must not see κ.** It compares frames at the same site. The fixed
   pattern is identical in both and cancels in the difference — exactly the property §2.1
   exploited to measure `g`. Inflating the *expected* disagreement by a term that
   contributes zero to the *actual* disagreement loosens the gate for no reason. This is
   fact 1063's ruling and it is correct.
2. **`focus.rs` must not see κ.** `FOCUS_NOISE_SD` is a *measured* constant fitted against
   the current σ. Changing σ underneath it silently rescales every focus decision. Not a
   physics argument — a calibration-coupling argument.
3. **`predicted_sigma` must see κ.** It predicts the error of the *average* of `n` frames.
   Shot noise falls as `1/√n`; the fixed pattern does not fall at all where frames sample
   the same photosite. As `n → ∞` the residual error tends to `κ·S`, not to zero.
   **A model that lets it tend to zero is unboundedly over-confident**, and §5.3 shows
   this is not theoretical: +285.71% at `n_eff` = 22.9.

**This split is measured, not only argued.** Running the `prnu-only` arm across six stacks
moved **0.0000%** of selection decisions while moving mean predicted σ by up to +19.6% at
p99 — precisely the signature of a term that is inert in the gate and live in the report.

**One caveat that undermines the clean version of point 3.** Frames in a focus stack are
*warped* before merging. If warping moves a scene point to a different photosite in each
frame, the fixed pattern **does** partially average down, and the correct floor is
`κ·S·√(ρ_warp)` for some `ρ_warp ∈ [0, 1]`. `ρ_warp = 1` is the no-averaging bound used
above; `ρ_warp = 0` recovers full averaging. **The project has never measured `ρ_warp`,
and §5.4 shows it is the dominant term.**

---

## 5. Blast radius (Deliverable B)

Six real stacks, all four arms computed inside a single decode pass so the arms see
byte-identical pixels.

### 5.1 The six stacks

| stack | ISO | frames | `n_eff` shipped | `n_eff` corrected | `n_eff` moved | winner moved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| foam | 1000 | 60 | 1.353090 | 1.349323 | 0.3754% | 0.0073% |
| 109MSDCF | 160 | 22 | 4.986550 | 4.940444 | 4.4639% | 0.0025% |
| wrapped-text-1 | 100 | 60 | 7.257642 | 7.228223 | 2.4053% | 0.0012% |
| 112MSDCF | 500 | 60 | 10.109531 | 10.049981 | 5.0236% | 0.0072% |
| coffee-bean | 50 | 60 | 22.890743 | 22.832821 | 4.9118% | 0.0006% |
| bee-3-cpl | 100 | 60 | 44.185481 | 44.005126 | **14.7182%** | 0.0033% |

### 5.2 Selection moves; reporting moves a lot; the image barely moves

Per-arm, on 109MSDCF (22 frames, ISO 160):

| arm | `n_eff` moved | winner moved | max Δ frames admitted | mean Δσ | p99 Δσ |
| --- | ---: | ---: | ---: | ---: | ---: |
| gain-only | 4.4639% | 0.0025% | 5 | −0.582% | +10.791% |
| **prnu-only** | **0.0000%** | **0.0000%** | **0** | +8.329% | +19.625% |
| both | 4.4639% | 0.0025% | 5 | +7.792% | +22.969% |

Three separate findings live in that table:

1. **`prnu-only` moves nothing that decides anything** — 0.0000% on all six stacks, all
   octaves. Fact 1063 verified in output.
2. **`both` and `gain-only` move `n_eff` identically** (4.4639% each). All selection
   movement comes from the gain, none from κ.
3. **The election winner moves on ≤ 0.0073% of pixels on every stack.** The merged image
   survives a flip. Whether those ~1-in-14 000 pixels are visually consequential is
   **unmeasured** (§10).

### 5.3 Signal-resolved — the correction is not uniform, it is concentrated

The brief predicted this and it is stronger than predicted. Δσ for the `both` arm:

**109MSDCF** (ISO 160, mid-brightness):

| octave (DN) | share of frame | Δσ | `prnu-only` `n_eff` moved |
| --- | ---: | ---: | ---: |
| 0–64 | — | −0.50% | 0.000% |
| 64–128 | — | −0.04% | 0.000% |
| 128–256 | — | +0.16% | 0.000% |
| 256–512 | 18.31% | +2.86% | 0.000% |
| 512–1024 | 7.02% | +2.59% | 0.000% |
| 1024–2048 | 48.33% | **+10.22%** | 0.000% |
| 2048–4096 | 18.73% | **+11.41%** | 0.000% |

**coffee-bean** (ISO 50, bright, `n_eff` = 22.9):

| octave (DN) | share of frame | Δσ |
| --- | ---: | ---: |
| 256–512 | 2.23% | +0.27% |
| 512–1024 | 6.63% | +0.82% |
| 1024–2048 | 21.09% | +2.33% |
| 2048–4096 | 11.36% | +7.47% |
| **4096–16383** | **58.69%** | **+285.71%** |

**This is the milestone's largest number and it needs stating plainly.** Fact 1064's
−12.8% is a *single-frame* figure. After merging, `predicted_sigma` divides the temporal
part by `√n_eff` while the fixed-pattern part does not shrink, so the fractional
over-confidence grows with `n_eff`. On the majority of a bright, deep stack's frame, the
shipped model claims a σ nearly **four times too small**.

### 5.4 Spatially resolved, and the `ρ_warp` lever

Pearson `r` between tile mean luma and tile Δσ:

| stack | `r` | brightest tile | darkest tile |
| --- | ---: | --- | --- |
| bee-3-cpl | **+0.9806** | — | — |
| 109MSDCF | **+0.9528** | 2110 DN → +11.64% | 452 DN → +1.05% |
| coffee-bean | +0.8403 | 14887 DN → **+434.75%** | 1283 DN → +1.84% |
| wrapped-text-1 | +0.5677 | — | — |
| foam | +0.3608 | — | — |
| 112MSDCF | **−0.2203** | — | — |

**The correction lands where the owner says the output looks worst.** `r ≈ +0.95` on the
two cleanest stacks: the brighter the region, the more over-confident the shipped model
is there. This is not an average effect that can be waved off — it is spatially
structured, and it is structured onto exactly the bright, detailed subject regions.

`112MSDCF`'s **negative** `r` is a useful control rather than an anomaly: it is a dark,
ISO 500 stack where the gain term dominates and the κ term is negligible, so Δσ is
driven by the (signal-independent) read floor instead. The sign flip is the model behaving
as designed.

**The `ρ_warp` sweep** — mean Δσ for the `both` arm at three assumed inter-frame
fixed-pattern correlations:

| stack | mean `n_eff` | ρ = 0 | ρ = 0.5 | ρ = 1 | lever |
| --- | ---: | ---: | ---: | ---: | ---: |
| foam | 1.35 | −0.76% | −0.74% | −0.72% | **1.06×** |
| 109MSDCF | 4.99 | +1.24% | +4.59% | +7.79% | 6.3× |
| coffee-bean | 22.89 | +12.27% | +112.56% | +169.09% | 13.8× |
| bee-3-cpl | 44.19 | +4.28% | +81.61% | +131.93% | **30.8×** |

(coffee-bean at ρ = 1 reaches **p99 +507%**.)

**The lever arm is `n_eff`, monotonically, across a 33× range of `n_eff`.** At `n_eff` = 1.35
the choice of ρ is worth 1.06× and is irrelevant. At `n_eff` = 44 it is worth 30.8× and
dominates every other quantity in this report — including κ itself.

**Recommendation: `ρ_warp` is the next measurement this project should make.** It is
tractable (correlate the flat-field pattern against the measured warp fields already
produced by the aligner) and until it exists, the magnitude of the merged over-confidence
is bounded but not known.

---

## 6. Facts whose numbers would move (Deliverable C)

### 6.1 Material — these move and would need re-running

| # | fact / quantity | direction | estimated magnitude |
| --- | --- | --- | --- |
| 1 | Fact 1064's **−12.8% at S = 8000** | more negative | −11.45% measured at 8000, continuing to **−16.90%** at 13230 DN. The *stated* number is roughly right; the *range* is understated. |
| 2 | Fact 1064's **S = 504 DN** crossover | two objects, split | model-vs-model ≈460–520 DN ✓ holds. Model-vs-**reality** ≈945 DN — new, and it is the operational number. |
| 3 | Fact 1065's **2.16%** gain error | larger | **3.42%** measured (§2.2). Contradicted, 3.6σ, unresolved. |
| 4 | Every published **mean `n_eff`** | down | −0.38% to −14.72%, larger for deeper stacks. All six measured. |
| 5 | Every published **admitted-frame fraction** | down | up to 5 frames of 22 on one stack; tracks `n_eff` exactly. |
| 6 | Every published **`predicted_sigma`** / confidence | up | +0.27% to **+285.71%**, signal-dependent, concentrated in bright regions. |
| 7 | M71 §8.3's **1009 DN** boundary | halved | **504 DN** in the photosite domain (§2.5). Bookkeeping, not physics. |

**Items 4, 5 and 6 are the expensive ones.** Any milestone that published an `n_eff`, an
admission fraction, or a confidence in σ-units measured it against the wrong σ. The
*ordering* of those results is very likely preserved (the correction is monotone in
signal), but the *values* are not.

### 6.2 Immaterial — these survive a flip, measured

| # | quantity | why |
| --- | --- | --- |
| 8 | Published **merged pixel values / images** | election winner moves on ≤0.0073% of pixels, all six stacks. |
| 9 | **`FOCUS_NOISE_SD`** and every focus decision | `focus.rs` is not a κ consumer (§4); untouched by design. |
| 10 | Any result measured under **`prnu-only`** | 0.0000% selection movement, six stacks, every octave. |
| 11 | Fact **1102**'s 25.12% / 74.88% split | no double counting (§3); the split is unaffected. |
| 12 | Fact **1062**'s κ = 0.3096% | independently replicated to four significant figures. |

### 6.3 Recommendation to the orchestrator

**Ship `PRNU_ONLY` as the default first. Hold `GAIN_ONLY` and `BOTH`.**

- `PRNU_ONLY` is a uniform improvement (§2.3), never over-confident at any measured level,
  moves zero decisions, and requires **no** prior milestone to be re-run.
- `GAIN_ONLY` is **worse than shipping nothing** and must never be the default.
- `BOTH` is the best model but its gain constant is contested at 3.6σ (§2.2, §8.2) and it
  invalidates every published `n_eff` and admission fraction. It should wait for the gain
  disagreement to be resolved.
- **Neither** should be defaulted at `ρ_warp = 1` without measuring `ρ_warp`, because that
  choice is worth up to 30.8× on deep stacks (§5.4).

---

## 7. Bit-identity proof for the default path (Deliverable A)

**The probe was written before any library code was touched**, so the baseline hash was
produced by code that could not know what the change would be. Baselines captured at
revision `206c80b5`.

| blob | bytes | SHA-256 |
| --- | ---: | --- |
| `identity.bin` | 8 545 833 | `09E274381BFC8A1D5F966AA67D7F2B5139B27203A2C1043C19B99D77BF399EEA` |
| `identity-real.bin` | 148 347 139 | `36C0470838497925889023B86116DCF2C81B3A37E1F8E51381AA2012E02C1FDE` |

Both hashes are **byte-identical after the change**. `cargo test --workspace`: **289
passed, 0 failed**; no pre-existing test broke.

**Re-verified at the end of the milestone**, after four sibling milestones had committed
into the same working tree: both blobs still hash to the values above
(fnv1a64 `36821ece6e6fbe0c` and `f3477529886859b6`; reference stack 109MSDCF, 22 frames,
mean `n_eff` 4.986550, σ gain 0.491569, gate 4.0), and the suite still reports 289 passed,
0 failed. The default path is bit-identical *as shipped tonight*, not merely as of the
moment the change was made.

Three design decisions made the identity achievable:

1. **κ went on `NoiseModel`, not `PlaneNoise`.** M71 §8.3 suggested a `prnu_frac` field on
   `PlaneNoise`, but that struct has **17 struct-literal construction sites** across the
   workspace, several in files owned by sibling milestones tonight. `NoiseModel` has
   private fields and a `new()` constructor, so a private `Option<Prnu>` defaulted to
   `None` is fully source-compatible and cannot be constructed wrong by accident.
2. **`Corrections::SHIPPED` early-returns.** `noise_model_with` delegates straight to
   `self.noise_model(iso, levels)` for `SHIPPED`, guaranteeing identical float operation
   *order*, not merely an identical result.
3. **The read-noise trap.** `profile.rs` records that `read_noise_e` was fitted to measured
   dark σ **in DN through this profile's gain** — so the quantity actually identified is
   the *product* `RN_e · g`. Correcting `g` alone would silently drop predicted dark σ by
   2.16% below M4's 44 reproduced cells. `noise_model_with` therefore rescales
   `read_noise_e` by the inverse gain ratio, preserving `read_floor_dn` **exactly**;
   asserted at zero signal in-crate.

**The fallback profile is deliberately never corrected.** Its gain is a placeholder of 1.0,
so M71's constants mean nothing against it. Per-plane gains are also deliberately not
carried: M71 measured B at −14.85%, which is the still-unruled B-plane anomaly, so only
the pooled green figure `100 / 0.224103 = 446.2233` is used.

**`merge.rs` and `focus.rs` were not modified.** They are neither owned nor barred; all
corrected-σ composition happens in the example through the public API. This keeps the
milestone reversible but has a cost, recorded in §10.

---

## 8. Registered bars

Registered in `experiments/M90-prnu/PREREGISTRATION.md`, committed at `d057947`
**before any measurement arm ran**.

### 8.1 Passed

PR-1 (bit identity), PR-2, PR-3, PR-4a/4b/4c (instrument recovery), PR-5b, PR-6,
PR-7, PR-8, PR-9, PR-10 (double counting), PR-11.

### 8.2 Failed — three

**PR-4d FAILED — the PTC intercept cannot recover the read floor.**
On synthetic data with a *known* planted read floor of 1.0413 DN, the intercept recovers
0.9266 DN — **11.0% low**. On the real flats the intercept is **−2.795 DN²**, i.e.
negative and physically impossible. Cause: the darkest usable flat is 257 DN, where
shot:read variance is 63:1, so the intercept is an extrapolation far outside the data.
**Consequence: no read-noise number in this report is trustworthy, and I do not publish
one.** The read floor is taken from the existing profile unchanged. This does not affect
`g` or `κ`, which are slope-domain and were both recovered correctly on the same
synthetic data (§8.4).

**PR-5a FAILED (partially) — my `g` does not reconcile with M71's.**
0.221113 vs 0.224103 is **−1.33%, i.e. 3.6× M71's quoted 1σ**. It is inside my own
registered ±3% bar, so the bar technically passes, but the *agreement* the bar was
designed to demonstrate does not hold. **I did not retune the bar.** The honest statement
is: the true shipped-gain error is somewhere in −2.2% to −3.4%, and this milestone cannot
narrow it further.

**PR-6b FAILED — arm (iv) is not flat.**
The registered bar asked for the fully-corrected residual to be flat within ±1%. It
drifts from +0.4% to +2.9%, **monotone in signal**. That drift is exactly the signature of
a residual gain error, consistent with PR-5a. **I declined to refit `g` to flatten it**,
because fitting the gain to make the corrected curve flat is circular — it would convert
a falsifiable prediction into a tautology, which is the specific failure §2.1 was built to
avoid.

### 8.3 The planted defect (rule 12), and a real harness gap it exposed

Plant: `A7C2.gain_divisor` 436.8 → **436.9** — a 0.023% change, deliberately far smaller
than any effect claimed in this report. Built in a **separate target directory** so no
sibling's build was disturbed.

**Caught.** Blob hash moved to
`28F15D9ECE51F5DD708121303E1584693B868940C4C0A12A37371553E0BA5196` vs baseline
`09E27438…`, and **3 pre-existing tests failed** (`gain_follows_the_iso_relation`,
`extended_iso_reads_out_at_base_gain`,
`the_high_mode_read_noise_is_the_relative_least_squares_optimum`).

**But my own in-crate identity test did not fire.**
`the_shipped_corrections_are_bit_identical_to_the_default_path` compares `noise_model`
against `noise_model_with(SHIPPED)` — and under the plant **both moved together**, so the
comparison still passed. Only the *external* blob hash caught it. This generalises: an
in-crate test that compares two paths through the same constant can never detect that
constant being wrong. It is the same shape as rule 34's warning about a plant supplying
its own noise constant. Recorded as **P13**, because it is a defect in the project's
verification habit, not just in mine.

Restored by `Copy-Item` from `experiments/M90-prnu/backup/*.bak` (**never**
`git checkout --`, which would have reverted to HEAD and could have destroyed a sibling's
uncommitted work), `LastWriteTime` reset per rule 33, rebuilt, hash verified back to
`09E27438…`.

### 8.4 Instrument placebo and self-test

The plant supplies its own `g` = 0.2137 and read floor = 1.0413 DN, deliberately different
from the profile's, so the instrument cannot pass by recovering a number it already knows.

| arm | planted κ | recovered κ | recovered `g` error | verdict |
| --- | ---: | ---: | ---: | --- |
| **placebo** | 0.0000% | **0.0110%** | +0.14% | **PASS** — 28× below signal |
| realistic | 0.3100% | 0.3084% | +0.14% | PASS (−0.5%) |
| 10× defect | 3.1000% | 3.0955% | +0.15% | PASS (−0.15%) |

**The placebo shows no effect** (0.0110% against a 0.3096% signal), so the instrument is
not manufacturing κ out of the high-pass filter. And **`g` is recovered to within 0.01%
across a 10× change in κ** — the temporal PTC is genuinely blind to the fixed pattern, as
§2.1 requires. Both are load-bearing for §2.

---

## 9. Candidate facts

**P1.** *MEASURED* — An independent M90 estimator on 360 flats and 86 signal levels
recovers κ = 0.3096% ± 0.0146% per green photosite, replicating M71's 0.3096% ± 0.0159%
to four significant figures with no shared code or intermediates.

**P2.** *MEASURED* — The shipped noise model's over-confidence does not stop at fact
1064's −12.8%: the single-frame residual reaches −16.90% at S = 13230 DN, the top of the
measured range, and is monotone in signal above ≈945 DN.

**P3.** *MEASURED* — Adding κ at `Estimator::predicted_sigma` moves **zero** frame
selection decisions — 0.0000% on six real stacks spanning ISO 50–1000 and `n_eff` 1.35–44,
in every signal octave — confirming fact 1063's ruling in output rather than by argument.

**P4.** *MEASURED* — **Contradicts fact 1065.** An independent temporal photon-transfer
measurement puts the shipped A7C II green gain 3.42% high, not 2.16%; M90's
g = 0.221113 ± 0.000142 disagrees with M71's 0.224103 by 3.6× M71's quoted 1σ and the
disagreement is unresolved.

**P5.** *MEASURED* — Correcting the profile gain **without** adding κ makes the noise model
worse than shipping nothing across the entire measured range (RMS 8.89% vs 8.22%, worst
17.98% vs 17.10%), so `GAIN_ONLY` must never be defaulted.

**P6.** *MEASURED* — Because `predicted_sigma` divides the temporal term by `√n_eff` while
the fixed pattern does not average down, merged over-confidence is far larger than the
single-frame figure: +285.71% over the 58.69% of the coffee-bean frame brighter than
4096 DN at `n_eff` = 22.9.

**P7.** *MEASURED* — The unmeasured constant `ρ_warp` is a lever on merged σ that scales
monotonically with `n_eff` — 1.06× at `n_eff` = 1.35, 6.3× at 4.99, 13.8× at 22.9 and
**30.8× at 44.2** — making it the single highest-value measurement currently available to
this project.

**P8.** *MEASURED* — Flipping the noise-model default changes the merge's per-pixel
election winner on at most 0.0073% of pixels across six stacks, so published *images*
survive a flip even though published *confidences* do not.

**P9.** *MEASURED* — The correction is spatially structured onto bright regions: Pearson r
between tile mean luma and tile Δσ is +0.9806 and +0.9528 on the two cleanest stacks,
with the brightest coffee-bean tile at +434.75% against +1.84% for the darkest.

**P10.** *DERIVED* — M71 §8.3's κ-inflation boundary of 1009 DN is quoted in the luma
domain but compared against a per-photosite level; in the photosite domain where
`PlaneNoise` operates it is **504 DN**.

**P11.** *MEASURED* — Adding κ does **not** double-count M70's absorbed flat-residual
floor, because no shipped code path carries a level-dependent multiplicative variance term
(`e_flat`, `flat_residual` and `1.83` appear zero times under `crates/*/src/`), so the
correction is the full size it appears.

**P12.** *MEASURED* — M71 §8.1's per-plane κ table juxtaposes two estimators that disagree
about green by 0.78% (0.3096% from `05-kappa.json`, 0.3072% from `10-rb.json`); the "B is
0.823× green" claim is correct **within** `10-rb.json` (0.82303) and the apparent
inconsistency with the tabulated 0.8165 is an artefact of the mix, not an error.

**P13.** *MEASURED* — An in-crate test that compares two code paths through the same
constant cannot detect that constant being wrong: a planted 0.023% gain change left M90's
own bit-identity test passing and was caught only by an external output hash.

**P14.** *MEASURED* — A photon-transfer intercept cannot recover this sensor's read floor
from flats: on synthetic data with a planted floor it reads 11.0% low, and on the real
flats it is **negative** (−2.795 DN²), because the darkest usable flat sits at 257 DN
where shot:read variance is 63:1.

**P15.** *ARGUED* — `Estimator::predicted_sigma` and `Estimator::disagreement` require
*different* variances from the same model: the fixed pattern is the floor the first
converges to and contributes exactly zero to the second, so a single shared σ cannot serve
both correctly.

---

## 10. Limits — what could make this wrong

1. **`ρ_warp` is unmeasured and it dominates.** Every merged-σ number in §5 is quoted at
   an assumed correlation. At `n_eff` = 44 the assumption is worth 30.8×. If `ρ_warp` is
   near 0, §5.3's +285.71% collapses toward +12%.
2. **My gain disagrees with M71's at 3.6σ and I could not resolve it.** If M71 is right,
   §2.4's 945 DN crossover moves and §2.3's arm-(iv) drift shrinks. The *qualitative*
   conclusions survive either value; several *numbers* do not.
3. **One body, one night, one flat set.** κ is replicated but not reproduced on a second
   camera. PRNU is a per-sensor property.
4. **Green only.** M71's B-plane anomaly (−14.85%) is untouched. If it is a real per-plane
   gain error rather than an estimator artefact, the blue channel's σ is wrong by an amount
   larger than anything corrected here.
5. **The high-pass radius is 30 px, so κ is a lower bound.** Any fixed-pattern structure
   with a period longer than ~61 px is filtered out before measurement. Large-scale
   response non-uniformity would be counted as zero.
6. **`--limit 60` truncated the deep stacks.** Stacks with more than 60 frames were
   measured on their first 60. Since the lever arm grows with `n_eff` (P7), the true blast
   radius on those stacks is **larger** than reported, not smaller.
7. **`predicted_sigma_for` is composed in the example, not in the library.** It
   reimplements the merge's σ composition through the public API. If `merge.rs` changes its
   composition, this instrument drifts silently out of agreement with the pipeline. A
   later integration milestone should move it inside.
8. **Six stacks is not a survey.** ISO 1600 and above is absent entirely, and the sample
   was chosen for decode speed and label clarity, not by any sampling rule.
9. **Whether the 0.0006%–0.0073% of flipped election winners are visually consequential is
   unmeasured.** They could be uniformly scattered and invisible, or clustered on one edge
   and obvious. §5.2 counts them; it does not look at them.

---

# M90 round 2 — `rho_warp` measured

## R2.0 Status

**`rho_warp` is MEASURED, per resampler, on six real stacks. It is not a constant, and
that is the finding.** It is a *decaying function of frame separation* `rho(d)`: 0.68 at
adjacent frames, 0.00 by `d` = 22–32. Any single scalar is a summary of that curve
weighted by which pairs the merge actually averages.

**Round 1's `rho_warp = 1` quotation must be RETRACTED.** It overstates merged PRNU sigma
by **3.3×** at the depth the owner shoots. Fact 1194's *30.8× lever* survives as a valid
**bound**, but the **realised** lever from `rho` = 0 to the measured `rho` is **4.4×**,
not 30.8×.

**The ruling on wiring is unchanged: do not touch `PlaneNoise::variance`.** Fact 1063
stands. Nothing here is a default flip and no threshold moved.

**M86's interpolator default is now evidenced: keep Catmull-Rom.** On the PRNU-noise axis
bilinear is only **10.7%** quieter, which does not come close to paying for the detail
Catmull-Rom retains and bilinear destroys (M86's own 0.9997 vs M23's 0.372).

---

## R2.1 The central result: `rho_warp` is a curve, not a constant

`rho(d)` — inter-frame correlation of the warped fixed pattern at frame separation `d`,
Catmull-Rom (the merge default), solver `S3-ba-unit`, `hp` = 8. **MEASURED.**

| stack | frames | `rho(1)` | `rho(2)` | `rho(4)` | `rho(8)` | first `d` with `rho` < 0.01 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 109MSDCF | 22 | 0.3070 | 0.1043 | 0.0269 | −0.0011 | 6 |
| flat-on-ruler-cpl | 79 | 0.4656 | 0.1846 | 0.0598 | 0.0072 | 8 |
| foam | 100 | 0.3077 | 0.1091 | 0.0283 | 0.0015 | 6 |
| coffee-bean | 105 | 0.5914 | 0.2884 | 0.0976 | 0.0214 | 11 |
| bee-2-cpl | 299 | 0.6038 | 0.3563 | 0.1393 | 0.0400 | 14 |
| bee-3-cpl | 299 | 0.6801 | 0.4800 | 0.2448 | 0.0885 | 22 |

Two things follow immediately.

**The all-pairs average is the wrong statistic and would have given the wrong ruling.**
Pooling every pair equally gives `rho` = 0.016–0.081 and `n_prnu` = 12–69, because the
overwhelming majority of pairs in a deep stack are far apart and contribute exactly
nothing. But `Estimator::fold` admits the frames whose focus response is within `gate`
sigmas of the winner's, and for a unimodal through-focus curve **that admitted set is an
interval in frame index**. The merge therefore sees the *near-pair* end of this curve.
Integrating `rho(d)` over a contiguous window instead of over all pairs changes the answer
by **2.7×–3.4×** (§R2.3). Had I stopped at the all-pairs number I would have reported a
merged PRNU floor 3.4× too optimistic.

**Round 1 reasoned correctly and concluded wrongly.** `m90-prnu.rs` says, in a comment
written before any of this was measured: *"the merge admits precisely the adjacent frames.
That argues for the top of the interval, but arguing is not measuring."* The *kind* of
argument was right — adjacent pairs do dominate — but the *degree* was wrong by ~14×,
because the admitted window is ~44 frames wide and `rho` is already below 0.01 by `d` = 22.

---

## R2.2 `W`: the within-frame attenuation nobody had recorded

Before any inter-frame question, a resampler wider than nearest is a **lowpass**, and it
attenuates the fixed pattern *inside a single frame*. Call that `W = Var(e_k)/kappa²`.
The project had no such quantity, and quoting `rho` without it lets a reader compute the
floor wrong.

**MEASURED**, pooled over the valid radial bins, 12 runs (6 stacks × 2 solvers):

| resampler | `W` | SD | min | max |
| --- | ---: | ---: | ---: | ---: |
| Nearest | **0.9888** | 0.0016 | 0.9869 | 0.9914 |
| Bilinear | **0.4793** | 0.0097 | 0.4721 | 0.5000 |
| Catmull-Rom | **0.6816** | 0.0064 | 0.6770 | 0.6956 |

`W` is a genuine per-resampler constant: stable across six stacks, two solvers, and a
3.75× change in high-pass radius (it moved +0.73% / −3.44% / −1.15%). It is the kernel's
phase-averaged squared L2 norm, which for a white field is field-independent by
construction. The half-pixel-phase analytic values are 1.0000 / 0.2500 / 0.4104 and the
integer-phase values are 1.0 / 1.0 / 1.0; the measured numbers sit between, as they must
for a real distribution of sub-pixel phases.

**`W_Nearest` ≡ 1 is an identity, and it is the instrument's self-check.** Nearest copies
one photosite, so for any stationary field under any warp `W_Nearest` must be exactly 1.
Where it deviates, the field is not stationary there and the ratio is measuring high-pass
residual rather than PRNU. That gives an objective validity mask — `|W_Nearest − 1| ≤ 0.05`
— which is an internal identity, **not** a fit to the answer.

---

## R2.3 The blast radius, measured at the measured `rho`

`rho_eff` solves `(1 − rho)/n_eff + rho = F_window`, which is exactly the split
`predicted_sigma_for` applies. Each stack uses **its own** measured `rho(d)` at **its own**
`n_eff`. **MEASURED** (`rho(d)`, `n_eff`, and the sweep) / **DERIVED** (`F_window`).

| stack | `n_eff` | `W` | `F_window` | `n_prnu` | `rho_eff` |
| --- | ---: | ---: | ---: | ---: | ---: |
| foam | 1.35 | 0.6788 | 0.50281 | 1.99 | **−0.9177** |
| 109MSDCF | 4.99 | 0.6980 | 0.23197 | 4.31 | 0.0395 |
| coffee-bean | 22.89 | 0.6789 | 0.10073 | 9.93 | 0.0597 |
| bee-3-cpl | 44.19 | 0.6780 | 0.09002 | 11.11 | 0.0690 |

Feeding those into round 1's own blast harness (`m90-prnu blast --rho`), against the
`rho` = 1 column round 1 published:

| stack | `n_eff` | mean Δσ at measured `rho` | median | p99 | mean Δσ at `rho` = 1 | round 1 overstated by |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| foam | 1.35 | **−0.76%** | −0.97% | +1.50% | −0.72% | 1.0× |
| 109MSDCF | 4.99 | **+1.51%** | +1.63% | +14.03% | +7.79% | 5.2× |
| coffee-bean | 22.89 | **+32.36%** | +18.29% | +92.12% | +169.09% | 5.2× |
| bee-3-cpl | 44.19 | **+19.04%** | +19.17% | +41.39% | +131.93% | 6.9× |

Round 1's own limit #1 predicted this collapse and got its magnitude about right: it said
*"if `rho_warp` is near 0, §5.3's +285.71% collapses toward +12%."* The measured mean is
+19.04% at `n_eff` = 44.

**`rho_eff` is negative at `n_eff` = 1.35, and that is structural, not noise.** Round 1's
one-parameter form has no `W`, so it cannot represent a measurement in which a single
frame already carries less than the full pattern variance. **Fact 1194's scalar
parameterisation is inadequate; the correct form is two-parameter, `(W, rho(d))`.**

---

## R2.4 Per-resampler ruling — this settles M86's open item

`warpmap.rs` documents its own default as only partly evidenced: *"What is **NOT
MEASURED** is any comparison of the two on real frames at merge time."* This is that
comparison, on the noise axis. bee-3-cpl, `n_eff` = 44.19. **MEASURED / DERIVED.**

| resampler | `W` | `F_window` | `n_prnu` | merged σ_PRNU, relative |
| --- | ---: | ---: | ---: | ---: |
| Nearest | 0.9902 | 0.09684 | 10.33 | 1.0000× |
| Bilinear | 0.4729 | 0.07177 | 13.93 | **0.8609×** |
| Catmull-Rom | 0.6780 | 0.09002 | 11.11 | 0.9642× |

**Ruling: keep Catmull-Rom.** Bilinear wins the PRNU axis by 10.7% in sigma. That is a
real but small gain, and it is bought by destroying sub-pixel detail — the axis on which
M86/M23 already measured bilinear at `R` = 0.372 against Catmull-Rom's 0.9997. A 10.7%
noise gain does not pay for that. The useful content of this measurement is the
**negative** one: the interpolator choice was *not* hiding a large noise penalty, so the
detail axis is free to decide it, and on that axis the existing default is correct.

---

## R2.5 The bandwidth bar: FAILED, then diagnosed, and I was the one who was wrong

**Registered bar: if `F` moves more than 20% between two high-pass radii, take the
unidentifiability exit.** It failed — 18/18 comparisons at 27–43%.

My first diagnosis was that the failure was an artefact. **It was, but not only.** Two
separate things were going on and I had to separate them.

**(a) My own border-contamination bug — found by cross-checking M71, which was right.**
M71 §5.1 claims `kappa` is flat to 1.0002× over a 16× change of cut scale. Mine moved
4.25×. `box_mean` is edge-clamped, so within ~R of a plane border it is not the mean of a
full window and `I/box(I) − 1` retains illumination curvature. That residual is fixed and
smooth, so it does **not** decorrelate under a warp and it biases `F` **upward**, worse at
larger R — about 1% of the plane at R = 8 but **17%** at R = 120. My radial validity mask
did not exclude borders. With an interior margin, `kappa` moves just **1.16× over 15×**,
and **1.058× over the consumer radii 2–13**. **M71 was right and my measurement was wrong.**

**(b) After the fix, the bandwidth dependence of `F` is real.** On identical point sets
(fixed 240 px margin at every radius), coffee-bean, Catmull-Rom:

| `hp` | `kappa` (interior) | `F` | `n_prnu` |
| ---: | ---: | ---: | ---: |
| 2 | 0.203848% | 0.0209 | 47.77 |
| 4 | 0.209544% | 0.0261 | 38.27 |
| **8** | **0.213436%** | **0.0318** | **31.42** |
| 13 | 0.215535% | 0.0366 | 27.35 |
| 30 | 0.218049% | 0.0461 | 21.69 |
| 120 | 0.249511% | 0.1116 | 8.96 |

**`kappa` is flat (1.07× over the whole range) while `F` moves 5.3×.** That is not a
contradiction, it is the physics: a small low-frequency tail, negligible in *variance*,
dominates *decorrelation*, because it survives a ~1 px warp while white pixel-scale PRNU
does not. **This is why `kappa` is a solid constant and `rho_warp` is not.**

**So the bar failed and I am reporting it failed.** But the exit it prescribes is wrong
for the reason it was written. `F` is not unidentifiable — it is *conditional on naming
the consumer*, because the consumer's own window sets what counts as signal. There is no
flat-field correction anywhere in `crates/`, and the windows are:
`merge::REGULARISER_RADIUS` = 8, `focus::WINDOW_RADIUS` = 13, `FINE_WINDOW_RADIUS` = 2,
`flat_ratio::HP_BOX_RADIUS` = 4. **Every consumer is narrower than the 30 at which round 1
and M71 measured `kappa`.** The headline is quoted at `hp` = 8, the merge's own radius.

**And the ruling is robust even where the constant is not:** across the entire range
`hp` = 2…120, `n_prnu` is 9.0–47.8 (all-pairs) and 2.0–11.1 (windowed) — **never near 1**.
Round 1's `rho` = 1 is refuted at every bandwidth, including at frame centre, where the
per-bin data gives `n_prnu` = 23.9 for a 299-frame stack and where the bound should be
tightest.

---

## R2.6 Registered bars: passed, failed, and the planted defect

| bar | prediction | measured | result |
| --- | --- | --- | --- |
| **N1 placebo** | induced cov < 5% of real | 0.0053 / 0.0055 / 0.0055 | **PASS** |
| **N1′ real-data twin** (unregistered) | — | `rho(d ≥ 32)` = 0.0000 ± 0.001, all 6 stacks | — |
| **N2 identity null** | `F` = 1 ± 0.01 | 1.0000 / 1.0000 / 1.0000 | **PASS** (weak — algebraically forced) |
| **N3 decorrelation** | `F` < 2/n = 0.25 | 0.1329 / 0.1322 / 0.1335 | **PASS** |
| **P1 kernel ladder** | 0.0000 / 0.2500 / 0.3164 ± 0.02, increasing | −0.0093 / 0.2393 / 0.3117 | **PASS** |
| **Bandwidth 20%** | `F` stable within 20% across radii | 27–43%, 18/18 | **FAILED** (§R2.5) |
| **P2 retraction test** | retract if `n_prnu` > 0.5·`n_eff` *everywhere* | 1.47 / 0.86 / 0.43 / 0.25 | **DOES NOT FIRE** |
| **P3 correction sign** | positive at every `n_eff`, monotone in `n_eff` | −0.76% at foam; +32.36% > +19.04% | **FAILED, both clauses** |
| **N4 planted defect** | registered bar must catch it | N3 3/3 FAIL planted, 0/3 after restore | **PASS** |

Three of these need saying out loud.

**P2 does not fire, and P2 was a badly specified bar.** It tests a ratio against `n_eff`
when the thing in dispute is whether `n_prnu` equals 1. It fails to fire at coffee-bean
(0.43) and bee-3-cpl (0.25) purely because those stacks are deep. **I am not retuning it.**
The retraction of round 1's `rho` = 1 rests on the direct measurement instead: `n_prnu` is
1.99–11.11 where round 1 asserted exactly 1.00. Both the bar's literal verdict and the
ground for retraction are recorded here.

**P3 failed on both clauses.** The correction is **negative** at foam (`n_eff` = 1.35,
−0.76%), because at that depth the gain correction dominates the PRNU term and lowers
sigma. And it is **not monotone** in `n_eff`: coffee-bean (+32.36% at `n_eff` = 22.89)
exceeds bee-3-cpl (+19.04% at 44.19). The driver is not `n_eff` alone but the ratio of
PRNU variance to shot variance, which is set by signal level and ISO — coffee-bean is
ISO 50, so PRNU dominates a larger share there. **My registered prediction was wrong about
what the lever arm is.**

**N4: the planted defect was caught, and the restore very nearly fooled me.** The plant
removed the transform from `merge_pattern`, so the instrument would have been measuring an
unwarped field. N3 went 3/3 red, and P1 caught it independently. The first restore
reported *byte-identical: True* and the bars were **still red** — because `shutil.copy2`
preserves the backup's mtime, cargo saw the restored source as older than the artefact
built from the planted source, and **silently skipped the rebuild, leaving the planted
binary live under clean source.** I only caught it by re-running the control separately
instead of trusting the script's own success message. This is discipline 592 again in a
new costume: the check that caught it was external to the thing being checked.

---

## R2.7 What did not change

- **No default was flipped.** `PlaneNoise::variance` is untouched; fact 1063's ruling
  stands and `FOCUS_NOISE_SD` is unaffected.
- **`cargo test --workspace`: 305 passed, 0 failed.** Including
  `profile::tests::the_two_errors_cross_at_about_504_dn`, round 1's guard on fact 1064.
- **Round 1's committed evidence is byte-identical to HEAD** (`git status --porcelain` on
  the four `rho-*.txt` files returns empty).
- **The double-counting question against M70 (facts 1086, 1102) is unchanged by round 2.**
  Round 2 measures how the pattern *averages*, not how large it is; `kappa` itself moved
  by 1.6% on independent replication. Round 1's answer stands.

---

## R2.8 Candidate facts

**P16.** *MEASURED* — `rho_warp` is not a constant but a decaying function of frame
separation: for Catmull-Rom on real stacks it is 0.31–0.68 at adjacent frames and falls
below 0.01 by a separation of 6–22 frames, measured on six stacks spanning 22–299 frames.

**P17.** *MEASURED* — The within-frame attenuation `W` — the fraction of PRNU variance a
resampler passes in a single gather — is a stable per-resampler constant: Nearest
0.9888 ± 0.0016, Bilinear 0.4793 ± 0.0097, Catmull-Rom 0.6816 ± 0.0064 over 12 runs, stable
across six stacks, two solvers and a 3.75× change of high-pass radius.

**P18.** *DERIVED* — Integrating the measured `rho(d)` over a **contiguous** admitted
window rather than over all pairs changes merged PRNU variance by 2.7×–3.4×, and the
contiguous form is the correct one because `Estimator::fold` admits frames within `gate`
sigmas of the winner, which for a unimodal through-focus curve is an interval in frame
index.

**P19.** *MEASURED* — Round 1's `rho_warp` = 1 overstates merged PRNU sigma by 3.3× at
`n_eff` = 44.19: the measured mean confidence correction is **+19.04%**, against +131.93%
quoted at `rho` = 1. Fact 1194's 30.8× lever is a valid bound but the realised lever is
**4.4×**.

**P20.** *MEASURED* — On the merged-noise axis the interpolator choice is nearly free:
at `n_eff` = 44.19, bilinear yields merged PRNU sigma 0.8609× and Catmull-Rom 0.9642×
relative to nearest, so the 10.7% bilinear advantage does not pay for the sub-pixel detail
it destroys, and M86's Catmull-Rom default is correct — now for a measured reason.

**P21.** *MEASURED* — `kappa` is flat to 1.07× over high-pass radii 2–120 px while `F`
moves 5.3× over the same range, because a low-frequency tail negligible in variance
dominates decorrelation; therefore `kappa` is a transferable constant and `rho_warp` is
only defined relative to a named consumer window.

**P22.** *MEASURED* — `box_mean` is edge-clamped, so `I/box(I) − 1` retains illumination
curvature within ~R of a plane border, contaminating ~1% of the plane at R = 8 but **17%**
at R = 120; this fixed, smooth residual does not decorrelate under warp and biases `F`
upward. An interior margin restores agreement with M71 (`kappa` flat to 1.16× over 15×).

**P23.** *MEASURED, NEGATIVE* — My registered prediction P3 failed on both clauses: the
confidence correction is **negative** (−0.76%) at `n_eff` = 1.35, and is **not monotone**
in `n_eff` (+32.36% at `n_eff` = 22.89 against +19.04% at 44.19), because the lever arm is
the PRNU-to-shot variance ratio set by signal level and ISO, not `n_eff` alone.

**P24.** *DERIVED* — Fact 1194's single-scalar `rho_warp` parameterisation is structurally
inadequate: solving for the `rho` that reproduces the measurement yields **−0.92** at
`n_eff` = 1.35, because the form has no `W` term and cannot express a single frame already
carrying less than full pattern variance. The correct form is two-parameter, `(W, rho(d))`.

**P25.** *MEASURED* — A byte-identical source restore does not imply a restored binary:
`shutil.copy2` preserves mtime, so cargo skipped the rebuild and left a planted binary live
under clean source; the planted defect was detected only by re-running the control
externally rather than trusting the restoring script's own success report.

**P26.** *MEASURED* — At high-pass radius 8 the interior-only `kappa` on green luma is
0.2134%, implying **0.3048%** per photosite if G1 ⊥ G2, a **1.6%** independent replication
of fact 1062's 0.3096% from different code, a different estimator and a different flat
subset.

---

## R2.9 Candidate disciplines

**D-a.** When a statistic averages over pairs, check what the *consumer* averages over
before quoting the pooled value — the all-pairs `rho` here was 3.4× wrong for a merge that
admits a contiguous window.

**D-b.** After restoring a planted defect, re-run the control in a separate invocation and
confirm it is green; a restore script's own "restored" message tests the copy, not the
build.

---

## R2.10 Limits — what could make this wrong

1. **`rho(d)` is measured with uniform weights over all frames at separation `d`; the
   merge weights pixels, not frames.** The window integration assumes the admitted set is
   a contiguous interval of uniform weight. It is contiguous, but the per-pixel admitted
   *width* varies across the plane, and I integrated at the stack-mean `n_eff` rather than
   per pixel. A per-pixel integration would spread these numbers.
2. **The admitted set is contiguous only if the through-focus curve is unimodal.** Where it
   is not — occlusion boundaries, repeated texture — the admitted set can be split, and
   split sets sample the low-`rho` tail, so my numbers are conservative there. M87 owns
   occlusion and I did not measure this.
3. **`F` is only defined relative to a high-pass radius**, and I chose 8 because it is
   `REGULARISER_RADIUS`. A consumer at radius 2 sees `F` about 1.5× smaller and one at 13
   about 1.15× larger. Anyone reusing these numbers must name their window.
4. **The pattern comes from 360 flats of one illumination geometry**, cropped 3520→3516 px.
   No scene data enters, so registration is moot, but a PRNU field with different
   low-frequency content would give a different `rho(d)` while giving nearly the same
   `kappa` — that is precisely the sensitivity P21 measures.
5. **Solver sensitivity is up to 22% on `F`** (bee-3-cpl, S3 vs S4-poly4), and I do not know
   which solver the merge will use, because `merge.rs` is M91's. I ran both as a sensitivity
   arm rather than picking one.
6. **Round 1's unresolved 3.6σ gain disagreement is still unresolved** (my 3.42% vs fact
   1065's 2.16%), and fact 1064's S = 504 DN cancellation point is *derived* from the
   contested 2.16%, so it must be re-derived before reuse. Round 2 does not touch this.
7. **`n_eff` values are round 1's**, measured at gate 4 on 60-frame limits, while `rho(d)`
   is measured over the full 299-frame stacks. If the owner's real gate differs, the window
   width and therefore `F` move with it.

---

## R2.11 Reproduction

```text
cargo run --release --example m90-rho --target-dir experiments/M90-prnu/target-m90 -- control
cargo run --release --example m90-rho --target-dir experiments/M90-prnu/target-m90 -- prnu --flats <DIR> --hp 8
cargo run --release --example m90-rho --target-dir experiments/M90-prnu/target-m90 -- rho --edges <CSV> --hp 8
cargo run --release --example m90-rho --target-dir experiments/M90-prnu/target-m90 -- sep --edges <CSV> --hp 8
cargo run --release --example m90-prnu --target-dir experiments/M90-prnu/target-m90 -- blast --dir <DIR> --limit 60 --gate 4 --rho 0.0690
python experiments/M90-prnu/window_rho.py
python experiments/M90-prnu/plant_n4.py
```

Evidence under `experiments/M90-prnu/out/` with the `rho2-` prefix (round 1's evidence uses
`rho-` and must not be overwritten — I did exactly that once and restored all four files
from HEAD via `git show` read as bytes). Pre-registration: `PREREGISTRATION-rho.md`,
committed `c2692ec` **before any measurement existed**.
---

## 11. Reproduction

From the project root, with a private target directory to avoid lock contention:

```text
cargo run --release --example m90-prnu --target-dir experiments/M90-prnu/target-m90 -- identity
cargo run --release --example m90-prnu --target-dir experiments/M90-prnu/target-m90 -- flats
cargo run --release --example m90-prnu --target-dir experiments/M90-prnu/target-m90 -- blast --stack <dir> --limit 60
cargo run --release --example m90-prnu --target-dir experiments/M90-prnu/target-m90 -- selftest
```

Raw outputs are preserved under `experiments/M90-prnu/out/` and are committed. The
identity blobs themselves are 173 MB and gitignored; their SHA-256 chain — baseline →
after → plant → restored → end-of-night, annotated with what each row proves — is in
`experiments/M90-prnu/out/identity-hashes.txt`. Pre-registration and baseline hashes are
in `experiments/M90-prnu/PREREGISTRATION.md` §6.

Commits: `d057947` (pre-registration, before any result), `cc67c7b` (Deliverable A),
`6602e52` (the instrument), `56e68e2` (this report), `e709a9d` (end-of-night
re-verification), `6ac517c` (the raw evidence and the hash ledger).
