# Real paired core CFA repeatability

MEASURED: precision has lower raw half-difference squared than equal-repeat and long-only in all ten frozen window/ROI/component summaries. This is actual core CFA repeatability evidence, not developed-RGB SNR or pure sensor variance. Adaptive green decisions, residual signal/focus changes and neighboring pyramid support remain in the output.

| Window | ROI | CFA | Tiles | Precision/equal | Precision/long | Spatial block ratio range |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 12 | adverse-flare-p12 | R | 1 | 0.9779 | 0.6909 | 0.803-1.365 |
| 12 | gray-ramp-middle | R | 4 | 0.8254 | 0.7525 | 0.592-1.214 |
| 20 | gray-ramp-middle | R | 2 | 0.8988 | 0.7046 | 0.744-1.045 |
| 28 | gray-ramp-middle | R | 4 | 0.7881 | 0.8085 | 0.639-0.992 |
| 36 | gray-ramp-middle | R | 3 | 0.8826 | 0.6987 | 0.674-1.049 |
| 44 | adverse-flare-p12 | R | 1 | 0.9200 | 0.6996 | 0.727-1.114 |
| 44 | gray-ramp-middle | R | 2 | 0.8945 | 0.6961 | 0.717-1.110 |
| 52 | adverse-flare-p12 | B | 2 | 0.8418 | 0.7270 | 0.636-1.193 |
| 52 | adverse-flare-p12 | R | 3 | 0.8458 | 0.7209 | 0.659-1.138 |
| 52 | gray-ramp-middle | R | 1 | 0.7053 | 0.8385 | 0.559-0.938 |

All21 red and two blue component-window tiles were retained, including actual core fallback coefficients. No green or all-RGB support was created. All92 arm/tile/component rows retain1024 pixels with zero invalid outputs. No output-driven survivor selection occurred. Several spatial blocks worsen; the largest precision/equal ratio is1.365. Eight-by-eight blocks share interpolation and pyramid support: ranges show descriptive variability, not independent trials or confidence intervals. Six acquisition windows provide two temporal samples each, hence one difference/window. Reused guides and common fitted geometry further couple the results.

Signed mean differences and centered values are saved beside raw half-difference squared. Gray-ramp precision base44 drifts+3.629DN and base52 drifts-2.893DN. Centering would hide these effects, so the headline ratios are uncentered. They do not isolate sensor variance.

VERIFIED controls ran before measurement cache loads. The root gate at SHA256 `0edf320de86ef2d6294f2c91461ef8c978d7bf1fba7d910d908dfba59784ec55` is unchanged apart from adapter/formatting. Through measured-map original-u16 generation, optical composition, RegionSampler and5x5 filtering, flat and weak stationary texture pass432/432 cases each; drift, translated texture, defocus and clipping pass0/432 each. Exact current optical applied records must equal saved calibration. Thresholds were unchanged.

The actual four core consumer arms then pass flat-first controls with both exposures, saved transfer arrays and injected camera variance over16 repetitions. Short variance exceeds long, while precision is below equal-repeat. A common unblurred two-dimensional signal gives0.19-0.70DN clean RMSE and projection about1.0000. Constant, radius12 blurred and12quad shifted output give about100,18.5 and60.7DN RMSE and fail the fixed15DN transfer sentinel. These commission the scoped instrument, not camera calibration or every signal bandwidth.

The real assay calls PreparedSource, GroupWorkspace and SessionMerge with seven bands, gate2, exponent2, sharpening1.4, Repeat grouping, and equal-observation focus reference for precision. Short and long arms each use one exposure; equal and precision use the same two photons sets. Ten even-ordinal guide acquisitions are normalized, averaged and filtered17x17 with a complete halo, then frozen for both temporal outputs. Guides exclude all current3mod4 measurement frames. Originals stream as u16; no aligned-frame volume is retained. The128quad crop and its pyramid boundary treatment scope this result; it is not the complete photograph.

Source/gate history: a prior20-step qualification refused all36 tiles. Six narrower bases12,20,28,36,44,52 and immutable source-only masks were frozen before this assay. Earlier exploration and shared geometry may have consulted these acquisitions, so they are not globally unseen data. Session/source identity, alignment, calibration and qualification hashes are checked. Cache envelopes/digests are validated; original freshness uses saved size/mtime, not a fresh RAW rehash at every load.

Green failures were classified from frozen qualification receipts alone. In21 red-qualified tiles, long G1 guide range fails20/21 and G2 fails21/21 (medians1.199/1.246, limit1.0). Mean drift fails9/21 long and11/21 short; gradients fail5/21 long and0/21 short; cross-pass gap fails5/21. No support or brightness failure occurs in this subset. Gray green is about11200DN long/4400DN short. Larger normalized gradients are consistent with structure relative to shot noise, but do not distinguish residual registration, sampling alias or focus change. Cause remains unproven; gates were not relaxed.

Reproduction and identities:

- Build and source/library hashes: `outputs/multi-stack/completion/real-noise-consumer-paired-build-01/build-receipt.json`; executable `867cf31a8ca9ce7ceaaee5a2dbfd483f7a74f14a11428d3ad1ec8aa55fc0e8e7`. All ten product14 library hashes are unchanged on postcheck.
- Exact command and resources: `outputs/multi-stack/completion/real-noise-consumer-paired-run-01`; four workers,126 cache hits,0RAW,162.5MB sampled peak private memory. Root work was concurrent; no isolated performance claim.
- Protocol and controls in `real-noise-consumer-paired-01` were written before measurement originals. That directory also contains all final CFA planes, per-band fallback diagnostics and block rows.
- Reproducible summary: `real-noise-consumer-summary-02.json`; command receipt `outputs/multi-stack/completion/real-noise-consumer-analysis-run-02`.
- Green failure census: `real-noise-consumer-green-rejections-01.json`; no measurement pixels were loaded.

A complete photographic claim still needs matched full repeat outputs, constant/structure sentinels, complete-image and native-crop review. This report retains the missing green/RGB evidence.
