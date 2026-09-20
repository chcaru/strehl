# Next visibility step: one bound-constrained continuation test

**ARGUED, not executed.** The smallest defensible step is a paired solver test
of the **original sheet-Huber objective**, with opacity fitted from observations
in physical coordinates instead of a sigmoid logit. This removes the supplied
alpha input; it does not identify physical opacity or fix the supplied optics.
Do not combine it with a new prior, pupil, output target, or calibrated depth.

The evidence is limited. `composite-latent-inspection.md` reports the original
free-alpha layered centre at alpha approximately .004: the sigmoid Jacobian
`alpha*(1-alpha)` is about .004, roughly sixty times below its maximum .25.
That is potential conditioning loss, not proof that it caused reconstruction
error. Saved receipts contain whole-state raw-gradient norms, not a profiled
opacity gradient. The composite prior's alpha=1 is a different rejected
objective and is not evidence for this hypothesis. Moreover, the known-alpha
original prior itself fails the bright held-out guard; an alpha solver cannot
be assumed to cure that remaining radiance/prior error.

**Exact consumer and comparison.** Restore the same original `screen-1`
160-step two-layer states for flat, layered, far-only and angular-mismatch.
Read no truth masks, sheets, held-out observations or fitted-oracle states.
Keep softplus sheet parameters, training indices, original censored DN
likelihood, all prior terms, 64 shared pupil rays, common PSF and supported
domain unchanged. Compare two continuations using the **same bound-constrained
L-BFGS implementation and evaluation budget**: baseline variables `(n,f,z)`
with `alpha=sigmoid(z)` and no finite bounds; candidate `(n,f,a)` with
`alpha=a, 0<=a<=1`. A small SciPy L-BFGS-B driver can call the existing streamed
Torch objective/adjoint; its optimizer bookkeeping may be f64, while all
image/state evaluations remain f32. This does not compare a new optimizer to
an old checkpoint alone. Both arms must initialize to the same fields and
objective within an independently commissioned f32 tolerance. Use the existing
1000-iteration/1400-evaluation settings and 1800 actual-evaluation hard cap,
counting initial/final monitors and every line-search trial identically.
No restarts, best-truth checkpoint choice, schedule sweep or budget extension.

For fixed sheets the sensor prediction is affine in opacity:

`y_k(a) = C B mean_p[ S_N(a*N) + (1-S_N(a))*S_F(F) ] + black`.

Thus the physical derivative is already available from the exact existing
forward/adjoint; the logit multiplies it by `a*(1-a)`. Box constraints express
coverage, not a new HDR cap. The heteroscedastic/censored likelihood and binary
prior are not a convex alpha problem; TV is nonsmooth. Record accepted-state
objective, physical-alpha projected gradient and sheet gradients, with explicit
line-search/stagnation/limit outcomes. A small raw-logit gradient cannot certify
opacity stationarity, and a projected-gradient number with TV's selected
subgradient is not a proof of a global minimum.

The supported-interior gauge still holds for constant `0<c<1`:
`a'=1-c*(1-a), F'=F/c, N'=a*N/a'`. Bilinear partition of unity preserves every
ray, the pinhole and observations. The original priors select its representative;
this test does not impose `max(1-a)=1`, which can require infinite near radiance
where premultiplied emission remains positive. Zero-padding boundaries do not
obey the constant-complement identity; commission it only on the full supported
interior. Storage remains two RGB sheets plus opacity and optimizer state,
with one original u16 observation/current graph, not an aligned-frame volume.

**Independent rejection power.** First commission an equal-colour constant
scene (zero data response to opacity), the finite gauge transformation, and
an actual two-depth crossing with a nonzero opacity response. Check one physical
alpha derivative against finite differences; deliberately retaining the sigmoid
factor must fail this control. Then score the fixed returned states using the
existing pinhole flat/RGB/chroma/component and held-out bars, with the matched
continuation as the additional comparator. Far-only catches invented near
structure; angular mismatch catches a plausible but wrong visibility explanation.
No alpha-truth accuracy, training NLL decrease, smooth mask or hidden-radiance
magnitude substitutes for delivered quality. If the physical-coordinate arm
does not improve the layered output while preserving flat and real colour, or
only lowers the objective while damaging truth, close this particular numerical
recipe without a strength/restart rescue. If both remain nonstationary, report
an unadmitted bounded optimization result, not failure of inverse reconstruction.

This is a practical non-oracle **generated** test, not an automatic RAW license.
The independent 64-versus-1024 pupil disagreement, unknown real optical/depth
parameters, alignment and model mismatch remain. It does not revive M115's
noise-amplifying Wiener inversion or M87's independently blurred layer unmixing;
the exact shared-ray visibility operator and injected-noise likelihood stay put.
