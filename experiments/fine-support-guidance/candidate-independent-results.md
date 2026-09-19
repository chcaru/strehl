# Fixed radius32 finest-band pooling: independent rejection

**MEASURED: no photographic replay admitted.** The fixed candidate fails the
predeclared quality screen. Close this intervention without a radius or
threshold rescue. The earlier real-stack nomination changes were a useful
diagnostic, but did not predict safe reconstruction of real detail.

Evidence: `candidate-controls-1/output/screen.json`, `process.log`,
`process.json`, and `invocation.json`. Root ran
`candidate-build-1/cli-tests.exe merge_cmd::fine_support_candidate_tests:: --nocapture --test-threads=1`
with the recorded environment. Two tests completed successfully in 0.797 s
job wall time; their successful execution includes the explicitly negative
quality decision. Fresh-build log contains `Compiling strehl-core` and
`Compiling strehl-cli`; executable SHA256 is
`752f50dda97fad3c3fb332fcd8b47261a09dbabf83a27fb48976e0ba5ead3716`.
The receipt binds the unchanged predeclared controls and plan hashes.

| Criterion | ISO100 | ISO400 |
| --- | ---: | ---: |
| Fan RGB truth-error ratio; required <=0.95 | **1.125616** | 1.231861; fan fixture inadequately exercised |
| Core recovery, truth capped at 1; required >=0.90 | **0.410–0.423** | 0.407–0.421 |
| Depth-boundary RGB error ratio; required <=1.10 | 1.001943 | 1.005581 |
| Genuine coloured radial RGB error ratio; required <=1.10 | 0.933677 | **1.161348** |
| Flat RGB / chroma error ratios; required <=1.25 each | 0.878550 / 0.889083 | 0.877643 / 0.887323 |

ISO100 fully exercises the fixed scene and is sufficient to reject. The glint
core loses roughly 58–59% of truth-capped template recovery, with RGB RMSE
increasing 6.530006x. Its baseline recovery was slightly above 1, so the loss is
not a false penalty for removing manufactured contrast: the test already caps
that baseline at truth. Core chroma error nevertheless improves to 0.893962x.
This is an explicit failure of using chroma suppression alone as quality.
The nearby coloured texture is essentially unchanged, and the broad boundary
strip passes, so neither would have detected the compact feature's destruction.
Spatial borrowing from another depth is consistent with this failure, but the
screen did not dump per-source contributions and does not establish that
particular causal attribution.

ISO400's glint fixture fails **both** predeclared fan-strength conditions:
baseline fan RMSE 0.003400573 and noiseless defocused fan RMSE 0.003701471 are
below twice the flat baseline RMSE, 0.004441566. The actual finest-band selection
and recovered-nearer-texture conditions pass. Thus this is insufficient fan
separation from the fixed noise control, not an inactive candidate. Do not
present ISO400 as an independently validated fan-removal failure. Its genuine
radial scene is independently exercised and does reject: RGB error rises 16.13%
even while template recovery improves and chroma error falls 4.12%. Recovery
and chroma alone would both miss the additional error. ISO100's valid rejection
does not depend on either ISO400 observation.

**VERIFIED structural scope:** disabled mode reproduces all four collapsed
planes exactly at both ISOs; every scene reports bit-identical actual band 1+
weighted numerators/denominators, including base, all unweighted sums, and
input/per-level hull data. The adapter checks these after each frame and before
finish. This justifies omitting a separate coarse-only fixture for this exact
finest-only implementation. It does not imply final coarse-looking image
features cannot change through finest-band reconstruction or final limiting.
The six direct-box hook checks, zero/positive admission, zero-energy control,
metric destroyers and unchanged original u16 arrays also pass.

This closure applies to the fixed radius32 finest-band candidate on the stated
adversarial operator fixtures. It neither calibrates the camera's actual PSF
nor disproves every spatially supported focus method. No full RAW candidate
render, photographic improvement, production promotion or SOTA claim is
licensed by these results. No source changes or new executions were needed
for this independent result review.
