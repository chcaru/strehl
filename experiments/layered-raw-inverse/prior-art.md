# Narrow prior-art boundary

Read on 2026-09-19. The implementation is a small original layered-ray model,
not a port of another repository. No external implementation source was read.

The local audit is saved in
`../raw-affinity-support/next-inverse-audit.md`. M115 already tested multi-frame
Wiener inversion; it must not be described as merely single-frame work. M87's
two-layer unmixing and September14's common-latent CFA inverse also matter.
None of the searched records establishes a joint spatial reconstruction of
unknown layer radiances and coverage through coupled aperture-ray visibility.
That absence supports one test, not a claim of algorithmic novelty or success.

[Alonso et al., Optics Letters 2015](https://opg.optica.org/ol/abstract.cfm?uri=ol-40-8-1671)
already proposes physical space-variant PSF reconstruction of all-in-focus
images under strong defocus. Only the publisher's abstract was inspected;
this is prior art for the broad idea, not a verified implementation recipe.

[Sheng et al., Dr. Bokeh, CVPR 2024](https://shengcn.github.io/DrBokeh/)
uses a layered representation and an occlusion-aware differentiable renderer
for bokeh synthesis and depth-from-defocus. The authors' project description
and indexed paper text identify visibility at boundaries as important. This
does not establish their method as a RAW focus-stacking solution, or validate
our simplified two-sheet model. The project code was not opened.

The present first screen deliberately supplies the optical geometry. It fits
radiance and coverage from training original-CFA observations only. A useful
result would still owe unknown-optics calibration, original capture geometry,
real-image held-out prediction and complete-stack image comparison. A lower
training residual alone does not justify any of those steps.
