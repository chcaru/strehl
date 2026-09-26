# Independent interpretation: reconstruction consistency

2026-09-25. **MEASURED: numerical controls pass; general image-quality qualification fails.** The fixed least-squares reconstruction substantially improves the generated broad contact, but increases focused-glint error and trades genuine far-coarse detail for near-fine detail. Lower coefficient residual is not sufficient for better image quality. No tolerance, norm, iteration cap or stimulus is changed after this result.

## Admitted measurement

Root ran the fresh `build-1/cli-tests.exe` with `merge_cmd::consistent_reconstruction::independent_controls:: --nocapture --test-threads=1`. Build wall time was 166.719 s; `controls-1/process.json` records 2.031 s and exit 0. All four named tests and all twelve cases completed. The completion receipt preserves unchanged source bindings and false photographic admission. These are operational times, not a real-stack speed benchmark.

Screen SHA256: `63ea41b7eb9be8bc6e8e4450c0649fddff87865773fdd69f76a1844203c59ac0`.

The independent dense-basis adjoint/oracle, inconsistent-target and synthesis-null controls, high-DN realizable cases, seven-band constant/edge controls and admission destroyers passed. Across the twelve scene cases, all 48 CFA-plane solves converged in 3–5 iterations. The recorded exact-linear RMS error bounds range from 0.002547 to 0.019611 DN; maximum final-addition rounding RMS is 0.000111 DN. These bounds are numerically commissioned, not interval certificates enclosing arbitrary f32 errors. The actual full-image objective is nonincreasing. No scene uses a refused-solver baseline placeholder.

Canonical source/weight/accumulator state, coefficient targets and input bounds remain exact. Canonical collapse plus bounds matches actual `finish`, and the Off arm preserves final CFA/RGB exactly. Every scene has live coefficient inconsistency and output change. Inconsistency also occurs on flat input; it must not be relabelled an occlusion-defect detector.

## Image gains and losses

Numbers are candidate/baseline truth-error ratios at the frozen windows, in ISO100 / ISO400 order. Error ratios can reward smoothing, while template amplitude can reward aligned false detail; the retained independent guards require both. The noise model is shared with generation and is not externally calibrated here.

| Case/window | RGB ratio | Green ratio | Chroma ratio | Decision |
| --- | --- | --- | --- | --- |
| Flat | 1.00525 / 1.00532 | 1.00319 / 1.00323 | 1.01305 / 1.01360 | Within preservation bars; slight error increase, not denoising. |
| Contact edge | 0.80723 / 0.82380 | 0.76612 / 0.77837 | 0.96636 / 0.96938 | New registered contact positive passes at both ISOs. |
| Protected contact interior | 0.70160 / 0.71849 | 0.69683 / 0.70470 | 0.88070 / 0.89626 | Large error reduction with increased template recovery. |
| Contact outside | 0.97639 / 0.97871 | 0.95127 / 0.95940 | 0.99248 / 0.99261 | Preservation passes; no exercised general glare positive. |
| Neutral focused-glint core | 1.10955 / 1.09463 | 1.09261 / 1.08082 | 1.05093 / 1.04906 | Fails the 5% error-damage guard. |
| Chromatic focused-glint core | 1.05068 / 1.04145 | 1.08156 / 1.06872 | 1.12040 / 1.09932 | Fails in green/chroma at both ISOs; ISO100 RGB also fails. |
| Near-fine/far-coarse whole region | 1.03992 / 1.04017 | 1.03158 / 1.03118 | 1.03034 / 1.03061 | Whole-error guard passes, but separate far-detail retention fails. |

The contact-edge RGB reduction is 19.28% / 17.62%. Its baseline error exceeds twice the flat error, actual coefficients are inconsistent, and the output changes, so this is an exercised positive rather than a solver objective or an inactive fixture. The protected interior gains are accompanied by recovery increases: at ISO100 R/G/B rise from `[0.81966,0.89062,0.82662]` to `[0.86472,0.91546,0.85067]`. It is not supported only by reduced error on an erased subject.

The glint failure differs from the earlier chromatic-evidence operator's highlight loss. Here the template amplitudes are already slightly above one and rise slightly further; the reconstruction does not fail their lower retention bound. It fails the independently required truth errors. The extension, depth-boundary and nearby texture windows stay inside the damage bars, but cannot cancel the focused-core failures. The retained genuine coloured rays also pass their protection at both ISOs.

The two-depth case exposes a different tradeoff. At ISO100, near-fine recovery rises from `[0.53649,0.56864,0.54705]` to `[0.60722,0.63817,0.62373]`, but far-coarse falls from `[0.76506,0.78398,0.77225]` to `[0.72397,0.74598,0.72966]`. ISO400 repeats the direction. Across the channels/noise levels the far component loses about 4.8–5.5% of its baseline amplitude, exceeding the fixed 2% allowance, while the near component gains about 12–14%. Joint regression retains the off-diagonal covariance, and both baseline components are live. Whole-region RGB error alone would have missed this failure.

The prescribed actual source0 wrong-depth control reduces far recovery to about 0.216 while preserving a strong near component, and is rejected. The erased-detail and other retained metric destroyers pass their commissioning checks. Neither the failed far retention nor the glint failures can be explained away as powerless tests.

## Scope decision for root

`numerical_pass=true` and `contact_positive=true`, but `preservation_pass=false`, `candidate_qualified=false` and `photographic_replay_admitted=false`. This fixed norm has failed general qualification. Its earlier no-sweep disposition remains; no parameter or stopping-rule rescue is proposed.

There is nevertheless a concrete distinction from an inactive or uniformly harmful method: an exercised 18–19% boundary-error benefit matches the type of broad-contact problem visible in the complete chip comparison, while flat and contact-detail protections pass. That evidence can inform root's separate decision about **one unchanged whole-chip observational pair**. It cannot authorize that run by itself, erase the focused-glint/far-detail harms, assert safety, or support default/other-stack transfer. Root owns that scheduling decision. If authorized, it must preserve the failed generated gate, exact baseline/pinned development, and review the complete image and all frozen native targets, including dark/coloured contacts and scratches. A useful whole-chip tradeoff is unmeasured at this report's writing.

The screen's `legacy_outside_positive_exercised` field is only the inherited baseline-error/signed-bias excitation check; it does not recompute the old unmerged-source4 truth term. Both recorded values are false. The new contact-boundary test was approved before execution and does not pass the old glare question.
