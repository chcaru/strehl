# Same-exposure chart decomposition

**MEASURED / VERIFIED, negative photographic result.** The fixed short-exposure,
long-exposure and combined dot neighborhoods, plus the short-exposure fine bars,
all had connected accepted RGB registration with cycles. Separating exposure
passes did not reveal a useful visible reconstruction improvement. Independent
review inspected all four complete192-square boards with the native display
transform and found neither recognizable detail/color-alias gain nor an obvious
new artifact. This result leaves the requested SR outcome open.

The [frozen plan](single-exposure-plan.md) records all sources, guides, locations,
defaults and comparison scope. `run-chart-decomposition.py` generated the actual
per-arm commands saved under `outputs/multi-stack/completion/`. The geometry
summary is `sr-chart-decomposition-17-measure-summary.json`; final rendering is
`sr-chart-decomposition-17c-render-summary.json`. Both are cache-only, four-worker
runs with unchanged geometry sigma1.2quad, tile46quad, grid3 and0.15sensor held
consistency. Final executable SHA256 is
`2b5c7ac47df2f195fcb9a08f04a84eb86ccf7009d7d6ebbb0f340e51351fe9ca`.

| Arm | Targets | Coherent pixels /36864 | Retained held-original R/G/B sites |
| --- | --- | --- | --- |
| Dot short | 7 | 1114 | 6/4/6 |
| Dot long | 7 | 2416 | 25/28/22 |
| Dot union | 14 | 3120 | 68/74/72 |
| Fine bars short | 7 | 1132 | 0/0/0 |

All delivered values were finite and every unsupported pixel retained exact
native fallback. The bars have11722 noninvertible native pixels and little
qualified focus support. The long-exposure bar pass had no qualified focus
nomination and was not silently replaced by a hand-picked neighborhood.
Single-pass versus union is not an equal-count estimator comparison. Prediction
is conditional on adaptive/shared geometry, focus and appearance admission;
the existing native master is a dependent fallback, not truth. Zero retained
bar predictions supplies no prediction-quality result.

All140 exported original same-color96-square patches were unclipped. The
commissioned Hann-spectrum observer found directional sampled band-edge energy
above its injected-model denominator, especially on the bars: vertical median
observed/model ratios R/G1/B/G2 were3.882/12.329/6.717/14.001. Flat/noisy-flat,
known-frequency and indistinguishable0.4/0.6cycles-per-quad alias controls passed.
This is descriptive sampled structure, not a measurement of unaliased optical
bandwidth, true noise, or resolution. Fixed pattern, spatial shot variance and
window leakage remain possible contributors. The full interpretation and source
audit are in [the independent review](../review/sr-next-instrument-review.md).

The first7-source prediction run exposed a research-harness indexing assumption
at withheld index10. Its failed receipt remains
`sr-chart-decomposition-run-17-render-dot-short` (exit101). The corrected harness
keeps the frozen withheld indices3/10 when available, preserving14-source
behavior. Five matched/prediction controls then passed, including flat first,
colored alias, exposure and clipping. The final legacy-union replay reproduced
all20 prior arrays/TIFF pixel artifacts exactly. The failure was not discarded
or represented as a completed result.

Final render arms took2.587–3.603seconds with sampled peak private memory below
1.178GB, alongside other owned work; these are bounded-pilot timings, not a
full-image speed claim. Full outputs were not rerun because this experiment
did not meet its photographic bar. The next fixed stimulus is the existing
[tilted chart](tilted-chart-plan.md), retaining all these negative results.
