# Learned band guide: working native training path, failed held-out quality

MEASURED, September26. The fixed737-parameter source scorer completes its one
1024-step training attempt and the actual Rust replay. It beats uniform
averaging on structured held scenes but fails both required improvements over
the current stacker, with additional bright-detail and colour regressions.
Keep this fixed checkpoint closed to photographic rendering and tuning.

All commands below were run with installed Python3.12, `-I -B -X faulthandler`,
and the root-owned bounded runner. Paths are relative to this experiment for
brevity; the saved invocation.json files contain the complete executed commands.

| Runner phase | Arguments after phase | Result / wall seconds |
| --- | --- | --- |
| build | --out build-1 | fresh strehl-cli compilation;185.625 |
| native | --build build-1 --test independent_arithmetic_controls --out arithmetic-1 | one test passed;.594 |
| native | --build build-1 --test export_dataset --out export-1 |12training/7held cases;31.203 |
| commission | --build build-1 --dataset export-1/output/dataset.json --out commission-1 | Python/native reconstruction passes;7.250 |
| train | --build build-1 --dataset export-1/output/dataset.json --commission commission-1/output --out train-1 | fixed final step completed;17.469 |
| infer | --build build-1 --dataset export-1/output/dataset.json --weights train-1/output/model.json --out infer-1 | frozen model inference;3.953 |
| native | --build build-1 --test replay_dataset --dataset export-1/output/dataset.json --weights train-1/output/model.json --inference infer-1/output/predictions.json --out replay-1 | one test passed, nomination false;2.234 |

These are operational readings, not speed benchmarks. The optimizer itself
takes14.4609353s, with156,370,944bytes peak allocated CUDA memory. Training reads
only the twelve training cases' truth and saves the final1024th update; inference
does not read truth. There was no model, seed, step-count or threshold sweep.

Before training, both positive witnesses have error above twice the matched-N
flat control, and canonical/uniform differ. Near/far, glint and colour protection
have live references. Exact truth passes every final judgment; erased near/far
detail, added noise and erased-image controls fail. The lower uniform near/glint
recovery is reported as unqualified retention rather than making perfect truth
ineligible. This commissions the score, not exact truth's representability by
the bounded-source consumer or the camera's physical calibration.

Uniform and prescribed spatial weights match the native reconstruction exactly
on all twelve commissioning cases, including exercised input bounds. Learned
weights then agree within6.91414e-6, final CFA within.0029296875DN, and camera RGB
within3.57628e-7. Actual source/gather/features/baselines and terminal means are
unchanged; zero-head is exactly uniform. Fixed-feature permutation and duplication
controls pass, and rotating learned weights onto the wrong sources is live and
fails the held score. These are execution checks, not photographic gains.

| Held ISO100 witness | Learned RGB RMSE / current | Learned RGB RMSE / uniform |
| --- | --- | --- |
| Flat,5sources | .90910 |1.03345 |
| Flat,9sources | .76180 |1.05608 |
| Curved bright occlusion |1.47747 | .36885 |
| Near-fine/far-coarse |1.09696 | .33066 |
| Genuine glint core |2.45170 | .20583 |
| Weak colour components |1.10377 | .58215 |

Lower error can reward smoothing, so the fixed absolute RGB/green/chroma guards
and signed component retention remain binding together. Both flats pass. The
near/far case retains its components (green near/far .95454/.93324) and passes
preservation, but fails the required5% improvement. Outside-glint RGB error drops
about5.8% versus current while core error more than doubles and green glint
recovery falls from.98102 to.89950. Its amplitude guard passes; absolute error
still rejects that tradeoff. Weak-colour chroma error rises16.7%, and green near
detail misses its90% retention guard. See independent-results.md for the separate
scientific interpretation and independent-execution-review.md for receipt checks.

Model SHA256:
`0388e4e2af9ff852dc19f0af716ae93642284c9499b68618d1cf747e3d341935`.
Screen SHA256:
`1f3e67c0d20fbb7a3381d86ce8fc9de20267c56689da04fd3fb43ae5d0cb8c23`.
The checkpoint changes only source scores; no learned RGB enters reconstruction.
This rejected small model is not a refutation of learned fusion in general.
Held validation is ISO100 and at most9sources; no real RAW, full photograph,
production/default change, large-stack performance or SOTA claim follows.
