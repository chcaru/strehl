# M-COVER-NATIVE Amendment 2 — scorecard crop adjudication

## Superseding question

The owner has supplied the closed `cover-default` result. This amendment does
not repeat its external-decoder identity campaign, border profile, safe-inset
search, or shipping-default decision. Earlier Q3/Q4 work remains provenance,
but those questions are superseded for this adjudication.

The only new empirical operation is one cheap repeat of the unchanged frozen
affine-ECC scale reader on the existing `m2-second-first16` Crop TIFF. That arm
is selected before the repeat because it has the smallest emitted Crop
rectangle in the existing eight-arm set. The result is not blinded: Phase A
already recorded its value. It is a repeatability confirmation, while
`cover-default`'s external LibRaw byte identity is the stronger native-sampling
evidence.

## Frozen dependencies

- Instrument:
  `experiments/SCORECARD-BASELINE/audit_geometry.py`
- Required instrument SHA-256:
  `be1ec143f3d391e7eb0ab4a927c4744aa18283f4992e82d3f975354163a357fd`
- Luma reader:
  `experiments/SCORECARD-BASELINE/measure.py`
- Required luma-reader SHA-256:
  `7c0d1175c76ffdab7adc3ab799831cbbd63debcdcb31dc5f9b80372e4ceb51b5`
- Arm:
  `m2-second-first16`
- Existing Crop TIFF SHA-256:
  `a0b38ce9cab2cd0c1030da21d8d44dc5832055045c03dc89c5d45e27a893ee1c`
- Reference:
  `second_second16.npy`
- Native rectangle:
  `4688 x 7032`
- Frozen diagnostic common rectangle:
  `(y=40, x=58, h=4608, w=6912)`

Only `audit_geometry.OUT`/`WORK`-independent functions are called:
`commission()`, `measure.output_luma()`, and `estimate()`. The instrument,
thresholds, downsample, interpolation, and ECC settings are not modified.
OpenCV and numerical thread counts are capped at six.

## Falsifiers and null

Before the real TIFF is opened:

1. the instrument and luma-reader hashes must match;
2. the frozen synthetic identity and translation nulls must remain GREEN;
3. the frozen `+0.300%` scale/rotation plant must remain RED.

The repeat is rejected if commissioning fails, the TIFF hash moves, its header
disagrees with the committed render manifest, or the reader reports scale
disagreement above scorecard section 1.5's `0.10%` gate.

The no-inset field census rereads only TIFF headers and committed Crop
rectangles. Percentages are deterministic arithmetic, not a new image-quality
instrument. It reports both:

- retained area against the full `4688 x 7032` native rectangle; and
- retained geometric intersection against the frozen
  `4608 x 6912` diagnostic common rectangle.

## Interpretation boundary

The adjudication quotes scorecard section 1.5 literally:

> Outputs must retain native scale. Resize is a hard invalidation.
>
> Crops are fixed from the common-input overlap before outputs exist. Retained
> field of view must be `>=99.0%` of that overlap.

`CoverMode::Crop` may establish unity pixel pitch without itself being the
scorecard crop. Its emitted rectangle is alignment-solution-dependent and
differs by arm. Scoring each arm over its own full emitted rectangle would not
satisfy the fixed-common-crop sentence. The report will separately determine
whether one rectangle can be frozen before output inspection and extracted
identically without resampling.

The closed COVER lane's `2.61%` boundary-level result is not imported as a new
measurement. It invalidates a scorecard arm only if a named scorecard clause or
commissioned metric maps to that result without reinterpretation.
