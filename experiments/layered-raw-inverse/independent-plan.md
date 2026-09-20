# Independent fixed layered reconstruction utility screen

This plan precedes execution. Root alone runs the model and these controls.
This is an ISO100 generated utility test with known optics and two known ordered
depths. It does not measure camera calibration, unknown-depth recovery, canonical
stacker quality, or SOTA. Failure closes this fixed prototype, not all layered
inverse methods. No optimizer, prior, PSF, threshold, or fixture sweep is allowed.

Use 96x96 original RGGB samples, nine equally spaced focus coordinates 0..1,
near/far inverse depths 1/0, defocus scale12 native pixels and sigma0.7 PSF.
Train on indices [0,1,3,4,5,7,8]. Entire observations 2 and6 are withheld from
initialization, optimization, normalization and baseline/oracle selection.
The true focused near/far observations 8/0 remain in training; heldout foci
0.25/0.75 test intermediate blur rather than removal of every focused view.

**Predata scope amendment:** utility uses known discrete64-ray optics. The
controls independently construct the64 antipodal equal-area pupil coordinates
and supply that identical input geometry to model and independent SciPy forward.
Independent separable Gaussian sampling uses radius ceil(4 sigma). For each ray
it samples premultiplied near radiance alpha*F and alpha at the near coordinate,
samples B at the far coordinate, then forms N+(1-alpha)*B before integrating
over rays and applying the fixed PSF. It never averages visibility separately
from far radiance. Pinhole truth is alpha*F+(1-alpha)*B, without postblur.
All image arithmetic and samples are f32; only scalar scores accumulate in f64.

Generate original CFA u16 through independent Poisson electrons and Gaussian
read noise using the shipped A7C2 ISO100 relation g=100/436.8 DN/electron and
read variance=(4.2*g)^2, black512. Round and censor only at digital16383. The
15360 metadata white is not a censor threshold. The model and generator share
these supplied sensor constants, so this validates an operator, not calibration.

Four fixed cases, in order:

1. Constant flat colour, noise only. Candidate RGB and R-G/B-G RMS <=1.05 of
   the training-CFA mean developed by independent normalized bilinear sampling.
2. Compact far highlight partly behind three real coloured near filaments.
   The highlight reaches actual digital saturation in TRAIN observations on
   valid likelihood support. At least one TRAIN observation must have no
   saturated code anywhere in the protected glint core [39,42,52,55], so the
   positive does not demand inference from only clipped core measurements.
   These liveness checks run before fitting. Alpha, radiances and occluded colour
   are unknown to the fit.
   Whole interior and crossing RGB RMS <=0.95 of the fixed far-only model;
   core/ridge individually <=1.05 of it. Whole/core/ridge RGB <=0.90 of the
   training mean. Independent glint and ridge component amplitudes must each
   recover >=0.8 and >=0.98 of the oracle component recovery capped at1.
   The ridge component uses fixed glint-free native segment [39,31,63,41]
   (half-open bounds), with live template energy in all three colours and the
   half-component destroyer. This avoids crediting blocked glint radiance as
   retained filament detail. The wider ridge/crossing/whole RGB metrics remain.
   Compactness is signed known-component error, not gradient or bright-pixel
   count. Core/fan truth errors and component scores are reported separately.
3. Matched far-only scene, alpha0. Candidate RGB/chroma <=1.05 of the same
   far-only model. This comparator is deliberately restricted to the known far
   depth; it is not an optimized best possible single-depth method.
4. The layered scene with fixed angular illumination: far radiance multiplied
   per ray by 1+0.55*u_x. This breaks the Lambertian radiance assumption while
   leaving pinhole truth at u=0 unchanged. It is a diagnostic destroyer, not a
   requirement that every small mismatch be detected. Heldout failure marks
   this case refused for this screen. The model does not implement an automatic
   adequacy gate, and passing prediction alone never establishes correct layers.

The independent focus oracle chooses one whole RGB donor per output pixel
using training-frame noiseless forward images versus pinhole truth, then copies
the same donor's independently developed noisy CFA RGB. This is a truth-informed
bound with no noise-coupled election, not a deployable algorithm. It receives
neither heldout observation. Mean/oracle error must be nonzero on the positive;
oracle detail is reported, not assumed perfect or an absolute quality ceiling.

Score only the common support margin16, excluding every possible pupil/PSF
boundary dependency. Whole-frame heldout checks score every valid CFA sample,
and each CFA plane plus fixed bright/dim truth subsets separately. Uncensored
residual RMS in units sqrt(g*truth_signal+read_variance+1/12) must be <=1.5
overall and <=1.75 in each nonempty plane/subset. Censored observations are
lower bounds: report one-sided standardized shortfall, never residual to the
ceiling; require RMS shortfall <=2. Empty bright or censored subsets are labelled
absent, not independent confirmations. Prediction metrics can reward a wrong
latent decomposition, so all positive truth/component bars remain binding.

Before optimization, evaluate independent truth latents through actual model64
and independently implemented generator64. Require maximum difference <=0.1DN
on whole/crossing support in the in-family cases. Separately, on the layered
scene at fixed focus indices0/2/4/6/8, compare independent64 versus resolved1024
pupil integration. Report whole/crossing deterministic RMS in supplied sensor
sigma units, with <=0.75 as the physical-adequacy guard. This separate guard
does not prevent discrete utility execution, but blocks real-RAW licensing.
Neither known geometry nor the independent shared64 operator verifies physical
aperture calibration. A same-discrete-operator failure saves its receipt and
stops before optimization or later cases. These choices are fixed before any
execution.

Mechanical controls independently cover constant radiance, alpha0/alpha1,
same-ray visibility noncommutation, original digital-max censor versus15360,
finite inputs and source immutability. An input facade rejects every access to
heldout observations during actual optimization and initialization, with an
explicit illegal-read destroyer. A deliberate heldout-value replacement on the
flat case must also leave optimize=False initialization bit-identical. Full
optimized-history hashes are not compared because timing fields and CUDA
backward accumulation can differ without observation leakage.
Metric commissioning uses exact pinhole truth, half retained component and a
wrong-colour component. No quality result is accepted from metric agreement
alone. Save every case, failed bar, operator adequacy result, source hash and
prediction result; report utility only when every in-family bar passes.

No real RAW files, full stack, geometry fit or photographic replay is used.
