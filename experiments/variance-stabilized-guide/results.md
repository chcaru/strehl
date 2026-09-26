# Fixed nonlinear guide: no bright-spill benefit

MEASURED, September 26. The generated actual-consumer experiment completes all
four independent tests and eight image cases. The fixed recipe is rejected:
the exercised ISO100 bright-spill positive does not improve, and the flat and
genuine bright-ridge errors fail the prospectively fixed limits. No real RAW,
one-source cost run, full photograph or default change follows.

Executed with the installed Python3.12 interpreter:

```text
python -I -B -X faulthandler experiments/variance-stabilized-guide/run.py build --out experiments/variance-stabilized-guide/build-1
python -I -B -X faulthandler experiments/variance-stabilized-guide/run.py controls --build experiments/variance-stabilized-guide/build-1 --out experiments/variance-stabilized-guide/controls-1
```

The fresh release build explicitly recompiles strehl-cli and finishes in
191.329s. Transform, paired-floor and metric controls pass before the image
screen. The screen takes2.672s with388,288,512bytes peak job committed memory;
these are operational readings, not throughput benchmarks. Source bindings are
unchanged. Screen SHA256:
`9fef5492f4334cb08cc16cfc3a3562b8c02878a937bbf649038f843b27d6e90d`.

The same sixteen original-source noise draws supply both matched-linear and
nonlinear floors. Four arms reconstruct original linear CFA through the existing
consumer. Canonical identity, original hashes, terminal means, input bounds and
all four diagnostics-on/off CFA/RGB hashes pass. These establish execution and
arithmetic consistency, not photographic quality or camera calibration.

| Case | Nonlinear RGB RMSE / canonical | Nonlinear RGB RMSE / matched linear |
| --- | --- | --- |
| Flat ISO100 | 1.15615 | 1.00027 |
| Flat ISO400 | 1.15391 | 1.00107 |
| Outside bright core ISO100 | 1.02747 | 1.01013 |
| Outside bright core ISO400 | 1.02616 | 1.01202 |
| Genuine bright ridge ISO100 | 1.40832 | 0.89518 |
| Genuine bright ridge ISO400 | 1.21345 | 1.03761 |

Lower truth error can reward smoothing, so separate component recovery and
flat controls remain binding. ISO100 spill has the required signed excess,
changed weights and changed outputs, but misses the required5% error reduction
against both references. The similar flat errors of the nonlinear and matched
linear arms locate that comparison's penalty in the common changed estimator;
they do not isolate its stochastic mechanism. Weak colour passes at both ISOs.
The ISO100 ridge improves over matched linear but remains much worse than the
current canonical output, so it is not a production-quality gain.

The independent joint core readout also exposes an unqualified protection:
both references recover only about0.27-0.30 of the known texture coefficient,
below the fixed0.5 exercise minimum. This is not evidence that the nonlinear
guide erased that texture; its coefficient is slightly larger. The glint and
texture cannot be pooled into one favorable retention claim. ISO400 spill is
not a replicated positive because its exercise condition fails.

Keep the fixed transform and estimator recipe closed without a tuning or
full-stack rescue. The result does not refute all nonlinear focus measures,
establish the cause of photographic mineral glare, or earn a SOTA claim.
See the frozen independent plans and independent-results.md for interpretation.
