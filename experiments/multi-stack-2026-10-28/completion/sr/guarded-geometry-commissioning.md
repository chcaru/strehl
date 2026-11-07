# Guarded discrete registration commissioning

MEASURED, synthetic only. The exact original-site guard is now compiled from the current core source while frozen release13 supplies alignment/noise/plane primitives. No continuous estimator is promoted.

The old24/4 matched low-DN positive failed as recorded in `sr-matched-signal-controls-01`. The unchanged old operator and fixture now assert the historical adverse result `[0,10,1]` supported RGB pairs/12. The same registered example also runs the wider46/3 guarded remedy; a fresh build passed40/40 (`sr-registered-geometry-controls-02`).

The wider arm uses five spatial training tiles and four held tiles, Gaussian sigma1.2quad, and the unchanged0.15sensor observed-disagreement threshold. Original footprint checks include seed eligibility, all attempted training stages/tiles, central derivatives, every strict bilinear tap and Gaussian/clipping support. Any overlap refuses the entire pair. A later iteration touching unsupported original taps also refuses.

Fresh core reconstruction tests passed50/50 (`sr-original-footprint-core-02`), including actual measure_pair shrinking-overlap and late-invalid-tap call paths. Both guarded measured-trajectory suites passed25/25 after flat-first4/4. New seeds16–31 retained useful acceptance: insect RGB45/48,48/48,48/48 and chart48/48,48/48,47/48. These are conditional descriptive counts, not a calibrated guarantee.

Boundary census was predeclared with independent reviewer before running: shifts0,.10,.14,.15,.16,.20,.25,.30sensor, both signs along x/y/diagonal, seeds64–79, two measured pairs, noisy and noiseless photons. Only saved pulls are displaced; source photons retain the true trajectory. Exact transformed consumer errors and signed rows are saved in `guarded-geometry-boundary-summary.json`.

| Scene | Noise | Requested shift | Cases | Accepted R/G/B | All RGB |
| --- | --- | ---: | ---: | --- | ---: |
| insect | False | 0.00 | 12 | [12, 12, 12] | 12 |
| insect | False | 0.10 | 12 | [12, 12, 12] | 12 |
| insect | False | 0.14 | 12 | [12, 12, 12] | 12 |
| insect | False | 0.16 | 12 | [0, 0, 1] | 0 |
| insect | False | 0.20 | 12 | [0, 0, 0] | 0 |
| insect | False | 0.30 | 12 | [0, 0, 0] | 0 |
| insect | True | 0.00 | 192 | [180, 192, 180] | 168 |
| insect | True | 0.10 | 192 | [98, 183, 92] | 45 |
| insect | True | 0.14 | 192 | [24, 81, 20] | 0 |
| insect | True | 0.16 | 192 | [10, 5, 4] | 0 |
| insect | True | 0.20 | 192 | [0, 0, 1] | 0 |
| insect | True | 0.30 | 192 | [0, 0, 0] | 0 |
| chart | False | 0.00 | 12 | [12, 12, 12] | 12 |
| chart | False | 0.10 | 12 | [12, 12, 12] | 12 |
| chart | False | 0.14 | 12 | [10, 11, 11] | 10 |
| chart | False | 0.16 | 12 | [4, 1, 4] | 1 |
| chart | False | 0.20 | 12 | [0, 0, 0] | 0 |
| chart | False | 0.30 | 12 | [0, 0, 0] | 0 |
| chart | True | 0.00 | 192 | [186, 192, 186] | 180 |
| chart | True | 0.10 | 192 | [135, 191, 155] | 109 |
| chart | True | 0.14 | 192 | [47, 110, 40] | 9 |
| chart | True | 0.16 | 192 | [10, 7, 4] | 0 |
| chart | True | 0.20 | 192 | [0, 0, 0] | 0 |
| chart | True | 0.30 | 192 | [0, 0, 0] | 0 |

The near-boundary false acceptances, including noiseless cases, explicitly disprove interpreting the0.15 observed-disagreement bar as an absolute true-placement-error bound. The runtime API documents this limitation; the gate was not tuned after the census. All per-color0.30 cases refused. Counts aggregate reused seeds/directions and cannot be treated as independent Bernoulli trials.

UNVERIFIED: photographic detail or SNR benefit. Next is the same preselected chart ROI with the compiled guarded operator, followed by held-out original prediction and complete-scene review.
