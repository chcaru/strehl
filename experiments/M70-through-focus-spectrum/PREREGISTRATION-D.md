# M70 PREREGISTRATION-D — the window floor of the spectral `n_eff` estimator

**Written and committed BEFORE `s27` was run.** Fourth pre-registration of this
milestone; same form as A/B/C.

## Why

M77 fact 40 measures admission saturating locally (a flat ROI freezes at gate 96
or gate 40) long before it saturates frame-wide. The orchestrator asks whether
M70's spectral `n_eff` — a per-patch quantity measured on **256 GQ-sample
windows (511×511 sensor px)** — has a spatially-local form small enough to serve
as a per-pixel or per-tile calibration target, and asks for **the window size
below which I would not trust it**, explicitly preferring that limit to an
optimistic answer.

`s12` already halved the window once (VOID condition 4) and found stack-median
`n_eff` ratios 0.839–1.073. **`s12` is not an answer to this question**, for a
reason I am recording before running anything: at a smaller patch size `s12`
measured **different image content**, because the patch grid rescales. Window
and content moved together, so `s12` cannot attribute its 0.839.

## Instrument

**Nested crops from one centre.** For window `P ∈ {256, 128, 64, 32, 16}` GQ
samples, crop concentrically about the **same** patch centres used by `s04`, with
Welch `tile = P/2` throughout, preserving the shipped 3×3 tiling. Content is then
held fixed and only the window changes.

**Bins per band is the governing quantity.** A band `[lo, hi)` at tile `t` holds
about `π(hi² − lo²)·t²` independent 2-D frequency bins. For `b3_mid`
(0.100–0.150) that is ≈ 25 bins at t=128, 6 at t=64, 1.6 at t=32, 0.4 at t=16.

**Mechanism, stated without a direction.** Two effects act at once and I am not
predicting which dominates. (i) Fewer bins make each per-frame band power noisier;
`n_eff = Σ_k S_k / max_k S_k` takes an **argmax over K noisy values** in its
denominator, and an argmax over noise moves with estimator variance. (ii) Fewer
bins also widen spectral leakage between adjacent bands, which moves measured
band power in its own direction. **The net sign is what the measurement is for.**

## Arms

1. **PLANT with a real latent.** The sharpest real frame's patch is the latent —
   **real texture, not synthesised** (facts 61–64; M63's failure mode). Blur it
   with a known Gaussian ladder `σ_k`, giving known amplitudes. Add
   photon+read noise from the calibrated model. Ground truth `n_eff_true(P)` is
   computed from the **noiseless** blurred stack **at the same window `P`**, so
   the window-discretisation term and the noise term are separated rather than
   conflated.
2. **NULL.** Pure modelled noise, no latent, every window. The unclipped
   statistic reads −0.16..+0.08 at P=256 (P5).
3. **REAL nested.** `wrapped-text-1` and `wrapped-text-2` — M77's two stacks —
   on nested crops.

## Criteria, fixed now

* **W1 (plant fidelity).** `|n_eff_hat(P)/n_eff_true(P) − 1| ≤ 0.10`.
* **W2 (null safety).** `|n_eff_null(P)| ≤ 0.25`.
* **W3 (real nested stability).** `n_eff(P)/n_eff(256) ∈ [0.90, 1.10]` on both
  real stacks.
* **Recommended floor** = the **smallest** `P` meeting W1, W2 and W3. If no `P`
  below 256 meets all three, the honest answer is that the estimator has **no
  usable local form at tile scale**, and I report that.

## VOID conditions

* **V15.** If the plant's `n_eff_true(256)` is not within 10% of the measured
  real `n_eff` for the stack its latent came from, the plant is unrepresentative
  and W1 is void.
* **V16.** If the **noiseless** window term alone moves `n_eff` by more than the
  noise term, the limit is spectral discretisation and not estimator noise; I
  must say which, and W1's ratio must be reported against the noiseless value at
  the same window rather than against the 256 value.
* **V17.** If `b3_mid` holds fewer than 1.0 bins at some `P`, every band-average
  at that `P` is undefined rather than merely noisy, and that `P` is reported as
  **UNDEFINED**, not as a failure of fidelity.

## What this cannot decide

The nested design holds content fixed, so it measures the **estimator's** window
dependence and **not** whether small windows land on informative texture. A
per-tile deployment picks its own tiles and would meet both problems. That is
outside this arm and I will say so.
