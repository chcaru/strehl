# Independent native spectral decision

2026-10-27. **DERIVED / ARGUED; no implementation or numerical execution.**
Reviewed design checkpoint `4b60313a4a905de3d846967da20244cd97c981c25bd6ac22871b59e8c38bbc63`
and the actual inverse, shared-color, direct-pixel and dual-tree failure reports.

**Allow a bounded implementation decision, followed promptly by an actual
photographic diagnostic if mechanics and measured cost permit.** This is a
defined interpolation-and-fusion operator, not a nonuniform projection being
mistaken for an inverse. It has a plausible native value path: original scalar
CFA samples, four reconstructed CFA components, then one final demosaic. It
does not fit a lens PSF, recover arbitrary aliases, or improve the held geometry.
Known color/depth adverses should remain visible; they do not logically forbid
one complete observation. No quality admission follows from this review.

## Quantities that must be frozen before code execution

The proposed green lattice is coherent: `x=u+v+1, y=u-v`, with native frequency
`fx=(fu+fv)/2, fy=(fu-fv)/2`. A physical affine pull acts in native coordinates,
not in either lattice's index units. R/B origins, green integer lattice origins,
their rounding rule, patch-local offsets and the held map's center convention
must be explicit. Do not insert a half-pixel correction from a different image
library. Both greens come from the same reconstructed green field; their
distinct physical sites must survive later Fourier packing.

For a declared source-cell-average Fourier mode at native frequency f and
reference-to-source derivative A, the stated ratio
`sinc(A^T f)_x*sinc(A^T f)_y / (sinc(f_x)*sinc(f_y))` is the appropriate
reference-cell/source-cell factor. Identity gives one. It is not a calibrated
Sony aperture or an inverse of defocus. Applying it to the tapered finite
interpolant is a model choice. Test a nonunit rotated similarity against an
independent continuous integrated mode; omitting the ratio must fail that
comparison, rather than a reference that repeats the same ratio code.

Symmetric splitting of even-size Nyquist terms before the ratio is necessary:
affine rotation can give different factors to signed edge representatives.
Unitary 4x two-dimensional padding needs the declared amplitude factor four.
The 16-node evaluator must handle exact integer nodes without a singular
division. Direct Fourier summation commissions the approximation, while
continuous truth separately exposes finite-window/model error. These are
different tests, neither of which proves photographic sharpness.

Complete patch enumeration is still a source contract to pin. A periodic Hann
window starting at output origin zero gives zero weight on the outer row and
column. Include the predeclared negative-origin/partial edge patches and assert
strictly positive accumulated weight at every delivered sensel. Record exact
patch count, edge clipping and normalization. Native even reflection must
preserve CFA parity; reflected occurrences and overlapping patches must use the
same absolute original-sensel probe value. Reflection is a boundary model, not
additional measured support. A missing-edge-patch and wrong-green-origin foil
should fail the actual producing coverage/null checks.

## Shared weights do not remove all depth conflicts

Per-frequency normalization avoids the old inverse's unbounded cross-level
objective dominance and allows genuinely different frequencies to choose
different source mixtures. This is a meaningful distinction from one scalar
weight on a whole source value. Nevertheless, a quad-frequency bin represents
multiple physical frequencies. For example, red detail at 0.20 native
cycles/pixel and green detail at 0.30 fold to the same conjugate pair at
0.40 cycles/quad pixel. Their different physical phase relations preserve
information, but one common scalar weight cannot independently retain each
from a different focus source. The quincunx interpolant does not resolve this
admission conflict.

Use that concrete collision within the planned independent-color/mixed-depth
screen, alongside a separable-frequency positive. The known red cancellation
case is also essential: the blurrier source can have more aliased energy.
Preserve sign-inverted defocus, crossing/glint and window-mismatch outputs even
when the recipe accepts them. No universal visibility guard is claimed. The
earlier shared-color blue loss and full dual-tree failure prevent interpreting
larger spectral energy or lower aggregate error as an insect-detail guarantee.

The [primary FBA paper](https://dev.ipol.im/~mdelbra/fba/FBA_cvpr2015_preprint.pdf)
supports magnitude-weighted fusion of registered motion-blurred images. Its
convolution model does not establish this CFA/focus/visibility adaptation.
Only the primary paper was consulted; no external implementation was read.

## Noise and cost: a practical release, not an idealized budget

Eight independent noise-pair differences summed and divided by sixteen give
the stated marginal variance estimator for this fixed linear consumer. Shared
original draws must pass through both means, source taper, cell ratio, affine
evaluation and output window. The expected sum of four normalized powers does
not require independence of those components; interpreting that sum as four
independent observations or a likelihood would be wrong. Probe-estimated V is
itself noisy and appears in a denominator. Consequently `E-2F` is neither an
unbiased signal estimator nor a guarantee against noise admission, especially
across299 opportunities. The fallback mean is used only when every source's
score is zero; it does not protect flats once noise has produced positive scores.

Flats must therefore pass through the actual final CFA/MHC writer first. Retain
output RGB/chroma error and an independent acquisition-noise comparison with
the supplied model and uniform arm. The same random V used by admission cannot
validate its own output noise. Conditional linear propagation is not complete
variance of the data-dependent selector. Do not impose the previously rejected
minimum-variance DC ceiling or relabel smoothed-away structure as denoising.

Sixteen probes are a proposed accuracy/cost choice, not a repository invariant.
They are not guaranteed sufficient, and they must not be called mandatory for
all valid estimators. With the current choice, a single patch's padded R/B/G
complex arrays contain roughly1.57million elements, or12.6MB before other
scratch. About8,000 patches times17 signal/probe instances already means about
1.7TB of padded-array output writes per source, ignoring repeated FFT passes,
evaluation and reads. This is a derived work-volume warning, not measured GPU
traffic or a runtime prediction. Global accumulators of roughly2.2GB are not
the dominant work estimate.

First time a fixed small real-map batch containing interior and boundary patches
through **all** signal/probe transforms, evaluation, floor and accumulation.
Use exact full patch counts and disclosed batching to reject obvious cost
infeasibility early. If plausible, run the complete one-source checkpoint with
all probes and finish/output costs before scheduling299. Do not extrapolate an
FFT-only kernel. A smaller probe count selected and frozen before execution is
a legitimate design change with a noisier-floor tradeoff; changing the injected
noise model or silently dropping propagation is not. No post-image sweep is
proposed.

The decisive outputs are complete candidate, uniform and unchanged native
baseline with common map/crop/development and the ten fixed native witnesses.
Uniform weights must reproduce the declared gathered-patch mean through the
actual overlap-add path; this is a producer null, not truth. All complete
images, flat/color/depth failures and operational costs remain reportable even
if the candidate looks sharper locally. A usable broad photographic gain, or
a clear complete-image null/regression, should close this bounded decision;
do not extend it into a synthetic-only optimization program.
