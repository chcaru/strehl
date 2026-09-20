# Independent matrix-Cauchy result review

MEASURED by the root-run `matrix-cauchy-1` receipts and frozen independent scorer; reviewed without refitting. The fixed recipe fails. `all_fixed_checks_pass=false`: both paired layered core/ridge chroma guards fail. This does not license the proposed stress run or a photographic experiment.

The primary comparison remains the same-known-alpha `visibility-1` result. Flat RGB/chroma RMSE is 5.7492/8.0299 DN, versus reference 5.6720/7.9256 and mean 6.0185/8.3676. It passes both 1.05 guards but does not improve the primary reference. Signed channel biases remain small, [0.121, -0.252, -0.044] DN, and similar to the reference; tails widen slightly. A uniform brightness shift does not explain this result.

| Layered region | Visibility RGB / chroma DN | Matrix-Cauchy RGB / chroma DN |
| --- | ---: | ---: |
| Whole supported region | 150.971 / 67.310 | 106.587 / 97.783 |
| Core | 731.457 / 260.393 | 488.987 / 383.707 |
| Ridge | 312.404 / 120.164 | 213.091 / 178.279 |

The core/ridge chroma increases are approximately 47.36%/48.36%, far beyond the fixed 2% allowance. Re-choosing colour error instead of whole RGB therefore reverses the attractive headline. The original image guards and paired RGB guards pass, but cannot cancel the independently protected colour failures. Compared descriptively with scalar Cauchy, matrix Cauchy reduces core/ridge chroma from 558.194/252.520 to 383.707/178.279 DN. That partial improvement still leaves substantial harm relative to the designated reference.

Glint recovery is [1.00013, 1.00353, 1.00308]; ridge recovery is [1.01372, 1.00306, 1.01675]. The truth-capped component guards pass. Every component is slightly above truth, so these are overshoots, not evidence of extra recovered detail. A projection onto a true component also leaves other colour errors unpenalized; the RMSE guards expose those errors here.

All available held-out residual guards pass. The independently defined bright stratum has 41 samples and normalized RMS 1.19514, versus visibility's 2.14781. Global held-out RMS is 1.02705/1.06181. Scalar Cauchy's bright RMS was slightly lower, 1.15837, despite its worse delivered colour. Neither the aggregate nor bright forward residual is a sufficient delivered-image quality test. There are no censored held-out samples in these comparisons.

The receipts retain exact original starting sheets, fixed alpha, unchanged source bindings, and training reads only at [0,1,3,4,5,7,8]. The scorer also verifies initial image equality against the fixed-alpha reference; the receipt's nonzero initial recomposition change is relative to the older free-alpha checkpoint, not an initialization difference between these paired fits. All evaluations completed within the bound. Flat returns after 174 iterations/187 evaluations with maximum raw-parameter gradient 5.30e-6; repeated final evaluations have identical objective. Layered reaches 1000 iterations/1039 evaluations with gradient 0.001627 and a still-decreasing late objective. Both exceed the declared 1e-6 stationarity criterion. These are accepted finite returned states, not demonstrated stationary solutions or global optima. Lower data NLL is comparable across arms; changed prior totals are not comparable evidence of image quality.

Commissioning supports the intended conditional mechanism: independent colour-and-spatial weak-direction curvature remains 0.5, while the same-spatial counterexample retains only about 0.5/65. The photographic-purpose failure is therefore not erased by passing that arithmetic witness. These outputs do not identify which singular direction carries their colour error, nor prove CFA aliasing or a nullspace explanation. The actual finding is narrower: this finite-budget matrix prior improves strong-feature RGB and forward fit while still insufficiently protecting colour. No parameter or continuation rescue is recommended from this screen; a different mechanism would need to address that measured tradeoff explicitly.

Bindings: scored result SHA256 `1a693c5b5b417a352f62389464b23bb43c3a1de1351788dbbceb8cdf96aa7db0`; fitting source `6555432834b543f5102899e4c21931c050ce6994b898e5b0ac74f38b03880b9a`; controls `46dc99bf4acd698e80b2d495be199b3540e83f08bbc0152165ab38e69ecc61a1`. Known optics/visibility and the outstanding resolved-pupil disagreement continue to prohibit RAW or SOTA generalization.
