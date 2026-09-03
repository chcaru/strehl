# M-CAND2 — full-covariance Hotelling information

**BLOCKER: the clipped-USM kill arm was potency-invalid.** I stopped rather than
turning a nonlinear no-op into a sharpening-safety claim.

## Freeze

Scientific freeze `c1e7840d3e509d69ce7496b6459d277989cde8db` preceded every
arm. It fixed 480 disjoint macro-tile sites, four complete CFA channels over
`8x8` pixels (`p=256`), 384 independent covariance sites/fold (`n/p=1.5`), four
sealed tasks, separate derivative/covariance/test streams, unregularized full
covariance, Cholesky-only solves, and 10,000 block-then-site bootstrap draws
(`experiments/M-CAND2/PREREGISTRATION.md:9-42,67-76`). Baseline-only tuning froze
amplitude `0.0045`; `d'^2=5.920683`, accuracy `0.895573`, and maximum condition
number `2.17187e5` (`PREREGISTRATION.md:44-50`).

## Ordered results

**Unclipped USM r1/a0.5 correctness check:** baseline `d'^2=6.012288556102`,
USM `6.012288556102`; `R=1.0000000000000266`, two-sided CI
`[0.9999999999996833,1.0000000000004767]`
(`experiments/M-CAND2/out/unclipped-usm.json:214-231`). Maximum covariance
congruence residual was `1.25e-15`, held-score residual `1.64e-11`, and the
operator minimum eigenvalue `1.0` (`unclipped-usm.json:2-12`). The implementation
check passed; this is algebraic correctness, not empirical sharpening evidence.

**Clipped USM:** the recorded `R=1.0000000000000266` is **INVALID**, not GREEN.
No value hit either `[0,1]` rail (`clipped-usm.json:2545-2550`), so clipping
changed exactly `0/2,088,960` scalars and the arm remained the same invertible
linear USM. Freeze `c1e7840d` mistakenly tested baseline-to-USM potency rather
than unclipped-to-clipped potency; the corrected assessment preserves both raw
outputs and records zero nonlinear change
(`experiments/M-CAND2/out/clipped-usm-invalidity.json:2-16`).

I did not change the range or rerun after seeing the no-op. The frozen order
therefore barred gamma, logistic, clipping/quantization, optical degradation,
improvement, and null (`PREREGISTRATION.md:53-73`).

Congruence invariance covers only full-rank linear transforms. It stops at actual
clipping/tone nonlinearity, rank loss, regularization, projection, covariance-model
failure, and the local-linear boundary (`PREREGISTRATION.md:78-88`).

## Verdict

**CANDIDATE 2 DOES NOT LIVE: it is uncommissioned, not empirically killed.**
