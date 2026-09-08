# M194h root source review

2026-09-08. PASS_SOURCE_REVIEW_ONLY. This is an independent read of the core hook, component controls and production bridge authored by factor review. No build, control, render or numerical output has run. The independent saved-data checker remains a separate execution prerequisite.

## Exact reviewed science sources

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| crates/strehl-core/src/pyramid.rs | 208956 | ea0a490d299b156c449b3de8c5633fcaeda2190d1c92d1d9c5356e6a9a92c02e |
| crates/strehl-core/Cargo.toml | 478 | 6ef45d6cecf366bc4a882850f14b2f2ce518dc9ff73f3a3169ee6df0bb04d331 |
| crates/strehl-cli/Cargo.toml | 931 | 3a7ef97eafe3ef7e3b3133fc3a45cca2d7e2da6b0a52bfde26abe09d78d4b32e |
| crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs | 67707 | 9557ee459309a41f5002e18aa09ddd9cb271ffc8498185dbc28bfa078d44e326 |
| experiments/m194h-pedestal-causality/core-hook.rs | 13319 | 2049a12575338d3f109da73b90c000722946eab7de5b9882f0c64d8de15ddad4 |
| experiments/m194h-pedestal-causality/component-controls.rs | 7664 | b32cf2a663eadd14c8b39d86d25c5a2400b70dd00e6907e2dafce036a81fdeb2 |
| experiments/m194h-pedestal-causality/production-bridge.rs | 15382 | fb9dd5d3f6194535f4acab9a743a41ca11a586b7ae85d06cb71e5e17aab3a066 |
| experiments/m194h-pedestal-causality/preregister.md | 13660 | 97ab9cce62e1c1e9bb458430d427de5defad02b5fc8f411ae4daee861d3508d5 |

## Consumer and intervention

The only changed arithmetic is P0's cutoff of already-computed weights where actual E<=F immediately before accumulate_level. Above-floor P bits, H and P arms, injected variance/beta, band exponent, four CFA planes, mean base, all-frame-mean fallback and InputRange hull remain on the same code path. Feature omission removes the hook from ordinary builds; the test-only CLI child provides no normal UI or environment activation.

I read the actual run_pyramid_prepared schedule in merge_cmd.rs: one BandWorker receives ascending original frame indices in serial chunks. The two-thread pool parallelizes spatial operations inside that held consumer. The global trace's frame ordinal is therefore appropriate for these five frames; no claim is made about a different concurrent caller.

The native red(202,104) site is a red sensel; red(205,113) is interpolated at blue CFA phase. Full two5x5 native MHC envelopes map to four-plane quad dependencies and every nonzero inverse-expand predecessor through three fine bands plus the mean base. Shapes are150x113,75x57,38x29,19x15. Retaining one final coefficient alone would not explain either output. The checker independently derives exact influence weights and final RGB reconstruction.

The CameraLinear profile=None writer uses constant measurement Software from CARGO_PKG_VERSION, here strehl 0.0.0. I checked this actual branch before retaining WHOLE TIFF equality against the archived H/P and null outputs. The alternative assumption that a new build forces pixel-only equality was withdrawn. Off/on/placebo must additionally be byte-identical within each arm and show the intended observer counts.

## Powered controls and limits of the inference

The fixed component test exercises nine real cutoff/fallback merges, three four-plane flat nulls, eleven observer/unarmed comparisons and three strong-stripe comparisons, plus one rejected consumer entry. The actual partition row's classification bit is flipped and restored. The direct all-above-floor weight control uses the actual cutoff function, carries nonconstant positive weights, crosses E=F deliberately and restores. It proves the mutation seam, not an all-above-floor image scene or physical noise calibration. The flat null precedes the strong-stripe error comparison; no gradient-energy sharpness metric is used.

The independent reader must reject a missing nonzero dependency, regroup actual accumulators with recorded chunk boundaries, distinguish mean-base routing from fine-band fallback, reproduce clamp/MHC/writer order and retain unresolved rounding cases. Actual H/P archive identities and source decode counts must pass; a source argument does not substitute for the output hashes.

Interpretation is fixed before outputs: absent relevant positive sub-floor weight is unsupported; exercised P0 failing to reduce P's primary-site absolute error falsifies this selected-case explanation. Improvement still worse than H is partial attribution. The all-RGB fixed window uses the common ideal, signed/absolute error, MSE and >10DN paired counts. Seed743 alone cannot estimate temporal variance. Both selected sites are discovery evidence, not holdouts. This test does not authorize a production default, threshold search, texture sweep or physical-registration claim.

No corpus file is written, no additional RAW decode is introduced, no external source is copied, and no SYNTHESIS fact number is allocated. Build and test results remain UNVERIFIED until the released commands actually run and the separate reader checks the retained outcomes.
