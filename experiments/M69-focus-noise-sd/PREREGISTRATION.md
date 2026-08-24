# M69 pre-registration — `FOCUS_NOISE_SD`, the constant every gate is denominated in

Committed **before any arm was run and before any result in this milestone existed**.
Where this file and the report disagree, this file is the record.

Facts in the report are numbered locally from 1. No file under `crates/` will be
modified by this milestone; §8 explains why no modification is needed to price
anything here.

---

## 0. Prior work read before writing this (rule 40)

Searches run over `docs/research/**` and `experiments/**` (ripgrep + `Select-String`):
`FOCUS_NOISE_SD`, `noise scale`, `response noise`, `sigma_F`, `noise_sd`,
`focus noise`, `k_sd`, `profiles as data`, `calibration seam`, `burst`.

**Files found by the search and actually read, and what I took from each:**

| File | Taken, not re-derived |
|---|---|
| `docs/research/M66-gate-n-dependence.md` | **My origin.** K7 in full (facts 9, 10, 12, 23) and its method; §4 arm B's plant; §8's naming of the per-pixel candidate as post hoc; §9's circularity declaration. Its headline (no `N` term in `Gate::tolerance()`, `c_N` drift 1.032 σ_F over N∈[19,299], 18% headroom erosion at gate 4). |
| `docs/research/M65-election-gate-measured.md` | K1's replication `σ_reg = 1.521409e-2 ± 7.468e-5`; fact 3's `k_sd = 1.23770` and its mechanism (the 27×27 operator window pre-correlates before the 17×17 box sees it); §9's circularity paragraph. |
| `docs/research/M62-sqrt-n.md` | §1 the burst's focus degeneracy; §3 the plant (`109MSDCF/DSC00020.ARW`, 2048² RGGB crop at y=1024 x=4096, ISO 160, 1229.90 DN binned green, model σ 15.0479 DN); §4 the shared-noise trap and the reference choice; §5 the statistic and the 32-px inset; §6.2 the gate ladder and 5.4778×. |
| `docs/research/M62-ruling-M64.md` | The certified `DEFAULT` **5.431624**, efficiency 1.000076, guard `109MSDCF` 0.22668; Q2's measured gate sweep on the burst (0.9773 / 1.3616 / 1.9710 / 3.7610 / **5.4354** / 5.4849 / 5.4849 / 5.4849 at gates 0…64) and its ruling that **the objective saturates at gate 8 and cannot choose a gate**; Q3's four explicit non-coverages. |
| `docs/research/M64-estimator-default.md` | §2.4's seven-stack guard table at gate 4.0 and the 22.15× spread; §1.1a's refutation of an adaptive `n_eff` target. |
| `docs/research/M43-plugin-calibration-seam.md` §8.2 | The seven-operator survey: `k = SD/FOCUS_NOISE_SD` spanning **10.4×** (ring 0.644 → SML 6.680), shipped tenengrad reading 1.008 against a 1.000 by construction. |
| `docs/research/M49-unapplied-findings.md` F12, SYNTHESIS facts 439/502/503/583/630 | The seam is built, tested and **off the shipped path**; `Gate::tolerance()` uses the compiled-in constant; fact 503's untested bit-identity prediction under a constant rescale. |
| `docs/captures-needed.md` §11, §12 | §12's static repeat burst is **REQUESTED, not delivered**; §11 records ISO 160 as the missing dark set. |
| `crates/strehl-core/src/merge.rs`, `focus.rs`, `noise.rs`, `profile.rs`; `crates/strehl-plugin/src/calibrate.rs`, `rng.rs` | The object under study, read rather than described. |

**Nothing in the corpus has ever measured `FOCUS_NOISE_SD` against real sensor
noise on real data.** Every prior determination — the crate test, M65 K1, M43's
survey, M66 K7 — runs on a synthetic plane or a synthetic burst.

---

## 1. The question, stated so it can be answered wrongly

`Gate::tolerance() = threshold · √2 · FOCUS_NOISE_SD` (`merge.rs:310`). Define

> **σ_F(p)** = the standard deviation, over independent realisations of sensor
> noise with the scene held fixed, of the **shipped regularised focus response**
> at plane pixel `p`.

`FOCUS_NOISE_SD` is a single f32 standing in for σ_F everywhere. Three questions,
in the order they must be answered:

- **Q1 provenance.** What plant, operator, field and data produced 0.015214?
- **Q2 replication.** Is M66's post-hoc K7 (σ_F on real texture ≈ 1.19–1.21 ×
  the constant) reproducible by an independent instrument, and does it survive a
  plant defect I name in §3 before running it?
- **Q3 form.** Is a scalar the right *form*, or is σ_F derivable per pixel from
  the sensor model `σ²(S) = gS + (RN·g)²` plus locally observable quantities?

## 2. The primary observable

For each arm and each interior pixel `p`:

```
sigma_hat_F(p) = temporal SD over realisations of  reg_box17( box27(|grad L|) / sigma_model(L) )(p)
rho(arm)       = mean_p sigma_hat_F(p) / FOCUS_NOISE_SD
```

Interior inset `WINDOW_RADIUS + REGULARISER_RADIUS + 2 = 23` plane px, matching
M66 K7 so the two are comparable. `mean_p` of the per-pixel SD is the primary
summary **because that is what M66 reported**; the median, p05, p95 and the
across-pixel IQR are reported beside it every time (rule 39), and the IQR is
D2's decision statistic.

**`rho` has `FOCUS_NOISE_SD` in its denominator and nothing else. That is a
comparison, not a circularity** — the constant does not enter the numerator's
computation at any point. §7 states where the real circularity is.

## 3. Arms

### A1 — provenance, in-crate, built by me (rule 33)

`cargo test -p strehl-core the_focus_noise_constant_is_the_measured_one` and a
fresh run of `strehl-plugin`'s `calibrate` at `host_default` and `reference`
plans across all three `NoiseSource` variants. Establishes the declared value,
its standard error, and its sensitivity to plane size and generator.

### A2 — direct replication of M66 K7, independent implementation

My own decode, Sobel, clamped box, sigma normalisation and regulariser (no line
of M66's code imported). Plants FLAT / SMOOTH / REAL on M62's exact latent, plus
**two latents M66 did not use**, at different ISOs, to test whether ρ is a
property of one crop.

### A3 — the plant defect I am naming in advance, and the arm that tests it

**Mechanism.** M66's REAL latent is a real frame, so it equals `T + eta`: the
scene plus **one frozen realisation of sensor noise**. Fresh noise is then added
on top. The deterministic gradient the response's noise is evaluated against is
therefore `grad(T + eta)`, not `grad T`; the plant carries a gradient
contribution from `eta` that a real frame's *deterministic* content does not
have. The per-sample noise SD of a Sobel magnitude is a Rice standard deviation
and is a monotone function of the ratio `nu/s` of deterministic gradient to
gradient-noise scale, so any arm whose `nu` is displaced changes ρ.

**Observable.** `rho(A3) - rho(A2)` on the same latent, where A3 replaces the
latent by a texture-matched one whose high-frequency gradient budget is
corrected for `eta`, and, independently, a **controlled plant**: a bandlimited
synthetic texture whose `nu/s` is set by construction and swept over
`nu/s ∈ [0, 30]`, giving the transfer curve `rho(nu/s)` with no frozen `eta`
anywhere in it.

**I state no expected sign for `rho(A3) - rho(A2)`.**

**Derived prediction fixed here, before the curve is measured.** For a Sobel
magnitude on white input noise the two components are uncorrelated with equal
variance `s² = (0.125)²·12·sigma²`, so `|grad|` is Rice with parameters
`(nu, s)`. Its SD is `0.6551·s` at `nu = 0` and `-> s` as `nu/s -> inf`. If the
window and regulariser correlation structure were unchanged by texture, ρ would
therefore be bounded above by **1/0.6551 = 1.5264**. A measured ρ above that
bound on any arm falsifies the single-mechanism account and I will report it as
such rather than widen the mechanism.

### A4 — real sensor noise, zero signal (`D:\macro-dark-frames`)

The corpus's only real repeated-frame captures. First two frames of each ISO
group discarded (stabilisation). Gives ρ on a **real flat field with real
temporal noise**, including any correlated component the synthetic generators
do not produce.

**Declared in advance:** A4's numerator is real noise and its denominator is
`sigma_model(L)`, so A4 is a **joint** test of (read-noise calibration × the
operator), not of the operator alone. It cannot separate them and I will not
report it as if it could.

### A5 — real sensor noise, real texture, no sensor model in the numerator

There is no static burst (§0: `captures-needed.md` §12 is REQUESTED, and I
verified no such directory exists on disk). The substitute is the **lag
structure function** of the response along a real through-focus stack:

```
D(tau, p) = 0.5 * mean_k ( X_{k+tau}(p) - X_k(p) )^2
```

Under `X_k = f(z_k) + e_k` with `e_k` white in `k` and `f` smooth in focus
position, `D(tau) = sigma_F^2 + 0.5*(f(z_{k+tau}) - f(z_k))^2`, whose second term
vanishes quadratically as `tau -> 0`. Fitting `D(tau) = a + b*tau^2` (and
`a + b*tau^2 + c*tau^4` as a robustness variant) over `tau = 1..6` and taking the
intercept estimates `sigma_F^2` **with no sensor model in the numerator at all**.
Run on the deepest stacks, where consecutive frames are closest in focus.

### A6 — blast radius

`Gate::tolerance()` is **exactly linear** in `FOCUS_NOISE_SD`, so running the
shipped binary at gate `T·rho` is arithmetically identical to running at gate `T`
with the constant multiplied by `rho`. Every priced number below is therefore
obtainable **without touching `crates/`**:

- corpus-wide mean `n_eff` and `n_eff/N` at gate 4.0 versus gate `4.0·rho`;
- M64 §2.4's guard margin and its 22.15× spread at both;
- M62's certified `DEFAULT` 5.431624 re-priced at gate `4.0·rho` on a
  reconstruction of M62's plant, **validated first** by reproducing 5.4316 at
  gate 4.0 (control K7 below);
- M65's `k_sd = 1.23770` re-expressed against whatever σ_F this milestone lands on.

## 4. Decisions, with their bars fixed now

**D1 — is M66's 19–21% reproducible?**
- **REPRODUCED** if A2 on M62's exact latent lands within **±0.02 absolute** of
  M66's `rho_REAL = 1.1921`.
- **NOT REPRODUCED** if it lands outside that band. A refutation is a successful
  outcome and will be reported as the headline if that is what happens.

**D1b — is 19–21% right *as a claim about real texture*?** This is a separate
decision from D1, because reproducing a number on one plant is not establishing
it about the world. The claim stands as a general statement about real texture
only if **both**
  (i) the corpus-wide real-data estimate (A5, or A3's transfer curve evaluated
      on the corpus's own measured `nu/s` distribution) lands inside
      **[1.15, 1.25]** on a **majority of the stacks measured**, and
  (ii) A3 does not move `rho` on M62's own latent by more than **0.05 absolute**.
If either fails, I report the claim as **not supported as a general statement**,
with the corrected number and its arm named.

**D2 — should it be a constant at all?** The scalar form is **refuted** if
either
  (a) the across-pixel interquartile range of `sigma_hat_F(p)` within a single
      stack exceeds **±10%** of that stack's median on a majority of stacks; or
  (b) the per-stack `rho` spans more than **1.10×** across the arms and stacks
      measured.
Otherwise the scalar form **survives** and I say so.

**D3 — is the per-pixel form derivable rather than merely measurable?** A
**parameter-free** predictor built from the sensor model and locally observable
gradient statistics (no fitting, no free constants) is accepted if its median
|predicted/measured − 1| over interior pixels is **≤ 0.10** on the arm where
truth is known by construction. If it exceeds 0.10 I report "not derivable at
this order" and name the missing term rather than fitting one.

## 5. Controls, each with its consequence attached

| id | what it checks | bar | consequence if NOT MET |
|---|---|---|---|
| **K1** | my pipeline reproduces `FOCUS_NOISE_SD` on the crate's own plant (zero-signal unit-sigma plane) | `\|rho - 1\| <= 0.02` | **no ρ in this milestone is believed**; the report becomes provenance-only |
| **K2** | my Python field is the shipped Rust field | mean `n_eff` within **0.2%** of the shipped `strehl merge` at gates 0.5/1/2/4 on ≥2 real stacks | every arm computed in Python is reported as an emulation, not as the shipped operator |
| **K3** | A5's structure-function estimator recovers a **known** σ_F | recovers planted σ_F within **5%** on a synthetic sequence carrying a planted smooth focus drift | **arm A5 is void**; D1b rests on A3 alone and I say so in the headline |
| **K4** | the stacks used in A5 are not dominated by photometric or geometric drift | frame-to-frame mean level and a displacement proxy reported; A5 restricted to stacks passing | A5 restricted or void on the failing stacks, named individually |
| **K5** | the controlled plant of A3 **is** the calibration plant at zero texture | `rho(nu/s = 0) = 1.00 ± 0.02` | A3's curve is descriptive only and cannot be used to correct A2 |
| **K6** | the instrument can detect a wrong answer (rule 39) | a response field scaled by a planted **1.30** must read `rho` scaled by 1.30 ± 0.01 | the whole instrument has no power and nothing is reported as measured |
| **K7** | my Python merge reproduces M62's certified plant number | **5.4316 ± 0.010** at gate 4.0, and 1.0000 ± 0.005 at gate 0 | the re-pricing of M62's number in A6 is withdrawn and replaced by an interval bounded by M62's own published ladder, labelled DERIVED |

`n_eff` is reported beside every gate in every table (rule 39).

## 6. What the static burst can and cannot arbitrate — decided in advance

**There is no real static burst.** `docs/captures-needed.md` §12 marks it
REQUESTED; I enumerated every directory under `D:\personal\macro` and there is
none. M62's burst is **synthetic** — one real frame plus noise drawn from the
crate's own model. So the known-answer control is:

- **What a static burst (real or synthetic) CAN arbitrate here.** A noise-scale
  measurement is exactly what a fixed-scene repeat is for: focus is held
  constant, so *all* temporal variation in the response is the quantity being
  measured. This is the opposite of M62's degeneracy problem.
- **What it CANNOT arbitrate.** M62 §Q2 proved that a static burst's √N objective
  is monotone and saturating in the gate, so **no static burst can choose a gate
  value.** I will not use any burst arm to argue for or against a gate.
- **What a *synthetic* burst additionally cannot do (rule 34).** Its noise is
  drawn from the same `g` and `RN_e` that the denominator normalises by, so ρ is
  invariant to a global error in those constants. A2, A3 and K7 therefore
  **cannot detect a mis-calibrated sensor model**. A4 and A5 can, because their
  numerator noise is real. This is why the milestone does not rest on the
  synthetic arms.

## 7. Circularity, declared before measuring

1. **Not circular:** ρ's denominator is the constant under test and its
   numerator is not. Comparing a measurement to a declared value is the point.
2. **Circular, and it bites A2/A3/K7:** the injected noise comes from the crate's
   sensor model and the divisor is the same model, so those arms are
   scale-invariant in `g` and `RN_e` to first order (rule 34, SYNTHESIS fact 599).
   A4 and A5 are the escape and are pre-registered for that reason.
3. **Circular, and I cannot remove it:** any *consequence* of a corrected σ_F
   that I price through `n_eff` is priced with an instrument whose own admission
   rule is denominated in the uncorrected constant. §A6's trick (gate `T·rho`)
   makes this arithmetically exact rather than approximate, but the *choice* of
   which gate a user should run is not thereby settled, and M62 §Q2 already ruled
   that its own objective cannot settle it.
4. **Circular, and it is the one M65 could not escape:** `k_sd = 1.23770` is the
   ratio of raw to regularised response noise on white noise. If σ_F is
   texture-dependent, `k_sd` is too, and the unit-matching M65's arm X′ performed
   is itself calibrated on the wrong field. I will report what my arms say about
   `k_sd` on textured content and will not claim to have repaired M65.

## 8. What I will not do

- **No file under `crates/` will be modified.** §A6 shows the entire blast
  radius is measurable through `--gate`, so no code change is needed to price
  anything. If I find a measurement that genuinely requires one, I will name it
  and not make it.
- **I am not the acceptance authority.** If a corrected σ_F disturbs M62's
  certified 5.431624, I will say so plainly and route it; M62 rules, not me.
- **No number in `docs/research/SYNTHESIS.md`, `AGENTS.md` or
  `docs/research/OWNER-QUESTIONS.md` will be edited by me.**

## 9. Reporting standard

Every pre-registered criterion in §4 and §5 is reported in the report as MET or
NOT MET **in the words it is written in here**, with the attached consequence
honoured. Facts are labelled MEASURED / DERIVED / ARGUED and numbered
`**Fact N (LABEL).**`. Anything found post hoc is labelled POST-HOC at the point
of first use.
