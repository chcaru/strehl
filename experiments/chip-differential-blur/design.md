# One differential-blur discriminator on retained chip CFA

This executes the second still-unexecuted discriminator in
`experiments/quality-september14/joint-photographic-verdict.md`. It is a model
identifiability experiment, not a photographic quality result. The September19
full-context chip correction had a modest local positive verdict; star sand's
lower guide residual did not produce a photographic gain. No generalization
or new renderer is justified by this test.

Inputs: exactly nine existing saved uint16 patches, frames145–153, reference149,
from `joint-raw-samples-2`. Their common target is392x392 native pixels; saved
source margins give varying408–412 extents. The original receipt supplies
source-origin CFA parity, reference-to-source similarity, source-patch hashes,
sensor centre, black/white normalization and pinned source map hash. Existing
independent decoder agreement is retained, not repeated. No RAW file is opened,
no maps written, no full stack rendered, and no photographic array read until
the independent generated controls pass.

Both nested models use the commissioned sigma1.5 native, radius6 normalized
Gaussian on measured green sites and bilinear sampling. Unlike the old pooled
green guide, each guide is built from only G1 or G2. Both have the same fixed
band. At every proposed translation, variable projection re-fits gain and bias;
the second model also fits one coefficient multiplying a fixed five-point
source-guide Laplacian. Translation is re-optimized jointly, never frozen to
the earlier result. Arithmetic guides are f32, coordinate/regression arithmetic
f64 as in the commissioned registrar. No frame-axis filters.

Model: target = gain * source(mapped+delta) + c * Lap(source)(mapped+delta) + bias.
Report beta=c/gain in source-native-pixel-squared units. Negative beta means
the fitted prediction sharpens a more blurred source; positive beta smooths it.
This sign is a local regression interpretation, not a physical PSF measurement.
Translations retain the existing ±4-source-native bound and absolute.02 finite
difference with50 evaluations; no restart or sweep. Source-native delta maps
to delta/a in reference149; inverse observation correction is -delta/a.

Four predeclared choice points: train G1/test G2 and reversed; left/right and
independent top/bottom spatial split. Every grid samples the declared reference
CFA phase at its actual native coordinate. Target margin32, split196 and gap16
give separated original source support after radius6 Gaussian, radius1 Lap,
shift4, derivative.02 and interpolation1. Gain/bias/Lap coefficients fitted on
training are never refitted in spatial holdout. All four choices are reported;
none is selected by its score. Compare both newly fitted shifts with each
historical frozen displacement and report changes in the stated gauge.

Before photographic metrics, independent-controls.py must show positive power
on translation-only, small symmetric blur-only and mixed continuous plants.
Neither flat input nor shifted sign may silently pass. Asymmetric PSF and
unequal-axis blur are outside this one-isotropic-Laplacian model: report their
known model failure, including any invented displacement; never attribute it
to camera motion. The independent reviewer owns those controls and bars.

Fixed refusal/stability rules: nonconvergence, shift within.01 of bound,
nonpositive gain, rank loss or standardized nuisance condition>1e6 refuse;
profiled two-shift Jacobian condition>1e3 or maximum singular value<1e-7 also
refuses motion information (including the straight-edge aperture control);
|beta|>1native px² is outside the small-blur model. Across all four choices,
joint shifts must stay within.25 reference149-native pixel and beta sign must
agree outside a±.02 dead zone. Incremental held-out RMSE must improve at least5%
in every choice to identify extra local blur contribution. Frame145 was already
boundary limited and reference149 is arithmetic identity; both remain reported
but cannot qualify the discriminator. Any eligible instability ends this branch.
No tuning, new maps, RAW rereads or rendering follows a failure.

RMSE can reward smoothing and overfit remaining scene/color mismatch. Separate
spatial and green-phase holdout can reject lack of transfer but does not turn
a lower residual into geometry truth or photographic detail. Coefficient and
shift stability are identifiability checks, not quality scores. No sharpness
metric is used; flat and known out-of-model generated cases are explicit.

Execution: `python -I -B -X faulthandler experiments/chip-differential-blur/run.py --out experiments/chip-differential-blur/run-1`
One owned Windows job:180wall/180CPU seconds,2GiB committed, one numerical
thread. It binds the exact source and helper hashes, command, interpreter,
environment, logs and terminal resource accounting. The result records all
saved-input hashes before/after and zero RAW decodes. Author executes the
parent-authorized measurement; a separate reviewer evaluates its implementation,
independent controls and conclusion. No author-only verification claim.
