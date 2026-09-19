# Independent complete periodic operator screen

Fixed before execution. Root runs; the author does not verify the candidate.
Completeness is geometric: fixed128x128 quads decompose through seven levels
to1x1 DC. Preserve the all-CFA summed energies, squared WB variance gains,
shared source weights, injected authority, smooth5, gate2, exponent_at(k,7),
mean fallback, InputRange and final MHC. Actual BandWorker is requested bands7,
but its existing minimum-dimension rule reaches [128,64,32,16,8]: four detail
bands and an8x8 base. Candidate alone reaches1x1. Assert/report this geometry;
relative scores can therefore reflect baseline truncation as well as operator choice.
Keep the earlier two-level rejection intact. No level/parameter sweep or RAW.

Commission tiny cyclic2x2,2x4,4x2,4x4 operators with full-basis complex Gram
matrices and asymmetric complex roundtrips. Require Gram/roundtrip errors
<=2e-5. Require bit-exact old-operator analysis and synthesis agreement on8x10.
On128x128 require full complex roundtrip <=2e-5*max(1,input magnitude), relative
Parseval error <=2e-5, constant output only at the terminal DC, fixed impulses
and a one-quad cyclic phase shift. Constant0.37 must give DC47.36 with no other
coefficient above2e-5*0.37. Constant variance0.6 is justified by independently
tested unitary stages/Parseval, not by the variance implementation.

Deep variance oracle: original variance0.6 plus fixed spikes at
[(0,0),(1,0),(0,127),(127,127),(63,64),(17,91)] with increments
[0.5,1.1,2.3,0.7,1.7,3.1]. Expected packed variance is0.6 plus those weights
times squared magnitudes of actual full-transform source impulse responses.
Check every coefficient at tolerance2e-5*max(1,expected), including a one-quad
cyclic shift of the spike sites. This costs a fixed number of transforms, not
an all-basis128x128 experiment. The impulse oracle never reads composed kernels.
Retain explicit invalid-input/finite checks and distinct per-plane authority
mapping. These validate routing/propagation, not sensor calibration.

Retain five native320x288 u16 sources, active origin(7,11), padded stride,
black512/white15360 and fixed noise seeds. Crops are128x128 quads at(7,9) and
(8,10), ISO100 and ISO400 separately. All image signals repeat every256 native
pixels. Fixed integer wave vectors per period: neutral horizontal(46,0),
vertical(0,46), diagonal(37,28); genuine-colour R(37,28), G(46,0), B(-28,37);
coarse neutral(12,9); weak-red horizontal(46,0). Keep the earlier channel phases,
bases and amplitudes, including weak red's2*model-sigma formula and actual warm
WB bits[1070374912,1065353216,1076715520]. Standard WB remains[1.7,1,2.3].
Defocus uses each carrier's actual radial frequency. Neutral/weak source blur
is1.3*abs(frame-2), coarse3.5*abs(frame-2). Varying-focus depth is the fixed
periodic field2+1.8*cos(2*pi*x/256+0.31)+0.2*sin(2*pi*y/256-0.27), followed
by1.3*abs(frame-depth). No plant claims physical PSF calibration or occlusion.

Flat first, then the eight retained scene purposes at every ISO/crop phase.
Score the entire256x256 native image: no trim can remove all complete-depth
boundary effects. The complex transform wraps; actual baseline and smooth5
clamp, and final MHC has its current boundary behavior. A result compares these
complete consumers and cannot isolate wavelets from boundary handling. It does
not establish a natural-image boundary solution. Verify periodic analytic
signal/blur continuity, original CFA/guide identity, live weighting/averaging,
unchanged sources, and observer on/off RGB/plane hashes.

Retain previous independent per-ISO/phase guards: >=5% RGB truth-error benefit
on flat or genuine colour; each structured RGB error <=1.10x baseline;
components recovered>=0.5 by baseline retain>=90% of truth-capped amplitude;
flat RGB/chroma errors <=1.25x baseline. Weak red must have known focused
source2 recovery>=0.5 and own-red positive support, then retain>=90% of that
focused-source truth-capped component. Report unexercised fixtures and do not
admit them. Do not let another ISO or scene compensate for a live failure.

**Additional absolute truth protections, approved before running:** every
nonweak structured component must recover>=0.5 of truth, and its RGB RMSE must
be<=0.70x the analytically known base-only/zero-contrast destroyer's error.
Flat candidate RGB and chroma error must also be no greater than predetermined
single-source error. These prevent poor boundary behavior in the baseline from
making an absolutely poor candidate look acceptable. Keep exact, grey,
half-amplitude and overcontrast metric controls; report quadrature. Error can
reward smoothing and amplitude can reward overcontrast, so neither stands alone.

Passing licenses only the next boundary/composed-gather test. No photographic,
fractional-covariance, optical, production or SOTA claim follows.

