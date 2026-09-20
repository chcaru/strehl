# Independent fixed matrix-Cauchy controls

Root executes only after source review:

```text
matrix-cauchy-controls.py commission --out <run/commission>
matrix-cauchy-prior.py --source <screen-1/output> --alpha-root <visibility-1/alpha> --out <run/output>
matrix-cauchy-controls.py score --source <screen-1/output> --candidate <run/output> --reference <visibility-1/output> --out <run/scored>
```

One family, fixed before data: form native RGB Jacobian J=[dx dy] using forward
DN differences divided by original `b=sqrt(2*V(2048))`. Right/bottom missing
differences are zero; multiply dx by sqrt(W/(W-1)) and dy by sqrt(H/(H-1)).
Loss per native pixel is `log1p((||dx||²+||dy||²)/4+||dx cross dy||²/16)`;
average pixels and sheets. No new epsilon is necessary; a constant's loss is
exactly zero. This matches the original **global** small-gradient curvature,
not identical boundary placement of each local scalar term.

Keep original160 sheet starts, exact known alpha, injected noise/censor model,
forward optics, other objective terms and1000-iteration/1400-evaluation solver
budget with hard1800 evaluations. No parameter sweep, new evidence-dependent
switch, or copy of truth radiances into fitting.

Independent arithmetic checks use a different formulation: f64 eigendecomposition
of J-transpose-J and an independent determinant of I+J-transpose-J/4 must agree.
Compare these scalar oracles to the actual f32 cross-product implementation on
zero, rank1, rank2, weak and strong signed RGB columns. This is operator
commissioning, not noise calibration.

The conditional mechanism receives explicit positive and negative controls.
Let colour unit u=(1,2,2)/3, orthogonal colour w=(-2,1,0)/sqrt5, spatial unit
v=(.6,.8), and its orthogonal vector q=(-.8,.6). With strong rank1 J=16*u*vT:

- Add t*w*qT: independent colour **and spatial** direction. Actual second
  derivative at t0 must remain .5, checked against literal calculus.
- Add t*w*vT: new colour but the **same spatial** direction. J stays rank1 and
  curvature must instead be .5/65, below2% of the first control. This live
  counterexample prevents a false claim of universal chroma protection.
- Use J=16*u*vT+8*w*qT: both singular directions are strong. Derivative in t is
  t/[2*(1+t²/4)], and curvature is negative at t8. Matrix coupling therefore
  does not remove nonconvexity or guarantee preservation of a real crossing.

An RGB rotation mixing R/G must preserve loss. A fixed arbitrary perturbation
of both signed columns compares autograd with independent centred f64 finite
difference at .001. No derivative comparison is used as image-quality evidence.

For a non-square7×11 image, independent literal zero-padded projections check
the full image value. At a=0 in `2048+a*[x+2y,3x-y,2x+4y]`, actual Hessian must
match the old Huber's and the literal17.5/b² within f32 roundoff. Omitting either
rectangular normalization fails this live check. Different near/far gradients
also check sheet averaging and unchanged alpha TV/binary/radiance-L2 remainder.

The two fits use the already frozen flat and layered data. Flat is evaluated
first and must pass the original mean and paired visibility1 RGB/chroma1.05
bars. Layered retains every original image, true-colour component and held-out
bar, including bright samples. Fixed core and ridge must **each** have both RGB
and chroma error <=1.02 visibility1. Glint and the fixed glint-free filament
y31..41 must retain >=.98 of capped reference recovery in every colour; require
live reference recovery>=.5. No bad channel or region is omitted. Candidate and
reference initial near/far/alpha/pinhole arrays must be bit-equal.

Source/checkpoint hashes, exact fixed alpha, training-only read indices and all
evaluation limits remain enforced. Use final checkpoints only; numerical
refusal is explicit and stationarity is separate from quality/global optimality.
Flat mean/p01/p99 errors remain descriptive. The closed scalar-Cauchy result is
hash-linked only for context and cannot lower a requirement.

Flat errors can reward lost detail, and component projection can reward excess
correlated amplitude: retain both component and RGB/chroma tests. No scale
decomposition or matrix rank is an optical ownership truth label. A two-case
pass is only this known-alpha, known-discrete-optics result. It does not repair
the64/1024 physical mismatch, estimate visibility, or admit a photograph.
