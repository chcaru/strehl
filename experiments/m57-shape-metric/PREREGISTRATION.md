# M57 — pre-registration: a detail metric that escapes single-frequency blindness

**Committed with `src/` empty.** Every prediction and every kill condition below
was written before the first line of measurement code existed. Question 164 is
the target. Facts 617/708, 641/702, 644, 695, 701–708 are folded and are treated
as known; nothing here re-measures them except where they are used as a control.

---

## 0. Rejected on sight, with the reason

Rejecting without running is only legitimate where a **proof** forecloses the
family. Fact 617 is such a proof, and fact 708 widens it.

| Family | Why rejected without running |
| --- | --- |
| Ring FRC / FSC at `f_sig`; any `C/(C+U)`; spectral SNR `C/U`; coherence; NCC; SSIM-family | **Fact 617.** A linear post-filter scales `C` and `U` by the same `\|H\|²`, so a normalised correlation cannot move. Measured 0.0001. |
| Oracle FSC against ground truth at one frequency | **Fact 708.** +0.00003. Ground truth does not rescue single-frequency blindness. |
| Phase-only / phase-congruency at one ring | Reduces to a normalised correlation at one frequency. Fact 617. |
| `hp_sd`, `mean_grad`, Tenengrad, Laplacian energy, `ringpow`, `p_ratio`, `sigpow` **as a candidate** | Degree ≥ 1 in photometric gain with no normalisation (facts 701/704), and each is an absolute-power statistic that cannot tell lost noise from lost signal (M46 §6.2: separation 0.233–0.587). `sigpow` is carried below **only as the incumbent control**, never as a candidate. |
| Slanted-edge / knife-edge MTF | No edge target exists in a macro focus stack, and fabricating one is ground truth. |
| Any statistic requiring the true latent | Requirement 6. |

**Note on what is NOT rejected.** A ratio of cross-powers **at two different
frequencies** is not a normalised correlation at one frequency: a post-filter
`H` multiplies the numerator by `|H(f₂)|²` and the denominator by `|H(f₁)|²`,
which differ. Fact 617's proof does not reach it. That is the whole opening.

---

## 1. Candidates to be measured

All are computed from **two half-merges** of one stack, split by parity of the
depth-sorted frame index (facts 641/702). Write `C_i(f)` for the mean per-mode
real cross-power of ring `f` of configuration `i`'s half-merge pair — i.e.
exactly canonical `sigpow` evaluated at an arbitrary ring rather than only at
`f_sig`.

| id | statistic | form |
| --- | --- | --- |
| **K0** | `sigpow` (incumbent, control only) | `C(f_sig)` |
| **K1** | **`dsig`** — equivalent-blur difference | WLS slope of `log[C₂(f)/C₁(f)]` on `−4π²f²` over a ring band; report `sign(b)·√\|b\|` in **px** |
| **K2** | `rmtf2` — two-ring relative MTF | `[C₂(f_hi)/C₁(f_hi)] / [C₂(f_lo)/C₁(f_lo)]` |
| **K3** | `ccent` — common-power centroid | `√(Σ f²C(f) / Σ C(f))` over the band; an **absolute** shape statistic of one pair |
| **K4** | `dsig_ped` | K1 with a measured white common-mode pedestal subtracted from `C_i(f)` |

**Predicted structural properties (DERIVED, to be confirmed or refuted):**

* K1/K2 are **degree 0** in photometric gain, for a scaling of either input of
  either pair, because a gain is a constant multiplier on `C_i(f)` at every `f`
  and is absorbed by the fitted intercept (K1) or cancels in the ratio of
  ratios (K2). This is the one requirement that can be met **exactly**.
* K1/K2 are blind to independent noise in expectation, because `C` is a
  cross-power of two images whose noise is independent.
* K1 is **monotone in Gaussian blur over the whole range by construction**:
  `log[C₂/C₁] = −4π²σ²f²` is exactly linear in `f²` with slope `σ²`.
* K3 is degree 0 in gain (a constant multiplier cancels between numerator and
  denominator) but is **not** blind to a common-mode pedestal.

---

## 2. Kill conditions — written before any run

Each is a condition that, if met, kills the candidate. I commit to reporting
every one of these outcomes including on the candidate I expect to win (K1).

* **PR1 — MONOTONICITY (the one that killed `sigpow`).**
  On the fact-703 ladder (matched `hp_sd`, PM_M adversary, true MTF
  0.9113 / 0.6870 / 0.2231 / 0.0068), the candidate must have the **same sign at
  all four widths** and `|value|` **non-decreasing** in blur width.
  **KILL if the sign inverts at any width**, or if `|value|` is non-monotone by
  more than 3 standard errors.
  *Falsifier of my own objection:* if `sigpow` passes this too, the ladder is not
  discriminating and the result is void.

* **PR2 — PHOTOMETRIC GAIN.**
  Measured homogeneity exponent `d log|m| / d log λ` for (a) both inputs scaled,
  (b) **one** input scaled (fact 701's real case, `P_a/P_b` = 1.30).
  **KILL if a one-sided gain of 11.7% (fact 704's real merge-configuration
  spread) moves the candidate by more than its own decision threshold.**

* **PR3 — SEPARATION AT MATCHED COST, WITH ITS NULL (rule 39).**
  At matched `hp_sd`, report `d_blur ± se` and `d_smooth ± se` separately.
  **Report no `S`** — fact 695 / M55's discipline. **KILL if `|d_blur|` is not
  ≥ 5 standard errors from zero, or if `|d_smooth|` is ≥ 3 se from zero in the
  direction that mimics detail.** Additionally sweep the repetition count 1→32
  and report whether either term drifts (the fact-695 test).

* **PR4 — SPLIT LEVERAGE (fact 705, the structural killer).**
  With the split held **common to both configurations**, measure the candidate's
  reading for split ∈ {parity, block-2, block-4, block-8, random, contiguous}.
  **KILL if the spread across the five interleaving splits exceeds the reading
  produced by a planted 0.05 px blur** — that is fact 705's 50× leverage
  restated as a pass/fail. Contiguous is reported separately since the contract
  forbids it.

* **PR5 — LATENT DRIFT (rule 34 / discipline 340).**
  Build a plant in which the two half-merges deliver **different latents** —
  `m46lib`'s plants cannot, which is why they could not express this failure.
  Apply **no blur**. **KILL if the candidate reports a blur difference larger
  than the planted-0.05 px signal when there is none.**

* **PR6 — REAL DATA, PLANTED BLUR, WITH A NULL.**
  On ≥ 3 real stacks × 2 ROIs (one **flat**, run first — rule 9), plant a
  Gaussian blur of known width on one configuration and require the recovered
  width to be within ±30% of truth. The **null** is a four-way re-pairing:
  identical merge rule, all frames, only the pairing changes, so truth is
  exactly 0. **KILL if the null is not within 2 se of zero, or if the recovered
  width on the flat ROI has the wrong sign.**

* **PR7 — PLANTED WRONG ANSWER (rule 39).**
  Plant σ = 0.10 px and test the hypothesis "σ = 0". **The test must reject it.**
  Also test the hypothesis "σ = 0.20 px" and require **that** to be rejected too.
  A test that accepts both has no power and the candidate is dead.

* **PR8 — REAL DEFOCUS, NOT A GAUSSIAN.**
  Repeat PR1's monotonicity on a **pillbox** OTF (`2J₁(x)/x`, with contrast
  reversals). **KILL if the sign inverts across a zero crossing.** M46 §9 item 5
  lists this as unmeasured; it is measured here.

* **PR9 — FLAT-ROI CONTROL FIRST (rule 9).** Every real-data cell is computed on
  a flat ROI **before** the detail ROI, and the flat number is reported whether
  or not it is convenient.

* **PR10 — THE PEDESTAL FLOOR.** DERIVED prediction: with a white common-mode
  pedestal `F`, K1 **saturates** rather than inverting, and the saturation floor
  is set by `F/S(f)`. Measure the blur width at which K1's reading departs from
  truth by 2×. **KILL if the departure occurs below 0.5 px equivalent**, since
  the operational range of interest is 0.02–0.5 px.

* **PR11 — TUNING HYGIENE.** The band `[f_lo, f_hi]`, `n`, `nbin` and the ring
  geometry are fixed **once**, from `f_sig = 0.2762` (fact 27) and the ring grid
  of A.1.7, before any real stack is scored, and are not re-chosen per stack or
  per ROI. **KILL the result, not the candidate, if any parameter is moved
  after seeing a score.**

---

## 3. What I expect (so that being wrong is visible)

1. K1 passes PR1, PR2 and PR3, and PR2 **exactly** rather than approximately.
2. K1 passes PR4 with a large margin, because the split is common to both
   configurations and cancels in the ratio — this is the specific structural
   reason to expect an improvement over `sigpow`, and if it fails, the family
   is dead for the same reason `sigpow` is.
3. K3 fails PR2 or PR10 — an absolute shape statistic has no reference to
   cancel the scene's own spectrum against.
4. K0 fails PR1 and PR2 (facts 703, 704 restated as a control; if it passes,
   my harness is broken).
5. **I expect PR5 to be the hardest**, and I do not know the outcome.

## 4. Reporting contract

* Every claim labelled MEASURED / DERIVED / ARGUED.
* Every separation or ratio reported with its null and that null's standard
  error (rule 39).
* No `S`-style score whose denominator may be consistent with zero (fact 695).
* Every script has an `if __name__ == "__main__":` guard.
* `crates/**`, `docs/research/SYNTHESIS.md`, `AGENTS.md`,
  `docs/research/OWNER-QUESTIONS.md`, `D:\personal\macro` and
  `D:\macro-dark-frames` are read-only for this milestone.
* If no candidate survives, that is the finding and it is reported as such.
