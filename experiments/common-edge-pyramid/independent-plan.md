# Independent fixed-basis screen

Prospective choices, before execution. This tests one common guide-dependent
analysis/synthesis pair, with the existing Gaussian-basis canonical source
weights held as decisions. Those weights and their old injected-noise floor do
not become calibrated significance tests for the new coefficients. The new
terminal band is averaged. No source selector, learned image, RAW experiment,
parameter sweep or production promotion is included.

Reuse the original-u16 learned-band-guide fixture generator and its fixed
truth/component scorer. Execute flats first: held-flat-n5 and held-flat-n9 at
ISO100, then train-flat-1 at ISO400. Follow with the existing held CurvedN9,
ThinN5, unclipped GlintN5, ClippedN5 and ColourN5. These eight cases are known
development fixtures, not fresh validation or calibrated optics. The same
injected shot/read model generates and is consumed by the data; this cannot
validate its camera calibration.

The fixed deployable candidate uses canonical merged mean-green as its common
guide. Independently retain a constant-guide null, the same canonical guide
displaced by (+7,-5) quad pixels with clamped addressing, and the arithmetic
temporal mean of gathered green. The temporal mean is a practical alternative
guide chosen without a focus selector or target. An additional truth-green
guide is diagnostic only: average each output-native 2x2 truth-green block and
multiply by the sensor range. It must never enter the canonical candidate,
weights or source noise. A better truth-guide result cannot qualify the actual
guide. A spatial basis cannot be required to remove glare present identically
in every original; the reused cases contain distinct focus responses.

The actual consumer must preserve every old per-source weight, source/gather
and injected-noise identity between passes. On the first flat and Thin cases,
a diagnostics-emission-disabled rerun must produce bit-identical complete
CFA/RGB for every arm; mandatory internal integrity checks remain enabled.
Separately, an ordinary single-pass BandWorker with no new field/hash/guide
extraction must match the instrumented canonical output exactly. This is
generated observer identity, not a full RAW observer-off photograph claim.
Constant-guide analysis/synthesis has the old Gaussian algebra, but arithmetic
order can differ: compare its final CFA/RGB within .02 DN / 5e-6 normalized
camera-RGB, rather than claim byte identity. New-basis uniform memberships
must agree with direct arithmetic source averaging within .02 DN; no old-base
substitution is allowed to make the property pass.

Pure operator controls cover even/odd 80x72 and 81x73 quad domains with three
AC levels, and 1024x1024 and 1031x1029 domains with seven AC levels. Use finite
high-DN signals, constants, impulses and a displaced step guide. Matched
analysis/synthesis must recover input within .02 DN max absolute error. This
is a fixed f32 numerical allowance, not an interval-certified guarantee.
Independently enumerate small R/E supports in f64, including duplicated
clamped-border taps and parity-specific expansion. A missing band, mismatched
guide in synthesis, and wrong boundary/parity must be live destroyers. Shared
uniform source memberships must commute with averaging up to declared f32
rounding; this tests a linear operator once its guide is frozen. Unequal AC
memberships do not weight terminal DC: unequal constant sources must retain
their unweighted terminal mean rather than a weighted source mean.
Also use a false 1000/9000-DN guide step on a constant 5000-DN source. The
matched reconstruction must remain constant within .02 DN: a copied guide
edge is a failure, not recovered structure. This adds no photographic case.

Score complete final camera RGB, with the unchanged old fixed windows and
independent truth decomposition. RGB, green and chroma RMSE protect against
noise, offsets and overshoot; centered signed component recovery protects
against smoothing or colour removal that improves those errors. Neither is
alone a quality metric: projections can credit correlated artifacts and
ignore offsets, while lower error can reward erased detail.

Nomination bars are flat errors <=1.10 times both canonical and uniform;
structured errors <=1.10 canonical; every eligible canonical component
(reference recovery >=.5 and existing template/conditioning rules) must keep
>=90% of capped reference recovery. Both fixed Curved and Thin positive windows
require >=5% RGB-error improvement over canonical. Record all arm errors and
all nuisance-guide differences, not just the conjunction. Preserve unavailable
components and unexercised positives as such. Perfect truth must pass this
exact scorer; erased near/far, erased glint/colour, and independently added
flat noise must reject on their same paths. An oracle or a constant-guide null
cannot nominate the canonical-guide recipe.
For the displaced and temporal-mean guides, predeclare harmful guide lock-in
when any original fixed structured window exceeds the same 10% error or 90%
eligible-component guard relative to canonical. Report those failures per arm
separately from actual-guide nomination. The unchanged whole/Curved/Thin
windows include the displacement region; do not recenter around a measured
artifact. Any extra visible edge absent from known truth must be reported as
a failure, even if aggregated error happened to improve.

The screen can nominate a separately reviewed complete photograph only.
Seven-band numerical reconstruction is not seven-band occlusion validation;
the compact physical cases carry the latter limited evidence. Any failure
closes this fixed recipe without bandwidth, guide-offset or threshold rescue.
