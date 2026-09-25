# Independent chip review and next bounded discriminator

VERIFIED BY NATIVE INSPECTION, September 25. I independently viewed both complete
chip overviews, the rail-crossing pair at native 384 pixels, and all four
upper-left contact-grid pairs at native 256 pixels. I did not execute the RAW
renders, change their parameters, or substitute a sharpness score for inspection.

The numerical repair does not resolve the broad chip defects. The complete views
are essentially unchanged in composition and apparent quality. The rail crossing
retains duplicated cyan/red fringes, rough coloured edges and broad bright spill.
All four contact-grid pairs retain swollen or overlapping contact edges and
bright plumes. Some contact interiors change locally; I cannot identify a general
restoration of separation or a broad spill reduction. This does not contradict
the separately established repair of overflowing accumulators. It limits the
photographic claim for this particular stack.

The full masters are `outputs/quality-september25/chip-before/stack-master.tiff`
and `outputs/quality-september25/chip-fixed/stack-master.tiff`. The reviewed
overviews are each output directory's `overview.jpg`. Pair provenance and all
native tiles are in `chip-numeric-fix-views-2/receipt.json`. The common output is
6500x4332 native pixels, with plane crop `[133,89,3250,2166]`. The receipt correctly
shifts the earlier experimental ROI coordinates by +16 native pixels in each
axis because its earlier crop began at `[141,97]`. My reviewed regions are:

- rail crossing: `[1098,958,384,384]`;
- upper-left contact grid: `[48,336,256,256]`, `[304,336,256,256]`,
  `[48,592,256,256]`, `[304,592,256,256]`.

The receipt's changed-pixel count is evidence of liveness, not image quality.
These observations do not attribute the residual colour to alignment alone,
establish a perfectly fronto-parallel optical subject, or establish a capture
resolution limit.

## Existing decisions that constrain the next step

`experiments/quality-september14/local-green-translation-review.md` independently
verified that the original green-only local correction reduced held-out guide
error for all eight nonreference frames, to 0.493–0.702 of baseline. The actual
eight-frame cropped consumer showed clearer existing rail separation; see
`local-placement-consumer-photographic-verdict.md` in the same directory.
Frame145 reached the existing translation bound and was excluded from the
photographic intervention. Lower guide error by itself was never a quality bar.

Crucially, this is no longer merely a cropped result.
`experiments/full-context-placement/results.md` and
`comparison-1/photographic-review.md` record a modest local benefit in the full
299-frame, seven-band chip render. Only frames146–153 receive supported, tapered
source-coordinate corrections; colour stipple remains. Repeating this experiment
or broadcasting its local displacement across a whole frame is not the next
research step.

`experiments/quality-september19/results.md`, especially "Focused-window repeat
and final decision", closes the tested star-sand transfer even after replacing
the initially defocused neighbourhood with detail-bearing frames116–124. Lower
held-out guide errors produced no identifiable photographic feature benefit.
`docs/proposals/2026-09-quality-path.md`, "September 19 full-context decision",
therefore defers multi-region extension and automatic promotion. The later
star-focused attribution result finds no specific lost pore/rim feature in its
inspected original/gathered/merged path. Another translation-bound, focus-window
or taper sweep is not justified.

Mechanical prior-art search also returns M103's per-frame consumer-gauge warning,
M78's unsuccessful cross-blur alignment transfer, and M23's resampler confound.
Neither low graph-cycle residual nor a blur-equalized registration residual is
independent proof of geometric truth. The closed peak-fitting, joint inverse
reconstruction, CA-before-MHC and twelve-plane colour trials should remain closed.

## Cheapest new falsifiable discriminator — proposed, not executed

Use only the already retained original-u16 samples:
`experiments/quality-september14/joint-raw-samples-2/frame-145-cfa.npy` through
`frame-153-cfa.npy`, with that directory's `receipt.json`. The reference is149;
the target support is392x392 native pixels, while each saved source patch has its
own slightly larger shape and source origin recorded in the receipt. Source
filenames, exact map parameters, CFA phase, levels and sample hashes are retained.
Independent decoder agreement is already recorded. No new RAW decoding, full
render, global alignment or production hook is needed for this diagnostic.

The unexecuted second discriminator in
`experiments/quality-september14/joint-photographic-verdict.md` is the useful next
question: does a small differential-blur term explain residuals that a local
translation otherwise absorbs? Compare the existing translation-only model with
translation **jointly refitted** alongside one signed Laplacian term. In source
native coordinates the latter predicts `gain * (S(x+delta) + beta * Laplacian(S)
(x+delta)) + bias`; beta has units of native-pixel squared. It is a local
small-blur predictor, not a restored photograph or a calibrated lens PSF.

Keep the existing fixed low-pass band, map, spatial training/holdout split and
gain/bias policy in both arms. Fit nuisance terms on training support only and
apply them unchanged on held-out support. Rechoose green phase for an independent
check at actual CFA coordinates; do not call the existing pooled-green fit a
phase-independent test. Account for derivative support in the existing explicit
train/holdout non-overlap assertion. Do not widen the translation search if145
again reaches its bound, and do not refit tone or modify original samples.

Before real patches, commission translation-only, symmetric-blur-only and mixed
continuous-field plants, plus a flat/noisy null and wrong-sign displacement.
The first must not need a blur term; the second must exercise it without inventing
comparable displacement. Use the existing fixed translation-recovery tolerance
where applicable, and freeze any additional admission rule before seeing the real
fit. An asymmetric-PSF control must expose the limitation: PSF-centroid displacement
can be observationally indistinguishable from geometric translation. It cannot
legitimately be certified as camera motion by this diagnostic.

Report held-out prediction gain, displacement change relative to translation-only,
and beta sign/stability across the two greens. These quantities can favour blur
or absorb unmodelled photometry; they are diagnostic, not quality metrics. If the
extra term fails to transfer or is confounded on the controls, close this small
model without a sweep. If displacement remains stable while the blur term explains
additional held-out residual, it supports a distinct optical-blur contribution
locally; if displacement changes substantially, the old fit's interpretation is
confounded. Neither outcome by itself licenses a general alignment change. Any
subsequent treatment still has to improve a complete image and preserve the
unaffected regions. The saved rail patch cannot settle the spatially distant
upper-left contact-grid defect without separate source evidence.

Read-only search actually run from the repository root:
`python -I -B experiments/ORCH-drift-check/prior_art.py chip alignment defocus centroid local-placement`.
A targeted search for differential-blur/Laplacian-model implementations in the
September14, September19 and full-context-placement directories found only the
unexecuted proposal cited above. No implementation or measurement is claimed here.
