# Independent phase-aware reconstruction test — frozen before execution

Root executes; this author does not. This is a new synthetic information-path test,
not an admission of any previous inverse, a camera calibration, or a real photograph.
Only flat and the retained coloured foreground/compact far highlight scene are used.

The eight source identities are 146..153, with 147/151 withheld completely from
initialization, objective, stopping and baseline selection. Synthetic foci are k/7,
not measured depths. Common translations are independently recomputed from the
original f64 warp bits and native source corrections at (1527.5,1299.5), checked
against the saved corrected-eight centre rows, then t=-centered_mod2(d-d149).
No per-colour phase selection, scale division or affine derivative is retained.
The 96-square plant centre differs by the even native offset (1480,1252), preserving
RGGB parity. Frame149 has exactly zero translation and identical original u16
codes/noise in the two geometries. Both fitted sheets start from that same observed
training CFA interpolation and alpha .5. There is no old checkpoint or oracle mask.

`commission --out` checks independently enumerated bilinear same-ray sampling,
translation sign, fractional diagonal products, coverage endpoints, and dense
translated forward/adjoint against independently written grid_sample integration.
The quarter-diagonal cancellation control uses alpha0 so pure far translation is
valid at the zero-padded boundary, and asserts that both separate Nyquist-axis
modes remain visible while their difference cancels; x-only translation breaks
that cancellation. The finite-difference directions are fixed smooth whole-field
perturbations with explicit rejection of zero and doubled derivatives at the same
tolerance. Thus tiny individual-pixel derivatives cannot make this check vacuous.
The dense first-adjoint reference accumulates gradients over <=1024-ray chunks;
it never creates a 16384-ray graph. Full forward tolerance is .1 DN, gradient
relative L2 <=3e-4 and maximum <=1e-5+3e-4*reference maximum, inherited from the
commissioned stencil. A literal finite-difference witness is separate. The old
once-PSF component/double-PSF/half-colour instrument is retained unchanged.

`generate --out` uses an independently assembled 128x128 polar pupil at angular
phase .60; the fitter uses the prospectively fixed phase .23 at the same density.
This is finite-quadrature re-choice, not continuum truth. At all eight foci and
both geometries, original-noise normalized discrepancy must be <=.75 on the
whole supported region and crossing. A failure records refusal before any fit.
Images are f32, original observations u16 with black512/digital censor16383;
coordinate/table setup and scalar diagnostics may use f64. Original injected
Poisson/read noise is reused without calibration claims. Expected images and truth
live only in the evaluator subtree; the fit manifest names only pristine CFA,
configuration, pupil and geometry. No aligned RAW is created for likelihood.

Observed comparisons use only the six training frames: independently develop each
CFA, inverse-translate its RGB by -t into reference coordinates, then average.
An explicitly labelled oracle bound chooses among those training observations
using their noiseless registered RGB error to the once-PSF target and pastes the
corresponding noisy developed values. It is not an automatic selector, and neither
baseline is passed to the fitter. They already contain the optical PSF and are not
filtered again. The independent full96 PSF is applied once to truth/templates and
latent reconstructions, before the unchanged supported [16:80,16:80] scoring.
The mean is accumulated in fixed source order in f32; oracle ties retain the first
training source. Only the current RGB frame, mean sum and current donor are held.

Root runs exactly two flat fits first. `score --data --fits --case flat --out`
returns `continue_layered` only if phase RGB/chroma <=1.05 its training mean,
same-budget identity, and retained fixed-alpha visibility, with both original
withheld predictive bars passed. If false, the three layered fits remain unrun.
Otherwise root runs phase, identity and deliberately wrong-zero-phase layered
fits. All are fresh160 cosine-Adam + the same bounded1000-step LBFGS budget;
fixed final outputs are scored regardless of nonstationarity, reported separately.

Layered phase retains all prior absolute in-focus bars: .90 mean whole/core/ridge,
.95 far-only whole/crossing and1.05 core/ridge; core/ridge RGB AND chroma <=1.02
retained fixed-alpha visibility; per-colour glint and glint-free ridge component
recovery >=.8, >=.98 capped training-donor and retained-visibility recovery.
The retained references are from different nine-frame/64-pupil observations and
are explicitly nonmatched constraints, not a causal comparison. Additionally,
core/ridge RGB/chroma <=1.02 same-budget identity, components >=.98 capped identity,
and whole RGB AND chroma <=.95 identity are required for a useful phase gain.
The wrong-phase arm must fail at least one fixed image or withheld guard; if not,
this screen cannot attribute an improvement to the supplied sampling geometry.
Withheld original-code bars remain whole1.5sigma, CFA/bright/dim1.75sigma,
one-sided censor2sigma. No alpha accuracy, gradient energy, rank or residual alone
can admit a reconstruction. Flat failure cannot be averaged away by layered gain.

Source and generated-file hashes, exact initializer/parameter hashes, training-only
read indices, final state/prediction/image receipts and input immutability are
checked. Controls never fit, tune a threshold, choose an iteration, or decode RAW.
Per-process wrapper caps:8GiB committed, commission/generation120s each,
fit600s each, scoring60s; maximum five conditional fits. CUDA allocated/reserved
are recorded separately. New data/foci/phase/initialization change the task: even
a pass permits only this bounded route's next real-data feasibility decision.

Instrument repair after preserved commissions1/2 (commits3f24b149/e5df5216):
the diagnostic isolated the refusal to the physical-alpha finite difference;
near/far directions passed. Root and the independent reviewer authorize only its
step .001 -> .25, retaining the direction, AD, tolerance and zero/doubled-gradient
destroyers. With both radiance sheets fixed, this tested same-ray forward, common
PSF and cotangent are affine in physical alpha: the larger symmetric step has no
real-arithmetic truncation error. There is no sigmoid, likelihood or prior in this
FD path. Actual perturbed alpha is asserted finite and within [0,1] before each
evaluation (the declared range is bounded by [.09,.86]). F32 subtraction error is
a plausible explanation for the small-step disagreement, not a proven cause or a
passing result. No generated observations, fits, model or quality bars changed.
