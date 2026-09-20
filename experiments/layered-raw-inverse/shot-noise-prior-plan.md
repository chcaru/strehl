# One shot-noise-scaled sheet prior, fixed visibility

Prospective; no author execution. Keep every prior source/result frozen. Only
the image prior changes: for each neighboring native RGB sheet pair S1/S2 in DN,
use `delta_h=sqrt(2)*(S2-S1)/(sqrt(g*S2+c)+sqrt(g*S1+c))`, where g is the supplied
gain and `c=read_variance+1/12`. Apply the same vector Huber transition2, mean
over each direction, mean over directions/sheets, and coefficient1. Keep all
derivatives through the denominator; no latent-noise estimate or detach.

This is the difference of `h(S)=sqrt(2)/g*sqrt(g*S+c)` in a cancellation-safe
form. Locally at2048DN its derivative is the old inverse gradient scale.
Convert the existing1e-12DN-squared norm safeguard by the old reference scale
squared, `2*(g*2048+c)`, to dimensionless units. Constant fields retain zero
image-prior gradient (a negligible positive norm floor), with no new constant.
Original alpha TV .02, binary .002 and normalized sheet L2 .0001 remain exactly
the same arithmetic/averages. Likelihood, supplied noise, censor threshold,
optics, CFA and supported interior remain unchanged.

Pure independent seams: `image_huber_dn(image,gain,read_variance)`,
`shot_image_prior(state,config)` and `selected_prior(state,config)`; module.model
is the frozen implementation. A ducktyped state supplies normalized `fields()`,
dn_scale and far (None for one layer); config supplies gain/read_variance.
Commission constant fields, small differences around2048, literal h-difference
and derivative agreement, and a bright-offset edge. The latter must expose
that a common brightness lift lowers the penalty for unchanged contrast.
That incentive is a risk, not a defect to hide by stopping denominator gradients.
Data and unchanged sheet L2 must constrain it. Frozen observed-DN scales are
not another tested arm: blurred/censored mixtures do not directly specify the
latent sheets' signal levels.

Fit only flat and layered with the same original screen160 near/far parameters
and identical visibility-1 exported alpha. Compare hashes/config to the retained
visibility-1 baseline receipt before fitting. Alpha remains a buffer and only
near/far parameters receive gradients. Initial sheets must match exactly; save
the fixed-alpha initial reconstruction. The original sheet-prior baseline is
the retained visibility-1 result; do not rerun or choose among baselines.

Solver remains one L-BFGS per arm: lr1,1000iterations,1400 nominal evaluations,
history10, gradient1e-6, change1e-11, strong-Wolfe, actual hardcap1800 including
initial/final monitors. Same framewise backward accumulation, original training
indices/facade, logical-value-preserving contiguous gradients, progress100 and
final raw-parameter stationarity interpretation. No restart, sweep, radiance
cap, opacity clamp, truth-dependent stopping or new optics. Root owns execution
and external immutable bindings; per-arm receipts also check their inputs.

Independent scoring retains flat/truth/components/held-prediction guards and
compares with visibility-1, including brightness/overshoot inspection. A smaller
prior or objective alone cannot establish quality. Numerical nonstationarity
and failed continuum optics remain explicit; even a positive known-alpha test
is not an automatic opacity estimator or real-RAW license.

CLI: `python shot-noise-prior.py --source screen-1/output --alpha-root visibility-1/alpha
--out <directory>`. Same `<case>/fixed-alpha` arrays, state, initial reconstruction,
held-index2/6 predictions and receipt schema as visibility-oracle; prior_kind is
`shot-noise-stabilized-sheets`. All held predictions are exported after fitting.
Only two fits; no original camera RAW or full-image rendering.
