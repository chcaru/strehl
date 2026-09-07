# Independent check of the corrected quality plan

2026-09-07. **DERIVED / source review; no model or product execution.**
Reviewed `next-quality-design.md` SHA256
`d526a571b30b820c2be03da88cf87ee393c405d38c74ef5873853bb1131d48da`
against Curie's `next-quality-independent-review.md` SHA256
`27ae8ce832722b236d40e1f11502155995fcfb8119894f8b8cb8ace035b00db0`.
The corrections are defensible design requirements. They admit no quality
population and do not change the retained M194g cost refusal or release gates.

## A different support choice confirms the distinction

I read the actual `F_G/F_H/F_V/F_X` taps and `demosaic_malvar_row` in
`crates/strehl-core/src/demosaic.rs`, source SHA256
`425d6889485011cf6f2aaf57b0b873f15fd6ee3250853f3ba5f6540b496b3810`.
All nonzero taps lie in the radius2 diamond. Its support for n=(1,-.15) is2.
A separately chosen, simpler5x5 square enclosure gives2.3 instead. Both are
conservative, but the square is looser; there is no requirement to discard
sites unnecessarily once the actual diamond support is established.

**Independent companion:** native(149,106), inside the proposed window, has
h=-8.9. The diamond's maximum foreground-intersection height at endpoint0 is
`-8.9+.575+2+6*sqrt(1.0225)<0`. Thus the corrected background mask admits it.
The square enclosure instead gives
`-8.9+.575+2.3+6*sqrt(1.0225)>0` and conservatively excludes it. This re-chosen
case distinguishes a genuinely sufficient tighter support from a convenient
bounding box without measuring radiance. Use it as a prospective valid
companion to the retained invalid(150,110), h=-8.5 case. It is not a proposal
to select masks from output errors.

I also checked `BandMerge::finish`: its final level0 InputRange clamp is
two-sided. The `hull_low_only`, lambda and starting-level options affect the
separate per-level clamp, not that final point-hull preservation. Hence the
single-input support reduction is reasonable **conditional on actual finite
single-input identity, unchanged gathered CFA values, final bounded hull and
disabled CA**. Record these in the actual plan and retain a nontrivial identity
fixture; the enum name alone is not an end-to-end proof. Nonidentity gathering
requires new mapped dependencies, as the correction already says.

The endpoint4 threshold2.575 and endpoint0 threshold approximately8.6421 are
specific to their own focused observations. Neither establishes pure-layer
dependence for the five-frame merge. The separate74-native border guard is
also not such a proof; its per-axis enclosure contributes85.1 mask-height
units, and beta still depends on the full analysis domain. The corrected
wording properly keeps all three statements separate.

## Readouts and remaining specification work

The K0 target correctly retains coupled within-cell visibility. The endpoint
TIFFs remain observed reconstructions, with MHC/quantization error, rather than
an attainable whole-scene lower bound. Freeze the same-centre ideal RGB
definition using actual represented f32 WB before scoring. Explicitly name
whether each surface mask is the outside-band mask, endpoint visibility mask,
or their intersection; the draft correctly distinguishes their purposes but
the eventual implementation needs exact Boolean definitions and native offsets.

The intercept plus joint two-wave sine/cosine regression and phase, amplitude,
flat and extra-wave controls are appropriate. One additional algebraic
counterexample explains why residual error must remain: with fixed design
matrix X and any vector v outside its span, set `r=(I-X*X^+)*v`. Adding a
nonzero multiple of r to the target leaves all fitted coefficients unchanged
while increasing common-target error. A fixed third-wave candidate such as
frequency(.117,.053), phase.29 can supply v in a later instrument control;
require its projected residual actually to be nonzero before claiming power.
This is a prospective scorer destroyer, not a new output or tuned image.
Rank/condition thresholds, residual norm and comparison tolerances still need
explicit values before the scorer is commissioned. No gain/phase fit may
subsequently remove a target error.

The eight-repeat decomposition is correct with sample variance s² using
denominator7: `MSE=mean(error)^2+7*s²/8`, so
`[mean(error)^2-s²/8]+s²=MSE`. Its equality is arithmetic, not corroboration;
negative unbiased squared-bias estimates must remain visible. Paired repeat
differences and deletion of whole repeats preserve dependence better than
treating pixels as independent draws. The corrected supplied-noise order,
per-CFA-parity moments and quantization caveats are consistent with that scope.

No further support correction blocks the later registration. Exact masks,
actual identity/hull prerequisites, scorer rank/power controls and fixed target
definitions remain required before any of the proposed38 TIFFs is generated
or scored. The present review used only source/document reads and this new
`next-*` file; it changes no bound geometry source, model, output or bar.
