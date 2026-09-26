# Source-weight headroom, without a deployable predictor

MEASURED, September 26. A fixed truth-assisted fit finds source weights that
reduce near/far-detail RGB error by21.4% versus the current tiny consumer while
passing every local protection. This is a constructive representation result,
not a photographic improvement or a learned algorithm. The optimizer reads
sharp truth that a real stack does not supply.

Only shared nonnegative AC source weights change. Original four-plane
coefficients, terminal Mean, InputRange and MHC remain fixed. These retained
fixtures have three AC levels on80x72 CFA quads; production photographs use
seven levels. The result does not locate a production bottleneck or justify a
base-band change. Prior mean-base and directional trials remain closed as
described in the plan and directional-prior.md.

The root-owned commands below were run with installed Python3.12 and
`-I -B -X faulthandler`, from the repository root. The experiment prefix is
`experiments/band-weight-oracle/`; exact absolute invocations and environment
are retained beside every process receipt.

| run.py phase | Remaining arguments within this experiment | Wall seconds / result |
| --- | --- | --- |
| commission | --out commission-1 |27.328 / completed |
| check-commission | --commission commission-1/output --out commission-check-1 |2.906 / refused analytic truth port |
| check-commission | --commission commission-1/output --out commission-check-2 |3.250 / passed |
| solve | --commission commission-check-2/output --qualification commission-check-2/output/commission.json --out solve-1 |27.640 / completed |
| check | --predictions solve-1/output/predictions.json --out check-1 |3.156 / passed mechanically |

The first checker failure is preserved. NumPy's vector float32 exponential
changed four scalar blur taps by one ULP; using scalar exponential rounded to
f32 matches the native tap bits. Only that reader expression changed. All
original truth/score tolerances remain. No optimizer rerun or fixture change
occurred. See independent-plan.md for the diagnostic and the separate execution
review for the historical/current source bindings.

Before sharp-truth fitting, the identical optimizer recovered two prescribed,
known-achievable outputs. Final/initial full-RGB MSE was8.23659e-7 on Flat N5
and.000182732 on Curved N9. Independent finite differences agreed with gradients,
and the wrong-direction steps worsened both targets. Saved final weights
reconstruct complete CFA/RGB exactly through the pinned commissioned consumer.

Both fits used exactly1024 Adam updates, rate.03, epsilon1e-15, uniform start
and final iterate only. The epsilon was selected algebraically before the first
run to avoid suppressing small per-pixel gradients, not tuned to results.
The seven-case oracle optimization took24.3708s with61,761,024bytes peak CUDA
allocation. These are bounded execution readings, not production speed claims.

| Truth-assisted witness | RGB RMSE / current | All protections |
| --- | --- | --- |
| Near-fine/far-coarse positive | .785829 |pass |
| Curved bright boundary positive | .677002 |fail: chroma2.57569x uniform |
| Genuine glint core | .754654 |fail: chroma2.99944x uniform |
| Weak-colour component window | .693298 |pass |

The curved whole-interior window also fails chroma versus uniform. These are
the only failed windows; eligible coefficient retention never fails. Near/far
green recovery is1.01957/.97708 versus current1.00855/.93711. Glint green recovery
improves to.99221; this is not the earlier learned model's lost-highlight
tradeoff. Uniform blurs that glint strongly while keeping lower chroma error,
which remains a binding protection in this registered test. Flat gains use
oracle truth and are not evidence of deployable noise reduction. The clipped
core is outside the original scored scope; no clipping-recovery claim follows.

Screen SHA256:
`c60e4d2399157a16f392a002589e041b6f6fd80ff9d0ca4cb07ff41e48ab0fe5`.
The independent scientific and execution reviews are separate files.
No whole-photo run or default change is admitted. This unsuccessful all-guard
search is not a global optimum or a representability ceiling; the positive
near/far witness establishes headroom only for that exact consumer and case.
