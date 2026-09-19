# Independent result: close this fixed weighting rule

**MEASURED:** the one-level, identity-gathered green-guided directional rule
fails its fixed quality guards at both ISO100 and ISO400. Do not advance this
rule to fractional geometry or a photograph. This closes the tested operator,
not complex-wavelet fusion as a family. No controls, stimuli, thresholds or
source code were changed during this review.

The root-run command was `build-3/cli-tests.exe
merge_cmd::complex_wavelet_merge::independent_controls:: --nocapture
--test-threads=1`, with the environment retained in
`controls-1/invocation.json`. Both tests passed their structural assertions;
quality admission is deliberately recorded separately and is **false**.
`controls-1/process.json` records1.250s job wall time; the test harness records
0.99s. This is no performance benchmark. Fresh build3 includes both required
Compiling lines. Build1's JSON-macro parentheses fix and build2's module-import
identifier fix were compile-only; the failed builds remain retained.

| Candidate/baseline RGB truth RMSE | ISO100 | ISO400 |
|---|---:|---:|
| Flat |0.930553|0.928816|
| Horizontal wave vector |1.333483|1.125238|
| Vertical wave vector |1.333559|1.123326|
| Diagonal wave vector |1.558112|1.442215|
| Genuine colour, equal focus |1.000124|1.000446|
| Genuine colour, varying focus |1.193885|1.190281|

The axis-aligned failures are **RGB-error failures, not large recovered-detail
losses**. Their baseline amplitudes are approximately1.04 times truth; candidate
amplitudes are0.981–0.989, closer to the correct amplitude. The truth-capped
retention guard correctly passes them. Nevertheless their complete RGB errors
increase beyond1.10: a fitted fundamental amplitude does not measure every
spatial/colour error. These results must not be described as33% detail loss.
The diagonal is different: baseline amplitude≈1.08 falls to0.895–0.896, just
below the0.90 truth-capped guard, while RGB error rises44–56%.

The decisive genuine-colour failure is substantially larger and cannot be
explained by removal of excess contrast. With varying focus, R recovery falls
from≈0.630 to≈0.429 and B from≈0.630 to≈0.273: losses31.8–31.9% and56.6%,
respectively. Both baseline components were already below truth. G loses
4.6–4.9%. Chroma truth error increases≈29.7–29.8%; the reported3800-pixel
truth-green-zero-crossing subset also worsens R/B error30.9–31.5%. That subset
was diagnostic, not an added rejection threshold.

**VERIFIED source choice / ARGUED mechanism:** this fixture's green structure
is horizontal, while its real R/B structures have different diagonal
orientations. The new rule asks each direction of green separately to justify
the corresponding coefficients of every colour. H has no fallback and all4464
positions have multiple weighted contributors. D/V instead fall back to
all-source means at87.8–90.6% of positions across these two varying-focus cases.
That mean mixes focused and defocused R/B detail even when green contains
usable focus evidence in H. The equal-focus colour case stays almost unchanged,
as expected when averaging those directions cannot mix different blur levels.
This comparison identifies a concrete information-loss risk of this choice;
it is not proof that every residual error has that cause.

The flat improvement is real within this fixture and was allowed to qualify
as a benefit. Approximately90–92% of detail positions actually use the mean
fallback. Candidate RGB error remains≈1.143 times the direct original-CFA
mean, so it is not an ideal averaging result. The hard control is≈1.977–1.978
times that mean, yet still below the measured single-source error: do not claim
that this five-frame control is noisier than a single frame.

**VERIFIED comparator limitation:** hard-control donors are elected by complex
magnitude for *every* coefficient, including LL. Voting subsequently changes
only H/D/V, and replay copies the elected LL donor too. Its low-frequency band
is therefore selected, not averaged. It changes selection, averaging and
voting together; its result cannot isolate voting's effect.

Structural controls remove simple implementation explanations: maximum complex
roundtrip error2.40e-7, boundary/phase impulse error6.66e-8, two-pixel cyclic
shift error0, and heteroscedastic impulse-response variance error3.82e-7.
Ideal axis fields place effectively all detail energy in the expected single
direction; the diagonal spreads it over H/D/V≈0.599/0.283/0.118. Actual original
CFA/green identity, source hashes, live weighting and fallback, invalid-input
refusal, and metric destroyers pass. The12-quad scoring trim exceeds composed
analysis/smoothing/synthesis plus final-MHC support. No RAW, optical,
occlusion-edge, covariance-after-warp or multilevel conclusion follows.

Evidence: `controls-1/output/screen.json` SHA256
`84cf8611ebb75faa12dccec451d3925b2ff3b2d90886b9f54eac183a65f61bb8`;
compiled controls `b4624d1eda99d5e487774660783ca25e749ffa46e4ac442b230390fa8f90b1f2`;
implementation `24d2befc4b8fdfa9a6acec0b15cb7d0cff3c1a270e2e97db2fc98b12474ffe31`.
