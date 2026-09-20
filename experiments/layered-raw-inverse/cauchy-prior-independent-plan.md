# Independent fixed Cauchy-prior controls

Root alone runs commissioning, two fixed fits, and final scoring:

```text
cauchy-prior-controls.py commission --out <run/commission>
cauchy-prior.py --source <screen-1/output> --alpha-root <visibility-1/alpha> --out <run/output>
cauchy-prior-controls.py score --source <screen-1/output> --candidate <run/output> --reference <visibility-1/output> --out <run/scored>
```

One global prior-family change: on each sheet use the original DN difference
norm `s²=(sum_RGB(deltaDN²)+1e-12)/(2*V(2048))`, but replace Huber by
`rho=2*log1p(s²/4)`. Retain the injected noise, fixed reference scale, spatial
and sheet means, all other objective terms, supplied true alpha, original160
sheet initialization and existing1000-iteration/1400-evaluation solver settings
(hard1800 evaluations). No local selector, coefficient search or adaptive scale.

Commissioning independently checks:

- Constant field's exact specified negligible epsilon floor and zero gradient.
- A nonconstant RGB field against literal f64 scalar log1p arithmetic. Candidate
  image arithmetic remains f32; calibration is supplied rather than verified.
- Actual two-pixel edge autograd at s0/.001/.1/1/2/4/16/64 against
  `s/(1+s²/4)`, accounting for the half spatial-direction mean. At s0, actual
  second derivative must equal one and the original Huber curvature within
  f32 roundoff (2e-6). The live small finite edge also matches the old penalty.
- Restoring force must decrease from s2 through4/16/64. This demonstrates the
  **risk** that an isolated spurious strong edge is weakly penalized, not a
  promised benefit. The s2 derivative is1, whereas Huber gives2.
- One central RGB impulse at (5,4) in a9×11 field, normalized amplitude s16,
  exercises the actual spatial penalty. Four incident edges give factor
  `1/(8*11)+1/(9*10)` after direction means; its force must match that factor
  times16/65, versus Huber times2, and be lower but nonzero. This is a restoring
  force risk witness, not a noise-contaminated image-quality pass.
- Adding +1000DN to an integer-valued nonconstant field leaves image penalty
  bit-exact and its common-brightness derivative approximately zero. Unlike
  shot normalization, this term supplies no brightness-denominator incentive.
- Distinct near/far gradient amplitudes check the sheet mean and independent
  literal remainder: unchanged alpha TV/binary and normalized radiance L2.

Wrong scale/sqrt factors, channel reduction, sheet averaging or a Huber-like
constant strong-edge derivative can fail these controls. A passing algebra
check does not imply that false edges will be rejected by the full likelihood.

Flat is scored first. Keep the original fixed RGB/chroma bounds against the
training-only mean and paired visibility1 reference (each1.05). Retain flat
per-channel mean bias and signed p01/p99 errors as descriptive overshoot
information. Layered keeps every original absolute image and held-out
prediction requirement, including the bright stratum and true glint/filament.
Add mandatory **both RGB and chroma error <=1.02 visibility1** in fixed core and
ridge regions. Each glint and glint-free filament y31..41 colour must retain
>=.98 of capped visibility1 recovery, with live reference recovery>=.5; no
failed colour may be omitted. The original absolute component bar also remains.

Initial near/far/alpha/pinhole arrays must equal visibility1 bit-for-bit, so
immediate recomposition cannot explain a difference. Compare only the prescribed
final result, never an iteration chosen by truth. Bind original sources, alpha,
checkpoints, read indices and reference outputs. Numerical refusal is explicit;
stationarity and image quality are separate. The retained shot-prior result is
hash-linked for descriptive comparison only and never used to relax a bar.

Failure directions remain explicit: flat error rewards oversmoothing, hence
the protected coloured component tests; projection can credit excess amplitude,
hence capped recovery plus RGB/chroma errors; aggregate prediction can hide
bright errors, hence separate strata. Redescending curvature can create local
minima and false sharp edges even when the numerical optimizer stops. No
global-optimum conclusion follows from a raw-parameter gradient.

Even a two-case pass licenses only a separately frozen new-seed flat/layered
and weak non-affine chromatic common-sheet stress test, with new training-only
initialization and paired Huber. It does not admit photography, solve unknown
visibility, overturn prior failures, or repair the failed64/1024 optical guard.
