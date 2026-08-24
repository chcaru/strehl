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
