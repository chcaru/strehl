# Independent result: two-level rule rejected on coarse detail

**MEASURED:** all32 cases exercised their fixtures. Seven scenes pass at both
ISOs and both crop phases; coarse-neutral fails all four times. Preserve this
exact screen's rejection. No thresholds, inputs or operator code were changed,
and no candidate rerun was performed for this review.

| Coarse-neutral | ISO100 phase0 | ISO100 phase1 | ISO400 phase0 | ISO400 phase1 |
|---|---:|---:|---:|---:|
| Candidate/baseline RGB truth RMSE |8.65671|8.64832|5.30340|5.29625|
| Baseline component recovery, approximate |0.964|0.964|0.965|0.965|
| Candidate component recovery, approximate |0.528|0.528|0.528|0.528|

This is genuine signal attenuation, not removal of above-truth contrast.
Candidate RGB RMSE is approximately0.029 at both ISOs; the larger ratio at
ISO100 partly reflects its cleaner baseline. Quadrature is below0.00074 of
truth amplitude, so a simple phase displacement does not explain the loss.
The deeper level is live: all three directions have zero fallback, with all1116
coefficients receiving multiple contributors. The failure is not an unused
coarse fixture or an inactive second transform.

**VERIFIED:** only detail positions receive weights. Deepest LL keeps zero
denominator and is assigned the source mean before reconstruction. A nominal
two-level Laplacian baseline has a different low-pass transfer from this
two-level complex transform; matching the number of levels did not match the
amount of resolved structure assigned to their mean bases.

**DERIVED, not a consumer intervention:** the actual f32 six-tap low-pass
coefficients make the LL explanation quantitative. Define
`L(f)=sum_j LOW[j]*exp(i*2*pi*f*(j-3))`. The known coarse sinusoid has original
quad frequencies `fx=0.096`, `fy=0.072`. Its interior/infinite-sinusoid fraction
of AC energy left in two-level LL is

`p=|L(fx)*L(fy)*L(2fx)*L(2fy)|^2/16 = 0.7600461454`.

The fixture's five amplitude factors are
`[0.0307459675,0.4187424993,1,0.4187424993,0.0307459675]`, whose mean is
`m=0.3797953867`. Ideal focused detail plus mean LL therefore has fundamental
recovery `1-(1-m)*p = 0.5286158743`, very close to the measured0.527–0.529.
This is strong evidence that resolved content stranded in the mean LL is the
main mechanism. It does **not** prove the exact share of final error caused by
LL: the calculation omits spatially varying weights, noise, InputRange and
final MHC. No actual LL-only replacement was run.

The structural log's coarse detail energies sum to14.6021/14.5909 over the
whole finite periodic crop. Inferring LL from those totals gives≈74.4% of the
finite crop's analytic AC energy, not the76.0% interior transfer above. Their
periodic seam contributes to the logged detail energies; those totals are not
a direct measurement of the trimmed output's LL contribution.

The other results are useful but bounded. Flat RGB truth error is0.800–0.809
times baseline. The earlier large genuine-colour focus loss is absent on this
screen. Weak red recovers≈0.643–0.645 versus≈0.244–0.246 for the green-guided
baseline, with a predetermined focused-source witness≈0.709–0.713. Its
focused-source retention is90.38–90.66%, narrowly passing the fixed90% guard.
Actual red-positive/aggregate-zero counts are5084–5296 source-coefficients:
aggregate-floor suppression exists despite this passing output, so general
weak-colour safety is not established. Diagnostic on/off RGB hashes and all
eight collapsed planes are exact.

Structural evidence is sound within scope: maximum reconstruction error
3.69e-7; composed variance agrees with full-transform impulses within3.70e-7,
including wrapped/repeated paths; naive scalar-LL recursion differs by0.0984
and0.0570 across the two phases and is correctly rejected. Distinct per-plane
authority values verify the R/G1/G2/B mapping independently. These are operator
and routing controls, not camera-calibration measurements.

**ARGUED next scope:** one complete transform whose depth follows output
geometry, with a specified dyadic extension and terminal1x1 DC per CFA plane,
so only DC is forced to average. Do not sweep level counts until this sinusoid
passes. Such a new architecture needs bounded storage, terminal small-filter
roundtrips, and covariance composed through every extension alias onto original
samples, followed by the unchanged colour/noise/detail guards. The present
results justify that bounded test, not a photograph, fractional-gather claim,
promotion or retrospective admission of this two-level operator.

Root command: `build-1/cli-tests.exe
merge_cmd::all_cfa_wavelet::independent_controls:: --nocapture --test-threads=1`;
environment in `controls-1/invocation.json`. Fresh build1 has both required
Compiling lines. Two tests pass; job wall3.125s, harness2.84s, not a performance
benchmark. Screen SHA256
`a1a7d16f82cc13aac903b86780725bb30f9522d9f321dce4f50412c471913308`.
Implementation `02993079671a30aa80d41238d388f0f16211514bfe1edbca3dbd0fb2462e21df`;
controls `c6805ccf00a913da5b7f4333d6c8f724ddf2173c4fe40bc80af121829a843bfe`.
