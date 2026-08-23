# M52 — Independent verification of the merge-gate calibration cluster (facts 500, 324, 436, 438, 439, 501, 509, 510)

**Status: MEASURED.** Source: `experiments/m52-gate-cluster/`. Runs against
`D:\personal\macro` (all seven stacks) and `D:\macro-dark-frames` (loader proof).
Shipped-binary numbers were re-taken at HEAD `4fb845c` after a rebuild, because
the binary I started with predated two noise-model corrections landed today.

Every fact below carried **NOT INDEPENDENTLY VERIFIED**. Rule 12 makes that a
standing request. Nothing here re-runs an M43 or M38 script: every number is from
an instrument written fresh against `merge.rs`, `focus.rs`, `boxfilter.rs`,
`noise.rs` and `profile.rs`, with a different decomposition at every stage
(Philox rather than PCG64, shift-sum and `uniform_filter` box rather than cumsum,
padded-slice Sobel rather than `np.roll`, and for one arm an autocovariance
contraction that never applies a box filter at all).

**Six of the eight stand. One is understated by 3.7x and has two wrong numbers.
One is right only under a condition nobody has written down.**

---

## 1. Verdicts

| Fact | Claim, in short | Verdict | The number that decides it |
|---|---|---|---|
| **500** | Fact 437's `k` = 5.94 was a units conflation; the honest value is 1.815 | **VERIFIED** | `SD(reg8(box2(\|grad\|)))` = **0.027605** vs published 0.027613 (**+0.03%**); `k` = **1.8145** vs 1.815; overstatement **3.275x** vs 3.27x |
| **501** | A two-target calibration caught it; one target would have shipped it | **VERIFIED** | Unregularised coarse model reads **+24.45%** against `FOCUS_NOISE_SD` (published +24.26%) while reading **+0.21%** against `FINE_FOCUS_NOISE_SD` (published +0.20%). One target passes, one misses by 24% |
| **439** | Seven operators, noise constant spans 10.4x | **VERIFIED WITH QUALIFICATION** | Span **10.32x**; all seven rows within **0.5%**. But 5 of 7 carry an arbitrary scale factor: under an equally defensible normalisation the span is **2.12x**. And the provenance line says 8 seeds; the survey ran at **4** |
| **510** | Radius alone gives `k` = 1.125; separability NOT DECIDED | **VERIFIED**, and the "not decided" is **decidable** | Arms reproduce: **1.1270 / 1.3674 / 1.5306** vs 1.125 / 1.364 / 1.528. Under paired per-seed ratios the residual is **−0.00133% ± 0.01779%** — separable to 0.02% |
| **509** | The pending M17+M42 edit re-scales the gate by 1.53x | **VERIFIED WITH QUALIFICATION** | Joint arm SD **0.023286** vs 0.023249, `k` = **1.5306** vs 1.528. **But 1.53x is right only if the edit also divides by `sigma^2`.** `tenengrad-sq` is degree 2; `focus.rs` divides by sigma once. Under the shipped divide the shift is `1.53 * sigma` ~ **13x–38x** and is not a constant |
| **436** | Tolerance is exactly linear in a constant that belongs to the operator | **VERIFIED WITH QUALIFICATION** | Linearity holds over **10 decades**, not the published 35x: `tol/t` = **0.021515844** at every rung = `sqrt(2) * 0.015214` exactly. But it is **one multiplication** — arithmetic, not evidence. And a per-operator constant is **necessary and not sufficient**: five operators each with its own correct constant still spread **4.54x** in `n_eff` at gate 2.0 |
| **438** | Neither capability negotiation nor confluence can catch a wrong constant | **VERIFIED** (DERIVED), and **extended** | `Caps` has six fields, none of them a noise constant. Pass one never reads the constant — the binary's `boundary %` is identical at every gate from **1e-6 to 1e6**. **New:** one declaration survives, `Normalisation::LumaSigma { degree }`, and the sigma = 1 calibration plane cannot check it (**ratio 1.00000000** whichever degree is declared) |
| **324** | The gate does not transfer; a fixed threshold is not a calibration | **Conclusion VERIFIED and understated 3.7x. Two of five published numbers REFUTED. The stated mechanism REFUTED** | Seven-stack spread at gate 2.0 is **12.22x**, not 3.3x. Gates for `n_eff` = 3 span **0.7618 to 21.9934 = 28.9x**, not "1.1 to 2.9". `119MSDCF` is **2.847, not 2.258**; `coffee-bean` is **14.386, not 7.422**. `n_eff/N` ranges **11.6x** and does not cluster |

---

## 2. Nothing below is believable without these three things first

### 2.1 The loader is proven

Rule 32's cross-check, re-run at the top of every RAW script. Twenty usable darks
per folder (first two dropped), per-pixel temporal variance, pooled RMS, against
M4 §8.1:

| folder | ISO | R | G1 | G2 | B | worst dev |
|---|---|---|---|---|---|---|
| `118MSDCF` | 100 | 1.0048 | 1.0042 | 1.0104 | 0.9184 | **0.01%** |
| `119MSDCF` | 400 | 1.2130 | 1.2266 | 1.2402 | 1.1145 | **0.01%** |

Worst deviation across all eight numbers: **0.013%**. The scripts `sys.exit` if it
exceeds 1%.

### 2.2 The instrument is calibrated against both in-crate constants

On unit-sigma Gaussian planes, 8 seeds x 2048^2, in the shipped configuration:

| target | crate | mine | deviation |
|---|---|---|---|
| `FOCUS_NOISE_SD` (w13 + r8) | 0.015214 | 0.015318 ± 0.000041 | **+0.68%** |
| `FINE_FOCUS_NOISE_SD` (w2, no regulariser) | 0.090400 | 0.090588 ± 0.000046 | **+0.21%** |

A structural check that is independent of both: the mean of `|grad|` on unit
noise must equal the closed-form Rayleigh value. Measured 0.54271 against
0.54270 analytic — **1.0000x**.

### 2.3 Placebos, so the instrument can say "no effect"

Rule 11. Three negative controls, run before any positive claim:

- **Placebo A — five mathematically identical tenengrad implementations**
  (hypot; sqrt of sum of squares; on the transpose; explicit 3x3 correlation;
  input scaled by 7 and divided back). All five read **0.015318**. Span
  **1.0000x**.
- **Placebo B — seed-to-seed on the shipped arm.** Span **1.0246x**. This is the
  noise floor: any claimed effect below ~2.5% on a single seed is nothing.
- **Placebo C — the same operator by two code paths, all the way through a real
  22-frame merge.** `n_eff` at gate 2.0 = 2.9051 vs 2.9051 on `109MSDCF` and
  4.8082 vs 4.8082 on `113MSDCF`. Span **1.00000x**.

Placebo C matters most: it is the control for §5.3's cross-operator result, and
it is run through the identical pipeline on identical data.

---
## 3. The synthetic cluster: 500, 501, 509, 510, 439

### 3.1 Fact 500 — VERIFIED, and the correction is not itself a conflation

The units question had to be settled from source, not from the report. It is:

- `merge.rs:146`/`:173` — `FOCUS_NOISE_SD` is the SD of the **regularised**
  response.
- `through_focus.rs:130` — `FINE_FOCUS_NOISE_SD` is documented in the crate as
  measured with **no** regulariser.

So `0.090400 / 0.015214 = 5.942` divides an unregularised SD by a regularised
one. The conflation is real and it is visible in the crate's own doc comments.

The correction puts both sides at r8 and lets only the operator window differ
(w2 against w13), which is the comparison fact 437 meant to make. My independent
measurement: **0.027605** against the published 0.027613 (+0.03%), `k` =
**1.8145** against 1.815, overstatement **3.275x** against 3.27x.

I checked the correction for the same fault it corrects, since a units error made
once can be made again. It is clean: both arms share the r8 regulariser, the same
seeds, the same plane size and the same normalisation. **MEASURED.**

One thing the fold should carry: the crate still encodes the superseded framing.
`through_focus.rs`'s `the_fine_scale_is_much_noisier_than_the_selection_scale`
asserts the ratio lies in `5.0..7.0` — i.e. it asserts the 5.94 that fact 500
retired. It passes, because the ratio of the two published constants really is
5.94; what fact 500 says is that this ratio is not a `k`.

### 3.2 Fact 501 — VERIFIED

Reproducing the *failing* instrument is the point of this fact. Modelling the
coarse field without the regulariser, my run reads **+24.45%** against
`FOCUS_NOISE_SD` (published +24.26%) and **+0.21%** against
`FINE_FOCUS_NOISE_SD` (published +0.20%). The diagnostic pattern — one target
passing, one missing by 24% — reproduces exactly, and it does localise the fault
to the one thing the two configurations differ in. **MEASURED.**

### 3.3 Facts 509 and 510 — arms VERIFIED; 510's "not decided" is decidable

| arm | published `k` | mine | dev |
|---|---|---|---|
| radius alone, w13 -> w11 | 1.125 | **1.1270** | +0.18% |
| operator alone, `\|grad\|` -> `\|grad\|^2` at w13 | 1.364 | **1.3674** | +0.25% |
| joint (the pending edit) | 1.528 | **1.5306** | +0.17% |

Fact 510 records the separability question as **NOT DECIDED** because the product
of the single arms overstates the joint by +0.47%, which is exactly the
instrument's own calibration offset. That reasoning is right about the cause and
wrong about the conclusion: the offset is removable. Dividing by the crate
constant injects one factor of the +0.47%; dividing by the **measured** shipped
arm, per seed, cancels it. Paired over 8 seeds:

- radius alone **1.11935 ± 0.00050**
- operator alone **1.35806 ± 0.00130**
- joint **1.52016 ± 0.00152**
- `(radius x operator) / joint − 1` = **−0.00133% ± 0.01779%**

**The two halves of the edit are separable to within 0.02%.** Fact 510's numbers
stand; its verdict can be upgraded from "not decided" to "separable", and its
consequence column ("the near-separability is a convenience, not a finding") is
now a measurement rather than a caution.

### 3.4 Fact 509's qualification — the pending edit may not be a scalar at all

`tenengrad-sq` is `Gx^2 + Gy^2`: **homogeneous of degree 2** in the luma. The
shipped focus field divides by `green_luma_sigma` exactly **once**
(`focus.rs`, `box_mean(grad, 13) / sigma`). A degree-2 response divided by sigma
once is degree-1 in sigma, so its noise SD is *proportional to the local signal
level* and is not a constant.

Measured, with the same noise realisation scaled so there is no sampling error at
all (`07-homogeneity-exact.py`, sigma swept 64x):

| operator | true degree | ratio over a 64x sigma sweep |
|---|---|---|
| ring(1,3) | 1 | **1.0000x** |
| tenengrad `\|grad\|` (shipped) | 1 | **1.0000x** |
| Brenner | 1 | **1.0000x** |
| Laplacian | 1 | **1.0000x** |
| sum-modified-Laplacian | 1 | **1.0000x** |
| **tenengrad-squared** | 2 | **64.0000x** |
| **local variance (3x3)** | 2 | **64.0000x** |

The five degree-1 rows are the negative control and read exactly 1.000000, max
deviation **0.00e+00**. The two degree-2 rows read exactly the sweep factor.

`strehl-plugin` already knows this: `reference.rs:157` declares
`Normalisation::LumaSigma { degree: 2 }` for `TenengradSquared`, and
`measure.rs:201` divides by `sigma^degree`. `strehl-core/src/focus.rs` does not
have a degree — it has one divide.

**So fact 509's 1.53x is correct for the plugin path and wrong for the core path,
and fact 509 does not say which path the edit lands in.** Median
`green_luma_sigma` on this corpus is 8.64–24.61 DN (§4.4), so under the core
path the real shift would be roughly 13x–38x, varying pixel to pixel. That is the
difference between `--gate 1.0` meaning 0.654 and it meaning about 0.03.

I am **not** claiming the edit is broken. I am claiming the fact prices it at
1.53x without recording the condition under which 1.53x is the right answer.

### 3.5 Fact 439 — VERIFIED WITH QUALIFICATION

| operator | published `k` | mine | dev |
|---|---|---|---|
| ring(1,3) | 0.644 | 0.646 | +0.3% |
| tenengrad `\|grad\|` | 1.008 | 1.007 | −0.1% |
| tenengrad-squared | 1.367 | 1.367 | 0.0% |
| Brenner | 1.962 | 1.971 | +0.5% |
| local variance | 2.475 | 2.479 | +0.2% |
| Laplacian | 6.590 | 6.589 | 0.0% |
| sum-modified-Laplacian | 6.680 | 6.671 | −0.1% |
| **span** | **10.4x** | **10.32x** | |

A **third route** confirms the ratio without any box filter: contracting the
analytic autocovariance of each stencil against the box kernels gives tenengrad
0.015485, SML 0.102520, ring 0.009827, and an SML/tenengrad ratio of **6.621**
against the filtering route's 6.626 — **0.08% agreement in the ratio**, which is
the quantity `k` actually is.

Three qualifications, none of which move the numbers:

1. **Provenance.** SYNTHESIS's source column says "8 seeds x 2048^2". The survey
   rows in `02b-operator-noise-spread.py` are called with `seeds=4`; only the
   calibration used 8. M43 §8.2's prose ("noise floor at 4 seeds") is right; the
   SYNTHESIS line is not.
2. **The span is partly a convention.** Five of the seven operators carry a scale
   factor that nothing pins down — `focus.rs` itself multiplies its Sobel by
   0.125 and calls the factor "cosmetic". Applying the same 1/8 to the Laplacian
   family, 1/2 to Brenner, and taking the SD rather than the variance for local
   variance gives 0.646 / 1.007 / 1.367 / 0.985 / 1.284 / 0.824 / 0.834 — a span
   of **2.12x**. Both spans are true; they are answers to different questions.
   The 10.4x is the right number for *this repository's* stencil conventions, and
   the fact should say so, because a contributor writing `Gx^2+Gy^2` with a 1/8
   folded in gets a different `k` for the same operator.
3. **Two of the seven are not constants.** §3.4.

---
## 4. Fact 324 — the load-bearing claim. Right, and understated by 3.7x

This is the claim the plugin calibration seam and `--target-n-eff` both rest on,
so it got the most work: a second full implementation of pass one and pass two in
Python, run on **all seven** stacks, cross-checked against the shipped binary.

### 4.1 The independent merge agrees with the shipped binary on all seven stacks

`10-fact324-current-model.py` reimplements the admission rule from source —
clamped-window box borders (`nx[x] * ny[y]`, not replicate), the 0.125 Sobel,
`0.5*(max(G1-b,0)+max(G2-b,0))` luma, `max(iso,100)/436.8` gain — and never calls
`strehl`:

| stack | N | ISO | mine, gate 2.0 | binary, gate 2.0 | dev |
|---|---|---|---|---|---|
| `119MSDCF` | 33 | 50 | 2.847 | 2.847 | +0.02% |
| `109MSDCF` | 22 | 160 | 2.891 | 2.891 | +0.00% |
| `113MSDCF` | 63 | 500 | 4.757 | 4.761 | −0.09% |
| `112MSDCF` | 79 | 500 | 6.187 | 6.190 | −0.04% |
| `coffee-bean` | 105 | 50 | 14.374 | 14.386 | −0.08% |
| `coffee-bubbles` | 19 | 1000 | 2.109 | 2.109 | +0.01% |
| `foam` | 100 | 1000 | 1.177 | 1.177 | −0.04% |

Worst deviation **0.09%**. Two independent implementations agreeing to 0.09% on
seven stacks is what licenses everything below.

### 4.2 Two of fact 324's five numbers are wrong, and the cause is datable

| stack | ISO | fact 324 | measured today | error |
|---|---|---|---|---|
| `119MSDCF` | **50** | 2.258 | **2.847** | **+26.1%** |
| `109MSDCF` | 160 | 2.891 | 2.891 | 0.0% |
| `113MSDCF` | 500 | 4.774 | 4.761 | −0.3% |
| `112MSDCF` | 500 | 6.226 | 6.190 | −0.6% |
| `coffee-bean` | **50** | 7.422 | **14.386** | **+93.8%** |

Both wrong stacks are ISO 50; all three that reproduce are ISO 160 or 500. EXIF
confirms the ISOs are uniform within every stack (`119MSDCF` 33/33 at ISO 50,
`coffee-bean` 105/105 at ISO 50).

The cause is in the log. M38 was folded at **06:20 and 06:29** today. Commit
`2a4f5c5`, *"ISO 50 is not a gain step, and the shipped model believed it was"*,
landed at **09:41** and introduced the `max(iso, 100)` floor in
`gain_dn_per_e`. At ISO 50 that raises sigma by about `sqrt(2)`, which lowers the
normalised focus field, which admits more frames at a fixed tolerance —
**exactly the direction and roughly the size of both errors**. Interpolating
M38's own coffee-bean ladder to an effective gate of `2 * sqrt(2)` predicts 13.5
against my measured 14.4.

This happened **twice in one day**. Commit `f95f6f4` at **11:17**,
*"read_noise_e_high was +18% on its own basis"*, changed `1.47 -> 1.2392` and
moved every ISO >= 400 stack again — which is why the `113`/`112` rows above are
0.3–0.6% off rather than exact, and why I rebuilt and re-ran everything. My first
pass used the 10:09 binary and was already stale when I took it.

### 4.3 The stated mechanism does not survive, and the conclusion gets stronger

Fact 324's middle sentence — *"`n_eff/N` clusters at 0.068–0.079 for four of
five, so the acceptance set is roughly a fixed fraction of the bracket"* — was
the interesting part, because it proposed a mechanism. Corrected:

| stack | `n_eff/N` at gate 2.0 |
|---|---|
| `foam` | **0.0118** |
| `113MSDCF` | 0.0755 |
| `112MSDCF` | 0.0783 |
| `119MSDCF` | 0.0863 |
| `coffee-bubbles` | 0.1110 |
| `109MSDCF` | 0.1314 |
| `coffee-bean` | **0.1369** |

Range **11.6x**. Only two of M38's own five fall inside 0.068–0.079. The
acceptance set is **not** a fixed fraction of the bracket, and `109MSDCF at 0.131
is unexplained` is no longer an isolated exception — it is one of three stacks
above 0.11. **REFUTED.**

The headline conclusion, meanwhile, is stronger than claimed:

- spread at gate 2.0 over M38's five stacks: **5.05x**, not 3.3x;
- over all seven: **12.22x**;
- gate needed for `n_eff` = 3, by the crate's own solver: `coffee-bean` **0.7618**,
  `112MSDCF` 1.1323, `113MSDCF` 1.3231, `109MSDCF` 2.0964, `119MSDCF` 2.1485,
  `coffee-bubbles` 3.2144, `foam` **21.9934** — a **28.9x** range, not 2.6x.

`foam` is the finding that was sitting there for free: at gate 2.0 it averages
**1.177** frames with **84.20%** of pixels on pure selection, and the crate's own
solver refuses it — *"target n_eff 3.000 is above the ladder: gate 4.0000 reaches
only 1.361."* **A stack in this corpus cannot reach the calibration target
anywhere on the shipped gate ladder.** Any default gate is wrong for `foam` by an
order of magnitude.

### 4.4 Per-stack sigma, for §3.4

Median `green_luma_sigma` on a mid-stack frame: `112MSDCF` 8.64, `113MSDCF`
12.24, `coffee-bubbles` 14.96, `109MSDCF` 17.48, `119MSDCF` 19.68, `coffee-bean`
24.33, `foam` 24.61 DN. Range across the corpus 8.6–24.6 DN.

---

## 5. Facts 436 and 438 — separating what is exact from what is argued

### 5.1 The linearity has no power to fail, and I extended it anyway

`Gate::tolerance()` is `self.threshold * SQRT_2 * FOCUS_NOISE_SD` — one
multiplication. Checking that one multiplication is linear cannot fail; this is
rule 20's situation, and the published "verified against the shipped binary at
five gates spanning 35x" is arithmetic re-printed as a measurement.

I ran it over **10 decades** rather than 35x, on `coffee-bubbles`:

| gate | printed `tol` | `tol/gate` |
|---|---|---|
| 0.0001 | 0.000002 | — |
| 0.168 | 0.003615 | 0.0215179 |
| 5.94 | 0.127804 | 0.0215158 |
| 1000 | 21.515844 | 0.021515844 |
| 1000000 | 21515.843750 | 0.021515844 |

`sqrt(2) * 0.015214 = 0.021515844`. Identical to **8 significant figures**. The
published "constant to 2.0e-6" is an artefact of dividing a 6-decimal *printed*
tolerance; the real constancy is f32 epsilon. **DERIVED, not MEASURED.**

The endpoints are the useful part: gate 1e-6 gives `n_eff` exactly 1.000 with
100.00% of pixels at `n_eff` = 1 (pure selection), and gate 1e6 gives exactly
19.000 = N (pure mean). The gate degenerates correctly at both limits.

### 5.2 "Operator k times noisier == gate divided by k" is exact — for a rescaling

Measured on `109MSDCF`, scaling the operator by 7 and its constant by 7:

| gate | `n_eff`, unscaled | `n_eff`, x7 | pixels differing |
|---|---|---|---|
| 0.5 | 1.416599 | 1.416599 | **12** of 8,236,816 |
| 2.0 | 2.905129 | 2.905130 | **18** of 8,236,816 |

Winner maps agree on **99.999927%**. That is f32 rounding, nothing else. Fact
436's substitution is exact in this sense. **MEASURED.**

### 5.3 It is *not* exact for a different operator

Fact 436's consequence — that the gate has no units of its own and means
something else for another operator — is why the seam measures a constant per
operator. The unstated next step is that a per-operator constant **restores**
portability. It does not.

Five operators, each carrying **its own correctly measured constant**, run through
the full shipped pipeline on real frames:

**`109MSDCF`, mean `n_eff`:**

| operator | own `C` | gate 0.5 | gate 1.0 | gate 2.0 | gate 4.0 | gate for `n_eff`=3 |
|---|---|---|---|---|---|---|
| ring(1,3) | 0.009835 | 1.397 | 1.847 | **2.806** | 4.670 | 2.1901 |
| tenengrad (shipped) | 0.015318 | 1.417 | 1.891 | **2.905** | 5.017 | 2.0832 |
| Brenner | 0.029983 | 1.563 | 2.230 | **3.711** | 7.286 | 1.4975 |
| SML | 0.101496 | 2.267 | 4.488 | **11.406** | 19.126 | 0.6645 |
| Laplacian | 0.100246 | 2.444 | 5.059 | **12.727** | 19.486 | 0.6079 |
| **spread** | | 1.75x | 2.74x | **4.54x** | 4.17x | **3.60x** |
| *placebo: tenengrad, 2nd code path* | *0.015318* | *1.417* | *1.891* | *2.905* | *5.017* | *2.0832* |

Placebo span **1.00000x**. On `113MSDCF` the same measurement gives a 1.98x
spread at gate 2.0 and a 1.55x spread in the solved gate.

Winner-map agreement with tenengrad on `109MSDCF`: ring 68.3%, Brenner 67.2%,
SML 33.9%, Laplacian 28.5%. Different operators do not merely scale — they elect
different winners on two-thirds of the frame.

**Conclusion: the per-operator noise constant is necessary and not sufficient.**
It makes `--gate t` mean "t sigmas of this operator's noise", which is what it is
for and it works. It does not make `--gate t` produce a comparable amount of
averaging. An operator swap needs the gate re-solved against a target `n_eff`,
exactly as fact 324 says a stack swap does. **MEASURED.**

A related number worth having: on `109MSDCF` at gate 2.0, SML with its own
constant gives 11.406 and SML inheriting the host's 0.015214 gives **1.660**,
against the host operator's 2.905. The *uncorrected* constant lands closer to the
host's behaviour than the corrected one. That is not an argument against the
seam — it is an argument that `n_eff` is not what the seam controls.

### 5.4 Fact 438 — VERIFIED, and there is one more hole

**Capability negotiation.** `Caps` (E-plugin-architecture.md §F3.3, lines
963–971) has exactly six fields: `domains_in`, `domains_out`, `devices`,
`precisions`, `access`, `fence`. There is no noise, response or calibration
field, so negotiation structurally cannot carry the constant, let alone check it.
**DERIVED from source** — `Caps` is a design, not shipped code, so this is a
reading and not a measurement.

**Confluence.** P1 asserts that the result is a function of the config alone.
Changing a constant is perfectly deterministic, so confluence passes. Corroborated
by measurement rather than assertion: pass one never reads `FOCUS_NOISE_SD`
(every occurrence in `merge.rs` is the definition, `tolerance()`, or a test), and
the binary's `boundary %` — a pure pass-one statistic — is **0.75% at all six
gates from 1e-6 to 1e6** on `coffee-bubbles`. The winner field is provably
gate-independent, so a wrong constant moves `n_eff` and leaves selection
untouched. §5.3's SML pair is the size of that: **6.9x** swing in `n_eff` with a
bit-identical winner map.

**The extension.** `measure.rs`'s header says the design removed every declared
number — *"a declaration can be wrong; a measurement cannot be wrong in the same
way. Fault 5 of §F4.6 becomes unrepresentable ... there is no place in this file
to put a wrong number."*

There is one place: `Normalisation::LumaSigma { degree }` (`measure.rs:123`).
And `calibrate.rs:309` measures every constant on `unit_sigma_model()` — a plane
whose `green_luma_sigma` is 1 DN, where `sigma^1 == sigma^2 == 1`:

| operator | true degree | calibrated as degree 1 | as degree 2 | ratio |
|---|---|---|---|---|
| tenengrad | 1 | 0.015453 | 0.015453 | **1.00000000** |
| SML | 1 | 0.100530 | 0.100530 | **1.00000000** |
| tenengrad-squared | 2 | 0.020901 | 0.020901 | **1.00000000** |
| local variance | 2 | 0.037581 | 0.037581 | **1.00000000** |

**The host measures the same constant whichever degree is declared.** On a
realistic plane (sigma = 17.48 DN, `109MSDCF`'s median) a mis-declared degree
costs exactly `sigma^±1` — **17.480x** or **0.057x**. Negative control:
correctly-declared operators read 1.000000 with max deviation **6.66e-16**.

All seven operators in `reference.rs` declare the correct degree today, so this
is a latent hole rather than a live wrong number. But it is the same shape as
fault 5, in the file that says fault 5 is unrepresentable, and the calibration
plane is the specific choice that hides it.

---
## 6. Defects found in shipped code and documentation

1. **Three shipped locations quote fact 324's stale numbers.**
   `crates/strehl-cli/src/main.rs:138–141` is **user-visible CLI help** for
   `--target-n-eff`: *"2.26-7.42 across five stacks, and reaching n_eff = 3 needs
   gates from 1.1 to 2.9."* Measured today: 2.847–14.386, and 0.7618 to 2.1485
   over the same five stacks. `merge_cmd.rs:78–80` repeats it.
2. **A regression test is pinned to stale data and cannot go red.**
   `merge_cmd.rs:1828` hard-codes `LADDERS` — including `(2.0, 2.258)` for
   `119MSDCF` and `(2.0, 7.422)`, `(4.0, 24.700)` for `coffee-bean` — and
   `the_solved_gate_spans_the_range_fact_324_claims` asserts
   `(1.0..1.2).contains(&lo)` and `(2.7..3.1).contains(&hi)`. Against today's
   pipeline `lo` = 0.7618 and `hi` = 2.1485, so **two of its three assertions
   would fail**. It passes because it tests the interpolator against frozen
   numbers rather than the claim against the pipeline. Full workspace suite:
   **187 tests, 0 failed** — this test is green and wrong.
3. **Fact 439's provenance line says 8 seeds; the survey ran at 4**
   (`02b-operator-noise-spread.py` passes `seeds=4` for the survey rows).
4. **`E-plugin-architecture.md` §F4.6 fault 5 mis-cites its own numbers**: it
   attributes "87.76% of pixels revert to selection" to a `k` = 6.68 operator,
   but 87.76% was measured at effective gate 0.168, i.e. `k` = 5.94.
5. **`through_focus.rs`'s `the_fine_scale_is_much_noisier_than_the_selection_scale`
   asserts the ratio is in `5.0..7.0`** — the framing fact 500 retired.
6. **Neither fact 439 nor fact 509 records the normalisation degree**, and
   `focus.rs` (one divide) and `reference.rs` (`degree: 2`) disagree about what
   `tenengrad-sq` means. §3.4.

---

## 7. My own errors and false starts

**1. I nearly shipped a wrong headline, and the source caught it.** On measuring
that `tenengrad-sq` is degree-2 homogeneous, I wrote up a finding that the
pending M17+M42 edit would break the gate by a factor of sigma and that
`calibrate.rs`'s sigma = 1 plane made it invisible. I had already drafted the
sentence when I checked what `TenengradSquared` actually declares — and it
declares `Normalisation::LumaSigma { degree: 2 }`, and `measure.rs:201` honours
it. **The plugin crate had already solved the problem I was about to report.**
What survives is narrower and conditional (§3.4: the *core* path has one divide
and no degree, and fact 509 does not say which path it prices) and one genuinely
new claim (§5.4: the calibration plane cannot check the declaration). This is the
exact failure mode I was sent to find in someone else's work, arrived at by the
same route — measure a real effect, then assert a consequence for code I had not
read.

**2. I reported a percentage with the wrong sign convention.** Step 01 printed
the separability residual as `radius * operator / joint` formatted as a
percentage, giving `+99.9987%` where the intended quantity was
`(product/joint − 1) = −0.0013%`. Caught in step 02 when the paired arm produced
a number three orders of magnitude different. Nothing downstream used the wrong
value, because the wrong value was obviously wrong; a subtler offset would not
have been.

**3. I ran the whole real-data campaign against a stale binary and did not
notice for two hours.** `target/release/strehl.exe` was built at 10:09. Commits
at 11:10, 11:13, 11:17 and 11:27 touched `noise.rs`/`profile.rs`, one of them
changing `read_noise_e_high` from 1.47 to 1.2392. I caught it only because I
checked `git status` before running `cargo test` and noticed HEAD had moved from
the commit I recorded at the start. Everything in §4 was re-taken after a
rebuild. **The lesson generalises past me:** in a repository with six agents
committing, a measurement is stamped by a commit or it is not a measurement.
Fact 324 is the same failure with a six-hour lag and no stamp at all.

**4. My step 06 sigma sweep drew a fresh noise realisation per sigma**, so
sampling noise contaminated a homogeneity test whose true answer is exactly
1.000. SML read 1.068x and I briefly believed SML was not degree-1. Rewritten in
step 07 to scale a *shared* realisation, which makes the test exact — the
degree-1 rows then read 1.000000 with deviation 0.00e+00 on the same operator. A
test whose null answer is exactly 1 should never be run with sampling noise in
it.

**5. I initially treated the 4688 x 7028 / 7032 x 4688 geometry difference
between `rawpy` and `rawler` as a candidate explanation** for the `coffee-bean`
discrepancy. It is a 2-column difference, 0.057% of columns, and cannot produce
94%. I should have bounded it before investigating it; instead I bounded it
after.

**6. I suspected `coffee-bean`'s known mid-capture exposure change** (M24: 4/5 s
-> 5/8 s, confirmed in EXIF as 40 frames then 65) as the cause of its 94% miss,
and spent time on it before checking commit timestamps. The exposure change is
real and irrelevant here: `119MSDCF` also missed, and its exposure change is a
different one (1/8 -> 1/6), while three stacks with perfectly constant exposure
reproduced exactly. ISO was the variable that separated the two groups, and one
`git log` would have found it faster than any measurement.

---

## 8. Reproducing this without my code

1. **Prove the loader.** Decode 20 darks per ISO folder (drop the first two),
   compute per-pixel temporal variance across frames, take the square root of the
   mean variance per CFA plane, compare to M4 §8.1. Must agree to 1%.
2. **Build the instrument.** Unit-variance Gaussian plane, >= 2048^2, >= 4 seeds.
   Apply the operator stencil with replicate borders, then a box mean of radius
   13, then divide by sigma, then a box mean of radius 8. Discard a margin of at
   least 13+8+2 and take the interior SD. Calibrate against **both**
   `FOCUS_NOISE_SD` (w13, with r8) and `FINE_FOCUS_NOISE_SD` (w2, **without**
   r8); if either misses by more than a few percent, stop.
3. **Placebos.** Implement one operator two or more mathematically identical ways
   and confirm the span is 1.000. Report seed-to-seed span as the noise floor.
4. **Facts 500/501/509/510.** Vary one thing at a time from the shipped arm
   (window radius; operator; both) and form ratios **per seed against the
   measured shipped arm**, not against the published constant.
5. **Fact 324.** Reimplement pass one and pass two: luma
   `0.5*(max(G1-b,0)+max(G2-b,0))`, gradient `0.125*hypot(Sobel)` with replicate
   borders, box radius 13, divide by `sqrt(0.5*(g*L + (RN*g)^2))` with
   `g = max(ISO,100)/436.8`, box radius 8, take the per-pixel max over frames,
   count frames within `t*sqrt(2)*0.015214`. **Box borders are clamped-window
   divided by the surviving count, not replicate.** Run all seven stacks. Then
   run `strehl merge --gate 0.5 1 2 4 --target-n-eff 3` and require agreement.
6. **Homogeneity.** Scale one realisation, do not draw new ones.
7. **Cross-operator transfer.** Same pipeline, swap the stencil, use each
   operator's own measured constant, and include a placebo operator.

Record the commit the binary was built from. See §7.3.

---

## 9. Proposed facts, disciplines, questions

Numbered locally from **P1**; the orchestrator renumbers on fold.

### Facts

**P1. MEASURED.** Fact 324's published `n_eff` for the two ISO 50 stacks was
measured before commit `2a4f5c5` corrected the ISO 50 gain, and is stale:
`119MSDCF` at gate 2.0 is **2.847, not 2.258** (+26.1%) and `coffee-bean` is
**14.386, not 7.422** (+93.8%), confirmed by an independent Python merge agreeing
with the shipped binary to 0.09% on all seven stacks. **Consequence: the CLI help
text in `main.rs:138–141`, the doc comment in `merge_cmd.rs:78–80`, and the
`LADDERS` fixture at `merge_cmd.rs:1828` all quote numbers the shipped binary no
longer produces, and must be re-taken.**

**P2. MEASURED.** Across all seven stacks at gate 2.0, mean `n_eff` spans
**1.177 (`foam`) to 14.386 (`coffee-bean`) — 12.22x** — and the gate needed to
reach `n_eff` = 3 spans **0.7618 to 21.9934, a 28.9x range**. **Consequence: fact
324's conclusion is right and its magnitude is understated by 3.7x; `foam` cannot
reach the calibration target anywhere on the shipped 0.5–4.0 ladder, so any fixed
default gate is wrong for it by an order of magnitude.**

**P3. MEASURED.** Fact 324's stated mechanism is refuted: `n_eff/N` at gate 2.0
is 0.0118 / 0.0755 / 0.0783 / 0.0863 / 0.1110 / 0.1314 / 0.1369 across the seven
stacks — an **11.6x range** — and only two of M38's own five fall inside the
claimed 0.068–0.079 band. **Consequence: the acceptance set is not "a fixed
fraction of the bracket", `109MSDCF at 0.131 is unexplained` is not an isolated
exception, and no rule of thumb converts a bracket length into a gate.**

**P4. MEASURED.** A per-operator noise constant does not make the gate portable
across operators: five operators each carrying its own correctly measured
constant give mean `n_eff` from 2.806 to 12.727 at gate 2.0 on `109MSDCF`
(**4.54x**) and solved gates from 0.6079 to 2.1901 (**3.60x**), while a placebo
(the same operator by two code paths) spans **1.00000x**. **Consequence: the
plugin calibration seam is necessary and not sufficient — it fixes the units of
`--gate` and not its meaning — so an operator swap requires re-solving against a
target `n_eff` exactly as a stack swap does, and fact 436's substitution must not
be read as restoring portability.**

**P5. MEASURED.** Fact 436's substitution is exact for a scalar rescaling and
only for that: scaling the operator by 7 and its constant by 7 changes `n_eff` on
`109MSDCF` from 2.905129 to 2.905130 and moves **18 pixels in 8,236,816**, while
substituting a genuinely different operator moves `n_eff` by up to 4.54x and the
winner map on 71.5% of pixels. **Consequence: "an operator `k` times noisier
behaves exactly like the gate divided by `k`" is true of the same operator
rescaled and false of a different operator, and the word "exactly" must be scoped
in fact 436.**

**P6. MEASURED.** Two of fact 439's seven operators — `tenengrad-squared` and
`local variance` — are homogeneous of degree 2, so under a single divide by
`green_luma_sigma` their response SD is proportional to the local signal level,
measured at exactly **64.0000x over a 64x sigma sweep** against **1.0000x** for
all five degree-1 operators. **Consequence: their `k` is a constant only at
sigma = 1 DN; `strehl-plugin` handles this with
`Normalisation::LumaSigma { degree: 2 }` but `strehl-core/src/focus.rs` has a
single divide and no degree, so fact 509's 1.53x for the pending `tenengrad-sq`
edit is correct on the plugin path and understates by roughly the local sigma
(8.6–24.6 DN on this corpus) on the core path.**

**P7. MEASURED.** The host's calibration cannot check the one declaration the
plugin seam still contains: because `calibrate.rs:309` calibrates on a
`unit_sigma_model()` plane where `sigma^1 == sigma^2 == 1`, the measured constant
is identical to **8 decimal places** whichever `degree` a `FocusMeasure`
declares, while a mis-declared degree costs exactly `sigma^±1` (**17.480x** at
`109MSDCF`'s median sigma) on real data. **Consequence: `measure.rs`'s claim that
fault 5 is "unrepresentable ... there is no place in this file to put a wrong
number" is too strong — `Normalisation::LumaSigma { degree }` is that place — and
calibrating at a second, non-unit sigma would close it for the cost of one more
plane.**

**P8. MEASURED.** Fact 510's separability question is decidable and the answer is
"separable": forming the arm ratios per seed against the *measured* shipped arm
rather than the published constant removes the instrument's +0.47% offset and
gives `(radius x operator)/joint − 1` = **−0.00133% ± 0.01779%**.
**Consequence: fact 510's "NOT DECIDED" can be upgraded, and the general lesson
is that a ratio against a published constant inherits that constant's calibration
error while a paired ratio against a measured arm does not.**

**P9. MEASURED.** Fact 439's 10.4x span is partly a statement about this
repository's stencil normalisation conventions rather than about operator shape:
applying the same 1/8 that `focus.rs` applies to its Sobel to the Laplacian
family, 1/2 to Brenner, and taking the SD rather than the variance for local
variance gives a span of **2.12x** with every operator otherwise unchanged.
**Consequence: `k` is not a property of "the Laplacian" but of a specific written
stencil, so a contributor implementing the same textbook operator with a
different constant folded in gets a different `k`, and fact 439 must name the
convention it measured.**

**P10. DERIVED.** Fact 436's linearity check has no power to fail:
`Gate::tolerance()` is a single multiplication, and extending the sweep from the
published 35x to **10 decades** returns `tol/t` = 0.021515844 at every rung,
identical to 8 significant figures and equal to `sqrt(2) * 0.015214` exactly.
**Consequence: the published "constant to 2.0e-6" is an artefact of dividing a
6-decimal printed tolerance and should be recorded as arithmetic, not as a
measurement that could have failed and did not.**

### Disciplines

**P11.** A measurement against a sensor model must record the commit it was taken
at. Fact 324's numbers were invalidated **twice in one day** — by `2a4f5c5` at
09:41 and `f95f6f4` at 11:17 — and nothing in the fact row, the report or the
shipped CLI text says which model produced them. Cite the commit or the number is
not reproducible.

**P12.** A regression test that hard-codes measured data tests the code that
consumes the data, never the claim. `merge_cmd.rs`'s
`the_solved_gate_spans_the_range_fact_324_claims` passes today while two of its
three assertions are false of the current pipeline. If a test exists to defend a
fact, it must recompute the fact or be labelled as defending only the
interpolator.

**P13.** When a ratio is formed between two measured arms, pair them per seed
against a measured reference rather than dividing each by a published constant.
Fact 510 spent its verdict on an offset that paired ratios remove entirely
(+0.47% -> ±0.018%).

**P14.** A homogeneity or invariance test whose correct answer is exactly 1 must
be run on a *shared* realisation, not on independent draws per arm. My step 06
read 1.068x for an operator whose true answer is 1.000000; step 07, on a shared
realisation, read 1.000000 with deviation 0.00e+00.

**P15.** Before asserting that a measured effect is a defect in some code, read
that code. §7.1 is a case where a real, correctly measured, 64x effect was about
to be reported as a bug in a crate that already handled it.

### Questions

**P16.** What gate does `foam` actually want? It reaches `n_eff` = 3 only at gate
**21.99**, 5x higher than any other stack and above the entire shipped ladder.
`foam` is ISO 1000 with 1.20% of pixels clipped in at least one frame and
`boundary %` of exactly 0.00. Is this a real property of a low-contrast subject,
or is the focus field being dominated by something the noise model mis-prices?

**P17.** Should the host calibrate at two sigmas rather than one? One extra plane
at, say, sigma = 16 would make a mis-declared `Normalisation` degree detectable
at load time (P7), turning the seam's last declaration into a measurement. Is
there a reason not to?

**P18.** Given P4, is a per-operator noise constant worth its complexity, if the
gate must be solved per (operator, stack) pair regardless? The constant buys a
meaningful *unit* for `--gate`; it does not buy transferability. Fact 438's
load-time refusal may be defensible purely as a unit check rather than as a
calibration.

**P19.** Does the pending M17+M42 edit land in `focus.rs` or through the plugin
`FocusMeasure` path? Fact 509's 1.53x is right for one and wrong for the other by
roughly the local sigma, and no document in the repository says which.
