# Fixed source-gradient target: rejected

MEASURED, 2026-09-25. The four controls completed, but the preregistered scientific screen failed. Flat and near/far target preservation passed; contact preservation and the required spill benefit failed. Do not proceed to a synthesis solver or photographic run for this fixed construction.

This is the control author's instrument/results report. Root executed the jobs; a separate reviewer interprets the choices. The evidence is `controls-1/completion.json` and its four hash-bound `output/*.json` records, under the unchanged preregistration. No reconstructed image, RAW gather, demosaic, sensor calibration or photographic quality was tested.

The candidate changes only the gradient target: differentiate each actual source coefficient before combining it with its fixed canonical weight at the edge origin. Compare against differentiating the resolved canonical coefficient, using the actual truth pyramid. The terminal target stays exact. The test supplies independent known 20-DN white noise and the corresponding guide variance; this validates the operator under that supplied model.

| Frozen check | Result |
| --- | --- |
| Finite-edge, equal-source, constant unequal-membership and unsupported-mean identities | Pass; constant-membership target error is exactly zero |
| Flat, noiseless and noisy; every plane and AC band | Pass the fixed no-harm bar |
| Contact spill benefit, noiseless and noisy | Fail |
| Contact whole/interior preservation, noiseless and noisy | Fail |
| Near-fine/far-coarse joint retention and error bars, both noise conditions | Pass |
| Wrong-depth, erased and half-far destroyers | Rejected as intended |

The contact result is not simply an inactive experiment. In the noiseless spill window, seven of eight plane/band cells exercise the proposed spurious-join condition. Six improve by the required amount; for example R level 0 falls from 0.2901 to 0.1176 DN gradient error. But G1 level 1 has positive join/error alignment and still worsens from 8.7992 to 9.1979 DN; G2 level 1 worsens from 8.4576 to 9.0944 DN and misses the eligibility alignment bar. Positive alignment alone does not make the removed gradient harmless.

With injected noise, all four finest-band spill cells fail the eligibility and benefit bars. Their small changes cannot establish useful defect removal against errors of roughly 26–30 DN. R level 1 improves from 7.3714 to 6.7329 DN; B level 1 is exercised but misses the required 5% gain. The fixed all-cell positive therefore fails in both conditions.

More decisively, the contact interior's level-2 gradient error increases in all four CFA planes, already without noise:

| Plane | Baseline DN | Candidate DN |
| --- | ---: | ---: |
| R | 27.8467 | 37.2427 |
| G1 | 85.7620 | 97.7928 |
| G2 | 76.6347 | 93.1073 |
| B | 32.8596 | 37.7337 |

The noisy case repeats all four failures. Whole-interior R level 2 also fails (17.1402 to 18.1448 DN without noise; 17.1144 to 18.1046 with noise). Fine contact-template retention passes, so this is a coarse target-error failure, not an erased-fine-detail diagnosis. RMS can reward smoothing; the separate live template protections remain necessary and were retained.

Near/far joint component retention passes in both conditions. In the noiseless R example, the protected coarse component remains about 0.94064 while the fixed source-0 wrong-depth target yields about 0.21767. The erased and half-far arms commission the scorer against truth recovery 1; they are not independent photographic evidence. Passing this depth fixture does not negate the contact failure.

Root's recorded commands are in each `process.json`: fresh standalone `cargo test --manifest-path experiments/source-gradient-target/Cargo.toml --lib --no-run --release --jobs 2 --target-dir target/source-gradient-target --message-format=json-render-diagnostics --locked --offline`, then `build-2/controls.exe independent_controls:: --nocapture --test-threads=1`. Build 2 took 1.782 s; the bounded controls process took 0.453 s and reported four passed tests. These are retained job observations, not speed benchmarks.

`build-1` is preserved: it failed E0583 because the small harness used the implicit underscore module filename while the existing file uses kebab case. Root added the explicit `#[path = "independent-controls.rs"]` attribute after that compiler exited. No operator, fixture, region, bar or score changed. Fresh build 2 and controls 1 are the measured result.

Closure: retain the observed fine-target improvements and coarse contact harm together. The fixed source-gradient target fails qualification; no solver, threshold adjustment, region change, alternate derivative, noise rescue or full-output claim follows from these results.
