# Independent one-level complex-wavelet screen

Fixed before execution. Root builds and runs; the implementation author does
not validate the result. Compare the new one-level complex merge to the actual
BandWorker with bands=1. Both retain a mean low-frequency component, but their
analysis bases differ. Neither is the seven-band product. Identity gathering
only: no fractional geometry, source resampling, fitted calibration or RAW.

The candidate uses independent H/V/D weights from smooth5 complex green energy
and smooth5 propagated injected variance, gate2 and existing SoftPower exponent.
Each directional weight is shared by all four CFA complex coefficients; LL
and zero-total-weight detail use source means. Unconditional median directional
weights are rejected: an ideal axis-aligned grating has two inactive directions
whose median would suppress its one active direction. Hard complex maximum
with donor vote is an unsafe descriptive control, never the quality baseline
or a candidate for promotion.

Commission the transform before scoring. Use asymmetric complex input and
constant fields, impulses at both phases and wrapped corners on rectangular
even dimensions. Require maximum reconstruction error <=2e-5 times
max(1, input magnitude), with finite values and unchanged dimensions. For a
constant real input, detail coefficients must be <=2e-5 relative to the
constant. A one-level two-input-pixel cyclic shift must move each subband by
one coefficient, not change its complex phase. Odd/too-small shapes and
nonfinite input must be refused. A heteroscedastic variance field is checked
against the sum of squared actual forward impulse responses, not against the
variance helper's own formula; require relative/absolute tolerance 2e-5.
This validates propagation through the tested transform, not independent
camera calibration. No clipping occurs in the variance/quality domain.

Reuse the existing five-frame native320x288 u16 fixture, active origin(7,11),
padded stride, black512, white15360, non-unity WB and analytic truth. The even
quad crop is(7,9,144,124); trim24 native pixels from quality scoring to exclude
periodic boundary interactions. Source inspection gives analysis2q-3..2q+2,
smooth5 support2q-7..2q+6 and synthesis2q in output-2..output+3: the composed
input dependency is at most9 quads, then final MHC adds1quad. The12quad trim
therefore covers the full operator, not just analysis. Score ISO100 and ISO400
separately, flat first.
Six fixed scenes: flat0.30; neutral horizontal, vertical and diagonal waves at
0.18 native cycles/pixel; the retained genuine-colour0.18 scene; and its retained
spatially varying-focus scene. Axis waves use direction(1,0)/(0,1), diagonal
uses(0.8,0.6), all neutral phase0.37/base0.30/amplitude0.08. Their source blur
is sigma=1.3*abs(frame-2). Genuine colour retains the existing channel phases
and amplitudes; the last scene retains its original smooth depth gradient.
This does not establish occlusion-edge or specular-fan safety.

Before quality is interpreted, assert exact known-CFA and identity-green
agreement with original samples, unchanged original buffers, finite RGB,
different focus guides, live actual detail weighting and multi-source or
mean-fallback participation. On an ideal noiseless guide, each axis grating
must put >99.999% of detail energy in one direction; the diagonal must activate
multiple directions. Report each orientation's actual noisy weighting and
fallback. Axis detail must recover >=0.5 of truth in the matched baseline,
otherwise this fixture cannot assess retention. Varying focus must exercise
the actual baseline's finest selection rather than an all-average path.
For flat fields also report a directly averaged original-CFA mean and one
source developed through the same final MHC. This is a noise-selection placebo,
not another quality threshold. Independently address original green sites in
the padded source to check the actual guide hash. A separate at-white source
must be refused by this adapter's unclipped-domain guard; that refusal does
not establish a clipping-aware merge.

For each ISO require >=5% lower RGB truth RMSE on flat OR a genuine-colour
scene. Every structured scene must stay within 10% of baseline RGB truth RMSE.
Every component recovered >=0.5 by baseline must retain >=90% of its
truth-capped in-phase amplitude. Flat RGB and R-G/B-G truth-error RMS may rise
at most25%. Report quadrature and neutral/colour cases separately. A live
failure cannot be compensated by another scene or ISO. Truth-green zero-cross
R/B error is retained as a reported local risk check, not a post-hoc gate.

Commission scores with exact truth, grey, half-amplitude and overcontrast
destroyers. Error alone can reward smoothing; amplitude alone can reward
manufactured contrast, hence the coupled guards. No gradients, chroma
high-pass energy or winner agreement counts as quality. A passing screen
licenses only further composed/multilevel controls, never a full RAW replay
or SOTA/promotion claim. No tuning after seeing results.
