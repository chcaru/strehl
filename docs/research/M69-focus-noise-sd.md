# M69 — `FOCUS_NOISE_SD` is a zero-signal constant standing in for a texture-dependent quantity

**Verdict: `FOCUS_NOISE_SD` should not be a constant, and that — not its value —
is the finding. Its value is very nearly right: across all 12 stacks the true
per-stack response noise sits between **0.9285×** and **1.1009×** the shipped
number, median 1.0147×, so as a corpus average it is good to about 1.5% and I
recommend against changing it. Its *form* is refuted. On a controlled plant the
same operator produces `sigma_F` from **0.2805×** to **1.1386×** — a 4.06× span
— driven not by signal-to-noise but by whether the deterministic gradient
*direction* stays coherent across the operator's 27×27 window; within a single
real stack the p05–p95 span reaches 2.0×; and adopting a per-pixel form would
move `n_eff` by **1.09×–1.72×** per stack, twenty to fifty times what any rescale
of the constant can do. The constant was calibrated on a 512×512 plane of pure
iid Gaussian noise with no signal, no gain, no ISO, no CFA and no texture; its
own plant size biases it 0.64% low, and that is the largest error in it that is a
scale error. M66's 19–21% reproduces here on M66's own plant by **both** of
M66's estimators — 1.1921 spatially, digit-for-digit, and 1.1971 temporally at
N = 299, inside the pre-registered ±0.02 band — and does **not** generalise: on
three further real latents the same measurement gives 0.8380, 1.0274 and 1.0246,
and the sign is not even consistent. A control that could have failed, and did
not, identifies why: M66's plant freezes one noise realisation into its latent,
and the derived predictor P2 forecasts the *slope* of that defect to 0.7% of its
own size. Priced: a uniform recalibration to any corpus-justified `rho` moves
mean `n_eff` by −2.8%…+3.2%, moves M62's certified `5.431624` by at worst
**−0.788%** (inside M62's own 1% tolerance), and leaves M64's guard and M65's D1
standing with **3.24×** and **1.45×** margins. The certified result survives —
*asymmetrically*, because M62's objective saturates above gate 4, so `rho > 1`
costs it +0.37% while `rho = 0.838` would cost −3.63% and break it. And the
replacement carries the same shape of error as the thing it replaces: a
per-pixel `sigma_F` still has no `N` term (§9.1).**

**Amended after its first commit (`02f501b`)** in response to two post-dispatch
updates: a report that M62 had independently reproduced M66's effect, and M62's
addendum `e4c1f98` pricing the acceptance battery by algebra. **§3b handles the
first, and it does not survive contact with the sources.** §8.2 defers to M62 on
the second and prices the limb M62 left open. §§3b, 8.2, 8.3, 9.1 and facts
36–47 are new; **nothing in the original was withdrawn.**

Pre-registered at **`33f3565`**, before any number in this report existed.

Status: MEASURED unless a fact says otherwise. No file under `crates/` was
modified; `git show --name-only` on every commit in this milestone shows only
paths under `experiments/M69-focus-noise-sd/`, `docs/research/M69-focus-noise-sd.md`
and `docs/captures-needed.md`.

---

## 0. Prior art read before measuring (rule 40)

Searched `docs/research/` for `FOCUS_NOISE_SD` (208 paths matched across the
repository), and for `noise scale|response noise|sigma_F|noise_sd` (34 matching
files under `docs/`). Read in full or in the named part:

| source | what I took from it, and did not re-derive |
|---|---|
| [`M66-gate-n-dependence.md`](M66-gate-n-dependence.md) | K7 in full — the origin of this milestone. Also its headline: `Gate::tolerance()` carries no `N`; the 22.15× M64 spread is 72% frame count. |
| [`M65-election-gate-measured.md`](M65-election-gate-measured.md) | the circularity — the constant is calibrated on the *regularised* field; `k_sd = 1.2377`; the 17×17 regulariser removes only 19% of response noise because the 27×27 window pre-correlates the samples. |
| [`M62-sqrt-n.md`](M62-sqrt-n.md) | the certified ladder (gates 0/0.5/1/2/4/8/16 → 0.97682/1.35937/1.96845/3.77637/**5.43162**/5.47768/5.47768), the 1% harness tolerance, `n_eff = 29.539` at gate 4, P17 (G1/G2 temporal correlation `+0.073`), and the finding that a static burst has no interior optimum. |
| [`M62-ruling-M64.md`](M62-ruling-M64.md) | M62's own ruling that its objective **saturates at gate 8** and cannot be used to choose a gate. This is load-bearing for §8. |
| [`M62-ruling-M64-addendum.md`](M62-ruling-M64-addendum.md) | **read after dispatch, and it changed two sections.** Its `CERTIFY-CONDITIONAL` verdict, its ≈8× robustness derivation, its exact σ-invariance of gate 0, its own post-hoc gate sweep, its confession that guard G shares the defect it polices, and — decisively for §3b — its statement *"No re-run … I implemented nothing."* |
| [`M64-estimator-default.md`](M64-estimator-default.md) | §2.4 — the shipped default path, the seven-stack guard table and the 22.15× spread. |
| [`M24-photometric-drift-measured.md`](M24-photometric-drift-measured.md) | photometric drift is already measured; K4 below corroborates and does not re-derive it. |
| [`M43-plugin-calibration-seam.md`](M43-plugin-calibration-seam.md) | the calibration seam whose expressive limit is fact 9. |
| [`M59-corpus-linter.md`](M59-corpus-linter.md) | what the linter can and cannot see. |
| `crates/strehl-core/src/{merge,focus,noise,profile,boxfilter,plane,through_focus}.rs` | read, not edited. |
| `crates/strehl-plugin/src/calibrate.rs`, `examples/calibration-survey.rs` | read, then *run* (§1). |
| `experiments/M66-gate-n-dependence/src/{02-fields,04-burst,07-response-sd}.py` | M66's K7 method, so that §2 could re-implement rather than re-run it. |
| `experiments/M64-estimator-default/src/{11-focus-guard,21-guard-corpus}.py` | the guard's definition. |

**The brief's premise about the data is false, and I checked before designing.**
The brief states a 30-frame static burst "was also delivered". It was not.
`docs/captures-needed.md` §12 still lists it as **REQUESTED**; enumerating
`D:\personal\macro` and the root of `D:\` finds no such capture. M62's burst is
**synthetic**. This removed the obvious known-answer control and forced the
redesign recorded in §5 of the pre-registration.

---

## 1. Provenance: what `FOCUS_NOISE_SD` actually is

**Fact 1 (MEASURED, source read).** The constant is one line.
`crates/strehl-core/src/merge.rs:185` declares `FOCUS_NOISE_SD = 0.015_214`.
`merge.rs:310` spends it: `tolerance() = T * SQRT_2 * FOCUS_NOISE_SD`.
`merge.rs:297` sets `DEFAULT_GATE = 4.0`. Nothing else in the crate sets or
adjusts it. A **second**, separate focus-noise constant exists and is not
mentioned anywhere in the research corpus I searched:
`FINE_FOCUS_NOISE_SD = 0.090_400` at `crates/strehl-core/src/through_focus.rs:153`.

**Fact 2 (MEASURED, source read).** Its entire calibration is one in-crate test,
`merge::tests::the_focus_noise_constant_is_the_measured_one` (`merge.rs:1197`).
Its plant is a **512×512 plane of `rng.normal()` — pure iid N(0,1), zero
signal**, over 12 SplitMix64 + Box–Muller seeds. It is not a flat field with
sensor noise; it is a field that is *only* noise.

**Fact 3 (MEASURED, source read).** The noise model the test uses,
`unit_sigma_model()` (`merge.rs:1058`), sets `gain = 1e-4` and
`read_noise_e = sqrt(2)/gain` precisely so that `green_luma_sigma(L) == 1` for
every `L`. **No ISO, no real gain, no shot-noise term, no CFA geometry and no
texture enters the calibration of `FOCUS_NOISE_SD` at any point.** The
provenance question "at what ISO, on what data" has the answer: *none, and none*.

**Fact 4 (MEASURED, source read).** The chain the test measures is the shipped
one: 3×3 Sobel scaled by `0.125` → `box_mean` radius 13 (a 27×27 window,
`focus.rs:83`) → divide by `green_luma_sigma` (`focus.rs:274`) → `regularise`
radius 8 (a 17×17 window, `merge.rs:91`); the statistic is the spatial SD of the
interior at margin 22. So the constant is calibrated on the **regularised**
field. This is exactly the surface M65 could not get behind, and §10 says where
it bites here.

**Fact 5 (MEASURED).** I rebuilt and ran that test myself into a private
`CARGO_TARGET_DIR` (`target-m69/`, never the shared `target/`). Quoted output:

```
   Compiling strehl-core v0.0.0 (C:\dev\blog\death-of-software\projects\strehl\crates\strehl-core)
test merge::tests::the_focus_noise_constant_is_the_measured_one ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 137 filtered out; finished in 0.56s
```

`Compiling` is present, so the artefact is mine (rule: `Finished` alone proves
freshness, not authorship).

**Fact 6 (MEASURED).** Running M43's `calibration-survey` on the crate's own
plant, at the plan the host uses (512², 12 seeds), reproduces the constant and
prices the six operators that were not chosen. `k` is measured SD ÷ the
compiled-in constant:

| operator | measured sd | sem | k |
|---|---|---|---|
| ring-1-3-w13 | 9.792747e-3 | 1.27e-4 | 0.6437 |
| **tenengrad-w13** (shipped) | **1.521126e-2** | 7.57e-5 | **0.9998** |
| tenengrad-sq-w13 | 2.067916e-2 | 1.16e-4 | 1.3592 |
| brenner-w13 | 2.996190e-2 | 3.18e-4 | 1.9694 |
| local-variance-3x3-w13 | 3.773914e-2 | 3.82e-4 | 2.4806 |
| laplacian-w13 | 9.924864e-2 | 1.15e-3 | 6.5235 |
| sml-w13 | 1.005925e-1 | 1.25e-3 | 6.6118 |

**Fact 7 (MEASURED).** The constant is **region-size dependent, and the shipped
value is 0.64% low from its plant size alone.** The same survey at the reference
plan (2048², 8 seeds) gives `1.530923e-2 ± 4.55e-5`, `k = 1.0063`, against 512²'s
`1.521126e-2 ± 7.57e-5`, `k = 0.9998`. The separation is 13 standard errors. The
crate itself records that a 192² region reads about 10% low; the effect does not
stop at 512². This is a real, small, *scale* error in the shipped number, and it
is in the direction M66 pointed — but it is one-thirtieth of the size M66 quoted.

**Fact 8 (DERIVED).** Therefore the honest one-line provenance is: *`FOCUS_NOISE_SD`
is the spatial SD, over a 512×512 interior, of the shipped regularised Tenengrad
response of a signal-free unit-variance white-noise plane.* Every appearance of
it in the codebase — every gate, every published `n_eff`, `DEFAULT_GATE = 4.0`,
and the certified acceptance result — is denominated in that quantity. There is
no part of its provenance I could not reconstruct; the surprise is how little
there is of it.

**Fact 9 (MEASURED, source read).** The calibration seam cannot express the
plant that matters. `strehl-plugin`'s `NoiseSource` offers three variants and
**all three are zero-signal**. There is no way, through M43's seam, to calibrate
this constant on a textured plant. The shipped calibration machinery is
structurally incapable of measuring the quantity the rest of this report shows
dominates it.

---

## 2. D1 — M66's number reproduces exactly

**Fact 10 (MEASURED).** On M62's exact latent (`109MSDCF/DSC00020.ARW`, 2048²
crop at `y=1024, x=4096`, ISO 160, 64 replicates, seed 7), an implementation
written independently of M66's — different box filter construction (summed-area
in float64 rather than `uniform_filter`), different replicate loop — gives:

| plant | M66's K7 | M69 | Δ |
|---|---|---|---|
| FLAT | 1.0018 | **1.0018** | 0.0000 |
| SMOOTH | 1.0690 | **1.0690** | 0.0000 |
| REAL | 1.1921 | **1.1921** | 0.0000 |

**D1: REPRODUCED.** The pre-registered bar was ±0.02 absolute of 1.1921; the
deviation is 0.0000. M66's K7 is arithmetically sound and its instrument is
correct. Whatever is wrong with the 19–21% claim is not an arithmetic error.

**Fact 11 (MEASURED).** FLAT is scale-free to four digits across every latent
tried (1.0018, 1.0071, 1.0071, 1.0072) — a consistency check that the divisor is
doing what it should, and the reason §6 can say the mechanism is not a
signal-level effect.

---

## 3. D1b — and it does not generalise

**Fact 12 (MEASURED).** The same measurement on three further real latents
(32 replicates, seed 11), each the mid-stack frame of a different subject:

| latent | ISO | FLAT | SMOOTH | **REAL** | IQR/median of REAL |
|---|---|---|---|---|---|
| `109MSDCF/DSC00020` (M62's) | 160 | 1.0018 | 1.0690 | **1.1921** | — |
| `coffee-bean/DSC00068` | 50 | 1.0071 | 0.7331 | **0.8380** | 0.3400 |
| `wrapped-text-1/DSC00066` | 100 | 1.0071 | 0.8919 | **1.0274** | 0.4284 |
| `bee-1/DSC00150` | 100 | 1.0072 | 0.8880 | **1.0246** | 0.2848 |

**D1b: NOT MET, and therefore the claim is reported as not supported as a
general statement about real texture.** The pre-registered bar required the real
estimate inside `[1.15, 1.25]` on a *majority* of stacks; it lands there on
**1 of 4** latents. On `coffee-bean` the ratio is **below** 1 — the constant is
16% *high* there, not 19% low. M66 was right to flag K7 as post hoc and right to
refuse to rule on it.

**Fact 13 (MEASURED, corpus-wide).** Using the derived per-pixel predictor of §6
— validated to 2.0% median error and cross-checked against the direct
measurement on all four latents above — evaluated on three frames of every stack
(central 2048² crop):

| stack | N | ISO | median `z` | `rho_obs` | **`rho_true`** | p05 | p95 | IQR/med |
|---|---|---|---|---|---|---|---|---|
| coffee-bubbles | 19 | 1000 | 1.93 | 1.0304 | 0.9686 | 0.6539 | 1.1330 | 0.2305 |
| 109MSDCF | 22 | 160 | 1.10 | 1.0713 | 0.9901 | 0.6412 | 1.1354 | 0.1382 |
| 119MSDCF | 33 | 50 | 1.91 | 1.0141 | 0.9664 | 0.5730 | 1.1963 | 0.2170 |
| 113MSDCF | 63 | 500 | 1.32 | 1.0677 | 1.0097 | 0.7722 | 1.1244 | 0.1060 |
| 112MSDCF | 79 | 500 | 0.70 | 1.1469 | 1.0562 | 0.9144 | 1.1392 | 0.0285 |
| foam | 100 | 1000 | 1.40 | 1.1098 | 1.0263 | 0.7978 | 1.0997 | 0.0606 |
| coffee-bean | 105 | 50 | 2.06 | 0.9388 | **0.9285** | 0.5820 | 1.0892 | 0.2232 |
| wrapped-text-2 | 120 | 400 | 0.75 | 1.1861 | **1.1009** | 0.9798 | 1.4113 | 0.0343 |
| wrapped-text-1 | 130 | 100 | 0.53 | 1.1053 | 1.0047 | 0.5523 | 1.1022 | 0.0349 |
| bee-1 | 299 | 100 | 0.76 | 1.0815 | 1.0196 | 0.7520 | 1.0934 | 0.0504 |
| bee-2 | 299 | 400 | 0.16 | 1.2002 | 1.0631 | 1.0184 | 1.0952 | 0.0171 |
| bee-3 | 299 | 100 | 0.46 | 1.1238 | 1.0343 | 0.8169 | 1.0941 | 0.0252 |

`rho_obs` is the ratio measured the way M66 measured it. `rho_true` corrects the
frozen-latent defect of fact 14. **Corpus `rho_true`: min 0.9285, max 1.1009,
median 1.0147, span 1.186×.**

**Fact 14 (DERIVED, and it explains 1.1921).** M66's REAL plant has a defect
that inflates it, and the defect is in the plant, not the instrument. A real
frame is `T + eta`. M66's replicates are `T + eta_0 + epsilon` — the latent is
*frozen with one realisation of the sensor noise baked in*, so it carries
`E|grad eta|^2 = 2 s^2` of gradient energy that a real frame's latent does not.
Debiasing (`nu_hat^2 = |grad L|^2 − 2 s^2`) and re-evaluating:

| latent | `rho` as measured (frozen eta) | `rho` debiased |
|---|---|---|
| `109MSDCF/DSC00020` | 1.1921 | **1.0985** |
| `coffee-bean/DSC00068` | 0.8380 | 0.8614 |
| `wrapped-text-1/DSC00066` | 1.0274 | 0.9481 |
| `bee-1/DSC00150` | 1.0246 | 1.0176 |

Roughly half of M66's 19% is a frozen-latent artefact. The rest is real, is
scene-specific, and is not a fixed sign. **This is the corrected number M66's
K7 was reaching for, and its arm is A2 plus the §6 predictor.**

---

## 3b. The "second, independent observation" is neither

After M69 was dispatched it was told that the effect had been independently
reproduced: *"M62, the project's acceptance authority, reproduced the effect
independently on its own plant at its own seeds — ρ = 1.2124 at seeds 0 and 1"*,
and that a refutation must therefore explain **two** independent observations
rather than one. I checked, because the same brief told me in its own words that
*"the configuration travels separately from the value and is the first thing
lost."* It did.

**Fact 36 (MEASURED, sources read).** `rho = 1.2124` (seed 0) and `1.2122`
(seed 1) is **M66's own fact 9**, at
[`M66-gate-n-dependence.md`](M66-gate-n-dependence.md):158–163, measured in
**M66's** arm B on M62's plant, `N = 299` synthetic frames, two seeds. It is not
M62's measurement. M62's addendum says so itself, in terms:

> **No re-run.** This ruling is derived from M66's committed report, my own
> committed post-hoc gate sweep at `53c8d47`, and a read-only check of
> `merge.rs` and `main.rs`. **I implemented nothing.**

and its own Labels section lists *"M66's facts as cited"* under MEASURED — the
posture of a citation, not a replication. M62's phrase *"measured on my own
plant"* is accurate and describes the **plant's** provenance: `109MSDCF/DSC00020`
is M62's certified latent, and M66 borrowed it. Somewhere between that phrase and
my brief it became a claim about the **measurer**.

**Fact 37 (DERIVED).** So there is **one** observation, made twice by **one**
milestone with two estimators on **one** plant — a spatial estimator over
replicates (fact 10 here, 1.1921) and a temporal estimator over N = 299 (fact 9
there, 1.2124). They are not independent in any sense that matters: same latent,
same crop, same code, same defect. **A refutation has one thing to explain, not
two, and §3 already explained it.** I record this without editing SYNTHESIS,
which is not mine to touch; SYNTHESIS fact 986 currently asserts the independent
reproduction and the orchestrator should route the correction.

**This does not lower M66's standing and I want that said plainly.** M66 flagged
K7 as post hoc and refused to rule on it. It was right to. The error is
downstream of M66 entirely.

### 3b.1 Reproducing M66's *other* estimator anyway — arm A7

The right response to "it has been reproduced twice" is not to argue about
authorship, so I ran the estimator I had not run.

**Fact 38 (MEASURED).** M66's fact 9 configuration exactly — M62's plant, 2048²
crop at `(y=1024, x=4096)`, ISO 160, **N = 299** synthetic frames, seeds 0 and 1,
temporal SD per pixel:

| seed | mean | median | p05 | p95 | `rho` |
|---|---|---|---|---|---|
| 0 | 0.018213 | 0.018633 | 0.014131 | 0.020789 | **1.1971** |
| 1 | 0.018203 | 0.018625 | 0.014110 | 0.020827 | **1.1965** |
| M66 fact 9 | 0.018446 | 0.018739 | 0.014232 | 0.021563 | 1.2124 |

Deviations **−0.0153** and **−0.0157** against D1's ±0.02 band, so M66's fact 9
also **reproduces**, though not to the zero digits its fact 10 did. Worth noting
before anyone reads significance into the 1.3% gap: **M66's own two estimators
disagree by 1.70% on this one plant** (fact 9 mean 0.018446 against fact 10's
REAL 0.018137), so the residual here is the same size as M66's internal spread
and I draw no conclusion from it.

### 3b.2 A control that could have failed

M69's account of both numbers is the frozen-latent defect of fact 14. Until now
that was algebra checked against P2. Arm A7 made it predict something it could
get wrong.

**Fact 39 (MEASURED).** Freeze `k` independent noise realisations into the latent
instead of one — `L_k = L + sum_{i=2..k} eta_i`, so `k = 1` is M66's plant and
each increment adds exactly the same `2 s^2` of spurious gradient the freeze
already added once. `k` then indexes the defect in known units. Measured at
N = 299, seed 0, against P2 — which was built and validated on the completely
unrelated A3 synthetic sweep and knows nothing of this construction:

| `k` | `rho` measured | P2 predicted | error |
|---|---|---|---|
| 1 (M66's plant) | 1.1971 | 1.1830 | −0.0141 |
| 2 | 1.2428 | 1.2289 | −0.0138 |
| 3 | 1.2714 | 1.2568 | −0.0146 |

Bars were fixed in the arm's docstring before it ran: level within 0.05 absolute,
**and separately** the `k=1→3` step within 30% of that step, because a predictor
anchored at roughly the right level can still get the slope wrong.

* **Level: MET** — worst error 0.0146 against 0.05.
* **Slope: MET** — measured step **+0.0743**, P2 **+0.0738**, miss **0.0005**
  against a bar of 0.0223. P2 forecasts the defect's slope to **0.7% of its own
  size**.

`rho` rises monotonically with `k` exactly as the mechanism requires. Had it been
flat, or fallen, or had P2 missed the step, M69's account of 1.1921 and 1.1971
would have collapsed. It did not.

**Fact 40 (MEASURED / DERIVED).** Back-extrapolating to `k = 0` — the defect-free
plant, which **cannot be built from one real frame**, because the only way to
observe a latent without a frozen noise realisation in it is to average many
frames at one focus position, which is the static burst that does not exist:

| method | `rho(0)` |
|---|---|
| linear back-step from `k` = 1, 2 (MEASURED) | 1.1514 |
| quadratic back-step from `k` = 1, 2, 3 (MEASURED) | 1.1343 |
| P2 on the debiased gradient (DERIVED) | **1.0985** |

The back-steps extrapolate outside their own range on a concave curve, so they
bracket high; P2 is the better estimate and the ladder bounds it. **The freeze
accounts for roughly a quarter to a half of M66's excess over 1.0** on this
latent — `0.1971` of excess, of which `0.046`–`0.099` is artefact. The remainder
is a real property of this particular crop, and fact 13 shows that crop is
unrepresentative of the corpus.

---

## 4. Controls, with their pre-registered consequences

| id | bar | result | verdict |
|---|---|---|---|
| **K0** (structural) | Sobel constants match closed form | component SD 0.433257 / 0.433312 vs `0.125·sqrt(12) = 0.433013`; `corr(gx,gy) = +0.000511` vs 0; `E\|grad\|` 0.543046 vs Rayleigh `s·sqrt(pi/2) = 0.542701`; `SD\|grad\|` 0.283851 vs `s·sqrt(2−pi/2) = 0.283682`; `C_xx(0,±2)/C_xx(0,0) = −0.500` exactly | **MET** |
| **K1** — my pipeline reproduces the constant on the crate's own plant | `\|rho−1\| ≤ 0.02` | `1.541341e-2 ± 1.50e-4`, **`rho = 1.0131`**; 1.20σ from the crate's 12-seed value | **MET** |
| **K1b** (post hoc) — temporal estimator on the same plant | same bar | `rho = 1.0031` | **MET** |
| **K2** — my Python field *is* the shipped Rust field | mean `n_eff` within **0.2%** of the shipped binary at gates 0.5/1/2/4 on ≥2 real stacks | worst deviation **0.031%** (see fact 15) | **MET** |
| **K3** — A5's structure-function estimator recovers a known `sigma_F` | within 5% | recovery 25.93 (coffee-bean), 5.24 (wrapped-text-1), 4.46 (109MSDCF) | **NOT MET** |
| **K4** — A5's stacks are not dominated by photometric drift | reported | frame-to-frame relative level SD 0.9292% / 0.2061% / 0.3328%, full span 14.30% / 1.3052% / 1.0246% — corroborates [`M24`](M24-photometric-drift-measured.md), not re-derived | reported |
| **K5** — A3's plant *is* the calibration plant at zero texture | `rho(nu/s=0) = 1.00 ± 0.02` | `1.521949e-2`, **`rho = 1.0004`** | **MET** |
| **K6** — the instrument can detect a wrong answer (rule 39) | planted 1.30 reads 1.30 ± 0.01 | recovered **1.3000** | **MET** |
| **K7** — my Python merge reproduces M62's certified number | 5.4316 ± 0.010 at gate 4 | **not attempted** | **NOT MET** |
| **K8** (post hoc) — real half-split noise matches the model | ±10% | ratios 2.1847 / 2.4041 / 0.9109 / 1.0953 | **NOT MET** |
| **K9** (post hoc, arm A7) — the frozen-latent mechanism predicts a *level* | \|P2 − measured\| ≤ 0.05 at `k` = 1, 2, 3 | worst 0.0146 | **MET** |
| **K10** (post hoc, arm A7) — and predicts the *slope*, which a level-anchored predictor can still get wrong | P2's `k`=1→3 step within 30% of the measured step | measured +0.0743, P2 +0.0738, **miss 0.0005** against a 0.0223 bar | **MET** |

**Fact 15 (MEASURED).** K2 is the control that makes every Python number in this
report a statement about the shipped binary. Running the full winner election and
noise gate in Python over the entire plane (2344×3514) of two real stacks, in two
streaming passes, against the mean `n_eff` the shipped binary printed for itself:

| stack | gate | tolerance | shipped `n_eff` | M69 `n_eff` | rel |
|---|---|---|---|---|---|
| 109MSDCF | 0.50 | 0.010758 | 1.414 | 1.414 | −0.031% |
| 109MSDCF | 1.00 | 0.021516 | 1.884 | 1.884 | +0.022% |
| 109MSDCF | 2.00 | 0.043032 | 2.891 | 2.891 | +0.004% |
| 109MSDCF | 4.00 | 0.086063 | 4.987 | 4.987 | −0.007% |
| coffee-bubbles | 0.50 | 0.010758 | 1.238 | 1.238 | +0.011% |
| coffee-bubbles | 1.00 | 0.021516 | 1.504 | 1.504 | −0.006% |
| coffee-bubbles | 2.00 | 0.043032 | 2.109 | 2.109 | +0.007% |
| coffee-bubbles | 4.00 | 0.086063 | **3.529** | **3.529** | −0.001% |

Worst 0.031% against a 0.2% bar. The gate-4 `coffee-bubbles` value **3.529** and
the whole seven-stack table of §8 also reproduce [`M64`](M64-estimator-default.md)
§2.4 exactly, from a binary I built myself.

**Consequences honoured.**

* **K3 NOT MET → arm A5 is void, and D1b rests on A3 alone. I say so in the
  headline and I say so here.** The pre-registered structure-function estimator
  does not recover a planted `sigma_F` on a synthetic sequence carrying a smooth
  focus drift; it over-reads by 4.5×–26×. A Savitzky–Golay variant met the 5% bar
  on exactly one stack (0.9574 on 109MSDCF) and I am not promoting a one-of-three
  result to an arm. Section 7 gives the root cause and why it is *not measurable*
  rather than merely not measured.
* **K7 NOT MET → the re-pricing of M62's number in A6 is withdrawn as a
  measurement and replaced by an interval bounded by M62's own published ladder,
  labelled DERIVED.** That is exactly what §8's A6.3 is: an interpolation of
  M62's published gates, checked to reproduce 5.43162 at gate 4 to +0.0000%. I
  did not attempt an independent reproduction of M62's acceptance harness; once
  the linearity identity of fact 21 made the re-pricing exact against M62's own
  ladder, rebuilding the harness inside M69 bought nothing it could not already
  have, and it would have been M69 grading M62's arithmetic rather than pricing
  M69's finding. That is a judgement, and the consequence stands regardless of
  whether the judgement was right: **A6.3 is DERIVED, not MEASURED.**
* **K8 NOT MET → the half-split figures are not quotable as a real-noise
  measurement of `sigma_F`.** The green half-split ratio (real ÷ matched
  synthetic) is 2.18 and 2.40 on two latents and 0.91 and 1.10 on two others; the
  excess is fixed-pattern structure that does not cancel between G1 and G2
  (`M62/109MSDCF` half-split 0.038033 vs matched synthetic 0.017409). M62's P17
  (G1/G2 temporally correlated at `+0.073`) biases the split down by only ~3.7%
  — far too little to rescue it. I therefore do not use the half-split anywhere
  in this report's conclusions; the real-noise evidence is the dark frames
  instead (fact 24).

---

## 5. D2 — the scalar form is refuted

The pre-registered wording: *"The scalar form is **refuted** if either (a) the
across-pixel interquartile range of `sigma_hat_F(p)` within a single stack
exceeds ±10% of that stack's median on a majority of stacks; or (b) the per-stack
`rho` spans more than 1.10× across the arms and stacks measured."*

**Fact 16 (MEASURED).** Clause (a): `IQR/median > 0.20` on **4 of 12** stacks
(coffee-bubbles 0.2305, 109MSDCF — 0.1382 — no; 119MSDCF 0.2170, coffee-bean
0.2232, and the two latents of fact 12 at 0.34 and 0.43). Four is not a majority.
**Clause (a) is not satisfied.**

**Fact 17 (MEASURED).** Clause (b): per-stack `rho_true` spans **1.186×**
(0.9285 → 1.1009), which exceeds 1.10×. Across the *arms* — the pre-registration
says "arms and stacks" — the controlled plant of A3 spans **4.06×** (0.2805 →
1.1386, fact 18). **Clause (b) is satisfied, decisively.**

**D2: the scalar form is REFUTED, via clause (b).** It is refuted on the corpus
by a 1.186× margin and on a controlled plant by a 4.06× margin. It is *not*
refuted by clause (a), and I report that separately because it matters: within
most stacks the interquartile spread is modest, and the shipped scalar is a
defensible *average*. What it is not is a *per-pixel* statement, which is what
`Gate::admits` uses it as.

---

## 6. What actually drives it, and whether the per-pixel form is derivable

### 6.1 The pre-registered predictor is wrong (D3)

**Fact 18 (MEASURED).** A transfer curve on a bandlimited synthetic plant under
the unit-sigma model (48 replicates, 512²), sweeping the deterministic gradient
magnitude `nu/s` against the texture correlation length `ell`:

| `ell` | `rho` at `nu/s → 40` |
|---|---|
| 2 | **1.1386** |
| 4 | 0.7425 |
| 8 | 0.4518 |
| 16 | **0.2805** |

**`rho` is not a function of `nu/s` at all.** At `ell = 2` it rises with signal;
at `ell = 16` it falls by a factor of 3.6. The pre-registered predictor P1 —
pointwise Rice, i.e. "rectification of a noisy gradient magnitude inflates its
variance toward the Rice ceiling `r(inf) = 1/sqrt(2−pi/2) = 1.5264`" — predicts
a monotone rise to 1.50 in every case, with errors up to **−78%** and the wrong
*sign* for every `ell ≥ 4`.

**D3: NOT MET for P1.** As pre-registered I report "not derivable at this order"
for the pointwise predictor and name the missing term rather than fitting one.
The missing term is spatial: P1 treats the 27×27 window as averaging independent
rectified samples, and it does not.

**Fact 19 (DERIVED, mechanism).** The real mechanism (call it **M-c**) is that
the Sobel stencil has **zero DC gain**. Where the deterministic gradient
*direction* is coherent across the 27×27 window, the projection of the noise onto
that direction telescopes to a few edge columns of the window and nearly cancels;
where the direction scrambles faster than the window, it does not. Long
correlation length ⇒ coherent direction ⇒ *less* response noise, not more. The
lag-2 anti-correlation of the stencil is exact and drives it:
`C_xx(0,±2)/C_xx(0,0) = −0.500` (fact K0). This is why texture *reduces*
`sigma_F` on smooth-but-strong subjects like `coffee-bean` and *raises* it on
fine-grained ones.

**Fact 20 (MEASURED).** The competing mechanism — that the `green_luma_sigma`
divisor is itself noisy (**M-b**) — is a minor player. Freezing the divisor at
the clean latent changes `rho` from 1.1835 to 1.1647 on M62's latent
(**+1.61%**) and from 0.8329 to 0.8297 on coffee-bean (**+0.39%**).

### 6.2 A derived per-pixel form does exist — but it is post hoc

**Fact 21 (DERIVED, POST HOC — not pre-registered, and I flag it as M66 flagged
K7).** After P1 failed I built a second, still parameter-free predictor, **P2**.
It is post hoc: it was constructed after seeing fact 18, and nothing in the
pre-registration anticipates it. Its form:

decompose `delta|grad|_q ≈ alpha(z_q) · (dhat_q · delta grad_q) + xi_q`, where
`alpha(z) = dE_Rice/d nu` is the exact linear-regression coefficient at local
signal-to-noise `z`, and `Var(xi) = Var_Rice(z) − alpha^2 s^2`. Propagate the
*linear* part exactly through the shipped operator using the closed-form 5×5
Sobel cross-correlations `C_ab(Delta)` and `G_Delta(t) = K(t)K(t−Delta)` with
`K = box27 (x) box17`; propagate the residual as white noise **anchored at
`FOCUS_NOISE_SD`**, which is precisely the `z = 0` limit the crate measured:

```
sigma_F^2(p) = Var_lin(p) + FOCUS_NOISE_SD^2 * <Var(xi)_q / Var(xi)_0>_{K^2}
```

**Fact 22 (MEASURED).** P2's accuracy: **median |predicted/measured − 1| = 2.01%,
worst 5.44%**, over the whole `ell × nu/s` sweep spanning `rho` 0.28→1.15. On the
four real latents: +0.77% (M62), −2.21% (coffee-bean), −2.34% (wrapped-text-1),
−2.77% (bee-1). At a *different* noise scale (the half-split's synthetic arm) it
gives 1.1830 vs 1.1909, 0.8569 vs 0.8607, 1.0520 vs 1.0821, 1.0538 vs 1.0538.
Had P2 been the pre-registered predictor, D3 would have been MET at 2.0% against
a 10% bar. **It was not, so D3 stands as NOT MET, and P2 is offered as a derived
hypothesis for a future milestone to pre-register and test, not as a result.**

**Fact 23 (DERIVED).** P2 also settles the question in the brief's §3 — *is the
focus response's noise derivable from `sigma^2(S) = gS + (RN·g)^2` per-pixel?*
**Yes in form, no in level.** The per-pixel *shape* is fully derivable from the
sensor model plus locally observable gradient statistics with no free parameters.
The *anchor* is not: P2 still normalises against `FOCUS_NOISE_SD` at `z = 0`, and
`1/sum K^2 = 1165.6` effective taps against the crate's claimed 348 effective
independent samples means the rectified residual carries a further 3.35×
correlation cost that the anchor silently absorbs. The `z = 0` level remains
certified by nothing but the crate's own synthetic plant. That is the circularity
of §10 and it is not removed.

---

## 7. Real sensor noise, and the thing that is *not measurable* here

**Fact 24 (MEASURED).** Dark frames are the only zero-texture arm in this
milestone whose noise is real rather than synthetic. Eleven ISO groups from
`D:\macro-dark-frames`, first two frames of each discarded as stabilisation, 20
used, central 2048² crop:

| group | ISO | emp read DN | model `RN·g` | ratio | **`rho_dark`** | clipped |
|---|---|---|---|---|---|---|
| 118MSDCF | 100 | 0.8870 | 0.9615 | 0.9225 | **1.1383** | 33.5% |
| 119MSDCF | 400 | 0.9947 | 1.1348 | 0.8766 | 1.1294 | 35.7% |
| 120MSDCF | 800 | 1.7252 | 2.2696 | 0.7601 | 1.0930 | 42.5% |
| 121MSDCF | 1600 | 3.3162 | 4.5392 | 0.7306 | 1.0554 | 43.0% |
| 122MSDCF | 50 | 0.8870 | 0.9615 | 0.9225 | 1.1227 | 34.3% |
| 123MSDCF | 200 | 1.4681 | 1.9231 | 0.7634 | **1.0190** | 28.1% |
| 124MSDCF | 640 | 1.4244 | 1.8157 | 0.7845 | 1.0664 | 31.8% |
| 125MSDCF | 500 | 1.1821 | 1.4185 | 0.8333 | 1.1307 | 37.7% |
| 126MSDCF | 250 | 1.7918 | 2.4038 | 0.7454 | 1.0579 | 36.7% |
| 127MSDCF | 1000 | 2.1398 | 2.8370 | 0.7543 | 1.0897 | 43.8% |
| 128MSDCF | 2000 | 4.1852 | 5.6740 | 0.7376 | 1.0488 | 47.6% |

Two findings. First, **the shipped profile over-predicts read noise by 8–27%** at
every ISO measured — empirical read noise runs 0.73×–0.92× the model's `RN·g`.
That is a sensor-profile matter and I flag it for whichever milestone owns the
profile rather than pursuing it. Second, **`rho_dark` runs 1.019–1.138 — every
value above 1** — even though 28–48% of pixels clip at the black level, which
should *reduce* measured noise.

**Fact 25 (ARGUED, not measured).** The likely explanation of fact 24's second
finding is that real sensor noise is not white: row and banding correlation
survives the 27×27 and 17×17 box filters, which suppress white noise by ~1166
effective taps but suppress a row-coherent component by far less. I did not
measure this. The cheap decisive test is the lag-1 row-versus-column
autocorrelation of the dark temporal residuals, and I name it rather than assert
the mechanism.

**Fact 26 (MEASURED, upper bounds only).** A5's direct attempt on real stacks
gives only upper bounds, because K3 failed. Total frame-to-frame response scatter
in units of `FOCUS_NOISE_SD`: coffee-bean 72.65 (structure function) / 35.74
(Savitzky–Golay); wrapped-text-1 19.28 / 12.10; 109MSDCF 4.02 / 2.32. These are
dominated by real focus change, which is the point.

**Fact 27 (DERIVED — this is "not measurable", not "not measured").** A5 failed
for a structural reason, not a coding one. **Macro depth of field is one to two
frames wide by design**, so a per-pixel through-focus curve is a narrow peak that
no smoothing estimator with a window wide enough to average down the noise can
follow. On a focus sweep, focus change and response noise are not separable at
the per-pixel level by any estimator of this family. The measurement requires a
sequence in which focus does **not** move — a static burst — and the brief's
claim that one was delivered is false (§0). **This is the one quantity in M69
that cannot be measured from the corpus that exists.** M62's observation that a
static burst has no interior optimum is correct and is exactly why a burst
cannot arbitrate a *gate*; it is also exactly why a burst is the only thing that
*can* arbitrate a *noise level*, because with focus held still every frame-to-frame
response difference is noise by construction. The two facts are complementary,
not in tension.

---

## 8. A6 — the blast radius, priced

**Fact 28 (DERIVED, and it is why no code change was needed).** `Gate::tolerance()
= T · sqrt(2) · FOCUS_NOISE_SD` is exactly linear in the constant. Therefore
running the shipped binary at `--gate T·rho` is arithmetically identical to
running gate `T` with the constant scaled by `rho`. **Every number below was
priced by running the shipped merge at rescaled gates; nothing under `crates/`
was touched.** I built the CLI myself into `target-m69/` (`Compiling strehl-cli`
observed) and ran a 17-rung gate ladder on all seven M64 guard stacks.

**Fact 41 (MEASURED, source read — M62's linearity claim, checked rather than
accepted).** M62's addendum derives the same identity and a good deal now rests
on it, so I was asked to check it against the code independently rather than
rely on M62's reading. `FOCUS_NOISE_SD` appears **17 times** in `merge.rs`.
Sixteen are documentation (`:62`, `:200`, `:228`, `:1078`, `:1107`, `:1114`), the
declaration (`:185`), the calibration test's own assertions (`:1268`, `:1272–3`,
`:1317`, `:1319`) and test fixtures (`:1630`, `:1640`, `:1653`, `:1728`).
**Exactly one is on the gate path:**

```
311: self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
```

A bare product, no additive term, no second use. **M62's linearity claim is
CONFIRMED by independent reading**, and fact 28 was derived the same way before
M62's addendum was available to me.

**Fact 29 (MEASURED).** Recalibrating each stack to its own `rho_true` (fact 13):

| stack | N | `rho_true` | `n_eff@4` | `n_eff/N` | `n_eff@4rho` | `n_eff/N` | change |
|---|---|---|---|---|---|---|---|
| 109MSDCF | 22 | 0.9901 | 4.987 | 0.22668 | 4.944 | 0.22471 | −0.87% |
| 112MSDCF | 79 | 1.0562 | 12.037 | 0.15237 | 12.425 | 0.15728 | +3.23% |
| 113MSDCF | 63 | 1.0097 | 8.581 | 0.13621 | 8.628 | 0.13695 | +0.55% |
| 119MSDCF | 33 | 0.9664 | 4.723 | 0.14312 | 4.605 | 0.13955 | −2.49% |
| coffee-bean | 105 | 0.9285 | 31.614 | 0.30109 | 30.740 | 0.29276 | −2.76% |
| coffee-bubbles | 19 | 0.9686 | 3.529 | 0.18574 | 3.436 | 0.18083 | −2.64% |
| foam | 100 | 1.0263 | 1.359 | 0.01359 | 1.368 | 0.01368 | +0.69% |

**M64's corpus-wide degeneracy guard is untouched.** Worst `n_eff/N` moves from
0.30109 to 0.29276 — the margin to the `0.95` guard *improves*, 3.16× → 3.24×.
M64's published **22.15×** cross-stack spread becomes **21.39×**: a 3.4% change
in a quantity M66 has already shown is 72% frame count. **Nothing in M64 changes
qualitatively.**

**Fact 30 (DERIVED — K7 NOT MET, so this is an interval bounded by M62's own
published ladder, per the pre-registered consequence).** Interpolating M62's own
seven published gates with a monotone PCHIP in log-gate (reproducing 5.43162 at
gate 4 to +0.0000%):

| `rho` | gate | `R` | vs `sqrt(30)` | **vs certified** |
|---|---|---|---|---|
| 0.2800 (A3 worst plant) | 1.1200 | 2.16323 | −60.505% | −60.173% |
| 0.7500 | 3.0000 | 4.97433 | −9.182% | −8.419% |
| 0.8380 (coffee-bean, M66's method) | 3.3520 | 5.23468 | −4.428% | **−3.626%** |
| 0.9285 (**corpus minimum**) | 3.7140 | 5.38883 | −1.614% | **−0.788%** |
| 1.0000 (shipped) | 4.0000 | 5.43162 | −0.833% | +0.000% |
| 1.0147 (**corpus median**) | 4.0588 | 5.43349 | −0.799% | +0.034% |
| 1.1009 (**corpus maximum**) | 4.4036 | 5.44325 | −0.620% | +0.214% |
| 1.1921 (M66's number) | 4.7684 | 5.45166 | −0.467% | **+0.369%** |

**M62's certified `5.431624` survives every recalibration this milestone can
justify.** The worst corpus-justified case is `rho = 0.9285`, costing **−0.788%**
— inside M62's own pre-registered 1% harness tolerance. **I am not asking M62 to
re-rule, because on the evidence in this report there is nothing to re-rule.**

**Fact 31 (DERIVED).** The certification is nonetheless **asymmetrically robust**,
and this is the part worth carrying forward. Because M62 ruled that its objective
saturates above gate 8, loosening the gate is nearly free: `rho = 1.1921` costs
+0.369%, `rho = 1.30` costs +0.514%. Tightening it is not: `rho = 0.8380` costs
−3.626% and **breaks the 1% tolerance**; `rho = 0.75` costs −8.419%. The
certified result is robust in exactly the direction M66's number pointed and
fragile in the direction three of the four latents in fact 12 point. **If a
future milestone finds a corpus `rho` below about 0.95, M62's certification does
come into question and M62 — not M69 — must rule.** I state that as a
conditional, and it is the only statement in this report that touches the
acceptance authority.

**Fact 32 (MEASURED, and it is the largest number in this section).** A uniform
rescale is the *small* change. Bounding what a genuinely per-pixel `sigma_F`
would do, by running the ladder at 4×p05 and 4×p95 of each stack's own per-pixel
distribution:

| stack | p05 | p95 | `n_eff@4·p05` | `n_eff@4` | `n_eff@4·p95` | swing |
|---|---|---|---|---|---|---|
| 109MSDCF | 0.6412 | 1.1354 | 3.481 | 4.987 | 5.597 | **1.61×** |
| 112MSDCF | 0.9144 | 1.1392 | 11.392 | 12.037 | 12.979 | 1.14× |
| 113MSDCF | 0.7722 | 1.1244 | 7.311 | 8.581 | 9.133 | 1.25× |
| 119MSDCF | 0.5730 | 1.1963 | 3.145 | 4.723 | 5.403 | **1.72×** |
| coffee-bean | 0.5820 | 1.0892 | 18.806 | 31.614 | 32.301 | **1.72×** |
| coffee-bubbles | 0.6539 | 1.1330 | 2.536 | 3.529 | 3.931 | 1.55× |
| foam | 0.7978 | 1.0997 | 1.285 | 1.359 | 1.397 | 1.09× |

**1.09×–1.72×, against ±3.2% for any global rescale.** Adopting a per-pixel
`sigma_F` is a 20–50× larger intervention than correcting the constant, and it is
the intervention the evidence actually supports. **This arm cannot price it
further**: a per-pixel tolerance is a change under `crates/`, which M69 may not
make. What is bounded above is the range, not the effect — the two are different,
and the sign of the net effect on any published number is unknown.

**Fact 33 (DERIVED).** Two errors in the same quantity, and their directions now
resolve. M66's headline is that `tolerance()` has **no `N` term** while the
expected maximum of `N` noisy responses grows with `N`, eroding gate-4 headroom
by 18% over `N ∈ [19, 299]` — an effect that makes the *effective* gate
**tighter** as `N` grows. M69 finds the constant itself is not systematically
low: corpus median `rho_true = 1.0147`, i.e. **+1.5%, essentially nil**, with the
only *systematic* scale error being the +0.64% plant-size bias of fact 7, also in
the loosening direction. **They do not compound.** The `N` effect is real and
one-sided; the constant's error is scene-dependent and two-sided and about a
tenth the size. M66's chartered finding survives M69 intact; M66's post-hoc K7
does not.

### 8.2 The acceptance-battery limb — deferring to M62, which priced it first

M62's addendum `e4c1f98` priced this limb by algebra while M69 was running, and
asked M69 not to redo it. I am not redoing it. What follows is what M62
established, cited rather than re-derived, and how it relates to fact 30.

**Fact 42 (DERIVED by M62, cited).** From
[`M62-ruling-M64-addendum.md`](M62-ruling-M64-addendum.md) §4: the
estimator-versus-selector verdict is **robust roughly eight-fold**, because even
at gate 1 — a 4× σ error — `DEFAULT` scores **1.9710** against
`SELECTOR-same-binary`'s **0.9773**. And the battery's **power arm is exactly
σ-invariant**, because at gate 0 the tolerance is `0 · sqrt(2) · sigma_F = 0`
identically for any `sigma_F`. **Neither of those depends on anything M69
measured, and M69 confirms neither is disturbed by anything it found.**

**Fact 43 (DERIVED).** Fact 30 is a **different quantity** and the two do not
overlap. M62's ≈8× robustness is about the *verdict* — whether the default path
estimates or selects. Fact 30 is about the *headline number* `5.431624` against
its own ±2% window and the harness's 1% tolerance, which M62 is precisely the
party that withdrew the unconditional form of. The two ladders agree where they
meet: M62's post-hoc sweep at `53c8d47` reads `0.9773 / 1.3616 / 1.9710 /
3.7610 / 5.4354 / 5.4849` against the certified ladder's `0.97682 / 1.35937 /
1.96845 / 3.77637 / 5.43162 / 5.47768` — **0.07% apart at gate 4**. Fact 30
interpolates the *certified* ladder, because that is the one under certification.

**M62's conditional resolves in M62's favour on M69's evidence.** Its `DEFAULT`
window tolerates a 2.5% `n_eff` loss; the corpus-justified recalibration costs at
most 2.8% on one stack (`coffee-bean`, fact 29) and −0.788% on the certified
objective. **M69's recommendation is that the constant's value not change at
all** (§9), which resolves the condition without any movement. **M62 remains the
acceptance authority; this is M69 reporting an input, not M69 ruling.**

### 8.3 The limb neither M62 nor M65 priced — the election comparison

**Fact 44 (MEASURED — the number M65 said it could not reach).** M65's
circularity is that `FOCUS_NOISE_SD` is calibrated on the **regularised** field,
so arm X — the arm built to break that circularity by turning the regulariser off
— is still scored in units derived from it. M65 worked around this with a
matched-unit arm X′ using `k_sd = 1.2377`, obtained as a **ratio**. Measuring the
raw field's constant **directly** on the crate's own calibration plant, through
the pipeline that reproduces the shipped constant to 1.3% (K1):

| field | measured SD | |
|---|---|---|
| raw focus field | **1.904436e-2 ± 1.44e-4** | ← the constant a raw-election merge needs |
| regularised field | 1.541341e-2 ± 1.50e-4 | shipped constant 1.521400e-2 |

`k_sd = 1.23557`, against M65's **1.23770** — **−0.17%**. The regulariser removes
**19.1%** of the response noise, against M65's 19.2%. **M65's fact 3 reproduces
independently, and from an absolute measurement rather than a ratio.**
`FOCUS_NOISE_SD_raw = 0.019044` is the number M65's arm X would need if it were
ever shipped; it has not existed until now.

**Fact 45 (MEASURED).** M65's D1 is a long way from being overturned. `dev(rho_W)`
is monotone *decreasing* in the gate (M65 fact 10), so by fact 41's linearity a
`rho < 1` recalibration moves M65 **toward** the regime where the election field
is load-bearing. Solving M65's own published rows for the crossing of its 1.332
bar, by monotone PCHIP in log-gate — no re-run:

| stack | `dev@4` | crossing gate | `rho_crit` | corpus `rho_true` | headroom |
|---|---|---|---|---|---|
| 109MSDCF | 1.0827 | 0.5487 | 0.1372 | 0.9901 | 7.22× |
| 119MSDCF | 1.1076 | 0.8198 | 0.2049 | 0.9664 | 4.72× |
| 113MSDCF | 1.1793 | 2.7087 | 0.6772 | 1.0097 | **1.49×** |
| coffee-bubbles | 1.2335 | 2.6630 | 0.6658 | 0.9686 | **1.45×** |

**σ would have to fall by 33% to overturn M65's D1; the corpus says at most 7%.**
Worst headroom **1.45×**. M65's *"not load-bearing at the shipped gate"* stands
under every recalibration M69 can justify.

**Fact 46 (MEASURED, and it is a form error in M65's instrument, not a value
error).** `k_sd` is itself texture-dependent, and far more strongly than the
regularised field is. Measured on the four real latents (24 replicates each):

| latent | `rho` regularised | `rho` raw | `k_sd` here | vs M65's plant value |
|---|---|---|---|---|
| M62 / 109MSDCF | 1.1889 | 2.4017 | **2.0202** | 1.632× |
| coffee-bean | 0.8357 | 1.3957 | 1.6700 | 1.349× |
| wrapped-text-1 | 1.0255 | 1.3921 | 1.3575 | 1.097× |
| bee-1 | 1.0221 | 1.4385 | 1.4073 | 1.137× |

**`k_sd` runs 1.3575–2.0202 on real texture — a 1.488× span — against the single
plant value 1.2377 M65 used.** The mechanism is fact 19 read twice: the raw field
keeps the fine-scale structure that drives direction incoherence, and
regularisation is precisely what removes it, so the raw field's texture
dependence is the stronger of the two. **The error is in the conservative
direction for M65 and its conclusion is safe**: a `k_sd` too small makes arm X′'s
tolerance too tight, `dev` too high, and crossing the bar *more* likely — and M65
reports X′ never crossed at any gate on any stack (max `dev` 1.2835). A larger
`k_sd` only lowers that further. **But M65's arm X′ is a single-scalar unit
conversion between two fields whose ratio is not a scalar, and any future
milestone converting between them inherits the same form error M69 found in the
constant itself.**

---

## 9. Should it be a constant at all?

**Fact 34 (DERIVED).** Three answers, and they are different questions.

1. **As a corpus-wide scalar, the shipped value is fine.** Median `rho_true`
   1.0147, span 1.186×. Correcting it to any corpus-justified value buys ±3%
   in `n_eff` and ≤0.8% in M62's objective. **This is not worth a recalibration
   on its own**, and I recommend against changing the number.
2. **As a per-pixel statement — which is how `Gate::admits` uses it — it is
   wrong, and materially so.** Fact 18 (4.06× on a controlled plant), fact 16
   (p05–p95 up to 2.0× within one stack) and fact 32 (1.09×–1.72× in `n_eff`)
   are the evidence. `docs/research/` §4.1 already demolished "constants" in
   favour of profiles-as-data and M43 built the seam; **this constant is the one
   that most deserves that treatment and the one the seam cannot currently
   express** (fact 9).
3. **The right form is not a profile entry either.** A profile is still a
   per-camera scalar. Fact 18 shows the dominant variable is neither camera nor
   ISO nor signal level but *texture directional coherence*, which varies within
   a single frame. The right form is a **per-pixel field computed at merge time
   from the sensor model and the local gradient statistics**, of which P2
   (fact 21) is a candidate. Its anchor is still the crate's synthetic constant,
   so it reduces the constant's role from *the* scale to *a* boundary condition
   at `z = 0` — which is progress and is not closure.

**I recommend the orchestrator route: (a) no change to `FOCUS_NOISE_SD`'s
value; (b) a milestone chartered to pre-register and test P2 as a per-pixel
field, with the burst capture of §11 in hand first; (c) the sensor-profile
agent to see fact 24's 8–27% read-noise over-prediction.**

### 9.1 Auditing the replacement for the defect the corpus is now suspicious of

M62 took M66's finding about the *subject* and applied it to its own
*instrument*, and found the identical defect: guard G is a fixed 0.95 line
against a statistic whose null drifts with N, with nothing in G's statement
mentioning N. Its words: *"my guard has the same shape of error as the thing it
polices."* The same test must be run on anything M69 proposes, and it does not
come out clean.

**Fact 47 (DERIVED). P2 has no `N` term, and inherits the defect verbatim.**
Replacing a scalar `sigma_F` with a per-pixel field does **nothing** about M66's
headline. The gate compares each frame against `max_j X_j(p)`, whose expected
value drifts upward with `N` by `c_N` — 1.032 `sigma_F` over the corpus's own
range, an 18% erosion of gate-4 headroom. A per-pixel `sigma_F` changes the
denominator of that comparison, not the numerator's `N`-dependence. **A merge
that adopted P2 and stopped there would have replaced one `N`-blind quantity with
a better-shaped `N`-blind quantity.** I state this as the first item because it
is the one I would otherwise have been most tempted to leave out.

Four further undeclared domains, named so that whoever charters the follow-up
declares them rather than discovering them:

1. **Region size.** P2's anchor is `FOCUS_NOISE_SD`, which fact 7 shows is a
   spatial-SD statistic on a *finite* region: 512² gives 1.521e-2 and 2048²
   gives 1.531e-2, thirteen standard errors apart, and the crate itself records
   192² reading 10% low. **P2 therefore carries an undeclared region-size domain
   of `≥ 512²` that nothing in its formula mentions.**
2. **Field.** P2 was built and validated on the **regularised** field only. Fact
   46 shows the raw field's texture dependence is 1.10×–1.63× stronger, so P2 is
   **not** transferable to a raw-election merge without re-derivation, and
   nothing in P2's statement says so.
3. **Stationarity.** The residual term averages `Var(xi)` over the combined
   kernel `K²`, which assumes the local gradient statistics are stationary across
   a 27×27 ⊛ 17×17 support. That assumption is weakest exactly at edges — which
   is where fact 19's direction-coherence mechanism is strongest and where P2 is
   most needed.
4. **ISO, by omission.** P2 is scale-free in noise magnitude: the `sigma`
   divisor cancels, which is why fact 11's FLAT arm is level-independent to four
   digits. That is correct behaviour on the shipped chain, but it means **P2
   cannot see** the 8–27% read-noise over-prediction of fact 24. It inherits the
   profile's error silently rather than exposing it.

**None of these is a reason to keep the scalar.** They are the domain statement
the replacement must ship with, which is the thing the scalar never had.

---

## 10. The circularity I could not remove

**Fact 35 (ARGUED).** I was calibrating the constant that every instrument
available to check it is denominated in. Four places it bites, and where it does
not:

1. **It bites at the anchor.** `FOCUS_NOISE_SD` is calibrated on the
   *regularised* field (fact 4), so any statistic scored in its units inherits
   it — M65's finding, and M69 does not escape it either. P2 breaks it only
   *partially*: P2 derives the per-pixel *shape* independently but **anchors the
   level on the constant at `z = 0`** (fact 23). The `z = 0` level is certified
   by nothing but the crate's own synthetic plant.
2. **It does not bite on the ratios.** Everything in §§2–6 is a *ratio* of the
   same operator's output on two plants. The constant cancels. Facts 10, 12, 13,
   16, 18 and 22 are unaffected by whether the anchor is right; they would be
   the same numbers if the constant were 0.02 or 0.01. This is the part of M69
   that is circularity-free, and it is the part carrying the headline.
3. **It bites hardest where I have the least evidence.** The one arm with real
   noise and no texture — the dark frames (fact 24) — reads `rho_dark` 1.019–1.138,
   *every value above 1*. If that is not clipping artefact (28–48% of pixels clip)
   then **the anchor itself is 2–14% low on real sensor noise**, and P2's whole
   scale moves with it. I could not resolve this without the burst capture of §11.
   I flag it rather than fold it in.
4. **M62's objective cannot arbitrate.** It is scored with the same gate the
   constant defines, and M62 itself ruled that it saturates at gate 8 — so it
   cannot be used to choose a gate. Fact 30 uses it only to *price* a change, in
   the direction where it is sensitive, which is a weaker and legitimate use.
5. **The debiasing of fact 14 is not clean.** `nu_hat^2 = |grad L|^2 − 2 s^2`
   takes `s` from the same sensor model whose read noise fact 24 finds 8–27%
   over-predicted. If `s` is over-stated, the debias over-corrects and the
   `rho_true` column of fact 13 is biased *high*. The direction is known; the
   magnitude is not, and correcting it is a sensor-profile job.
6. **The seam cannot express the plant.** M43's calibration seam offers only
   zero-signal noise sources (fact 9), so the project's own designated mechanism
   for recalibrating this constant cannot be pointed at the thing that moves it.
   That is not a circularity in my measurement; it is a circularity in the
   project's ability to act on it.
7. **One place it stopped biting, after the amendment.** M65's specific
   circularity — that an arm which turns the regulariser off is still scored in
   units defined *on* the regularised field — **is now removed, for that arm.**
   Fact 44 measures the raw field's own constant directly on the crate's plant:
   `FOCUS_NOISE_SD_raw = 0.019044`. A raw-election merge no longer has to borrow
   the regularised unit or convert through a scalar. That does not rescue the
   general case — fact 46 shows the conversion factor is itself texture-dependent
   across a 1.488× range — but the specific hole M65 named is filled.
8. **Where the amendment made the circularity worse, not better.** Fact 39's
   control validates P2's *slope* against a defect measured in units of `2 s^2`,
   and `s` comes from the same sensor model item 5 flags as 8–27% over-predicted.
   The slope agreement (0.7% of the step) is therefore a strong test of the
   *mechanism* and a weak test of the *units*. I did not find a way to separate
   them without the burst.

---

## 11. Captures owed

Appended to `docs/captures-needed.md`. In priority order:

1. **A real 30-frame static burst** — already §12 of that file, **REQUESTED and
   still undelivered**. M69 corroborates the request and raises its urgency: it
   is the *only* way to measure `sigma_F` on real texture with real noise, and
   fact 27 shows the quantity is **not measurable** without it, not merely not
   measured.
2. **A textured static burst at ≥2 contrast levels** — the new ask. A burst on a
   flat card certifies only `z = 0`, which is what the crate already has
   synthetically. Two contrast levels on the same subject, focus untouched, is
   what separates fact 19's direction-coherence mechanism from fact 25's
   row-noise mechanism, and is what would let P2 be tested rather than merely
   proposed.
3. **An ISO-160 dark group at working exposure** — already §11. Fact 24 has 11
   ISO groups and none at 160, which is the ISO of M62's own certified plant.

---

## 12. Pre-registered decisions, in their own words

| decision | pre-registered bar | result |
|---|---|---|
| **D1** — is M66's 19–21% reproducible? | within ±0.02 of `rho_REAL = 1.1921` | **REPRODUCED** (Δ = 0.0000). Amended: M66's *other* estimator, fact 9's temporal `rho = 1.2124`, also reproduces at Δ = −0.0153, inside the same ±0.02 band (fact 38) |
| **D1b** — is it right *as a claim about real texture*? | real estimate in `[1.15, 1.25]` on a majority of stacks **and** A3 moving `rho` on M62's latent by ≤0.05 | **NOT MET** — 1 of 4 latents, 0 of 12 stacks by `rho_true`; reported as **not supported as a general statement**, corrected number 1.0147 median (fact 13), arm A2 + §6 |
| **D2** — should it be a constant at all? | refuted if (a) IQR > ±10% of median on a majority, **or** (b) per-stack `rho` spans > 1.10× | **REFUTED via (b)**: 1.186× on the corpus, 4.06× across arms. (a) not satisfied (4 of 12) |
| **D3** — is the per-pixel form derivable? | parameter-free predictor within median 10% on the known-truth arm | **NOT MET for P1** (errors to −78%, wrong sign); missing term named (fact 19) rather than fitted. P2 (fact 21) achieves 2.01% but is **post hoc** and does not satisfy D3 |

---

## 13. What M69 asserts, and what it does not

**Asserts.** The provenance of facts 1–9. The reproduction of facts 10 and 38.
The non-generalisation of facts 12–14. The mechanism of facts 18–20, now with a
control that could have failed (facts 39–40). The corpus distribution of fact 13.
The pricing of facts 29–32 and 44–46. The read-noise over-prediction of fact 24.
That the "second independent observation" of fact 36 is a mis-attribution.

**Does not assert.** That `FOCUS_NOISE_SD` should change value — §9 recommends it
should not. That P2 is correct — it is post hoc, untested against a
pre-registration, and §9.1 lists five domains it does not declare, the first of
which is the same `N`-blindness M66 proved and M62 confessed. That M62's
certification is in question — fact 30 says it is not, on this evidence, and fact
31 states the conditional under which it would be, for M62 and not M69 to rule.
That M65's D1 is in question — fact 45 says it clears by 1.45×. That fact 24's
`rho_dark > 1` is real rather than a clipping artefact — fact 25 names the test I
did not run. That M66 erred: fact 36's error is downstream of M66 entirely, and
M66 flagged its own K7 as post hoc and declined to rule on it.

**One thing the orchestrator must route, which M69 may not.** SYNTHESIS fact 986
records that M62 *"independently reproduced M66's post-hoc 19-21% FOCUS_NOISE_SD
effect on its own plant (rho = 1.2124 at seeds 0 and 1)"*. Fact 36 shows that
number is M66's own fact 9 and that M62 states it re-ran nothing. **M69 does not
edit SYNTHESIS.** The correction is the orchestrator's to make, and the reason it
matters is not bookkeeping: the corpus currently believes a post-hoc result has
been independently confirmed when it has not been, and that belief is what
promoted it from flagged anomaly to settled fact before M69 reported.

**Reproduction.** `experiments/M69-focus-noise-sd/` — `PREREGISTRATION.md`
(committed at `33f3565` before any result existed), `src/*.py`, `out/*.log`,
`out/*.json`. `src/m69.py` parses every constant out of `crates/` at run time and
never retypes one. The amendment's arms are `src/95-a7-second-observation.py`
(facts 38–40) and `src/96-a8-m65-election.py` (facts 41, 44–46); both carry their
bars in their docstrings, fixed before they ran.

