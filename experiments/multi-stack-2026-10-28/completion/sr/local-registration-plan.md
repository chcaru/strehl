# Local registration evidence after the diagnostic SR ROI

Status: ARGUED design; no local registration measurement has run. The first
cache-only pilot explicitly assumes 0.10 sensor-pixel uncertainty and cannot
establish that the native map is accurate enough for a new output lattice.

## Observations and independent checks

Keep the saved global placements frozen. Select spatial measurement patches
inside the authorized <=384-sensor-pixel rectangle, excluding the native global
alignment tile footprints where feasible. Record the actual overlap; merely
moving a tile centre is not independent evidence. Use original green photosites,
retaining the two Bayer green offsets. A cropped patch keeps its full sensor
origin and the original map centre, so crop recentering cannot create an apparent
placement correction.

Build a direct local edge graph among original sources admitted by the whole-track
focus evidence. Include within-pass and cross-pass edges, cycles, and more than one
neighbor per source. Do not chain corrections or infer per-source quality solely
from an end-to-end image. Refuse sources disconnected from the diagnostic anchor.
Report graph components/cycle rank and every edge refusal.

Use one disjoint set of original spatial patches to estimate each local residual
pull and another to score it. Repeat with the roles swapped. G1/G2 separation can
provide an additional noise-independent witness, but they remain two sampling
sites of one acquisition; their physical offset and different local signal must
be included. Do not count them as independent frames or present them as identical
images. The target guide is fixed before the held-out samples are scored.

Each held-out pair yields a displacement vector at its actual full-grid location.
Express errors in the anchor sensor lattice: factor two from guide pixels, with
explicit source/anchor Jacobian. Report signed bias, robust spread, direction and
structure/curvature conditioning; a scalar RMS can hide an aperture problem.
A pair-fit residual is not automatically a per-source uncertainty. Per-source
bounds require the direct graph, an explicit gauge, leave-patch-out checks and
cycle consistency. The first usable gate should be a conservative policy bound,
labelled as such, unless statistical coverage is validated by the controls below.

Green geometry alone does not certify red/blue channel placement. The production
radial-only optical profile has calibration residuals, especially in blue. Test
raw same-color held-out predictions with optics off/radial-only and include
profile uncertainty in per-color admission; never treat an assumed green bound
as a measured RGB bound.

## Controls before using the gate

Run flat/noise first: zero contrast and one-dimensional edges must fail the
2D registration-information gate, even if a fitted scalar displacement looks
precise. Inject the calibrated sensor model, fixed geometry and independently
formed original-CFA samples. Vary signal and noise independently.

Use independently generated 2D texture with measured curved scale/rotation
trajectories. Plant fractional translations at integer, quarter and half CFA
phases. Score the predicted displacement and nominal bound against known truth;
repeat with the map biased by 0.10,0.25,0.50 sensor pixels, wrong origin/parity,
shuffled source assignment, clipped taps, defocus mismatch and a moving edge.
A gate that accepts a wrong map because both measurement and score shared one
interpolation is a failed instrument. Include a second interpolation or direct
sample-domain held-out residual as a causal witness, and report phase dependence.

Fit and score separate patches; rerun role exchange. The noise bound uses the
injected model and exact operator transfer, not variance fitted from target
residuals. Residual structure is a separate model-mismatch term. A low residual
from blurring away texture is not a registration improvement: preserve truth
transfer and reject the optical-lowpass/null arm as evidence of sampling gain.

## Held-out photographic prediction and next output

For the existing insect sources, predict withheld original photosites from the
candidate and from the same-count no-SR arm. Match their color, exposure, sensor
pixel aperture and noise normalization. Use held-out acquisition(s) excluded
from the reconstruction and guide where possible; a source already used to
choose focus or tune parameters is not a clean final validation set. Separate
bias/edge residual from expected temporal noise. This is consistency evidence,
not truth, because nearby acquisition focus/motion can differ.

Only after these diagnostics should the ROI use measured registration admission.
Retain the native fallback exactly where local phase, focus, motion or geometry
fails; report how much of each color actually reconstructed. The current native
master has unknown propagated variance, so no relative temporal gain can be
claimed from it. A favorable small ROI does not replace complete full-resolution
photographs and independent review with a common display transform.
