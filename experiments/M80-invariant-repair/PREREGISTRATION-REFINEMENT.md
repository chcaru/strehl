# M80 refinement — pre-registration of target detectability

**State at registration.** M80's original repair and measurements are published
through commit `0c6b0d2`. M70 §22 was then read at its source. No M80
detectability code, contrast-ladder result, or new real-stack result exists when
this document is committed. The old flat and detail measurements are already
known and are not blind; the new threshold formula, calibration simulation,
contrast ladder, and consequences below are fixed before they are run.

## M80 refinement §1 — Decision and observable

**ARGUED.** M70's numerical null does not transfer: M70 estimates a spectral
frame count, while M80 measures spatial gradient power. Its identifiability
argument does transfer. If the selector's resolved detail power is
indistinguishable from zero, "detail retained / detail present" has no
identifiable denominator. M80 will therefore keep `STRUCTURE` as a numerical
null diagnostic but report `RETENTION = N/A` and verdict `NO TARGET` whenever
the full-stack selector has no detectable resolved detail.

**ARGUED.** Detectability is determined once, from the full-stack selector, not
again from each candidate. If the selector has measurable detail and a
candidate destroys it, the candidate must return a small numerical retention
and `COLLAPSE`; candidate-side non-detection must not excuse the loss.

## M80 refinement §2 — Noise-derived detection threshold

**DERIVED.** For a vector of zero-mean Gaussian gradient observations
\(g\sim N(0,C)\), its summed energy \(S=g^\mathsf{T}g\) has

\[
E[S]=\operatorname{tr}(C)=V,\qquad
\operatorname{Var}(S)=2\operatorname{tr}(C^2)=2T.
\]

For the right/down finite-difference graph used by M80, \(V\) and \(T\) are
computed directly from the per-pixel calibrated noise variances. No fitted
contrast or `STRUCTURE` cutoff enters.

**DERIVED.** For one cross-fit pair, let \(D\) be a detail half, \(F\) the
opposite flat half, and \(k^2=S_F/V_F\). Under the null
\(C_{\mathrm{true}}=k^2C_{\mathrm{model}}\), the variance of
\(S_D-k^2V_D\), including finite-control uncertainty, is

\[
2k^4\left(T_D + V_D^2 T_F/V_F^2\right).
\]

The two disjoint cross-fit pairs add in variance. Dividing the resulting
standard deviation by the total gradient-anchor count gives the standard error
of M80's signed mean power \(Q\).

**ARGUED.** No noise model can determine the acceptable false-answer
probability; that is a loss decision. M80 fixes the only policy input now,
before measurement: a one-sided false-answer rate
\(\alpha=0.01\). Its standard-normal quantile is
\(z_{0.99}=2.326347874\). The selector target is `MEASURABLE` only when

\[
Q_0 > z_{0.99}\operatorname{SE}(Q_0).
\]

Thus no DN, contrast, `STRUCTURE`, frame-count, or ROI-size threshold is chosen.
Those thresholds are derived per invocation from the calibrated noise map, the
measured selection inflation, the gradient graph, and the ROI sample count.

**ARGUED.** The Gaussian quadratic-form variance is exact for the calibrated
independent-pixel noise model before selection. The flat control measures
selection's mean inflation but not every correlation it induces. The
calibration simulation below is therefore a required falsification test, not a
decorative unit test.

## M80 refinement §3 — Acceptance bars fixed before measurement

**ARGUED — D1, real controls.** On both M77 arm-B2 flat ROIs:

* selector target status must be `NOT-MEASURABLE`;
* every gate's `RETENTION` must be `N/A` with verdict `NO TARGET`; and
* selector, gate-zero, and gate-four `STRUCTURE` must remain in
  `[0.90, 1.10]`, proving that the repaired nuisance model still reads the null.

On both M77 arm-B1 detail ROIs:

* selector target status must be `MEASURABLE`;
* gate-zero and gate-four retention must be numerical; and
* gate-zero and gate-four `STRUCTURE` must remain at least `3.0`.

Both directions must pass on both stacks.

**ARGUED — D2, false-answer calibration.** For each synthetic stack depth
`N = 22`, `N = 130`, and `N = 299`, run 1,000 independent zero-signal
selector/control pairs on 64×64 ROIs under the registered Gaussian noise model.
At nominal
\(\alpha=0.01\), the exact binomial 99th-percentile acceptance count is 18
false answers out of 1,000
(\(P_{\mathrm{Binom}(1000,0.01)}[K\le18]=0.993095\)). Each depth must produce
at most 18 `MEASURABLE` answers. The three depths are judged separately.

**ARGUED — D3, decreasing-contrast transition.** Use the existing deterministic
512×512 three-pixel checkerboard, but set its signed amplitude in DN to
`0, 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 200`. Use the same noise realisation at
every contrast within a depth, at synthetic selection inflation for
`N = 22`, `N = 130`, and `N = 299`.

For each depth:

* amplitude zero must be `NOT-MEASURABLE`;
* amplitude 200 must be `MEASURABLE`;
* once the ladder becomes measurable, no higher contrast may return to
  `NOT-MEASURABLE`; and
* let \(G_1\) be noiseless checker gradient power at amplitude one and
  \(A_*=\sqrt{z_{0.99}\operatorname{SE}(Q_0)/G_1}\). The first measurable
  ladder amplitude must be within one factor-of-two rung of \(A_*\), i.e.
  its ratio to \(A_*\) must lie in `[0.5, 2.0]`.

The full ladder, \(A_*\), and the observed transition will be printed. A
statistic that never answers fails; a statistic that answers at zero fails.

**ARGUED — D4, retained positive control.** At amplitude 200, the unchanged
candidate must retain `[0.95, 1.05]` and the registered three-by-three blur must
retain at most `0.80`, for all three depths. Both values must be numerical.

**ARGUED — D5, source mutation.** The Python byte-string control will bypass
the cross-fitted selection scale exactly as before, verify its planted bytes by
read-back, and run the refined noise-null test. The planted run must exit
non-zero with a diagnostic naming either a false measurable target or the
noise-null structure failure. Exact source restoration must then make the
identical command exit zero.

**ARGUED — D6, observer non-perturbation.** The no-ROI and with-ROI gate-four
outputs must remain byte-identical under SHA-256.

## M80 refinement §4 — Consequence for the collapse floor

**ARGUED.** `DETAIL_COLLAPSE_FLOOR = 0.90` is evaluated only when the selector
target is measurable. Its numerical value remains the separately unclaimed
product tolerance from M80's original report. `NO TARGET` is not a pass and
must never flow through `detail_verdict`.
