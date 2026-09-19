# Independent two-level all-CFA screen

Fixed before execution. Root builds/runs; the author does not validate the
implementation. The candidate sums four separate complex coefficient energies
and injected variances after squared as-shot WB gains, then applies the fixed
smooth5/gate2/production SoftPower at each of two levels. One weight serves all
four colour coefficients. Mean deepest LL and fallback, InputRange and current
MHC remain. Compare with actual BandWorker bands=2. Identity generated u16 only;
neither fractional covariance nor the seven-band product is tested.

First commission full two-level complex reconstruction on a rectangular 12x16
field: asymmetric complex input, constant, impulses at all four decimation
residues including wrapped corners, and a cyclic shift of one input quad.
Require maximum error <=2e-5*max(1,input magnitude). Do not require coefficients
or merged images to be invariant under a one-quad phase change. For a fixed
heteroscedastic field, sum every original-pixel forward impulse response's
squared complex magnitude times that original variance. Compare the complete
packed variance with tolerance2e-5*max(1,expected). The composed effective
six-tap/two-level filter spans16 source positions, so width12 forces periodic
path collisions. Check a one-quad shifted variance field too. A deliberately
wrong oracle recursively filters scalar LL variances; it must disagree by
>1e-4 at a deepest-level coefficient. This makes loss of complex correlation
detectable. Shared injected constants validate the operator, not calibration.

Reuse five native320x288 u16 sources, active origin(7,11), padded stride,
black512/white15360, and existing truth/noise seeds. Use quad crop144x124 at
(7,9) and (8,10) separately, ISO100 and ISO400 separately. Trim56 native pixels
(28 quads) on every side. Two-level analysis reaches4q-9..4q+6; smooth5 adds
8 source quads, and composed synthesis permits4q in output-6..output+9.
Thus dependency is at most23 quads plus final-MHC1, inside the fixed trim.

Eight fixed scenes, flat first at each ISO and phase: original flat0.30;
horizontal, vertical and diagonal neutral0.18 waves; retained genuine-colour
0.18 equal-focus and spatially varying-focus scenes; coarse neutral0.06 wave
with source blur sigma=3.5*abs(frame-2); weak red-only0.18 horizontal wave with
sigma=1.3*abs(frame-2), constant green/blue0.30. Original axis/diagonal phases,
colour phases, bases and amplitudes stay fixed. Standard scenes retain
WB[1.7,1,2.3]. Weak red uses actual retained warm-capture WB bits
[1070374912,1065353216,1076715520] from the vitamin-C full-adapter receipt scope.
Its truth amplitude is exactly twice injected red single-site sigma at its
0.30 base, converted through that WB to normalized camera units. This formula
is fixed; no observed variance fit, amplitude sweep or post-result rescue.

Require exact original-CFA/identity-green agreement, unchanged original
buffers and finite outputs. Verify actual weighted participation and mean
fallback. Ideal axis structure must remain confined to its one active
orientation at both levels; diagonal activates multiple directions. Coarse
ideal level1 detail energy must exceed level0 and actual level1 weighting must
occur. The varying-focus baseline must actually select and use distinct guides.
If a feasibility fixture is unexercised, report it and do not admit the rule.
An additional one-source mapping witness supplies distinct synthetic noise
gains in the authority's [R,G1,B,G2] order and independently checks the actual
stored [R,G1,G2,B] variance hashes. This tests routing, not camera calibration.

Retain all prior guards independently for every ISO and crop phase: benefit
requires >=5% RGB truth-error reduction on flat or a genuine-colour scene;
each structured RGB error <=1.10 times baseline; each component recovered>=0.5
by baseline retains>=90% of truth-capped in-phase amplitude; flat RGB/chroma
truth-error RMS <=1.25 times baseline. Report quadrature and cases separately.
Flat original-CFA mean and a predetermined single source are descriptive
placebos, never sharpness scores. Retain exact, grey, half-amplitude and
overcontrast metric destroyers.

**Additional pre-run failure test for this changed evidence path:** on weak
red, the predetermined focused source2 must recover>=0.5 of red truth and
the actual red-only diagnostic weight must have positive support. Candidate
red must retain>=90% of that focused source's truth-capped red component,
even if the green-guided baseline is blind. Keep all flat/RGB guards too.
Count red-positive but aggregate-zero coefficients where available to expose
aggregate-floor suppression directly. This is not a retroactive alteration of
the earlier experiment. The single-source witness is not elected by noisy
argmax and is not an alternate candidate. No clipping safety is inferred.
On ISO100 weak red at the original crop, disabling only the diagnostic
own-plane counters must leave both RGB outputs and all eight collapsed CFA
planes bit-exact by SHA256; disabled counters must actually be zero.

A pass permits only the next composed-gather check; no photograph, original
RAW run, optical claim, parameter tuning or production promotion is admitted.
