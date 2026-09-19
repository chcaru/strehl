# Independent generated-only green-match screen

Fixed before execution. Root owns builds/runs; the implementation author does
not validate results. This compares the current actual four-plane pyramid
baseline with one exact rule: use its collapsed green target, accept each
source quad when squared green difference is <=4 times the injected source
guide variance, then average every accepted source's complete twelve-slot RGB
tuple. With no accepted source, return the baseline RGB at all four sites.
No fitted noise, RGB covariance, optical or calibrated 2-sigma probability
claim is made: the target is correlated with these sources and source guide
variance is only a proxy for variance of their difference.

Reuse the phase-packed experiment's five-frame u16 CFA fixtures: native
320x288, decoded active origin (7,11), padded stride, non-unity WB, crop
(7,9,145,125), and its fixed fractional similarity maps. Use its original
analytic neutral/coloured waves and spatial focus gradient. Run flat first,
then neutral 0.18, coloured 0.18 and coloured varying-focus 0.18, at ISO100
and ISO400 separately. No new physical image model, threshold sweep or scene
tuning. The varying-focus scene must really select finest-band signal and
must supply different actual guides; this is a depth gradient, not a claim of
occlusion-edge safety. The baseline's four known gathered CFA sites must agree
with the twelve-slot source gather and original source arrays stay unchanged.

For one possible later photographic replay, at each ISO require >=5% lower
RGB truth RMSE in at least one genuine-colour case OR in the flat case. Every
structured case must remain within 10% of baseline RGB truth RMSE, and no
structured component recovered at least halfway by the baseline may lose >10%
of its truth-capped in-phase amplitude. Flat RGB and R-G/B-G error RMS may rise
at most 25%.
Report neutral error changes, all colour cases and each ISO separately. These
bars do not promote the rule and do not establish that it addresses vitamin-C
fans. A success cannot offset a live failure of the component or flat bars.

Pre-run amendment requested by root, before numerical output: flat-noise gain
is a valid benefit only if all structured guards hold. Also score the fixed
truth-green zero-crossing subset, abs(cos(green phase))<=0.15, in the existing
coloured varying-focus scene. Report R/B truth RMSE there and require no more
than 10% increase. Frozen colour phases are unchanged. This exposes a relative
failure that is distinguishable using the baseline's contextual gradients:
equal green intensity can occur at a zero crossing while out-of-phase red and
blue contain real detail. It is not the impossible demand to disambiguate an
entirely identical green neighbourhood. Do not pool this local failure away
with improvements elsewhere.

Absolute truth error can improve by blurring, so retain the component bar.
Template recovery can reward manufactured contrast, so cap recovery at true
amplitude and retain absolute error. Reuse exact-truth, grey, half-amplitude
and overcontrast metric destroyers. No gradient/high-pass or winner-coherence
metric counts as quality. Injecting and consuming the same sensor noise model
tests an operator, not camera calibration.

Reverse the replay source order, retaining the canonical baseline. Require
identical target, acceptance counts, fallback population and per-source masks;
report maximum RGB difference and require <=1e-6 in normalized camera units
for f32 summation order. Compare the baseline itself bit-exactly. On real u16
fixtures require actual acceptance, rejection and multi-source participation;
an unchanged or single-source arm cannot provide averaging evidence.

The same acceptance and finish loop also receives a tiny explicit field to
exercise cases a baseline-derived target may not naturally produce: exactly
at the inclusive 2-sigma boundary, just outside, zero accepted sources and
bit-exact fallback at all four native sites, whole-tuple common acceptance,
and independent colour/phase patterns. A genuinely zero-count field must be
seen. These are code-path controls, not a replacement synthetic image model.

Two explicit information-limit witnesses are required. First, equal green
with incompatible chroma admits both tuples and creates their mean colour.
Second, matching green with red at the supplied sensor white level remains
admitted under the proposed rule. Test the actual arithmetic and record these
limitations; do not invent an impossible demand that green alone distinguish
identical green observations, or falsely call these outcomes colour/clipping
safety. The comparison cannot be described as clipping aware or colour safe.
No source image is modified, and no RAW/build run is performed by this reviewer.
