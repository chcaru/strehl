# Independent actual-source descriptive review

2026-09-19. **Preserve these six fixed results and stop; no automatic source
assignment or full-render admission.** Root's run completed in14.766 seconds
with unchanged bindings. This review reads the retained results and source;
no refit, new measurement or parameter search was performed.

All values below are black-subtracted DN RMS in[R,G1,G2,B] order, not noise
significance or ownership probabilities.

- **Facet28→69:** the fitted blur reduces held extension error from roughly
  [567,1123,1060,614] to[222,370,344,276]. This is a real descriptive transfer
  beyond the fitted target pixels. Yet core training errors remain1199–1797DN,
  and adjacent red error rises while the other channels improve. Reverse gives
  little extension improvement. The asymmetry suggests this local forward
  model captures some change; it does not certify one physical PSF or source
  ownership, especially with clipping unexcluded.
- **Dark33→69:** both fitted sigmas hit the8-quad ceiling; training errors are
  4229–6085DN and the held column remains[2187,4919,4755,1961]. Reverse is also
  a poor description, despite its numerical `fitted` status. The bounded
  family is crucial: annotated core centre(256,257) and column centre
  (255.5,288.5) are about31.5quads apart, beyond the24-quad kernel radius.
  A compact point at that centre contributes exactly zero there under this
  truncated model; an extended source can contribute through nearer samples.
  Thus this trial may be too short-ranged to express the proposed tail
  spreading. It closes neither broader relative blur nor physical core
  ownership. The bound hit cannot favour the reverse direction.
- **Nearby25→33:** training improves, but continuation changes from about
  [68,92,98,45] to[50,94,115,46]: only red improves. Reverse worsens all four
  continuation channels. Both directions numerically fit. This is a concrete
  warning against propagating a core fit into neighbouring real structure or
  interpreting optimizer success as a shared-depth label.

The real split is deliberately weaker than the generated screen: fit and
held-out TARGET pixels are disjoint, while observed SOURCE convolution
stencils may overlap the held region. This does not feed held target values
into the objective, but shared source noise couples residuals. No calibrated
compatibility threshold was used. The exported guide variance is not composed
four-plane covariance, and original-site clipping remains unknown. MHC,
resampling/CA, residual placement, mixed depths, spectral/asymmetric spread
and brightness change can all contribute; this check distinguishes none of
them causally.

There is a limited positive observation at the facet and no reliable ownership
rule across the protected examples. Retain the exact linear source cache and
signed predictions/residuals. Do not turn smaller residuals into fusion
weights, reinterpret numerical refusals as reverse evidence, or broaden the
kernel after inspecting this outcome within the same frozen trial.

| Binding | SHA256 |
| --- | --- |
| real-1/output/result.json | 3f76584c988e1ba86d2e7e02929ca585106270767f9d03c3df24f174b024b950 |
| real-1/process.json | a5615644fc223b0c96a9e8e74443a48bb8d7b65fba215e287b36a0713d87cf9b |
| real-plan.md | 9de19bc6f88f1e18131d04450426ac695e79d3a0a662ce016b46f72b824e82d0 |
| real-check.py | 5cd1e108d5c394f48a249bea1aaf583e28baadedc91590b83d3dd6f4f6e43747 |
| model.py | 4a40f8b201e5baaf47597203b8031e896bb68c0b005e2b09082d8b6adc739e0c |
