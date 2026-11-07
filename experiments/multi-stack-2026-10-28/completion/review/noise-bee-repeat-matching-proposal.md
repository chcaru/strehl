# Runtime cross-pass matching for an unresolved focus plateau

PROPOSED experiment; no product threshold or grouping has changed. Preserve the four completed product16 baselines. In the32bee run the current matcher proposed only four2-source groups plus24singletons. `fraction*min(median adjacent |logscale step|)` treats jitter as focus spacing, and mutual-nearest matching cannot cover a plateau. Fixed maker focus is corroborating context, never the admission test.

## Bounded first correction

Keep groups at at most one original acquisition per pass, exactly as today. Construct a bipartite candidate graph, independently qualify its edges, then perform deterministic maximum-cardinality/minimum-cost one-to-one assignment on admitted edges only. Unmatched acquisitions remain singleton groups. Do not force uncertain or rejected edges to fill the matching. Keep the consumer's coefficient agreement sigma4, clipping/support handling, source ordering and normal single-pass behavior unchanged.

For sourcei define a conservative scale-uncertainty **proxy**, not a calibrated standard deviation: the75thpercentile of accepted incident direct-native `rms_plane_px/lever_plane_px`, without division by sqrt(tilecount), plus the95thpercentile absolute logscale cycle disagreement on incident independent triangles. Require finite positive leverage and enough independently situated support to identify scale; missing evidence is unknown. The pair proposal radius is the larger of the old focus-step radius and ui+uj. Logscale/uncertainty only proposes edges. Residual RMS contains PSF/model bias, and cycles can share systematic bias, so neither proves same focus. Record every source proxy, attempted edge and refusal. A direct-native accepted cross-pass edge and a bounded consuming-placement consistency check remain required.

This proposal deliberately does not turn a larger proxy into acceptance. Very uncertain geometry may propose many edges but must fail the separate placement/PSF evidence. Benchmark proxy behavior on measured-curvature plants and genuine fine-focus sweeps before using the real bee result to motivate a default.

## Independent compatibility evidence

Use the physical patches nominated before candidates in the bee protocol. Fit pair geometry on the frozen antenna-tip patch; use distinct forehead/lower-body texture patches for PSF compatibility, with original-sensel support/search/filter footprints disjoint from each other and all nine scored photographic/assay witnesses. The three nominations may be unusable; that produces unknown rather than a convenient replacement patch. The disjoint right-thorax patch is the only optional photometric-fit region.

At the returned consuming placement, gather original same-color CFA samples and compare noise-corrected low/middle/high spatial-band responses in both directions. Treat a loss of real high-frequency contrast separately from a lower residual/noise value. Require actual textured support in at least two separated validation regions and all relevant colors; flat calibration pixels cannot certify focus compatibility. Preserve raw-gain1 residual and gain-normalized shape diagnostics separately. A global gain match cannot hide complementary texture, local lighting or channel-only damage. Photometric fitting does not silently enable gain correction in the Repeat consumer.

The equivalence margin must be commissioned in the actual candidate→compatibility→assignment→core producer. A useful decision quantity is an upper estimate of signal-discrepancy loss divided by the independently predicted two-source averaging benefit; do not fit it to the real measured noise reduction. For an equal pair targeting both physical states, known signal discrepancy contributes squared difference/4, opposing the noise benefit. Finite-support uncertainty and geometry mismatch increase the conservative loss estimate. High-noise data with insufficient power must remain unknown, even if its observed residual looks small.

Before a measured implementation exists, no numeric equivalence margin is licensed by this note. The independently injected camera model and exact per-warp noise transfer remain mandatory; no stage-specific noise fitting. Do not call compatibility same physical focus or transfer a threshold from the bee to a genuine fine sweep without its controls.

## Assignment and dependence

Use maximum cardinality among fully admitted edges; secondarily minimize the summed normalized compatibility cost, then use a stable source-content-hash tie key. Do not use source filename ordinal as a focus coordinate. Pass swap must produce the same unordered source pairs, and source-order permutation must produce the same content-identified matching unless an explicit deterministic equal-cost tie is exercised. The optional-primary preference affects target behavior, not pair evidence.

The matching is data dependent. Its photons must be disjoint from the independent-reference assay's scored photons, including complete guide and pyramid/plugin halos. Report the fit/matching dependence for full photographs whose normal geometry uses the entire scene. Noise/transfer controls must run the matching step itself; proving an isolated score is insufficient.

## Falsifiable battery and real comparison

1. Flat independent original-u16 noise first: a perfectly flat calibration field must not certify a plateau. With separate textured calibration and a flat scored field, actual matching plus core must preserve mean and lower conditional variance without selection bias; same-photon calibration/score reuse is an explicit foil.
2. Constant-focus known colored texture with measured bee-like translation/scale jitter: recover all eligible cross-pass pairs despite scale-order perturbation. Duplicate content/hash is rejected and gains remain calibrated.
3. Genuine fine-focus and unequal-spacing sweeps, including almost identical scale with different local PSF: reject incompatible edges or retain singleton fallback. Challenge spatially different focus/occlusion rather than only uniform Gaussian blur. Passing a wide sweep is not evidence for the difficult fine-step case.
4. Wrong geometry, repeated-grid period error, equal-mean opposite texture, local light change, color-only damage and a high-noise low-power pair: no false admitted compatibility. Preserve all attempted outcomes, including close failures, without selecting favorable seeds/colors.
5. Exact producer signal-retention foils: constant output/common blur/shift can lower temporal differences but must worsen the independent two-state risk or violate a frozen transfer sentinel. Inspect full matched bee photographs and all nine witnesses under the same display mapping.
6. Pass swap, source-order permutations, deterministic tie and no-cross-edge cases: preserve equivalent matching/fallback, one acquisition per pass, resource bound and unchanged coefficient gate.

Only after commissioning should a new cached bee candidate be rendered beside the existing passA/passB/equal/precision outputs. Report how many additional pairs were independently admitted and where actual coefficient averaging changed. If matching remains unidentifiable, retain that result and examine the physical evidence rather than widening the scale proxy again.
