# Independent ribbon-screen result

2026-10-27. **MEASURED conditional generated success; no photographic admission.** The bounded two-capsule fit retains both thin structures and their crossing, with acceptable held predictions under the supplied optics. This is useful evidence for the continuous shared-ray representation. It does not establish automatic topology, uniquely recovered geometry, arbitrary radiance, mismatch rejection, or an immediate original-photo route.

## Integrity and execution

VERIFIED current control/model hashes against `observations.json`; read root's completed invocation/process receipts. The actual command was:

```text
python -I -B -X faulthandler experiments/raw-quality-2026-10-26/ribbon-visibility/independent-controls.py --out outputs/raw-quality-2026-10-26/ribbon-visibility-1
```

Exit 0, 13.172 seconds, zero terminal active processes, no error or cleanup error. Peak job commitment was 2,741,702,656 bytes. Torch GPU allocation/reservation peaked at 21,633,536/25,165,824 bytes, excluding driver/runtime memory. One CPU worker, RTX5090, Torch2.11.0+cu128/CUDA12.8, both TF32 flags false. These are one tiny job's operational costs, not full-stack performance.

No model import, RAW read, fit, or numerical rerun was performed during review. Saved complete arrays were converted only for viewing: signal-DN/14848, fixed gain2, sRGB transfer, identical ICC, no clipping. Inspected native32x28 truth/final images and complete256x224 nearest-replicated truth/final/null/known-geometry views. Replication duplicates pixels; it supplies no extra resolution.

## Operator evidence

Flat-forward error is exactly 0 DN; supplied noisy flat observations have RMS0.996 sigma. **This is not inverse flat-noise validation.** Equal-colour geometry remains unidentifiable.

Independent8192/32768-node reference disagreement is RMS0.234 DN, maximum1.436 DN, or0.0106/0.0650 supplied sigma on the fixed selected queries. Producer/reference disagreement is RMS0.1167 sigma, maximum1.318, within the declared finite-quadrature envelope. These checks qualify this numerical operator, not the optical assumptions for Sony captures.

Reversing only first-hit order produces16.420-DN RMS difference; multiplying marginal coverages produces2.579 DN. Both exceed the predeclared reference-precision allowance. Their non-null results support actual shared-ray ordering. Translation identity is exactly0 DN but remains an ungated observation. No separate infinite-strip or blur-displacement discriminator ran.

## Unknown fit and complete output

The fit used480 original-u16 CFA observations from five supplied views; two views stayed held. It completed the fixed73 evaluations without a convergence or identifiability claim. Training normalized MSE falls4.172→0.990 after conditional radiance fitting at each geometry. The null-constant MSE is50.232. The displayed initial image has uniform3400-DN colours: it is a null, **not** a fair radiance-refit initial-geometry image, so its image improvement cannot be attributed solely to geometry.

Complete held prediction RMS is1.150 sigma; phase RMS values are1.107–1.194. The dense independent final-state operator gives1.157 sigma on64 balanced held queries, with2.190-DN producer/reference RMS disagreement. This supports the returned conditional prediction beyond the producer's own quadrature.

Whole pinhole RGB error is27.276 DN. Near/far/crossing components retain0.984/1.011/0.979 of truth and pass the fixed90% guards; deliberate near/far erasure returns zero and fails. Recovery above1 is slight overcontrast, not extra detail. The complete images visibly retain the finite green and magenta structures and their crossing, with small coverage/colour differences. The known-geometry forward image is closer, at1.385-DN whole error.

Geometry is not exact: fitted radii0.305/0.227 versus true0.28/0.19 make widths approximately9%/19% larger, accompanied by altered radiances. Fitted depths0.25/0.81 are close to supplied truth0.25/0.80, but conditional full radiance rank cannot establish unique geometry. This shape–radiance tradeoff remains visible despite a good image and prediction result.

## Remaining boundary

Fixed opaque-versus-translucent discrepancy is3.661 sigma; constant-background-versus-glint is3.067 sigma. These are known-model mismatch observations. No mismatch fit or automatic refusal ran. A single translucent constant-colour object over a constant background remains colour/transmittance-ambiguous.

Two supplied constant-colour capsules cannot represent the proposed real marigold family or general insect surfaces. Initialization/topology, spatial radiance, calibrated optical behaviour, uncertainty fallback, and complete-image consumption remain missing. Do not advance directly to an original photographic fit or call this an occlusion-halo repair. Retain the conditional positive without reversing earlier qualified glint or free-alpha failures. The corpus quality goal remains open.

## Complete retained evidence

[Native truth](saved-previews/truth_pinhole.png), [native fitted image](saved-previews/final_pinhole.png), [complete truth replicated8x](saved-previews/truth_pinhole-nearest8.png), [complete fit replicated8x](saved-previews/final_pinhole-nearest8.png), [preview/hash receipt](saved-previews/receipt.json), [full float masters](../../../outputs/raw-quality-2026-10-26/ribbon-visibility-1/fit-outputs.npz), [observations](../../../outputs/raw-quality-2026-10-26/ribbon-visibility-1/observations.json), [process receipt](../../../outputs/raw-quality-2026-10-26/ribbon-visibility-job-1/process.json).

Observation SHA256 `d44fea333d923147fca5520500ea21be0a821919c29ce5ed217877422a64a194`; float masters `f9001b5c39b11482e22ea211f2351228513e0c39a07f8cd614362098c0730d57`.
