# Fixed native coherent estimator: two separate predata decisions

The operator is the existing regularized whole-source estimator, applied to the
current rounded GPU gathered f32 CFA tuple and guide: Tenengrad27, box17,
Gate4. The original u16 storage, injected camera model, current gather and
development remain. The legacy focus-response noise constant is **not calibrated
for this gathered/interpolated guide**. This tests a fixed operator with an
explicit model limitation; it does not establish noise calibration or borrow
old noise/quality measurements for the new consumer.

The independent reviewer owns controls and this plan; root builds/runs and the
operator author never verifies their implementation. No parameter/scene/threshold
change follows results. Exact inherited fixtures/metrics are copied from the
frozen cross-scale-source-prior controls: five320x288 original-u16 frames,
odd storage origin(7,11), RGGB active phase, WB(1.7,1,2.3), fixed fractional
similarities, crop(7,9,145,125) quads, injected ISO100/400 models and fixed noise
seeds. No RAW reads or image volume. Whole means the retained supported interior
[38,42]–[280,244], not an entire photograph.

Twelve mandatory cases run, flat first at each ISO, regardless of a preceding
quality failure: flat; broad bright contact; neutral/chromatic glint plus depth
edge/near texture; transparent near-fine/far-coarse superposition; true coloured
thin radial detail. Exact scene formulae, windows, RGB/chroma truth-error RMS,
signed bias and truth-capped component guards remain inherited. A structural
execution failure may stop the test; image failure must remain in the result.

## General qualification

Preserve all previous bars: flat<=1.05 current RGB/chroma; contact outside RGB
<=.95 current and its signed-excess/input-spill exercise tests; other structured
RGB/chroma<=1.05; protected current component>=.5 and candidate truth-capped
component>=.98 current. The joint near/far regression retains both templates
and their covariance so stronger fine detail cannot conceal genuine coarse loss.

The baseline's signed contact-outside positive is already known UNEXERCISED
from the unchanged current scene/consumer. This limitation is not newly
discovered failure evidence and cannot become a qualified spill-repair claim.
General qualification retains that missing exercise independently from any
new exercised errors in the twelve scenes. It is not the permission for the
separately defined observation below.

## Optional whole-chip observation, fixed before results

This is mode characterization, not an opaque-scene safety classifier, general
quality pass or default proposal. At **both** ISO100 and400 require:

- Flat RGB and R-G/B-G error RMS<=1.05 current. More than95% of supported
  interior quads must actually average at least2 of5 source tuples.
- Contact interior **and** contact-edge RGB error<=.95 current, chroma<=1.05
  current, and protected interior components live(current>=.5) with >=.98
  truth-capped retention. More than10% of contact-interior quads must exclude
  at least one source (count<5), proving it does not merely run MeanAll.
- True coloured rays keep their inherited local/whole RGB/chroma<=1.05 and
  live protected components with >=.98 capped retention.
- All twelve cases and mandatory structural/destroyer checks complete. Near/far
  and glint damage is fully reported even when optional observation is permitted.

The known absent signed-outside positive is not an optional gate. Interior/edge
improvement cannot be relabelled outside bright-spill repair. If these prospective
bars pass, they permit only one unchanged complete299 held-chip Current/candidate
pair with all masters/whole views and all seven fixed native regions retained.
The original warp/crop/CA/WB/tone and exact historical Current pixels are required.
Whole-photo review can still reject utility. Any gain licenses only optional-mode
investigation, not SOTA or production/default eligibility. No after-result
rescoping is needed or authorized by this plan.

## Consumer and instrument controls

Every case also runs **MeanAll through the same actual gathered tuple consumer**;
its baseline must exactly equal the coherent arm baseline, counts must all equal5,
and source/guide/variance/beta/focus replay evidence must agree. MeanAll truth
scores are reported; they are neither a new benchmark target nor automatically
good on defocus. A neutral flat's true resolution cannot justify selecting one
noisy source, so flat averaging participation is an explicit requirement.

Forced wrong whole-tuple donor4 on Contact and donor0 on NearFar must change
actual outputs and fail a relevant contact or far-component/error guard.
Each receives all five original gathered sources through the same consumer;
counts must all equal1. Destroyer failure-to-fail makes the instrument
unexercised and blocks observation, not a reason to relax a guard.

The pure test builds a tiny independent focus field with exact ties and
responses inside/outside the literal4*sqrt(2)*.015214 tolerance. It checks the
four tuple channels share one acceptance set, exact signed-zero/one-source
identity, lower-index tie election, MeanAll literal source-order f32 average,
forced tuple identity, malformed/nonfinite/count refusals, and live multiple
source averaging/exclusion. This is arithmetic commissioning, not calibration.
An independent Sobel/27-box/variance-normalization/17-box control can compare
FocusWorkspace only if the actual frozen API exposes it cheaply; no new focus
noise fit, Monte Carlo campaign or parameter sweep is requested.

Actual one-source generated MeanAll/Coherent outputs must equal the same
gathered known4 fields bitwise; their camera-RGB must match. Canonical one-frame
pyramid reconstruction need not be bit-identical to that tuple, so do not
mistake its possible f32 reconstruction roundoff for failure of this control.
Original input storage and both-pass known4/guide/variance/beta/focus hashes
remain bound. Selection/exclusion is measured from actual counts, not merely
the fixture's blur widths or index-map appearance.

Retained metric commissioning passes exact truth, rejects half true components,
neutralized colour and a half-far component with intact near detail; it allows
removing baseline overcontrast by capping recovery at truth. RMS alone can reward
smoothing; recovery alone can reward manufactured contrast or miss errors
outside its template. Both controls remain mandatory. No gradient-energy score.

Output STREHL_NATIVE_COHERENT_OUT/screen.json, status SCREEN_COMPLETE,12cases,
general_qualification_admitted and optional_chip_observation_admitted separately.
Two tests under merge_cmd::native_coherent_estimator::independent_controls::;
marker NATIVE_COHERENT. Successful Rust exit never substitutes for either decision.
