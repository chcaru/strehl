# M11 — focus-measure bake-off: pre-registration

Status: **registered before any measurement was run.** Committed on its own, ahead of
the harness output, so `git log` carries the ordering. Follows M9's precedent
(`experiments/m9-support/PREREGISTRATION.md`, commit `f29e4db`).

Milestone: close SYNTHESIS **risk 2** ("every focus-measure noise analysis in the
literature is synthetic — build the benchmark before choosing the operator") and run
SYNTHESIS §8 **experiment 3**.

The question: **`crates/strehl-core/src/focus.rs` ships a ring difference with
`INNER_RADIUS: 1`, `OUTER_RADIUS: 3`, chosen arbitrarily and never justified against
alternatives. What is the measured trade-off between focus selectivity and argmax's
noise excess across a wide operator set, and what should the default be?**

---

## 0. What I had already seen before registering

Disclosed because it constrains what counts as a novel result here, and because a
pre-registration that hides its priors is theatre.

I read, before writing a line of this design:

- `docs/research/SYNTHESIS.md` in full, including facts 1–36 and risk 2.
- `experiments/m9-support/` in full: `PREREGISTRATION.md`, `README.md`,
  `src/measures.rs`, `src/tile.rs`, `src/main.rs`, and its committed data —
  `data/sensitivity-109MSDCF.csv` (measured phi per operator),
  `data/sweep-109MSDCF-coupled.csv` (flat-ROI noise ratio per operator per width),
  `data/rois-109MSDCF.txt`, `data/analysis-109MSDCF-coupled.txt`.
- `crates/strehl-core/src/focus.rs`, `noise.rs`, `plane.rs`, `stack.rs`.

So I already know, going in:

- **phi predicts noise excess** (M9 fact 35): rho = +0.918 / +0.894 across two stacks,
  p < 0.0001; support radius does not (rho = −0.170 / −0.243, n.s.).
- **A 3x3 Sobel measured 0.9952x** — no noise excess at all.
- **`ring(1,3)` measured 1.2527x** unregularised, 1.0737x at width 17, and **1.3625x at
  width 3** — regularising can harm.
- Roughly where each M9 operator sits on the phi axis.

What I do **not** know, and what this milestone is actually for: **none of those
operators has ever been scored for focus selectivity in this project.** M9 measured one
axis of a two-axis problem. Every selectivity number in M11 is new. The registered
hypotheses below are therefore about selectivity and about the *joint* outcome, not
about the noise axis, which is largely a reproduction.

**H1 (registered, mine, falsifiable):** a zero-centre-tap operator (Tenengrad,
structure tensor, symmetric Brenner) will be *both* noise-free (N <= 1.02) and within
5% of the best measured selectivity, and will therefore become the recommended default.

**H2 (registered, mine, falsifiable):** among ring differences, selectivity will
increase with `inner` (bigger centre tap, more of the pixel's own signal) and the
noise/selectivity trade will be monotone, so there will be *no* interior optimum in
`inner` and the ring family will be dominated by some non-ring operator.

I register both because I expect to publish whichever way they fall, including "both
wrong".

---

## 1. Design

### 1.1 Operators (37, fixed now)

Selected to span the **centre-tap axis** (phi ~ 0 to phi = 1) and the **support axis**
(1 px to 12 px) independently, so neither is confounded with the other. Implemented in
`src/measures.rs`, inside this experiment crate — `crates/` is not touched.

| Family | Members | Why it is in the set |
| --- | --- | --- |
| Ring difference | `ring-0-1`, `ring-0-3`, `ring-1-2`, `ring-1-3`, `ring-1-5`, `ring-2-4`, `ring-2-6`, `ring-3-8`, `ring-4-12` | The incumbent's own grid. Answers the `INNER_RADIUS`/`OUTER_RADIUS` question on its own terms; analytically phi = 1/(2(2·inner+1)²) with `outer` cancelling. |
| Sum-modified Laplacian | `sml-w0`, `sml-w2`, `sml-w5` | The textbook high-phi discriminator. |
| Dilated SML | `dsml-s1`, `dsml-s3`, `dsml-s6` | M9's decoupling device: phi ~ 0.44 held roughly fixed while support sweeps 1→12. |
| Tenengrad / Sobel | `tenengrad-w0`, `tenengrad-w2`, `tenengrad-w5`, `tenengrad-sq-w2` | **Zero centre tap.** The candidate that would make argmax's noise excess structurally zero. |
| Brenner | `brenner-fwd-s2-w2`, `brenner-sym-s1-w2`, `brenner-sym-s2-w2`, `brenner-sym-s2-w5` | Contains both signs of the centre-tap question inside one family: forward difference touches the centre, central difference does not. |
| Structure tensor | `stensor-w2`, `stensor-w5` | Zero centre tap but orientation-selective — a genuinely different statistic from gradient energy. |
| Variance | `varlap-w2`, `varlap-w5`, `localvar-w2` | Variance-of-Laplacian and local variance, both standard, both quadratic. |
| Band energy | `dct8-hi`, `msband-lo`, `msband-hi` | DCT high-band (Parseval form) and multi-scale band energy — the transform-domain family. |
| Normalisation variants | `ring-1-3-nonorm`, `tenengrad-w2-nonorm`, `tenengrad-w2-boxnorm` | Operator held fixed, only the divisor changes, so movement is attributable to normalisation alone. **Registered prediction: `tenengrad-w2-nonorm` has phi exactly 0; the pointwise-normalised `tenengrad-w2` does not, because dividing by sigma(L(p)) puts a centre tap on an operator that had none.** |
| Controls | `ctl-const`, `ctl-random`, `ctl-luma` | See §5. |

Cost is measured and **reported**, but registered as a **tie-break only**: a fused GPU
focus+merge over 22 frames runs in 4.117 ms and is bandwidth-bound, so focus arithmetic
is not the bottleneck.

### 1.2 Regulariser widths

`{1, 9, 17}` plane px only. M9 fact 36 already established the shape of the width
curve (monotone-decreasing then flat, **no interior optimum**), so re-sweeping it finely
would only rediscover a boundary. M11 instead **pairs every width with a selectivity
number** so the objective is two-sided.

### 1.3 Data

Read-only. `C:\dev\macro\test\109MSDCF` (22 frames, M2's and M9's reference stack, so
numbers stay comparable) and `C:\dev\macro\test\119MSDCF` (33 frames, the independent
replication). Rule 7 is respected by construction: every statistic is computed inside an
explicit ROI tile lifted from the **CFA-quad plane** (3516x2344), never over the
zero-padded 7168x5120 decode.

ROI selection is by **scene structure only** (`rois` mode: flattest and most-detailed
tiles by local gradient), never by outcome, and is run and committed before any operator
is scored.

---

## 2. Pre-registered statistics

### 2.1 Noise excess `N` — the cost axis

Exactly M2's and M9's convention, so M11's numbers are comparable to theirs:

> `N = sd_spatial(argmax-merged green over a flat ROI) / sd_spatial(the middle single
> frame's green over the same ROI)`.

Both terms are **spatial** standard deviations of the same quantity over the same
pixels. **Rule 10 is satisfied by construction: no temporal sigma appears anywhere in
M11.** `N = 1` means "as noisy as one frame"; the ideal for 22 frames is 1/sqrt(22) =
0.213 and the measured mean is 0.534x.

Recorded alongside: `distinct_winners`, `speckle`, and `grad_stacked` / `grad_single`
(mean gradient magnitude, the rule-9 amplification check).

### 2.2 Planted selectivity `S` — the benefit axis, primary

The hard half, so it gets ground truth. One real frame is blurred by a symmetric
Gaussian defocus ladder

> `sigma_k = sigma0 + alpha * |k - w_true|`, with `sigma0 = 0.8 px`, `alpha = 0.35 px/frame`,

and fresh calibrated sensor noise is drawn per frame. `w_true` is **constant over the
tile** (fronto-parallel), so the blur is spatially uniform and exactly correct — there
are no seams and **no resampling anywhere**, which is what SYNTHESIS §5 item 11 warns
about.

> `S = fraction of ROI pixels whose argmax winner equals w_true`.
> `S1 = fraction within +/-1 frame`. `MAE = mean |winner - w_true|` in frames.

`sigma0 > 0` is deliberate. Blurring a real frame also blurs its inherited noise, so a
ladder starting at sigma = 0 would make the in-focus frame the noisiest and bias every
operator toward the wings. The **realised** per-frame noise is measured and disclosed
(`--frames-out`, column `hp_sd`, a high-passed spatial sd per frame); if the spread
between the in-focus frame and the far wings exceeds **10%**, the planted result is
reported as contaminated and demoted to a corroborator.

### 2.3 Real-data stability `kappa` — the benefit axis, corroborator

No ground truth exists on a real stack, so selectivity is probed by **reproducibility**:
build two independent realisations of the same stack and compare their winner maps.

> `kappa = Cohen's kappa between the two winner maps` (0 = chance, 1 = identical).

Cohen's kappa rather than raw agreement, so an operator that collapses onto one frame
cannot look stable for free. Two independent realisations:

- `inject` — the same real frames plus two independent calibrated noise draws at scale
  `beta`. Controlled, but the shared underlying frame noise makes it an **optimistic**
  bound.
- `--planes` — G1 and G2, the two physical green photosites, as two genuinely
  independent measurements of the same scene. No synthetic noise at all, but the two
  lattices are offset by half a plane pixel diagonally, so structure contributes to
  disagreement and it is a **pessimistic** bound.

Both are run and reported side by side; the truth is bracketed, not asserted.

Also recorded: `prominence` = median over pixels of (peak − median)/sigma_response and
`margin` = (best − second best)/sigma_response, with sigma_response estimated from the
paired difference. This is literally SYNTHESIS §8 experiment 3's "winner-margin versus
sigma".

### 2.4 Cost

`ms_per_frame_mpx`, single-threaded, best of `reps`. Reported; weighted lightly.

---

## 3. The full outcome grid

SYNTHESIS §5 item 14 exists because M9's registered rule did not cover the outcome that
actually occurred and had to fall back on a post-hoc statistic. **A Pareto front very
plausibly has no single winner, so that branch is registered explicitly and first.**

Let `A = { operators with N <= 1.02 }` (the "noise-free" set — 1.02 is two percentage
points, comfortably above the measured ROI-to-ROI spread but far below the incumbent's
1.25) and `S_max = max over all operators of S`.

| # | Outcome | Registered response |
| --- | --- | --- |
| **O1** | `A` is non-empty and contains an operator with `S >= 0.95 * S_max` | **Recommend the highest-`S` member of `A`.** H1 confirmed. Zero-centre-tap becomes the default and argmax's noise excess is structurally removed. |
| **O2** | `A` is non-empty but its best `S` is in `[0.80, 0.95) * S_max` | **No single winner.** Report the front, rank by `J` (§6), recommend the argmin `J`, and state the selectivity price of the noise-free choice in measured units. |
| **O3** | `A` is non-empty but its best `S` is `< 0.80 * S_max` | Zero-centre-tap is **not** viable as a drop-in default. Recommend the argmin `J`, and record that the noise excess must be attacked by estimation (the project thesis) rather than by operator choice. |
| **O4** | `A` is empty | Report it as a **negative result about the whole operator class**: no operator in a 37-wide, phi-spanning set is noise-free on real data. Recommend the argmin `J`. |
| **O5** | Two or more operators are within the measured ROI-to-ROI spread of each other on **both** axes | **Declare a tie explicitly.** Prefer, in order: (i) fewer parameters, (ii) lower cost, (iii) the incumbent. Do not manufacture a winner from noise. |
| **O6** | The incumbent `ring(1,3)` is itself the argmin `J` | **Recommend no change**, and say that the arbitrary choice happened to be defensible. |
| **O7** | `S` and the real-data corroborators disagree (Spearman rho between `S` and `kappa` across operators `< 0.5`) | **Downgrade the whole ruling to provisional**, publish both rankings, and register the follow-up. Do not pick the ranking that suits the thesis. |
| **O8** | Controls fail (§5) | **No recommendation at all.** Publish the control failure as the result. |

O1 is the interesting outcome; O8 is the one that costs the most to admit; both are
registered at equal weight.

---

## 4. Severity thresholds, fixed now

| Quantity | Threshold | Meaning |
| --- | --- | --- |
| `N <= 1.02` | membership in `A` | "noise-free" |
| `N >= 1.10` | material noise excess | the operator imports noise |
| `S >= 0.95 * S_max` | "as selective as the best" | |
| `S < 0.80 * S_max` | materially less selective | |
| P0 positive control | `S >= 0.90` | else the selectivity metric is invalid (O8) |
| P2 null control | `S <= 2/N_frames` | else the metric is scoring something that is not focus (O8) |
| flat-ROI planted control | `S` collapses to within `3x` of chance | rule 9 pairing |
| `xcheck` reproduction | within `1%` of 1.2527x and 1.0737x | else the code path is not M2's (O8) |
| realised per-frame noise spread | `<= 10%` | else the planted ladder is contaminated |
| ROI-to-ROI spread | measured, not assumed | sets the tie width for O5 |

---

## 5. Controls

**Measure-level** (run in every mode, reported *before* any treatment):

- `ctl-const` — response identically 0, so every frame ties and the shipped tie-break
  elects frame 0. `N` is then `sd(frame 0)/sd(frame middle)`: the **instrument floor**.
  Any operator scoring below it is measuring the instrument, not itself.
- `ctl-random` — winner from an index hash: uniform random selection with **zero noise
  coupling**. This is M2's placebo (0.981x) generalised. Registered prediction: `N ~ 1`
  on the noise axis and `S ~ chance` on the selectivity axis. Note it is *stable* across
  noise draws, so it is deliberately **not** the stability null.
- `ctl-luma` — response = L, so phi = 1 exactly and focus content is ~0. The noise-axis
  **positive control** (must show the largest `N`) and the stability null.

**Experiment-level:**

- **P0, positive control** — planted ladder on a *synthetic noiseless* texture. `S` must
  be ~1.0 for a working operator. Proves the selectivity metric can recover a planted,
  known focus surface (rule 11) before any real-data number is trusted.
- **P1** — planted ladder on a real detail ROI with calibrated noise. The operating
  point.
- **P2, null** — `--null`: `alpha = 0`, so every frame has identical blur and **no focus
  is planted**. `S` must sit at chance `1/N_frames`. An operator that beats chance here
  is scoring noise.
- **Rule 9 pairing** — every planted run on a detail ROI is paired with the same run on
  a **flat** ROI, where `S` must collapse to chance. A sharpening pass raises every
  sharpness metric while destroying the image; without the flat control, selectivity
  cannot be told from amplification. `grad_stacked`/`grad_single` are recorded for the
  same reason.
- **Reproduction first** (SYNTHESIS §5 item 15) — `xcheck` reproduces M2's published
  1.253x and 1.075x through *this* code path before this code path is believed about
  anything else.
- **Replication** — every headline number is computed on two independent stacks
  (109MSDCF, 22 frames; 119MSDCF, 33 frames) and on multiple ROIs.

---

## 6. Decision rule

Registered scalar, used **only** in outcomes O2/O3/O4/O6:

> `J = (1 − S / S_max) + lambda * max(0, N − 1)`, with **`lambda = 1.0`**.

`lambda = 1` says: one percentage point of lost selectivity is worth one percentage
point of added noise. It is a value judgement, so it is registered in advance and its
**sensitivity is reported over `lambda` in [0.25, 4]**; if the argmin changes inside that
range, the ruling is reported as lambda-dependent and the range that supports each choice
is given.

`max(0, N − 1)` and not `N` because going *below* single-frame noise is a bonus, not a
credit to be traded against selectivity — no operator should be able to buy selectivity
points by being averaged.

`S` and `N` for the ranking are taken at **width 1** (unregularised), because the
regulariser is a separate lever that M9 already characterised and because it is what
`focus.rs` ships. Regularised results are reported but do not drive the ruling.

Aggregation across stacks and ROIs: **median across ROIs, then mean across stacks**,
fixed now. Medians because a single unlucky ROI should not swing a ranking.

**Both axes must be measured on the same operator at the same width, or the operator is
excluded from the ranking rather than imputed.**

---

## 7. Deviations policy

Any deviation from this document is listed explicitly in
`docs/research/M11-focus-bakeoff-measured.md` under a "Deviations from
pre-registration" heading, with the reason and the direction it could bias the result.
Adding a *reported* statistic is allowed; changing the *decision rule* after seeing
results is not.

Every claim in the report carries one of **MEASURED / VERIFIED / DERIVED / ARGUED /
UNVERIFIED** (rule 8). Raw CSVs are committed, not just conclusions (rule 12) — the
orchestrator re-verifies against them, and the author does not verify his own work.

---

## 8. Amendments

Made **after** §1–§7 were committed but **before any measurement was run**, all forced by
harness self-test failures — that is, by controls doing their job. The commit ordering is
the evidence: the self-test that produced each finding runs on synthetic data only and
never touches a RAW file. **No decision rule, threshold or outcome branch is changed by
any amendment.**

### A1 — the registered set contained no operator with strictly zero phi

The self-test asserted that `tenengrad-w2-nonorm`, `brenner-sym-s2-w2` and `stensor-w2`
have exactly zero centre sensitivity. All three **failed**: measured 6.4e-3, 9.9e-2 and
3.5e-3 respectively against a required 0.

The reason is structural and was missed at design time. **A window mean re-introduces a
centre tap.** `tenengrad-wN` is the box mean over a `(2N+1)²` window of Sobel energies;
Sobel's own centre coefficient is zero, but the *neighbours'* Sobel energies inside that
window do depend on the centre pixel, so the windowed operator's response at `p` depends
on `L(p)`. The pointwise `sigma(L(p))` divisor does the same thing for the same reason:
it is a function of the centre pixel by construction.

So every "zero-centre-tap" candidate in the registered set was in fact non-zero, and the
milestone's highest-value question — *is a zero-centre-tap operator viable as the
default?* — could not have been answered cleanly by it.

**Amendment:** add two operators, `tenengrad-w0-nonorm` and `brenner-sym-s2-w0-nonorm`,
being the only forms with `window = 0` **and** `Norm::None`. Both now measure exactly
`0.000e0` centre sensitivity in the self-test. Set size 37 → 39. Nothing is removed.

This is the amendment most at risk of looking like fitting the design to a hoped-for
answer, so: it was made before any RAW frame was opened, it *adds* candidates rather than
removing inconvenient ones, and it makes H1 **easier to falsify**, not harder — the new
operators are the crudest in the set and now have to earn their selectivity on the same
scale as everything else.

The re-introduction of a centre tap by windowing and by normalisation is itself now a
**registered prediction to be measured**: `phi(tenengrad-w0-nonorm) = 0 <
phi(tenengrad-w0) < phi(tenengrad-w2-nonorm)`, holding the base operator fixed.

### A2 — the synthetic positive-control texture was not a valid control

The self-test asserted that a noiseless planted stack is recovered by `ring-1-3`. It
failed at 27% of pixels wrong. The cause was the control texture, not the operator: it
was a sum of four sinusoid products, and a bandpass response there is
`sum_j c_j exp(-sigma^2 k_j^2 / 2)` over a handful of components whose signs are
*spatially coherent*, so cancellation puts a zero crossing at an interior `sigma` and
`|response|` stops being monotone in blur. Whole nodal lines voted for the most-defocused
frame.

**Amendment:** `synthetic_texture` is now a deterministic broadband random field —
white Gaussian noise summed over five octaves from 1 px to 8 px with 1/f weighting,
variance-normalised. Component signs are spatially incoherent, there is content at every
scale the operator set can see, and there is no nodal structure.

### A3 — two clarifications the self-test forced, and one added statistic

- **Mirror ties.** The ladder is exactly symmetric about `w_true`, so with
  `noise_scale = 0` the frames at `w_true +/- d` are **bit-identical** and the shipped
  tie-break gives every mirror tie to the lower index. `mean_winner` is therefore not a
  bias diagnostic on a noiseless plant. `acc` is unaffected — it only asks whether
  `w_true` won — and remains the registered statistic. Now asserted as a control.
- **§4's `P0 >= 0.90` threshold is a threshold on the metric, not on every operator at
  every width.** A *pointwise* bandpass response is a noisy estimator of local sharpness
  **even with zero sensor noise**: at one pixel it is a zero-mean random variable whose
  *scale* shrinks with blur, so a single-pixel argmax is only stochastically biased
  toward the sharp frame. Measured on the noiseless broadband control, `ring-1-3` scores
  `acc = 0.723` pointwise and `acc = 1.0000` under a 17-wide box. The control is
  therefore read as: **the metric is valid if the planted surface is recovered at
  `>= 0.90` by some operator/width in the set**, which it is. The per-operator width-1
  numbers remain the registered ranking input. This reading is fixed now, before any
  treatment is run.
- **Added reported statistic:** `--alpha` becomes a swept list, so the planted ladder's
  *steepness* (px of blur per frame of defocus) can be varied. This measures
  depth-discrimination directly — how much defocus an operator needs before it can tell
  frames apart — which the milestone brief asks for and §2.2 did not provide. Reported
  only; the ranking still uses the registered `alpha = 0.35`.
