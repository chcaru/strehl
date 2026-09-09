# Cached-pixel display after the preserved white-threshold refusal

The original five-job diagnostic stopped at the whole-ROI product-white gate.
Its failure, counts, sources and receipts remain unchanged. Independent review
identified a scope error: that gate cannot say whether a smaller nominated mark
is clipped, and decoder white levels disagree (15360 versus16383).

Root authorizes one display-only read of the two retained, byte-verified original
u16 arrays. No decoder, changed crop, numerical acceptance rerun or source-image
resampling. Show every original G1/G2 sample in the entire allocated704x512 ROI,
one green sample per display pixel. Use shared fixed0..14848DN and pooled2/98
inspection-only ranges. Show separate masks for BOTH white thresholds so display
clamping cannot conceal high codes. Record counts in the same fixed sensor target
and its mapped scene extent, without redefining the failed whole-ROI condition.

This is a visualization amendment, not qualification of the failed experiment.
No physical dust attribution, correction fitting, noise estimate or quality claim.
The existing arrays, source metadata, map and full-ROI decoder comparisons must
still match their held hashes. The original corpus remains read-only.
