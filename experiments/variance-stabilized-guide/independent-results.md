# Independent interpretation of the fixed guide screen

2026-09-26. **Reject nomination; no cost or photographic run.** The required
ISO100 positive is exercised but does not improve. There are also measured
flat and genuine-bright error regressions versus canonical. Separately, the
core texture protection is unqualified because both references already recover
too little texture; that is not evidence that H newly erased it.

VERIFIED execution: all four exact test processes exited zero with terminal job
accounting and no cleanup error. The image screen took 2.672s and completed all
eight fixed cases. Its command is recorded in
`controls-1/independent-quality-screen/process.json`: `build-1/cli-tests.exe
merge_cmd::variance_stabilized_guide::independent_controls::independent_quality_screen
--exact --nocapture --test-threads=1`. No experiment was rerun for this review.
The reviewed `controls-1/output/screen.json` SHA256 is
`9fef5492f4334cb08cc16cfc3a3562b8c02878a937bbf649038f843b27d6e90d`, matching
the completion receipt. Canonical replay, original inputs, terminal means and
input hull checks pass. Veil ISO100 diagnostics on/off CFA and RGB hashes match
for all four arms. These prove the commissioned path, not photographic quality.

MEASURED truth-RGB RMSE ratios (H/reference; lower is better):

| Fixed window | ISO | H/canonical | H/matched-linear |
| --- | ---: | ---: | ---: |
| Flat interior | 100 | 1.15615 | 1.00027 |
| Flat interior | 400 | 1.15391 | 1.00107 |
| Veil spill, required positive | 100 | 1.02747 | 1.01013 |
| Genuine bright ridge | 100 | 1.40832 | 0.89518 |
| Genuine bright ridge | 400 | 1.21345 | 1.03761 |

The flat errors are 0.00112654 -> 0.00130244 at ISO100 and
0.00225697 -> 0.00260434 at ISO400. Matched-linear is already almost as high
as H: these regressions cannot be attributed wholly to the nonlinear transform.
They nevertheless reject this complete candidate against the current consumer.
These are generated truth errors, not measured sensor temporal-noise ratios.

The ISO100 spill has genuine signed positive error above the flat control and
changed weights/output. Its RGB errors are canonical0.00663335,
matched0.00674718, H0.00681555; H increases signed spill bias as well. It misses
the prospectively required 5% benefit against both references. ISO400 is
unexercised under the frozen positive criterion, and is not promoted to a
second positive. At ISO100 H partly repairs the matched estimator's bright-ridge
error, but remains much worse than canonical. At ISO400 it worsens both. Ridge
component recovery still passes the 90% bar: the failure is actual error, not
invented component extinction. Weak-colour protections pass at both ISOs.
ISO100 adjacent-texture chroma also fails against canonical (1.14860x).

The independently predeclared joint CORE readout changes the interpretation of
the core failure. Across RGB and both ISOs, canonical texture recovery is
0.2673-0.2793, matched-linear0.2773-0.2959, and H0.3037-0.3252. H modestly
increases this coefficient; it does not cause the low reference recovery.
All references remain below the fixed .5 eligibility bar, so this protection
cannot qualify the candidate. The regression is well conditioned: rank3,
relative determinant0.998906 and standardized condition1.06840. This is not a
collinearity failure. The half-texture scorer destroyer recovers .5 while
holding the glint at1, demonstrating the intended separation.

The glint coefficients remain about1.029-1.044 in all arms, while the aggregate
full-truth core recovery reads about0.886-1.012. Thus a nearly preserved glint
would conceal substantial unrecovered texture in a single-template account.
H core absolute errors pass the error bars; do not describe the unqualified
joint protection as a newly measured core-quality regression. Conversely,
coefficients slightly above one are not additional detail, and fitted intercepts
do not excuse absolute brightness error.

The result supports neither a cost run nor a photographic nomination. It does
not refute all variance-stabilized guides, calibrate noise, or identify the cause
of real mineral glare. No threshold, fixture, window, seed or floor rescue is
recommended for this fixed candidate. Prior colour/wavelet/Phase1 conclusions
remain separate and unchanged.
