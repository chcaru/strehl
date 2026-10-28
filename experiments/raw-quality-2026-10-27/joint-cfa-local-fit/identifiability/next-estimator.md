# Local variance-bounded bands: design checkpoint, no code release

2026-10-27. **DERIVED / ARGUED, source-only.** The deflated flat remains worse than the actual product in RGB/chroma after its large bias is removed. Do not extend that solver. I proposed local variance-bounded band estimation as a different direction, but the initial paragraph was underspecified. The concrete route below exposes limitations that prevent an implementation recommendation now. No additional experiment, solver, dependency or numerical job is authorized.

## Concrete estimand and what would stream

For each colour and reference-pyramid band location, use the six continuous native-pixel basis functions `phi=[1,x,y,x*x,x*y,y*y]`, centred at that location. A source row d is their exact integral over the mapped original sensel square, including its transformed second moment; y is original black-subtracted DN. No per-source RGB is constructed. A band's prospective spatial support must cover the actual signed reference analysis row, expanded by the original-sensel footprint. Merely naming a small radius does not establish that support.

Let h be the literal signed row of a declared reference pyramid analysis, including its boundary rule. The target is `t=sum_p h[p]*integral_reference_cell(phi,p)`. This estimates the actual band functional of the fitted local field. It is not a fitted full-value image renamed as a band. Interior AC rows annihilate constants; the base does not. Separate fixed, noise-gated source admissions apply to each band, so the same scalar full-value mixture obstruction does not apply directly.

For frozen spatial/admission weights w and the injected original variances:

`M=sum w*d*dT; r=sum w*d*y; Q=sum w*w*variance*d*dT`

`band=tT*M_inverse*r; conditional_variance=tT*M_inverse*Q*M_inverse*t`.

Use a checked small solve, not an unchecked inverse. M, r and Q need21+6+21 f32 accumulators per colour/band location. This offers streamed sufficient statistics, avoiding iterative visits to all299 originals. At full native RGB density, a dyadic pyramid would require roughly `48*4*(4/3)*3*W*H` bytes: about24.3GB for6896x4596 before output, geometry or source buffers. Thus a whole-resident implementation already exceeds the earlier14GiB host budget. Tiling with exact analysis/synthesis halos or separate colour passes is necessary; no competitive-time claim is established. A source-tiled u16 cache can avoid repeated RAW decoding, but does not make repeated I/O free.

## Why this is not ready

1. **Fine structure is not guaranteed by signed moments.** A six-dimensional quadratic model preserves only its specified moments. Native .22-cycle detail, independent coloured texture, thin hairs and crossings are not quadratic. The October16 positive kernel already softened complete photographs; a signed quadratic correction is a real difference, but no demonstrated remedy. A higher-order/radius sweep would repeat the unproductive direction.
2. **The variance reference was not defined correctly in the initial proposal.** A positive smoother is a full-value estimator, not a nonzero DC-annihilating band estimator. A difference of positive smoothers is signed. It requires the covariance of its shared original samples. Moreover, a minimum-variance unbiased DC estimate plus a nonzero zero-DC correction generally increases variance; a strict cap at that DC estimator's variance can force the correction to zero. That would pass flat noise by removing detail.
3. **Individual Q matrices do not certify the synthesized image.** Bands, neighbouring coefficients and their synthesis kernels share original samples. Final variance is the variance of the complete combined kernel, including cross terms. Data-dependent admissions or an output limiter make frozen-weight propagation conditional, not the stochastic variance of the whole estimator. A proposed cap must not disguise either distinction.
4. **Rank refusal needs a complete-output policy.** Replacing ill-conditioned fine estimates with a positive/coarse estimate changes spatial response and can erase genuine colour. Such fallback is a prior decision requiring independent detail tests, not a mechanical success state.

The smallest decisive existing witnesses would be the actual flat, fine-near/far-coarse pair, independent red/blue plus8DN green, and repeated/diverse-phase alias pair under the same blur competition. A zero-detail fallback must fail them. A common-band admission foil would test whether the new target actually escapes the full-value mixture. These are falsifiers, not a dispatch request.

**Recommendation:** do not allocate code for this candidate as currently specified. It lacks a defensible complete-kernel variance budget and a proven adequate fine-detail representation. The earlier local-mode paragraph should not be treated as an implementable noise-safe architecture. This closes this proposal without asserting that local original-CFA estimation, regularization, or direct reconstruction in general is impossible. A replacement design must supply those missing choices before another generated screen; no further mode census or numerical campaign follows from this note.
