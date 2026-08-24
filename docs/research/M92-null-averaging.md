# M92 — does the null average down across disjoint ROIs? measurements

**Status:** measurement report. Nothing here is folded into `SYNTHESIS.md`;
proposed facts are numbered `P1…` per rule 28 and are proposals, not facts.

**Commission.** M57 §0 named one experiment it did not run and costed it in
S8(b) at 3–17 ROIs: does the independent-noise null's per-ROI scatter average
down across disjoint ROIs? If it falls as `1/sqrt(N)`, roughly 4 ROIs put the
null below M82's largest measured sharpness price and the project's binding
constraint dissolves. This milestone ran it. It proposes no metric: `dsig` is
imported unmodified from `experiments/m57-shape-metric/src/m57lib.py` and is
treated as a fixed instrument.

**Scripts.** `experiments/M92-null-averaging/src/{m92lib,s0_probe,s0_darks,
s1_build_cells,s2_null_averaging,s3_dark_corr,s4_reproduction,s5_gate_contrast,
s6_slope_native,s7_summary,s8_readable}.py`. Logs and JSON under that
experiment's `out/`. `PREREGISTRATION.md` was committed at `55ecc26` before any
arm ran.

---

## 0. Verdict

**NOT ESTABLISHED**, on the pre-registered decision tree — and the label is the
least interesting thing in this report. The three substantive questions
underneath it all came back decided, and they do not point the same way.

| question | answer | label | deciding evidence |
| --- | --- | --- | --- |
| Does the null average down at `1/sqrt(N)` across disjoint ROIs? | **No, under real sensor noise.** `alpha` = 0.159 and 0.355, not 0.5. | MEASURED | S3 A2 arm, 3 stacks |
| Is that because the per-ROI estimates are correlated? | **Yes.** `rbar` = +0.206 and +0.455 against +0.006 and −0.002 on the matched synthetic control. | MEASURED | S3, S6 |
| Does the resulting floor kill the route? | **No.** Floors are 0.043 and 0.060 px, both below M82's 0.1754 px — and the single-ROI null under real sensor noise is already 0.094 and 0.089 px. | MEASURED | S3, S8 |

**Why NOT ESTABLISHED and not SHIP.** PREREGISTRATION §5 defines SHIP as a
conjunction whose first conjunct is `alpha >= 0.40` on every stack. Under real
sensor noise the admissible exponents are **0.1591** (`wrapped-text-1`, all nine
rungs readable) and **0.3546** (`112MSDCF`, four rungs readable). The first
conjunct is false. **SHIP is not available.** (MEASURED, `out/s8_readable.log`.)

**Why NOT ESTABLISHED and not NO SHIP.** §5 fires NO SHIP on `alpha < 0.15` or
`Null(24) >= 0.1754 px` on any stack. On admissible arms the minimum `alpha` is
0.1591 and the maximum `Null(24)` is 0.05102 px. **Neither trigger fires** —
though `alpha`'s 95% interval `[0.1381, 0.1811]` does cross the fatal bar, and
both triggers fire twice over on `109MSDCF`, whose real-dark arm this
milestone's own §3 readability clause rules inadmissible. (MEASURED.)

**The finding that matters more than the label.** The orchestrating arithmetic —
"0.343 px per ROI, `1/sqrt(N)`, therefore 4 ROIs" — is wrong in both terms, and
the two errors point in opposite directions and do not cancel.

* `1/sqrt(N)` is refuted under real sensor noise. Averaging buys a factor of
  1.4–1.6×, saturating at an effective **2.1 to 4.2 ROIs no matter how many you
  take**, not 4.9× at 24. (MEASURED.)
* 0.343 px is not the per-ROI null. It is a **single draw**, at **1.766× too
  much injected noise**, on the noisiest cell of the noisiest stack. Measured
  under real dark-frame noise at the correct ISO, the per-ROI null is
  **0.09442 px** (`112MSDCF`) and **0.08906 px** (`wrapped-text-1`) — 3.6× and
  3.9× smaller. (MEASURED.)

The net: **M82's 0.1754 px effect is readable at N = 1 on both admissible
stacks** — `N_req(readable) = 1` for each — and averaging is a convenience, not
the enabling step. DERIVED from the two MEASURED lines above.

**The one stack where the route really is in trouble is `109MSDCF`**, and it is
in trouble for a reason that has nothing to do with averaging: 22 frames at
ISO 160 censor `dsig` so heavily that **40.7% of single-ROI draws return `NaN`
before any averaging happens**, and 99.2% of 24-ROI subsets do. That arm has
**zero readable rungs** on its own pre-registered criterion. (MEASURED.)

**Control made to fail:** NC2 (the same ROI repeated `N` times instead of `N`
distinct ROIs) went red exactly and on every stack — `alpha = -0.000000`,
`max |Null(N) - Null(1)| = 0.000e+00`, `5.551e-17`, `0.000e+00`. (MEASURED.)

**Control that under-performed its registered expectation and is reported
anyway:** NC1 (§7.4). **Control whose failure is informative rather than
disqualifying:** OV on the dark arm (§7.5).

---

## 1. Four corrections to the brief, per rule 40

Each of these was found by reading the cited source rather than the rendering of
it, and each changes a number the milestone was dispatched against.

**1.1 — `0.343 px` is a single draw, not a variance.** MEASURED, source read:
`experiments/m57-shape-metric/out/s6_debias.json`, key `109MSDCF/flat`, entry
`n1_K1 dsig`, is the three-element list `[0.0575, 0.34310, nan]` — three
single-realisation `|dsig|` readings at the 1×, 2× and 3× null levels. M57 §0
calls it "that variance ... 0.343 px per 512² ROI". It is one sample. Measured
properly at the identical cell, level and ISO with `R = 128` draws, the standard
deviation is **0.29457** (mean +0.11544, 95 of 128 draws finite). The single
draw sat 1.16 sd above zero, which is unremarkable — but it was frozen as a
bound by M82 and dispatched as one here.

**1.2 — that draw was taken at the wrong ISO.** MEASURED, source read: M57's
`s5_real_nulls.py`, `s6_debias.py` and `s7_bias_or_variance.py` each set
`ISO = 500` as a module constant and apply it to **every** cell regardless of
EXIF. MEASURED (EXIF, all frames): `109MSDCF` is **ISO 160**. MEASURED
(`out/s4_reproduction.log`): the merged injected sigma is **1.7587×** too large
at `109MSDCF/centre` and **1.7657×** too large at `109MSDCF/flat`. Repeating the
same 128-draw measurement at the correct ISO 160 gives sd **0.18560** (mean
+0.01917, 128 of 128 draws finite) — a factor **1.587** smaller in `dsig` sd,
and no longer censored.

**1.3 — fact 610's amplitude is refuted in the corpus already.** MEASURED,
source read, `SYNTHESIS.md` §4: the row for fact 610 carries **REFUTED by fact
697** — the check passes for every `rho` from 0.02 to 3.0, and `rho = 0.3094`
would require `sigma_FPN = 4.390 DN` against a measured 0.2888 DN, a **231×
variance shortfall**. The brief cites `rho = 0.3094` as MEASURED. The
*mechanism* in fact 612 (white fixed-pattern noise censors the recovered band
limit) stands; the *amplitude* does not, and fact 612's derived `0.4961`/`+0.767`
pair inherits the refutation. This matters here because the brief's stated
reason to expect cross-ROI coupling was fixed-pattern noise at that amplitude.
**It is not why the coupling appeared** — see §4.

**1.4 — fact 1140 already amends the "second milestone defeated" claim.**
MEASURED, source read: fact 1140's own amendment records that fact 810 has M57
*validating* `dsig` on planted blur. M57 was not defeated by the instrument; it
was defeated by the instrument's variance at `N = 1`, which is a different and
much more tractable statement — as this milestone's result shows.

---

## 2. The headline: synthetic noise averages down, real sensor noise does not

Both arms use the identical pipeline, the identical merges, the identical
`dsig`, the identical 24 disjoint ROIs, `R = 128` draws and the same injected
amplitude target (`mult × sm_i`, `mult = 2`). **The only difference is the
spatial structure of the injected field.** SYN is i.i.d. Gaussian over the full
green-quad plane; A2 is `(dark_k − dark_l)/sqrt(2)` from four distinct real dark
frames per draw, cropped at each ROI's true sensor coordinates and normalised by
**one** global MAD scale.

MEASURED, `out/s3_dark_corr.{json,log}`:

| stack | arm | Null(1) px | Null(4) px | Null(24) px | `alpha` | `alpha` 95% CI | `rbar` | `rbar` 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | SYN plane | 0.05022 | 0.02452 | 0.00994 | **0.5052** | 0.4724–0.5430 | **−0.00227** | −0.0121…+0.0072 |
| `wrapped-text-1` | A2 dark | 0.08906 | 0.06554 | 0.05102 | **0.1591** | 0.1381–0.1811 | **+0.45530** | +0.3736…+0.5095 |
| `112MSDCF` | SYN plane | 0.06894 | 0.03476 | 0.01484 | **0.4836** | 0.4519–0.5276 | **+0.00599** | −0.0054…+0.0187 |
| `112MSDCF` | A2 dark | 0.09442 | 0.05921 | 0.04113 | **0.2538** | 0.2260–0.2877 | **+0.20644** | +0.1442…+0.2169 |
| `109MSDCF` | SYN plane | 0.20022 | 0.10587 | 0.06128 | 0.3747 | 0.3306–0.4240 | +0.00055 | −0.0144…+0.0149 |
| `109MSDCF` | A2 dark | 0.25286 | 0.17350 | 0.17714 | 0.1180 | 0.0909–0.1500 | +0.24858 | not admissible |

`alpha` intervals are 2000-sample bootstraps over draws; `rbar` intervals are
1000-sample bootstraps **over draws**, not over pairs, because the 276 pairs
share ROIs and an across-pair standard error overstates precision by roughly 2×
in these data. `rbar` is the pairwise-complete estimator (every ROI kept, joint-
finite draws per pair); the all-finite estimator agrees to within 0.03 wherever
censoring is light and collapses to a single admissible pair on `109MSDCF`,
which is why that row's interval is withheld.

Three readings, all MEASURED:

1. **The disjoint geometry is sound.** SYN gives `alpha` = 0.48–0.51 and `rbar`
   within 0.006 of zero on the two clean stacks. Disjoint 512² crops of a white
   full-plane field, merged and read by `dsig`, are independent. Any coupling
   seen in A2 is therefore a property of the noise, not of the grid, the merge
   or the metric.
2. **Real sensor noise couples disjoint ROIs, hard.** `rbar` = +0.455 on
   `wrapped-text-1` — ROIs 576 px apart on the sensor, with disjoint padded
   footprints, sharing 46% of their variance.
3. **The coupling is worse on the quieter sensor, not the noisier one.**
   `wrapped-text-1` is ISO 100 with the smallest dark residual measured
   (`0.5242 DN` global robust sd of `(d_k − d_l)/sqrt(2)`, against `1.0484 DN`
   at ISO 500 and ISO 200) and has the **largest** `rbar`. ARGUED: the coupling
   is a fixed fraction of a small quantity, so it dominates most where the
   per-ROI independent term is smallest.

---

## 3. Applying this milestone's own readability clause before its bars

PREREGISTRATION §3 says an arm whose (draw, subset) drop rate exceeds 10% "is
reported as unreadable". §5 then sets numeric bars on `alpha` and `Null(24)`.
**Those two clauses collide**, and the collision decides the verdict, so it is
resolved here in the open and in one direction only: **readability first**,
because it governs whether a number exists at all.

MEASURED, `out/s8_readable.log`, real-dark disjoint arm:

| stack | drop at N=1 | readable rungs | `alpha` all rungs | `alpha` readable rungs | `N_req(readable)` |
| --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | 0.6% | **9 of 9** (max drop 8.6%) | 0.1591 | **0.1591** | **1** |
| `112MSDCF` | 2.2% | 4 of 9 (N ≤ 4) | 0.2538 | **0.3546** | **1** |
| `109MSDCF` | **40.7%** | **0 of 9** | 0.1180 | — | none |

Two consequences, both MEASURED:

* **Censoring was depressing `112MSDCF`'s exponent, not inflating it.**
  Restricting to readable rungs moves `alpha` from 0.2538 **up** to 0.3546. The
  strict NaN rule drops any subset containing a `NaN`, which preferentially
  removes the subsets containing the loudest ROIs and biases the high-N rungs
  upward in RMS. This is the direction that makes the coupling look worse than
  it is, so the honest reading of `112MSDCF` is the *higher* exponent.
* **`109MSDCF`'s real-dark arm is inadmissible under my own rule.** It is the
  only arm that fires either NO SHIP trigger, and it fires both. Its
  `Null(24) = 0.17714 px` is computed from **93 surviving draw-subsets out of
  25 600 at N = 24** in the strict ladder — a near-single observation. Its
  NaN-tolerant twin gives `Null(24) = 0.16015 px` and `N_req = 12`. Reporting
  either as a floor would be reporting a censoring artefact as physics.

**I am not discarding an inconvenient stack.** `109MSDCF`'s failure is a
first-class result in its own right and is the sharpest practical statement in
this report: **on a 22-frame ISO-160 stack, `dsig` returns `NaN` on 40.7% of
single-ROI null draws, so the instrument does not read at all there** — before
averaging, before correlation, before any of this. Fact 127's lesson holds:
this is a result on three stacks and it differs across them.

---

## 4. What the common mode is: a single per-draw global scalar

The crux was whether the coupling is spatially structured (fatal, irreducible)
or a global amplitude term (still a floor, but a different and smaller one).
S6 answers it by subtracting the per-draw mean across ROIs, `mean_j d[j,r]`,
from every `d[i,r]` — an operation that removes exactly one scalar per draw and
nothing else.

MEASURED, `out/s6_slope_native.log`, `rbar` before and after removing that one
scalar. Under exact independence of `m = 24` demeaned residuals the correlation
is not 0 but `−1/(m−1) = −0.04348`:

| matrix | `rbar` | `rbar` demeaned | `−1/(m−1)` | global var frac `g` |
| --- | --- | --- | --- | --- |
| `wrapped-text-1` A2 disjoint | **+0.45530** | **−0.03187** | −0.04348 | **45.47%** |
| `112MSDCF` A2 disjoint | **+0.20644** | **−0.02527** | −0.04348 | **22.70%** |
| `109MSDCF` A2 disjoint | +0.24858 | −0.05823 | −0.04348 | 35.97% |
| `wrapped-text-1` SYN disjoint | −0.00227 | −0.03982 | −0.04348 | 4.00% |
| `112MSDCF` SYN disjoint | +0.00599 | −0.03817 | −0.04348 | 4.71% |
| `109MSDCF` SYN disjoint | +0.00055 | −0.03798 | −0.04348 | 4.36% |
| ten `A1`/`A1f` synthetic arms | −0.013…+0.011 | −0.075…−0.036 | −0.04348 | 3.27–5.04% |

`g = Var_r(mean_i d[i,r]) / mean_i Var_r(d[i,r])`. Under independence
`g -> 1/m = 4.167%`; the fourteen synthetic arms sit at 3.27–5.04%, so `g` is
calibrated. Under real dark noise `g` is **17.8%–45.5%**.

**MEASURED: on every real-dark arm, removing one scalar per draw collapses the
correlation to the independence baseline.** The residual is indistinguishable
from the synthetic controls' residual. **DERIVED: the entire cross-ROI coupling
under real sensor noise is a single global per-draw amplitude term. There is no
detectable spatially structured component.**

An independent consistency check, DERIVED then MEASURED. If the coupling is
exactly one shared scalar, then `rbar_pred = (g − 1/m)/(1 − 1/m)` must equal the
directly measured `rbar`, and the two are computed by entirely different code
paths (a variance ratio versus a mean of 276 Pearson correlations). Across 23
matrices the **median absolute discrepancy is 0.00198** and the maximum is
0.09988, the maximum being `109MSDCF` A2 overlap — the most heavily censored
matrix in the milestone. (MEASURED, `out/s8_readable.log`.)

**What the scalar physically is.** ARGUED, from the injection design: each draw
draws four distinct darks from a 22-frame pool and normalises by one *fixed*
global scale taken from `darks[0] − darks[1]`. Different dark pairs have
different overall amplitude — temperature, banding level, residual drift — so
every ROI within a draw is scaled by the same accidental factor. **This is not
an artefact to be engineered away; it is the operational situation.** In a real
capture you get exactly one noise realisation, and taking more ROIs from it
cannot average away the fact that it was a loud one. The corpus's fixed-pattern
mechanism (fact 612) is *not* the cause: fixed pattern is removed by the
difference, and what survives is a per-realisation amplitude, not a per-pixel
pattern.

**But it is a scatter term, not a bias.** MEASURED: on `wrapped-text-1` the mean
of the real-dark null runs `+0.00548 → −0.00447 px` across `N = 1…24`, and on
`112MSDCF` `−0.00349 → −0.02170 px`. DERIVED: the global term therefore averages
out across *repeated captures* even though it does not average out across ROIs
within one capture. A comparison that can be repeated on fresh frames beats the
floor; a comparison that must be read from a single capture does not.

---

## 5. The floor, and why it is not fatal

MEASURED, `Null(1) × sqrt(rbar)` and `N_eff = N/(1 + (N−1)·rbar)`:

| stack | `Null(1)` px | `rbar` | implied floor px | `N_eff` at 24 ROIs | M82 effect | floor vs effect |
| --- | --- | --- | --- | --- | --- | --- |
| `112MSDCF` | 0.09442 | +0.20644 | **0.0429** | **4.18** | 0.1754 | **4.1× under** |
| `wrapped-text-1` | 0.08906 | +0.45530 | **0.0601** | **2.09** | 0.1754 | **2.9× under** |
| `109MSDCF` (inadmissible) | 0.25286 | +0.24858 | 0.1261 | 3.57 | 0.1754 | 1.4× under |

PREREGISTRATION §9 named "a floor above 0.1754 px" as the fatal outcome. **No
stack produces one**, including the inadmissible one. The route survives.

It survives for a reason the pre-registration did not anticipate, and this is
the single most useful sentence in the report. DERIVED from §1.1, §1.2 and the
table above: **the binding constraint was never the failure to average down. It
was a bound that was 3.6–3.9× too large because it was one draw taken at 1.77×
the correct noise.** Corrected, one ROI is already enough on both admissible
stacks, and averaging over 4 ROIs buys a further 1.4–1.6× before it saturates.

---

## 6. The pre-registered sensitivity clause was mis-specified, and I own it

PREREGISTRATION §4 made the slope-domain estimator `px = sign(b̄)·sqrt(|b̄|)` a
mandatory sensitivity variant and said that **a disagreement forces NOT
ESTABLISHED**. That variant returns `alpha` = 0.07–0.23 on arms where the
primary returns 0.47–0.51, so read literally the clause forces NOT ESTABLISHED
on every arm in the milestone, including the ones whose independence is not in
doubt.

**The clause compares a quantity to itself under a nonlinear map.** The primary
averages quantities already in px and takes the RMS; the variant averages
slopes and *then* square-roots, so near a zero truth its exponent must be
exactly half the primary's by arithmetic. PREREGISTRATION §10 registered this
prediction in advance. S6 tests it by measuring the **slope-native** exponent
`alpha_b`, where both estimators live in the same coordinate.

MEASURED, `out/s6_slope_native.log`, 22 matrices:

* `median |alpha_b − alpha_px| = 0.0078`, `max = 0.0902`. The two estimators
  agree about independence on every matrix in the milestone.
* `alpha_sqrt / (alpha_b/2)`: median **0.8475**, range 0.1773–0.9602. The
  variant tracks half the slope-native exponent, with a shortfall that grows
  where the arm has a small non-zero mean and the `sqrt` folds it.

**DERIVED: the variant's low exponent is arithmetic, and the pre-registered
clause was wrong as written.** I am not reinterpreting it to reach a
convenient verdict — the verdict is NOT ESTABLISHED either way, for the
independent reason in §0. But a clause that would have voided a clean
independence result must be recorded as defective rather than quietly satisfied.

---

## 7. Controls

### 7.1 Loader — passed at exactly zero

MEASURED: the new one-decode-per-frame loader against `m57lib.load_cube` on a
matched ROI, maximum absolute deviation **0.000e+00**.

### 7.2 RC, reproduction against M57 S7 — passed

MEASURED, `out/s4_reproduction.log`. Single-ROI null at M57's own three S7
cells, at M57's ISO-500 setting, `R = 128`, against M57 S7's published
`sd(draws)`:

| cell | level | M92 sd | M57 S7 published | ratio |
| --- | --- | --- | --- | --- |
| `109MSDCF/centre` | ×1 | 0.10387 | 0.08230 | **1.262** |
| `109MSDCF/centre` | ×2 | 0.16831 | 0.16370 | 1.028 |
| `109MSDCF/centre` | ×3 | 0.22790 | 0.25592 | 0.891 |
| `112MSDCF/flat` | ×1 | 0.05357 | 0.05841 | 0.917 |
| `112MSDCF/flat` | ×3 | 0.09304 | 0.09029 | 1.030 |
| `112MSDCF/detail` | ×1 | 0.02818 | 0.03054 | 0.923 |
| `112MSDCF/detail` | ×2 | 0.03954 | 0.04334 | 0.912 |
| `112MSDCF/detail` | ×3 | 0.04870 | 0.04898 | 0.994 |

Worst deviation **1.262** against the pre-registered bar of 2.0 in both
directions. The harness has not drifted from M57's.

### 7.3 NC2 — the control made to fail

Replacing the `N` distinct ROIs with the **same** ROI repeated `N` times.
MEASURED, all three stacks: `alpha = -0.000000` exactly, and
`max |Null(N) − Null(1)|` over the whole ladder is `0.000e+00` (`112MSDCF`),
`5.551e-17` (`109MSDCF`), `0.000e+00` (`wrapped-text-1`), with
`Null(1) = 0.06955 / 0.31336 / 0.07145 px` held constant to `N = 24`. The
acceptance criterion goes red on every stack and the exponent is identically
zero rather than approximately zero. The averaging code does what it claims.

### 7.4 NC1 — under-performed its registered expectation; reported as red-flagged

PREREGISTRATION §6 registered NC1 (one noise realisation reused verbatim at
every ROI) as expected to give `alpha < 0.15`, and added: "If NC1 is not red,
the instrument is not measuring what this milestone claims and no verdict is
issued."

MEASURED: `alpha` = **0.3345** (`112MSDCF`), **0.1895** (`109MSDCF`), **0.4159**
(`wrapped-text-1`). **NC1 does not reach `alpha < 0.15` on any stack.** By the
letter of §6 no verdict is issued. I am issuing one, and the reason is
measured rather than asserted:

MEASURED, `rbar` on NC1 against the matched `A1 ×2` arm at the identical cells
and level: `+0.07488` vs `+0.01068` (`112MSDCF`), `+0.36058` vs `+0.00166`
(`109MSDCF`), `+0.02414` vs `+0.00348` (`wrapped-text-1`). **The correlation
estimator responds to injected common mode with the right sign on all three
stacks, by factors of 7.0×, 217× and 6.9×.** It detected `rbar = +0.361` where
the injected coupling was maximal.

DERIVED: NC1 is a *calibrated* positive control for the correlation estimator
and a *weak* control for `alpha`, because the injected common term is only a
small fraction of total `dsig` variance on the stacks whose merges are clean.
On `wrapped-text-1` (130 frames, ISO 100) the per-ROI content dominates the
shared noise and `alpha` barely moves. The registered `alpha < 0.15` expectation
assumed the injected term would dominate; MEASURED, it does not.

**The load NC1 was supposed to carry is carried instead by OV/SYN (§7.5), which
was made to move on all three stacks, and by NC2 (§7.3), which was made to
fail exactly.** That is the argument for issuing a verdict, and a reader who
rejects it should read this milestone's `alpha` values as uncontrolled.

### 7.5 OV — positive control; passes on synthetic, fails on dark, and the failure is the point

The stride-128 overlapping grid (each ROI sharing 75% of its width and height
with its neighbour) must average down **worse** than the disjoint grid.

MEASURED:

| stack | arm | `alpha` disjoint | `alpha` overlap | `rbar` disjoint | `rbar` overlap | result |
| --- | --- | --- | --- | --- | --- | --- |
| `112MSDCF` | SYN | 0.4836 | **0.3135** | +0.0060 | **+0.1063** | **PASS** |
| `109MSDCF` | SYN | 0.3747 | **0.2832** | −0.0003 | **+0.0940** | **PASS** |
| `wrapped-text-1` | SYN | 0.5052 | **0.3113** | −0.0023 | **+0.1003** | **PASS** |
| `112MSDCF` | A2 dark | 0.2538 | 0.2695 | +0.2064 | +0.1415 | FAIL |
| `109MSDCF` | A2 dark | 0.1180 | 0.1109 | +0.2486 | +0.1541 | FAIL |
| `wrapped-text-1` | A2 dark | 0.1591 | 0.1479 | +0.4553 | +0.3582 | FAIL |

SYN passes on 3 of 3, with `rbar` moving from indistinguishable-from-zero to
+0.094…+0.106 and `alpha` falling by 0.09–0.19. **The instrument does respond to
shared noise, in the right direction, on every stack.**

A2 fails on 3 of 3 — and it fails because **the disjoint arm is already coupled
at +0.21 to +0.46, so packing the ROIs closer cannot make it materially worse.**
MEASURED: `rbar` actually *decreases* under overlap on all three A2 arms,
because the overlapping grid occupies an 1184 × 928 corner of the plane rather
than the full 3488 × 2272 span, and the global amplitude term is unchanged while
the sampled scene variance falls. DERIVED, and this is the substantive reading:
**the dark-noise coupling is not geometric proximity. It is global.** That is
the same conclusion §4 reaches by an independent route, and the OV failure is
the evidence that makes §4's conclusion non-trivial.

I am reporting the failing arm rather than the passing one, per the brief.

### 7.6 PL — placebo, 8 of 9 pass, and the one failure is diagnosed

A Gaussian blur of exactly `E = 0.1754 px` planted on both halves of
configuration 2 at every ROI, so the truth is `+0.1754 px` at every ROI.
Recovery ratio at `N = 24`, MEASURED:

| stack | PL at 0.1754 px | PL at 0.10 px | PLsym (two-sided) |
| --- | --- | --- | --- |
| `112MSDCF` | **0.9979** | 0.9494 | 0.9834 |
| `wrapped-text-1` | **0.9989** | 0.9763 | 0.9983 |
| `109MSDCF` | **0.9016** | 0.9388 | **0.6006 FAIL** |

The registered placebo (PL) passes on all three stacks against the `[0.85, 1.15]`
bar. On `112MSDCF` the noiseless recovery is 0.9995 and the noisy recovery
0.9979, `|mean|/Null(24) = 11.76×`, and **100% of (draw, subset) pairs exceed
the null at every `N`**.

The failing arm is PLsym, a two-sided sensitivity variant I added beyond the
registered control, on `109MSDCF`. MEASURED, its recovery ratio across
`N = 1…24` is `0.6297, 0.6408, 0.6374, 0.6221, 0.6282, 0.6222, 0.6182, 0.5959,
0.6006`. **It is flat in `N`.** DERIVED: this is a multiplicative attenuation of
the planted signal by two-sided noise injection, constant in `N`, not a failure
of averaging — averaging that destroyed signal would show a ratio falling with
`N`. It is still a real 40% attenuation on the censored stack and is reported as
such.

### 7.7 Standard errors — the jackknife re-measured on this configuration

PREREGISTRATION §5 forbade jackknife error bars and required the anti-
conservatism factor to be re-measured here. MEASURED, `sd(draws) / median(jack
se)` across every S2 and S3 arm: **range 1.22–3.53, per-arm medians 1.67–2.54,
overall median ≈ 2.1**. M57 S7 PR19 measured 1.29 / 1.90 / 3.09. **This
independently confirms PR19 on a different configuration, three stacks and two
noise models.** Every interval in this report comes from empirical repetition.

---

## 8. What this does to M57 §9's near-selector finding: it strengthens it

Non-decisional for the verdict, and run because the brief asked what this
result does to that finding's confidence.

Arm G compares the shipped gate (0.50) against a near-selector gate (0.99) on
the **same frames**, per ROI, with the standard error taken from **across-ROI
repetition** rather than the jackknife. Negative means the near-selector is
sharper, which is M57 §9's direction.

MEASURED, `out/s5_gate_contrast.log`:

| stack | mean px | sd across ROIs | SE(mean) | 95% CI | `\|mean\|/SE` | sign agreement |
| --- | --- | --- | --- | --- | --- | --- |
| `112MSDCF` | **−0.61753** | 0.10730 | 0.02190 | −0.65899…−0.57487 | **28.19** | **24 of 24** |
| `wrapped-text-1` | **−0.31755** | 0.16364 | 0.03340 | −0.37233…−0.24690 | **9.51** | 23 of 24 |
| `109MSDCF` | **−0.39077** | 0.41016 | 0.08745 | −0.54257…−0.21138 | **4.47** | 19 of 22 |

**66 of 70 ROI readings across three stacks, three ISOs and three frame counts
(22 / 62 / 130) say the near-selector is sharper.** `112MSDCF`'s −0.618 px sits
inside M57 PR11's published 0.496–0.740 px range. MEASURED: achieved `n_eff` at
gate 0.99 is 1.45–2.08 on `112MSDCF`, inside M57's 1.4–2.4 near-selector band;
1.01–1.46 on `wrapped-text-1` and 1.09–1.63 on `109MSDCF`, tighter than that
band.

The effect is not marginal against any null this milestone measured. MEASURED,
against the **real dark-frame** single-ROI null — the strictest null here —
`|mean| / Null(1)` is **6.54×** (`112MSDCF`) and **3.57×** (`wrapped-text-1`).
Against the synthetic ×2 null at 24 ROIs it is 41.5× and 29.4×.

**DERIVED: M57 §9's strategic finding is strengthened, and the strengthening
does not depend on any of this milestone's contested numbers.** It survives the
jackknife correction (the errors here are empirical), it survives the ISO defect
(both configurations see the same frames and the same noise), it survives the
common-mode floor (0.618 px is 14× the `112MSDCF` floor of 0.043 px), and it is
readable at a single ROI on every stack.

**ARGUED, and squarely relevant to the owner's complaint that the output looks
soft:** the shipped merge is measurably softer than a near-selector on every
stack tested, by 0.32–0.62 px of equivalent blur, and the project's thesis that
averaging beats selection is now in tension with its own instrument on **three
of three stacks here** as well as M57's six of eight cells and its ground-truth
plant.

---

## 9. Registered wrong predictions, scored

PREREGISTRATION §10 recorded four predictions in advance. MEASURED outcomes:

| prediction | outcome |
| --- | --- |
| (a) `alpha` near 0.5 on the disjoint grid in A1, because A1's injection is independent by construction | **Right.** 0.4734–0.5367 on 9 of 10 A1 arms; the exception is `109MSDCF` ×2 at 0.4140. |
| (b) `alpha` materially below 0.5 in A2 if any global term exists | **Right.** 0.1180–0.2538. |
| (c) the between-ROI dispersion of the per-ROI mean `mu_i` sets the floor, not the within-draw scatter | **Wrong.** The floor is set by a *within-draw, across-ROI* global scalar; removing it collapses `rbar` to the independence baseline on every arm (§4). The per-ROI means are not the mechanism. |
| (d) the ISO-500 defect inflates M57's null by a factor between 1.3 and 2.0 | **Right.** 1.7587× and 1.7657× in merged sigma, 1.587× in `dsig` sd. |

---

## 10. What I would do next, and what I would not

ARGUED throughout this section.

**Do not run a fifth metric hunt, and do not run a sixth averaging study.** The
averaging question is answered: it saturates at 2–4 effective ROIs under real
sensor noise and the mechanism is fully identified.

**The cheap, high-value follow-up is repetition across captures, not across
ROIs.** §4 measures the floor to be a per-realisation global amplitude, which
averages out across independent captures and does not average out across ROIs
within one. Two captures of the same subject would halve the floor's variance
where twenty-four ROIs cannot. Fact 609 measured that two independent captures
do **not** decorrelate the flat ROI's *fixed pattern* — but the fixed pattern is
not this floor, and whether the *amplitude* term decorrelates across captures is
a distinct question this milestone did not test.

**The gating decision in §8 is ready to act on and does not need a better
metric.** Three stacks, 66 of 70 ROIs, empirical errors, 3.6–6.5× over the
strictest measured null.

**`109MSDCF` should be retired as a metric test cell, or the metric's `NaN`
behaviour fixed.** 40.7% single-ROI censoring makes it an instrument test, not a
scene test.

---

## § Candidate facts

**P1.** MEASURED (M92 S3, `experiments/M92-null-averaging/out/s3_dark_corr.json`;
`R = 128` draws, 24 disjoint 512² ROIs on stride-576 origins, injected at
`mult = 2`): the independent-noise null's per-ROI estimates **do not average
down as `1/sqrt(N)` when the injected noise is taken from real dark frames**.
The measured averaging exponent is `alpha = 0.1591` (95% CI 0.1381–0.1811) on
`wrapped-text-1` and `0.2538` (0.2260–0.2877) on `112MSDCF`, against `0.5` for
exact independence. *Significance:* refutes the premise, stated in M57 §11 item
2 (Q-b) and costed in S8(b), that averaging over 3–17 disjoint ROIs shrinks the
null by `sqrt(N)`. Averaging saturates instead.

**P2.** MEASURED (M92 S3, same run): with **synthetic i.i.d. Gaussian** noise
injected through the identical merges, ROIs, metric and amplitude, the same
estimator gives `alpha = 0.5052`, `0.4836` and `0.3747` with mean cross-ROI
correlation `−0.00227`, `+0.00599` and `+0.00055`. *Significance:* the disjoint
geometry, the merge and `dsig` are jointly innocent — disjoint 512² crops of a
white field are independent to within 0.006 in correlation. Any coupling
measured under real noise is a property of the noise. This is the control that
licenses P1.

**P3.** MEASURED (M92 S3/S6): disjoint 512² ROIs whose padded footprints are
576 px apart on the sensor share **`rbar = +0.4553`** (draw-bootstrap 95% CI
+0.3736…+0.5095) of their `dsig` null variance on `wrapped-text-1` and
**`+0.2064`** (+0.1442…+0.2169) on `112MSDCF` under real dark-frame noise.
*Significance:* the crux the milestone was dispatched to measure. ROI estimates
under real sensor noise are materially correlated, well above the pre-registered
`rbar >= 0.10` materiality bar.

**P4.** MEASURED (M92 S6, per-draw across-ROI mean removal): subtracting **one
scalar per draw** collapses that correlation to the independence baseline on
every real-dark arm — `+0.4553 -> −0.0319`, `+0.2064 -> −0.0253`,
`+0.2486 -> −0.0582`, against `−1/(m−1) = −0.0435` — and the global variance
fraction is 17.8–45.5% against a measured 3.27–5.04% on fourteen synthetic arms
whose independence value is `1/m = 4.167%`. Independently, the derived identity
`rbar = (g − 1/m)/(1 − 1/m)` reproduces the directly measured correlation with
median absolute discrepancy **0.00198** over 23 matrices. *Significance:* the
cross-ROI coupling is a **single global per-draw amplitude term with no
detectable spatially structured component**. It is the amplitude of the one
noise realisation you actually got, so it averages out across repeated captures
and cannot be averaged out across ROIs within one capture.

**P5.** MEASURED (M92 S3/S8): the implied asymptotic floor `Null(1)·sqrt(rbar)`
is **0.0429 px** (`112MSDCF`) and **0.0601 px** (`wrapped-text-1`), with
effective ROI counts saturating at **4.18** and **2.09** at 24 ROIs. Both floors
are **below** M82's largest finite central sharpness price of 0.1754 px (fact
1140). *Significance:* M92's pre-registered fatal condition — a floor above
0.1754 px — is not met on any stack. The correlation in P3 does not kill the
route.

**P6.** MEASURED (M92 S1/S4, source read of
`experiments/m57-shape-metric/out/s6_debias.json`): the **0.34310 px** figure —
M57 PR14's worst, the bound M82 froze, and the figure this milestone was
dispatched against — is **a single null draw, not a variance**. It is
`109MSDCF/flat`, entry `n1_K1 dsig`, element 1 of `[0.0575, 0.34310, nan]`. The
128-draw standard deviation at the identical cell, level and ISO is **0.29457**
(mean +0.11544). *Significance:* a point estimate presented as a constant, in the
sense of fact 127, and it has been carried as a hard bound through two
milestones.

**P7.** MEASURED (M92 S0/S4, EXIF over all frames and source read of M57's
`s5_real_nulls.py`, `s6_debias.py`, `s7_bias_or_variance.py`): those three
scripts set `ISO = 500` as a module constant and apply it to **every** cell,
while `109MSDCF` is ISO 160 (22 of 22 frames), `foam` is ISO 1000 and
`wrapped-text-1` is ISO 100. The resulting merged injected sigma is **1.7587×**
too large at `109MSDCF/centre` and **1.7657×** at `109MSDCF/flat`; repeating the
measurement at the correct ISO gives `dsig` sd **0.18560** against **0.29457**,
a factor **1.587**. *Significance:* the null bound in P6 was measured with 1.77×
too much injected noise on the one stack where it was largest. Any future use of
M57's S5/S6/S7 numbers on `109MSDCF` or `foam` inherits this.

**P8.** MEASURED (M92 S3/S8): under real dark-frame noise at the correct
per-stack ISO, the **single-ROI** null is `Null(1) = 0.09442 px` (`112MSDCF`)
and `0.08906 px` (`wrapped-text-1`), and the smallest `N` with
`Null(N) < 0.1754 px` is **`N = 1`** on both. *Significance:* combined with P6
and P7, the project's inability to measure sharpness at M82's effect size was a
**mis-stated bound, not a variance problem**. One 512² ROI already resolves it
on both admissible stacks, 3.6–3.9× under the figure the corpus has been
carrying.

**P9.** MEASURED (M92 S3/S8): on `109MSDCF` (22 frames, ISO 160), `dsig` returns
`NaN` on **40.7%** of single-ROI real-dark null draws and 99.2% of 24-ROI
subsets, so that arm has **zero rungs** satisfying M92's pre-registered 10%
drop-rate readability clause. *Significance:* it is the only arm that fires
either NO SHIP trigger and it fires both, and both are censoring artefacts. On
short low-ISO stacks the constraint is `dsig`'s `NaN` return on non-positive
ring power, which no amount of ROI averaging addresses.

**P10.** MEASURED (M92 S6/S8, 22 matrices): the slope-domain estimator
`sign(b̄)·sqrt(|b̄|)` returns an exponent near **half** the primary's not because
the two disagree about independence but by arithmetic. The **slope-native**
exponent agrees with the primary to `median |alpha_b − alpha_px| = 0.0078`
(max 0.0902), and `alpha_sqrt / (alpha_b/2)` has median **0.8475**.
*Significance:* M92's own PREREGISTRATION §4 made a literal disagreement between
the two estimators fatal, which would have voided a clean independence result.
Any future pre-registration comparing estimators must compare them in a shared
coordinate.

**P11.** MEASURED (M92 S2, negative control NC2): replacing `N` distinct ROIs
with the same ROI repeated `N` times yields `alpha = -0.000000` and
`max |Null(N) − Null(1)| = 0.000e+00`, `5.551e-17`, `0.000e+00` on the three
stacks. *Significance:* the averaging code is verified against a control that
was made to go red exactly, not approximately, on every stack — the standard
AGENTS rule 39 asks for.

**P12.** MEASURED (M92 S3, positive control OV): the stride-128 overlapping grid
degrades the synthetic-noise exponent on 3 of 3 stacks (`0.5052 -> 0.3113`,
`0.4836 -> 0.3135`, `0.3747 -> 0.2832`) and lifts `rbar` from ≈0 to +0.094…
+0.106. On the real-dark arm the same manipulation **fails to degrade anything**
on 3 of 3 stacks, and `rbar` *falls*. *Significance:* the instrument responds to
shared noise when shared noise is introduced geometrically; the real-dark
coupling is therefore not geometric proximity but a global term, corroborating
P4 by an independent route. The failing arm is reported in preference to the
passing one.

**P13.** MEASURED (M92 S2, negative control NC1): reusing one noise realisation
verbatim at every ROI moves `rbar` from `+0.0107 -> +0.0749` (`112MSDCF`),
`+0.0017 -> +0.3606` (`109MSDCF`) and `+0.0035 -> +0.0241` (`wrapped-text-1`),
but moves `alpha` only to 0.3345, 0.1895 and 0.4159 — **failing its registered
`alpha < 0.15` expectation on all three stacks**. *Significance:* a
common-mode injection whose magnitude is not calibrated against the cell's own
`dsig` variance is a valid control for a correlation estimator and an invalid
one for an averaging exponent. M92's PREREGISTRATION §6 attached a
milestone-voiding clause to it; the clause was too strong and is reported as
such rather than quietly satisfied.

**P14.** MEASURED (M92 S4, `sd(draws)/median(jackknife se)` across every arm,
three stacks, two noise models): **range 1.22–3.53, overall median ≈ 2.1**.
*Significance:* independently reproduces M57 S7 PR19 (1.29 / 1.90 / 3.09) on a
different configuration. The sector jackknife's anti-conservatism is a property
of the estimator family, not of M57's particular cells, and the standing
instruction to read every jackknife standard error as roughly double is
confirmed.

**P15.** MEASURED (M92 S5, arm G; 24 disjoint ROIs per stack, standard errors
from across-ROI repetition, not the jackknife): the near-selector gate (0.99)
produces a sharper merge than the shipped gate (0.50) by **0.61753 px**
(`112MSDCF`, SE 0.02190, 28.19 sigma, 24 of 24 ROIs), **0.31755 px**
(`wrapped-text-1`, SE 0.03340, 9.51 sigma, 23 of 24) and **0.39077 px**
(`109MSDCF`, SE 0.08745, 4.47 sigma, 19 of 22) — **66 of 70 ROI readings across
three ISOs and frame counts of 22, 62 and 130**. Against the real dark-frame
single-ROI null the effect is 6.54× and 3.57× on the admissible stacks.
*Significance:* strengthens M57 §9 / PR11 with empirical rather than jackknife
errors, on a third stack, at a single ROI, and independently of every contested
number in M92. `112MSDCF`'s 0.618 px falls inside PR11's published 0.496–0.740
px range. It is a standing tension with the project's thesis that averaging
beats selection, and it is the most direct available answer to the owner's
complaint that the output looks soft.

**P16.** MEASURED (M92 S3, real dark frames at three ISOs): the global robust sd
of `(d_k − d_l)/sqrt(2)` on the green quad is **0.5242 DN** at ISO 100
(`118MSDCF`), **1.0484 DN** at ISO 200 (`123MSDCF`) and **1.0484 DN** at ISO 500
(`125MSDCF`), against plain standard deviations of 0.7738, 1.3073 and 1.0958 DN.
*Significance:* the robust/plain gap is hot pixels, and it is largest at ISO 200
and smallest at ISO 500 — a plain standard deviation of a dark difference is set
by hot pixels rather than by the temporal pattern, by a factor up to 1.25×.
Cross-ROI correlation is **largest** on the quietest sensor (`rbar = +0.455` at
ISO 100 against +0.206 at ISO 500), because the coupling is a fixed fraction of
a term that shrinks with ISO while the independent term shrinks faster.
