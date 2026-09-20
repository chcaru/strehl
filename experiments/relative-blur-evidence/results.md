# Relative-blur evidence: no photographic admission

The fixed generated model-adequacy screen passes. The separate actual-source
check does not justify source ownership or another complete render. This is
not an image-quality improvement. Product defaults remain unchanged.

Commands run from the repository root with Python3.12:

```
python -B -X faulthandler experiments/relative-blur-evidence/smoke.py
python -I -B -X faulthandler experiments/relative-blur-evidence/screen-run.py --out experiments/relative-blur-evidence/controls-1
python -I -B experiments/relative-blur-evidence/witness-run.py build --out experiments/relative-blur-evidence/build-1
python -I -B -X faulthandler experiments/relative-blur-evidence/witness-run.py export --build experiments/relative-blur-evidence/build-1 --out experiments/relative-blur-evidence/witness-1
python -I -B -X faulthandler experiments/relative-blur-evidence/real-run.py --witness experiments/relative-blur-evidence/witness-1 --out experiments/relative-blur-evidence/real-1
```

The author supplied the model; another agent authored the falsification
fixtures and independently reviewed results. Root ran the listed commands.
The reviewer also ran the separately bound four-seed flat test; its exact
command, process and unchanged-model bindings are in flat-stress-1.

MEASURED: the independent screen completed in9.453s with20 records. It fits
the known Gaussian positive on separate training features and predicts its
held-out glint to at most0.000113DN RMS. The different-depth crossing is
refused, with138–893DN per-plane errors; its no-glint twin remains refused.
The supplied5DN plane-noise positives, reversed directions, coloured fan,
gain-only and clipping controls behave as preregistered. These tests validate
an operator within their plants, not sensor calibration, native gather
covariance, or optical adequacy on photographs.

MEASURED: exact flat and identical structured inputs remain ambiguous. Of the
first two noisy-flat pairs, one is compatible both ways and one reaches the
sigma ceiling both ways. Four further independently chosen seeds are compatible
both ways. No false exclusive direction was reproduced in these six pairs;
this is not a probability bound or permission to interpret numerical refusal
as the losing direction. See results-review.md. A solver failure, insufficient
apron or bound hit leaves the direction unknown.

VERIFIED: the test-only source exporter freshly compiled strehl-cli in129.844s
and exported four original sources in3.484s. It consumes the actual full-domain
GPU MHC/Catmull/CA rounded gather. Every source's complete known4, original
active-u16, guide, injected variance and beta match retained consumer evidence.
All eight old192-square windows are byte-identical within their wider512-square
exports. Original metadata/map and gathered values remain unchanged. The export
contains measurements, not complete candidate photographs. Exported guide
variance must not be substituted for four-plane/spatial residual covariance.

MEASURED: all six prespecified real fits complete in14.766s. These use disjoint
TARGET fit/held values but permit observed SOURCE stencil overlap, as declared
before fitting in real-plan.md and independently reviewed. Shared input noise
couples residuals; no statistical threshold, source label or ownership claim
is computed. RMS values below are black-subtracted source DN, not temporal
noise estimates or perceptual quality metrics.

| Fixed direction/support | Prediction RMS R/G1/G2/B | Unblurred-source RMS R/G1/G2/B |
| --- | --- | --- |
| Facet28→69, held extension |222.46 /370.11 /344.44 /275.96|567.27 /1122.89 /1059.69 /614.41|
| Dark33→69, held column |2186.95 /4919.28 /4755.43 /1960.78|2542.57 /5462.02 /5245.89 /2258.19|
| Nearby25→33, held continuation |50.48 /93.83 /115.08 /46.23|67.95 /92.11 /98.32 /45.04|

Facet forward prediction improves that held residual, but its training RMS
remains1199–1797DN and adjacent red error worsens. Dark forward fitting reaches
the fixed8-quad sigma ceiling in both axes; its reverse also leaves large
residuals. Nearby forward fitting improves training while worsening held G1,
G2 and B continuation errors. Both nearby directions numerically fit. The full
record retains every direction and support rather than only favourable entries.

This limited model has not supplied a useful automatic donor decision. A lower
residual can arise from smoothing, brightness mismatch or depth mixture, and
cannot establish ownership. The24-quad kernel support/8-quad sigma cap may also
be too narrow for the dark column about31 quads from its annotated core. A bound
hit therefore cannot refute relative blur generally. Original-site clipping,
asymmetry, chromatic spread and placement remain possible explanations, not
measured causes. No kernel-size/threshold search or full-stack render follows
from this fixed descriptive panel. Independent interpretation is recorded in
actual-results-review.md.

The reusable result is a small bounded fitter, independent counterexamples,
and exact wider source witnesses. Further automatic source work must establish
actual support membership and preserve nearby real structure; a compatibility
score alone does not provide that missing evidence.
