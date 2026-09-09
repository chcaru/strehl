# Independent direct-plane fidelity decision

2026-09-09. **Close float precision as no demonstrated improvement under the fixed rule. Rounded passes the complete generated consumer equality checks and remains suitable for experimental opt-in retention.** The precision arm failed6 of15 strict flat checks, but the adverse changes are small and the paired uncertainty does not establish a significant or visible degradation. No precision detail render was released. The modest native rounded timing result remains separate in independent-results.md; no default promotion or extra timing build is needed to close this experiment.

## Actual finite population and provenance

Root executed the existing M194b consumer from build2 source730542ab83c79f19969ae0eacbe13ed16f015175. The compile log contains fresh `Compiling strehl-cli`; build cost was91.266 s wall. The test executable is13,311,488 bytes, SHA-25658873b3ce09843c013b05195020f1b1b0696930c5f6e370f86db8f48485dc544. Commands were `Python312/python.exe -I -B experiments/native-direct-planes/run-matrix.py --scene flat`, the held scorer with `--scene flat`, then the runner/scorer with `--scene detail`. Root ran the production and scoring paths; this reviewer read saved receipts, small delivered TIFF bytes and already computed metrics. No render, source CFA decode or numerical quality metric was rerun by the reviewer.

The fixed run contains27 flat primary TIFFs (noise-off plus eight repeats, each off/rounded/float), four detail primary TIFFs (plane/colour, each off/rounded), and one flat/noise-off/off observer placebo:31 primary +1 placebo,64 separate plan/render invocations. Every primary consumes all nine original frames, reference4, with the original full-grid transform and142x106 quad crop. All64 process receipts show exit0, no error/cleanup error, completed job accounting and no attempted termination; log digests match. Summed child wall is5.753 s, owned CPU3.671875 s and maximum job committed memory9,220,096 bytes. No native speed claim is made from these costs.

The original scorer refused before metrics on Windows normal versus extended canonical path spelling. score-flat-attempt-1.json preserves the failure. The correction changed exactly three path identity/distinctness comparisons to `samefile`/`not samefile`, retaining file hashes and sizes. The writer-software concern was withdrawn; its literal was unchanged. Scorer source65ee812 uses SHA-256faa3de1227a4b80da4364847b2bc060d37d50a7fc1c9a6bed5fb447d7571e46c. No metric, threshold, target, source observation or rendered output changed to obtain a result.

Bindings checked for this review:

| Saved artifact | SHA-256 |
| --- | --- |
| run-flat-1/run-index.json | 5fca02c070ef75de3a138c097bb4e05357892b5e627793be335e01186669f629 |
| run-detail-1/run-index.json | 0afb4cda88b3a18c701d60e7c29cd1117cb9d1cf9aec24e527c728d56cfa0879 |
| score-flat-1/decision.json | 00e5ddd8753052524136bf3139e0c4013078b36d9ffbeaeee683027ba6e44d41 |
| score-detail-1/decision.json | 9dd29da132407a29bc80b103249dd8cd8a6197c16d704f1c737e84f9052a593d |
| score-flat-1/result.json | 0a7a7dcba5058e9504dab993a58186a11cb1bb4ed61765ba36341e368d727c7a |
| score-detail-1/result.json | 9d5e56acb22836098727f0dd63ee60d5c878a3fc8a1241666da41768174ca188 |

## Exactness, liveness and observer placebo

VERIFIED directly from bound receipts and complete small TIFF bytes: all11 rounded/off pairs agree on99 ordered original-frame input records, covering396 consumed CFA-plane digests,99 luma digests and99 beta digests. Each beta contains two finite values. All11 complete collapsed four-plane digests also agree, followed by identical full TIFF bytes and recorded decoded pixel hashes. This closes build1's intermediate-f32 evidence gap; it does not merely infer that equality from RGB16.

All31 primary renders capture nine inputs and one complete collapsed result of60,208 f32 values:279 primary input captures in total. Every observer-on rounded/float render records exactly9 actual direct calls and9 synthetic-probe direct calls; off records0/0. These are successful production-branch hits, not explicit-helper calls. The observer-off placebo records no captures or counters. Its full TIFF SHA-256 is4cf945da51c2fc41715c07c20188b0329c6de60d17f5a8aa3c2928b5ae86bfcd and decoded pixel SHA-256 is2fc3eeb603ae1f0a8d0a9bdfb4da0e1262e260d5ce18f1e105acf564b9b485db, identical to the observer-on off-mode primary.

Precision is live: in each of nine flat bundles, eight non-reference consumed input/beta records change and the collapsed result changes. The reference self-pair remains equal. Float has248,448 fractional consumed values in noise-off and481,495-481,535 across each noisy bundle. All eight noisy delivered TIFFs change. The noise-off TIFF remains identical despite changed intermediate values. This independently chosen case is a concrete warning against using final quantized TIFF equality as proof of collapsed-f32 equality.

## Fixed flat outcome and magnitude

MEASURED on the held21,504-native-site mask in post-WB DN, using the eight paired temporal repeats. The strict failures are R/G temporal variance, all three repeat-mean MSE values, and G absolute repeat-mean bias. Noise-off MSE and bias are exactly equal in all channels. No channel meets the frozen material-benefit requirement.

| Metric, float minus off | R | G | B |
| --- | ---: | ---: | ---: |
| Temporal variance change, DN² | +0.347354 | +0.032136 | -0.008990 |
| Relative temporal variance change | +0.183413% | +0.017099% | -0.004451% |
| Variance-difference jackknife SE, DN² | 0.194542 | 0.192944 | 0.256148 |
| Repeat-mean MSE change, DN² | +0.048925 | +0.052517 | +0.120302 |
| Relative repeat-mean MSE change | +0.205240% | +0.224643% | +0.477625% |
| Absolute repeat-mean bias change, DN | -0.003008 | +0.001168 | -0.013345 |

The actual off/float temporal variances are189.384031/189.731385,187.940892/187.973028 and201.990445/201.981454 DN². The corresponding temporal sigma changes are approximately+0.012615,+0.001172 and-0.000316 DN. These are temporal statistics across repeats, not spatial image standard deviations. R/G variance increases fail the prespecified non-regression rule, while the tiny B reduction is far below the required1% and lacks the paired uncertainty support required for a benefit.

The paired mean per-repeat MSE differences are+0.352860,+0.080636,+0.112436 DN² with SEM0.177622,0.148882,0.184739. Those are different quantities from MSE of the repeat-mean image. Every variance difference lies within twice its jackknife SE, and every paired mean-MSE difference lies within twice its SEM. These are small-sample diagnostics, not a formal universal confidence guarantee. They do not establish a statistically significant adverse effect or a visible degradation. A deterministic strict gate can reject a small observed regression without proving either claim.

## Independent sensitivity choice and closure

DERIVED from the saved per-repeat/leave-one-out quantities, without changing the fixed decision: excluding each repeat in turn keeps the R variance difference positive, ranging+0.227875 to+0.481846 DN². In contrast, G ranges-0.059186 to+0.150777 and B ranges-0.192742 to+0.139343, changing sign with the omitted repeat. Removing the most adverse R repeat739 still leaves a positive R variance difference; removing the favorable repeat709 increases it. The paired mean-MSE difference remains positive under every single omission in all channels: R0.228664-0.461092, G0.013931-0.189818, B0.014561-0.219807 DN². This checks sensitivity to repeat choice rather than selecting a favorable average. It does not rescue precision, alter the gate, or upgrade tiny effects into a material quality claim.

Flat decision is FLAT_REJECT with rounded_exact_pass=true and proceed_to_precision_detail=false. The only detail outputs are off/rounded plane and genuine colour, which preserve exact consumer and writer results. Detail status PRECISION_REJECT inherits that flat decision; its zero new precision checks are intentional, not evidence that unrendered precision detail passed. Plane/colour precision fidelity is therefore unmeasured in this closed population. There is no basis for claiming an optical, colour or texture benefit.

The useful outcome is exact rounded handoff with the separately recorded small local native speed improvement. Retaining it as experimental opt-in while leaving default policy unchanged is proportionate to that evidence. Float closes as **not a demonstrated improvement** under this fixed program. No further precision population, parameter adjustment or synthetic rescue is justified by these results. The next program step can examine the actual visible product gap on a development stack with the available comparator, under a separately stated comparison contract; this experiment establishes no formal SOTA advantage.
