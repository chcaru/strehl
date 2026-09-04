# M164 preregistration amendment 1 — constructive improvement ambiguity

Status: frozen before any M164 measurement pixel was decoded.

The mandatory optical-improvement ladder in `PREREGISTRATION.md` tests whether
fresh downstream noise keeps a real improvement outside the deterministic
post-transfer family. It does not by itself prove the sharper direction's
identifiability limit.

Add one second, non-substitutive improvement arm on every development crop:

```text
truth = S
A     = quantize(G_0.80(S))
B     = quantize(A + 0.50 * (A - G_1.00(A)))
```

Measure truth MSE for both outputs. If `MSE(B,S) < MSE(A,S)`, `B` is a planted
improvement by an external truth unavailable to the veto, while also being a
literal common post-render unsharp mask of `A`. Report whether the veto fires.
No outcome from this arm may alter the frozen gate.

This is the constructive indistinguishability case: an output-only observer
cannot label the same `(A,B)` pair “good deconvolution” when truth is present
and “mere sharpening” when truth is hidden. A fire is therefore not an
arithmetic defect in the veto; it is the exact boundary that keeps the veto
from being interpreted as a quality metric.
