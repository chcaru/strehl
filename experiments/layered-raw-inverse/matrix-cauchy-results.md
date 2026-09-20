# Matrix-Cauchy still fails the original colour requirement

MEASURED / independently reviewed. The fixed known-alpha output fails both
core and ridge chroma guards. It reduces the rejected scalar-Cauchy colour
error but remains substantially worse than the original-Huber primary reference.
No coefficient, continuation or pass-gated stress rescue is admitted.

Command run:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-matrix-cauchy.py --out experiments/layered-raw-inverse/matrix-cauchy-1
```

Commission/fitting/scoring wall times2.000/35.453/2.407s; peak fitting job
committed memory2,648,301,568 bytes. These are execution receipts, not speed
benchmarks. Scored SHA256:
`1a693c5b5b417a352f62389464b23bb43c3a1de1351788dbbceb8cdf96aa7db0`.
All bound inputs remain unchanged, with exact original160 sheet/alpha/pinhole
initial identity, training-only reads, and unchanged likelihood/solver/remainder.

| Fixed returned-image measurement | Original Huber | Scalar Cauchy | Matrix Cauchy |
|---|---:|---:|---:|
| Flat RGB/chroma RMSE, DN | 5.672017 / 7.925566 | 5.734541 / 8.011089 | 5.749229 / 8.029854 |
| Layered interior RGB/chroma RMSE, DN | 150.971384 / 67.309896 | 121.755868 / 131.312300 | 106.586642 / 97.783288 |
| Core RGB/chroma RMSE, DN | 731.456906 / 260.393167 | 566.931016 / 558.193564 | 488.986860 / 383.707091 |
| Ridge RGB/chroma RMSE, DN | 312.403505 / 120.163530 | 246.086762 / 252.519871 | 213.091121 / 178.279392 |
| Bright held41-sample RMS, supplied-noise units | 2.147807 | 1.158371 | 1.195145 |

Flat passes both retained-mean and paired requirements but is slightly worse
than original Huber. All layered absolute/component and held-prediction guards
pass; the mandatory paired chroma errors do not. Pooled RGB improvement is not
colour fidelity, and comparison with the worse scalar Cauchy cannot replace
the primary reference. Glint projections[1.00013,1.00353,1.00308] and filament
[1.01372,1.00306,1.01675] slightly overshoot; caps prevent extra-detail credit.
Projection can conceal spatial colour error, as the failed guards demonstrate.

The mechanism was commissioned as conditional, not universal: independent
colour AND spatial perturbation curvature is0.5; the same-spatial-direction
colour counterexample is0.007692306. A strong rank-two crossing still has
negative curvature. Arbitrary-direction AD0.501120090 agrees with independent
finite difference0.501120110. The rectangular small-gradient curvature matches
original Huber at0.018622076. These validate the intended operator, not the
cause of the remaining colour error. A smaller final error than scalar Cauchy
does not isolate colour coupling from changed finite-edge loss or trajectory.

Flat returns at174 iterations/187 actual evaluations, max gradient5.30e-6;
layered reaches1000/1039 at0.00162723. Both exceed1e-6. The evidence concerns
these returned states, not proved global optima. Known visibility and failed
continuum-pupil adequacy remain. No original camera photograph was rendered.

Independent choice-point review: independent-matrix-cauchy-results.md. The next
question is the intended output consumer: the present target is an unblurred
pinhole although each sensor image includes the supplied common in-focus PSF.
Auditing a fixed in-focus-appearance target must preserve every existing
failure and apply the same optical transfer to truth and comparators. It must
not become a blur-strength search or a way to conceal lost real colour detail.
