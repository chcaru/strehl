# Independent fixed shot-noise-prior controls

Root runs commissioning before either fit, then scores prescribed final states:

```text
shot-noise-prior-controls.py commission --out <run/commission>
shot-noise-prior.py --source <screen-1/output> --alpha-root <visibility-1/alpha> --out <run/output>
shot-noise-prior-controls.py score --source <screen-1/output> --candidate <run/output> --reference <visibility-1/output> --out <run/scored>
```

Only the hidden-sheet image prior changes. For each spatial edge, use the
supplied gain and c=read_variance+1/12 in
`sqrt(2)*(S2-S1)/(sqrt(g*S2+c)+sqrt(g*S1+c))`, then the same RGB vector Huber
delta2, spatial-direction mean and sheet mean. All likelihood, fixed true alpha,
original screen160 sheet initialization, other prior coefficients and solver
bounds stay fixed. No gain fitting, empirical noise estimate, strength search,
clipping change, or restart is authorized. Both cases use the same seven
training frames; neither of the two held-out frames initializes or optimizes.

Pure helper commissioning runs on CPU and does not fit an image:

- Constant image has negligible original epsilon residual and exactly zero
  spatial image gradient. The inherited 1e-12 DN² norm epsilon is divided by
  `2*(g*2048+c)` in normalized units; this is not an exact-zero scalar claim.
- A nonconstant three-colour field matches an independent f64 scalar oracle
  using differences of literal `h(S)=sqrt(2)/g*sqrt(g*S+c)`. Candidate image
  arithmetic remains f32. Missing sqrt(2), wrong variance, channel averaging or
  wrong spatial support can fail this oracle.
- Small variations around 2048DN match the original fixed-scale prior to .2%.
  The nonzero prior is asserted. This checks local normalization, not sensor
  calibration; both functions share the supplied calibration.
- Autograd along a contrast direction matches a centred independent literal
  finite difference at fixed step .001; derivative must be live. Tolerance is
  1e-4+.002*abs(derivative), specified before data.
- Adding a uniform +1000DN to the nonconstant field must reduce the image
  penalty and have a negative brightness derivative. A ±1DN independent
  difference must agree to 1e-7+.002*abs(derivative). **This is the expected
  brightness-bias incentive, not a pass requirement that it disappear.** Its
  sign is reported separately from the data likelihood and unchanged L2 term.
- Different near/far images test the two-sheet mean and an independent literal
  sum of unchanged alpha TV, binary and normalized radiance L2 terms.

The fixed-alpha flat case is scored first. Reuse all original independent
absolute image and held-out prediction bars unchanged, including bright
prediction strata. Flat RGB/chroma must remain within1.05 of the training mean
and within1.05 of visibility-1. Report per-channel valid-interior mean error,
signed p01 and p99 error separately as descriptive bias/overshoot witnesses;
these do not replace noise or image bars.

For layered, keep original whole/core/ridge/mean/restricted-far-only comparisons
and true component bars. In addition, core/ridge RGB error must be <=1.02 of
the retained visibility-1 result, and glint plus glint-free filament y31..41
must retain >=.98 of capped per-channel reference recovery. References must be
live with recovery>=.5 in every colour; no failed colour is skipped. Initial
near/far/alpha/pinhole arrays must be bit-equal between candidate and reference.

Existing half-component and colour-swapped destroyers give the inherited
metrics power to reject smoothed/decoloured detail. Component projections can
credit excessive correlated signal, so capped recovery and RGB truth error
remain paired; flat error alone can reward excessive smoothing, so structured
component guards remain mandatory. A lower objective cannot compensate for a
failed image, colour, or held-out bar. A numerical refusal remains explicitly
incomplete, not a measured quality failure. No best-iteration selection.

All input, reference and output hashes are retained. Report stationarity in
raw softplus parameter coordinates separately from quality and from global
optimality. Existing failed screens and 64-versus-1024 physical-adequacy failure
remain unchanged. Even a pass is utility under known discrete optics and true
coverage; it is not calibration, a real-photo licence, or SOTA evidence.
