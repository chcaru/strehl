# M194e — joint-pupil two-layer forward-model commission

Allocated in AGENTS.md on 2026-09-07 before dispatch. This is the next bounded
step after M194d's fixed flat-noise benefit, small plane-detail cost and local
truth-error worsening. Author implementation must await committed design and
independent objections. No new quality matrix is authorized by this commission.

## Question and model boundary

Can a small, independently checked geometric renderer preserve foreground
visibility and background radiance at the same pupil sample, integrate sensor
cells, and deliver explicit u16 CFA inputs for the existing production seam?

The M194b one-plane/analytic-color model cannot express this coupling. M25
already has a two-layer compositor; do not rebuild that as a new discovery.
Its separate blurred-layer means omit their joint visibility/background term
on textured scenes. M25's failed real-occlusion and optical-validation gates
remain failed. A new mathematical implementation cannot clear those gates.

Use two ordered fronto-parallel opaque geometric layers, with a declared
foreground mask and complete background radiance. For each sensor-cell sample,
integrate rays across a normalized circular pupil; evaluate both layer
coordinates on the same ray, select the visible layer, then integrate. Define
the coordinate gauge, signed defocus law, pupil density, radiance units and
cell footprint explicitly. Known similarities may map the sensor gauge to
the canonical scene, but must not introduce an alignment-estimation claim or
an aligned-frame volume. Preserve the existing measured curved-track shape
if that track is used. Do not substitute an unexamined linear breathing plant.

This is a geometric, radiance-normalized software model. Diffraction,
aberrations, field-dependent optics, semi-transparent fibers, scattering,
camera-response calibration and real-scene transfer remain outside its claim.
Do not label a geometric pinhole latent as attainable by a real capture.
No adjustment to the M194d weight law, gate, seed or product default.

## Prior art read and binding cautions

Root ran `python experiments/ORCH-drift-check/prior_art.py two layer occlusion
forward model dilution` and read M25's actual `render.py`, M25's measured report
and M87 §26's corrected result. The report search returns M87-occlusion,
M63-bimodality, M79-edof-microscopy-survey, F-camera-lens-optics,
M48-read-noise-measured, M98-gate-adjudication, M90-prnu-noise-model,
M72-green-plane-correlation, V-BLEND-verification and M48c-defect-layer-measured;
the adjacent mentions include ORCH-veiling, G-edof-deconvolution, BUILD-SHARP,
M70-through-focus-spectrum, BUILD-HALO and V-HEADTOHEAD2. Relevance differs:
do not treat a keyword match as a supporting result. The independent bounded
audit at `../m194d-band-admission/next-occlusion-audit.md` supplies the focused
reading and corrected conclusions before final preregistration.

M87 §26 explicitly distinguishes the two-component model from failed depth
propagation and an erroneous arm-ratio gate. The model was not refuted there.
M63 already refutes interpreting focus-curve bimodality as two depths. No
bimodality detector, depth recovery or unmixing method belongs to this task.
M13's depth-step/window lesson motivates a stimulus that can express harm;
it does not validate the optics. M194b's scalar PSF and M25's noise calibration
are not independent ground truth for this new visibility integration.

[Cook, Porter and Carpenter, Distributed Ray Tracing (1984), §3](https://www.cs.cmu.edu/~462/www/lectures/cook84.pdf)
describes integrating lens-area visibility with defocus and explicitly excludes
diffraction. This supports the chosen geometric approximation, not any
implementation or numerical tolerance. The
[ICCP 2021 Depth from Defocus with Learned Optics project](https://www.computationalimaging.org/publications/deepopticsdfd/)
also distinguishes an occlusion-aware approximation from ray-traced reference.
Only primary papers/pages were read; no external source code or model weights.

## Required pre-output decisions and controls

The author proposes an exact small case set, API/schema and numerical method.
The independent reviewer chooses different defensible quadrature/coordinates
and a cheaper analytic oracle. Freeze both before implementation and generation.
State a realizable input that fails each check and demonstrate its power.

Required model controls include a two-ray visibility/background covariance
counterexample; constant-radiance/DC conservation; full foreground and absent
foreground limits; aperture-zero and focused-plane limits; foreground/background
order reversal; signed-defocus behavior; cell integration across a mask edge;
and an asymmetric scene showing that independently averaging mask/background
is a wrong operation. An exact arithmetic identity is DERIVED, not measured
camera evidence. Numerical tolerances must be fixed as engineering error
budgets before evaluating the intended scene, with independent quadrature and
refinement. Failure cannot silently choose a looser tolerance or a new scene.

Bound temporary storage by tiles or samples, and emit one u16 CFA frame at a
time if files are produced. Reuse the existing injected noise/CFA conventions
where applicable, with calibration claims separate from operator tests. Any
new schema must bind actual semantics and frames rather than disguise them as
M194b's different producer. Do not weaken the frozen M194b/M194d consumers.
First commission the geometric/noiseless generator; a compatible production
bridge and a later fixed quality experiment need explicit, independently
reviewed scope. Existing RAWs and holdouts stay untouched.

Root owns integration and disposition. implementation_audit owns the new
producer and author controls; directional_detail owns independent model tests.
No product Rust, Cargo dependency, historical experiment, SYNTHESIS fold,
scorecard or capture change is authorized here. Work remains inside the newly
allocated experiment directory and its eventual report. A bounded negative
result with a retained failure is a completed commission outcome; it is not
permission to tune until the old benchmark wins.
